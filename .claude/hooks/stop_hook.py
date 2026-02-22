#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# ///
"""Stop hook: remind to create session documentation before ending.

Non-blocking reminder that prompts for documentation if:
- Files were modified during the session (Write/Edit tools used)
- No documentation was created in docs/sessions/

Never blocks session end — only shows a warning message to the user.
"""

import json
import sys
from pathlib import Path


def parse_transcript_for_modifications(transcript_path: Path) -> bool:
    """Check if any files were modified during this session."""
    if not transcript_path.exists():
        return False

    try:
        with open(transcript_path, encoding="utf-8") as f:
            for line in f:
                try:
                    entry = json.loads(line.strip())
                    # Check for Write or Edit tool uses
                    if entry.get("type") == "tool_use":
                        tool_name = entry.get("name", "")
                        if tool_name in ("Write", "Edit"):
                            return True
                except json.JSONDecodeError:
                    continue
    except Exception:
        pass

    return False


def check_session_docs_exist(session_id: str) -> bool:
    """Check if session documentation was created."""
    docs_dir = Path("docs/sessions")
    if not docs_dir.exists():
        return False

    # Look for any file matching the session ID
    session_files = list(docs_dir.glob(f"{session_id}*"))
    return len(session_files) > 0


def main():
    try:
        raw_input = sys.stdin.read()
        data = json.loads(raw_input)
    except (json.JSONDecodeError, Exception):
        sys.exit(0)

    # CRITICAL: Always allow session to end if stop_hook_active is true
    # This prevents infinite loops
    if data.get("stop_hook_active"):
        sys.exit(0)

    session_id = data.get("session_id", "")
    transcript_path = Path(data.get("transcript_path", ""))

    # Check if files were modified
    files_modified = parse_transcript_for_modifications(transcript_path)

    # Check if docs exist
    docs_exist = check_session_docs_exist(session_id)

    # If files were modified but no docs created, show warning
    if files_modified and not docs_exist:
        print(
            json.dumps(
                {
                    "systemMessage": (
                        "⚠️  Session ending without documentation.\n\n"
                        "Consider creating:\n"
                        "• Session summary (what was accomplished)\n"
                        "• Next steps (what's remaining)\n"
                        "• Decision log (key choices made)\n\n"
                        f"Suggested location: docs/sessions/{session_id}-summary.md"
                    )
                }
            )
        )

    # Always allow session to end (exit 0)
    sys.exit(0)


if __name__ == "__main__":
    main()
