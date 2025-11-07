#!/usr/bin/env python3
"""
Import NHTSA FLAT_CMPL complaint data into SQLite database.

This script processes the large NHTSA complaint file (1.5GB+) using
streaming to avoid memory issues. It parses tab-delimited records and
imports them into the nhtsa_complaints table.

Usage:
    python scripts/import_nhtsa_complaints.py data/raw_imports/FLAT_CMPL.txt/FLAT_CMPL.txt

Features:
- Streams file (never loads all 1.5GB into memory)
- Batch inserts for performance (1000 records at a time)
- Progress tracking
- Error handling with detailed logging
- Data validation
"""

import sys
import sqlite3
import re
from pathlib import Path
from datetime import datetime
from typing import Dict, Optional, List, Tuple


# Field positions in the tab-delimited file
# Based on NHTSA FLAT_CMPL file format
FIELD_MAP = {
    'record_number': 0,
    'complaint_id': 1,
    'manufacturer_name': 2,
    'make': 3,
    'model': 4,
    'year': 5,
    'fire_flag': 6,
    'failure_date': 7,
    'crash_flag': 8,
    'num_injuries': 9,
    'num_deaths': 10,
    'component_description': 11,
    'city': 12,
    'state': 13,
    'vin_partial': 14,
    'date_received': 15,
    'date_opened': 16,
    # Field 17-18 appear empty in samples
    'complaint_narrative': 19,
    # Additional fields may exist but these are the critical ones
}


class NHTSAComplaintParser:
    """Parse NHTSA FLAT_CMPL complaint records."""

    def __init__(self, db_path: str):
        """
        Initialize parser with database connection.

        Args:
            db_path: Path to SQLite database file
        """
        self.db_path = Path(db_path)
        self.conn = None
        self.cursor = None
        self.stats = {
            'total_lines': 0,
            'imported': 0,
            'skipped': 0,
            'errors': 0,
        }

    def connect_db(self):
        """Connect to database and ensure schema exists."""
        self.conn = sqlite3.connect(self.db_path)
        self.cursor = self.conn.cursor()

        # Load and execute schema
        schema_path = self.db_path.parent / 'schema_nhtsa_complaints.sql'
        if schema_path.exists():
            with open(schema_path, 'r') as f:
                self.conn.executescript(f.read())
            print(f"✓ Schema loaded from {schema_path.name}")
        else:
            print(f"⚠️  Schema file not found: {schema_path}")
            print("   Assuming tables already exist...")

    def parse_date(self, date_str: str) -> Optional[str]:
        """
        Parse NHTSA date format (YYYYMMDD) to ISO format (YYYY-MM-DD).

        Args:
            date_str: Date in YYYYMMDD format

        Returns:
            Date in YYYY-MM-DD format or None if invalid
        """
        if not date_str or len(date_str) != 8:
            return None

        try:
            year = int(date_str[0:4])
            month = int(date_str[4:6])
            day = int(date_str[6:8])

            # Basic validation
            if not (1900 <= year <= 2100 and 1 <= month <= 12 and 1 <= day <= 31):
                return None

            return f"{year:04d}-{month:02d}-{day:02d}"
        except (ValueError, IndexError):
            return None

    def parse_line(self, line: str) -> Optional[Dict]:
        """
        Parse a single tab-delimited line.

        Args:
            line: Raw line from file

        Returns:
            Dict with parsed fields or None if invalid
        """
        fields = line.strip().split('\t')

        # Need minimum number of fields
        if len(fields) < 20:
            return None

        try:
            # Parse required fields
            complaint_id = int(fields[FIELD_MAP['complaint_id']])
            make = fields[FIELD_MAP['make']].strip()
            model = fields[FIELD_MAP['model']].strip()
            year = int(fields[FIELD_MAP['year']])

            # Skip if missing critical data
            if not make or not model or year < 1900:
                return None

            # Parse optional fields
            record = {
                'record_number': self._safe_int(fields[FIELD_MAP['record_number']]),
                'complaint_id': complaint_id,
                'manufacturer_name': fields[FIELD_MAP['manufacturer_name']].strip(),
                'make': make,
                'model': model,
                'year': year,
                'fire_flag': self._normalize_flag(fields[FIELD_MAP['fire_flag']]),
                'failure_date': self.parse_date(fields[FIELD_MAP['failure_date']]),
                'crash_flag': self._normalize_flag(fields[FIELD_MAP['crash_flag']]),
                'num_injuries': self._safe_int(fields[FIELD_MAP['num_injuries']], 0),
                'num_deaths': self._safe_int(fields[FIELD_MAP['num_deaths']], 0),
                'component_description': fields[FIELD_MAP['component_description']].strip(),
                'city': fields[FIELD_MAP['city']].strip(),
                'state': fields[FIELD_MAP['state']].strip(),
                'vin_partial': fields[FIELD_MAP['vin_partial']].strip(),
                'date_received': self.parse_date(fields[FIELD_MAP['date_received']]),
                'date_opened': self.parse_date(fields[FIELD_MAP['date_opened']]),
                'complaint_narrative': fields[FIELD_MAP['complaint_narrative']].strip() if len(fields) > FIELD_MAP['complaint_narrative'] else '',
            }

            return record

        except (ValueError, IndexError) as e:
            # Skip malformed lines
            return None

    def _safe_int(self, value: str, default: int = 0) -> int:
        """Safely convert string to int."""
        try:
            return int(value.strip()) if value.strip() else default
        except ValueError:
            return default

    def _normalize_flag(self, value: str) -> str:
        """Normalize Y/N flags."""
        v = value.strip().upper()
        return v if v in ('Y', 'N') else ''

    def insert_batch(self, records: List[Dict]):
        """
        Insert a batch of records into database.

        Args:
            records: List of parsed record dicts
        """
        if not records:
            return

        sql = """
        INSERT OR IGNORE INTO nhtsa_complaints (
            record_number, complaint_id, manufacturer_name, make, model, year,
            fire_flag, failure_date, crash_flag, num_injuries, num_deaths,
            component_description, city, state, vin_partial,
            date_received, date_opened, complaint_narrative
        ) VALUES (
            :record_number, :complaint_id, :manufacturer_name, :make, :model, :year,
            :fire_flag, :failure_date, :crash_flag, :num_injuries, :num_deaths,
            :component_description, :city, :state, :vin_partial,
            :date_received, :date_opened, :complaint_narrative
        )
        """

        try:
            self.cursor.executemany(sql, records)
            self.conn.commit()
            self.stats['imported'] += len(records)
        except sqlite3.Error as e:
            print(f"❌ Database error: {e}")
            self.stats['errors'] += len(records)
            self.conn.rollback()

    def process_file(self, file_path: Path, batch_size: int = 1000):
        """
        Process the entire complaints file in streaming mode.

        Args:
            file_path: Path to FLAT_CMPL.txt file
            batch_size: Number of records to batch before inserting
        """
        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")

        print(f"\n{'='*80}")
        print(f"IMPORTING NHTSA COMPLAINTS")
        print(f"{'='*80}")
        print(f"Source: {file_path.name}")
        print(f"Database: {self.db_path}")
        print(f"Batch size: {batch_size:,} records\n")

        batch = []
        start_time = datetime.now()

        # Determine encoding (try UTF-8 first, fallback to Latin-1)
        encodings = ['utf-8', 'latin-1', 'cp1252']
        file_handle = None

        for encoding in encodings:
            try:
                file_handle = open(file_path, 'r', encoding=encoding, errors='replace')
                # Try reading first line
                file_handle.readline()
                file_handle.seek(0)
                print(f"✓ Using encoding: {encoding}\n")
                break
            except UnicodeDecodeError:
                if file_handle:
                    file_handle.close()
                continue

        if not file_handle:
            raise ValueError("Could not determine file encoding")

        try:
            for line in file_handle:
                self.stats['total_lines'] += 1

                # Parse line
                record = self.parse_line(line)

                if record:
                    batch.append(record)
                else:
                    self.stats['skipped'] += 1

                # Insert batch when full
                if len(batch) >= batch_size:
                    self.insert_batch(batch)
                    batch = []

                    # Progress update every 10k lines
                    if self.stats['total_lines'] % 10000 == 0:
                        elapsed = (datetime.now() - start_time).total_seconds()
                        rate = self.stats['total_lines'] / elapsed if elapsed > 0 else 0
                        print(f"  Processed: {self.stats['total_lines']:,} lines "
                              f"| Imported: {self.stats['imported']:,} records "
                              f"| Rate: {rate:,.0f} lines/sec")

            # Insert remaining records
            if batch:
                self.insert_batch(batch)

        finally:
            file_handle.close()

        # Final statistics
        elapsed = (datetime.now() - start_time).total_seconds()
        print(f"\n{'='*80}")
        print(f"IMPORT COMPLETE")
        print(f"{'='*80}")
        print(f"Total lines processed: {self.stats['total_lines']:,}")
        print(f"Records imported:      {self.stats['imported']:,}")
        print(f"Records skipped:       {self.stats['skipped']:,}")
        print(f"Errors:                {self.stats['errors']:,}")
        print(f"Time elapsed:          {elapsed:.1f} seconds")
        print(f"Processing rate:       {self.stats['total_lines']/elapsed:,.0f} lines/sec")
        print()

    def close(self):
        """Close database connection."""
        if self.conn:
            self.conn.close()


def main():
    if len(sys.argv) != 2:
        print("Usage: python import_nhtsa_complaints.py <path_to_FLAT_CMPL.txt>")
        print("\nExample:")
        print("  python scripts/import_nhtsa_complaints.py data/raw_imports/FLAT_CMPL.txt/FLAT_CMPL.txt")
        sys.exit(1)

    file_path = Path(sys.argv[1])
    db_path = Path('database/automotive_diagnostics.db')

    # Ensure database directory exists
    db_path.parent.mkdir(parents=True, exist_ok=True)

    parser = NHTSAComplaintParser(str(db_path))

    try:
        parser.connect_db()
        parser.process_file(file_path, batch_size=1000)
    except KeyboardInterrupt:
        print("\n\n⚠️  Import interrupted by user")
        print(f"   Imported {parser.stats['imported']:,} records before stopping")
    except Exception as e:
        print(f"\n❌ Error: {e}")
        sys.exit(1)
    finally:
        parser.close()


if __name__ == '__main__':
    main()
