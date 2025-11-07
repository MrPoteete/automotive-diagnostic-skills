#!/usr/bin/env python3
"""
Quick data exploration tool for NHTSA complaints database.

Usage:
    python scripts/explore_complaints.py
"""

import sqlite3
from pathlib import Path


def run_query(db_path: Path, query: str, description: str):
    """Run a query and display results."""
    print(f"\n{'='*80}")
    print(f"{description}")
    print(f"{'='*80}\n")

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    try:
        cursor.execute(query)
        rows = cursor.fetchall()

        # Get column names
        if cursor.description:
            headers = [desc[0] for desc in cursor.description]

            # Calculate column widths
            col_widths = [len(h) for h in headers]
            for row in rows:
                for i, val in enumerate(row):
                    col_widths[i] = max(col_widths[i], len(str(val)))

            # Print headers
            header_line = " | ".join(h.ljust(w) for h, w in zip(headers, col_widths))
            print(header_line)
            print("-" * len(header_line))

            # Print rows
            for row in rows:
                print(" | ".join(str(val).ljust(w) for val, w in zip(row, col_widths)))

        print(f"\n({len(rows)} rows)\n")

    except sqlite3.Error as e:
        print(f"❌ Error: {e}\n")
    finally:
        conn.close()


def main():
    db_path = Path('database/automotive_diagnostics.db')

    if not db_path.exists():
        print(f"❌ Database not found: {db_path}")
        return

    print("\n" + "="*80)
    print("NHTSA COMPLAINTS DATABASE EXPLORER")
    print("="*80)

    # Query 1: Total counts
    run_query(db_path,
        "SELECT COUNT(*) as total_complaints FROM nhtsa_complaints;",
        "📊 TOTAL COMPLAINTS IN DATABASE")

    # Query 2: Most complained-about vehicles
    run_query(db_path,
        """SELECT make, model, year, COUNT(*) as complaints
           FROM nhtsa_complaints
           GROUP BY make, model, year
           ORDER BY complaints DESC
           LIMIT 10;""",
        "🚗 TOP 10 MOST COMPLAINED-ABOUT VEHICLES")

    # Query 3: Safety-critical statistics
    run_query(db_path,
        """SELECT
               COUNT(*) as total_safety_critical,
               SUM(CASE WHEN fire_flag = 'Y' THEN 1 ELSE 0 END) as fires,
               SUM(CASE WHEN crash_flag = 'Y' THEN 1 ELSE 0 END) as crashes,
               SUM(num_injuries) as total_injuries,
               SUM(num_deaths) as total_deaths
           FROM nhtsa_complaints
           WHERE fire_flag = 'Y' OR crash_flag = 'Y' OR num_injuries > 0 OR num_deaths > 0;""",
        "⚠️  SAFETY-CRITICAL INCIDENTS")

    # Query 4: Complaints by manufacturer
    run_query(db_path,
        """SELECT manufacturer_name, COUNT(*) as complaints
           FROM nhtsa_complaints
           GROUP BY manufacturer_name
           ORDER BY complaints DESC
           LIMIT 10;""",
        "🏢 TOP 10 MANUFACTURERS BY COMPLAINT COUNT")

    # Query 5: Ford F-150 statistics
    run_query(db_path,
        """SELECT year, COUNT(*) as complaints
           FROM nhtsa_complaints
           WHERE make = 'FORD' AND model = 'F-150'
           GROUP BY year
           ORDER BY year DESC
           LIMIT 15;""",
        "🔧 FORD F-150 COMPLAINTS BY YEAR (Last 15 years)")

    # Query 6: Most common component issues
    run_query(db_path,
        """SELECT component_description, COUNT(*) as frequency
           FROM nhtsa_complaints
           WHERE component_description != ''
           GROUP BY component_description
           ORDER BY frequency DESC
           LIMIT 10;""",
        "⚙️  TOP 10 MOST COMMONLY COMPLAINED-ABOUT COMPONENTS")

    # Query 7: RAM 1500 specific (your focus vehicles)
    run_query(db_path,
        """SELECT year, COUNT(*) as complaints
           FROM nhtsa_complaints
           WHERE make = 'RAM' AND model = '1500'
           AND year BETWEEN 2015 AND 2025
           GROUP BY year
           ORDER BY year DESC;""",
        "🚙 RAM 1500 (2015-2025) COMPLAINTS BY YEAR")

    # Query 8: Chevrolet Silverado (your focus vehicles)
    run_query(db_path,
        """SELECT year, COUNT(*) as complaints
           FROM nhtsa_complaints
           WHERE make = 'CHEVROLET' AND model = 'SILVERADO'
           AND year BETWEEN 2015 AND 2025
           GROUP BY year
           ORDER BY year DESC;""",
        "🚙 CHEVROLET SILVERADO (2015-2025) COMPLAINTS BY YEAR")

    print("="*80)
    print("✅ Exploration complete!")
    print("\nTo run custom queries, use:")
    print("  python -c \"import sqlite3; conn = sqlite3.connect('database/automotive_diagnostics.db'); ...")
    print("="*80)
    print()


if __name__ == '__main__':
    main()
