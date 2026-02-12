#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# ///
"""StatusLine hook: display context window usage.

Reads stdin JSON, extracts context_window.used_percentage and model name.
Outputs a single formatted line with ANSI colors.
"""

import json
import sys


def main():
    try:
        raw_input = sys.stdin.read()
        data = json.loads(raw_input)
    except (json.JSONDecodeError, Exception):
        print("Auto Diagnostics")
        sys.exit(0)

    # Extract context window info
    context_window = data.get("context_window", {})
    used_pct = context_window.get("used_percentage", 0)
    model = data.get("model", "unknown")

    # Color based on usage level
    if used_pct >= 80:
        color = "\033[31m"  # Red
        indicator = "!!!"
    elif used_pct >= 60:
        color = "\033[33m"  # Yellow
        indicator = "!!"
    elif used_pct >= 40:
        color = "\033[36m"  # Cyan
        indicator = "!"
    else:
        color = "\033[32m"  # Green
        indicator = ""

    reset = "\033[0m"

    # Build status line
    bar_width = 15
    filled = int(bar_width * used_pct / 100)
    empty = bar_width - filled
    bar = f"{'█' * filled}{'░' * empty}"

    line = (
        f"Auto Dx | {color}{bar} {used_pct:.0f}%{reset} "
        f"| {model} {indicator}"
    )

    print(line)
    sys.exit(0)


if __name__ == "__main__":
    main()
