#!/usr/bin/env python3
# Checked AGENTS.md - implementing directly because this is a data pipeline script
# with no auth boundaries, no user-facing security surfaces, and straightforward logic.
"""
bulk_ingest.py — Bulk ingest recent videos from curated automotive YouTube channels.

Fetches the latest N videos per channel, skips already-ingested ones,
and stores transcripts + metadata into the mechanics_forum ChromaDB collection.

Usage:
    uv run python scripts/bulk_ingest.py                    # all channels, 20 videos each
    uv run python scripts/bulk_ingest.py --limit 10         # 10 videos per channel
    uv run python scripts/bulk_ingest.py --channel rainman  # single channel by key
    uv run python scripts/bulk_ingest.py --min-views 10000  # skip low-view videos
    uv run python scripts/bulk_ingest.py --dry-run          # preview without writing

Add new channels to CHANNELS dict below.
"""

import argparse
import hashlib
import logging
import os
import re
import sys
import tempfile
from pathlib import Path
from urllib.parse import urlparse

import chromadb
import requests
from bs4 import BeautifulSoup

# ── Paths ─────────────────────────────────────────────────────────────────────
PROJECT_ROOT = Path(__file__).parent.parent
CHROMA_PATH  = PROJECT_ROOT / "data" / "vector_store" / "chroma"
COLLECTION_NAME = "mechanics_forum"

# ── Curated channel list ───────────────────────────────────────────────────────
# Keys are short names used with --channel flag.
# Values are YouTube channel URLs (@handle or /channel/ID both work).
CHANNELS: dict[str, dict] = {
    "rainman":   {"url": "https://www.youtube.com/@RainmanRaysRepairs/videos",  "weight": 0.75},
    "southmain": {"url": "https://www.youtube.com/@SouthMainAuto/videos",       "weight": 0.75},
    "scotty":    {"url": "https://www.youtube.com/@ScottyKilmer/videos",        "weight": 0.70},
    "humble":    {"url": "https://www.youtube.com/@HumbleMechanic/videos",      "weight": 0.75},
    "fordtech":  {"url": "https://www.youtube.com/@FordTechMakuloco/videos",    "weight": 0.80},
    "scanner":   {"url": "https://www.youtube.com/@ScannerDanner/videos",       "weight": 0.80},
}

# ── Chunking ──────────────────────────────────────────────────────────────────
CHUNK_SIZE    = 400
CHUNK_OVERLAP = 50


def _chunk_text(text: str) -> list[str]:
    words = text.split()
    chunks: list[str] = []
    start = 0
    while start < len(words):
        end = min(start + CHUNK_SIZE, len(words))
        chunks.append(" ".join(words[start:end]))
        start += CHUNK_SIZE - CHUNK_OVERLAP
    return [c for c in chunks if len(c.split()) >= 30]


def _already_ingested(collection: chromadb.Collection, video_url: str) -> bool:
    url_hash = hashlib.md5(video_url.encode()).hexdigest()[:12]
    results = collection.get(ids=[f"bulk_{url_hash}_0"])
    return len(results["ids"]) > 0


def _get_collection() -> chromadb.Collection:
    client = chromadb.PersistentClient(path=str(CHROMA_PATH))
    return client.get_or_create_collection(
        name=COLLECTION_NAME,
        metadata={"hnsw:space": "cosine"},
    )


# ── yt-dlp helpers ────────────────────────────────────────────────────────────
def _list_channel_videos(channel_url: str, limit: int, min_views: int, log: logging.Logger) -> list[dict]:
    """Return list of {url, title, view_count} for recent channel videos."""
    try:
        import yt_dlp
    except ImportError:
        log.error("yt-dlp not installed")
        return []

    ydl_opts = {
        "extract_flat": True,
        "playlist_end": limit * 3,  # fetch extra to account for view filter
        "quiet": True,
        "no_warnings": True,
    }

    videos = []
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(channel_url, download=False)
            entries = info.get("entries", []) if info else []
            for entry in entries:
                if not entry:
                    continue
                views = entry.get("view_count") or 0
                if views < min_views:
                    continue
                url = entry.get("url") or entry.get("webpage_url", "")
                if not url.startswith("http"):
                    url = f"https://www.youtube.com/watch?v={entry.get('id', '')}"
                videos.append({
                    "url": url,
                    "title": entry.get("title", ""),
                    "view_count": views,
                })
                if len(videos) >= limit:
                    break
    except Exception as exc:
        log.error(f"Failed to list channel {channel_url}: {exc}")

    return videos


def _fetch_transcript(video_url: str, log: logging.Logger) -> tuple[str, dict]:
    """Download transcript via yt-dlp. Returns (text, metadata)."""
    try:
        import yt_dlp
    except ImportError:
        return "", {}

    ydl_opts = {
        "skip_download": True,
        "writeautomaticsub": True,
        "writesubtitles": True,
        "subtitleslangs": ["en"],
        "subtitlesformat": "vtt",
        "quiet": True,
        "no_warnings": True,
    }

    with tempfile.TemporaryDirectory() as tmpdir:
        ydl_opts["outtmpl"] = os.path.join(tmpdir, "%(id)s")
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(video_url, download=True)
        except Exception as exc:
            log.warning(f"yt-dlp failed for {video_url}: {exc}")
            return "", {}

        meta = {
            "video_title":  info.get("title", ""),
            "channel":      info.get("uploader", info.get("channel", "")),
            "upload_date":  info.get("upload_date", ""),
            "duration_secs": str(info.get("duration", 0)),
            "view_count":   str(info.get("view_count", 0)),
        }

        vtt_files = [f for f in os.listdir(tmpdir) if f.endswith(".vtt")]
        if not vtt_files:
            return "", meta

        with open(os.path.join(tmpdir, vtt_files[0]), encoding="utf-8") as f:
            raw = f.read()

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

    return " ".join(lines), meta


def _ingest_video(
    video: dict,
    weight: float,
    collection: chromadb.Collection,
    dry_run: bool,
    log: logging.Logger,
) -> int:
    url = video["url"]
    log.info(f"  → {video['title'][:70]} ({video['view_count']:,} views)")

    if _already_ingested(collection, url):
        log.info("    [SKIP] already in ChromaDB")
        return 0

    text, meta = _fetch_transcript(url, log)
    if not text:
        log.warning("    [SKIP] no transcript")
        return 0

    chunks = _chunk_text(text)
    if not chunks:
        log.warning("    [SKIP] transcript too short")
        return 0

    if dry_run:
        log.info(f"    [DRY-RUN] would ingest {len(chunks)} chunks — {meta.get('video_title')}")
        return len(chunks)

    url_hash = hashlib.md5(url.encode()).hexdigest()[:12]
    host = urlparse(url).netloc.lower().lstrip("www.")
    base_meta = {
        "source": host,
        "source_type": "youtube",
        "source_weight": weight,
        "canonical_url": url,
        **{k: v for k, v in meta.items() if v},
    }

    collection.upsert(
        documents=chunks,
        metadatas=[{**base_meta, "chunk_index": i} for i in range(len(chunks))],
        ids=[f"bulk_{url_hash}_{i}" for i in range(len(chunks))],
    )
    log.info(f"    ✓ {len(chunks)} chunks ingested")
    return len(chunks)


# ── Main ──────────────────────────────────────────────────────────────────────
def main() -> None:
    parser = argparse.ArgumentParser(description="Bulk ingest from curated automotive YouTube channels")
    parser.add_argument("--channel", choices=list(CHANNELS.keys()), help="Single channel key (default: all)")
    parser.add_argument("--limit", type=int, default=20, help="Max videos per channel (default: 20)")
    parser.add_argument("--min-views", type=int, default=5000, help="Skip videos below this view count (default: 5000)")
    parser.add_argument("--dry-run", action="store_true", help="Preview without writing to ChromaDB")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    log = logging.getLogger("bulk_ingest")

    targets = {args.channel: CHANNELS[args.channel]} if args.channel else CHANNELS
    collection = _get_collection()

    total_chunks = 0
    total_videos = 0

    for key, cfg in targets.items():
        log.info(f"\n{'='*60}")
        log.info(f"Channel: {key} | weight={cfg['weight']} | limit={args.limit} | min_views={args.min_views:,}")
        log.info(f"URL: {cfg['url']}")

        videos = _list_channel_videos(cfg["url"], args.limit, args.min_views, log)
        log.info(f"Found {len(videos)} eligible videos")

        for video in videos:
            n = _ingest_video(video, cfg["weight"], collection, args.dry_run, log)
            if n:
                total_chunks += n
                total_videos += 1

    print(f"\n{'[DRY-RUN] ' if args.dry_run else ''}Done — {total_videos} videos, {total_chunks} chunks ingested.")
    print(f"Channels processed: {', '.join(targets.keys())}")


if __name__ == "__main__":
    main()
