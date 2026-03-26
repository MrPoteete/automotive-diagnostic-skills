#!/usr/bin/env python3
# Checked AGENTS.md - implementing directly because this is a straightforward
# data ingestion script with no auth logic, no user-facing security boundaries,
# and no complex architecture decisions. Security-engineer delegation is not
# warranted for a CLI tool that reads public URLs and writes to local ChromaDB.
"""
ingest_url.py — Ingest a URL (web page or YouTube video) into the mechanics_forum ChromaDB collection.

Usage:
    uv run python scripts/ingest_url.py "https://..."
    uv run python scripts/ingest_url.py "https://..." --dry-run

Source weights (higher = more authoritative):
    1.0  — NHTSA, official government
    0.85 — Manufacturer official, AllData
    0.75 — YouTube repair videos, iATN professional network
    0.60 — Quality forums (BITOG, F150Forum, etc.)
    0.55 — Reddit
    0.50 — Unknown/general forum (default)
"""

import argparse
import hashlib
import logging
import os
import re
import shutil
import sys
import textwrap
from pathlib import Path
from typing import Optional
from urllib.parse import urlparse

import chromadb
import requests
from bs4 import BeautifulSoup

# ── Paths ─────────────────────────────────────────────────────────────────────
PROJECT_ROOT = Path(__file__).parent.parent
CHROMA_PATH = PROJECT_ROOT / "data" / "vector_store" / "chroma"
COLLECTION_NAME = "mechanics_forum"

# Optional Firecrawl (local instance on desktop)
FIRECRAWL_URL = os.getenv("FIRECRAWL_URL", "")  # e.g. http://192.168.1.100:3002
FIRECRAWL_KEY = os.getenv("FIRECRAWL_API_KEY", "local-only")

# ── Source weight table ────────────────────────────────────────────────────────
DOMAIN_WEIGHTS: dict[str, float] = {
    # Government / official
    "nhtsa.gov": 1.0,
    "regulations.gov": 1.0,
    "cpsc.gov": 1.0,
    "tc.gc.ca": 1.0,
    # Manufacturer official
    "ford.com": 0.85,
    "gm.com": 0.85,
    "chevrolet.com": 0.85,
    "buick.com": 0.85,
    "cadillac.com": 0.85,
    "gmc.com": 0.85,
    "dodge.com": 0.85,
    "ram.com": 0.85,
    "jeep.com": 0.85,
    "chrysler.com": 0.85,
    "toyota.com": 0.85,
    "lexus.com": 0.85,
    "honda.com": 0.85,
    "acura.com": 0.85,
    "mopar.com": 0.85,
    "acdelco.com": 0.85,
    "alldata.com": 0.85,
    # Professional / high-quality
    "youtube.com": 0.75,
    "youtu.be": 0.75,
    "iatn.net": 0.75,
    "motorweek.org": 0.75,
    # Quality forums
    "bobistheoilguy.com": 0.60,
    "f150forum.com": 0.60,
    "f150gen14.com": 0.60,
    "silveradosierra.com": 0.60,
    "gmtrucks.com": 0.60,
    "cumminsforums.com": 0.60,
    "cumminsforum.com": 0.60,
    "ramforumz.com": 0.60,
    "dodgecummins.com": 0.60,
    "tundratalk.net": 0.60,
    "tacomatalk.net": 0.60,
    "teamswift.net": 0.60,
    # Reddit
    "reddit.com": 0.55,
    "old.reddit.com": 0.55,
}
DEFAULT_WEIGHT = 0.50

# ── Chunking ──────────────────────────────────────────────────────────────────
CHUNK_SIZE = 400     # target words per chunk
CHUNK_OVERLAP = 50   # overlap words between chunks


def _weight_for_url(url: str) -> float:
    host = urlparse(url).netloc.lower().lstrip("www.")
    for domain, weight in DOMAIN_WEIGHTS.items():
        if host == domain or host.endswith(f".{domain}"):
            return weight
    return DEFAULT_WEIGHT


# ── Disk-space guardrail ──────────────────────────────────────────────────────
MIN_FREE_GB = 5  # refuse to download anything if less than this is free

def _check_disk_space(log: logging.Logger) -> None:
    """Abort if free disk space is below MIN_FREE_GB."""
    usage = shutil.disk_usage("/")
    free_gb = usage.free / (1024 ** 3)
    pct_used = usage.used / usage.total * 100
    if free_gb < MIN_FREE_GB:
        log.error(
            f"Disk guardrail: only {free_gb:.1f} GB free ({pct_used:.0f}% used). "
            f"Refusing to download. Free up space or raise MIN_FREE_GB."
        )
        sys.exit(1)
    log.debug(f"Disk OK: {free_gb:.1f} GB free ({pct_used:.0f}% used)")


VIDEO_HOSTS = {"youtube.com", "youtu.be", "vimeo.com", "dailymotion.com", "rumble.com"}

def _source_type(url: str) -> str:
    host = urlparse(url).netloc.lower().lstrip("www.")
    if any(vh in host for vh in VIDEO_HOSTS):
        return "youtube"  # treated as video type regardless of platform
    return "web"


def _chunk_text(text: str) -> list[str]:
    words = text.split()
    chunks: list[str] = []
    start = 0
    while start < len(words):
        end = min(start + CHUNK_SIZE, len(words))
        chunks.append(" ".join(words[start:end]))
        start += CHUNK_SIZE - CHUNK_OVERLAP
    return [c for c in chunks if len(c.split()) >= 30]


# ── Video (yt-dlp) ────────────────────────────────────────────────────────────
# Strategy (disk-safe):
#   Phase 1 — transcript only (skip_download=True): no video bytes touch disk.
#   Phase 2 — lowest-quality audio only, only if Phase 1 yields no subtitles.
#             Video files are deleted immediately after the VTT is read.
# A disk-space check runs before any download attempt.

def _parse_vtt(raw: str) -> str:
    lines, seen = [], set()
    for line in raw.splitlines():
        line = line.strip()
        if (not line or "-->" in line or line.startswith("WEBVTT")
                or re.match(r"^\d+$", line) or re.match(r"^[\d:\.]+$", line)):
            continue
        line = re.sub(r"<[^>]+>", "", line).strip()
        if line and line not in seen:
            seen.add(line)
            lines.append(line)
    return " ".join(lines)


def _fetch_video(url: str, log: logging.Logger) -> tuple[Optional[str], dict]:
    """Fetch transcript + metadata for any yt-dlp supported URL.

    Returns (transcript_text, metadata_dict). metadata_dict is empty on failure.
    """
    _check_disk_space(log)

    try:
        import yt_dlp
    except ImportError:
        log.error("yt-dlp not installed. Run: uv pip install yt-dlp")
        return None, {}

    import tempfile

    # ── Phase 1: transcript only (no video download) ──────────────────────────
    base_opts = {
        "writeautomaticsub": True,
        "writesubtitles": True,
        "subtitleslangs": ["en"],
        "subtitlesformat": "vtt",
        "quiet": True,
        "no_warnings": True,
    }

    meta: dict = {}

    with tempfile.TemporaryDirectory() as tmpdir:
        opts = {**base_opts, "skip_download": True, "outtmpl": os.path.join(tmpdir, "%(id)s")}
        try:
            with yt_dlp.YoutubeDL(opts) as ydl:
                info = ydl.extract_info(url, download=True)
            meta = {
                "video_title": info.get("title", ""),
                "channel": info.get("uploader", info.get("channel", "")),
                "upload_date": info.get("upload_date", ""),
                "duration_secs": info.get("duration", 0),
                "view_count": info.get("view_count", 0),
            }
            log.info(f"Video: {meta['video_title']} | {meta['channel']}")
        except Exception as exc:
            log.error(f"yt-dlp phase-1 failed: {exc}")
            return None, {}

        vtt_files = [f for f in os.listdir(tmpdir) if f.endswith(".vtt")]
        if vtt_files:
            with open(os.path.join(tmpdir, vtt_files[0]), encoding="utf-8") as f:
                raw = f.read()
            text = _parse_vtt(raw)
            log.info(f"Phase 1 transcript: {len(text.split())} words")
            return text, meta

    # ── Phase 2: lowest-quality audio download (transcript unavailable) ────────
    log.warning("No subtitles in phase 1 — falling back to lowest-quality audio download")
    _check_disk_space(log)  # re-check before actually downloading bytes

    with tempfile.TemporaryDirectory() as tmpdir:
        opts = {
            **base_opts,
            "skip_download": False,
            "format": "worstaudio/worst",        # absolute minimum bytes
            "postprocessors": [],                 # no conversion, just raw audio
            "outtmpl": os.path.join(tmpdir, "%(id)s.%(ext)s"),
        }
        try:
            with yt_dlp.YoutubeDL(opts) as ydl:
                ydl.extract_info(url, download=True)
        except Exception as exc:
            log.error(f"yt-dlp phase-2 failed: {exc}")
            return None, meta

        vtt_files = [f for f in os.listdir(tmpdir) if f.endswith(".vtt")]
        if not vtt_files:
            log.warning("No subtitles after phase-2 download — skipping")
            # tmpdir context manager removes all downloaded files on exit
            return None, meta

        with open(os.path.join(tmpdir, vtt_files[0]), encoding="utf-8") as f:
            raw = f.read()
        # All downloaded files (audio + vtt) are deleted when tmpdir exits here

    text = _parse_vtt(raw)
    log.info(f"Phase 2 transcript: {len(text.split())} words")
    return text, meta


# ── Web scraping ──────────────────────────────────────────────────────────────
def _fetch_via_firecrawl(url: str, log: logging.Logger) -> Optional[str]:
    if not FIRECRAWL_URL:
        return None
    try:
        resp = requests.post(
            f"{FIRECRAWL_URL}/v1/scrape",
            headers={"Authorization": f"Bearer {FIRECRAWL_KEY}", "Content-Type": "application/json"},
            json={"url": url, "formats": ["markdown"]},
            timeout=30,
        )
        if resp.status_code == 200:
            data = resp.json()
            text = data.get("data", {}).get("markdown", "")
            if text:
                log.info(f"Firecrawl: {len(text.split())} words")
                return text
    except Exception as exc:
        log.warning(f"Firecrawl unavailable, falling back to requests: {exc}")
    return None


def _fetch_via_requests(url: str, log: logging.Logger) -> Optional[str]:
    headers = {"User-Agent": "Mozilla/5.0 (compatible; automotive-diagnostic-bot/1.0)"}
    try:
        resp = requests.get(url, headers=headers, timeout=20)
        resp.raise_for_status()
    except Exception as exc:
        log.error(f"HTTP fetch failed: {exc}")
        return None

    soup = BeautifulSoup(resp.text, "html.parser")
    for tag in soup(["nav", "header", "footer", "script", "style", "aside", "form"]):
        tag.decompose()

    content = soup.find("article") or soup.find("main") or soup.find("body")
    if not content:
        log.error("No parseable content found")
        return None

    text = content.get_text(separator=" ", strip=True)
    text = re.sub(r"\s+", " ", text).strip()
    log.info(f"requests+BS4: {len(text.split())} words")
    return text


def _fetch_web(url: str, log: logging.Logger) -> Optional[str]:
    text = _fetch_via_firecrawl(url, log)
    if text:
        return text
    return _fetch_via_requests(url, log)


# ── ChromaDB ──────────────────────────────────────────────────────────────────
def _get_collection() -> chromadb.Collection:
    client = chromadb.PersistentClient(path=str(CHROMA_PATH))
    return client.get_or_create_collection(
        name=COLLECTION_NAME,
        metadata={"hnsw:space": "cosine"},
    )


def _ingest(url: str, dry_run: bool, log: logging.Logger) -> int:
    stype = _source_type(url)
    weight = _weight_for_url(url)
    log.info(f"URL type: {stype} | weight: {weight}")

    video_meta: dict = {}
    if stype == "youtube":
        text, video_meta = _fetch_video(url, log)
    else:
        text = _fetch_web(url, log)

    if not text:
        log.error("No content retrieved — aborting")
        return 0

    chunks = _chunk_text(text)
    log.info(f"Chunks: {len(chunks)}")

    if dry_run:
        log.info("[DRY-RUN] Would upsert %d chunks. First chunk preview:", len(chunks))
        if video_meta:
            log.info(f"  Title: {video_meta.get('video_title')} | Channel: {video_meta.get('channel')}")
        print(textwrap.shorten(chunks[0], width=300, placeholder="..."))
        return len(chunks)

    collection = _get_collection()
    url_hash = hashlib.md5(url.encode()).hexdigest()[:12]
    host = urlparse(url).netloc.lower().lstrip("www.")

    ids = [f"ingest_{url_hash}_{i}" for i in range(len(chunks))]
    base_meta: dict = {
        "source": host,
        "source_type": stype,
        "source_weight": weight,
        "canonical_url": url,
        **{k: str(v) for k, v in video_meta.items() if v},  # flatten video metadata
    }
    metadatas = [{**base_meta, "chunk_index": i} for i in range(len(chunks))]

    collection.upsert(documents=chunks, metadatas=metadatas, ids=ids)
    log.info(f"Upserted {len(chunks)} chunks from {url}")
    return len(chunks)


# ── CLI ───────────────────────────────────────────────────────────────────────
def main() -> None:
    parser = argparse.ArgumentParser(description="Ingest a URL into mechanics_forum ChromaDB collection")
    parser.add_argument("url", help="URL to ingest (web page or YouTube video)")
    parser.add_argument("--dry-run", action="store_true", help="Preview without writing to ChromaDB")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    log = logging.getLogger("ingest_url")

    count = _ingest(args.url, args.dry_run, log)
    if count:
        status = "[DRY-RUN] " if args.dry_run else ""
        print(f"\n{status}Done — {count} chunks {'would be ' if args.dry_run else ''}ingested.")
    else:
        sys.exit(1)


if __name__ == "__main__":
    main()
