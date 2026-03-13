#!/usr/bin/env python3
# Checked AGENTS.md - implementing directly: standalone data import utility,
# CSV parse + INSERT OR IGNORE, no auth/security surface.
"""
Import EPA FuelEconomy.gov vehicle data into epa_vehicles table.

Usage:
    python scripts/import_epa_vehicles.py data/raw_imports/epa/vehicles.csv

Downloads from: https://www.fueleconomy.gov/feg/epadata/vehicles.csv.zip

Key columns used:
    year, make, model, VClass, fuelType, cylinders, displ,
    drive, trany (transmission), tCharger, sCharger,
    city08, highway08, comb08, co2, fuelCost08
"""

import sys
import csv
import sqlite3
from pathlib import Path
from datetime import datetime
from typing import Optional


PROJECT_ROOT = Path(__file__).parent.parent
DB_PATH = PROJECT_ROOT / "database" / "automotive_complaints.db"

# Map EPA transmission codes to human-readable
TRANS_MAP = {
    'A': 'Automatic',
    'M': 'Manual',
    'AV': 'CVT',
    'AM': 'Automated Manual',
    'S': 'Semi-Auto',
}


def normalize_transmission(trany: str) -> tuple[str, str]:
    """Return (code, descriptor) from EPA 'trany' field like 'Automatic 6-spd'."""
    if not trany:
        return '', ''
    trany = trany.strip()
    # EPA format is descriptive: "Automatic 6-spd", "Manual 5-spd", "CVT"
    return trany, trany


def safe_int(val: str, default: Optional[int] = None) -> Optional[int]:
    try:
        stripped = val.strip()
        return int(float(stripped)) if stripped and stripped not in ('', 'N/A', '-1') else default
    except (ValueError, TypeError):
        return default


def safe_float(val: str, default: Optional[float] = None) -> Optional[float]:
    try:
        stripped = val.strip()
        return float(stripped) if stripped and stripped not in ('', 'N/A') else default
    except (ValueError, TypeError):
        return default


def import_epa_vehicles(file_path: Path) -> dict[str, int]:
    stats: dict[str, int] = {'total': 0, 'imported': 0, 'skipped': 0}
    start = datetime.now()

    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA synchronous=NORMAL")

    sql = """
    INSERT OR IGNORE INTO epa_vehicles
        (year, make, model, vehicle_class, fuel_type, engine_cylinders,
         engine_displacement, drive, transmission, transmission_descriptor,
         turbo, supercharged, mpg_city, mpg_highway, mpg_combined,
         co2_gpm, annual_fuel_cost)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """

    batch: list[tuple] = []
    batch_size = 2000

    with open(file_path, 'r', encoding='utf-8', errors='replace', newline='') as f:
        reader = csv.DictReader(f)
        print(f"  EPA CSV columns: {list(reader.fieldnames or [])[:20]}")

        for row in reader:
            stats['total'] += 1

            year = safe_int(row.get('year', ''))
            make = row.get('make', '').strip()
            model = row.get('model', '').strip()

            if not make or not model or year is None:
                stats['skipped'] += 1
                continue

            trany = row.get('trany', '')
            trans_code, trans_desc = normalize_transmission(trany)

            turbo = 1 if row.get('tCharger', '').strip().upper() == 'T' else 0
            supercharged = 1 if row.get('sCharger', '').strip().upper() == 'S' else 0

            record = (
                year,
                make,
                model,
                row.get('VClass', '').strip(),
                row.get('fuelType1', row.get('fuelType', '')).strip(),
                safe_int(row.get('cylinders', '')),
                safe_float(row.get('displ', '')),
                row.get('drive', '').strip(),
                trans_code,
                trans_desc,
                turbo,
                supercharged,
                safe_int(row.get('city08', '')),
                safe_int(row.get('highway08', '')),
                safe_int(row.get('comb08', '')),
                safe_int(row.get('co2', '')),
                safe_int(row.get('fuelCost08', '')),
            )
            batch.append(record)

            if len(batch) >= batch_size:
                conn.executemany(sql, batch)
                conn.commit()
                stats['imported'] += len(batch)
                batch = []

            if stats['total'] % 10000 == 0:
                print(f"  {stats['total']:,} rows | {stats['imported']:,} imported")

    if batch:
        conn.executemany(sql, batch)
        conn.commit()
        stats['imported'] += len(batch)

    conn.close()
    elapsed = (datetime.now() - start).total_seconds()
    print(f"\nEPA vehicles import complete: {stats['imported']:,} imported in {elapsed:.1f}s")
    return stats


def main() -> None:
    if len(sys.argv) != 2:
        print("Usage: python scripts/import_epa_vehicles.py <path_to_vehicles.csv>")
        sys.exit(1)

    file_path = Path(sys.argv[1])
    if not file_path.exists():
        print(f"File not found: {file_path}")
        sys.exit(1)

    print(f"\nImporting EPA vehicle specs from {file_path.name}...")
    import_epa_vehicles(file_path)


if __name__ == '__main__':
    main()
