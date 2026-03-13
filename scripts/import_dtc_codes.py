#!/usr/bin/env python3
# Checked AGENTS.md - implementing directly: standalone data import utility,
# CSV parse + INSERT OR IGNORE, no auth/security surface.
"""
Import OBD-II DTC codes from mytrile/obd-trouble-codes CSV into dtc_codes table.

Source: https://github.com/mytrile/obd-trouble-codes (MIT License)
Download: data/raw_imports/obd/obd-trouble-codes.csv

Usage:
    python scripts/import_dtc_codes.py data/raw_imports/obd/obd-trouble-codes.csv
"""

import sys
import csv
import re
import sqlite3
from pathlib import Path
from typing import Optional


PROJECT_ROOT = Path(__file__).parent.parent
DB_PATH = PROJECT_ROOT / "database" / "automotive_diagnostics.db"

DTC_SYSTEMS = {
    "P": "Powertrain",
    "C": "Chassis",
    "B": "Body",
    "U": "Network & Integration",
}

SAFETY_CRITICAL_KEYWORDS = [
    "airbag", "srs", "brake", "abs", "steering", "throttle",
    "fuel pump", "transmission", "sudden", "acceleration",
    "engine stall", "loss of power", "misfire", "detonation",
]

SEVERITY_HIGH = [
    "malfunction", "failure", "circuit open", "short", "engine stall",
    "no signal", "no activity", "catalyst efficiency", "misfire",
]

SEVERITY_MEDIUM = [
    "range/performance", "intermittent", "slow response", "incorrect",
    "rationality", "correlation",
]

DTC_PATTERN = re.compile(r"^[PCBU][0-3][0-9A-F]{3}$")


def get_system(code: str) -> str:
    return DTC_SYSTEMS.get(code[0].upper(), "Unknown") if code else "Unknown"


def get_subsystem(code: str, desc: str) -> Optional[str]:
    d = desc.lower()
    if "fuel" in d or "injector" in d:
        return "Fuel System"
    if "ignition" in d or "spark" in d or "coil" in d:
        return "Ignition System"
    if ("o2" in d or "oxygen" in d) and "sensor" in d:
        return "Oxygen Sensors"
    if "catalyst" in d or ("cat" in d and "catalytic" in d):
        return "Emissions/Catalyst"
    if "misfire" in d:
        return "Combustion/Misfire"
    if "throttle" in d or "pedal" in d or "tps" in d:
        return "Throttle Control"
    if "maf" in d or "air flow" in d or "mass air" in d:
        return "Air Intake"
    if "map" in d or "manifold pressure" in d or "vacuum" in d:
        return "Intake Manifold"
    if "coolant" in d or ("temperature" in d and "engine" in d):
        return "Cooling System"
    if "transmission" in d or ("gear" in d and "shift" in d):
        return "Transmission"
    if "evap" in d or "purge" in d or "vapor" in d:
        return "EVAP System"
    if "egr" in d or "exhaust gas recirculation" in d:
        return "EGR System"
    if "variable valve" in d or "vvt" in d or "camshaft" in d:
        return "Variable Valve Timing"
    if "abs" in d or "anti-lock" in d:
        return "ABS"
    if "traction" in d or "tcs" in d:
        return "Traction Control"
    if "steering" in d:
        return "Steering"
    if "suspension" in d:
        return "Suspension"
    if "wheel speed" in d:
        return "Wheel Speed Sensors"
    if "airbag" in d or "srs" in d:
        return "Airbag/SRS"
    if "seat belt" in d or "restraint" in d:
        return "Restraint System"
    if "communication" in d or " can " in d or "network" in d:
        return "Vehicle Network"
    if "module" in d or "ecm" in d or "pcm" in d:
        return "Control Modules"
    return None


def get_severity(desc: str) -> str:
    d = desc.lower()
    if any(kw in d for kw in SEVERITY_HIGH):
        return "HIGH"
    if any(kw in d for kw in SEVERITY_MEDIUM):
        return "MEDIUM"
    return "LOW"


def is_safety_critical(code: str, desc: str) -> int:
    text = f"{code} {desc}".lower()
    return 1 if any(kw in text for kw in SAFETY_CRITICAL_KEYWORDS) else 0


def get_drivability(desc: str) -> str:
    d = desc.lower()
    if any(kw in d for kw in ["engine stall", "no start", "loss of power", "misfire"]):
        return "SEVERE"
    if any(kw in d for kw in ["transmission", "shift", "hesitation", "rough"]):
        return "MODERATE"
    if any(kw in d for kw in ["circuit", "sensor", "range"]):
        return "MINOR"
    return "MINIMAL"


def get_emissions(desc: str) -> str:
    d = desc.lower()
    if any(kw in d for kw in ["catalyst", "evap", "o2", "oxygen", "lean", "rich"]):
        return "HIGH"
    if any(kw in d for kw in ["fuel", "air", "egr", "purge"]):
        return "MEDIUM"
    return "LOW"


def import_dtc_codes(file_path: Path) -> dict[str, int]:
    stats: dict[str, int] = {"total": 0, "imported": 0, "skipped": 0}

    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA synchronous=NORMAL")

    sql = """
    INSERT OR IGNORE INTO dtc_codes
        (code, system, subsystem, description, severity,
         drivability_impact, emissions_impact, safety_critical, standard)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """

    batch: list[tuple] = []
    batch_size = 500

    with open(file_path, "r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f, fieldnames=["Code", "Description"])
        for row in reader:
            stats["total"] += 1
            code = row.get("Code", "").strip().upper()
            desc = row.get("Description", "").strip()

            if not code or not desc or not DTC_PATTERN.match(code):
                stats["skipped"] += 1
                continue

            batch.append((
                code,
                get_system(code),
                get_subsystem(code, desc),
                desc,
                get_severity(desc),
                get_drivability(desc),
                get_emissions(desc),
                is_safety_critical(code, desc),
                "SAE J2012",
            ))

            if len(batch) >= batch_size:
                conn.executemany(sql, batch)
                conn.commit()
                stats["imported"] += len(batch)
                batch = []

    if batch:
        conn.executemany(sql, batch)
        conn.commit()
        stats["imported"] += len(batch)

    # Print breakdown by system
    cur = conn.cursor()
    cur.execute(
        "SELECT system, COUNT(*) FROM dtc_codes GROUP BY system ORDER BY COUNT(*) DESC"
    )
    rows = cur.fetchall()
    cur.execute("SELECT COUNT(*) FROM dtc_codes WHERE safety_critical = 1")
    safety_count = cur.fetchone()[0]
    conn.close()

    print(f"\nDTC import complete: {stats['imported']:,} imported, {stats['skipped']:,} skipped")
    print(f"Safety-critical codes: {safety_count:,}")
    print("\nBy system:")
    for system, count in rows:
        print(f"  {system}: {count:,}")

    return stats


def main() -> None:
    if len(sys.argv) != 2:
        print("Usage: python scripts/import_dtc_codes.py <path_to_obd-trouble-codes.csv>")
        sys.exit(1)

    file_path = Path(sys.argv[1])
    if not file_path.exists():
        print(f"File not found: {file_path}")
        sys.exit(1)

    print(f"\nImporting OBD-II DTC codes from {file_path.name}...")
    import_dtc_codes(file_path)


if __name__ == "__main__":
    main()
