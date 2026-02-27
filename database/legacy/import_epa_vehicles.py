#!/usr/bin/env python3
"""
EPA Fuel Economy CSV Importer for Automotive Diagnostic Database.

Parses EPA Fuel Economy Guide CSV files and imports vehicle data into SQLite database.
Handles field mapping from EPA format to database schema with comprehensive error handling.

Usage:
    python import_epa_vehicles.py --file 2006_FE_Guide.csv
    python import_epa_vehicles.py --directory ./epa_data --pattern "*_FE_Guide*.csv"
    python import_epa_vehicles.py --stats

Author: Automotive Diagnostic System
Version: 1.0
"""

import sqlite3
import csv
import re
import os
from pathlib import Path
from typing import Dict, Optional, Tuple


class EPAVehicleImporter:
    """
    Import EPA Fuel Economy data into automotive diagnostic database.

    Handles parsing of EPA CSV format, field mapping to database schema,
    error handling, and statistics reporting. Designed for Windows compatibility
    with ASCII-only output.
    """

    # EPA fuel type codes
    FUEL_TYPE_MAP = {
        'P': 'Premium',
        'R': 'Regular',
        'D': 'Diesel',
        'E': 'E85',
        'C': 'CNG',
        'N': 'Natural Gas',
    }

    # EPA drive system codes
    DRIVE_TYPE_MAP = {
        'F': 'FWD',
        'R': 'RWD',
        '4': '4WD',
        'A': 'AWD',
        'P': 'Part-time 4WD',
    }

    def __init__(self, db_path: str = "automotive_diagnostics.db"):
        """
        Initialize EPA vehicle importer.

        Args:
            db_path: Path to SQLite database file
        """
        self.db_path = db_path
        self.conn: Optional[sqlite3.Connection] = None

    def connect(self) -> sqlite3.Connection:
        """
        Connect to SQLite database.

        Returns:
            Database connection object

        Raises:
            sqlite3.Error: If connection fails
        """
        try:
            self.conn = sqlite3.connect(self.db_path)
            self.conn.execute("PRAGMA foreign_keys = ON")
            return self.conn
        except sqlite3.Error as e:
            print(f"[ERROR] Failed to connect to database: {e}")
            raise

    def disconnect(self):
        """Close database connection and cleanup resources."""
        if self.conn:
            try:
                self.conn.close()
            except sqlite3.Error as e:
                print(f"[WARN] Error closing database: {e}")
            finally:
                self.conn = None

    def parse_fuel_type(self, fuel_code: str) -> Optional[str]:
        """
        Convert EPA fuel type code to descriptive name.

        Args:
            fuel_code: Single-character EPA fuel type code

        Returns:
            Fuel type name or None if code is invalid

        Examples:
            'P' -> 'Premium'
            'R' -> 'Regular'
            'D' -> 'Diesel'
        """
        if not fuel_code or not isinstance(fuel_code, str):
            return None
        return self.FUEL_TYPE_MAP.get(fuel_code.strip().upper())

    def parse_drive_type(self, drive_code: str) -> Optional[str]:
        """
        Convert EPA drive system code to descriptive name.

        Args:
            drive_code: Single-character or short EPA drive code

        Returns:
            Drive type name or None if code is invalid

        Examples:
            'F' -> 'FWD'
            'R' -> 'RWD'
            '4' -> '4WD'
        """
        if not drive_code or not isinstance(drive_code, str):
            return None
        return self.DRIVE_TYPE_MAP.get(drive_code.strip().upper())

    def parse_transmission(self, trans_str: str) -> Tuple[Optional[str], Optional[int]]:
        """
        Parse EPA transmission string to extract type and gear count.

        Args:
            trans_str: EPA transmission string (e.g., "Auto(S6)", "Manual(M5)")

        Returns:
            Tuple of (transmission_type, gear_count)

        Examples:
            "Auto(S6)" -> ("Automatic", 6)
            "Manual(M5)" -> ("Manual", 5)
            "Auto(AV)" -> ("CVT", None)
        """
        if not trans_str or not isinstance(trans_str, str):
            return (None, None)

        trans_str = trans_str.strip()

        # Extract type
        trans_type = None
        if trans_str.startswith('Auto'):
            if 'AV' in trans_str:
                trans_type = 'CVT'
            else:
                trans_type = 'Automatic'
        elif trans_str.startswith('Manual'):
            trans_type = 'Manual'
        else:
            trans_type = trans_str

        # Extract gear count (number after letter in parentheses)
        gear_count = None
        match = re.search(r'\([A-Z](\d+)\)', trans_str)
        if match:
            try:
                gear_count = int(match.group(1))
            except ValueError:
                pass

        return (trans_type, gear_count)

    def parse_forced_induction(self, turbo: str, supercharger: str) -> Optional[str]:
        """
        Determine forced induction type from EPA flags.

        Args:
            turbo: EPA turbo flag ('T' or empty)
            supercharger: EPA supercharger flag ('S' or empty)

        Returns:
            Forced induction type or None

        Examples:
            ('T', '') -> 'Turbo'
            ('', 'S') -> 'Supercharger'
            ('T', 'S') -> 'Twin-Charged'
            ('', '') -> None
        """
        has_turbo = turbo and turbo.strip().upper() == 'T'
        has_supercharger = supercharger and supercharger.strip().upper() == 'S'

        if has_turbo and has_supercharger:
            return 'Twin-Charged'
        elif has_turbo:
            return 'Turbo'
        elif has_supercharger:
            return 'Supercharger'
        else:
            return None

    def parse_gas_guzzler(self, guzzler_flag: str) -> int:
        """
        Convert EPA gas guzzler flag to boolean integer.

        Args:
            guzzler_flag: EPA gas guzzler flag ('G' or empty)

        Returns:
            1 if gas guzzler, 0 otherwise
        """
        if guzzler_flag and guzzler_flag.strip().upper() == 'G':
            return 1
        return 0

    def is_hybrid(self, eng_blk_txt: str) -> bool:
        """
        Determine if vehicle is a hybrid based on engine block text.

        Args:
            eng_blk_txt: EPA engine block text field

        Returns:
            True if vehicle is hybrid
        """
        if not eng_blk_txt:
            return False
        return 'HEV' in eng_blk_txt.upper()

    def format_engine_string(self, displacement: str, cylinders: str) -> str:
        """
        Format engine string in database format.

        Args:
            displacement: Engine displacement in liters
            cylinders: Number of cylinders

        Returns:
            Formatted engine string (e.g., "3.5/6")

        Examples:
            ("3.5", "6") -> "3.5/6"
            ("2.0", "4") -> "2.0/4"
        """
        try:
            disp = float(displacement) if displacement else None
            cyl = int(float(cylinders)) if cylinders else None

            if disp and cyl:
                return f"{disp}/{cyl}"
            elif disp:
                return f"{disp}"
            else:
                return ""
        except (ValueError, TypeError):
            return ""

    def safe_float(self, value: str) -> Optional[float]:
        """
        Safely convert string to float.

        Args:
            value: String value to convert

        Returns:
            Float value or None if conversion fails
        """
        if not value or not isinstance(value, str):
            return None
        try:
            return float(value.strip())
        except ValueError:
            return None

    def safe_int(self, value: str) -> Optional[int]:
        """
        Safely convert string to integer.

        Args:
            value: String value to convert

        Returns:
            Integer value or None if conversion fails
        """
        if not value or not isinstance(value, str):
            return None
        try:
            # Handle floats that should be ints (e.g., "6.0" -> 6)
            return int(float(value.strip()))
        except ValueError:
            return None

    def parse_vehicle_record(self, row: Dict[str, str], year: int) -> Optional[Dict]:
        """
        Parse a single EPA CSV row into a vehicle record.

        Args:
            row: CSV row as dictionary (column name -> value)
            year: Vehicle model year

        Returns:
            Parsed vehicle dictionary or None if parsing fails
        """
        try:
            # Extract core fields
            make = row.get('MFR', '').strip()
            model = row.get('CAR LINE', '').strip()

            if not make or not model:
                return None

            # Parse engine fields
            displacement = self.safe_float(row.get('DISPLACEMENT', ''))
            cylinders = self.safe_int(row.get('NUMB CYL', ''))
            engine_str = self.format_engine_string(
                row.get('DISPLACEMENT', ''),
                row.get('NUMB CYL', '')
            )

            # Parse transmission
            trans_type, gear_count = self.parse_transmission(row.get('TRANS', ''))

            # Parse drive type
            drive_type = self.parse_drive_type(row.get('DRIVE SYS', ''))

            # Parse fuel type
            fuel_type = self.parse_fuel_type(row.get('FUEL TYPE', ''))

            # Parse EPA-specific fields
            forced_induction = self.parse_forced_induction(
                row.get('TURBO', ''),
                row.get('SPCHGR', '')
            )

            mpg_city = self.safe_int(row.get('CITY MPG (GUIDE)', ''))
            mpg_highway = self.safe_int(row.get('HWY MPG (GUIDE)', ''))
            mpg_combined = self.safe_int(row.get('COMB MPG (GUIDE)', ''))

            valves_per_cyl = self.safe_int(row.get('VLVS PER CYL', ''))
            gas_guzzler = self.parse_gas_guzzler(row.get('GUZLR', ''))
            annual_fuel_cost = self.safe_int(row.get('ANL FL CST', ''))

            vehicle_class = row.get('CLASS', '').strip()

            # Check if hybrid
            body_style = None
            if self.is_hybrid(row.get('ENG BLK TXT', '')):
                body_style = 'Hybrid'

            # Build vehicle record
            vehicle = {
                'make': make,
                'model': model,
                'year': year,
                'engine': engine_str,
                'engine_displacement': displacement,
                'engine_cylinders': cylinders,
                'body_style': body_style,
                'drive_type': drive_type,
                'transmission_type': trans_type,
                'fuel_type': fuel_type,
                'forced_induction': forced_induction,
                'mpg_city': mpg_city,
                'mpg_highway': mpg_highway,
                'mpg_combined': mpg_combined,
                'valves_per_cylinder': valves_per_cyl,
                'vehicle_class': vehicle_class,
                'gas_guzzler': gas_guzzler,
                'annual_fuel_cost': annual_fuel_cost,
            }

            return vehicle

        except Exception as e:
            print(f"[ERROR] Failed to parse vehicle record: {e}")
            return None

    def insert_vehicle(self, cursor: sqlite3.Cursor, vehicle: Dict) -> Tuple[bool, str]:
        """
        Insert a vehicle record into the database.

        Args:
            cursor: Database cursor
            vehicle: Vehicle dictionary

        Returns:
            Tuple of (success: bool, error_type: str)
            error_type is 'duplicate', 'error', or '' for success
        """
        try:
            cursor.execute("""
                INSERT INTO vehicles (
                    make, model, year, engine,
                    engine_displacement, engine_cylinders,
                    body_style, drive_type, transmission_type, fuel_type,
                    forced_induction, mpg_city, mpg_highway, mpg_combined,
                    valves_per_cylinder, vehicle_class, gas_guzzler, annual_fuel_cost
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                vehicle['make'],
                vehicle['model'],
                vehicle['year'],
                vehicle['engine'],
                vehicle['engine_displacement'],
                vehicle['engine_cylinders'],
                vehicle['body_style'],
                vehicle['drive_type'],
                vehicle['transmission_type'],
                vehicle['fuel_type'],
                vehicle['forced_induction'],
                vehicle['mpg_city'],
                vehicle['mpg_highway'],
                vehicle['mpg_combined'],
                vehicle['valves_per_cylinder'],
                vehicle['vehicle_class'],
                vehicle['gas_guzzler'],
                vehicle['annual_fuel_cost'],
            ))
            return (True, '')

        except sqlite3.IntegrityError:
            # Duplicate vehicle (UNIQUE constraint on make/model/year/engine)
            return (False, 'duplicate')

        except sqlite3.Error as e:
            print(f"[ERROR] Database error inserting {vehicle['make']} {vehicle['model']} "
                  f"{vehicle['year']}: {e}")
            return (False, 'error')

    def extract_year_from_filename(self, filename: str) -> Optional[int]:
        """
        Extract year from EPA filename pattern.

        Args:
            filename: CSV filename

        Returns:
            Year as integer or None if not found

        Examples:
            "2006_FE_Guide_14-Nov-2005_download.csv" -> 2006
            "2008_FE_guide_ALL.csv" -> 2008
        """
        match = re.match(r'(\d{4})_', filename)
        if match:
            try:
                year = int(match.group(1))
                # Validate year is reasonable (EPA data range)
                if 1984 <= year <= 2030:
                    return year
            except ValueError:
                pass
        return None

    def import_from_file(self, file_path: str, year: Optional[int] = None) -> Dict:
        """
        Import vehicles from a single EPA CSV file.

        Args:
            file_path: Path to EPA CSV file
            year: Override year (if not extractable from filename)

        Returns:
            Dictionary with import statistics

        Example:
            >>> importer = EPAVehicleImporter()
            >>> importer.connect()
            >>> stats = importer.import_from_file('2006_FE_Guide.csv')
            >>> print(f"Imported: {stats['inserted']:,}")
        """
        if not os.path.exists(file_path):
            print(f"[ERROR] File not found: {file_path}")
            return {'inserted': 0, 'duplicates': 0, 'errors': 0, 'total': 0}

        print(f"\n[INFO] Processing file: {file_path}")

        # Extract year from filename if not provided
        if year is None:
            filename = os.path.basename(file_path)
            year = self.extract_year_from_filename(filename)

            if year is None:
                print("[ERROR] Cannot determine year from filename. Please provide --year parameter.")
                return {'inserted': 0, 'duplicates': 0, 'errors': 0, 'total': 0}

            print(f"[INFO] Extracted year from filename: {year}")

        # Validate year
        if year < 2005 or year > 2025:
            print(f"[ERROR] Year {year} is outside supported range (2005-2025)")
            return {'inserted': 0, 'duplicates': 0, 'errors': 0, 'total': 0}

        # Read and parse CSV
        vehicles = []
        parse_errors = 0

        try:
            with open(file_path, 'r', encoding='utf-8') as csvfile:
                reader = csv.DictReader(csvfile)

                for row_num, row in enumerate(reader, start=2):  # Start at 2 (header is row 1)
                    vehicle = self.parse_vehicle_record(row, year)

                    if vehicle:
                        vehicles.append(vehicle)
                    else:
                        parse_errors += 1

        except Exception as e:
            print(f"[ERROR] Failed to read CSV file: {e}")
            return {'inserted': 0, 'duplicates': 0, 'errors': 0, 'total': 0}

        print(f"[INFO] Parsed vehicles: {len(vehicles):,}")
        if parse_errors > 0:
            print(f"[WARN] Parse errors: {parse_errors:,}")

        # Insert into database
        if not self.conn:
            self.connect()

        cursor = self.conn.cursor()
        inserted = 0
        duplicates = 0
        errors = 0

        for vehicle in vehicles:
            success, error_type = self.insert_vehicle(cursor, vehicle)

            if success:
                inserted += 1
            elif error_type == 'duplicate':
                duplicates += 1
            else:
                errors += 1

        # Commit transaction
        try:
            self.conn.commit()
        except sqlite3.Error as e:
            print(f"[ERROR] Failed to commit transaction: {e}")
            self.conn.rollback()

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

    def import_from_directory(self, directory_path: str, pattern: str = "*_FE_Guide*.csv") -> Dict:
        """
        Import vehicles from all matching CSV files in a directory.

        Args:
            directory_path: Path to directory containing EPA CSV files
            pattern: Glob pattern for files (default: *_FE_Guide*.csv)

        Returns:
            Dictionary with aggregated statistics

        Example:
            >>> importer = EPAVehicleImporter()
            >>> importer.connect()
            >>> stats = importer.import_from_directory('./epa_data')
            >>> print(f"Total imported: {stats['inserted']:,}")
        """
        directory = Path(directory_path)

        if not directory.exists():
            print(f"[ERROR] Directory not found: {directory_path}")
            return {'inserted': 0, 'duplicates': 0, 'errors': 0, 'total': 0, 'files_processed': 0}

        # Find all matching files
        files = sorted(directory.glob(pattern))

        if not files:
            print(f"[WARN] No files found matching pattern: {pattern}")
            return {'inserted': 0, 'duplicates': 0, 'errors': 0, 'total': 0, 'files_processed': 0}

        print(f"\n[INFO] Found {len(files)} files to import")

        # Aggregate statistics
        total_stats = {
            'inserted': 0,
            'duplicates': 0,
            'errors': 0,
            'total': 0,
            'files_processed': 0
        }

        # Import each file
        for file_path in files:
            stats = self.import_from_file(str(file_path))

            if stats:
                total_stats['inserted'] += stats['inserted']
                total_stats['duplicates'] += stats['duplicates']
                total_stats['errors'] += stats['errors']
                total_stats['total'] += stats['total']
                total_stats['files_processed'] += 1

        # Print aggregate statistics
        print("\n[SUMMARY] Total Import Results")
        print("=" * 50)
        print(f"Files processed: {total_stats['files_processed']}")
        print(f"Total inserted:  {total_stats['inserted']:,}")
        print(f"Total duplicates: {total_stats['duplicates']:,}")
        print(f"Total errors:    {total_stats['errors']:,}")
        print(f"Grand total:     {total_stats['total']:,}")
        print("=" * 50)

        return total_stats

    def get_vehicle_stats(self) -> Dict:
        """
        Get statistics about vehicles in database.

        Returns:
            Dictionary with database statistics
        """
        if not self.conn:
            self.connect()

        cursor = self.conn.cursor()
        stats = {}

        # Total vehicles
        cursor.execute("SELECT COUNT(*) FROM vehicles")
        stats['total_vehicles'] = cursor.fetchone()[0]

        # Vehicles with EPA data (mpg_city not null)
        cursor.execute("SELECT COUNT(*) FROM vehicles WHERE mpg_city IS NOT NULL")
        stats['vehicles_with_epa_data'] = cursor.fetchone()[0]

        # Top manufacturers by count
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

        # Average MPG by fuel type
        cursor.execute("""
            SELECT fuel_type,
                   ROUND(AVG(mpg_combined), 1) as avg_mpg,
                   COUNT(*) as count
            FROM vehicles
            WHERE mpg_combined IS NOT NULL AND fuel_type IS NOT NULL
            GROUP BY fuel_type
            ORDER BY avg_mpg DESC
        """)
        stats['mpg_by_fuel_type'] = cursor.fetchall()

        # Vehicles with forced induction
        cursor.execute("""
            SELECT forced_induction, COUNT(*) as count
            FROM vehicles
            WHERE forced_induction IS NOT NULL
            GROUP BY forced_induction
        """)
        stats['forced_induction'] = cursor.fetchall()

        return stats

    def print_vehicle_stats(self):
        """Print comprehensive vehicle database statistics."""
        stats = self.get_vehicle_stats()

        print("\n[STATS] Vehicle Database Statistics")
        print("=" * 60)
        print(f"Total vehicles:           {stats['total_vehicles']:>10,}")
        print(f"Vehicles with EPA data:   {stats['vehicles_with_epa_data']:>10,}")

        print("\nTop 10 Manufacturers:")
        for make, count in stats['top_makes']:
            print(f"  {make:25s} {count:>10,}")

        print("\nVehicles by Year:")
        for year, count in stats['by_year']:
            print(f"  {year}  {count:>10,}")

        if stats['mpg_by_fuel_type']:
            print("\nAverage MPG by Fuel Type:")
            for fuel_type, avg_mpg, count in stats['mpg_by_fuel_type']:
                print(f"  {fuel_type:15s} {avg_mpg:>6.1f} MPG  ({count:,} vehicles)")

        if stats['forced_induction']:
            print("\nForced Induction Distribution:")
            for fi_type, count in stats['forced_induction']:
                print(f"  {fi_type:20s} {count:>10,}")

        print("=" * 60)


def main():
    """Main function for command-line usage."""
    import argparse

    parser = argparse.ArgumentParser(
        description='Import EPA Fuel Economy data into automotive diagnostic database',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Import single CSV file
  python import_epa_vehicles.py --file 2006_FE_Guide.csv

  # Import with manual year override
  python import_epa_vehicles.py --file data.csv --year 2006

  # Import all CSV files from directory
  python import_epa_vehicles.py --directory ./epa_data

  # Import with custom file pattern
  python import_epa_vehicles.py --directory ./data --pattern "20*_FE*.csv"

  # Show database statistics
  python import_epa_vehicles.py --stats
        """
    )

    parser.add_argument(
        '--db',
        default='automotive_diagnostics.db',
        help='Database file path (default: automotive_diagnostics.db)'
    )
    parser.add_argument(
        '--file',
        help='Import single CSV file'
    )
    parser.add_argument(
        '--directory',
        help='Import all files from directory'
    )
    parser.add_argument(
        '--pattern',
        default='*_FE_Guide*.csv',
        help='File pattern for directory import (default: *_FE_Guide*.csv)'
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
    importer = EPAVehicleImporter(db_path=args.db)

    try:
        # Import from file
        if args.file:
            importer.connect()
            importer.import_from_file(args.file, year=args.year)

        # Import from directory
        elif args.directory:
            importer.connect()
            importer.import_from_directory(args.directory, pattern=args.pattern)

        # Show stats
        if args.stats or (not args.file and not args.directory):
            importer.connect()
            importer.print_vehicle_stats()

        print("\n[SUCCESS] Import completed successfully")

    except Exception as e:
        print(f"\n[ERROR] Import failed: {e}")
        return 1

    finally:
        importer.disconnect()

    return 0


if __name__ == "__main__":
    exit(main())
