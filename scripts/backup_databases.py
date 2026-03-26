#!/usr/bin/env python3
# Checked AGENTS.md - implementing directly: operational safety script,
# no auth surfaces, no complex architecture decisions.
"""
backup_databases.py — Safe, rotating backup of both SQLite databases.

Safeguards:
  - Aborts if disk is < 10% free before starting
  - Uses SQLite's built-in .backup() API (hot backup, no lock required)
  - Verifies each backup by checking table row counts match source
  - Keeps last KEEP_BACKUPS copies, deletes older ones automatically
  - Logs every run to database/backups/backup.log

Usage:
    uv run python scripts/backup_databases.py            # normal backup
    uv run python scripts/backup_databases.py --verify   # verify latest backup only
    uv run python scripts/backup_databases.py --list     # list all backups

Cron (weekly Sunday 2am):
    0 2 * * 0 cd /home/poteete/projects/automotive-diagnostic-skills && uv run python scripts/backup_databases.py >> database/backups/backup.log 2>&1
"""

import argparse
import logging
import shutil
import sqlite3
import sys
from datetime import datetime
from pathlib import Path

# ── Config ────────────────────────────────────────────────────────────────────
PROJECT_ROOT   = Path(__file__).parent.parent
DB_DIR         = PROJECT_ROOT / "database"
BACKUP_DIR     = DB_DIR / "backups"
KEEP_BACKUPS   = 5          # number of timestamped backups to retain
MIN_FREE_PCT   = 10         # abort if free disk < this percent
MIN_FREE_GB    = 5          # also abort if free disk < this many GB

DATABASES = {
    "automotive_complaints.db": {
        "verify_table": "nhtsa_recalls",   # quick sanity-check table
    },
    "automotive_diagnostics.db": {
        "verify_table": "vehicles",
    },
}

# ── Logging ───────────────────────────────────────────────────────────────────
BACKUP_DIR.mkdir(parents=True, exist_ok=True)
log_file = BACKUP_DIR / "backup.log"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
    handlers=[
        logging.FileHandler(log_file),
        logging.StreamHandler(sys.stdout),
    ],
)
log = logging.getLogger("backup_databases")


# ── Disk check ────────────────────────────────────────────────────────────────
def check_disk_space() -> None:
    usage = shutil.disk_usage("/")
    free_gb  = usage.free  / (1024 ** 3)
    free_pct = usage.free  / usage.total * 100
    used_pct = 100 - free_pct
    log.info("Disk: %.1f GB free  (%.0f%% used)", free_gb, used_pct)
    if free_pct < MIN_FREE_PCT or free_gb < MIN_FREE_GB:
        log.error(
            "ABORT: insufficient disk — %.1f GB free (%.0f%% free). "
            "Need ≥ %d%% or ≥ %d GB free.",
            free_gb, free_pct, MIN_FREE_PCT, MIN_FREE_GB,
        )
        sys.exit(1)


# ── SQLite hot backup ─────────────────────────────────────────────────────────
def backup_db(src_path: Path, dest_path: Path) -> bool:
    """Use SQLite's .backup() API — safe even while the DB is being written."""
    if not src_path.exists():
        log.error("Source DB not found: %s", src_path)
        return False
    src_size = src_path.stat().st_size / (1024 ** 2)
    log.info("Backing up %s (%.1f MB) → %s", src_path.name, src_size, dest_path.name)
    try:
        src  = sqlite3.connect(str(src_path))
        dest = sqlite3.connect(str(dest_path))
        src.backup(dest, pages=512)   # stream in 512-page chunks
        dest.close()
        src.close()
        dest_size = dest_path.stat().st_size / (1024 ** 2)
        log.info("  ✓ Written: %.1f MB", dest_size)
        return True
    except Exception as exc:
        log.error("  ✗ Backup failed: %s", exc)
        return False


# ── Verify backup ─────────────────────────────────────────────────────────────
def verify_backup(src_path: Path, backup_path: Path, verify_table: str) -> bool:
    """Confirm the backup has the same row count as the source for key table."""
    try:
        src_count    = sqlite3.connect(str(src_path)).execute(
            f"SELECT COUNT(*) FROM {verify_table}"
        ).fetchone()[0]
        backup_count = sqlite3.connect(str(backup_path)).execute(
            f"SELECT COUNT(*) FROM {verify_table}"
        ).fetchone()[0]
        if src_count == backup_count:
            log.info("  ✓ Verified: %s has %d rows (matches source)", verify_table, backup_count)
            return True
        else:
            log.error(
                "  ✗ MISMATCH: source %s=%d, backup %s=%d",
                verify_table, src_count, verify_table, backup_count,
            )
            return False
    except Exception as exc:
        log.error("  ✗ Verification error: %s", exc)
        return False


# ── Rotation ──────────────────────────────────────────────────────────────────
def rotate_backups() -> None:
    """Delete oldest backup sets beyond KEEP_BACKUPS."""
    # Backup dirs are named YYYY-MM-DDTHH-MM-SS/
    sets = sorted(
        [d for d in BACKUP_DIR.iterdir() if d.is_dir() and d.name[0].isdigit()]
    )
    while len(sets) > KEEP_BACKUPS:
        oldest = sets.pop(0)
        log.info("Rotating out old backup: %s", oldest.name)
        for f in oldest.iterdir():
            f.unlink()
        oldest.rmdir()


# ── List backups ──────────────────────────────────────────────────────────────
def list_backups() -> None:
    sets = sorted(
        [d for d in BACKUP_DIR.iterdir() if d.is_dir() and d.name[0].isdigit()],
        reverse=True,
    )
    if not sets:
        print("No backups found.")
        return
    print(f"\n{'Backup':<25} {'Files':<5} {'Total Size'}")
    print("-" * 50)
    for bset in sets:
        files = list(bset.glob("*.db"))
        total = sum(f.stat().st_size for f in files) / (1024 ** 2)
        print(f"{bset.name:<25} {len(files):<5} {total:.1f} MB")
    print()


# ── Verify latest ─────────────────────────────────────────────────────────────
def verify_latest() -> None:
    sets = sorted(
        [d for d in BACKUP_DIR.iterdir() if d.is_dir() and d.name[0].isdigit()]
    )
    if not sets:
        print("No backups found to verify.")
        sys.exit(1)
    latest = sets[-1]
    log.info("Verifying latest backup: %s", latest.name)
    ok = True
    for db_name, cfg in DATABASES.items():
        src    = DB_DIR / db_name
        backup = latest / db_name
        if not backup.exists():
            log.error("  Missing: %s", db_name)
            ok = False
            continue
        ok &= verify_backup(src, backup, cfg["verify_table"])
    sys.exit(0 if ok else 1)


# ── Main ──────────────────────────────────────────────────────────────────────
def main() -> None:
    parser = argparse.ArgumentParser(description="Backup automotive diagnostic databases")
    parser.add_argument("--verify", action="store_true", help="Verify latest backup only")
    parser.add_argument("--list",   action="store_true", help="List all backups")
    args = parser.parse_args()

    if args.list:
        list_backups()
        return

    if args.verify:
        verify_latest()
        return

    # ── Full backup run ──────────────────────────────────────────────────────
    stamp      = datetime.now().strftime("%Y-%m-%dT%H-%M-%S")
    backup_set = BACKUP_DIR / stamp
    backup_set.mkdir(parents=True, exist_ok=True)

    log.info("=" * 60)
    log.info("Backup started: %s", stamp)

    check_disk_space()

    all_ok = True
    for db_name, cfg in DATABASES.items():
        src    = DB_DIR / db_name
        dest   = backup_set / db_name
        if backup_db(src, dest):
            all_ok &= verify_backup(src, dest, cfg["verify_table"])
        else:
            all_ok = False

    if all_ok:
        log.info("All backups verified ✓")
        rotate_backups()
        log.info("Rotation complete — keeping last %d sets", KEEP_BACKUPS)
    else:
        log.error("One or more backups FAILED — keeping all sets, investigate before next import")
        sys.exit(1)

    # Final disk report
    usage = shutil.disk_usage("/")
    log.info(
        "Disk after backup: %.1f GB free (%.0f%% used)",
        usage.free / (1024 ** 3),
        usage.used / usage.total * 100,
    )
    log.info("Backup run complete")
    log.info("=" * 60)


if __name__ == "__main__":
    main()
