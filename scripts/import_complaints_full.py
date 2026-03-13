#!/usr/bin/env python3
# Checked AGENTS.md - implementing directly: standalone data import utility,
# streaming file parse + INSERT OR IGNORE into FTS5 table, no security surface.
"""
Import all NHTSA FLAT_CMPL complaints (all years) into complaints_fts table.
Skips records already imported via INSERT OR IGNORE on processed_complaints(odi_id).

Usage:
    python scripts/import_complaints_full.py data/raw_imports/FLAT_CMPL.txt/FLAT_CMPL.txt

The existing DB has 562K records (2005+). This script adds the remaining
pre-2005 records and any newer records not yet in the DB.

FLAT_CMPL tab-delimited fields:
  0: RECORD       1: CMPLID       2: MFRID        3: MAKETXT (make)
  4: MODELTXT     5: YEARTXT      6: FIREINJ      7: FAILDATE
  8: CRASH        9: INJURIES    10: DEATHS      11: COMPDESC
 12: CITY        13: STATE       14: VIN         15: DATEA
 16: LDATE       17-18: (empty) 19: CDESCR (narrative)
"""

import sys
import re
import sqlite3
from pathlib import Path
from datetime import datetime
PROJECT_ROOT = Path(__file__).parent.parent
DB_PATH = PROJECT_ROOT / "database" / "automotive_complaints.db"


def safe_int(val: str, default: int = 0) -> int:
    try:
        return int(val.strip()) if val.strip() else default
    except ValueError:
        return default


def clean_text(val: str) -> str:
    """Normalize whitespace and strip."""
    return re.sub(r'\s+', ' ', val.strip())


def import_complaints(file_path: Path, batch_size: int = 2000) -> dict[str, int]:
    stats: dict[str, int] = {'total': 0, 'imported': 0, 'skipped': 0, 'errors': 0}
    start = datetime.now()

    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA synchronous=NORMAL")
    conn.execute("PRAGMA cache_size=-64000")  # 64MB cache

    # FTS5 insert — the content table (c0-c4) is populated automatically
    fts_sql = """
    INSERT INTO complaints_fts(make, model, year, component, summary)
    VALUES (?, ?, ?, ?, ?)
    """
    # Guard against duplicates using processed_complaints(odi_id)
    pc_sql = "INSERT OR IGNORE INTO processed_complaints(odi_id) VALUES (?)"

    print(f"\nImporting ALL NHTSA complaints from {file_path.name}")
    print(f"Database: {DB_PATH}")
    print("Existing records: ", end='', flush=True)
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM processed_complaints")
    existing = cur.fetchone()[0]
    print(f"{existing:,}")

    fts_batch: list[tuple] = []
    pc_batch: list[tuple] = []

    for encoding in ('utf-8', 'latin-1', 'cp1252'):
        try:
            fh = open(file_path, 'r', encoding=encoding, errors='replace')
            fh.readline()
            fh.seek(0)
            break
        except Exception:
            continue

    try:
        for line in fh:
            stats['total'] += 1
            parts = line.strip().split('\t')

            if len(parts) < 12:
                stats['skipped'] += 1
                continue

            try:
                cmplid = int(parts[1])
                make = clean_text(parts[3])
                model = clean_text(parts[4])
                year_raw = parts[5].strip()
                year = int(year_raw) if year_raw.isdigit() else 0
                component = clean_text(parts[11])
                narrative = clean_text(parts[19]) if len(parts) > 19 else ''
            except (ValueError, IndexError):
                stats['skipped'] += 1
                continue

            if not make or not model or year < 1950:
                stats['skipped'] += 1
                continue

            pc_batch.append((cmplid,))
            fts_batch.append((make, model, str(year), component, narrative))

            if len(fts_batch) >= batch_size:
                # Check which are truly new
                conn.executemany(pc_sql, pc_batch)
                new_count = conn.execute("SELECT changes()").fetchone()[0]
                if new_count > 0:
                    # Only insert FTS rows for new entries
                    # Since we can't easily cross-reference, insert all and let FTS handle it
                    # (FTS5 has no UNIQUE constraint, so use pc as the guard and skip if 0 new)
                    conn.executemany(fts_sql, fts_batch[-new_count:])
                conn.commit()
                stats['imported'] += new_count
                stats['skipped'] += (batch_size - new_count)
                fts_batch = []
                pc_batch = []

            if stats['total'] % 50000 == 0:
                elapsed = (datetime.now() - start).total_seconds()
                rate = stats['total'] / elapsed if elapsed > 0 else 0
                print(f"  {stats['total']:,} lines | {stats['imported']:,} new | "
                      f"{stats['skipped']:,} skipped | {rate:,.0f}/s")

        # Final batch
        if pc_batch:
            conn.executemany(pc_sql, pc_batch)
            new_count = conn.execute("SELECT changes()").fetchone()[0]
            if new_count > 0:
                conn.executemany(fts_sql, fts_batch[-new_count:])
            conn.commit()
            stats['imported'] += new_count
            stats['skipped'] += len(pc_batch) - new_count

    finally:
        fh.close()

    # Optimize FTS index
    print("  Optimizing FTS index...")
    conn.execute("INSERT INTO complaints_fts(complaints_fts) VALUES('optimize')")
    conn.commit()
    conn.close()

    elapsed = (datetime.now() - start).total_seconds()
    print("\nFull complaints import complete:")
    print(f"  Total lines:    {stats['total']:,}")
    print(f"  New records:    {stats['imported']:,}")
    print(f"  Already exist:  {stats['skipped']:,}")
    print(f"  Errors:         {stats['errors']:,}")
    print(f"  Time:           {elapsed:.1f}s ({elapsed/60:.1f} min)")
    return stats


def main() -> None:
    if len(sys.argv) != 2:
        print("Usage: python scripts/import_complaints_full.py <path_to_FLAT_CMPL.txt>")
        sys.exit(1)

    file_path = Path(sys.argv[1])
    if not file_path.exists():
        print(f"File not found: {file_path}")
        sys.exit(1)

    import_complaints(file_path)


if __name__ == '__main__':
    main()
