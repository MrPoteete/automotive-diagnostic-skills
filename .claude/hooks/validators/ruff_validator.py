#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# ///
"""PostToolUse hook: run ruff check on Python files after Write/Edit.

If ruff finds errors, outputs a block decision so Claude sees the lint
errors and fixes them before continuing. Skips non-Python files silently.
"""

import json
import subprocess
import sys


def main():
    try:
        raw_input = sys.stdin.read()
        data = json.loads(raw_input)
    except (json.JSONDecodeError, Exception):
        sys.exit(0)

    tool_name = data.get("tool_name", "")
    tool_input = data.get("tool_input", {})

    # Only run on Write/Edit of Python files
    if tool_name not in ("Write", "Edit"):
        sys.exit(0)

    file_path = tool_input.get("file_path", "")
    if not file_path.endswith(".py"):
        sys.exit(0)

    try:
        result = subprocess.run(
            ["ruff", "check", "--no-fix", file_path],
            capture_output=True,
            text=True,
            timeout=30,
        )
    except (FileNotFoundError, subprocess.TimeoutExpired, Exception):
        # If ruff is not installed or times out, don't block
        sys.exit(0)

    if result.returncode != 0 and result.stdout.strip():
        print(json.dumps({
            "decision": "block",
            "reason": (
                f"ruff check found issues in {file_path}:\n"
                f"{result.stdout.strip()}\n\n"
                "Please fix these lint errors before continuing."
            ),
        }))
        sys.exit(0)

    # Clean — no output needed
    sys.exit(0)


if __name__ == "__main__":
    main()
