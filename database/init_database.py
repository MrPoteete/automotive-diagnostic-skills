#!/usr/bin/env python3
"""
Automotive Diagnostic System - Database Initialization
Creates and initializes the SQLite database with optimized schema.
"""

import sqlite3
import os
from pathlib import Path
from datetime import datetime

# Database configuration
DB_FILE = "automotive_diagnostics.db"
SCHEMA_FILE = "schema.sql"

class DatabaseInitializer:
    """Initialize and manage the automotive diagnostic database."""

    def __init__(self, db_path=None, schema_path=None):
        """
        Initialize database manager.

        Args:
            db_path: Path to database file (default: automotive_diagnostics.db)
            schema_path: Path to schema SQL file (default: schema.sql)
        """
        self.db_path = db_path or DB_FILE
        self.schema_path = schema_path or SCHEMA_FILE
        self.conn = None

    def create_database(self, force_recreate=False):
        """
        Create database with schema.

        Args:
            force_recreate: If True, delete existing database and create new one

        Returns:
            bool: True if successful, False otherwise
        """
        # Check if database exists
        db_exists = os.path.exists(self.db_path)

        if db_exists and force_recreate:
            print(f"🗑️  Removing existing database: {self.db_path}")
            os.remove(self.db_path)
            db_exists = False

        if db_exists:
            print(f"ℹ️  Database already exists: {self.db_path}")
            print(f"   Use force_recreate=True to rebuild")
            return False

        # Read schema file
        if not os.path.exists(self.schema_path):
            print(f"❌ Schema file not found: {self.schema_path}")
            return False

        print(f"📄 Reading schema from: {self.schema_path}")
        with open(self.schema_path, 'r', encoding='utf-8') as f:
            schema_sql = f.read()

        # Create database
        print(f"🔨 Creating database: {self.db_path}")
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            # Enable foreign keys
            cursor.execute("PRAGMA foreign_keys = ON")

            # Execute schema
            cursor.executescript(schema_sql)
            conn.commit()

            # Verify creation
            cursor.execute("SELECT value FROM metadata WHERE key = 'schema_version'")
            version = cursor.fetchone()

            if version:
                print(f"✅ Database created successfully!")
                print(f"   Schema version: {version[0]}")

                # Get table count
                cursor.execute("SELECT COUNT(*) FROM sqlite_master WHERE type='table'")
                table_count = cursor.fetchone()[0]
                print(f"   Tables created: {table_count}")

                # Get index count
                cursor.execute("SELECT COUNT(*) FROM sqlite_master WHERE type='index'")
                index_count = cursor.fetchone()[0]
                print(f"   Indexes created: {index_count}")

                conn.close()
                return True
            else:
                print(f"⚠️  Database created but metadata not found")
                conn.close()
                return False

        except sqlite3.Error as e:
            print(f"❌ Database creation failed: {e}")
            return False

    def connect(self):
        """
        Connect to database.

        Returns:
            sqlite3.Connection: Database connection
        """
        if not os.path.exists(self.db_path):
            print(f"❌ Database not found: {self.db_path}")
            print(f"   Run create_database() first")
            return None

        try:
            self.conn = sqlite3.connect(self.db_path)
            self.conn.row_factory = sqlite3.Row  # Enable column access by name
            self.conn.execute("PRAGMA foreign_keys = ON")
            return self.conn
        except sqlite3.Error as e:
            print(f"❌ Connection failed: {e}")
            return None

    def disconnect(self):
        """Close database connection."""
        if self.conn:
            self.conn.close()
            self.conn = None

    def get_stats(self):
        """
        Get database statistics.

        Returns:
            dict: Database statistics
        """
        if not self.conn:
            self.connect()

        cursor = self.conn.cursor()

        stats = {}

        # Table counts
        tables = [
            'vehicles', 'dtc_codes', 'failure_patterns',
            'parts', 'diagnostic_tests', 'service_procedures',
            'tsbs', 'recalls'
        ]

        for table in tables:
            cursor.execute(f"SELECT COUNT(*) FROM {table}")
            count = cursor.fetchone()[0]
            stats[table] = count

        # Database size
        stats['database_size_mb'] = os.path.getsize(self.db_path) / (1024 * 1024)

        return stats

    def print_stats(self):
        """Print database statistics."""
        stats = self.get_stats()

        print("\n📊 Database Statistics")
        print("=" * 50)
        print(f"Database file: {self.db_path}")
        print(f"Size: {stats['database_size_mb']:.2f} MB")
        print("\nRecord Counts:")
        print(f"  Vehicles:           {stats['vehicles']:>8,}")
        print(f"  DTC Codes:          {stats['dtc_codes']:>8,}")
        print(f"  Failure Patterns:   {stats['failure_patterns']:>8,}")
        print(f"  Parts:              {stats['parts']:>8,}")
        print(f"  Diagnostic Tests:   {stats['diagnostic_tests']:>8,}")
        print(f"  Service Procedures: {stats['service_procedures']:>8,}")
        print(f"  TSBs:               {stats['tsbs']:>8,}")
        print(f"  Recalls:            {stats['recalls']:>8,}")
        print("=" * 50)

    def verify_schema(self):
        """
        Verify database schema integrity.

        Returns:
            bool: True if schema is valid
        """
        if not self.conn:
            self.connect()

        cursor = self.conn.cursor()

        print("\n🔍 Verifying Schema...")

        # Check required tables
        required_tables = [
            'vehicles', 'dtc_codes', 'failure_patterns', 'parts',
            'vehicle_failures', 'dtc_failure_correlations', 'failure_parts',
            'diagnostic_tests', 'service_procedures', 'tsbs', 'recalls',
            'metadata'
        ]

        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        existing_tables = {row[0] for row in cursor.fetchall()}

        missing_tables = set(required_tables) - existing_tables

        if missing_tables:
            print(f"❌ Missing tables: {', '.join(missing_tables)}")
            return False

        print(f"✅ All required tables present ({len(required_tables)} tables)")

        # Check foreign key constraints
        cursor.execute("PRAGMA foreign_key_check")
        fk_errors = cursor.fetchall()

        if fk_errors:
            print(f"❌ Foreign key constraint violations: {len(fk_errors)}")
            return False

        print(f"✅ Foreign key constraints valid")

        # Check indexes
        cursor.execute("SELECT COUNT(*) FROM sqlite_master WHERE type='index'")
        index_count = cursor.fetchone()[0]
        print(f"✅ Indexes created: {index_count}")

        print("\n✅ Schema validation successful!")
        return True

    def optimize(self):
        """Optimize database for query performance."""
        if not self.conn:
            self.connect()

        print("\n⚡ Optimizing database...")

        cursor = self.conn.cursor()

        # Analyze tables for query planner
        print("  Analyzing tables...")
        cursor.execute("ANALYZE")

        # Optimize indexes
        print("  Optimizing indexes...")
        cursor.execute("PRAGMA optimize")

        # Vacuum to defragment
        print("  Vacuuming database...")
        cursor.execute("VACUUM")

        self.conn.commit()
        print("✅ Optimization complete!")

    def backup(self, backup_path=None):
        """
        Create database backup.

        Args:
            backup_path: Path for backup file (default: automotive_diagnostics_backup_YYYYMMDD.db)

        Returns:
            str: Path to backup file
        """
        if not backup_path:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_path = f"automotive_diagnostics_backup_{timestamp}.db"

        print(f"\n💾 Creating backup: {backup_path}")

        if not self.conn:
            self.connect()

        # Create backup
        backup_conn = sqlite3.connect(backup_path)
        self.conn.backup(backup_conn)
        backup_conn.close()

        backup_size = os.path.getsize(backup_path) / (1024 * 1024)
        print(f"✅ Backup created: {backup_size:.2f} MB")

        return backup_path


def main():
    """Main function for command-line usage."""
    import argparse

    parser = argparse.ArgumentParser(
        description='Initialize Automotive Diagnostic Database'
    )
    parser.add_argument(
        '--db',
        default='automotive_diagnostics.db',
        help='Database file path (default: automotive_diagnostics.db)'
    )
    parser.add_argument(
        '--schema',
        default='schema.sql',
        help='Schema SQL file path (default: schema.sql)'
    )
    parser.add_argument(
        '--force',
        action='store_true',
        help='Force recreate database (deletes existing)'
    )
    parser.add_argument(
        '--stats',
        action='store_true',
        help='Show database statistics'
    )
    parser.add_argument(
        '--verify',
        action='store_true',
        help='Verify schema integrity'
    )
    parser.add_argument(
        '--optimize',
        action='store_true',
        help='Optimize database performance'
    )
    parser.add_argument(
        '--backup',
        action='store_true',
        help='Create database backup'
    )

    args = parser.parse_args()

    # Initialize database manager
    db = DatabaseInitializer(db_path=args.db, schema_path=args.schema)

    # Create database if requested
    if not args.stats and not args.verify and not args.optimize and not args.backup:
        db.create_database(force_recreate=args.force)

    # Show stats
    if args.stats:
        db.connect()
        db.print_stats()
        db.disconnect()

    # Verify schema
    if args.verify:
        db.connect()
        db.verify_schema()
        db.disconnect()

    # Optimize
    if args.optimize:
        db.connect()
        db.optimize()
        db.disconnect()

    # Backup
    if args.backup:
        db.connect()
        db.backup()
        db.disconnect()


if __name__ == "__main__":
    main()
