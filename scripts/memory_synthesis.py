#!/usr/bin/env python3
"""
Sleep-time memory synthesis — extracts insights from recent Claude Code sessions
and writes/updates memory files using Claude Haiku.

Designed to run:
  - Every 6 hours via systemd timer
  - On session end via stop_hook.py trigger

Usage:
    uv run python scripts/memory_synthesis.py [--dry-run] [--hours 6]

What it does:
  1. Finds all session JSONL files modified in the last N hours
  2. Extracts user messages, assistant corrections, and tool failure events
  3. Calls Claude Haiku to identify new facts, corrections, or preferences
  4. Writes/updates memory files in the memory/ directory
  5. Runs memory_prune.py to archive TTL-expired entries
  6. Git-commits the memory directory with a timestamped message
"""

import argparse
import json
import os
import subprocess
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path

MEMORY_DIR = Path("/home/poteete/.claude/projects/-home-poteete-projects-automotive-diagnostic-skills/memory")
PROJECT_DIR = Path("/home/poteete/.claude/projects/-home-poteete-projects-automotive-diagnostic-skills")
PRUNE_SCRIPT = Path("/home/poteete/projects/automotive-diagnostic-skills/scripts/memory_prune.py")
STATE_FILE = MEMORY_DIR / ".synthesis_last_run"


def get_anthropic_key() -> str:
    """Read API key from project .env file."""
    env_path = Path("/home/poteete/projects/automotive-diagnostic-skills/.env")
    if env_path.exists():
        for line in env_path.read_text().splitlines():
            if line.startswith("ANTHROPIC_API_KEY="):
                return line.split("=", 1)[1].strip().strip('"').strip("'")
    key = os.environ.get("ANTHROPIC_API_KEY", "")
    if not key:
        raise RuntimeError("ANTHROPIC_API_KEY not found in .env or environment")
    return key


def get_session_files(since_hours: int) -> list[Path]:
    """Find session JSONL files modified in the last N hours."""
    cutoff = time.time() - (since_hours * 3600)
    files = []
    for path in PROJECT_DIR.glob("*.jsonl"):
        if path.stat().st_mtime > cutoff:
            files.append(path)
    return sorted(files, key=lambda p: p.stat().st_mtime)


def extract_conversation(jsonl_path: Path, max_chars: int = 12000) -> str:
    """Extract human/assistant exchanges from a session JSONL, truncated to max_chars."""
    lines = []
    try:
        raw = jsonl_path.read_text(encoding="utf-8", errors="ignore")
        for line in raw.splitlines():
            if not line.strip():
                continue
            try:
                entry = json.loads(line)
            except json.JSONDecodeError:
                continue

            msg = entry.get("message", {})
            if not isinstance(msg, dict):
                continue
            role = msg.get("role", "")
            content = msg.get("content", "")

            # Extract text from content (may be list of blocks or plain string)
            text = ""
            if isinstance(content, str):
                text = content
            elif isinstance(content, list):
                for block in content:
                    if isinstance(block, dict) and block.get("type") == "text":
                        text += block.get("text", "")

            text = text.strip()
            if text and role in ("user", "assistant") and entry.get("type") in ("user", "assistant"):
                # Skip very short lines (tool confirmations etc)
                if len(text) > 20:
                    label = "User" if role == "user" else "Claude"
                    lines.append(f"{label}: {text[:800]}")

    except Exception as e:
        return f"[Error reading {jsonl_path.name}: {e}]"

    full = "\n\n".join(lines)
    # Truncate to max_chars from the END (most recent is most valuable)
    if len(full) > max_chars:
        full = "...[truncated]...\n" + full[-max_chars:]
    return full


def call_haiku(conversation: str, existing_memory: str, dry_run: bool) -> str:
    """Call Claude Haiku to extract memory-worthy insights."""
    if dry_run:
        return "[DRY RUN — no API call made]"

    try:
        import anthropic  # type: ignore[import-untyped]
    except ImportError:
        return "[anthropic not installed — run: uv run --with anthropic python scripts/memory_synthesis.py]"

    client = anthropic.Anthropic(api_key=get_anthropic_key())

    prompt = f"""You are a memory synthesis agent for an automotive diagnostic AI project.

Review this conversation excerpt and the existing memory files, then identify any NEW information worth persisting.

Focus ONLY on:
1. User corrections to Claude's behavior ("don't do X", "always do Y")
2. New project facts (new features built, bugs found, data counts changed)
3. Updated preferences or workflow changes
4. Infrastructure changes (new services, config changes)

SKIP anything already captured in existing memory or obvious/generic.

Return a JSON array of memory updates. Each item:
{{
  "action": "create" | "update" | "skip",
  "file": "feedback_foo.md" | "project_bar.md" | etc,
  "type": "feedback" | "project" | "user" | "reference",
  "name": "short name",
  "description": "one-line description",
  "body": "full memory content (rule + Why: + How to apply: for feedback type)"
}}

Return [] if nothing new is worth persisting.

--- EXISTING MEMORY FILES ---
{existing_memory}

--- RECENT CONVERSATION ---
{conversation}

Respond with ONLY the JSON array, no other text."""

    response = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=2000,
        messages=[{"role": "user", "content": prompt}],
    )
    return response.content[0].text


def apply_updates(updates_json: str, dry_run: bool) -> int:
    """Parse Haiku output and write memory files. Returns count of files written."""
    try:
        updates = json.loads(updates_json)
    except (json.JSONDecodeError, ValueError):
        print(f"  [WARN] Could not parse Haiku response as JSON:\n{updates_json[:300]}")
        return 0

    if not isinstance(updates, list):
        return 0

    written = 0
    today = datetime.now().strftime("%Y-%m-%d")

    for item in updates:
        if item.get("action") == "skip":
            continue

        fname = item.get("file", "").strip()
        if not fname or not fname.endswith(".md"):
            continue

        dest = MEMORY_DIR / fname
        mtype = item.get("type", "project")
        name = item.get("name", fname.replace(".md", ""))
        desc = item.get("description", "")
        body = item.get("body", "")

        content = f"""---
name: {name}
description: {desc}
type: {mtype}
created: {today}
last_accessed: {today}
source: claude-haiku-synthesis
ttl: 90d
---

{body}
"""
        if dry_run:
            print(f"  [DRY RUN] Would write: {fname}")
            print(f"    {desc}")
        else:
            dest.write_text(content, encoding="utf-8")
            print(f"  Written: {fname}")

        written += 1

    return written


def update_memory_index(new_files: list[str], dry_run: bool) -> None:
    """Add new files to MEMORY.md index if not already present."""
    index_path = MEMORY_DIR / "MEMORY.md"
    if not index_path.exists():
        return

    content = index_path.read_text(encoding="utf-8")
    lines_to_add = []
    for fname in new_files:
        link = f"- [{fname}]({fname})"
        if link not in content:
            lines_to_add.append(link + " — (synthesized)")

    if not lines_to_add:
        return

    # Insert under ### Project section
    insert_after = "### Project"
    if insert_after in content:
        idx = content.index(insert_after) + len(insert_after)
        content = content[:idx] + "\n" + "\n".join(lines_to_add) + content[idx:]
        if not dry_run:
            index_path.write_text(content, encoding="utf-8")


def git_commit_memory(dry_run: bool) -> None:
    """Commit any changes in the memory directory."""
    if dry_run:
        return
    try:
        result = subprocess.run(
            ["git", "-C", str(MEMORY_DIR), "status", "--porcelain"],
            capture_output=True, text=True, timeout=10
        )
        if not result.stdout.strip():
            return  # Nothing to commit
        ts = datetime.now().strftime("%Y-%m-%d %H:%M")
        subprocess.run(
            ["git", "-C", str(MEMORY_DIR), "add", "."],
            capture_output=True, timeout=10
        )
        subprocess.run(
            ["git", "-C", str(MEMORY_DIR), "commit", "-m", f"Memory synthesis {ts}"],
            capture_output=True, timeout=15
        )
        print("  Memory git commit done")
    except Exception as e:
        print(f"  [WARN] git commit failed: {e}")


def load_existing_memory_summary() -> str:
    """Load a brief summary of existing memory files for context."""
    parts = []
    for path in sorted(MEMORY_DIR.glob("*.md")):
        if path.name == "MEMORY.md":
            continue
        try:
            text = path.read_text(encoding="utf-8")
            # Just include name + first 200 chars of body
            parts.append(f"[{path.name}]\n{text[:300]}\n")
        except Exception:
            pass
    return "\n".join(parts)[:6000]


def run(since_hours: int, dry_run: bool) -> None:
    print(f"\nMemory Synthesis — {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print(f"  Looking back: {since_hours} hours | dry_run={dry_run}")

    session_files = get_session_files(since_hours)
    if not session_files:
        print("  No recent session files found — nothing to synthesize")
        return

    print(f"  Sessions found: {len(session_files)}")

    # Combine conversations from all recent sessions
    combined = ""
    for sf in session_files[-3:]:  # At most 3 most recent sessions
        excerpt = extract_conversation(sf)
        if excerpt:
            combined += f"\n--- Session: {sf.name[:8]} ---\n{excerpt}\n"

    if not combined.strip():
        print("  No extractable conversation content")
        return

    existing = load_existing_memory_summary()

    print("  Calling Claude Haiku for synthesis...")
    result = call_haiku(combined, existing, dry_run)

    new_files: list[str] = []
    if not dry_run and result and result != "[DRY RUN — no API call made]":
        count = apply_updates(result, dry_run)
        print(f"  Memory updates written: {count}")
    elif dry_run:
        print(f"  Haiku response preview:\n{result[:500]}")

    # Run prune script
    print("  Running memory_prune.py...")
    prune_cmd = ["uv", "run", "python", str(PRUNE_SCRIPT)]
    if dry_run:
        prune_cmd.append("--dry-run")
    subprocess.run(prune_cmd, cwd="/home/poteete/projects/automotive-diagnostic-skills")

    # Git commit
    git_commit_memory(dry_run)

    # Update last-run timestamp
    if not dry_run:
        STATE_FILE.write_text(datetime.now().isoformat())

    print("  Synthesis complete.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Sleep-time memory synthesis via Claude Haiku")
    parser.add_argument("--dry-run", action="store_true", help="Preview without writing or calling API")
    parser.add_argument("--hours", type=int, default=6, help="Look back N hours for sessions (default: 6)")
    args = parser.parse_args()
    run(since_hours=args.hours, dry_run=args.dry_run)
