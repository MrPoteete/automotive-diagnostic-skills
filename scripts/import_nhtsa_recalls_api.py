#!/usr/bin/env python3
# Checked AGENTS.md - implementing directly, data pipeline with no security concerns
"""
Import NHTSA recall data from the live recalls API into nhtsa_recalls table.

The NHTSA bulk flat file (FLAT_RCL.txt) was deleted from NHTSA S3 storage.
This script uses the live API instead, querying by make/model/year.

Usage:
    # Test mode — 3 makes, 3 years only (default)
    .venv/bin/python3 scripts/import_nhtsa_recalls_api.py

    # Full run — all 264 make/model combos × 2015-2025
    .venv/bin/python3 scripts/import_nhtsa_recalls_api.py --full

    # Single make
    .venv/bin/python3 scripts/import_nhtsa_recalls_api.py --full --make FORD

    # Force restart (ignore checkpoint)
    .venv/bin/python3 scripts/import_nhtsa_recalls_api.py --full --reset

API:
    GET https://api.nhtsa.gov/recalls/recallsByVehicle?make=FORD&model=F-150&modelYear=2020
    No API key required. Returns JSON with recall records per vehicle/year.

Deduplication strategy:
    The same campaign can cover multiple model years. The same campaign_no
    will appear in the 2020, 2021, 2022 queries for the same vehicle.
    The UNIQUE(campaign_no, make, model) constraint + ON CONFLICT upsert
    aggregates year_from/year_to across all appearances.
"""

import argparse
import json
import re
import sqlite3
import time
from datetime import datetime
from pathlib import Path
from typing import Optional

import requests  # type: ignore[import-untyped]


PROJECT_ROOT = Path(__file__).parent.parent
DB_PATH = PROJECT_ROOT / "database" / "automotive_complaints.db"
CHECKPOINT_PATH = Path("/tmp/nhtsa_recalls_checkpoint.json")
NHTSA_API = "https://api.nhtsa.gov/recalls/recallsByVehicle"
REQUEST_HEADERS = {"User-Agent": "Mozilla/5.0 (automotive-diagnostic-skills research tool)"}
RATE_LIMIT_SEC = 0.3
YEARS_FULL = list(range(2015, 2026))       # 2015–2025 inclusive
YEARS_TEST = list(range(2020, 2023))       # 2020–2022 (3 years for test mode)
TEST_MAKES = {"HONDA", "FORD", "CHEVROLET"}


# ---------------------------------------------------------------------------
# Schema management
# ---------------------------------------------------------------------------

DDL_NHTSA_RECALLS = """
CREATE TABLE nhtsa_recalls (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    campaign_no      TEXT NOT NULL,
    make             TEXT NOT NULL,
    model            TEXT NOT NULL,
    year_from        INTEGER,
    year_to          INTEGER,
    component        TEXT,
    manufacturer     TEXT,
    mfg_campaign_no  TEXT,
    vehicles_affected INTEGER,
    report_date      TEXT,
    summary          TEXT,
    consequence      TEXT,
    remedy           TEXT,
    notes            TEXT,
    park_it          INTEGER DEFAULT 0,
    park_outside     INTEGER DEFAULT 0,
    imported_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(campaign_no, make, model)
);
"""

DDL_RECALLS_FTS = """
CREATE VIRTUAL TABLE recalls_fts USING fts5(
    campaign_no,
    make,
    model,
    component,
    summary,
    consequence,
    remedy,
    content='nhtsa_recalls',
    content_rowid='id'
);
"""

DDL_RECALLS_IDX_VEHICLE = """
CREATE INDEX IF NOT EXISTS idx_recalls_vehicle
    ON nhtsa_recalls (make, model, year_from, year_to);
"""

DDL_RECALLS_IDX_COMPONENT = """
CREATE INDEX IF NOT EXISTS idx_recalls_component
    ON nhtsa_recalls (component);
"""

UPSERT_SQL = """
INSERT INTO nhtsa_recalls
    (campaign_no, make, model, year_from, year_to,
     component, manufacturer, mfg_campaign_no,
     vehicles_affected, report_date,
     summary, consequence, remedy, notes,
     park_it, park_outside)
VALUES
    (?, ?, ?, ?, ?,
     ?, ?, ?,
     ?, ?,
     ?, ?, ?, ?,
     ?, ?)
ON CONFLICT(campaign_no, make, model) DO UPDATE SET
    year_from        = MIN(year_from, excluded.year_from),
    year_to          = MAX(year_to, excluded.year_to),
    component        = COALESCE(excluded.component, component),
    manufacturer     = COALESCE(excluded.manufacturer, manufacturer),
    mfg_campaign_no  = COALESCE(excluded.mfg_campaign_no, mfg_campaign_no),
    vehicles_affected = COALESCE(excluded.vehicles_affected, vehicles_affected),
    report_date      = COALESCE(excluded.report_date, report_date),
    summary          = COALESCE(excluded.summary, summary),
    consequence      = COALESCE(excluded.consequence, consequence),
    remedy           = COALESCE(excluded.remedy, remedy),
    notes            = COALESCE(excluded.notes, notes),
    park_it          = MAX(park_it, excluded.park_it),
    park_outside     = MAX(park_outside, excluded.park_outside)
;
"""

# ---------------------------------------------------------------------------
# Model name normalization
# ---------------------------------------------------------------------------

# Cab designator suffixes (word-boundary aware)
_CAB_PATTERN = re.compile(
    r"\s+\b(?:REGULAR\s+CAB|CREW\s+CAB|SUPER\s+CREW|SUPERCAB|EXTENDED\s+CAB"
    r"|STANDARD\s+CAB|SUPER\s+CAB|DOUBLE\s+CAB|ACCESS\s+CAB|KING\s+CAB"
    r"|QUAD\s+CAB|CLUB\s+CAB)\b",
    re.IGNORECASE,
)

# Fuel/powertrain suffixes (trailing only)
_FUEL_PATTERN = re.compile(
    r"\s+\b(?:GAS|HEV|PHEV|BEV|EV|HYBRID|ENERGI|ELECTRIC|PLUGIN)\b$",
    re.IGNORECASE,
)

# Body style suffixes (trailing only)
_BODY_PATTERN = re.compile(
    r"\s+\b(?:SEDAN|HATCHBACK|HATCH|COUPE|CONVERTIBLE|WAGON)\b$",
    re.IGNORECASE,
)


def normalize_model(model: str) -> str:
    """
    Strip sub-variant suffixes from a complaints_fts model name so it matches
    the base model name expected by the NHTSA recalls API.

    Examples:
        "F-150 REGULAR CAB"  -> "F-150"
        "CIVIC SEDAN"        -> "CIVIC"
        "ESCAPE HEV"         -> "ESCAPE"
        "MUSTANG MACH-E"     -> "MUSTANG MACH-E"  (no matching suffix)
    """
    result = model.strip().upper()

    # Strip cab designators (can appear anywhere in the name)
    result = _CAB_PATTERN.sub("", result).strip()

    # Strip trailing fuel/powertrain suffix
    result = _FUEL_PATTERN.sub("", result).strip()

    # Strip trailing body style suffix
    result = _BODY_PATTERN.sub("", result).strip()

    # Guard: never return empty string
    if not result:
        return model.strip().upper()

    return result


# Checked AGENTS.md - implementing directly because this is a targeted bug fix (2 lines) to an existing script
def drop_and_recreate_schema(conn: sqlite3.Connection) -> None:
    """Drop existing nhtsa_recalls and recalls_fts tables and recreate with correct schema."""
    print("  Dropping existing nhtsa_recalls and recalls_fts tables...")
    conn.execute("DROP TABLE IF EXISTS recalls_fts")
    conn.execute("DROP TABLE IF EXISTS nhtsa_recalls")
    conn.execute(DDL_NHTSA_RECALLS.strip())
    conn.execute(DDL_RECALLS_FTS.strip())
    conn.execute(DDL_RECALLS_IDX_VEHICLE.strip())
    conn.execute(DDL_RECALLS_IDX_COMPONENT.strip())
    conn.commit()
    print("  Schema created: nhtsa_recalls (UNIQUE campaign_no, make, model) + recalls_fts (FTS5)")


# Checked AGENTS.md - implementing directly because this is a targeted bug fix to an existing data pipeline script
def ensure_schema(conn: sqlite3.Connection) -> None:
    """Create schema only if tables don't exist yet (non-destructive resume path)."""
    cur = conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='nhtsa_recalls'")
    if cur.fetchone() is None:
        conn.execute(DDL_NHTSA_RECALLS.strip())
        conn.execute(DDL_RECALLS_FTS.strip())
        conn.execute(DDL_RECALLS_IDX_VEHICLE.strip())
        conn.execute(DDL_RECALLS_IDX_COMPONENT.strip())
        conn.commit()
        print("  Schema created: nhtsa_recalls + recalls_fts (FTS5)")
    else:
        print("  Schema OK (existing table, resuming)")


# ---------------------------------------------------------------------------
# Checkpoint management
# ---------------------------------------------------------------------------

def load_checkpoint() -> set[str]:
    """Load completed make|model keys from checkpoint file."""
    if not CHECKPOINT_PATH.exists():
        return set()
    try:
        data = json.loads(CHECKPOINT_PATH.read_text())
        completed = set(data.get("completed", []))
        print(f"  Checkpoint loaded: {len(completed)} make/model combos already done")
        return completed
    except (json.JSONDecodeError, OSError) as e:
        print(f"  Warning: could not read checkpoint ({e}) — starting fresh")
        return set()


def save_checkpoint(completed: set[str]) -> None:
    """Persist completed set to checkpoint file."""
    try:
        CHECKPOINT_PATH.write_text(json.dumps({"completed": sorted(completed)}, indent=2))
    except OSError as e:
        print(f"  Warning: could not save checkpoint: {e}")


# ---------------------------------------------------------------------------
# Vehicle list
# ---------------------------------------------------------------------------

def get_vehicle_combos(conn: sqlite3.Connection, make_filter: Optional[str] = None,
                        test_mode: bool = False) -> list[tuple[str, str]]:
    """
    Return distinct (make, normalized_model) tuples from complaints_fts for years 2015-2025.
    Sub-variant suffixes (cab designators, fuel types, body styles) are stripped so the
    model names match what the NHTSA recalls API expects (e.g. "F-150" not "F-150 CREW CAB").
    """
    sql = """
        SELECT DISTINCT make, model
        FROM complaints_fts
        WHERE CAST(year AS INTEGER) BETWEEN 2015 AND 2025
    """
    params: list = []
    if make_filter:
        sql += " AND UPPER(make) = ?"
        params.append(make_filter.upper())
    elif test_mode:
        placeholders = ",".join("?" * len(TEST_MAKES))
        sql += f" AND UPPER(make) IN ({placeholders})"
        params.extend(sorted(TEST_MAKES))
    sql += " ORDER BY make, model"
    cur = conn.execute(sql, params)
    raw_rows = cur.fetchall()

    # Normalize model names and deduplicate
    seen: set[tuple[str, str]] = set()
    result: list[tuple[str, str]] = []
    for make, model in raw_rows:
        norm_model = normalize_model(model)
        key = (make, norm_model)
        if key not in seen:
            seen.add(key)
            result.append(key)
    return result


# ---------------------------------------------------------------------------
# API fetch
# ---------------------------------------------------------------------------

def fetch_recalls_for_year(make: str, model: str, year: int,
                            session: requests.Session) -> list[dict]:
    """
    Fetch all recalls for a specific make/model/year from NHTSA API.
    Returns list of result dicts, or empty list on error.
    """
    try:
        resp = session.get(
            NHTSA_API,
            params={"make": make, "model": model, "modelYear": str(year)},
            headers=REQUEST_HEADERS,
            timeout=15,
        )
        if resp.status_code == 404:
            return []          # no data for this combination — normal
        resp.raise_for_status()
        data = resp.json()
        return data.get("results") or []
    except requests.exceptions.Timeout:
        print(f"    TIMEOUT: {make} {model} {year} — skipping")
        return []
    except requests.exceptions.RequestException as e:
        print(f"    ERROR: {make} {model} {year} — {e}")
        return []
    except (json.JSONDecodeError, KeyError) as e:
        print(f"    PARSE ERROR: {make} {model} {year} — {e}")
        return []


def record_to_row(rec: dict, year: int) -> tuple:
    """Convert one API result dict to a parameter tuple for UPSERT_SQL."""
    campaign_no  = (rec.get("NHTSACampaignNumber") or "").strip()
    make         = (rec.get("Make") or "").strip().upper()
    model        = (rec.get("Model") or "").strip().upper()
    component    = (rec.get("Component") or "").strip()
    manufacturer = (rec.get("Manufacturer") or "").strip()
    report_date  = (rec.get("ReportReceivedDate") or "").strip()
    summary      = (rec.get("Summary") or "").strip()
    consequence  = (rec.get("Consequence") or "").strip()
    remedy       = (rec.get("Remedy") or "").strip()
    notes        = (rec.get("Notes") or "").strip()
    park_it      = 1 if rec.get("parkIt") else 0
    park_outside = 1 if rec.get("parkOutSide") else 0

    return (
        campaign_no, make, model,
        year, year,                 # year_from, year_to — upsert will expand the range
        component, manufacturer, None,   # mfg_campaign_no not in API response
        None, report_date,               # vehicles_affected not in API response
        summary, consequence, remedy, notes,
        park_it, park_outside,
    )


# ---------------------------------------------------------------------------
# FTS rebuild
# ---------------------------------------------------------------------------

def rebuild_fts(conn: sqlite3.Connection) -> None:
    """Populate recalls_fts from nhtsa_recalls content table."""
    # Checked AGENTS.md - implementing directly, no security concerns
    print("\n  Rebuilding recalls_fts index...")
    # DROP and recreate to avoid malformed virtual table issues
    conn.execute("DROP TABLE IF EXISTS recalls_fts")
    conn.execute("""
        CREATE VIRTUAL TABLE recalls_fts USING fts5(
            campaign_no, make, model, component, summary, consequence, remedy,
            content='nhtsa_recalls', content_rowid='id'
        )
    """)
    conn.execute("""
        INSERT INTO recalls_fts(rowid, campaign_no, make, model, component, summary, consequence, remedy)
        SELECT id, campaign_no, make, model, component, summary, consequence, remedy
        FROM nhtsa_recalls
    """)
    conn.commit()
    cur = conn.execute("SELECT COUNT(*) FROM recalls_fts")
    count = cur.fetchone()[0]
    print(f"  recalls_fts rebuilt: {count:,} rows indexed")


# ---------------------------------------------------------------------------
# Stats
# ---------------------------------------------------------------------------

def print_stats(conn: sqlite3.Connection) -> None:
    """Print completion statistics."""
    print("\n" + "=" * 60)
    print("IMPORT COMPLETE — STATISTICS")
    print("=" * 60)

    cur = conn.execute("SELECT COUNT(*) FROM nhtsa_recalls")
    total_rows = cur.fetchone()[0]
    print(f"  Total recall records:   {total_rows:,}")

    cur = conn.execute("SELECT COUNT(DISTINCT campaign_no) FROM nhtsa_recalls")
    unique_campaigns = cur.fetchone()[0]
    print(f"  Unique campaigns:       {unique_campaigns:,}")

    cur = conn.execute("SELECT COUNT(DISTINCT make || '|' || model) FROM nhtsa_recalls")
    unique_vehicles = cur.fetchone()[0]
    print(f"  Unique make/model:      {unique_vehicles:,}")

    cur = conn.execute("""
        SELECT make, COUNT(*) as cnt
        FROM nhtsa_recalls
        GROUP BY make
        ORDER BY cnt DESC
        LIMIT 15
    """)
    print("\n  Top makes by recall record count:")
    for row in cur.fetchall():
        print(f"    {row[0]:<25} {row[1]:>6,}")

    cur = conn.execute("""
        SELECT COUNT(*) FROM nhtsa_recalls WHERE park_it = 1
    """)
    park_it_count = cur.fetchone()[0] or 0
    if park_it_count:
        print(f"\n  Park-it safety recalls:   {park_it_count:,}")

    print("=" * 60)


# ---------------------------------------------------------------------------
# Main pipeline
# ---------------------------------------------------------------------------

def run_import(test_mode: bool = True, make_filter: Optional[str] = None,
               reset: bool = False) -> None:
    start = datetime.now()

    print("\nNHTSA Recalls API Import")
    print(f"  Mode:   {'TEST (3 makes, 3 years)' if test_mode and not make_filter else 'FULL'}")
    if make_filter:
        print(f"  Filter: make = {make_filter.upper()}")
    print(f"  DB:     {DB_PATH}")
    print(f"  Time:   {start.strftime('%Y-%m-%d %H:%M:%S')}")
    print()

    conn = sqlite3.connect(str(DB_PATH))
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA synchronous=NORMAL")
    conn.execute("PRAGMA cache_size=-32000")
    conn.execute("PRAGMA temp_store=MEMORY")

    # Checked AGENTS.md - direct fix: only drop table on --reset, otherwise resume safely
    # Step 1: schema — only drop/recreate on --reset; otherwise preserve existing data
    if reset:
        drop_and_recreate_schema(conn)
    else:
        ensure_schema(conn)

    # Step 2: gather vehicle list
    combos = get_vehicle_combos(conn, make_filter=make_filter, test_mode=test_mode)
    years = YEARS_TEST if (test_mode and not make_filter) else YEARS_FULL
    total_calls = len(combos) * len(years)
    print(f"  Vehicles: {len(combos)} make/model combos × {len(years)} years = {total_calls:,} API calls\n")

    # Step 3: load checkpoint (skip completed make/model combos)
    if reset and CHECKPOINT_PATH.exists():
        CHECKPOINT_PATH.unlink()
        print("  Checkpoint reset.\n")
    completed: set[str] = load_checkpoint() if not reset else set()

    # Step 4: fetch and insert
    session = requests.Session()
    api_call_count = 0
    inserted_count = 0
    error_count = 0
    skipped_combos = 0

    for make, model in combos:
        combo_key = f"{make}|{model}"

        if combo_key in completed:
            skipped_combos += 1
            continue

        combo_inserted = 0
        for year in years:
            results = fetch_recalls_for_year(make, model, year, session)
            api_call_count += 1

            for rec in results:
                campaign_no = (rec.get("NHTSACampaignNumber") or "").strip()
                if not campaign_no:
                    continue
                try:
                    conn.execute(UPSERT_SQL, record_to_row(rec, year))
                    combo_inserted += 1
                    inserted_count += 1
                except sqlite3.Error as e:
                    print(f"    DB ERROR ({make} {model} {year}): {e}")
                    error_count += 1

            # Rate limit between API calls
            time.sleep(RATE_LIMIT_SEC)

            if api_call_count % 50 == 0:
                conn.commit()
                elapsed = (datetime.now() - start).total_seconds()
                rate = api_call_count / elapsed if elapsed > 0 else 0
                eta_sec = (total_calls - api_call_count) / rate if rate > 0 else 0
                print(
                    f"  [{api_call_count:>5}/{total_calls}] "
                    f"{inserted_count:,} records | "
                    f"{rate:.1f} calls/s | "
                    f"ETA {int(eta_sec//60)}m {int(eta_sec%60)}s"
                )

        conn.commit()
        completed.add(combo_key)
        save_checkpoint(completed)

        if combo_inserted > 0:
            print(f"  {make} {model}: {combo_inserted} recall records")

    if skipped_combos:
        print(f"\n  Skipped {skipped_combos} already-completed combos (checkpoint)")

    # Step 5: rebuild FTS
    rebuild_fts(conn)

    # Step 6: stats
    print_stats(conn)

    elapsed = (datetime.now() - start).total_seconds()
    print(f"\n  API calls made: {api_call_count:,}  |  Errors: {error_count}  |  Time: {elapsed:.1f}s")
    if error_count:
        print(f"  Warning: {error_count} insert errors encountered — check output above")

    conn.close()


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Import NHTSA recall data from live API into automotive_complaints.db",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Verify pipeline (test mode — 3 makes, 3 years)
  .venv/bin/python3 scripts/import_nhtsa_recalls_api.py

  # Full run — all 264 make/model combos × 2015-2025
  .venv/bin/python3 scripts/import_nhtsa_recalls_api.py --full

  # Single make only
  .venv/bin/python3 scripts/import_nhtsa_recalls_api.py --full --make FORD

  # Full run, restart from scratch
  .venv/bin/python3 scripts/import_nhtsa_recalls_api.py --full --reset
        """,
    )
    parser.add_argument(
        "--full",
        action="store_true",
        default=False,
        help="Run full import (all 264 combos × 2015-2025). Default is test mode.",
    )
    parser.add_argument(
        "--make",
        type=str,
        default=None,
        help="Limit to a single make (e.g. --make FORD). Implies full year range.",
    )
    parser.add_argument(
        "--reset",
        action="store_true",
        default=False,
        help="Ignore checkpoint and start from scratch.",
    )
    args = parser.parse_args()

    # --make implies full year range but still scoped to one make
    test_mode = not args.full and args.make is None

    if test_mode:
        print("Running in TEST mode. Use --full for the complete import.")

    run_import(
        test_mode=test_mode,
        make_filter=args.make,
        reset=args.reset,
    )


if __name__ == "__main__":
    main()
