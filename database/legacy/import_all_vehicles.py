"""
Universal Vehicle Data Importer

Imports vehicle data from CSV and Excel files (2005-2026) into the SQLite
automotive diagnostics database. Handles multiple file formats and column
naming variations across different years.

Usage:
    python import_all_vehicles.py --all
    python import_all_vehicles.py --year 2005
    python import_all_vehicles.py --file "path/to/file.csv" --year 2005
"""

import sqlite3
import csv
import argparse
import sys
from pathlib import Path
from typing import Dict, List, Optional, Tuple

try:
    import openpyxl
    OPENPYXL_AVAILABLE = True
except ImportError:
    OPENPYXL_AVAILABLE = False

try:
    import xlrd
    XLRD_AVAILABLE = True
except ImportError:
    XLRD_AVAILABLE = False


# Database configuration
DATABASE_PATH = Path(__file__).parent / 'automotive_diagnostics.db'
VEHICLE_DATA_ROOT = Path(__file__).parent.parent / 'Vehicle data'


class VehicleImporter:
    """Handles importing vehicle data from various file formats."""

    # Column mapping for different CSV/Excel formats
    COLUMN_MAPPINGS = {
        'make': ['Manufacturer', 'MFR', 'mfr', 'Make', 'Mfr Name',
                 'Mfr Name (blue fill means Verify rel 8 label)'],
        'model': ['carline name', 'CAR LINE', 'Model', 'model', 'Carline'],
        'displacement': ['displ', 'DISPLACEMENT', 'Displacement', 'Eng Displ'],
        'cylinders': ['cyl', 'NUMB CYL', 'Cylinders', 'numb cyl', '# Cyl'],
        'transmission': ['trans', 'TRANS', 'Transmission',
                        'Trans in FE Guide (MFR entered for data entered after May 13 2011)'],
        'drive': ['drv', 'DRIVE SYS', 'Drive', 'drive sys'],
        'fuel_type': ['fl', 'FUEL TYPE', 'Fuel Type', 'fuel type'],
        'class': ['CLASS', 'Class', 'Vehicle Class'],
        'city_mpg': ['cty', 'CITY MPG (GUIDE)', 'City FE (Guide) - Conventional Fuel'],
        'highway_mpg': ['hwy', 'HWY MPG (GUIDE)', 'Hwy FE (Guide) - Conventional Fuel'],
    }

    def __init__(self, db_path: Path):
        """Initialize importer with database connection."""
        self.db_path = db_path
        self.conn = None
        self.cursor = None
        self.stats = {
            'total': 0,
            'inserted': 0,
            'duplicates': 0,
            'errors': 0,
            'error_details': []
        }

    def connect(self):
        """Connect to the SQLite database."""
        self.conn = sqlite3.connect(str(self.db_path))
        self.conn.execute("PRAGMA foreign_keys = ON")
        self.cursor = self.conn.cursor()

    def close(self):
        """Close database connection."""
        if self.conn:
            self.conn.close()

    def find_column(self, headers: List[str], field_name: str) -> Optional[int]:
        """
        Find column index by trying multiple possible names.

        Args:
            headers: List of column headers from file
            field_name: Field name to search for in COLUMN_MAPPINGS

        Returns:
            Column index if found, None otherwise
        """
        possible_names = self.COLUMN_MAPPINGS.get(field_name, [])

        for idx, header in enumerate(headers):
            header_clean = header.strip().strip('"').strip()
            if header_clean in possible_names:
                return idx

        return None

    def parse_engine_info(
        self,
        row: List[str],
        headers: List[str]
    ) -> Tuple[Optional[float], Optional[int], str]:
        """
        Parse engine displacement and cylinder count from row data.

        Args:
            row: Data row from CSV/Excel
            headers: Column headers

        Returns:
            Tuple of (displacement_liters, cylinders, engine_description)
        """
        disp_idx = self.find_column(headers, 'displacement')
        cyl_idx = self.find_column(headers, 'cylinders')
        trans_idx = self.find_column(headers, 'transmission')

        displacement = None
        cylinders = None
        engine_parts = []

        # Extract displacement
        if disp_idx is not None and disp_idx < len(row):
            try:
                disp_str = row[disp_idx].strip()
                if disp_str:
                    displacement = float(disp_str)
                    engine_parts.append(f"{displacement}L")
            except (ValueError, AttributeError):
                pass

        # Extract cylinders
        if cyl_idx is not None and cyl_idx < len(row):
            try:
                cyl_str = row[cyl_idx].strip()
                if cyl_str:
                    cylinders = int(float(cyl_str))
                    engine_parts.append(f"{cylinders}-Cyl")
            except (ValueError, AttributeError):
                pass

        # Build engine description
        if trans_idx is not None and trans_idx < len(row):
            trans_str = row[trans_idx].strip()
            if trans_str:
                engine_parts.append(trans_str)

        engine_description = " ".join(engine_parts) if engine_parts else "Unknown"

        return displacement, cylinders, engine_description

    def import_csv(self, file_path: Path, year: int) -> Dict[str, int]:
        """
        Import vehicles from CSV file.

        Args:
            file_path: Path to CSV file
            year: Model year for vehicles

        Returns:
            Statistics dictionary
        """
        print(f"[INFO] Importing CSV: {file_path.name} (Year: {year})")

        local_stats = {'inserted': 0, 'duplicates': 0, 'errors': 0, 'total': 0}

        try:
            with open(file_path, 'r', encoding='utf-8', errors='replace') as f:
                reader = csv.reader(f)
                headers = next(reader)  # Read header row

                # Find column indices
                make_idx = self.find_column(headers, 'make')
                model_idx = self.find_column(headers, 'model')

                if make_idx is None or model_idx is None:
                    print(f"[ERROR] Could not find required columns in {file_path.name}")
                    print(f"        Headers: {headers[:10]}...")
                    self.stats['errors'] += 1
                    return local_stats

                for row in reader:
                    local_stats['total'] += 1

                    try:
                        # Extract basic info
                        make = row[make_idx].strip() if make_idx < len(row) else ""
                        model = row[model_idx].strip() if model_idx < len(row) else ""

                        if not make or not model:
                            continue

                        # Parse engine info
                        displacement, cylinders, engine_desc = self.parse_engine_info(row, headers)

                        # Insert into database
                        self.cursor.execute("""
                            INSERT INTO vehicles (
                                make, model, year, engine,
                                engine_displacement, engine_cylinders
                            )
                            VALUES (?, ?, ?, ?, ?, ?)
                        """, (
                            make.upper(),
                            model,
                            year,
                            engine_desc,
                            displacement,
                            cylinders
                        ))

                        local_stats['inserted'] += 1

                    except sqlite3.IntegrityError:
                        # Duplicate vehicle
                        local_stats['duplicates'] += 1

                    except Exception as e:
                        local_stats['errors'] += 1
                        error_msg = f"Year {year}, Row {local_stats['total']}: {str(e)}"
                        self.stats['error_details'].append(error_msg)

                self.conn.commit()

        except Exception as e:
            print(f"[ERROR] Failed to read {file_path.name}: {e}")
            self.stats['errors'] += 1

        return local_stats

    def import_excel(self, file_path: Path, year: int, file_format: str = 'xlsx') -> Dict[str, int]:
        """
        Import vehicles from Excel file (XLS or XLSX).

        Args:
            file_path: Path to Excel file
            year: Model year for vehicles
            file_format: 'xlsx' or 'xls'

        Returns:
            Statistics dictionary
        """
        print(f"[INFO] Importing Excel ({file_format.upper()}): {file_path.name} (Year: {year})")

        local_stats = {'inserted': 0, 'duplicates': 0, 'errors': 0, 'total': 0}

        try:
            if file_format == 'xlsx':
                if not OPENPYXL_AVAILABLE:
                    print("[ERROR] openpyxl library not installed. Run: pip install openpyxl")
                    self.stats['errors'] += 1
                    return local_stats

                wb = openpyxl.load_workbook(str(file_path), read_only=True, data_only=True)
                sheet = wb.active
                rows = list(sheet.iter_rows(values_only=True))

            else:  # xls
                if not XLRD_AVAILABLE:
                    print("[ERROR] xlrd library not installed. Run: pip install xlrd")
                    self.stats['errors'] += 1
                    return local_stats

                wb = xlrd.open_workbook(str(file_path))
                sheet = wb.sheet_by_index(0)
                rows = [sheet.row_values(i) for i in range(sheet.nrows)]

            if not rows:
                print(f"[ERROR] No data found in {file_path.name}")
                return local_stats

            # Find the header row (skip empty or title rows)
            header_row_idx = 0
            for idx, row in enumerate(rows[:10]):  # Check first 10 rows
                row_str = [str(cell).strip() if cell else "" for cell in row]
                # Look for known header keywords
                if any('Mfr' in cell or 'Manufacturer' in cell or 'Make' in cell
                       for cell in row_str):
                    header_row_idx = idx
                    break

            headers = [str(h).strip() if h else "" for h in rows[header_row_idx]]
            data_start_idx = header_row_idx + 1

            # Find column indices
            make_idx = self.find_column(headers, 'make')
            model_idx = self.find_column(headers, 'model')

            if make_idx is None or model_idx is None:
                print(f"[ERROR] Could not find required columns in {file_path.name}")
                print(f"        Headers: {headers[:10]}...")
                self.stats['errors'] += 1
                return local_stats

            # Process data rows
            for row in rows[data_start_idx:]:
                local_stats['total'] += 1

                try:
                    # Convert row to strings
                    row_str = [str(cell).strip() if cell is not None else "" for cell in row]

                    # Extract basic info
                    make = row_str[make_idx] if make_idx < len(row_str) else ""
                    model = row_str[model_idx] if model_idx < len(row_str) else ""

                    if not make or not model or make == "None" or model == "None":
                        continue

                    # Parse engine info
                    displacement, cylinders, engine_desc = self.parse_engine_info(row_str, headers)

                    # Insert into database
                    self.cursor.execute("""
                        INSERT INTO vehicles (
                            make, model, year, engine,
                            engine_displacement, engine_cylinders
                        )
                        VALUES (?, ?, ?, ?, ?, ?)
                    """, (
                        make.upper(),
                        model,
                        year,
                        engine_desc,
                        displacement,
                        cylinders
                    ))

                    local_stats['inserted'] += 1

                except sqlite3.IntegrityError:
                    # Duplicate vehicle
                    local_stats['duplicates'] += 1

                except Exception as e:
                    local_stats['errors'] += 1
                    error_msg = f"Year {year}, Row {local_stats['total']}: {str(e)}"
                    self.stats['error_details'].append(error_msg)

            self.conn.commit()

        except Exception as e:
            print(f"[ERROR] Failed to read {file_path.name}: {e}")
            self.stats['errors'] += 1

        return local_stats

    def import_year(self, year: int) -> bool:
        """
        Import data for a specific year.

        Args:
            year: Year to import (2005-2026)

        Returns:
            True if successful, False otherwise
        """
        # Determine directory and file
        year_dir = VEHICLE_DATA_ROOT / f"{year % 100:02d}data"

        if not year_dir.exists():
            print(f"[ERROR] Directory not found: {year_dir}")
            return False

        # Find data file in directory
        csv_files = list(year_dir.glob("*.csv"))
        xls_files = list(year_dir.glob("*.xls"))
        xlsx_files = list(year_dir.glob("*.xlsx"))

        if csv_files:
            file_path = csv_files[0]
            local_stats = self.import_csv(file_path, year)
        elif xlsx_files:
            file_path = xlsx_files[0]
            local_stats = self.import_excel(file_path, year, 'xlsx')
        elif xls_files:
            file_path = xls_files[0]
            local_stats = self.import_excel(file_path, year, 'xls')
        else:
            print(f"[ERROR] No data file found in {year_dir}")
            return False

        # Update global stats
        self.stats['total'] += local_stats['total']
        self.stats['inserted'] += local_stats['inserted']
        self.stats['duplicates'] += local_stats['duplicates']
        self.stats['errors'] += local_stats['errors']

        print(f"[STATS] Year {year}: Inserted={local_stats['inserted']}, "
              f"Duplicates={local_stats['duplicates']}, "
              f"Errors={local_stats['errors']}, "
              f"Total={local_stats['total']}")

        return True

    def import_all_years(self) -> bool:
        """
        Import data for all available years (2005-2026).

        Returns:
            True if all years imported successfully
        """
        years = range(2005, 2027)  # 2005 to 2026
        success_count = 0

        print(f"\n[INFO] Starting import of {len(years)} years of vehicle data\n")

        for year in years:
            if self.import_year(year):
                success_count += 1
            print()  # Blank line between years

        print(f"\n[SUMMARY] Successfully imported {success_count}/{len(years)} years")

        return success_count == len(years)

    def print_final_stats(self):
        """Print final import statistics."""
        print("\n" + "=" * 70)
        print("FINAL IMPORT STATISTICS")
        print("=" * 70)
        print(f"Total Records Processed: {self.stats['total']:,}")
        print(f"Successfully Inserted:   {self.stats['inserted']:,}")
        print(f"Duplicates Skipped:      {self.stats['duplicates']:,}")
        print(f"Errors:                  {self.stats['errors']:,}")

        if self.stats['error_details']:
            print("\nError Details (first 10):")
            for error in self.stats['error_details'][:10]:
                print(f"  - {error}")

        # Query database for final counts
        self.cursor.execute("SELECT COUNT(*) FROM vehicles")
        total_vehicles = self.cursor.fetchone()[0]

        self.cursor.execute("""
            SELECT year, COUNT(*) as count
            FROM vehicles
            GROUP BY year
            ORDER BY year
        """)
        year_counts = self.cursor.fetchall()

        print(f"\nTotal Vehicles in Database: {total_vehicles:,}")
        print("\nVehicles by Year:")
        for year, count in year_counts:
            print(f"  {year}: {count:,} vehicles")

        print("=" * 70 + "\n")


def main():
    """Main entry point for the script."""
    parser = argparse.ArgumentParser(
        description='Import vehicle data from CSV/Excel files into SQLite database'
    )
    parser.add_argument(
        '--all',
        action='store_true',
        help='Import all years (2005-2026)'
    )
    parser.add_argument(
        '--year',
        type=int,
        help='Import specific year (e.g., 2005)'
    )
    parser.add_argument(
        '--file',
        type=str,
        help='Import specific file (requires --year)'
    )
    parser.add_argument(
        '--db',
        type=str,
        default=str(DATABASE_PATH),
        help=f'Database path (default: {DATABASE_PATH})'
    )

    args = parser.parse_args()

    # Validate arguments
    if not args.all and not args.year:
        parser.error("Must specify --all or --year")

    if args.file and not args.year:
        parser.error("--file requires --year")

    # Initialize importer
    db_path = Path(args.db)
    if not db_path.exists():
        print(f"[ERROR] Database not found: {db_path}")
        print("        Run init_database_simple.py first")
        sys.exit(1)

    importer = VehicleImporter(db_path)

    try:
        importer.connect()

        if args.all:
            importer.import_all_years()
        elif args.year:
            if args.file:
                # Import specific file
                file_path = Path(args.file)
                if file_path.suffix.lower() == '.csv':
                    importer.import_csv(file_path, args.year)
                elif file_path.suffix.lower() in ['.xlsx', '.xls']:
                    fmt = 'xlsx' if file_path.suffix.lower() == '.xlsx' else 'xls'
                    importer.import_excel(file_path, args.year, fmt)
            else:
                # Import year directory
                importer.import_year(args.year)

        importer.print_final_stats()

    except Exception as e:
        print(f"\n[FATAL ERROR] {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

    finally:
        importer.close()

    print("[SUCCESS] Import complete!")


if __name__ == '__main__':
    main()
