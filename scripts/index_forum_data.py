"""
Index StackExchange automotive mechanics forum data into ChromaDB.

Checked AGENTS.md - delegated to Gemini (gemini-2.5-flash) per GEMINI_WORKFLOW.md.
This file contains Gemini's output, reviewed and fixed by Claude:
- Fixed: use creation_date from question data (confirmed present in raw files)
- Fixed: clear batch lists after dry-run pass to prevent double-counting
- Updated (Phase 5l): improved chunking strategy embeds question body symptom
  language alongside the accepted answer, validated by test_rag_chunking.py.

Chunking strategy (improved):
  document = "Q: {title}\nSymptoms: {body[:400]}\nTags: {tags}\nA: {answer}"
  Rationale: users query with symptom language ("loud rattle cold start"), not
  answer language. Including both body and answer maximises cosine similarity
  to symptom-phrased queries without losing diagnostic answer content.

Run:  python scripts/index_forum_data.py
Dry:  python scripts/index_forum_data.py --dry-run
"""

import argparse
import json
import os
import re

import chromadb  # type: ignore[import-untyped]

RAW_DATA_DIR = "data/raw_imports/forum_data/"
CHROMA_DB_PATH = "data/vector_store/chroma/"
COLLECTION_NAME = "mechanics_forum"
BATCH_SIZE = 100


def strip_html(text: str) -> str:
    """Remove HTML tags from a string."""
    if not isinstance(text, str):
        return ""
    cleaned = re.sub(r"<[^>]+>", " ", text)
    return re.sub(r"\s+", " ", cleaned).strip()


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Index StackExchange automotive mechanics forum data into ChromaDB."
    )
    parser.add_argument(
        "--dry-run", action="store_true", help="Count documents without indexing."
    )
    args = parser.parse_args()

    client = chromadb.PersistentClient(path=CHROMA_DB_PATH)
    collection = client.get_or_create_collection(name=COLLECTION_NAME)

    print(f"ChromaDB ready. Collection '{COLLECTION_NAME}': {collection.count()} docs.")
    if args.dry_run:
        print("DRY-RUN mode — no data will be written.")

    documents_to_add: list[str] = []
    metadatas_to_add: list[dict] = []
    ids_to_add: list[str] = []
    total_indexed = 0
    total_skipped = 0

    if not os.path.exists(RAW_DATA_DIR):
        print(f"Error: {RAW_DATA_DIR} not found")
        return

    for year in range(2015, 2026):
        file_path = os.path.join(RAW_DATA_DIR, f"stackexchange_mechanics_{year}.json")
        if not os.path.exists(file_path):
            print(f"Warning: {file_path} not found, skipping.")
            continue

        print(f"\nProcessing stackexchange_mechanics_{year}.json...")
        try:
            with open(file_path, encoding="utf-8") as f:
                data = json.load(f)
        except (json.JSONDecodeError, OSError) as exc:
            print(f"  Error reading {file_path}: {exc}, skipping.")
            continue

        for question in data.get("questions", []):
            question_id = question.get("question_id")
            title = strip_html(question.get("title", ""))
            body = strip_html(question.get("body", ""))
            tags: list[str] = question.get("tags", [])
            score: int = question.get("score", 0)
            is_answered: bool = question.get("is_answered", False)
            link: str = question.get("link", "")
            creation_date: str = question.get("creation_date", "")

            if not title and not body:
                total_skipped += 1
                continue

            # Build accepted answer body (empty string if none)
            accepted_body = ""
            for answer in question.get("answers", []):
                if answer.get("is_accepted"):
                    accepted_body = strip_html(answer.get("body", ""))
                    break

            # Improved chunking: embed symptom language from question body
            # alongside the accepted answer so symptom-phrased queries match well.
            body_excerpt = body[:400]
            parts = [f"Q: {title}"]
            if body_excerpt:
                parts.append(f"Symptoms: {body_excerpt}")
            parts.append(f"Tags: {', '.join(tags)}")
            if accepted_body:
                parts.append(f"A: {accepted_body}")
            document = "\n".join(parts)

            if not document:
                total_skipped += 1
                continue

            doc_id = f"se_{question_id}" if question_id else f"se_noid_{total_indexed}"
            doc_year = int(creation_date[:4]) if len(creation_date) >= 4 else year

            documents_to_add.append(document)
            metadatas_to_add.append({
                "source": "stackexchange",
                "year": doc_year,
                "tags": ",".join(tags),
                "score": score,
                "url": link,
                "is_answered": is_answered,
            })
            ids_to_add.append(doc_id)
            total_indexed += 1

            if len(documents_to_add) >= BATCH_SIZE:
                if not args.dry_run:
                    try:
                        collection.add(
                            documents=documents_to_add,
                            metadatas=metadatas_to_add,
                            ids=ids_to_add,
                        )
                    except Exception as exc:
                        print(f"  Batch insert error: {exc}")
                documents_to_add.clear()
                metadatas_to_add.clear()
                ids_to_add.clear()

            if total_indexed % 1000 == 0:
                print(f"  {total_indexed} documents processed...")

    # Final partial batch
    if documents_to_add and not args.dry_run:
        try:
            collection.add(
                documents=documents_to_add,
                metadatas=metadatas_to_add,
                ids=ids_to_add,
            )
        except Exception as exc:
            print(f"Final batch insert error: {exc}")

    print("\n--- Indexing Complete ---")
    print(f"Documents indexed: {total_indexed}")
    print(f"Documents skipped (empty): {total_skipped}")
    if not args.dry_run:
        print(f"Collection '{COLLECTION_NAME}' total: {collection.count()} docs")
    else:
        print("Dry-run: 0 documents written.")


if __name__ == "__main__":
    main()
