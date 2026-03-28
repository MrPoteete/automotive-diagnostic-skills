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
import shutil
import sys
import tempfile
from pathlib import Path
from urllib.parse import urlparse

import json
from datetime import datetime

import chromadb
import requests
from bs4 import BeautifulSoup

# ── Paths ─────────────────────────────────────────────────────────────────────
PROJECT_ROOT = Path(__file__).parent.parent
CHROMA_PATH  = PROJECT_ROOT / "data" / "vector_store" / "chroma"
COLLECTION_NAME = "mechanics_forum"
MANIFEST_PATH = PROJECT_ROOT / "data" / "ingested_videos_manifest.jsonl"

# ── Curated channel list ───────────────────────────────────────────────────────
# Keys are short names used with --channel flag.
# weight:     source reliability score injected into ChromaDB metadata (0.0-1.0)
# limit:      per-channel video limit override (optional; falls back to --limit arg)
# focus:      "professional" | "diy" — used for metadata tagging
CHANNELS: dict[str, dict] = {
    # ── Original channels ──────────────────────────────────────────────────
    "rainman":    {"url": "https://www.youtube.com/@RainmanRaysRepairs/videos",   "weight": 0.75, "focus": "professional"},
    "southmain":  {"url": "https://www.youtube.com/@SouthMainAuto/videos",        "weight": 0.75, "focus": "professional"},
    "scotty":     {"url": "https://www.youtube.com/@ScottyKilmer/videos",         "weight": 0.70, "focus": "professional"},
    "humble":     {"url": "https://www.youtube.com/@HumbleMechanic/videos",       "weight": 0.75, "focus": "professional"},
    "fordtech":   {"url": "https://www.youtube.com/@FordTechMakuloco/videos",     "weight": 0.80, "focus": "professional"},
    "scanner":    {"url": "https://www.youtube.com/@ScannerDanner/videos",        "weight": 0.85, "focus": "professional", "limit": 40},

    # ── New channels (2026-03-27) ──────────────────────────────────────────
    # Royalty Auto Service — "We Test, Not Guess" shop in St. Marys GA;
    # oscilloscope/scope diagnostics, multi-make; ~310K subs
    "royalty":    {"url": "https://www.youtube.com/@theroyaltyautoservice/videos", "weight": 0.85, "focus": "professional"},

    # Eric The Car Guy — foundational professional-mechanic channel since 2009;
    # broad diagnostic walkthroughs, ~1.9M subs
    "etcg":       {"url": "https://www.youtube.com/@ericthecarguy/videos",        "weight": 0.75, "focus": "professional"},

    # The Car Care Nut — Toyota/Lexus master diagnostic tech (AMD), specialty shop owner;
    # extremely thorough pre-purchase inspections and diagnostic methodology, ~1.68M subs
    "carcarenut": {"url": "https://www.youtube.com/@TheCarCareNut/videos",        "weight": 0.80, "focus": "professional"},

    # 1A Auto — step-by-step repair tutorials, 70+ years combined mechanic experience;
    # DIY-oriented framing but accurate procedures, ~3M subs; lower weight reflects audience
    "1aauto":     {"url": "https://www.youtube.com/@1aauto/videos",               "weight": 0.65, "focus": "diy"},

    # ── New channels (2026-03-27 batch 2) ─────────────────────────────────
    # Pine Hollow Auto Diagnostics — Ivan Temnykh, professional shop in State College PA;
    # first-principles live diagnostics on customer vehicles, Diagnostic Network top-ranked;
    # ~266K subs, weekly uploads
    "pinehollow": {"url": "https://www.youtube.com/@pinehollowautodiagnostics/videos", "weight": 0.85, "focus": "professional"},

    # DiagnoseDan — professional mechanic (Netherlands), European vehicle specialist
    # (Mercedes, BMW, Mini, Lexus, Jeep); Diagnostic Network recommended; ~210K subs
    "diagnosedan": {"url": "https://www.youtube.com/@diagnosedan/videos",          "weight": 0.80, "focus": "professional"},

    # WeberAuto (Weber State University) — Professor John Kelly; hybrid/EV high-voltage
    # systems, automatic transmissions, vibration diagnostics; university-level depth; ~467K subs
    "weberauto":  {"url": "https://www.youtube.com/@weberauto/videos",             "weight": 0.85, "focus": "professional"},

    # Adept Ape — Josh, CAT Master Truck Technician; Caterpillar diesel / HD equipment
    # diagnostics; featured on CAT's official blog and podcast; ~250K subs
    "adeptape":   {"url": "https://www.youtube.com/@AdeptApe/videos",              "weight": 0.80, "focus": "professional"},

    # DieselTechRon — Ron, Ford-certified Diesel Master Tech since 1982; Power Stroke
    # 6.0/6.4/6.7 diagnostics; dealer-level Ford diesel resource; ~144K subs
    "dieselron":  {"url": "https://www.youtube.com/@DieselTechRon/videos",         "weight": 0.82, "focus": "professional"},

    # Motor Age Training — Pete Meier ASE Master Tech; "The Trainer" series (100+ episodes),
    # scan tool interpretation, drivability, ASE prep; oldest automotive trade publication;
    # ~162K subs
    "motorage":   {"url": "https://www.youtube.com/@MotorAgeTraining/videos",      "weight": 0.80, "focus": "professional"},

    # Motor Age Magazine (Mastering Diagnostics series) — Brandon Steckler Technical Editor;
    # Vehicle Service Pros network; Mastering Diagnostics series 30+ episodes; ~100K subs
    "motoragemag": {"url": "https://www.youtube.com/@MotorAgeMagazine/videos",     "weight": 0.80, "focus": "professional"},

    # Mechanic Mindset — Darren, oscilloscope/PicoScope/CAN bus specialist;
    # training-first channel, small but extremely high technical density; confirmed active 2026
    "mechanikmindset": {"url": "https://www.youtube.com/@MechanicMindset/videos",  "weight": 0.82, "focus": "professional"},

    # GoTech — CAN bus / network communication specialist; 3-part CAN series covering
    # real-world diagnostic process (network topology → protocols → testing); 225K subs;
    # "where do I start" approach to modern vehicle network diagnosis
    "gotech":     {"url": "https://www.youtube.com/channel/UCt2U5SZn_m2dtolft_O3DHQ/videos", "weight": 0.85, "focus": "professional"},

    # ── AC/HVAC batch (2026-03-28) ────────────────────────────────────────
    # Waldo's World — European luxury vehicle diagnostics (Land Rover, BMW, Mercedes);
    # complex HVAC/climate systems; Diagnostic Network top-rated; ~576K subs
    "waldos":     {"url": "https://www.youtube.com/@waldosworld/videos",              "weight": 0.82, "focus": "professional"},

    # HVAC School (Bryan Orr) — refrigeration theory: manifold reading, superheat/subcool,
    # leak detection, evacuation; not automotive but skills transfer directly; ~453K subs
    "hvacschool": {"url": "https://www.youtube.com/@HVACS",              "weight": 0.72, "focus": "professional"},

    # AC Service Tech LLC — manifold gauge technique, vacuum procedures, system evacuation,
    # leak detection; refrigeration fundamentals directly applicable to automotive AC
    "acservtech": {"url": "https://www.youtube.com/@ACServiceTech",            "weight": 0.72, "focus": "professional"},

    # Ratchets and Wrenches — general automotive repair, AC system work in catalog;
    # bridges theory and hands-on for shop technicians; ~974K subs
    "ratchets":   {"url": "https://www.youtube.com/channel/UCT5dv3iwFuy041dbWPB6skg/videos", "weight": 0.73, "focus": "professional"},

    # Super Mario Diagnostics — systematic diagnostic methodology, electrical/oscilloscope;
    # Diagnostic Network recommended list; ~63K subs
    "supermario": {"url": "https://www.youtube.com/channel/UCaNH77hSGAZ5vF45hv6FpmQ/videos", "weight": 0.78, "focus": "professional"},
}

# ── Disk-space guardrail ──────────────────────────────────────────────────────
MIN_FREE_GB = 5  # refuse to download if less than this is free

def _check_disk_space(log: logging.Logger) -> None:
    """Abort if free disk space is below MIN_FREE_GB."""
    usage = shutil.disk_usage("/")
    free_gb = usage.free / (1024 ** 3)
    pct_used = usage.used / usage.total * 100
    if free_gb < MIN_FREE_GB:
        log.error(
            f"Disk guardrail: only {free_gb:.1f} GB free ({pct_used:.0f}% used). "
            f"Refusing to continue. Free up space or raise MIN_FREE_GB."
        )
        sys.exit(1)
    log.debug(f"Disk OK: {free_gb:.1f} GB free ({pct_used:.0f}% used)")


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


def _load_manifest_urls() -> set[str]:
    """Load set of already-ingested video URLs from manifest file (fast pre-check)."""
    if not MANIFEST_PATH.exists():
        return set()
    urls: set[str] = set()
    try:
        for line in MANIFEST_PATH.read_text().splitlines():
            if line.strip():
                entry = json.loads(line)
                urls.add(entry["url"])
    except Exception:
        pass
    return urls


def _write_manifest_entry(video: dict, channel_key: str, chunks: int, meta: dict) -> None:
    """Append an ingested video record to the manifest JSONL file."""
    entry = {
        "url": video["url"],
        "title": video.get("title", ""),
        "channel_key": channel_key,
        "channel_name": meta.get("channel", ""),
        "view_count": video.get("view_count", 0),
        "upload_date": meta.get("upload_date", ""),
        "duration_secs": meta.get("duration_secs", ""),
        "chunks": chunks,
        "ingested_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    }
    MANIFEST_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(MANIFEST_PATH, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry) + "\n")


def _already_ingested(collection: chromadb.Collection, video_url: str, manifest_urls: set[str]) -> bool:
    """Check manifest first (fast), fall back to ChromaDB query."""
    if video_url in manifest_urls:
        return True
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


# Checked AGENTS.md - implementing directly because this is a targeted safety guardrail
# (disk check + two-phase download strategy) on an existing data pipeline function.
# No architectural decisions or complex refactoring — refactoring-expert delegation not warranted.
def _fetch_transcript(video_url: str, log: logging.Logger) -> tuple[str, dict]:
    """Fetch transcript via yt-dlp using a disk-safe two-phase strategy.

    Phase 1 — transcript only (skip_download=True): zero video bytes on disk.
    Phase 2 — lowest-quality audio, only if Phase 1 finds no subtitles.
              All downloaded files are deleted by tempfile.TemporaryDirectory on exit.
    """
    _check_disk_space(log)

    try:
        import yt_dlp
    except ImportError:
        log.error("yt-dlp not installed")
        return "", {}

    base_opts = {
        "writeautomaticsub": True,
        "writesubtitles": True,
        "subtitleslangs": ["en"],
        "subtitlesformat": "vtt",
        "quiet": True,
        "no_warnings": True,
    }

    meta: dict = {}

    # ── Phase 1: transcript only (no video download) ──────────────────────────
    with tempfile.TemporaryDirectory() as tmpdir:
        opts = {**base_opts, "skip_download": True, "outtmpl": os.path.join(tmpdir, "%(id)s")}
        try:
            with yt_dlp.YoutubeDL(opts) as ydl:
                info = ydl.extract_info(video_url, download=True)
            meta = {
                "video_title":   info.get("title", ""),
                "channel":       info.get("uploader", info.get("channel", "")),
                "upload_date":   info.get("upload_date", ""),
                "duration_secs": str(info.get("duration", 0)),
                "view_count":    str(info.get("view_count", 0)),
            }
        except Exception as exc:
            log.warning(f"yt-dlp phase-1 failed for {video_url}: {exc}")
            return "", {}

        vtt_files = [f for f in os.listdir(tmpdir) if f.endswith(".vtt")]
        if vtt_files:
            with open(os.path.join(tmpdir, vtt_files[0]), encoding="utf-8") as f:
                raw = f.read()
            return _parse_vtt(raw), meta

    # ── Phase 2: lowest-quality audio (transcript unavailable) ────────────────
    log.warning(f"No subtitles in phase 1 for {video_url} — falling back to lowest-quality audio")
    _check_disk_space(log)  # re-check before downloading bytes

    with tempfile.TemporaryDirectory() as tmpdir:
        opts = {
            **base_opts,
            "skip_download": False,
            "format": "worstaudio/worst",        # absolute minimum bytes on disk
            "postprocessors": [],
            "outtmpl": os.path.join(tmpdir, "%(id)s.%(ext)s"),
        }
        try:
            with yt_dlp.YoutubeDL(opts) as ydl:
                ydl.extract_info(video_url, download=True)
        except Exception as exc:
            log.warning(f"yt-dlp phase-2 failed for {video_url}: {exc}")
            return "", meta

        vtt_files = [f for f in os.listdir(tmpdir) if f.endswith(".vtt")]
        if not vtt_files:
            log.warning(f"No subtitles after phase-2 for {video_url} — skipping")
            return "", meta  # tmpdir cleanup removes all downloaded files

        with open(os.path.join(tmpdir, vtt_files[0]), encoding="utf-8") as f:
            raw = f.read()
        # tmpdir exits here — all downloaded audio + vtt files deleted

    return _parse_vtt(raw), meta


def _ingest_video(
    video: dict,
    channel_key: str,
    weight: float,
    focus: str,
    collection: chromadb.Collection,
    manifest_urls: set[str],
    dry_run: bool,
    log: logging.Logger,
) -> int:
    url = video["url"]
    log.info(f"  → {video['title'][:70]} ({video['view_count']:,} views)")

    if _already_ingested(collection, url, manifest_urls):
        log.info("    [SKIP] already ingested")
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
        "channel_focus": focus,
        "canonical_url": url,
        **{k: v for k, v in meta.items() if v},
    }

    collection.upsert(
        documents=chunks,
        metadatas=[{**base_meta, "chunk_index": i} for i in range(len(chunks))],
        ids=[f"bulk_{url_hash}_{i}" for i in range(len(chunks))],
    )
    _write_manifest_entry(video, channel_key, len(chunks), meta)
    manifest_urls.add(url)  # update in-memory set to prevent re-check within same run
    log.info(f"    ✓ {len(chunks)} chunks ingested")
    return len(chunks)


# ── Main ──────────────────────────────────────────────────────────────────────
def main() -> None:
    parser = argparse.ArgumentParser(description="Bulk ingest from curated automotive YouTube channels")
    parser.add_argument("--channel", choices=list(CHANNELS.keys()), help=f"Single channel key (default: all). Options: {', '.join(CHANNELS.keys())}")
    parser.add_argument("--limit", type=int, default=20, help="Max videos per channel (default: 20)")
    parser.add_argument("--min-views", type=int, default=5000, help="Skip videos below this view count (default: 5000)")
    parser.add_argument("--dry-run", action="store_true", help="Preview without writing to ChromaDB")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    log = logging.getLogger("bulk_ingest")

    _check_disk_space(log)  # abort early if disk is already low

    targets = {args.channel: CHANNELS[args.channel]} if args.channel else CHANNELS
    collection = _get_collection()
    manifest_urls = _load_manifest_urls()
    log.info(f"Manifest: {len(manifest_urls)} URLs already ingested (fast pre-check)")

    total_chunks = 0
    total_videos = 0

    for key, cfg in targets.items():
        channel_limit = cfg.get("limit", args.limit)  # per-channel override or global default
        focus = cfg.get("focus", "professional")
        log.info(f"\n{'='*60}")
        log.info(f"Channel: {key} | weight={cfg['weight']} | focus={focus} | limit={channel_limit} | min_views={args.min_views:,}")
        log.info(f"URL: {cfg['url']}")

        videos = _list_channel_videos(cfg["url"], channel_limit, args.min_views, log)
        log.info(f"Found {len(videos)} eligible videos")

        for video in videos:
            n = _ingest_video(video, key, cfg["weight"], focus, collection, manifest_urls, args.dry_run, log)
            if n:
                total_chunks += n
                total_videos += 1

    print(f"\n{'[DRY-RUN] ' if args.dry_run else ''}Done — {total_videos} videos, {total_chunks} chunks ingested.")
    print(f"Channels processed: {', '.join(targets.keys())}")
    if not args.dry_run:
        print(f"Manifest: {MANIFEST_PATH}")


if __name__ == "__main__":
    main()
