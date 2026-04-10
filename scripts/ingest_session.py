#!/usr/bin/env python3
# Checked AGENTS.md - implementing directly because this is a ChromaDB write
# adapter with no auth surfaces, no external API calls, and no complex logic.
# Mirrors the pattern established in bulk_ingest.py and ingest_url.py.
"""
ingest_session.py — Ingest a confirmed diagnostic session into the RAG vector store.

Confirmed real-world cases are the highest-quality diagnostic data in the system.
They are ingested at source_weight=0.95 (above YouTube at 0.75, below NHTSA at 1.0).

Usage:
    uv run python scripts/ingest_session.py data/sessions/20260408_BMW_328DXDRIVE_abc123.session
    uv run python scripts/ingest_session.py data/sessions/*.session      # batch
    uv run python scripts/ingest_session.py --all                        # ingest all sessions

Deduplication: skips sessions already in the manifest (by session_id).
"""

import argparse
import hashlib
import json
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import chromadb
import yaml

PROJECT_ROOT    = Path(__file__).resolve().parent.parent
CHROMA_PATH     = PROJECT_ROOT / "data" / "vector_store" / "chroma"
MANIFEST_PATH   = PROJECT_ROOT / "data" / "ingested_videos_manifest.jsonl"
SESSIONS_DIR    = PROJECT_ROOT / "data" / "sessions"
COLLECTION_NAME = "mechanics_forum"
SOURCE_WEIGHT   = 0.95   # higher than YouTube (0.75), below NHTSA (1.0)
CHUNK_SIZE      = 400
CHUNK_OVERLAP   = 50
FRONTMATTER_SEP = "---"


# ── File parsing ──────────────────────────────────────────────────────────────

def _read_session_file(path: Path) -> tuple[dict, list[dict]]:
    """Return (frontmatter_dict, log_entries_list)."""
    text = path.read_text(encoding="utf-8")
    if not text.startswith(FRONTMATTER_SEP):
        raise ValueError(f"No frontmatter: {path.name}")
    second = text.find(FRONTMATTER_SEP, len(FRONTMATTER_SEP))
    if second == -1:
        raise ValueError(f"Unclosed frontmatter: {path.name}")
    fm = yaml.safe_load(text[len(FRONTMATTER_SEP):second].strip()) or {}
    body = text[second + len(FRONTMATTER_SEP):].strip()
    entries = []
    for line in body.splitlines():
        line = line.strip()
        if line:
            try:
                entries.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return fm, entries


def _session_to_text(fm: dict, entries: list[dict]) -> str:
    """Convert session frontmatter + log entries to a single diagnostic narrative."""
    year  = fm.get("vehicle_year", "")
    make  = fm.get("vehicle_make", "")
    model = fm.get("vehicle_model", "")
    vin   = fm.get("vehicle_vin", "N/A")
    ro    = fm.get("repair_order", "")
    symptoms = fm.get("symptoms", "")
    phase = fm.get("phase", "")
    date  = str(fm.get("created_at", ""))[:10]

    ro_line = f"Repair Order: {ro}" if ro else ""
    header = "\n".join(filter(None, [
        f"Confirmed Diagnostic Case: {year} {make} {model}",
        f"VIN: {vin}",
        ro_line,
        f"Date: {date}",
        f"Customer Concern: {symptoms}",
        f"Status: {phase}",
        "",
    ]))

    body_parts = [header]
    for entry in entries:
        etype = entry.get("type")
        if etype == "note":
            body_parts.append(entry.get("note", ""))
        elif etype == "hypothesis":
            label  = entry.get("label", "")
            status = entry.get("status", "")
            if label:
                body_parts.append(f"Hypothesis {status}: {label}")
        elif etype == "message":
            role    = entry.get("role", "")
            content = entry.get("content", "")
            if role and content:
                body_parts.append(f"{role.upper()}: {content}")

    return "\n".join(p for p in body_parts if p.strip())


# ── Chunking ──────────────────────────────────────────────────────────────────

def _chunk_text(text: str) -> list[str]:
    words = text.split()
    chunks: list[str] = []
    start = 0
    while start < len(words):
        end = min(start + CHUNK_SIZE, len(words))
        chunks.append(" ".join(words[start:end]))
        start += CHUNK_SIZE - CHUNK_OVERLAP
    return [c for c in chunks if len(c.split()) >= 20]


# ── Deduplication ─────────────────────────────────────────────────────────────

def _load_ingested_session_ids() -> set[str]:
    """Load set of session_ids already ingested (stored in manifest as canonical_url)."""
    ids: set[str] = set()
    if not MANIFEST_PATH.exists():
        return ids
    for line in MANIFEST_PATH.read_text().splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            entry = json.loads(line)
            # Session entries stored with url = "session:<session_id>"
            url = entry.get("url", "")
            if url.startswith("session:"):
                ids.add(url[8:])
        except Exception:
            continue
    return ids


def _write_manifest_entry(session_id: str, fm: dict, chunks: int) -> None:
    entry = {
        "url":          f"session:{session_id}",
        "title":        f"Confirmed Case: {fm.get('vehicle_year','')} {fm.get('vehicle_make','')} {fm.get('vehicle_model','')}",
        "channel_key":  "confirmed_case",
        "channel_name": "Shop Diagnostic Cases",
        "view_count":   0,
        "upload_date":  str(fm.get("created_at", ""))[:10].replace("-", ""),
        "duration_secs": "",
        "chunks":       chunks,
        "ingested_at":  datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    }
    MANIFEST_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(MANIFEST_PATH, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry) + "\n")


# ── ChromaDB ──────────────────────────────────────────────────────────────────

def _get_collection() -> chromadb.Collection:
    client = chromadb.PersistentClient(path=str(CHROMA_PATH))
    return client.get_or_create_collection(
        name=COLLECTION_NAME,
        metadata={"hnsw:space": "cosine"},
    )


# ── Ingest ────────────────────────────────────────────────────────────────────

def ingest_session_file(path: Path, collection: chromadb.Collection,
                        ingested_ids: set[str], dry_run: bool = False) -> int:
    """Ingest one session file. Returns number of chunks upserted (0 if skipped)."""
    fm, entries = _read_session_file(path)
    session_id = fm.get("session_id", "")

    if not session_id:
        print(f"  SKIP {path.name} — no session_id in frontmatter")
        return 0

    if session_id in ingested_ids:
        print(f"  SKIP {path.name} — already ingested")
        return 0

    text = _session_to_text(fm, entries)
    chunks = _chunk_text(text)
    if not chunks:
        print(f"  SKIP {path.name} — too short to chunk")
        return 0

    year  = fm.get("vehicle_year", "")
    make  = fm.get("vehicle_make", "")
    model = fm.get("vehicle_model", "")
    vin   = fm.get("vehicle_vin", "")
    ro    = fm.get("repair_order", "")
    date  = str(fm.get("created_at", ""))[:10].replace("-", "")

    print(f"  {'[DRY-RUN] ' if dry_run else ''}Ingesting {path.name}")
    print(f"    Vehicle: {year} {make} {model}" + (f"  VIN: {vin}" if vin else ""))
    print(f"    {len(chunks)} chunks from {len(text.split())} words")

    if dry_run:
        return len(chunks)

    sid_hash = hashlib.md5(session_id.encode()).hexdigest()[:12]
    base_meta = {
        "source":        "confirmed_case",
        "source_type":   "session",
        "source_weight": SOURCE_WEIGHT,
        "channel_focus": "professional",
        "category":      "confirmed_case",
        "canonical_url": f"session:{session_id}",
        "session_id":    session_id,
        "vehicle_year":  str(year),
        "vehicle_make":  str(make),
        "vehicle_model": str(model),
        "upload_date":   date,
        "view_count":    "0",
    }
    if vin:
        base_meta["vehicle_vin"] = vin
    if ro:
        base_meta["repair_order"] = ro

    collection.upsert(
        documents=chunks,
        metadatas=[{**base_meta, "chunk_index": i} for i in range(len(chunks))],
        ids=[f"session_{sid_hash}_{i}" for i in range(len(chunks))],
    )
    _write_manifest_entry(session_id, fm, len(chunks))
    ingested_ids.add(session_id)
    print(f"    OK — {len(chunks)} chunks upserted at weight {SOURCE_WEIGHT}")
    return len(chunks)


# ── CLI ───────────────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Ingest confirmed diagnostic sessions into the RAG vector store"
    )
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("files", nargs="*", default=[], metavar="SESSION_FILE",
                       help="One or more .session files to ingest")
    group.add_argument("--all", action="store_true",
                       help=f"Ingest all .session files in {SESSIONS_DIR}")
    parser.add_argument("--dry-run", action="store_true",
                        help="Preview without writing to ChromaDB")
    args = parser.parse_args()

    if args.all:
        paths = sorted(SESSIONS_DIR.glob("*.session"))
        if not paths:
            print(f"No .session files found in {SESSIONS_DIR}")
            sys.exit(0)
    else:
        paths = [Path(f) for f in args.files]

    ingested_ids = _load_ingested_session_ids()
    collection = None if args.dry_run else _get_collection()

    total_chunks = 0
    ingested = 0
    skipped = 0

    print(f"{'[DRY-RUN] ' if args.dry_run else ''}Processing {len(paths)} session file(s)\n")

    for path in paths:
        if not path.exists():
            print(f"  ERROR: not found: {path}")
            continue
        n = ingest_session_file(
            path, collection, ingested_ids, dry_run=args.dry_run  # type: ignore[arg-type]
        )
        if n:
            total_chunks += n
            ingested += 1
        else:
            skipped += 1

    prefix = "[DRY-RUN] " if args.dry_run else ""
    print(f"\n{prefix}Done — {ingested} ingested ({total_chunks} chunks), {skipped} skipped")


if __name__ == "__main__":
    main()
