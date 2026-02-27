"""
OBD-II Diagnostic Trouble Codes (DTC) Importer

Imports generic diagnostic trouble codes from OBD_II_Diagnostic_Codes.txt
into the SQLite automotive diagnostics database. Parses markdown table format
to extract code, description, and system information.

Usage:
    python import_dtc_codes.py
    python import_dtc_codes.py --dry-run
    python import_dtc_codes.py --system P  # Import only Powertrain codes
"""

import sqlite3
import re
import argparse
import sys
from pathlib import Path
from typing import List, Optional


# Database and file configuration
DATABASE_PATH = Path(__file__).parent / 'automotive_diagnostics.db'
DTC_DATA_FILE = Path(__file__).parent.parent / 'data' / 'raw_imports' / 'OBD_II_Diagnostic_Codes.txt'


# DTC system mapping
DTC_SYSTEMS = {
    'P': 'Powertrain',
    'C': 'Chassis',
    'B': 'Body',
    'U': 'Network & Integration'
}


# Safety-critical DTC keywords
SAFETY_CRITICAL_KEYWORDS = [
    'airbag', 'srs', 'brake', 'abs', 'steering', 'throttle',
    'fuel pump', 'transmission', 'sudden', 'acceleration',
    'engine stall', 'loss of power', 'misfire', 'detonation'
]


# Severity classification keywords
SEVERITY_HIGH = [
    'malfunction', 'failure', 'circuit open', 'short', 'engine stall',
    'no signal', 'no activity', 'catalyst efficiency', 'misfire'
]

SEVERITY_MEDIUM = [
    'range/performance', 'intermittent', 'slow response', 'incorrect',
    'rationality', 'correlation'
]

SEVERITY_LOW = [
    'circuit low', 'circuit high', 'bank', 'sensor'
]


class DTCCode:
    """Represents a single diagnostic trouble code."""

    def __init__(self, code: str, description: str):
        self.code = code.strip().upper()
        self.description = description.strip()
        self.system = self._get_system()
        self.subsystem = self._extract_subsystem()
        self.severity = self._classify_severity()
        self.safety_critical = self._is_safety_critical()
        self.drivability_impact = self._assess_drivability()
        self.emissions_impact = self._assess_emissions()

    def _get_system(self) -> str:
        """Get system name from DTC prefix."""
        if not self.code:
            return "Unknown"
        return DTC_SYSTEMS.get(self.code[0], "Unknown")

    def _extract_subsystem(self) -> Optional[str]:
        """Extract subsystem from description."""
        desc_lower = self.description.lower()

        # Engine subsystems
        if 'fuel' in desc_lower or 'injector' in desc_lower:
            return 'Fuel System'
        elif 'ignition' in desc_lower or 'spark' in desc_lower or 'coil' in desc_lower:
            return 'Ignition System'
        elif 'o2' in desc_lower or 'oxygen' in desc_lower or 'sensor' in desc_lower and 'bank' in desc_lower:
            return 'Oxygen Sensors'
        elif 'catalyst' in desc_lower or 'cat' in desc_lower:
            return 'Emissions/Catalyst'
        elif 'misfire' in desc_lower:
            return 'Combustion/Misfire'
        elif 'throttle' in desc_lower or 'pedal' in desc_lower or 'tps' in desc_lower:
            return 'Throttle Control'
        elif 'maf' in desc_lower or 'air flow' in desc_lower or 'mass air' in desc_lower:
            return 'Air Intake'
        elif 'map' in desc_lower or 'manifold pressure' in desc_lower or 'vacuum' in desc_lower:
            return 'Intake Manifold'
        elif 'coolant' in desc_lower or 'temperature' in desc_lower and 'engine' in desc_lower:
            return 'Cooling System'
        elif 'transmission' in desc_lower or 'gear' in desc_lower or 'shift' in desc_lower:
            return 'Transmission'
        elif 'evap' in desc_lower or 'purge' in desc_lower or 'vapor' in desc_lower:
            return 'EVAP System'
        elif 'egr' in desc_lower or 'exhaust gas' in desc_lower:
            return 'EGR System'
        elif 'variable valve' in desc_lower or 'vvt' in desc_lower or 'camshaft' in desc_lower:
            return 'Variable Valve Timing'

        # Chassis subsystems
        elif 'abs' in desc_lower or 'anti-lock' in desc_lower:
            return 'ABS'
        elif 'traction' in desc_lower or 'tcs' in desc_lower:
            return 'Traction Control'
        elif 'steering' in desc_lower:
            return 'Steering'
        elif 'suspension' in desc_lower or 'ride' in desc_lower:
            return 'Suspension'
        elif 'wheel speed' in desc_lower:
            return 'Wheel Speed Sensors'

        # Body subsystems
        elif 'airbag' in desc_lower or 'srs' in desc_lower:
            return 'Airbag/SRS'
        elif 'seat belt' in desc_lower or 'restraint' in desc_lower:
            return 'Restraint System'

        # Network subsystems
        elif 'communication' in desc_lower or 'can' in desc_lower or 'network' in desc_lower:
            return 'Vehicle Network'
        elif 'module' in desc_lower or 'ecm' in desc_lower or 'pcm' in desc_lower:
            return 'Control Modules'

        return None

    def _classify_severity(self) -> str:
        """Classify DTC severity based on description."""
        desc_lower = self.description.lower()

        # Check for high severity indicators
        if any(keyword in desc_lower for keyword in SEVERITY_HIGH):
            return 'HIGH'

        # Check for medium severity indicators
        elif any(keyword in desc_lower for keyword in SEVERITY_MEDIUM):
            return 'MEDIUM'

        # Default to low
        else:
            return 'LOW'

    def _is_safety_critical(self) -> bool:
        """Determine if DTC is safety-critical."""
        search_text = f"{self.code} {self.description}".lower()
        return any(keyword in search_text for keyword in SAFETY_CRITICAL_KEYWORDS)

    def _assess_drivability(self) -> Optional[str]:
        """Assess impact on vehicle drivability."""
        desc_lower = self.description.lower()

        if any(kw in desc_lower for kw in ['engine stall', 'no start', 'loss of power', 'misfire']):
            return 'SEVERE'
        elif any(kw in desc_lower for kw in ['transmission', 'shift', 'hesitation', 'rough']):
            return 'MODERATE'
        elif any(kw in desc_lower for kw in ['circuit', 'sensor', 'range']):
            return 'MINOR'
        else:
            return 'MINIMAL'

    def _assess_emissions(self) -> Optional[str]:
        """Assess impact on vehicle emissions."""
        desc_lower = self.description.lower()

        if any(kw in desc_lower for kw in ['catalyst', 'evap', 'o2', 'oxygen', 'lean', 'rich']):
            return 'HIGH'
        elif any(kw in desc_lower for kw in ['fuel', 'air', 'egr', 'purge']):
            return 'MEDIUM'
        else:
            return 'LOW'

    def is_valid(self) -> bool:
        """Check if DTC code is valid format."""
        # Valid DTC format: Letter + 4 hex digits (P0123, C1234, etc.)
        pattern = r'^[PCBU][0-3][0-9A-F]{3}$'
        return bool(re.match(pattern, self.code))


class DTCImporter:
    """Imports DTC codes from markdown file into SQLite database."""

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
            'total_parsed': 0,
            'valid_codes': 0,
            'invalid_codes': 0,
            'inserted': 0,
            'duplicates': 0,
            'errors': 0,
            'by_system': {}
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

    def parse_markdown_table(self, file_path: Path, system_filter: Optional[str] = None) -> List[DTCCode]:
        """
        Parse DTC codes from markdown table file.

        Args:
            file_path: Path to markdown file
            system_filter: Optional system filter (P, C, B, U)

        Returns:
            List of DTCCode objects
        """
        print(f"[INFO] Parsing {file_path.name}...")

        codes = []
        in_table = False

        with open(file_path, 'r', encoding='utf-8') as f:
            for line_num, line in enumerate(f, 1):
                line = line.strip()

                # Detect section headers
                if line.startswith('Specific') or line.startswith('Part'):
                    in_table = False
                    continue

                # Detect table headers
                if line.startswith('| DTC |') or line.startswith('| Code |'):
                    in_table = True
                    continue

                # Skip table separator lines
                if line.startswith('|---'):
                    continue

                # Parse table rows
                if in_table and line.startswith('|'):
                    parts = [p.strip() for p in line.split('|')]

                    # Expect format: | Code | Description | Source |
                    if len(parts) >= 4:  # ['', 'Code', 'Description', 'Source', '']
                        code = parts[1].strip()
                        description = parts[2].strip()

                        # Skip if empty
                        if not code or not description:
                            continue

                        # Clean up any formatting issues
                        # Remove "...source" artifacts
                        description = re.sub(r'\.\.\.source\s*', '', description)

                        # Apply system filter if specified
                        if system_filter and not code.startswith(system_filter):
                            continue

                        # Create DTC object
                        dtc = DTCCode(code, description)

                        self.stats['total_parsed'] += 1

                        if dtc.is_valid():
                            codes.append(dtc)
                            self.stats['valid_codes'] += 1

                            # Track by system
                            system = dtc.system
                            self.stats['by_system'][system] = self.stats['by_system'].get(system, 0) + 1
                        else:
                            self.stats['invalid_codes'] += 1
                            if not self.dry_run:
                                print(f"[WARNING] Invalid DTC format: {code} (line {line_num})")

        print(f"[INFO] Parsed {len(codes)} valid DTC codes")
        return codes

    def insert_dtc_code(self, dtc: DTCCode) -> bool:
        """
        Insert DTC code into database.

        Args:
            dtc: DTCCode object

        Returns:
            True if inserted, False if duplicate or error
        """
        if self.dry_run:
            return True

        try:
            self.cursor.execute("""
                INSERT INTO dtc_codes (
                    code, system, subsystem, description,
                    severity, drivability_impact, emissions_impact,
                    safety_critical, standard
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                dtc.code,
                dtc.system,
                dtc.subsystem,
                dtc.description,
                dtc.severity,
                dtc.drivability_impact,
                dtc.emissions_impact,
                1 if dtc.safety_critical else 0,
                'SAE J2012'  # All generic codes follow SAE standard
            ))

            self.stats['inserted'] += 1
            return True

        except sqlite3.IntegrityError:
            # Duplicate code
            self.stats['duplicates'] += 1
            return False

        except sqlite3.Error as e:
            self.stats['errors'] += 1
            print(f"[ERROR] Failed to insert {dtc.code}: {str(e)}")
            return False

    def import_all_codes(self, file_path: Path, system_filter: Optional[str] = None):
        """
        Import all DTC codes from file.

        Args:
            file_path: Path to markdown file
            system_filter: Optional system filter (P, C, B, U)
        """
        # Parse codes
        codes = self.parse_markdown_table(file_path, system_filter)

        if not codes:
            print("[WARNING] No codes found to import")
            return

        print(f"\n[INFO] Importing {len(codes)} DTC codes...")

        # Insert codes
        for i, dtc in enumerate(codes, 1):
            self.insert_dtc_code(dtc)

            if self.dry_run:
                if i % 50 == 0:
                    print(f"[DRY RUN] Parsed {i}/{len(codes)} codes...")
            else:
                if i % 50 == 0:
                    print(f"[{i}/{len(codes)}] Inserted: {self.stats['inserted']}, "
                          f"Duplicates: {self.stats['duplicates']}")
                    self.conn.commit()

        # Final commit
        if not self.dry_run:
            self.conn.commit()

    def print_statistics(self):
        """Print import statistics."""
        print("\n" + "=" * 70)
        print("DTC CODES IMPORT STATISTICS")
        print("=" * 70)
        print(f"Total Codes Parsed:        {self.stats['total_parsed']:,}")
        print(f"Valid Codes:               {self.stats['valid_codes']:,}")
        print(f"Invalid Codes:             {self.stats['invalid_codes']:,}")
        print(f"Codes Inserted:            {self.stats['inserted']:,}")
        print(f"Duplicates Skipped:        {self.stats['duplicates']:,}")
        print(f"Errors:                    {self.stats['errors']:,}")

        print("\nCodes by System:")
        for system, count in sorted(self.stats['by_system'].items()):
            print(f"  {system:25s}: {count:4d}")

        if not self.dry_run and self.cursor:
            # Query database for final counts
            self.cursor.execute("SELECT COUNT(*) FROM dtc_codes")
            total_codes = self.cursor.fetchone()[0]

            self.cursor.execute("SELECT COUNT(*) FROM dtc_codes WHERE safety_critical = 1")
            safety_count = self.cursor.fetchone()[0]

            self.cursor.execute("""
                SELECT system, COUNT(*) as count
                FROM dtc_codes
                GROUP BY system
                ORDER BY count DESC
            """)
            system_counts = self.cursor.fetchall()

            print(f"\nTotal DTC Codes in Database:    {total_codes:,}")
            print(f"Safety-Critical Codes:          {safety_count:,} ({safety_count/total_codes*100:.1f}%)")

            print("\nDatabase Counts by System:")
            for system, count in system_counts:
                print(f"  {system:25s}: {count:4d}")

        print("=" * 70 + "\n")


def main():
    """Main entry point for the script."""
    parser = argparse.ArgumentParser(
        description='Import OBD-II diagnostic trouble codes into SQLite database'
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Parse data but do not write to database'
    )
    parser.add_argument(
        '--system',
        type=str,
        choices=['P', 'C', 'B', 'U'],
        help='Filter to specific system (P=Powertrain, C=Chassis, B=Body, U=Network)'
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
        default=str(DTC_DATA_FILE),
        help=f'DTC data file path (default: {DTC_DATA_FILE})'
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
        print(f"[ERROR] DTC data file not found: {file_path}")
        sys.exit(1)

    # Initialize importer
    importer = DTCImporter(db_path, dry_run=args.dry_run)

    try:
        importer.connect()

        if args.dry_run:
            print("\n[DRY RUN MODE] - No database changes will be made\n")

        importer.import_all_codes(file_path, system_filter=args.system)
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
