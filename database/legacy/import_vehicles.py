#!/usr/bin/env python3
"""
Import vehicle data from make/model/year/engine files into SQLite database.
Handles the format from NHTSA vehicle database exports.
"""

import sqlite3
import re
import os
from pathlib import Path

class VehicleImporter:
    """Import vehicle data from text files."""

    def __init__(self, db_path="automotive_diagnostics.db"):
        """
        Initialize vehicle importer.

        Args:
            db_path: Path to SQLite database
        """
        self.db_path = db_path
        self.conn = None

    def connect(self):
        """Connect to database."""
        self.conn = sqlite3.connect(self.db_path)
        self.conn.execute("PRAGMA foreign_keys = ON")
        return self.conn

    def disconnect(self):
        """Close database connection."""
        if self.conn:
            self.conn.close()
            self.conn = None

    def parse_engine(self, engine_str):
        """
        Parse engine string to extract displacement and cylinders.

        Args:
            engine_str: Engine string like "3.5/6" or "3.5L V6"

        Returns:
            tuple: (displacement in liters, cylinder count)

        Examples:
            "3.5/6" -> (3.5, 6)
            "2.0L 4-Cyl" -> (2.0, 4)
            "5.7L HEMI V8" -> (5.7, 8)
        """
        if not engine_str or engine_str.strip() == '':
            return (None, None)

        # Pattern 1: "3.5/6" format
        match = re.match(r'(\d+\.\d+)/(\d+)', engine_str)
        if match:
            displacement = float(match.group(1))
            cylinders = int(match.group(2))
            return (displacement, cylinders)

        # Pattern 2: "3.5L" or "3.5 L" format
        match = re.search(r'(\d+\.\d+)\s*L', engine_str, re.IGNORECASE)
        if match:
            displacement = float(match.group(1))
        else:
            displacement = None

        # Extract cylinders: "V6", "6-Cyl", "6 Cylinder", etc.
        cyl_match = re.search(r'V?(\d+)[\s-]?(Cyl|Cylinder)?', engine_str, re.IGNORECASE)
        if cyl_match:
            cylinders = int(cyl_match.group(1))
        else:
            cylinders = None

        return (displacement, cylinders)

    def import_from_file(self, file_path, year=None):
        """
        Import vehicles from a pipe-delimited text file.

        Expected format:
        | Make | Model | Year | Engine Size |
        | FORD | F-150 | 2020 | 3.5/6 |

        Args:
            file_path: Path to vehicle data file
            year: Override year (if file contains multiple years or year column is missing)

        Returns:
            dict: Import statistics
        """
        if not os.path.exists(file_path):
            print(f"[ERROR] File not found: {file_path}")
            return None

        print(f"\n[IMPORT] Processing file: {file_path}")

        # Read file
        with open(file_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()

        total_lines = len(lines)
        print(f"[INFO] Total lines: {total_lines:,}")

        # Parse vehicles
        vehicles = []
        skipped = 0

        for line_num, line in enumerate(lines, 1):
            # Skip empty lines
            if not line.strip():
                continue

            # Check for header row
            if '| Make |' in line or '| :---' in line:
                continue

            # Check for category headers (e.g., | **TWO-SEATER CARS** | | | |)
            if '**' in line:
                continue

            # Parse pipe-delimited line
            parts = [p.strip() for p in line.split('|')]

            # Remove empty first and last elements (from leading/trailing pipes)
            if parts and parts[0] == '':
                parts = parts[1:]
            if parts and parts[-1] == '':
                parts = parts[:-1]

            # Expect: Make, Model, Year, Engine
            if len(parts) != 4:
                skipped += 1
                continue

            make, model, year_str, engine = parts

            # Skip if make is empty
            if not make or make == '':
                skipped += 1
                continue

            # Determine year
            if year:
                vehicle_year = year
            elif year_str and year_str.isdigit():
                vehicle_year = int(year_str)
            else:
                skipped += 1
                continue

            # Parse engine
            displacement, cylinders = self.parse_engine(engine)

            # Create vehicle record
            vehicle = {
                'make': make,
                'model': model,
                'year': vehicle_year,
                'engine': engine,
                'displacement': displacement,
                'cylinders': cylinders
            }

            vehicles.append(vehicle)

        print(f"[INFO] Parsed vehicles: {len(vehicles):,}")
        print(f"[INFO] Skipped lines: {skipped:,}")

        # Insert into database
        if not self.conn:
            self.connect()

        cursor = self.conn.cursor()

        inserted = 0
        duplicates = 0
        errors = 0

        for vehicle in vehicles:
            try:
                cursor.execute("""
                    INSERT INTO vehicles (
                        make, model, year, engine,
                        engine_displacement, engine_cylinders
                    ) VALUES (?, ?, ?, ?, ?, ?)
                """, (
                    vehicle['make'],
                    vehicle['model'],
                    vehicle['year'],
                    vehicle['engine'],
                    vehicle['displacement'],
                    vehicle['cylinders']
                ))
                inserted += 1

            except sqlite3.IntegrityError:
                # Duplicate vehicle (make/model/year/engine already exists)
                duplicates += 1

            except sqlite3.Error as e:
                print(f"[ERROR] Failed to insert {vehicle['make']} {vehicle['model']} {vehicle['year']}: {e}")
                errors += 1

        self.conn.commit()

        # Print statistics
        print("\n[STATS] Import Summary")
        print(f"  Inserted:   {inserted:>8,}")
        print(f"  Duplicates: {duplicates:>8,}")
        print(f"  Errors:     {errors:>8,}")
        print(f"  Total:      {len(vehicles):>8,}")

        return {
            'inserted': inserted,
            'duplicates': duplicates,
            'errors': errors,
            'total': len(vehicles)
        }

    def import_from_directory(self, directory_path, pattern="*.txt"):
        """
        Import vehicles from all matching files in a directory.

        Args:
            directory_path: Path to directory containing vehicle files
            pattern: Glob pattern for files (default: *.txt)

        Returns:
            dict: Aggregated statistics
        """
        directory = Path(directory_path)

        if not directory.exists():
            print(f"[ERROR] Directory not found: {directory_path}")
            return None

        # Find all matching files
        files = list(directory.glob(pattern))

        if not files:
            print(f"[WARN] No files found matching pattern: {pattern}")
            return None

        print(f"\n[IMPORT] Found {len(files)} files to import")

        total_stats = {
            'inserted': 0,
            'duplicates': 0,
            'errors': 0,
            'total': 0,
            'files_processed': 0
        }

        # Import each file
        for file_path in sorted(files):
            # Extract year from filename if present (e.g., "2005_Make_Model.txt")
            year_match = re.match(r'(\d{4})_', file_path.name)
            year = int(year_match.group(1)) if year_match else None

            stats = self.import_from_file(str(file_path), year=year)

            if stats:
                total_stats['inserted'] += stats['inserted']
                total_stats['duplicates'] += stats['duplicates']
                total_stats['errors'] += stats['errors']
                total_stats['total'] += stats['total']
                total_stats['files_processed'] += 1

        # Print total statistics
        print("\n[SUMMARY] Total Import Results")
        print("=" * 50)
        print(f"Files processed: {total_stats['files_processed']}")
        print(f"Total inserted:  {total_stats['inserted']:,}")
        print(f"Total duplicates: {total_stats['duplicates']:,}")
        print(f"Total errors:    {total_stats['errors']:,}")
        print(f"Grand total:     {total_stats['total']:,}")
        print("=" * 50)

        return total_stats

    def get_vehicle_stats(self):
        """Get statistics about vehicles in database."""
        if not self.conn:
            self.connect()

        cursor = self.conn.cursor()

        stats = {}

        # Total vehicles
        cursor.execute("SELECT COUNT(*) FROM vehicles")
        stats['total_vehicles'] = cursor.fetchone()[0]

        # Vehicles by make
        cursor.execute("""
            SELECT make, COUNT(*) as count
            FROM vehicles
            GROUP BY make
            ORDER BY count DESC
            LIMIT 10
        """)
        stats['top_makes'] = cursor.fetchall()

        # Vehicles by year
        cursor.execute("""
            SELECT year, COUNT(*) as count
            FROM vehicles
            GROUP BY year
            ORDER BY year DESC
        """)
        stats['by_year'] = cursor.fetchall()

        # Unique make/model combinations
        cursor.execute("SELECT COUNT(DISTINCT make || model) FROM vehicles")
        stats['unique_models'] = cursor.fetchone()[0]

        return stats

    def print_vehicle_stats(self):
        """Print vehicle statistics."""
        stats = self.get_vehicle_stats()

        print("\n[STATS] Vehicle Database Statistics")
        print("=" * 50)
        print(f"Total vehicles: {stats['total_vehicles']:,}")
        print(f"Unique models:  {stats['unique_models']:,}")

        print("\nTop 10 Manufacturers:")
        for make, count in stats['top_makes']:
            print(f"  {make:20s} {count:>8,}")

        print("\nVehicles by Year:")
        for year, count in stats['by_year']:
            print(f"  {year}  {count:>8,}")

        print("=" * 50)


def main():
    """Main function for command-line usage."""
    import argparse

    parser = argparse.ArgumentParser(
        description='Import vehicle data into automotive diagnostic database'
    )
    parser.add_argument(
        '--db',
        default='automotive_diagnostics.db',
        help='Database file path (default: automotive_diagnostics.db)'
    )
    parser.add_argument(
        '--file',
        help='Import single file'
    )
    parser.add_argument(
        '--directory',
        help='Import all files from directory'
    )
    parser.add_argument(
        '--pattern',
        default='*.txt',
        help='File pattern for directory import (default: *.txt)'
    )
    parser.add_argument(
        '--year',
        type=int,
        help='Override year for all vehicles in file'
    )
    parser.add_argument(
        '--stats',
        action='store_true',
        help='Show vehicle database statistics'
    )

    args = parser.parse_args()

    # Initialize importer
    importer = VehicleImporter(db_path=args.db)

    # Import from file
    if args.file:
        importer.connect()
        importer.import_from_file(args.file, year=args.year)
        importer.disconnect()

    # Import from directory
    elif args.directory:
        importer.connect()
        importer.import_from_directory(args.directory, pattern=args.pattern)
        importer.disconnect()

    # Show stats
    if args.stats or (not args.file and not args.directory):
        importer.connect()
        importer.print_vehicle_stats()
        importer.disconnect()


if __name__ == "__main__":
    main()
