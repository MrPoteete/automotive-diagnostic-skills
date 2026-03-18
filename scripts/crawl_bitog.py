# Checked AGENTS.md - implementing directly because this is a standalone data import CLI
# with no auth/sensitive data (read-only HTTP + ChromaDB upsert).
"""
Crawl BobIsTheOilGuy (BITOG) forums via the Wayback Machine CDX API.

BITOG uses Cloudflare Managed Challenge — direct HTTP returns 403.
This crawler uses the Internet Archive's CDX API to retrieve archived
snapshots, bypassing Cloudflare entirely.

Run:
  .venv/bin/python3 scripts/crawl_bitog.py --dry-run --limit 50
  .venv/bin/python3 scripts/crawl_bitog.py --resume
  .venv/bin/python3 scripts/crawl_bitog.py --limit 5000
  .venv/bin/python3 scripts/crawl_bitog.py  # full crawl (runs for hours)
"""

from __future__ import annotations

import argparse
import datetime
import hashlib
import json
import logging
import pathlib
import re
import sqlite3
import sys
import time
import urllib.parse
import urllib.robotparser
from typing import TYPE_CHECKING, Any

import requests  # type: ignore[import-untyped]
from bs4 import BeautifulSoup  # type: ignore[import-untyped]

if TYPE_CHECKING:
    pass

# ---------------------------------------------------------------------------
# Paths & constants
# ---------------------------------------------------------------------------

PROJECT_ROOT = pathlib.Path(__file__).resolve().parent.parent
CHROMA_PATH = PROJECT_ROOT / "data" / "vector_store" / "chroma"
COLLECTION_NAME = "mechanics_forum"
RAW_IMPORTS_DIR = PROJECT_ROOT / "data" / "raw_imports" / "bitog"
CHECKPOINT_FILE = RAW_IMPORTS_DIR / ".bitog_crawl.checkpoint.json"
URL_LIST_FILE = RAW_IMPORTS_DIR / "thread_urls.jsonl"
DEFAULT_DB_PATH = PROJECT_ROOT / "database" / "automotive_complaints.db"

CRAWLER_UA = "Python-Crawler/1.0 (automotive research; respectful 2s delay)"

# Sub-forums to skip (off-topic for automotive diagnostics)
# All others are accepted — BITOG is automotive-focused throughout.
BLOCKED_SUBFORUM_SLUGS: frozenset[str] = frozenset({
    "small-engine-oil",
    "aviation-oil",
    "forum-help",
    "introductions",
    "buy-sell-trade",
    "off-topic",
})

# ---------------------------------------------------------------------------
# Compiled regexes
# ---------------------------------------------------------------------------

_BOT_AUTHOR_RE = re.compile(
    r"\[(deleted|removed)\]|^Guest$|\b(bot|spam|automod)\b",
    re.IGNORECASE,
)
_YEAR_RE = re.compile(r"\b(19[9]\d|20[012]\d|202[0-6])\b")
_OIL_SPEC_RE = re.compile(
    r"\b(\d[Ww]-\d{2}|\d{2}[Ww]-\d{2}|API\s+[A-Z]{2,3}|ACEA\s+[A-C]\d"
    r"|ILSAC\s+GF-\d|dexos\d?)\b",
    re.IGNORECASE,
)
_TECH_TERMS = [
    # Automotive diagnostics (from import_reddit.py)
    "sensor", "solenoid", "relay", "fuse", "connector", "bearing", "gasket",
    "pump", "injector", "coil", "alternator", "starter", "caliper", "rotor",
    "strut", "actuator", "harness", "seal", "valve", "thermostat", "catalytic",
    "oxygen", "throttle", "camshaft", "crankshaft", "timing", "serpentine",
    "replace", "torque", "bleed", "flush", "ohm", "voltage", "resistance",
    "measure", "inspect", "disconnect", "diagnose", "scan", "test",
    "OBD", "DTC", "misfire", "lean", "rich", "vacuum", "pressure", "fault",
    "code", "ECU", "PCM", "BCM", "TCM", "MAF", "MAP", "TPS", "IAT",
    "transmission", "differential", "coolant", "cylinder", "ABS", "brake",
    "suspension", "steering", "ignition", "exhaust", "fuel", "oil",
    # BITOG-specific extras
    "viscosity", "additive", "zinc", "ZDDP", "synthetic", "UOA", "wear",
    "TBN", "TAN", "sludge", "varnish", "shear", "turbo", "DPF", "LSPI",
    "cSt", "ACEA", "dexos", "ILSAC", "piston", "ring",
]
_TECH_RE = re.compile(
    r"\b(?:" + "|".join(re.escape(t) for t in sorted(set(_TECH_TERMS), key=len, reverse=True)) + r")\b",
    re.IGNORECASE,
)

# ---------------------------------------------------------------------------
# Rate limiter
# ---------------------------------------------------------------------------


class RateLimiter:
    def __init__(self, delay: float = 2.0) -> None:
        self._delay = delay
        self._last = 0.0

    def wait(self) -> None:
        elapsed = time.monotonic() - self._last
        if elapsed < self._delay:
            time.sleep(self._delay - elapsed)
        self._last = time.monotonic()


# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------


def setup_logging(log_path: pathlib.Path | None = None) -> logging.Logger:
    log = logging.getLogger("bitog_crawler")
    log.setLevel(logging.INFO)
    fmt = logging.Formatter("%(asctime)s  %(message)s", datefmt="%Y-%m-%d %H:%M:%S")
    if not log.handlers:
        ch = logging.StreamHandler(sys.stdout)
        ch.setFormatter(fmt)
        log.addHandler(ch)
        if log_path:
            log_path.parent.mkdir(parents=True, exist_ok=True)
            fh = logging.FileHandler(log_path, mode="a", encoding="utf-8")
            fh.setFormatter(fmt)
            log.addHandler(fh)
    return log


# ---------------------------------------------------------------------------
# ChromaDB helpers
# ---------------------------------------------------------------------------


def _get_collection(dry_run: bool, log: logging.Logger) -> Any:
    try:
        import chromadb  # type: ignore[import-untyped]
    except ImportError as exc:
        raise ImportError("chromadb not installed. Run: .venv/bin/pip install chromadb") from exc

    if dry_run:
        log.info("ChromaDB: DRY-RUN mode — no writes.")
        return None

    client = chromadb.PersistentClient(path=str(CHROMA_PATH))
    collection = client.get_or_create_collection(
        name=COLLECTION_NAME,
        metadata={"hnsw:space": "cosine"},
    )
    for attempt in range(10):
        try:
            count = collection.count()
            log.info(f"ChromaDB ready. Collection '{COLLECTION_NAME}': {count:,} docs before import.")
            return collection
        except Exception:
            if attempt == 9:
                log.warning("ChromaDB HNSW index still compacting — proceeding without count.")
                return collection
            log.info(f"  ChromaDB index compacting, retrying in 30s (attempt {attempt + 1}/10)...")
            time.sleep(30)
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
    if dry_run:
        total_upserted += len(batch_ids)
        log.info(
            f"  Batch upserted: {len(batch_ids)} docs | running total: {total_upserted:,} [DRY-RUN]"
        )
        return total_upserted
    try:
        collection.upsert(documents=batch_docs, metadatas=batch_meta, ids=batch_ids)
        total_upserted += len(batch_ids)
        log.info(f"  Batch upserted: {len(batch_ids)} docs | running total: {total_upserted:,}")
    except Exception as exc:
        log.warning(f"Batch upsert error: {exc}")
    return total_upserted


# ---------------------------------------------------------------------------
# Checkpoint helpers
# ---------------------------------------------------------------------------


def load_checkpoint(log: logging.Logger) -> dict[str, Any]:
    if CHECKPOINT_FILE.exists():
        try:
            data: dict[str, Any] = json.loads(CHECKPOINT_FILE.read_text())
            data["seen_url_hashes"] = set(data.get("seen_url_hashes", []))
            log.info(
                f"Checkpoint loaded: phase={data.get('phase')} "
                f"fetched={data.get('threads_fetched', 0):,} "
                f"indexed={data.get('threads_indexed', 0):,}"
            )
            return data
        except Exception as exc:
            log.warning(f"Could not load checkpoint ({exc}) — starting fresh.")
    return _fresh_checkpoint()


def _fresh_checkpoint() -> dict[str, Any]:
    return {
        "phase": "fetch_urls",
        "threads_fetched": 0,
        "threads_indexed": 0,
        "last_url": "",
        "seen_url_hashes": set(),
        "file_offset": 0,
        "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
    }


def save_checkpoint(data: dict[str, Any], dry_run: bool, log: logging.Logger) -> None:
    if dry_run:
        return
    to_save = dict(data)
    to_save["seen_url_hashes"] = sorted(data.get("seen_url_hashes", set()))
    to_save["timestamp"] = datetime.datetime.now(datetime.timezone.utc).isoformat()
    RAW_IMPORTS_DIR.mkdir(parents=True, exist_ok=True)
    CHECKPOINT_FILE.write_text(json.dumps(to_save, indent=2))


# ---------------------------------------------------------------------------
# Vehicle make regex (loaded from complaints DB at startup)
# ---------------------------------------------------------------------------


def build_make_regex(db_path: pathlib.Path, log: logging.Logger) -> re.Pattern[str]:
    log.info(f"Loading vehicle makes from {db_path} ...")
    if not db_path.exists():
        log.error(f"DB not found at {db_path}. Make extraction will be empty.")
        return re.compile(r"(?!)")  # never-matches pattern
    try:
        con = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
        rows = con.execute("SELECT DISTINCT make FROM complaints_fts").fetchall()
        con.close()
        makes = sorted(
            (r[0].strip() for r in rows if r[0] and len(r[0].strip()) > 2),
            key=len,
            reverse=True,
        )
        log.info(f"  Loaded {len(makes)} makes.")
        return re.compile(
            r"\b(" + "|".join(re.escape(m) for m in makes) + r")\b",
            re.IGNORECASE,
        )
    except Exception as exc:
        log.warning(f"Could not load makes ({exc}). Make extraction disabled.")
        return re.compile(r"(?!)")


# ---------------------------------------------------------------------------
# Phase 1: CDX URL fetch
# ---------------------------------------------------------------------------


def fetch_cdx_urls(
    from_date: str,
    to_date: str,
    limiter: RateLimiter,
    log: logging.Logger,
) -> int:
    log.info("Phase 1: Fetching thread URLs from Wayback CDX API ...")
    params: dict[str, Any] = {
        "url": "bobistheoilguy.com/forums/threads/*",
        "output": "json",
        "fl": "timestamp,original,statuscode",
        "filter": "statuscode:200",
        "collapse": "urlkey",
        "limit": 100000,
        "from": from_date,
        "to": to_date,
    }
    headers = {"User-Agent": CRAWLER_UA}

    limiter.wait()
    try:
        resp = requests.get(
            "https://web.archive.org/cdx/search/cdx",
            params=params,
            headers=headers,
            timeout=120,
        )
        resp.raise_for_status()
        rows_all: list[list[str]] = resp.json()
    except Exception as exc:
        log.error(f"CDX API request failed: {exc}")
        return 0

    if not rows_all or len(rows_all) <= 1:
        log.warning("CDX API returned no rows.")
        return 0

    header = rows_all[0]
    rows = rows_all[1:]
    log.info(f"CDX API returned {len(rows):,} raw rows.")

    RAW_IMPORTS_DIR.mkdir(parents=True, exist_ok=True)
    count = 0
    with URL_LIST_FILE.open("w", encoding="utf-8") as fh:
        for row in rows:
            try:
                entry = dict(zip(header, row))
                original_url = entry.get("original", "")
                parsed = urllib.parse.urlparse(original_url)
                segments = [s for s in parsed.path.split("/") if s]
                # XenForo thread URL: /forums/threads/{slug}.{id}/
                if len(segments) < 3 or segments[0] != "forums" or segments[1] != "threads":
                    continue
                slug_with_id = segments[2]
                # Thread URLs: /forums/threads/{title-slug}.{id}/
                # Sub-forum is NOT in the thread URL — it's in the breadcrumb on the page.
                # Accept all thread URLs here; sub-forum filtering happens during HTML parse.
                m = re.match(r"^(.+?)\.\d+$", slug_with_id)
                if not m:
                    continue
                record = {
                    "timestamp": entry.get("timestamp", ""),
                    "original_url": original_url,
                    "sub_forum_slug": "",  # populated during Phase 2 HTML parse
                }
                fh.write(json.dumps(record) + "\n")
                count += 1
            except Exception as exc:
                log.warning(f"Skipping malformed CDX row {row}: {exc}")

    log.info(f"Phase 1 complete. {count:,} filtered thread URLs → {URL_LIST_FILE}")
    return count


# ---------------------------------------------------------------------------
# HTML parsing (XenForo 2)
# ---------------------------------------------------------------------------


def _parse_thread_page(
    html: str,
    canonical_url: str,
    log: logging.Logger,
) -> dict[str, Any] | None:
    soup = BeautifulSoup(html, "lxml")

    title_tag = soup.select_one("h1.p-title-value, h1[class*='title']")
    title = title_tag.get_text(strip=True) if title_tag else "Untitled"

    # Extract sub-forum from breadcrumb (XenForo: .p-breadcrumbs li a or .breadcrumb)
    sub_forum_slug = ""
    for crumb in soup.select(".p-breadcrumbs a, nav.breadcrumb a"):
        href = str(crumb.get("href", ""))
        m = re.search(r"/forums/([^/]+?\.\d+)/?$", href)
        if m:
            raw = m.group(1).rsplit(".", 1)[0]
            sub_forum_slug = raw
            break

    posts: list[dict[str, Any]] = []
    for article in soup.select("article.message"):
        try:
            body_tag = article.select_one(".message-body .bbWrapper")
            body = body_tag.get_text(separator="\n", strip=True) if body_tag else ""

            author_tag = article.select_one(".message-userDetails .username")
            author = author_tag.get_text(strip=True) if author_tag else "Unknown"

            time_tag = article.select_one("time[datetime]")
            post_ts = 0
            if time_tag and time_tag.get("datetime"):
                try:
                    dt_str: str = str(time_tag["datetime"]).replace("Z", "+00:00")
                    post_ts = int(datetime.datetime.fromisoformat(dt_str).timestamp())
                except ValueError:
                    pass

            like_tag = article.select_one("[data-reaction-score]")
            like_count = 0
            if like_tag and like_tag.get("data-reaction-score"):
                try:
                    like_count = int(str(like_tag["data-reaction-score"]))
                except ValueError:
                    pass

            if _BOT_AUTHOR_RE.search(author):
                continue

            posts.append({
                "body": body,
                "author": author,
                "timestamp": post_ts,
                "like_count": like_count,
            })
        except Exception as exc:
            log.warning(f"Post parse error in {canonical_url}: {exc}")

    if not posts:
        return None

    # Get reply count from page description metadata
    reply_count = max(0, len(posts) - 1)
    for dd in soup.select(".p-description dd"):
        text = dd.get_text(strip=True).replace(",", "")
        if text.isdigit():
            reply_count = int(text)
            break

    return {
        "title": title,
        "sub_forum_slug": sub_forum_slug,
        "op": posts[0],
        "replies": sorted(posts[1:], key=lambda p: p["like_count"], reverse=True),
        "reply_count": reply_count,
    }


# ---------------------------------------------------------------------------
# Entity extraction
# ---------------------------------------------------------------------------


def _extract_entities(
    text: str,
    make_re: re.Pattern[str],
) -> dict[str, str]:
    raw_years = [int(y) for y in _YEAR_RE.findall(text) if 1990 <= int(y) <= 2026]
    years = " ".join(str(y) for y in sorted(set(raw_years)))
    oil_specs = " ".join(sorted({m.upper() for m in _OIL_SPEC_RE.findall(text)}))
    makes = " ".join(sorted({m.upper() for m in make_re.findall(text)}))
    return {"years": years, "oil_specs": oil_specs, "makes": makes, "models": ""}


# ---------------------------------------------------------------------------
# Phase 2: Thread crawl loop
# ---------------------------------------------------------------------------


def process_threads(
    args: argparse.Namespace,
    checkpoint: dict[str, Any],
    collection: Any,
    limiter: RateLimiter,
    make_re: re.Pattern[str],
    log: logging.Logger,
) -> None:
    log.info("Phase 2: Crawling threads from URL list ...")

    if not URL_LIST_FILE.exists():
        log.error(f"URL list not found: {URL_LIST_FILE}. Run without --resume first.")
        sys.exit(1)

    batch_docs: list[str] = []
    batch_meta: list[dict[str, Any]] = []
    batch_ids: list[str] = []
    total_processed = 0
    total_upserted: int = checkpoint.get("threads_indexed", 0)
    seen_url_hashes: set[str] = checkpoint.get("seen_url_hashes", set())
    headers = {"User-Agent": CRAWLER_UA}

    try:
        with URL_LIST_FILE.open(encoding="utf-8") as fh:
            if checkpoint.get("file_offset", 0) > 0:
                log.info(f"Resuming from file offset {checkpoint['file_offset']:,}")
                fh.seek(checkpoint["file_offset"])

            while True:
                line = fh.readline()
                if not line:
                    break
                current_offset = fh.tell()

                if args.limit and total_processed >= args.limit:
                    log.info(f"Reached --limit {args.limit}.")
                    break

                try:
                    data = json.loads(line)
                    timestamp = data["timestamp"]
                    canonical_url = data["original_url"]
                except (json.JSONDecodeError, KeyError):
                    log.warning(f"Malformed URL list line: {line.strip()}")
                    continue

                total_processed += 1

                # Dedup by URL hash
                url_hash = hashlib.sha256(canonical_url.encode()).hexdigest()
                if url_hash in seen_url_hashes:
                    continue

                # Extract thread ID from URL
                m = re.search(r"\.(\d+)/?$", canonical_url)
                if not m:
                    continue
                thread_id = m.group(1)

                # Fetch Wayback snapshot
                snapshot_url = f"https://web.archive.org/web/{timestamp}/{canonical_url}"
                log.info(f"[{total_processed}] Fetching: {canonical_url}")
                limiter.wait()
                try:
                    resp = requests.get(snapshot_url, headers=headers, timeout=30)
                    if resp.status_code != 200:
                        log.warning(f"  HTTP {resp.status_code} for {snapshot_url}")
                        continue
                except requests.RequestException as exc:
                    log.error(f"  Request failed: {exc}")
                    continue

                # Parse
                parsed = _parse_thread_page(resp.text, canonical_url, log)
                if not parsed:
                    continue

                # Apply sub-forum blocklist (extracted from breadcrumb during parse)
                sub_forum = parsed["sub_forum_slug"]
                if sub_forum and sub_forum in BLOCKED_SUBFORUM_SLUGS:
                    continue

                op = parsed["op"]

                # OP length gate
                if len(op["body"]) < 150:
                    continue

                # Assemble document
                entities = _extract_entities(parsed["title"] + "\n" + op["body"], make_re)
                top_replies = "\n".join(f"• {r['body'][:200]}" for r in parsed["replies"][:3])
                doc_text = (
                    f"[BITOG THREAD] {parsed['title']}\n"
                    f"[SUB-FORUM] {sub_forum}\n"
                    f"{op['body'][:600]}\n"
                    f"[TOP REPLIES]\n{top_replies}\n"
                    f"[VEHICLE] {entities['makes']} {entities['models']} {entities['years']}\n"
                    f"[OIL SPECS] {entities['oil_specs']}"
                ).strip()

                # Final quality gates
                if len(doc_text) < 200:
                    continue
                if len(_TECH_RE.findall(doc_text)) < 1:
                    continue

                metadata: dict[str, Any] = {
                    "source": "bitog",
                    "sub_forum": sub_forum,
                    "thread_id": thread_id,
                    "canonical_url": canonical_url,
                    "makes": entities["makes"],
                    "models": entities["models"],
                    "years": entities["years"],
                    "oil_specs": entities["oil_specs"],
                    "like_count": op["like_count"],
                    "thread_reply_count": parsed["reply_count"],
                    "post_timestamp": op["timestamp"],
                    "author": op["author"],
                }

                batch_docs.append(doc_text)
                batch_meta.append(metadata)
                batch_ids.append(f"bitog_{thread_id}")
                seen_url_hashes.add(url_hash)

                if len(batch_ids) >= args.batch_size:
                    total_upserted = _upsert_batch(
                        collection, batch_docs, batch_meta, batch_ids,
                        args.dry_run, total_upserted, log,
                    )
                    batch_docs.clear()
                    batch_meta.clear()
                    batch_ids.clear()

                    checkpoint["phase"] = "crawl_threads"
                    checkpoint["threads_fetched"] = total_processed
                    checkpoint["threads_indexed"] = total_upserted
                    checkpoint["last_url"] = canonical_url
                    checkpoint["file_offset"] = current_offset
                    checkpoint["seen_url_hashes"] = seen_url_hashes
                    save_checkpoint(checkpoint, args.dry_run, log)

    finally:
        if batch_ids:
            total_upserted = _upsert_batch(
                collection, batch_docs, batch_meta, batch_ids,
                args.dry_run, total_upserted, log,
            )

        checkpoint["phase"] = "completed"
        checkpoint["threads_fetched"] = total_processed
        checkpoint["threads_indexed"] = total_upserted
        checkpoint["seen_url_hashes"] = seen_url_hashes
        save_checkpoint(checkpoint, args.dry_run, log)
        log.info(
            f"Phase 2 complete. Processed: {total_processed:,} | "
            f"Upserted: {total_upserted:,}" + (" [DRY-RUN]" if args.dry_run else "")
        )


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Crawl BITOG forums via Wayback CDX API → ChromaDB.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("--dry-run", action="store_true", help="No writes to ChromaDB or checkpoint.")
    parser.add_argument("--limit", type=int, default=0, metavar="N", help="Stop after N threads (0 = no limit).")
    parser.add_argument("--batch-size", type=int, default=500, metavar="N", help="ChromaDB upsert batch size.")
    parser.add_argument("--resume", action="store_true", help="Resume from checkpoint.")
    parser.add_argument("--from-date", type=str, default="20200101", metavar="YYYYMMDD")
    parser.add_argument("--to-date", type=str, default="20260101", metavar="YYYYMMDD")
    parser.add_argument("--log-file", type=pathlib.Path, default=None, metavar="PATH")
    parser.add_argument("--db-path", type=pathlib.Path, default=DEFAULT_DB_PATH, metavar="PATH")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)

    log_path = args.log_file or pathlib.Path("/tmp/bitog_crawl.log")
    log = setup_logging(log_path)

    log.info("=" * 60)
    log.info("BITOG Crawler — Wayback CDX strategy (Cloudflare bypass)")
    log.info("=" * 60)
    if args.dry_run:
        log.info("MODE: DRY-RUN")
    if args.limit:
        log.info(f"LIMIT: {args.limit:,} threads")
    if args.resume:
        log.info("RESUME: loading checkpoint")

    RAW_IMPORTS_DIR.mkdir(parents=True, exist_ok=True)

    # robots.txt check — use requests (custom UA) since urllib gets CF 403
    rp = urllib.robotparser.RobotFileParser()
    try:
        robots_resp = requests.get(
            "https://bobistheoilguy.com/robots.txt",
            headers={"User-Agent": CRAWLER_UA},
            timeout=15,
        )
        if robots_resp.status_code == 200:
            rp.parse(robots_resp.text.splitlines())
            if not rp.can_fetch("*", "https://bobistheoilguy.com/forums/threads/"):
                log.critical("robots.txt disallows crawling /forums/threads/. Aborting.")
                return 1
            log.info("robots.txt check passed.")
        else:
            log.warning(f"robots.txt returned HTTP {robots_resp.status_code} — proceeding cautiously.")
    except Exception as exc:
        log.warning(f"Could not read robots.txt ({exc}) — proceeding cautiously.")

    make_re = build_make_regex(args.db_path, log)
    limiter = RateLimiter(delay=2.0)
    collection = _get_collection(args.dry_run, log)

    checkpoint = load_checkpoint(log) if args.resume else _fresh_checkpoint()

    # Phase 1: fetch CDX URL list (skip if checkpoint already past this phase)
    if checkpoint.get("phase") == "fetch_urls":
        fetched = fetch_cdx_urls(args.from_date, args.to_date, limiter, log)
        if fetched == 0:
            log.error("CDX fetch returned 0 URLs. Aborting.")
            return 1
        checkpoint["phase"] = "crawl_threads"
        checkpoint["threads_fetched"] = fetched
        save_checkpoint(checkpoint, args.dry_run, log)
    else:
        log.info(f"Skipping Phase 1 (checkpoint phase='{checkpoint.get('phase')}').")

    # Phase 2: crawl threads
    process_threads(args, checkpoint, collection, limiter, make_re, log)

    log.info("--- BITOG Crawler Finished ---")
    return 0


if __name__ == "__main__":
    sys.exit(main())
