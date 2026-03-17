# Checked AGENTS.md - implementing directly because this is a data pipeline script
# (no security concerns, no UI, delegated boilerplate to Gemini per GEMINI_WORKFLOW.md)
"""
Parse a mechanics.StackExchange XML dump (Posts.xml) and index Q&As into ChromaDB.

The dump archive lives at:
  data/raw_imports/stackexchange_dump/mechanics.stackexchange.com.7z

Posts.xml schema:
  PostTypeId=1 → question  (has Title, Tags, AcceptedAnswerId)
  PostTypeId=2 → answer    (has ParentId)

Quality filter: keep questions with Score >= 3 OR AcceptedAnswerId set AND non-empty Title.

Chunking strategy (mirrors index_forum_data.py):
  document = "Q: {title}\\nSymptoms: {body[:400]}\\nTags: {tags}\\nA: {accepted_answer}"

Run:
  .venv/bin/python3 scripts/import_se_dump.py               # extract + parse + index
  .venv/bin/python3 scripts/import_se_dump.py --skip-extract # skip 7z extraction
  .venv/bin/python3 scripts/import_se_dump.py --dry-run      # count only, no writes
"""

import argparse
import html
import re
import time
import xml.etree.ElementTree as ET
from pathlib import Path

import chromadb  # type: ignore[import-untyped]
import py7zr  # type: ignore[import-untyped]

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

ARCHIVE_PATH = Path("data/raw_imports/stackexchange_dump/stackexchange_20250331/mechanics.stackexchange.com.7z")
EXTRACT_DIR = Path("data/raw_imports/stackexchange_dump/extracted/")
XML_PATH = EXTRACT_DIR / "Posts.xml"
CHROMA_DB_PATH = "data/vector_store/chroma/"
COLLECTION_NAME = "mechanics_forum"
BATCH_SIZE = 200
MIN_SCORE = 3
PROGRESS_INTERVAL = 5000


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def strip_html(text: str) -> str:
    """Remove HTML tags and collapse whitespace."""
    if not isinstance(text, str):
        return ""
    text = html.unescape(text)
    text = re.sub(r"<[^>]+>", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def parse_tags(raw_tags: str) -> str:
    """Convert '<ford><p0300><engine>' → 'ford, p0300, engine'."""
    if not raw_tags:
        return ""
    decoded = html.unescape(raw_tags)
    # Remove angle brackets and split on the boundary between tags
    tags = re.findall(r"<([^>]+)>", decoded)
    return ", ".join(tags)


def extract_year(creation_date: str) -> int:
    """Return 4-digit year from ISO date string, or 0 on failure."""
    try:
        return int(creation_date[:4])
    except (ValueError, TypeError, IndexError):
        return 0


def format_eta(elapsed_s: float, done: int, total: int) -> str:
    """Return human-readable ETA string."""
    if done == 0:
        return "unknown"
    rate = done / elapsed_s  # rows per second
    remaining = (total - done) / rate
    mins = int(remaining // 60)
    secs = int(remaining % 60)
    return f"{mins}m {secs}s"


# ---------------------------------------------------------------------------
# Phase 1: Extract archive
# ---------------------------------------------------------------------------


def extract_archive(archive_path: Path, extract_dir: Path) -> None:
    """Extract Posts.xml from the 7z archive."""
    if not archive_path.exists():
        raise FileNotFoundError(
            f"Archive not found: {archive_path}\n"
            "Download: https://archive.org/download/stackexchange_20251231/"
            "mechanics.stackexchange.com.7z"
        )
    extract_dir.mkdir(parents=True, exist_ok=True)
    print(f"Extracting Posts.xml from {archive_path} …")
    t0 = time.time()
    with py7zr.SevenZipFile(archive_path, mode="r") as z:
        z.extract(path=str(extract_dir), targets=["Posts.xml"])
    elapsed = time.time() - t0
    print(f"Extraction complete in {elapsed:.1f}s → {XML_PATH}")


# ---------------------------------------------------------------------------
# Phase 2 & 3: Two-pass XML parse
# ---------------------------------------------------------------------------


def _scan_answers(xml_path: Path) -> dict[int, str]:
    """
    Pass 1: Collect all answer bodies keyed by Post Id.
    Only PostTypeId=2 rows are read; everything else is ignored.
    """
    answers: dict[int, str] = {}
    print("Pass 1: collecting answer bodies …")
    for _event, elem in ET.iterparse(str(xml_path), events=("end",)):
        if elem.tag != "row":
            elem.clear()
            continue
        if elem.get("PostTypeId") != "2":
            elem.clear()
            continue
        post_id = elem.get("Id", "")
        body = strip_html(elem.get("Body", ""))
        if post_id and body:
            answers[int(post_id)] = body
        elem.clear()
    print(f"Pass 1 done — {len(answers):,} answers collected.")
    return answers


def _iter_questions(
    xml_path: Path,
    answers: dict[int, str],
) -> tuple[int, int, list[tuple[str, dict, str]]]:
    """
    Pass 2: Iterate questions, apply quality filter, build (document, metadata, id) tuples.
    Returns (total_scanned, total_skipped, rows_list).
    Rows are yielded in-order for batching by the caller via a generator but for
    simplicity we buffer them here — the XML is ~200 MB so memory is manageable.
    """
    rows: list[tuple[str, dict, str]] = []
    total_scanned = 0
    total_skipped = 0

    print("Pass 2: filtering questions and building documents …")
    t0 = time.time()

    for _event, elem in ET.iterparse(str(xml_path), events=("end",)):
        if elem.tag != "row":
            elem.clear()
            continue
        if elem.get("PostTypeId") != "1":
            elem.clear()
            continue

        total_scanned += 1

        # --- raw attribute extraction ---
        post_id_str = elem.get("Id", "")
        title_raw = html.unescape(elem.get("Title", ""))
        body_raw = elem.get("Body", "")
        tags_raw = elem.get("Tags", "")
        score_str = elem.get("Score", "0")
        accepted_id_str = elem.get("AcceptedAnswerId", "")
        creation_date = elem.get("CreationDate", "")
        elem.clear()

        # --- quality filter ---
        title = title_raw.strip()
        if not title:
            total_skipped += 1
            continue

        try:
            score = int(score_str)
        except ValueError:
            score = 0

        has_accepted = bool(accepted_id_str)
        if score < MIN_SCORE and not has_accepted:
            total_skipped += 1
            continue

        # --- build document ---
        body_clean = strip_html(body_raw)
        body_excerpt = body_clean[:400]
        tags_clean = parse_tags(tags_raw)

        accepted_answer = ""
        if has_accepted:
            try:
                accepted_answer = answers.get(int(accepted_id_str), "")
            except ValueError:
                pass

        parts = [f"Q: {title}"]
        if body_excerpt:
            parts.append(f"Symptoms: {body_excerpt}")
        if tags_clean:
            parts.append(f"Tags: {tags_clean}")
        if accepted_answer:
            parts.append(f"A: {accepted_answer}")

        document = "\n".join(parts)
        if not document.strip():
            total_skipped += 1
            continue

        # --- metadata ---
        year = extract_year(creation_date)
        try:
            post_id = int(post_id_str)
        except ValueError:
            post_id = 0

        doc_id = f"se_dump_{post_id}" if post_id else f"se_dump_noid_{total_scanned}"
        metadata: dict = {
            "source": "stackexchange_dump",
            "year": year,
            "tags": tags_clean,
            "score": score,
            "url": f"https://mechanics.stackexchange.com/q/{post_id}" if post_id else "",
            "is_answered": has_accepted,
        }

        rows.append((document, metadata, doc_id))

        # Progress
        n_indexed = len(rows)
        if total_scanned % PROGRESS_INTERVAL == 0:
            elapsed = time.time() - t0
            print(
                f"[{total_scanned:7,} scanned | {n_indexed:6,} indexed | "
                f"{total_scanned - n_indexed:6,} skipped | {elapsed:.0f}s elapsed]"
            )

    return total_scanned, total_skipped, rows


# ---------------------------------------------------------------------------
# Phase 4: Index into ChromaDB
# ---------------------------------------------------------------------------


def index_into_chroma(
    rows: list[tuple[str, dict, str]],
    collection: chromadb.Collection,
    dry_run: bool,
) -> int:
    """Upsert rows into ChromaDB in batches. Returns count of rows written."""
    if dry_run:
        print(f"DRY-RUN: would upsert {len(rows):,} documents (no writes performed).")
        return 0

    written = 0
    batch_docs: list[str] = []
    batch_metas: list[dict] = []
    batch_ids: list[str] = []
    t0 = time.time()

    for i, (doc, meta, doc_id) in enumerate(rows):
        batch_docs.append(doc)
        batch_metas.append(meta)
        batch_ids.append(doc_id)

        if len(batch_docs) >= BATCH_SIZE:
            try:
                collection.upsert(
                    documents=batch_docs,
                    metadatas=batch_metas,
                    ids=batch_ids,
                )
                written += len(batch_docs)
            except Exception as exc:
                print(f"  Batch upsert error at offset {i}: {exc}")
            batch_docs.clear()
            batch_metas.clear()
            batch_ids.clear()

            if written % (BATCH_SIZE * 10) == 0:
                elapsed = time.time() - t0
                eta = format_eta(elapsed, written, len(rows))
                print(f"  Indexed {written:,}/{len(rows):,} … ETA {eta}")

    # Final partial batch
    if batch_docs:
        try:
            collection.upsert(
                documents=batch_docs,
                metadatas=batch_metas,
                ids=batch_ids,
            )
            written += len(batch_docs)
        except Exception as exc:
            print(f"  Final batch upsert error: {exc}")

    return written


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Import mechanics.StackExchange XML dump into ChromaDB."
    )
    parser.add_argument(
        "--skip-extract",
        action="store_true",
        help="Skip 7z extraction (use if Posts.xml already extracted).",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Parse and count documents only — no ChromaDB writes.",
    )
    args = parser.parse_args()

    # Phase 1: Extract
    if args.skip_extract:
        if not XML_PATH.exists():
            print(
                f"ERROR: --skip-extract specified but {XML_PATH} does not exist.\n"
                "Run without --skip-extract to extract first."
            )
            return
        print(f"Skipping extraction — using existing {XML_PATH}")
    else:
        if XML_PATH.exists():
            print(f"Posts.xml already exists at {XML_PATH} — skipping extraction.")
        else:
            extract_archive(ARCHIVE_PATH, EXTRACT_DIR)

    # Connect to ChromaDB (even in dry-run, so we can report current count)
    client = chromadb.PersistentClient(path=CHROMA_DB_PATH)
    collection = client.get_or_create_collection(name=COLLECTION_NAME)
    initial_count = collection.count()
    print(f"\nChromaDB ready. Collection '{COLLECTION_NAME}': {initial_count:,} docs.")
    if args.dry_run:
        print("DRY-RUN mode — no data will be written to ChromaDB.")

    # Phase 2: Collect answers (pass 1)
    answers = _scan_answers(XML_PATH)

    # Phase 3: Filter questions and build documents (pass 2)
    total_scanned, total_skipped_filter, rows = _iter_questions(XML_PATH, answers)

    total_quality = len(rows)
    print(
        f"\nParse complete: {total_scanned:,} questions scanned, "
        f"{total_quality:,} passed quality filter, "
        f"{total_scanned - total_quality:,} skipped."
    )

    # Phase 4: Index
    written = index_into_chroma(rows, collection, args.dry_run)

    # Summary
    final_count = collection.count() if not args.dry_run else initial_count
    print("\n--- Import Complete ---")
    print(f"Questions scanned : {total_scanned:,}")
    print(f"Passed filter     : {total_quality:,}")
    print(f"Skipped (quality) : {total_scanned - total_quality:,}")
    if args.dry_run:
        print("Written           : 0  (dry-run)")
    else:
        print(f"Written (upserted): {written:,}")
        print(f"Collection total  : {final_count:,} docs  (was {initial_count:,})")


if __name__ == "__main__":
    main()
