#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# ///
"""UserPromptSubmit hook: audit logger for user prompts.

Logs every user prompt with timestamp and session_id to
logs/{session_id}/prompts.json. Purely observational — never blocks.
"""

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from utils.constants import ensure_session_log_dir


def main():
    try:
        raw_input = sys.stdin.read()
        data = json.loads(raw_input)
    except (json.JSONDecodeError, Exception):
        sys.exit(0)

    session_id = data.get("session_id", "unknown")
    prompt = data.get("prompt", "")

    try:
        log_dir = ensure_session_log_dir(session_id)
        log_file = log_dir / "prompts.json"

        entries = []
        if log_file.exists():
            content = log_file.read_text(encoding="utf-8").strip()
            if content:
                entries = json.loads(content)

        entries.append({
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "session_id": session_id,
            "prompt_length": len(prompt),
            "prompt_preview": prompt[:200] if prompt else "",
        })

        log_file.write_text(
            json.dumps(entries, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
    except Exception:
        pass  # Never block on logging failure

    sys.exit(0)


if __name__ == "__main__":
    main()
