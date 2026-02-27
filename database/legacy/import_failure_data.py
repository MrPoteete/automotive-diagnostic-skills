"""
Common Automotive Failure Data Importer

Imports failure patterns from Common_Automotive_failures.md into the SQLite
automotive diagnostics database. Parses markdown structure to extract failure
information and links failures to affected vehicles.

Usage:
    python import_failure_data.py
    python import_failure_data.py --dry-run
    python import_failure_data.py --manufacturer FORD
"""

import sqlite3
import re
import argparse
import sys
from pathlib import Path
from typing import Dict, List, Optional


# Database and file configuration
DATABASE_PATH = Path(__file__).parent / 'automotive_diagnostics.db'
FAILURE_DATA_FILE = Path(__file__).parent.parent / 'Common Failure data' / 'Common_Automotive_failures.md'


# Safety-critical keywords for automatic flagging
SAFETY_CRITICAL_KEYWORDS = [
    'airbag', 'srs', 'brake', 'abs', 'steering', 'eps', 'tipm',
    'throttle', 'pedal', 'fuel pump', 'fuel leak', 'fire', 'crash',
    'rollaway', 'loss of power', 'loss of propulsion', 'stall',
    'sudden acceleration', 'door latch', 'seat belt', 'restraint'
]


class FailurePattern:
    """Represents a single failure pattern extracted from markdown."""

    def __init__(self):
        self.name: str = ""
        self.manufacturer: str = ""
        self.component: str = ""
        self.vehicles: str = ""  # Raw vehicle string
        self.failure_description: str = ""
        self.source: str = ""
        self.source_url: str = ""
        self.confidence: str = "MEDIUM"
        self.nhtsa_number: str = ""
        self.tsb_number: str = ""
        self.safety_critical: bool = False
        self.repair_cost_min: Optional[int] = None
        self.repair_cost_max: Optional[int] = None
        self.additional_info: List[str] = []

    def is_complete(self) -> bool:
        """Check if failure pattern has minimum required fields."""
        return bool(self.name and self.manufacturer and self.failure_description)

    def detect_safety_critical(self) -> bool:
        """Detect if failure involves safety-critical systems."""
        search_text = (
            f"{self.name} {self.component} {self.failure_description}"
        ).lower()

        return any(keyword in search_text for keyword in SAFETY_CRITICAL_KEYWORDS)


class FailureDataImporter:
    """Imports failure pattern data from markdown file into SQLite database."""

    def __init__(self, db_path: Path, dry_run: bool = False):
        """
        Initialize importer.

        Args:
            db_path: Path to SQLite database
            dry_run: If True, parse but don't write to database
        """
        self.db_path = db_path
        self.dry_run = dry_run
        self.conn = None
        self.cursor = None
        self.stats = {
            'total_patterns': 0,
            'inserted_patterns': 0,
            'inserted_links': 0,
            'skipped': 0,
            'errors': 0,
            'error_details': []
        }

    def connect(self):
        """Connect to the SQLite database."""
        if not self.dry_run:
            self.conn = sqlite3.connect(str(self.db_path))
            self.conn.execute("PRAGMA foreign_keys = ON")
            self.cursor = self.conn.cursor()

    def close(self):
        """Close database connection."""
        if self.conn:
            self.conn.close()

    def parse_markdown_file(self, file_path: Path) -> List[FailurePattern]:
        """
        Parse the markdown file and extract failure patterns.

        Args:
            file_path: Path to markdown file

        Returns:
            List of FailurePattern objects
        """
        print(f"[INFO] Parsing {file_path.name}...")

        patterns = []
        current_manufacturer = ""
        current_pattern = None

        with open(file_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()

        i = 0
        while i < len(lines):
            line = lines[i].strip()

            # Detect manufacturer section
            if line.startswith('## ') and not line.startswith('## KEY') and not line.startswith('## CRITICAL') and not line.startswith('## IMPORTANT') and not line.startswith('## METHODOLOGY'):
                manufacturer_match = re.match(r'^##\s+(.+?)(?:\s+\(|$)', line)
                if manufacturer_match:
                    current_manufacturer = manufacturer_match.group(1).strip()
                    print(f"[INFO] Processing manufacturer: {current_manufacturer}")

            # Detect failure pattern section (### heading)
            elif line.startswith('### '):
                # Save previous pattern if exists
                if current_pattern and current_pattern.is_complete():
                    patterns.append(current_pattern)
                    self.stats['total_patterns'] += 1

                # Start new pattern
                current_pattern = FailurePattern()
                current_pattern.manufacturer = current_manufacturer
                current_pattern.name = line[4:].strip()  # Remove '### '

                # Remove numbering like "1. ", "2A. ", etc.
                current_pattern.name = re.sub(r'^\d+[A-Z]?\.\s+', '', current_pattern.name)

            # Parse bullet point data
            elif line.startswith('- **') and current_pattern:
                field_match = re.match(r'^- \*\*(.+?):\*\*\s+(.+)$', line)
                if field_match:
                    field_name = field_match.group(1).strip()
                    field_value = field_match.group(2).strip()

                    if field_name == 'Component':
                        current_pattern.component = field_value

                    elif field_name == 'Vehicles':
                        current_pattern.vehicles = field_value

                    elif field_name == 'Failure':
                        current_pattern.failure_description = field_value

                    elif field_name == 'Source':
                        # Extract URL from markdown link or plain text
                        url_match = re.search(r'https?://[^\s\)]+', field_value)
                        if url_match:
                            current_pattern.source_url = url_match.group(0)
                            current_pattern.source = field_value
                        else:
                            current_pattern.source = field_value

                    elif field_name == 'NHTSA':
                        # Extract NHTSA numbers
                        nhtsa_codes = re.findall(r'\d+[VN]-?\d+', field_value)
                        current_pattern.nhtsa_number = ', '.join(nhtsa_codes)

                        # Check for confidence marker
                        if 'HIGH CONFIDENCE' in field_value:
                            current_pattern.confidence = 'HIGH'

                    elif field_name == 'TSB':
                        # Extract TSB numbers
                        tsb_match = re.search(r'[\d-]+[A-Z]?\d+', field_value)
                        if tsb_match:
                            current_pattern.tsb_number = tsb_match.group(0)

                        if 'HIGH CONFIDENCE' in field_value:
                            current_pattern.confidence = 'HIGH'

            # Check for HIGH CONFIDENCE markers in regular text
            elif 'HIGH CONFIDENCE' in line and current_pattern:
                current_pattern.confidence = 'HIGH'

                # Extract cost range if present
                cost_match = re.search(r'\$?([\d,]+)-\$?([\d,]+)', line)
                if cost_match:
                    try:
                        current_pattern.repair_cost_min = int(cost_match.group(1).replace(',', ''))
                        current_pattern.repair_cost_max = int(cost_match.group(2).replace(',', ''))
                    except ValueError:
                        pass

                # Extract settlement/penalty amounts as additional info
                settlement_match = re.search(r'\$([\d.]+)M', line)
                if settlement_match:
                    current_pattern.additional_info.append(f"Settlement: ${settlement_match.group(1)}M")

            i += 1

        # Don't forget the last pattern
        if current_pattern and current_pattern.is_complete():
            patterns.append(current_pattern)
            self.stats['total_patterns'] += 1

        print(f"[INFO] Parsed {len(patterns)} failure patterns")
        return patterns

    def parse_vehicle_string(self, vehicles_str: str, manufacturer: str) -> List[Dict]:
        """
        Parse vehicle string to extract individual vehicle specifications.

        Args:
            vehicles_str: String like "2011-2016 Fiesta, Focus, Fusion"
            manufacturer: Manufacturer name

        Returns:
            List of dicts with make, model, year_min, year_max, engine
        """
        vehicle_specs = []

        # Extract year range
        year_match = re.search(r'(\d{4})(?:-(\d{4}))?', vehicles_str)
        if not year_match:
            return vehicle_specs

        year_min = int(year_match.group(1))
        year_max = int(year_match.group(2)) if year_match.group(2) else year_min

        # Extract models - split by comma
        # Remove year ranges and parenthetical info first
        models_str = re.sub(r'\d{4}-?\d{0,4}', '', vehicles_str)
        models_str = re.sub(r'\([^)]+\)', '', models_str)
        models_str = models_str.strip()

        # Split by comma and clean
        models = [m.strip() for m in models_str.split(',') if m.strip()]

        # Extract engine info if present
        engine_info = None
        engine_match = re.search(r'(\d\.\d)L', vehicles_str)
        if engine_match:
            engine_info = f"{engine_match.group(1)}L"

        # Create vehicle spec for each model
        for model in models:
            # Clean model name
            model = re.sub(r'^\s*and\s+', '', model, flags=re.IGNORECASE)
            model = model.strip()

            if model:
                vehicle_specs.append({
                    'make': manufacturer.upper(),
                    'model': model,
                    'year_min': year_min,
                    'year_max': year_max,
                    'engine': engine_info
                })

        return vehicle_specs

    def insert_failure_pattern(self, pattern: FailurePattern) -> Optional[int]:
        """
        Insert failure pattern into database.

        Args:
            pattern: FailurePattern object

        Returns:
            failure_id if successful, None otherwise
        """
        if self.dry_run:
            print(f"[DRY RUN] Would insert: {pattern.name}")
            return None

        # Detect safety critical
        pattern.safety_critical = pattern.detect_safety_critical()

        try:
            # Build combined technical description
            technical_desc = f"Component: {pattern.component}\n"
            technical_desc += f"Affected Vehicles: {pattern.vehicles}\n"
            if pattern.additional_info:
                technical_desc += "\n" + "\n".join(pattern.additional_info)

            # Determine category from component/failure
            category = self._determine_category(pattern)

            self.cursor.execute("""
                INSERT INTO failure_patterns (
                    name, category, symptom_description, technical_description,
                    root_cause, confidence, safety_critical,
                    repair_cost_min, repair_cost_max,
                    source_type, source_url, nhtsa_number, tsb_number
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                f"{pattern.manufacturer} - {pattern.name}",
                category,
                pattern.failure_description,
                technical_desc,
                pattern.component,  # Use component as root cause
                pattern.confidence,
                1 if pattern.safety_critical else 0,
                pattern.repair_cost_min,
                pattern.repair_cost_max,
                'NHTSA/TSB' if pattern.nhtsa_number or pattern.tsb_number else 'Manufacturer',
                pattern.source_url,
                pattern.nhtsa_number if pattern.nhtsa_number else None,
                pattern.tsb_number if pattern.tsb_number else None
            ))

            failure_id = self.cursor.lastrowid
            self.stats['inserted_patterns'] += 1

            return failure_id

        except sqlite3.Error as e:
            self.stats['errors'] += 1
            error_msg = f"Failed to insert '{pattern.name}': {str(e)}"
            self.stats['error_details'].append(error_msg)
            print(f"[ERROR] {error_msg}")
            return None

    def _determine_category(self, pattern: FailurePattern) -> str:
        """Determine failure category from component and description."""
        text = f"{pattern.component} {pattern.failure_description}".lower()

        if any(kw in text for kw in ['engine', 'cylinder', 'piston', 'valve', 'cam', 'turbo']):
            return 'Engine'
        elif any(kw in text for kw in ['transmission', 'clutch', 'gear', 'shift']):
            return 'Transmission'
        elif any(kw in text for kw in ['brake', 'abs', 'caliper', 'rotor']):
            return 'Braking System'
        elif any(kw in text for kw in ['airbag', 'srs', 'restraint', 'seat belt']):
            return 'Safety Systems'
        elif any(kw in text for kw in ['electrical', 'battery', 'alternator', 'wire', 'module', 'computer']):
            return 'Electrical'
        elif any(kw in text for kw in ['suspension', 'strut', 'shock', 'spring']):
            return 'Suspension'
        elif any(kw in text for kw in ['steering', 'rack', 'pinion']):
            return 'Steering'
        elif any(kw in text for kw in ['fuel', 'injector', 'pump']):
            return 'Fuel System'
        elif any(kw in text for kw in ['door', 'latch', 'lock', 'window']):
            return 'Body/Doors'
        elif any(kw in text for kw in ['camera', 'sync', 'infotainment', 'radio']):
            return 'Electronics/Infotainment'
        else:
            return 'Other'

    def link_failure_to_vehicles(self, failure_id: int, pattern: FailurePattern) -> int:
        """
        Link failure pattern to affected vehicles in database.

        Args:
            failure_id: ID of inserted failure pattern
            failure_pattern: FailurePattern object

        Returns:
            Number of vehicle links created
        """
        if self.dry_run:
            return 0

        # Parse vehicle string
        vehicle_specs = self.parse_vehicle_string(pattern.vehicles, pattern.manufacturer)

        if not vehicle_specs:
            print(f"[WARNING] Could not parse vehicles for: {pattern.name}")
            return 0

        links_created = 0

        for spec in vehicle_specs:
            try:
                # Find matching vehicles in database
                if spec['engine']:
                    # Match with engine specification
                    self.cursor.execute("""
                        SELECT vehicle_id
                        FROM vehicles
                        WHERE make = ?
                          AND model LIKE ?
                          AND year BETWEEN ? AND ?
                          AND (engine LIKE ? OR engine_displacement LIKE ?)
                    """, (
                        spec['make'],
                        f"%{spec['model']}%",
                        spec['year_min'],
                        spec['year_max'],
                        f"%{spec['engine']}%",
                        f"%{spec['engine']}%"
                    ))
                else:
                    # Match without engine (applies to all engines for model/year)
                    self.cursor.execute("""
                        SELECT vehicle_id
                        FROM vehicles
                        WHERE make = ?
                          AND model LIKE ?
                          AND year BETWEEN ? AND ?
                    """, (
                        spec['make'],
                        f"%{spec['model']}%",
                        spec['year_min'],
                        spec['year_max']
                    ))

                matching_vehicles = self.cursor.fetchall()

                # Create links for each matching vehicle
                for (vehicle_id,) in matching_vehicles:
                    try:
                        self.cursor.execute("""
                            INSERT INTO vehicle_failures (vehicle_id, failure_id)
                            VALUES (?, ?)
                        """, (vehicle_id, failure_id))
                        links_created += 1
                    except sqlite3.IntegrityError:
                        # Link already exists
                        pass

            except sqlite3.Error as e:
                print(f"[ERROR] Failed to link vehicles for {spec}: {str(e)}")

        return links_created

    def import_all_patterns(self, file_path: Path, manufacturer_filter: Optional[str] = None):
        """
        Import all failure patterns from markdown file.

        Args:
            file_path: Path to markdown file
            manufacturer_filter: Optional manufacturer name to filter (e.g., 'FORD')
        """
        # Parse markdown file
        patterns = self.parse_markdown_file(file_path)

        # Filter by manufacturer if specified
        if manufacturer_filter:
            patterns = [p for p in patterns if manufacturer_filter.upper() in p.manufacturer.upper()]
            print(f"[INFO] Filtered to {len(patterns)} patterns for {manufacturer_filter}")

        if not patterns:
            print("[WARNING] No patterns found to import")
            return

        print(f"\n[INFO] Importing {len(patterns)} failure patterns...")

        for i, pattern in enumerate(patterns, 1):
            # Insert failure pattern
            failure_id = self.insert_failure_pattern(pattern)

            if failure_id:
                # Link to vehicles
                links_count = self.link_failure_to_vehicles(failure_id, pattern)
                self.stats['inserted_links'] += links_count

                if links_count > 0:
                    print(f"[{i}/{len(patterns)}] {pattern.manufacturer} - {pattern.name}: "
                          f"Linked to {links_count} vehicles")
                else:
                    print(f"[{i}/{len(patterns)}] {pattern.manufacturer} - {pattern.name}: "
                          f"No matching vehicles found")

            # Commit every 10 patterns
            if not self.dry_run and i % 10 == 0:
                self.conn.commit()

        # Final commit
        if not self.dry_run:
            self.conn.commit()

    def print_statistics(self):
        """Print import statistics."""
        print("\n" + "=" * 70)
        print("FAILURE DATA IMPORT STATISTICS")
        print("=" * 70)
        print(f"Total Patterns Parsed:     {self.stats['total_patterns']:,}")
        print(f"Patterns Inserted:         {self.stats['inserted_patterns']:,}")
        print(f"Vehicle Links Created:     {self.stats['inserted_links']:,}")
        print(f"Errors:                    {self.stats['errors']:,}")

        if self.stats['error_details']:
            print("\nError Details (first 10):")
            for error in self.stats['error_details'][:10]:
                print(f"  - {error}")

        if not self.dry_run and self.cursor:
            # Query database for final counts
            self.cursor.execute("SELECT COUNT(*) FROM failure_patterns")
            total_failures = self.cursor.fetchone()[0]

            self.cursor.execute("SELECT COUNT(*) FROM vehicle_failures")
            total_links = self.cursor.fetchone()[0]

            self.cursor.execute("""
                SELECT COUNT(DISTINCT vehicle_id)
                FROM vehicle_failures
            """)
            vehicles_with_failures = self.cursor.fetchone()[0]

            print(f"\nTotal Failures in Database:    {total_failures:,}")
            print(f"Total Vehicle-Failure Links:   {total_links:,}")
            print(f"Vehicles with Known Failures:  {vehicles_with_failures:,}")

        print("=" * 70 + "\n")


def main():
    """Main entry point for the script."""
    parser = argparse.ArgumentParser(
        description='Import common automotive failure data into SQLite database'
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Parse data but do not write to database'
    )
    parser.add_argument(
        '--manufacturer',
        type=str,
        help='Filter to specific manufacturer (e.g., FORD, GM)'
    )
    parser.add_argument(
        '--db',
        type=str,
        default=str(DATABASE_PATH),
        help=f'Database path (default: {DATABASE_PATH})'
    )
    parser.add_argument(
        '--file',
        type=str,
        default=str(FAILURE_DATA_FILE),
        help=f'Failure data file path (default: {FAILURE_DATA_FILE})'
    )

    args = parser.parse_args()

    # Validate database exists
    db_path = Path(args.db)
    if not args.dry_run and not db_path.exists():
        print(f"[ERROR] Database not found: {db_path}")
        print("        Run init_database_simple.py first")
        sys.exit(1)

    # Validate data file exists
    file_path = Path(args.file)
    if not file_path.exists():
        print(f"[ERROR] Failure data file not found: {file_path}")
        sys.exit(1)

    # Initialize importer
    importer = FailureDataImporter(db_path, dry_run=args.dry_run)

    try:
        importer.connect()

        if args.dry_run:
            print("\n[DRY RUN MODE] - No database changes will be made\n")

        importer.import_all_patterns(file_path, manufacturer_filter=args.manufacturer)
        importer.print_statistics()

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
