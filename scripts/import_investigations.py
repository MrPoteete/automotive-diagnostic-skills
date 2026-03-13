#!/usr/bin/env python3
# Checked AGENTS.md - implementing directly: standalone data import utility,
# read-only file parse + INSERT OR IGNORE, no auth/security surface.
"""
Import NHTSA FLAT_INV investigation data into nhtsa_investigations table.

Usage:
    python scripts/import_investigations.py data/raw_imports/investigations/FLAT_INV.txt

FLAT_INV is tab-delimited with NO header row, 11 fields:
  0: NHTSA_ID   - investigation ID (prefix = type: AQ/DP/PE/EA/RQ)
  1: MAKE       - vehicle make (or equipment mfr code for non-vehicle)
  2: MODEL      - vehicle model
  3: YEAR       - model year (single year; '9999' or non-numeric = non-vehicle)
  4: COMPONENT  - system/component affected
  5: MFG_NAME   - manufacturer full name
  6: OPEN_DATE  - YYYYMMDD
  7: CLOSE_DATE - YYYYMMDD (empty if still open)
  8: RELATED_ID - petition/recall ID (often empty)
  9: SUBJECT    - investigation subject/title
 10: SUMMARY    - full investigation narrative
"""

import sys
import sqlite3
from pathlib import Path
from datetime import datetime
from typing import Optional


PROJECT_ROOT = Path(__file__).parent.parent
DB_PATH = PROJECT_ROOT / "database" / "automotive_complaints.db"


def inv_type_from_id(inv_id: str) -> str:
    """Derive investigation type from ID prefix."""
    prefix = inv_id[:2].upper()
    types = {
        'PE': 'PE',   # Preliminary Evaluation
        'EA': 'EA',   # Engineering Analysis
        'DP': 'DP',   # Defect Petition
        'AQ': 'AQ',   # Audit Query
        'RQ': 'RQ',   # Recall Query
        'IN': 'IN',   # Investigation
    }
    return types.get(prefix, prefix)


def parse_year(val: str) -> Optional[int]:
    """Parse year string; return None for non-vehicle codes like 9005, 9999."""
    try:
        y = int(val.strip())
        return y if 1950 <= y <= 2030 else None
    except (ValueError, AttributeError):
        return None


def import_investigations(file_path: Path) -> dict[str, int]:
    stats: dict[str, int] = {'total': 0, 'imported': 0, 'skipped': 0}
    start = datetime.now()

    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA synchronous=NORMAL")

    sql = """
    INSERT OR IGNORE INTO nhtsa_investigations
        (inv_id, inv_type, make, model, year_from, year_to, component,
         summary, open_date, close_date, status)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """

    batch: list[tuple] = []
    batch_size = 2000

    with open(file_path, 'r', encoding='latin-1', errors='replace') as f:
        for line in f:
            stats['total'] += 1
            parts = line.strip().split('\t')

            if len(parts) < 9:
                stats['skipped'] += 1
                continue

            inv_id = parts[0].strip()
            if not inv_id:
                stats['skipped'] += 1
                continue

            year = parse_year(parts[3])
            close_date = parts[7].strip()
            status = 'CLOSED' if close_date else 'OPEN'

            # Combine subject + summary for the summary field
            subject = parts[9].strip() if len(parts) > 9 else ''
            summary = parts[10].strip() if len(parts) > 10 else ''
            full_summary = f"{subject}: {summary}" if subject and summary else (subject or summary)

            record = (
                inv_id,
                inv_type_from_id(inv_id),
                parts[1].strip(),   # make
                parts[2].strip(),   # model
                year,               # year_from
                year,               # year_to (same — single year in file)
                parts[4].strip(),   # component
                full_summary,
                parts[6].strip(),   # open_date
                close_date,
                status,
            )
            batch.append(record)

            if len(batch) >= batch_size:
                try:
                    conn.executemany(sql, batch)
                    conn.commit()
                    stats['imported'] += len(batch)
                except sqlite3.Error as e:
                    print(f"  Batch error: {e}")
                batch = []

            if stats['total'] % 50000 == 0:
                elapsed = (datetime.now() - start).total_seconds()
                print(f"  {stats['total']:,} lines | {stats['imported']:,} imported | {elapsed:.1f}s")

    if batch:
        try:
            conn.executemany(sql, batch)
            conn.commit()
            stats['imported'] += len(batch)
        except sqlite3.Error as e:
            print(f"  Final batch error: {e}")

    conn.close()
    elapsed = (datetime.now() - start).total_seconds()
    print(f"\nInvestigations import complete: {stats['imported']:,} imported in {elapsed:.1f}s")
    return stats


def main() -> None:
    if len(sys.argv) != 2:
        print("Usage: python scripts/import_investigations.py <path_to_FLAT_INV.txt>")
        sys.exit(1)

    file_path = Path(sys.argv[1])
    if not file_path.exists():
        print(f"File not found: {file_path}")
        sys.exit(1)

    print(f"\nImporting NHTSA Investigations from {file_path.name}...")
    import_investigations(file_path)


if __name__ == '__main__':
    main()
