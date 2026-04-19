#!/usr/bin/env python3
"""
Deterministic memory health checker — no API calls, no AI.

Checks:
  1. MEMORY.md is under 200 lines (truncation threshold)
  2. All files indexed in MEMORY.md actually exist
  3. No blank-line frontmatter bloat (more than 3 blank lines inside ---)
  4. No orphan files (in directory but not in MEMORY.md index)

Usage:
    uv run python scripts/memory_lint.py [--fix-blanks]

Exits 0 always — reports issues but never blocks.
"""

import re
import sys
from pathlib import Path

MEMORY_DIR = Path("/home/poteete/.claude/projects/-home-poteete-projects-automotive-diagnostic-skills/memory")
INDEX_FILE = MEMORY_DIR / "MEMORY.md"
SKIP_FILES = {"MEMORY.md", ".gitignore", ".synthesis_last_run"}
SKIP_DIRS = {"archive", "attachments", "cells"}
MAX_INDEX_LINES = 200
MAX_FRONTMATTER_BLANKS = 3


def parse_index_links(index_text: str) -> set[str]:
    """Extract all linked filenames from MEMORY.md."""
    return set(re.findall(r'\[([^\]]+\.md)\]\(([^\)]+\.md)\)', index_text, re.IGNORECASE)
             and [m[1] for m in re.findall(r'\[([^\]]+)\]\(([^\)]+\.md)\)', index_text)])


def count_frontmatter_blanks(text: str) -> int:
    """Count blank lines inside the frontmatter block (between --- markers)."""
    if not text.startswith("---"):
        return 0
    end = text.find("\n---", 3)
    if end == -1:
        return 0
    fm = text[3:end]
    return sum(1 for line in fm.splitlines() if line.strip() == "")


def fix_frontmatter_blanks(text: str) -> str:
    """Strip blank lines from inside frontmatter block."""
    if not text.startswith("---"):
        return text
    end = text.find("\n---", 3)
    if end == -1:
        return text
    fm = text[3:end]
    body = text[end + 4:]
    clean_fm = "\n".join(line for line in fm.strip().splitlines())
    return "---\n" + clean_fm + "\n---" + body


def run(fix_blanks: bool = False) -> None:
    issues: list[str] = []
    fixed: list[str] = []

    if not INDEX_FILE.exists():
        print("ERROR: MEMORY.md not found")
        sys.exit(0)

    index_text = INDEX_FILE.read_text(encoding="utf-8")
    index_lines = index_text.splitlines()

    # 1. Index line count
    if len(index_lines) > MAX_INDEX_LINES:
        issues.append(f"MEMORY.md is {len(index_lines)} lines — exceeds 200-line load limit (lines after 200 are truncated)")

    # 2. Parse indexed files
    indexed_files = set(re.findall(r'\]\(([^)]+\.md)\)', index_text))

    # 3. Check indexed files exist
    for fname in sorted(indexed_files):
        fpath = MEMORY_DIR / fname
        if not fpath.exists():
            issues.append(f"BROKEN LINK: {fname} is in MEMORY.md index but file does not exist")

    # 4. Check for orphan files and blank-line bloat
    all_md_files = {
        p.name for p in MEMORY_DIR.glob("*.md")
        if p.name not in SKIP_FILES
    }

    for fname in sorted(all_md_files):
        fpath = MEMORY_DIR / fname
        text = fpath.read_text(encoding="utf-8")

        # Orphan check
        if fname not in indexed_files:
            issues.append(f"ORPHAN: {fname} exists but is not in MEMORY.md index")

        # Blank-line bloat check
        blank_count = count_frontmatter_blanks(text)
        if blank_count > MAX_FRONTMATTER_BLANKS:
            if fix_blanks:
                fixed_text = fix_frontmatter_blanks(text)
                fpath.write_text(fixed_text, encoding="utf-8")
                fixed.append(f"FIXED blanks in {fname} ({blank_count} → 0)")
            else:
                issues.append(f"BLOAT: {fname} has {blank_count} blank lines in frontmatter")

    # Report
    print(f"\nMemory Lint — {MEMORY_DIR.name}")
    print(f"  Index: {len(index_lines)} lines | Indexed files: {len(indexed_files)} | Total .md: {len(all_md_files)}")

    if fixed:
        print(f"\n  Fixed ({len(fixed)}):")
        for f in fixed:
            print(f"    {f}")

    if issues:
        print(f"\n  Issues ({len(issues)}):")
        for issue in issues:
            print(f"    ⚠  {issue}")
    else:
        print("  ✓ All checks passed")

    print()


if __name__ == "__main__":
    fix_blanks = "--fix-blanks" in sys.argv
    run(fix_blanks=fix_blanks)
