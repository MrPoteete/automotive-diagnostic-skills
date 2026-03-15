#!/usr/bin/env python3
# Checked AGENTS.md - implementing directly because this is a standalone data import CLI
# with no auth/sensitive data (read-only file I/O + ChromaDB upsert).
"""
Ingest Reddit JSONL data into ChromaDB mechanics_forum collection.

Input files (relative to project root):
  data/knowledge_base/reddit/r_MechanicAdvice_posts.jsonl
  data/knowledge_base/reddit/r_MechanicAdvice_comments.jsonl
  data/knowledge_base/reddit/r_AskMechanics_posts.jsonl
  data/knowledge_base/reddit/r_AskMechanics_comments.jsonl

Strategy:
  0. Pre-scan posts file to collect qualifying post IDs (reduces comment index memory).
  1. Stream comments file into memory as a filtered index (post_id → [comment, ...]),
     restricted to qualifying post IDs only.
  2. Stream posts file, assemble post+comments documents, batch-upsert to ChromaDB.
  3. Checkpoint file tracks byte offset after each batch — resume on restart.

Run:
  .venv/bin/python3 scripts/import_reddit.py
  .venv/bin/python3 scripts/import_reddit.py --posts data/knowledge_base/reddit/r_AskMechanics_posts.jsonl \\
      --comments data/knowledge_base/reddit/r_AskMechanics_comments.jsonl
  .venv/bin/python3 scripts/import_reddit.py --dry-run
  .venv/bin/python3 scripts/import_reddit.py --limit 1000
  .venv/bin/python3 scripts/import_reddit.py --batch-size 250
  .venv/bin/python3 scripts/import_reddit.py --resume  # continue from checkpoint
"""

from __future__ import annotations

import argparse
import hashlib
import json
import logging
import pathlib
import sys
import time
from collections import defaultdict
from pathlib import Path
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
# Logging setup — writes to both stdout and a persistent log file
# ---------------------------------------------------------------------------


def setup_logging(log_path: pathlib.Path) -> logging.Logger:
    """Configure root logger to write to stdout + a persistent log file."""
    logger = logging.getLogger("reddit_import")
    logger.setLevel(logging.DEBUG)

    fmt = logging.Formatter("%(asctime)s  %(message)s", datefmt="%Y-%m-%d %H:%M:%S")

    # Console handler
    ch = logging.StreamHandler(sys.stdout)
    ch.setFormatter(fmt)
    logger.addHandler(ch)

    # File handler — append so prior runs are preserved
    fh = logging.FileHandler(log_path, encoding="utf-8")
    fh.setFormatter(fmt)
    logger.addHandler(fh)

    return logger


# ---------------------------------------------------------------------------
# Automotive tech-term filter (pre-compiled as a single alternation regex)
# ---------------------------------------------------------------------------

import re  # noqa: E402 (after stdlib imports)

_TECH_TERMS = [
    # Parts
    "sensor", "solenoid", "relay", "fuse", "connector", "bearing", "gasket",
    "pump", "injector", "coil", "alternator", "starter", "caliper", "rotor",
    "strut", "actuator", "harness", "seal", "valve", "thermostat", "catalytic",
    "oxygen", "throttle", "camshaft", "crankshaft", "timing", "serpentine",
    # Actions
    "replace", "torque", "bleed", "flush", "ohm", "voltage", "resistance",
    "measure", "inspect", "disconnect", "diagnose", "scan", "test",
    # Diagnostic codes / ECUs
    "OBD", "DTC", "misfire", "lean", "rich", "vacuum", "pressure", "fault",
    "code", "ECU", "PCM", "BCM", "TCM", "MAF", "MAP", "TPS", "IAT",
    # Systems
    "transmission", "differential", "coolant", "cylinder", "ABS", "brake",
    "suspension", "steering", "ignition", "exhaust", "fuel", "oil",
]

_TECH_TERMS_SORTED = sorted(set(_TECH_TERMS), key=len, reverse=True)
_TECH_RE = re.compile(
    r"\b(?:" + "|".join(re.escape(t) for t in _TECH_TERMS_SORTED) + r")\b",
    re.IGNORECASE,
)

# ---------------------------------------------------------------------------
# Reject patterns for comments (substring, case-insensitive)
# ---------------------------------------------------------------------------

_REJECT_PATTERNS: list[str] = [
    "take it to a", "take it to your", "go to a dealer", "go to the dealer",
    "can't help", "cannot help", "no idea", "same here", "same issue",
    "sounds expensive", "good luck with", "yikes", "idk man",
]

_REJECT_RE = re.compile(
    "|".join(re.escape(p) for p in _REJECT_PATTERNS),
    re.IGNORECASE,
)

_YEAR_RE = re.compile(r"\b(19|20)\d{2}\b")
_BOT_AUTHORS: frozenset[str] = frozenset({"automoderator", "[deleted]", "[removed]"})
_EMPTY_SELFTEXT: frozenset[str] = frozenset({"", "[deleted]", "[removed]"})

# ---------------------------------------------------------------------------
# Filtering helpers
# ---------------------------------------------------------------------------


def _sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def tech_score(body: str) -> int:
    return len(_TECH_RE.findall(body))


def _comment_passes(comment: dict[str, Any]) -> bool:
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
# Phase 0: Pre-scan posts to collect qualifying post IDs
# ---------------------------------------------------------------------------


def collect_qualifying_post_ids(
    posts_path: pathlib.Path,
    log: logging.Logger,
) -> set[str]:
    """
    Quick first pass of the posts file: collect IDs of posts that pass quality gates.
    This set is used to restrict the comment index to only relevant entries,
    dramatically reducing memory for large comments files.
    """
    qualifying_ids: set[str] = set()
    lines_seen = 0
    malformed = 0

    log.info(f"Phase 0: Pre-scanning {posts_path.name} for qualifying post IDs …")
    t0 = time.monotonic()

    with posts_path.open(encoding="utf-8", errors="replace") as fh:
        for raw_line in fh:
            raw_line = raw_line.strip()
            if not raw_line:
                continue
            lines_seen += 1
            try:
                post = json.loads(raw_line)
            except json.JSONDecodeError:
                malformed += 1
                continue
            if _post_passes(post):
                post_id: str = post.get("id") or ""
                if post_id:
                    qualifying_ids.add(post_id)

    elapsed = time.monotonic() - t0
    log.info(
        f"Phase 0 done: {lines_seen:,} posts scanned | "
        f"{len(qualifying_ids):,} qualifying IDs | "
        f"{malformed:,} malformed | {elapsed:.1f}s"
    )
    return qualifying_ids


# ---------------------------------------------------------------------------
# Phase 1: Comment index builder (restricted to qualifying post IDs)
# ---------------------------------------------------------------------------


def build_comment_index(
    path: pathlib.Path,
    qualifying_post_ids: set[str],
    log: logging.Logger,
) -> dict[str, list[dict[str, Any]]]:
    """
    Stream the comments JSONL and build a filtered in-memory index.
    Only keeps comments for posts in qualifying_post_ids — massively reduces
    memory usage for large comments files (e.g. 4.3GB r_AskMechanics_comments.jsonl).
    """
    index: dict[str, list[dict[str, Any]]] = defaultdict(list)
    lines_seen = 0
    comments_kept = 0
    skipped_no_post_match = 0
    malformed = 0

    log.info(f"Phase 1: Building comment index from {path.name} …")
    log.info(f"  Filtering to {len(qualifying_post_ids):,} qualifying post IDs only.")
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

            # Check post ID first (cheap) before quality filter (more expensive)
            link_id: str = comment.get("link_id") or ""
            if not link_id.startswith("t3_"):
                continue
            post_id = link_id[3:]

            if post_id not in qualifying_post_ids:
                skipped_no_post_match += 1
                continue

            if not _comment_passes(comment):
                continue

            index[post_id].append({
                "body": comment["body"],
                "score": int(comment.get("score", 0)),
            })
            comments_kept += 1

            if lines_seen % 500_000 == 0:
                elapsed = time.monotonic() - t0
                log.info(
                    f"  Comments: {lines_seen:,} seen | {comments_kept:,} kept"
                    f" | {skipped_no_post_match:,} skipped (no post match)"
                    f" | {malformed:,} malformed | {elapsed:.1f}s"
                )

    elapsed = time.monotonic() - t0
    log.info(
        f"Phase 1 done: {lines_seen:,} lines | {comments_kept:,} kept"
        f" | {skipped_no_post_match:,} skipped (no post match)"
        f" | {malformed:,} malformed | {len(index):,} posts have comments"
        f" | {elapsed:.1f}s"
    )
    return dict(index)


# ---------------------------------------------------------------------------
# Checkpoint helpers
# ---------------------------------------------------------------------------


def _checkpoint_path(posts_path: pathlib.Path) -> pathlib.Path:
    """Return the checkpoint file path for a given posts file."""
    return posts_path.parent / f".{posts_path.stem}.checkpoint.json"


def load_checkpoint(posts_path: pathlib.Path, log: logging.Logger) -> dict[str, Any]:
    """Load checkpoint if it exists, else return empty state."""
    cp_path = _checkpoint_path(posts_path)
    if cp_path.exists():
        try:
            state = json.loads(cp_path.read_text())
            log.info(
                f"Checkpoint found: {cp_path.name} — "
                f"posts_seen={state.get('posts_seen', 0):,}, "
                f"docs_upserted={state.get('docs_upserted', 0):,}, "
                f"file_offset={state.get('file_offset', 0):,}"
            )
            return state
        except Exception as exc:
            log.warning(f"Could not load checkpoint ({exc}) — starting fresh.")
    return {}


def save_checkpoint(
    posts_path: pathlib.Path,
    posts_seen: int,
    docs_upserted: int,
    file_offset: int,
    seen_title_hashes: set[str],
) -> None:
    """Persist checkpoint state to disk."""
    cp_path = _checkpoint_path(posts_path)
    state = {
        "posts_seen": posts_seen,
        "docs_upserted": docs_upserted,
        "file_offset": file_offset,
        "seen_title_hashes": list(seen_title_hashes),
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S"),
    }
    cp_path.write_text(json.dumps(state))


def clear_checkpoint(posts_path: pathlib.Path, log: logging.Logger) -> None:
    """Remove checkpoint file after successful completion."""
    cp_path = _checkpoint_path(posts_path)
    if cp_path.exists():
        cp_path.unlink()
        log.info(f"Checkpoint cleared: {cp_path.name}")


# ---------------------------------------------------------------------------
# Document assembly
# ---------------------------------------------------------------------------


def _assemble_document(
    post: dict[str, Any],
    top_comments: list[dict[str, Any]],
) -> str:
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


def _get_collection(dry_run: bool, log: logging.Logger) -> Any:
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

    doc_count = 0
    for attempt in range(10):
        try:
            doc_count = collection.count()
            break
        except Exception:
            if attempt == 9:
                log.warning("ChromaDB HNSW index still compacting — proceeding without count.")
            else:
                log.info(f"  ChromaDB index compacting, retrying in 30s (attempt {attempt + 1}/10)...")
                time.sleep(30)

    log.info(
        f"ChromaDB ready [{action}]. Collection '{COLLECTION_NAME}': "
        f"{doc_count:,} docs before import."
    )
    return collection


def _upsert_batch(
    collection: Any,
    batch_docs: list[str],
    batch_meta: list[dict[str, Any]],
    batch_ids: list[str],
    dry_run: bool,
    total_upserted: int,
    log: logging.Logger,
) -> int:
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
            log.warning(f"Batch upsert error: {exc}")
            return total_upserted
    total_upserted += len(batch_ids)
    log.info(
        f"  Batch upserted: {len(batch_ids)} docs | "
        f"running total: {total_upserted:,}"
        + (" [DRY-RUN]" if dry_run else "")
    )
    return total_upserted


# ---------------------------------------------------------------------------
# Phase 2: Main ingestion loop (with checkpoint/resume)
# ---------------------------------------------------------------------------


def ingest(
    posts_path: pathlib.Path,
    comment_index: dict[str, list[dict[str, Any]]],
    collection: Any,
    log: logging.Logger,
    *,
    dry_run: bool,
    limit: int | None,
    batch_size: int,
    resume: bool,
) -> None:
    """
    Stream posts file, assemble documents, and upsert to ChromaDB.
    Checkpoints byte offset after each batch so the run can be resumed.
    """
    # Load checkpoint if resuming
    checkpoint_state: dict[str, Any] = {}
    if resume:
        checkpoint_state = load_checkpoint(posts_path, log)

    resume_offset: int = checkpoint_state.get("file_offset", 0)
    posts_seen: int = checkpoint_state.get("posts_seen", 0)
    docs_upserted: int = checkpoint_state.get("docs_upserted", 0)
    seen_title_hashes: set[str] = set(checkpoint_state.get("seen_title_hashes", []))

    if resume_offset > 0:
        log.info(
            f"Resuming from byte offset {resume_offset:,} "
            f"(posts_seen={posts_seen:,}, docs_upserted={docs_upserted:,})"
        )

    docs_skipped = 0
    malformed = 0

    batch_docs: list[str] = []
    batch_meta: list[dict[str, Any]] = []
    batch_ids: list[str] = []

    log.info(f"\nPhase 2: Streaming posts from {posts_path.name} …")
    t0 = time.monotonic()

    with posts_path.open(encoding="utf-8", errors="replace") as fh:
        if resume_offset > 0:
            fh.seek(resume_offset)

        while True:
            raw_line = fh.readline()
            if not raw_line:
                break  # EOF

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

            if posts_seen % 10_000 == 0:
                elapsed = time.monotonic() - t0
                log.info(
                    f"  Posts: {posts_seen:,} seen | {docs_upserted:,} upserted"
                    f" | {docs_skipped:,} skipped | {elapsed:.1f}s elapsed"
                )

            if not _post_passes(post):
                docs_skipped += 1
                continue

            title: str = post.get("title") or ""
            title_hash = _sha256(title.lower().strip())
            if title_hash in seen_title_hashes:
                docs_skipped += 1
                continue
            seen_title_hashes.add(title_hash)

            post_id: str = post.get("id") or ""
            raw_comments = comment_index.get(post_id, [])
            top_comments = sorted(raw_comments, key=lambda c: c["score"], reverse=True)[:3]

            final_text = _assemble_document(post, top_comments)
            if len(final_text) < 200:
                docs_skipped += 1
                continue

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

            if len(batch_ids) >= batch_size:
                docs_upserted = _upsert_batch(
                    collection, batch_docs, batch_meta, batch_ids,
                    dry_run, docs_upserted, log
                )
                batch_docs.clear()
                batch_meta.clear()
                batch_ids.clear()

                # Checkpoint after every successful batch flush
                if not dry_run:
                    save_checkpoint(
                        posts_path,
                        posts_seen=posts_seen,
                        docs_upserted=docs_upserted,
                        file_offset=fh.tell(),
                        seen_title_hashes=seen_title_hashes,
                    )

    # Final partial batch
    if batch_ids:
        docs_upserted = _upsert_batch(
            collection, batch_docs, batch_meta, batch_ids,
            dry_run, docs_upserted, log
        )
        if not dry_run:
            save_checkpoint(
                posts_path,
                posts_seen=posts_seen,
                docs_upserted=docs_upserted,
                file_offset=0,  # 0 = completed
                seen_title_hashes=seen_title_hashes,
            )

    elapsed = time.monotonic() - t0
    log.info("\n--- Import Complete ---")
    log.info(f"  Posts seen:      {posts_seen:,}")
    log.info(f"  Docs upserted:   {docs_upserted:,}" + (" [DRY-RUN]" if dry_run else ""))
    log.info(f"  Docs skipped:    {docs_skipped:,}")
    log.info(f"  Malformed lines: {malformed:,}")
    log.info(f"  Elapsed:         {elapsed:.1f}s")
    if not dry_run:
        try:
            log.info(f"  Collection total after import: {collection.count():,} docs")
        except Exception:
            pass

    # Clear checkpoint on successful completion
    if not dry_run:
        clear_checkpoint(posts_path, log)


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Ingest Reddit JSONL data into ChromaDB.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
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
    parser.add_argument(
        "--resume",
        action="store_true",
        help="Resume from checkpoint if one exists for this posts file.",
    )
    parser.add_argument(
        "--log-file",
        type=Path,
        default=None,
        metavar="PATH",
        help="Path to persistent log file. Defaults to /tmp/reddit_import_<subreddit>.log",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)

    posts_file: Path = args.posts
    comments_file: Path = args.comments

    # Derive log file path
    subreddit_slug = posts_file.stem.replace("_posts", "")
    log_path: Path = args.log_file or Path(f"/tmp/reddit_import_{subreddit_slug}.log")

    log = setup_logging(log_path)

    # Validate inputs
    for path, label in [(posts_file, "posts"), (comments_file, "comments")]:
        if not path.exists():
            log.error(f"ERROR: {label} file not found: {path}")
            return 1
        if path.stat().st_size == 0:
            log.error(f"ERROR: {label} file is empty: {path}")
            return 1

    if args.batch_size < 1:
        log.error("ERROR: --batch-size must be >= 1")
        return 1

    subreddit_label = posts_file.stem.replace("_posts", "").replace("r_", "r/")

    log.info("=" * 60)
    log.info(f"Reddit {subreddit_label} → ChromaDB importer")
    log.info(f"Log file: {log_path}")
    log.info("=" * 60)
    if args.dry_run:
        log.info("MODE: DRY-RUN (no writes to ChromaDB)")
    if args.limit:
        log.info(f"LIMIT: {args.limit:,} posts")
    if args.resume:
        log.info("RESUME: will continue from checkpoint if found")
    log.info(f"Batch size: {args.batch_size}")

    # Phase 0: Pre-scan posts to collect qualifying IDs (reduces comment index memory)
    qualifying_ids = collect_qualifying_post_ids(posts_file, log)

    # Phase 1: Build comment index (restricted to qualifying post IDs)
    comment_index = build_comment_index(comments_file, qualifying_ids, log)

    # Phase 2: Open ChromaDB
    collection = _get_collection(dry_run=args.dry_run, log=log)

    # Phase 3: Ingest posts
    ingest(
        posts_path=posts_file,
        comment_index=comment_index,
        collection=collection,
        log=log,
        dry_run=args.dry_run,
        limit=args.limit,
        batch_size=args.batch_size,
        resume=args.resume,
    )

    return 0


if __name__ == "__main__":
    sys.exit(main())
