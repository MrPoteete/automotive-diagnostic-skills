#!/usr/bin/env python3
"""
Memory pruner — archives TTL-expired memory entries and updates last_accessed timestamps.

Usage:
    uv run python scripts/memory_prune.py [--dry-run]

Scans all .md files in the memory directory (not subdirs), reads YAML frontmatter,
and for files with a ttl: field:
  - If (today - created) > ttl → move to memory/archive/YYYY-MM/
  - Updates last_accessed: to today for all files read

Supports ttl formats: 90d (days), 6m (months)
Never deletes — only moves to archive. Safe to run repeatedly (idempotent).
"""

import argparse
import re
import shutil
import sys
from datetime import date, datetime
from pathlib import Path

MEMORY_DIR = Path("/home/poteete/.claude/projects/-home-poteete-projects-automotive-diagnostic-skills/memory")
SKIP_FILES = {"MEMORY.md"}


def parse_frontmatter(text: str) -> tuple[dict[str, str], str]:
    """Extract YAML frontmatter from markdown text. Returns (fields, body)."""
    if not text.startswith("---"):
        return {}, text
    end = text.find("\n---", 3)
    if end == -1:
        return {}, text
    fm_text = text[3:end].strip()
    body = text[end + 4:]
    fields: dict[str, str] = {}
    for line in fm_text.splitlines():
        if ":" in line:
            key, _, val = line.partition(":")
            fields[key.strip()] = val.strip()
    return fields, body


def update_frontmatter(text: str, updates: dict[str, str]) -> str:
    """Update specific frontmatter fields in markdown text."""
    if not text.startswith("---"):
        return text
    end = text.find("\n---", 3)
    if end == -1:
        return text
    fm_text = text[3:end]
    body = text[end + 4:]

    lines = fm_text.splitlines()
    updated_keys = set()
    new_lines = []
    for line in lines:
        if ":" in line:
            key = line.partition(":")[0].strip()
            if key in updates:
                new_lines.append(f"{key}: {updates[key]}")
                updated_keys.add(key)
                continue
        new_lines.append(line)

    # Add any keys not already present
    for key, val in updates.items():
        if key not in updated_keys:
            new_lines.append(f"{key}: {val}")

    return "---\n" + "\n".join(new_lines) + "\n---" + body


def parse_ttl_days(ttl: str) -> int | None:
    """Parse ttl string to days. Supports '90d' and '6m' formats."""
    m = re.fullmatch(r"(\d+)([dm])", ttl.strip())
    if not m:
        return None
    value, unit = int(m.group(1)), m.group(2)
    return value if unit == "d" else value * 30


def parse_date(date_str: str) -> date | None:
    """Parse YYYY-MM-DD date string."""
    try:
        return datetime.strptime(date_str.strip(), "%Y-%m-%d").date()
    except ValueError:
        return None


def run(dry_run: bool = False) -> None:
    today = date.today()
    today_str = today.isoformat()

    files_checked = 0
    files_archived = 0
    files_updated = 0
    errors = []

    for path in sorted(MEMORY_DIR.glob("*.md")):
        if path.name in SKIP_FILES:
            continue

        files_checked += 1
        text = path.read_text(encoding="utf-8")
        fields, _ = parse_frontmatter(text)

        should_archive = False

        # Check TTL expiry
        ttl_str = fields.get("ttl", "")
        created_str = fields.get("created", "")
        if ttl_str and created_str:
            ttl_days = parse_ttl_days(ttl_str)
            created = parse_date(created_str)
            if ttl_days is not None and created is not None:
                age_days = (today - created).days
                if age_days > ttl_days:
                    should_archive = True

        if should_archive:
            archive_dir = MEMORY_DIR / "archive" / today_str[:7]  # YYYY-MM
            if not dry_run:
                archive_dir.mkdir(parents=True, exist_ok=True)
                shutil.move(str(path), archive_dir / path.name)
            print(f"  ARCHIVE: {path.name} → archive/{today_str[:7]}/ (age exceeded ttl:{ttl_str})")
            files_archived += 1
            continue

        # Update last_accessed on files that are still active
        new_text = update_frontmatter(text, {"last_accessed": today_str})
        if new_text != text:
            if not dry_run:
                path.write_text(new_text, encoding="utf-8")
            files_updated += 1

    print(f"\nMemory prune complete ({today_str})")
    print(f"  Checked:  {files_checked}")
    print(f"  Archived: {files_archived}")
    print(f"  Updated:  {files_updated} (last_accessed)")
    if dry_run:
        print("  [DRY RUN — no files written]")
    if errors:
        print(f"  Errors:   {len(errors)}")
        for e in errors:
            print(f"    {e}")
        sys.exit(1)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Prune TTL-expired memory entries")
    parser.add_argument("--dry-run", action="store_true", help="Show what would happen without writing")
    args = parser.parse_args()
    run(dry_run=args.dry_run)
