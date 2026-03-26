# Checked AGENTS.md - implementing directly because this is a Gemini-delegated implementation task.
# Architecture designed by Claude; schema fix + migration logic implemented by Gemini; integrated here.
"""
migrate_epa_to_vehicles.py — Cross-DB migration: epa_vehicles → vehicles table

Copies from automotive_complaints.db (epa_vehicles, 49,806 rows 1984-2026) into
automotive_diagnostics.db (vehicles table). Also expands the year CHECK constraint
from 2005-2025 to 1984-2030 to accommodate full EPA year range.

Usage:
    uv run python scripts/migrate_epa_to_vehicles.py

Safe to re-run: INSERT OR IGNORE on UNIQUE(make, model, year, engine) prevents duplicates.
"""
import sqlite3
import shutil
import sys
import time
from pathlib import Path

PROJECT_ROOT   = Path(__file__).parent.parent
COMPLAINTS_DB  = PROJECT_ROOT / "database" / "automotive_complaints.db"
DIAGNOSTICS_DB = PROJECT_ROOT / "database" / "automotive_diagnostics.db"
BACKUPS_DIR    = PROJECT_ROOT / "database" / "backups"


def pre_flight_checks() -> None:
    _, _, free = shutil.disk_usage(str(PROJECT_ROOT))
    if free < 5 * 1024 ** 3:
        print(f"ERROR: only {free / 1024**3:.1f} GB free — need ≥ 5 GB. Aborting.", file=sys.stderr)
        sys.exit(1)
    print(f"Disk OK: {free / 1024**3:.1f} GB free")

    if not BACKUPS_DIR.exists():
        print("WARNING: database/backups/ missing — run scripts/backup_databases.py first")
        return
    backup_sets = sorted([d for d in BACKUPS_DIR.iterdir() if d.is_dir() and d.name[0].isdigit()])
    if not backup_sets:
        print("WARNING: No backup sets found — run scripts/backup_databases.py first")
    else:
        latest = backup_sets[-1]
        age_days = (time.time() - latest.stat().st_mtime) / 86400
        if age_days > 7:
            print(f"WARNING: Latest backup is {age_days:.0f} days old ({latest.name})")
        else:
            print(f"Backup OK: {latest.name} ({age_days:.1f} days old)")


def expand_vehicles_year_constraint(conn: sqlite3.Connection) -> None:
    """Expand CHECK(year >= 2005..2025) → (1984..2030) via full table recreation.
    Drops dependent views first, recreates them after rename.
    """
    print("Expanding year constraint 2005–2025 → 1984–2030 ...")
    conn.executescript("""
        BEGIN IMMEDIATE;

        -- Drop views that reference vehicles (must be done before DROP TABLE)
        DROP VIEW IF EXISTS v_vehicle_diagnostics;
        DROP VIEW IF EXISTS v_safety_critical_issues;

        CREATE TABLE vehicles_new (
            vehicle_id INTEGER PRIMARY KEY AUTOINCREMENT,
            make TEXT NOT NULL COLLATE NOCASE,
            model TEXT NOT NULL COLLATE NOCASE,
            year INTEGER NOT NULL CHECK(year >= 1984 AND year <= 2030),
            engine TEXT,
            engine_displacement REAL,
            engine_cylinders INTEGER,
            body_style TEXT,
            drive_type TEXT,
            transmission_type TEXT,
            fuel_type TEXT,
            vin_pattern TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(make, model, year, engine)
        );

        INSERT INTO vehicles_new SELECT * FROM vehicles;

        DROP TRIGGER IF EXISTS vehicles_fts_insert;
        DROP TRIGGER IF EXISTS vehicles_fts_update;
        DROP TRIGGER IF EXISTS vehicles_fts_delete;

        DROP INDEX IF EXISTS idx_vehicles_make_model;
        DROP INDEX IF EXISTS idx_vehicles_year;
        DROP INDEX IF EXISTS idx_vehicles_make_year;
        DROP INDEX IF EXISTS idx_vehicles_full;

        DROP TABLE vehicles;
        ALTER TABLE vehicles_new RENAME TO vehicles;

        CREATE INDEX idx_vehicles_make_model ON vehicles(make, model);
        CREATE INDEX idx_vehicles_year ON vehicles(year);
        CREATE INDEX idx_vehicles_make_year ON vehicles(make, year);
        CREATE INDEX idx_vehicles_full ON vehicles(make, model, year, engine);

        CREATE TRIGGER vehicles_fts_insert AFTER INSERT ON vehicles BEGIN
            INSERT INTO vehicles_fts(rowid, make, model, year, engine, body_style)
            VALUES (NEW.vehicle_id, NEW.make, NEW.model, NEW.year, NEW.engine, NEW.body_style);
        END;
        CREATE TRIGGER vehicles_fts_update AFTER UPDATE ON vehicles BEGIN
            DELETE FROM vehicles_fts WHERE rowid = OLD.vehicle_id;
            INSERT INTO vehicles_fts(rowid, make, model, year, engine, body_style)
            VALUES (NEW.vehicle_id, NEW.make, NEW.model, NEW.year, NEW.engine, NEW.body_style);
        END;
        CREATE TRIGGER vehicles_fts_delete AFTER DELETE ON vehicles BEGIN
            DELETE FROM vehicles_fts WHERE rowid = OLD.vehicle_id;
        END;

        -- Recreate views
        CREATE VIEW v_vehicle_diagnostics AS
        SELECT v.vehicle_id, v.make, v.model, v.year, v.engine,
               COUNT(DISTINCT vf.failure_id) as total_known_failures,
               COUNT(DISTINCT vt.tsb_id)     as total_tsbs,
               COUNT(DISTINCT vr.recall_id)  as total_recalls
        FROM vehicles v
        LEFT JOIN vehicle_failures vf ON v.vehicle_id = vf.vehicle_id
        LEFT JOIN vehicle_tsbs vt     ON v.vehicle_id = vt.vehicle_id
        LEFT JOIN vehicle_recalls vr  ON v.vehicle_id = vr.vehicle_id
        GROUP BY v.vehicle_id;

        CREATE VIEW v_safety_critical_issues AS
        SELECT v.make, v.model, v.year, f.name as failure_name,
               f.symptom_description, f.confidence, f.source_type, f.nhtsa_number
        FROM vehicles v
        JOIN vehicle_failures vf ON v.vehicle_id = vf.vehicle_id
        JOIN failure_patterns f  ON vf.failure_id = f.failure_id
        WHERE f.safety_critical = 1
        ORDER BY v.make, v.model, v.year;

        COMMIT;
    """)
    print("  ✓ Constraint expanded, views recreated")


def migrate_epa_to_vehicles() -> None:
    pre_flight_checks()

    for db in (COMPLAINTS_DB, DIAGNOSTICS_DB):
        if not db.exists():
            print(f"ERROR: {db} not found", file=sys.stderr)
            sys.exit(1)

    conn = sqlite3.connect(str(DIAGNOSTICS_DB))
    conn.execute("PRAGMA main.journal_mode=WAL")
    conn.execute("PRAGMA main.synchronous=NORMAL")

    expand_vehicles_year_constraint(conn)

    conn.execute("ATTACH DATABASE ? AS complaints", (str(COMPLAINTS_DB),))
    cursor = conn.cursor()

    cursor.execute("SELECT COUNT(*) FROM main.vehicles")
    before_count = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM complaints.epa_vehicles")
    total_source = cursor.fetchone()[0]
    print(f"\nSource rows  : {total_source:,}")
    print(f"Target before: {before_count:,}")
    print(f"\nMigrating {total_source:,} EPA records → vehicles table...")

    batch_size = 1000
    offset = 0

    while offset < total_source:
        cursor.execute("""
            INSERT OR IGNORE INTO main.vehicles (
                make, model, year, engine,
                engine_displacement, engine_cylinders,
                body_style, drive_type, transmission_type, fuel_type
            )
            SELECT
                UPPER(ev.make),
                ev.model,
                ev.year,
                CASE
                    WHEN ev.engine_cylinders IS NOT NULL AND ev.engine_displacement IS NOT NULL
                        THEN ev.engine_cylinders || '-cyl ' || ev.engine_displacement || 'L'
                    WHEN ev.engine_cylinders IS NOT NULL
                        THEN ev.engine_cylinders || '-cyl'
                    WHEN ev.engine_displacement IS NOT NULL
                        THEN ev.engine_displacement || 'L'
                    ELSE NULL
                END,
                ev.engine_displacement,
                ev.engine_cylinders,
                ev.vehicle_class,
                ev.drive,
                ev.transmission,
                ev.fuel_type
            FROM complaints.epa_vehicles ev
            ORDER BY ev.rowid
            LIMIT ? OFFSET ?
        """, (batch_size, offset))

        conn.commit()
        offset += batch_size
        processed = min(offset, total_source)
        if processed % 10000 == 0 or offset >= total_source:
            print(f"  {processed:,} / {total_source:,}")

    cursor.execute("SELECT COUNT(*) FROM main.vehicles")
    after_count = cursor.fetchone()[0]
    conn.close()

    print(f"\nMigration complete.")
    print(f"  Rows before : {before_count:,}")
    print(f"  Rows after  : {after_count:,}")
    print(f"  Inserted    : {after_count - before_count:,}")


if __name__ == "__main__":
    migrate_epa_to_vehicles()
