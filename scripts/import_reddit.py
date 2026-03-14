#!/usr/bin/env python3
# Checked AGENTS.md - implementing directly because this is a standalone data import CLI
# with no auth/sensitive data (read-only file I/O + ChromaDB upsert).
"""
Ingest Reddit r/MechanicAdvice JSONL data into ChromaDB mechanics_forum collection.

Input files (relative to project root):
  data/knowledge_base/reddit/r_MechanicAdvice_posts.jsonl
  data/knowledge_base/reddit/r_MechanicAdvice_comments.jsonl

Strategy:
  1. Stream comments file into memory as a filtered index (post_id → [comment, ...]).
  2. Stream posts file, assemble post+comments documents, batch-upsert to ChromaDB.

Run:
  .venv/bin/python3 scripts/import_reddit.py
  .venv/bin/python3 scripts/import_reddit.py --dry-run
  .venv/bin/python3 scripts/import_reddit.py --limit 1000
  .venv/bin/python3 scripts/import_reddit.py --batch-size 250
"""

from __future__ import annotations

import argparse
import hashlib
import json
import pathlib
from pathlib import Path
import re
import sys
import time
from collections import defaultdict
from typing import Any

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

PROJECT_ROOT = pathlib.Path(__file__).resolve().parent.parent
POSTS_FILE = PROJECT_ROOT / "data" / "knowledge_base" / "reddit" / "r_MechanicAdvice_posts.jsonl"
COMMENTS_FILE = (
    PROJECT_ROOT / "data" / "knowledge_base" / "reddit" / "r_MechanicAdvice_comments.jsonl"
)
CHROMA_PATH = PROJECT_ROOT / "data" / "vector_store" / "chroma"
COLLECTION_NAME = "mechanics_forum"

# ---------------------------------------------------------------------------
# Automotive tech-term filter (pre-compiled as a single alternation regex)
# ---------------------------------------------------------------------------

_TECH_TERMS = [
    # Parts
    "sensor",
    "solenoid",
    "relay",
    "fuse",
    "connector",
    "bearing",
    "gasket",
    "pump",
    "injector",
    "coil",
    "alternator",
    "starter",
    "caliper",
    "rotor",
    "strut",
    "actuator",
    "harness",
    "seal",
    "valve",
    "thermostat",
    "catalytic",
    "oxygen",
    "throttle",
    "camshaft",
    "crankshaft",
    "timing",
    "serpentine",
    # Actions
    "replace",
    "torque",
    "bleed",
    "flush",
    "ohm",
    "voltage",
    "resistance",
    "measure",
    "inspect",
    "disconnect",
    "diagnose",
    "scan",
    "test",
    # Diagnostic codes / ECUs
    "OBD",
    "DTC",
    "misfire",
    "lean",
    "rich",
    "vacuum",
    "pressure",
    "fault",
    "code",
    "ECU",
    "PCM",
    "BCM",
    "TCM",
    "MAF",
    "MAP",
    "TPS",
    "IAT",
    # Systems
    "transmission",
    "differential",
    "coolant",
    "cylinder",
    "ABS",
    "brake",
    "suspension",
    "steering",
    "ignition",
    "exhaust",
    "fuel",
    "oil",
]

# Sorted longest-first to avoid shorter alternations shadowing longer ones
_TECH_TERMS_SORTED = sorted(set(_TECH_TERMS), key=len, reverse=True)
_TECH_RE = re.compile(
    r"\b(?:" + "|".join(re.escape(t) for t in _TECH_TERMS_SORTED) + r")\b",
    re.IGNORECASE,
)

# ---------------------------------------------------------------------------
# Reject patterns for comments (substring, case-insensitive)
# ---------------------------------------------------------------------------

_REJECT_PATTERNS: list[str] = [
    "take it to a",
    "take it to your",
    "go to a dealer",
    "go to the dealer",
    "can't help",
    "cannot help",
    "no idea",
    "same here",
    "same issue",
    "sounds expensive",
    "good luck with",
    "yikes",
    "idk man",
]

# Pre-compile reject patterns as a single regex for efficiency
_REJECT_RE = re.compile(
    "|".join(re.escape(p) for p in _REJECT_PATTERNS),
    re.IGNORECASE,
)

# Year pattern for post title vehicle context detection
_YEAR_RE = re.compile(r"\b(19|20)\d{2}\b")

# Bot / mod author names to skip
_BOT_AUTHORS: frozenset[str] = frozenset({"automoderator", "[deleted]", "[removed]"})

# Selftext values that indicate deleted / empty posts
_EMPTY_SELFTEXT: frozenset[str] = frozenset({"", "[deleted]", "[removed]"})

# ---------------------------------------------------------------------------
# Filtering helpers
# ---------------------------------------------------------------------------


def _sha256(text: str) -> str:
    """Return hex SHA-256 of text (for dedup fingerprinting)."""
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def tech_score(body: str) -> int:
    """Count distinct automotive tech-term matches in body (word-boundary, case-insensitive)."""
    return len(_TECH_RE.findall(body))


def _comment_passes(comment: dict[str, Any]) -> bool:
    """Return True if a comment satisfies all quality gates."""
    body: str = comment.get("body") or ""
    if body in _EMPTY_SELFTEXT:
        return False
    if len(body) < 80:
        return False

    score = comment.get("score")
    if score is None or int(score) < 2:
        return False

    author: str = (comment.get("author") or "").lower()
    if "bot" in author or author in _BOT_AUTHORS:
        return False

    if tech_score(body) < 1:
        return False

    if _REJECT_RE.search(body):
        return False

    return True


def _post_passes(post: dict[str, Any]) -> bool:
    """Return True if a post satisfies all quality gates (excluding dedup)."""
    selftext: str = post.get("selftext") or ""
    if selftext in _EMPTY_SELFTEXT:
        return False

    score = post.get("score")
    if score is None or int(score) < 1:
        return False

    title: str | None = post.get("title")
    if not title:
        return False

    long_enough = len(selftext) >= 100
    has_year = bool(_YEAR_RE.search(title))
    if not long_enough and not has_year:
        return False

    return True


# ---------------------------------------------------------------------------
# Comment index builder
# ---------------------------------------------------------------------------


def build_comment_index(
    path: pathlib.Path,
) -> dict[str, list[dict[str, Any]]]:
    """
    Stream the comments JSONL and build a filtered in-memory index.

    Returns:
        Mapping of post_id → list of qualifying comment dicts,
        each containing only {body, score}.
    """
    index: dict[str, list[dict[str, Any]]] = defaultdict(list)
    lines_seen = 0
    comments_kept = 0
    malformed = 0

    print(f"Building comment index from {path.name} …")
    t0 = time.monotonic()

    with path.open(encoding="utf-8", errors="replace") as fh:
        for raw_line in fh:
            lines_seen += 1
            raw_line = raw_line.strip()
            if not raw_line:
                continue

            try:
                comment = json.loads(raw_line)
            except json.JSONDecodeError:
                malformed += 1
                continue

            if not _comment_passes(comment):
                continue

            # Extract post_id from link_id (format: "t3_<post_id>")
            link_id: str = comment.get("link_id") or ""
            if not link_id.startswith("t3_"):
                continue
            post_id = link_id[3:]

            index[post_id].append({
                "body": comment["body"],
                "score": int(comment.get("score", 0)),
            })
            comments_kept += 1

            if lines_seen % 200_000 == 0:
                elapsed = time.monotonic() - t0
                print(
                    f"  Comments: {lines_seen:,} seen | {comments_kept:,} kept"
                    f" | {malformed:,} malformed | {elapsed:.1f}s elapsed"
                )

    elapsed = time.monotonic() - t0
    print(
        f"Comment index built: {lines_seen:,} lines | {comments_kept:,} kept"
        f" | {malformed:,} malformed | {len(index):,} posts have comments"
        f" | {elapsed:.1f}s"
    )
    return dict(index)


# ---------------------------------------------------------------------------
# Document assembly
# ---------------------------------------------------------------------------


def _assemble_document(
    post: dict[str, Any],
    top_comments: list[dict[str, Any]],
) -> str:
    """Build the final document string from post and its top comments."""
    title: str = post.get("title") or ""
    selftext: str = post.get("selftext") or ""

    parts = [f"[VEHICLE QUESTION] {title}", selftext]

    if top_comments:
        parts.append("[TOP ANSWERS]")
        for c in top_comments:
            body = c["body"].strip()
            parts.append(f"• {body}")

    return "\n".join(parts)


# ---------------------------------------------------------------------------
# ChromaDB helpers
# ---------------------------------------------------------------------------


def _get_collection(dry_run: bool) -> Any:
    """Initialise ChromaDB client and return the target collection."""
    try:
        import chromadb  # type: ignore[import-untyped]
    except ImportError as exc:
        raise ImportError(
            "chromadb not installed. Run: .venv/bin/pip install chromadb"
        ) from exc

    client = chromadb.PersistentClient(path=str(CHROMA_PATH))
    collection = client.get_or_create_collection(
        name=COLLECTION_NAME,
        metadata={"hnsw:space": "cosine"},
    )
    action = "DRY-RUN (no writes)" if dry_run else "WRITE"
    print(
        f"ChromaDB ready [{action}]. Collection '{COLLECTION_NAME}': "
        f"{collection.count():,} docs before import."
    )
    return collection


def _upsert_batch(
    collection: Any,
    batch_docs: list[str],
    batch_meta: list[dict[str, Any]],
    batch_ids: list[str],
    dry_run: bool,
    total_upserted: int,
) -> int:
    """Upsert one batch to ChromaDB. Returns updated total_upserted count."""
    if not batch_ids:
        return total_upserted

    if not dry_run:
        try:
            collection.upsert(
                documents=batch_docs,
                metadatas=batch_meta,
                ids=batch_ids,
            )
        except Exception as exc:
            print(f"  [WARN] Batch upsert error: {exc}")
            return total_upserted

    total_upserted += len(batch_ids)
    print(
        f"  Batch upserted: {len(batch_ids)} docs | "
        f"running total: {total_upserted:,}"
        + (" [DRY-RUN]" if dry_run else "")
    )
    return total_upserted


# ---------------------------------------------------------------------------
# Main ingestion loop
# ---------------------------------------------------------------------------


def ingest(
    posts_path: pathlib.Path,
    comment_index: dict[str, list[dict[str, Any]]],
    collection: Any,
    *,
    dry_run: bool,
    limit: int | None,
    batch_size: int,
) -> None:
    """
    Stream posts file, assemble documents, and upsert to ChromaDB.

    Args:
        posts_path: Path to the posts JSONL file.
        comment_index: Pre-built mapping of post_id → qualifying comments.
        collection: ChromaDB collection object.
        dry_run: If True, skip writes.
        limit: Stop after this many posts (None = no limit).
        batch_size: ChromaDB upsert batch size.
    """
    seen_title_hashes: set[str] = set()

    posts_seen = 0
    posts_kept = 0
    docs_upserted = 0
    docs_skipped = 0
    malformed = 0

    batch_docs: list[str] = []
    batch_meta: list[dict[str, Any]] = []
    batch_ids: list[str] = []

    print(f"\nStreaming posts from {posts_path.name} …")
    t0 = time.monotonic()

    with posts_path.open(encoding="utf-8", errors="replace") as fh:
        for raw_line in fh:
            raw_line = raw_line.strip()
            if not raw_line:
                continue

            try:
                post = json.loads(raw_line)
            except json.JSONDecodeError:
                malformed += 1
                continue

            posts_seen += 1

            if limit is not None and posts_seen > limit:
                break

            # Progress reporting every 10,000 posts
            if posts_seen % 10_000 == 0:
                elapsed = time.monotonic() - t0
                print(
                    f"  Posts: {posts_seen:,} seen | {posts_kept:,} kept"
                    f" | {docs_upserted:,} upserted | {docs_skipped:,} skipped"
                    f" | {elapsed:.1f}s elapsed"
                )

            # --- Quality gate ---
            if not _post_passes(post):
                docs_skipped += 1
                continue

            title: str = post.get("title") or ""
            title_hash = _sha256(title.lower().strip())
            if title_hash in seen_title_hashes:
                docs_skipped += 1
                continue
            seen_title_hashes.add(title_hash)

            posts_kept += 1

            # --- Assemble document ---
            post_id: str = post.get("id") or ""
            raw_comments = comment_index.get(post_id, [])
            top_comments = sorted(raw_comments, key=lambda c: c["score"], reverse=True)[:3]

            final_text = _assemble_document(post, top_comments)
            if len(final_text) < 200:
                docs_skipped += 1
                continue

            # --- Build ChromaDB record ---
            doc_id = f"reddit_{post_id}"
            metadata: dict[str, Any] = {
                "source": "reddit_mechanicadvice",
                "subreddit": post.get("subreddit") or "MechanicAdvice",
                "post_id": post_id,
                "score": int(post.get("score") or 0),
                "num_comments": int(post.get("num_comments") or 0),
                "created_utc": int(post.get("created_utc") or 0),
                "permalink": post.get("permalink") or "",
                "comment_count_used": len(top_comments),
            }

            batch_docs.append(final_text)
            batch_meta.append(metadata)
            batch_ids.append(doc_id)

            # --- Flush batch ---
            if len(batch_ids) >= batch_size:
                docs_upserted = _upsert_batch(
                    collection, batch_docs, batch_meta, batch_ids, dry_run, docs_upserted
                )
                batch_docs.clear()
                batch_meta.clear()
                batch_ids.clear()

    # Final partial batch
    if batch_ids:
        docs_upserted = _upsert_batch(
            collection, batch_docs, batch_meta, batch_ids, dry_run, docs_upserted
        )

    elapsed = time.monotonic() - t0
    print("\n--- Import Complete ---")
    print(f"  Posts seen:      {posts_seen:,}")
    print(f"  Posts kept:      {posts_kept:,}")
    print(f"  Docs upserted:   {docs_upserted:,}" + (" [DRY-RUN]" if dry_run else ""))
    print(f"  Docs skipped:    {docs_skipped:,}")
    print(f"  Malformed lines: {malformed:,}")
    print(f"  Elapsed:         {elapsed:.1f}s")
    if not dry_run:
        try:
            print(f"  Collection total after import: {collection.count():,} docs")
        except Exception:
            pass


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------


# Checked AGENTS.md - implementing directly because this is a 2-line CLI arg
# addition to an existing script; no security/arch concern, delegation overhead > task.
def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Ingest Reddit JSONL data into ChromaDB.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    # Checked AGENTS.md - implementing directly: trivial CLI arg addition, no delegation needed.
    parser.add_argument(
        "--posts",
        type=Path,
        default=POSTS_FILE,
        metavar="PATH",
        help="Path to posts JSONL file.",
    )
    parser.add_argument(
        "--comments",
        type=Path,
        default=COMMENTS_FILE,
        metavar="PATH",
        help="Path to comments JSONL file.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Filter and assemble documents but do NOT write to ChromaDB.",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        metavar="N",
        help="Stop after processing N posts (for testing).",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=500,
        metavar="N",
        help="Number of documents per ChromaDB upsert call.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)

    posts_file: Path = args.posts
    comments_file: Path = args.comments

    # Validate inputs
    for path, label in [(posts_file, "posts"), (comments_file, "comments")]:
        if not path.exists():
            print(f"ERROR: {label} file not found: {path}", file=sys.stderr)
            return 1
        if path.stat().st_size == 0:
            print(f"ERROR: {label} file is empty: {path}", file=sys.stderr)
            return 1

    if args.batch_size < 1:
        print("ERROR: --batch-size must be >= 1", file=sys.stderr)
        return 1

    subreddit_label = posts_file.stem.replace("_posts", "").replace("r_", "r/")

    print("=" * 60)
    print(f"Reddit {subreddit_label} → ChromaDB importer")
    print("=" * 60)
    if args.dry_run:
        print("MODE: DRY-RUN (no writes to ChromaDB)")
    if args.limit:
        print(f"LIMIT: {args.limit:,} posts")
    print(f"Batch size: {args.batch_size}")
    print()

    # Phase 1: Build comment index
    comment_index = build_comment_index(comments_file)

    # Phase 2: Open ChromaDB
    collection = _get_collection(dry_run=args.dry_run)

    # Phase 3: Ingest posts
    ingest(
        posts_path=posts_file,
        comment_index=comment_index,
        collection=collection,
        dry_run=args.dry_run,
        limit=args.limit,
        batch_size=args.batch_size,
    )

    return 0


if __name__ == "__main__":
    sys.exit(main())
