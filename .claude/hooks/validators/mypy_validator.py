#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# ///
"""PostToolUse hook: run mypy type checking on Python files after Write/Edit.

If mypy finds type errors, outputs a block decision so Claude sees the errors
and fixes them before continuing. Skips non-Python files silently.
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

    if tool_name not in ("Write", "Edit"):
        sys.exit(0)

    file_path = tool_input.get("file_path", "")
    if not file_path.endswith(".py"):
        sys.exit(0)

    # Skip hook files themselves to avoid circular issues
    if "/.claude/hooks/" in file_path:
        sys.exit(0)

    try:
        result = subprocess.run(
            [
                "mypy",
                "--ignore-missing-imports",
                "--no-error-summary",
                file_path,
            ],
            capture_output=True,
            text=True,
            timeout=60,
        )
    except (FileNotFoundError, subprocess.TimeoutExpired, Exception):
        # If mypy is not installed or times out, don't block
        sys.exit(0)

    if result.returncode != 0 and result.stdout.strip():
        # Filter out "note:" lines to reduce noise — keep only errors
        error_lines = [
            line
            for line in result.stdout.strip().splitlines()
            if ": error" in line
        ]
        if error_lines:
            print(
                json.dumps(
                    {
                        "decision": "block",
                        "reason": (
                            f"mypy found type errors in {file_path}:\n"
                            f"{chr(10).join(error_lines)}\n\n"
                            "Please fix these type errors before continuing."
                        ),
                    }
                )
            )
            sys.exit(0)

    # Clean — no output needed
    sys.exit(0)


if __name__ == "__main__":
    main()
