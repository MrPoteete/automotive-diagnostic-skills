#!/usr/bin/env python3
"""
ingest_ebook.py — Ingest ebook frames into ChromaDB via Gemini Flash captioning.

Pipeline:
  1. Load PNG frames from --frames-dir
  2. Deduplicate consecutive similar frames (pixel diff via Pillow thumbnail)
  3. Caption each unique frame with Gemini 2.5 Flash
  4. Ingest captions into a ChromaDB collection

Usage:
    uv run python scripts/ingest_ebook.py --frames-dir /tmp/scannerdanner_frames
    uv run python scripts/ingest_ebook.py --frames-dir /tmp/scannerdanner_frames --dry-run
    uv run python scripts/ingest_ebook.py --frames-dir /tmp/scannerdanner_frames \\
        --source-name scannerdanner_ebook --collection scannerdanner_ebook

Options:
    --frames-dir DIR        Directory of PNG frames (required)
    --collection NAME       ChromaDB collection name (default: scannerdanner_ebook)
    --source-name NAME      Source tag in metadata (default: scannerdanner_ebook)
    --confidence FLOAT      Confidence score for metadata (default: 0.90)
    --model MODEL           Gemini model (default: gemini-2.5-flash)
    --dedup-threshold INT   Mean pixel diff below this = duplicate (default: 10)
    --dry-run               Preview deduplication without calling Gemini or writing DB
"""

from __future__ import annotations

import argparse
import hashlib
import logging
import os
import subprocess
import sys
from pathlib import Path

import chromadb
from PIL import Image

PROJECT_ROOT = Path(__file__).parent.parent
CHROMA_PATH = PROJECT_ROOT / "data" / "vector_store" / "chroma"

DEFAULT_COLLECTION = "scannerdanner_ebook"
DEFAULT_SOURCE = "scannerdanner_ebook"
DEFAULT_CONFIDENCE = 0.90
DEFAULT_MODEL = "gemini-2.5-flash"
DEDUP_THUMBNAIL = (32, 32)

CAPTION_PROMPT = """You are analyzing a page spread from a professional automotive diagnostic textbook (ScannerDanner).

Describe everything you see, focusing on what a mechanic would need to know:
- Oscilloscope waveforms: signal names, voltage/time scales, waveform shape, what the pattern indicates diagnostically
- Scan tool / live data tables: each parameter name and value shown, and what they suggest
- Component photos: what part is shown, its condition, relevant features visible
- Wiring diagrams or circuit schematics: components labeled, signal flow, key test points
- Diagnostic text, procedures, bullet lists, or conclusions on the page
- Section or topic heading

Be specific and technical. Use proper automotive diagnostic terminology. This description will be used for semantic search by professional mechanics diagnosing real vehicles."""


def _read_key(env_var: str, secret_name: str | None = None) -> str:
    """Read key from environment, .env file, or GCP Secret Manager."""
    key = os.environ.get(env_var, "")
    if key:
        return key
    env_path = PROJECT_ROOT / ".env"
    if env_path.exists():
        for line in env_path.read_text().splitlines():
            if line.startswith(f"{env_var}="):
                return line.split("=", 1)[1].strip().strip('"').strip("'")
    if secret_name:
        result = subprocess.run(
            ["gcloud", "secrets", "versions", "access", "latest", f"--secret={secret_name}"],
            capture_output=True, text=True,
        )
        if result.returncode == 0:
            return result.stdout.strip()
    return ""


def _thumbnail_pixels(path: Path) -> list[int]:
    """Return flat grayscale pixel list of a tiny thumbnail for comparison."""
    img = Image.open(path).convert("L").resize(DEDUP_THUMBNAIL, Image.LANCZOS)
    return list(img.tobytes())


def _pixel_diff(a: list[int], b: list[int]) -> float:
    """Mean absolute pixel difference (0–255 scale)."""
    return sum(abs(x - y) for x, y in zip(a, b)) / len(a)


def deduplicate(frames: list[Path], threshold: int) -> list[Path]:
    """Return frames that differ meaningfully from the previously kept frame."""
    if not frames:
        return []
    kept = [frames[0]]
    prev_pixels = _thumbnail_pixels(frames[0])
    for frame in frames[1:]:
        pixels = _thumbnail_pixels(frame)
        if _pixel_diff(prev_pixels, pixels) >= threshold:
            kept.append(frame)
            prev_pixels = pixels
    return kept


def caption_frame(genai_client: object, frame_path: Path, model: str, retries: int = 3) -> str:
    """Send a frame image to Gemini and return a detailed diagnostic caption.

    Retries up to `retries` times on transient 503/429 errors with exponential backoff.
    """
    import time
    from google.genai import types  # type: ignore[import-untyped]

    image_bytes = frame_path.read_bytes()
    last_exc: Exception | None = None
    for attempt in range(retries):
        try:
            response = genai_client.models.generate_content(  # type: ignore[union-attr]
                model=model,
                contents=[
                    types.Part.from_bytes(data=image_bytes, mime_type="image/png"),
                    CAPTION_PROMPT,
                ],
            )
            if response.text:
                return response.text.strip()
            # Safety filter or empty response — not retryable
            candidates = getattr(response, "candidates", None)
            reason = "unknown"
            if candidates:
                finish_reason = getattr(candidates[0], "finish_reason", None)
                reason = str(finish_reason) if finish_reason else "unknown"
            return f"[Caption unavailable — Gemini response blocked or empty: finish_reason={reason}]"
        except Exception as exc:
            last_exc = exc
            err_str = str(exc)
            if attempt < retries - 1 and ("503" in err_str or "429" in err_str or "UNAVAILABLE" in err_str):
                wait = 5 * (3 ** attempt)  # 5s, 15s, 45s
                logging.getLogger(__name__).warning(
                    "Gemini transient error (attempt %d/%d), retrying in %ds: %s",
                    attempt + 1, retries, wait, exc,
                )
                time.sleep(wait)
            else:
                raise
    raise last_exc  # type: ignore[misc]


def get_collection(name: str) -> chromadb.Collection:
    client = chromadb.PersistentClient(path=str(CHROMA_PATH))
    return client.get_or_create_collection(
        name=name,
        metadata={"hnsw:space": "cosine"},
    )


def chunk_id(source: str, frame_name: str) -> str:
    return hashlib.sha256(f"{source}:{frame_name}".encode()).hexdigest()[:16]


def main() -> int:
    parser = argparse.ArgumentParser(description="Ingest ebook frames into ChromaDB via Gemini captioning")
    parser.add_argument("--frames-dir", required=True, type=Path)
    parser.add_argument("--collection", default=DEFAULT_COLLECTION)
    parser.add_argument("--source-name", default=DEFAULT_SOURCE)
    parser.add_argument("--confidence", type=float, default=DEFAULT_CONFIDENCE)
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument("--dedup-threshold", type=int, default=10)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
        handlers=[logging.StreamHandler()],
    )
    log = logging.getLogger(__name__)

    # Load frames
    frames = sorted(args.frames_dir.glob("*.png"))
    if not frames:
        log.error("No PNG frames found in %s", args.frames_dir)
        return 1
    log.info("Found %d total frames", len(frames))

    # Deduplicate
    unique = deduplicate(frames, threshold=args.dedup_threshold)
    log.info("After deduplication (threshold=%d): %d unique frames", args.dedup_threshold, len(unique))

    if args.dry_run:
        log.info("--dry-run: showing unique frames, no Gemini calls or DB writes")
        for f in unique:
            print(f"  {f.name}")
        return 0

    # Init Gemini
    api_key = _read_key("GOOGLE_AI_API_KEY", secret_name="gemini-api-key")
    if not api_key:
        log.error("No Gemini API key found (env GOOGLE_AI_API_KEY or GCP secret gemini-api-key)")
        return 1
    from google import genai as google_genai  # type: ignore[import-untyped]
    genai_client = google_genai.Client(api_key=api_key)

    # Init ChromaDB
    collection = get_collection(args.collection)
    log.info("ChromaDB collection '%s' — %d existing docs", args.collection, collection.count())

    # Caption and ingest
    ingested = skipped = errors = 0
    for i, frame_path in enumerate(unique, 1):
        cid = chunk_id(args.source_name, frame_path.name)

        # Skip already-ingested frames
        existing = collection.get(ids=[cid])
        if existing["ids"]:
            log.info("[%d/%d] %s — already ingested, skipping", i, len(unique), frame_path.name)
            skipped += 1
            continue

        log.info("[%d/%d] Captioning %s ...", i, len(unique), frame_path.name)
        try:
            caption = caption_frame(genai_client, frame_path, args.model)
        except Exception as exc:
            log.error("  Failed to caption %s: %s", frame_path.name, exc)
            errors += 1
            continue

        doc_text = f"[{args.source_name}] {frame_path.stem}\n\n{caption}"

        collection.upsert(
            ids=[cid],
            documents=[doc_text],
            metadatas=[{
                "source": args.source_name,
                "frame": frame_path.name,
                "confidence": args.confidence,
                "content_type": "ebook_image",
            }],
        )
        ingested += 1
        log.info("  Ingested %s (id=%s)", frame_path.name, cid[:8])

    log.info(
        "Done — ingested: %d | skipped: %d | errors: %d | collection total: %d",
        ingested, skipped, errors, collection.count(),
    )
    return 0 if errors == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
