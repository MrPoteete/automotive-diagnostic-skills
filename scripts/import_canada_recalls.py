#!/usr/bin/env python3
# Checked AGENTS.md - implementing directly: standalone data import utility,
# CSV parse + INSERT OR IGNORE, no auth/security surface.
"""
Import Transport Canada vehicle recall data into canada_recalls table.

Usage:
    python scripts/import_canada_recalls.py data/raw_imports/canada/vrdb_full_monthly.csv

Source: https://opendatatc.tc.canada.ca/vrdb_full_monthly.csv
License: Open Government Licence - Canada (attribution required)

CSV column headers (quoted):
  RECALL_NUMBER_NUM  - recall ID
  YEAR               - single model year
  MANUFACTURER_RECALL_NO_TXT - mfr's own recall number
  CATEGORY_ETXT      - vehicle category (Car, Truck, etc.)
  MAKE_NAME_NM       - vehicle make
  MODEL_NAME_NM      - vehicle model
  UNIT_AFFECTED_NBR  - units affected
  SYSTEM_TYPE_ETXT   - system affected
  COMMENT_ETXT       - English description/consequence/remedy (combined)
  RECALL_DATE_DTE    - date of recall (YYYY-MM-DD)
"""

import sys
import csv
import sqlite3
from pathlib import Path
from datetime import datetime
from typing import Optional


PROJECT_ROOT = Path(__file__).parent.parent
DB_PATH = PROJECT_ROOT / "database" / "automotive_complaints.db"


def safe_int(val: str) -> Optional[int]:
    try:
        cleaned = val.strip().replace(',', '')
        return int(float(cleaned)) if cleaned else None
    except (ValueError, TypeError):
        return None


def import_canada_recalls(file_path: Path) -> dict[str, int]:
    stats: dict[str, int] = {'total': 0, 'imported': 0, 'skipped': 0}
    start = datetime.now()

    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA synchronous=NORMAL")

    sql = """
    INSERT OR IGNORE INTO canada_recalls
        (recall_no, make, model, year_from, year_to, system,
         description, consequence, remedy, recall_date)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """

    batch: list[tuple] = []
    batch_size = 2000

    # TC CSV is UTF-8 with BOM
    with open(file_path, 'r', encoding='utf-8-sig', errors='replace', newline='') as f:
        reader = csv.DictReader(f)
        print(f"  Columns: {list(reader.fieldnames or [])[:10]}")

        for row in reader:
            stats['total'] += 1

            recall_no = row.get('RECALL_NUMBER_NUM', '').strip()
            make = row.get('MAKE_NAME_NM', '').strip()
            model = row.get('MODEL_NAME_NM', '').strip()

            if not recall_no or not make:
                stats['skipped'] += 1
                continue

            year = safe_int(row.get('YEAR', ''))
            description = row.get('COMMENT_ETXT', '').strip()

            record = (
                recall_no,
                make.upper(),
                model.upper(),
                year,           # year_from = year (single year in TC data)
                year,           # year_to = year
                row.get('SYSTEM_TYPE_ETXT', '').strip(),
                description,
                '',             # consequence not separate in TC data
                '',             # remedy not separate in TC data
                row.get('RECALL_DATE_DTE', '').strip(),
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
                print(f"  {stats['total']:,} rows | {stats['imported']:,} imported")

    if batch:
        try:
            conn.executemany(sql, batch)
            conn.commit()
            stats['imported'] += len(batch)
        except sqlite3.Error as e:
            print(f"  Final batch error: {e}")

    conn.close()
    elapsed = (datetime.now() - start).total_seconds()
    print(f"\nCanada recalls import complete: {stats['imported']:,} imported in {elapsed:.1f}s")
    return stats


def main() -> None:
    if len(sys.argv) != 2:
        print("Usage: python scripts/import_canada_recalls.py <path_to_vrdb_full_monthly.csv>")
        sys.exit(1)

    file_path = Path(sys.argv[1])
    if not file_path.exists():
        print(f"File not found: {file_path}")
        sys.exit(1)

    print(f"\nImporting Transport Canada recalls from {file_path.name}...")
    import_canada_recalls(file_path)


if __name__ == '__main__':
    main()
