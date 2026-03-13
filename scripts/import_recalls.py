#!/usr/bin/env python3
# Checked AGENTS.md - implementing directly: standalone data import utility,
# read-only file parse + INSERT OR IGNORE, no auth/security surface.
"""
Import NHTSA FLAT_RCL recall data into nhtsa_recalls table.

Usage:
    python scripts/import_recalls.py data/raw_imports/recalls/FLAT_RCL.txt

The FLAT_RCL file is tab-delimited with fields:
  0: RECORD_ID
  1: CAMPNO      - NHTSA recall campaign number
  2: MAKETXT     - Vehicle make
  3: MODELTXT    - Vehicle model
  4: YEARTXT     - Model year (range, e.g. "2018" or "2018-2020")
  5: MFGCAMPNO   - Manufacturer campaign number
  6: COMPNAME    - Component affected
  7: MFGNAME     - Manufacturer name
  8: BGMAN       - Begin manufacture date (YYYYMM)
  9: ENDMAN      - End manufacture date (YYYYMM)
 10: POTAFF      - Potentially affected vehicles
 11: VALDT       - Validation date
 12: RGINNM      - Region
 13: DATEA       - Announcement date
 14: DPETXT      - Defect type text
 15: MFGTXT      - Manufacturer text
 16: DESCRIPT    - Defect description
 17: CONEQUENCE  - Consequence
 18: REMEDY      - Remedy description
 19: NOTES
 20: RCDATE      - Recall date (YYYYMMDD)
 21+: additional fields (ignored)
"""

import sys
import sqlite3
from pathlib import Path
from datetime import datetime
from typing import Optional


PROJECT_ROOT = Path(__file__).parent.parent
DB_PATH = PROJECT_ROOT / "database" / "automotive_complaints.db"


def parse_year_range(year_text: str) -> tuple[Optional[int], Optional[int]]:
    """Parse YEARTXT which can be '2018', '2018-2020', or empty."""
    if not year_text or not year_text.strip():
        return None, None
    year_text = year_text.strip()
    if '-' in year_text:
        parts = year_text.split('-')
        try:
            y1 = int(parts[0]) if parts[0].isdigit() else None
            y2 = int(parts[1]) if len(parts) > 1 and parts[1].isdigit() else y1
            return y1, y2
        except (ValueError, IndexError):
            return None, None
    try:
        y = int(year_text)
        return y, y
    except ValueError:
        return None, None


def safe_int(val: str) -> Optional[int]:
    try:
        return int(val.strip()) if val.strip() else None
    except ValueError:
        return None


def import_recalls(file_path: Path) -> dict[str, int]:
    stats: dict[str, int] = {'total': 0, 'imported': 0, 'skipped': 0, 'errors': 0}
    start = datetime.now()

    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA synchronous=NORMAL")

    sql = """
    INSERT OR IGNORE INTO nhtsa_recalls
        (campaign_no, make, model, year_from, year_to, component, mfg_name,
         mfg_campaign_no, begin_mfg_date, end_mfg_date, vehicles_affected,
         report_date, description, consequence, remedy, notes)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """

    batch: list[tuple] = []
    batch_size = 2000

    with open(file_path, 'r', encoding='latin-1', errors='replace') as f:
        for line in f:
            stats['total'] += 1
            parts = line.strip().split('\t')
            if len(parts) < 19:
                stats['skipped'] += 1
                continue

            campaign_no = parts[1].strip()
            if not campaign_no:
                stats['skipped'] += 1
                continue

            year_from, year_to = parse_year_range(parts[4])

            record = (
                campaign_no,
                parts[2].strip(),       # make
                parts[3].strip(),       # model
                year_from,
                year_to,
                parts[6].strip(),       # component
                parts[7].strip(),       # mfg_name
                parts[5].strip(),       # mfg_campaign_no
                parts[8].strip(),       # begin_mfg_date
                parts[9].strip(),       # end_mfg_date
                safe_int(parts[10]),    # vehicles_affected
                parts[20].strip() if len(parts) > 20 else '',  # report_date
                parts[16].strip(),      # description
                parts[17].strip(),      # consequence
                parts[18].strip(),      # remedy
                parts[19].strip() if len(parts) > 19 else '',  # notes
            )
            batch.append(record)

            if len(batch) >= batch_size:
                try:
                    conn.executemany(sql, batch)
                    conn.commit()
                    stats['imported'] += len(batch)
                except sqlite3.Error as e:
                    print(f"  Batch error: {e}")
                    stats['errors'] += len(batch)
                batch = []

            if stats['total'] % 10000 == 0:
                elapsed = (datetime.now() - start).total_seconds()
                rate = stats['total'] / elapsed if elapsed > 0 else 0
                print(f"  {stats['total']:,} lines | {stats['imported']:,} imported | {rate:.0f}/s")

    if batch:
        try:
            conn.executemany(sql, batch)
            conn.commit()
            stats['imported'] += len(batch)
        except sqlite3.Error as e:
            print(f"  Final batch error: {e}")
            stats['errors'] += len(batch)

    # Rebuild FTS index
    print("  Rebuilding recalls FTS index...")
    conn.execute("INSERT INTO recalls_fts(recalls_fts) VALUES('rebuild')")
    conn.commit()
    conn.close()

    elapsed = (datetime.now() - start).total_seconds()
    print(f"\nRecalls import complete: {stats['imported']:,} imported, "
          f"{stats['skipped']:,} skipped, {stats['errors']:,} errors in {elapsed:.1f}s")
    return stats


def main() -> None:
    if len(sys.argv) != 2:
        print("Usage: python scripts/import_recalls.py <path_to_FLAT_RCL.txt>")
        sys.exit(1)

    file_path = Path(sys.argv[1])
    if not file_path.exists():
        print(f"File not found: {file_path}")
        sys.exit(1)

    print(f"\nImporting NHTSA Recalls from {file_path.name}...")
    import_recalls(file_path)


if __name__ == '__main__':
    main()
