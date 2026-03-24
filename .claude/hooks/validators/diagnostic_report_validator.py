#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# ///
# Checked AGENTS.md - implementing directly because this is safety-critical quality enforcement
"""PostToolUse hook: validate diagnostic content in written .md files.

Fires after Write operations on Markdown files. If the written content looks
like a diagnostic report, enforces the presence of required sections
(📚 SOURCES, ⚖️ DISCLAIMER) and a categorical assessment level before
allowing the file to persist.

Violations are:
  1. Written to session state via set_violations() for downstream tracking.
  2. Surfaced to Claude as a block decision so the missing sections are added
     before the file is accepted.

Never blocks on import errors, state write failures, or unexpected input —
the validator must never disrupt a non-diagnostic workflow.
"""

import json
import sys
from pathlib import Path

# ---------------------------------------------------------------------------
# Path bootstrap — add .claude/hooks to sys.path so utils imports work
# regardless of the working directory when the hook is invoked.
# ---------------------------------------------------------------------------
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


def main() -> None:
    # ------------------------------------------------------------------
    # 1. Parse stdin JSON — never block on malformed input
    # ------------------------------------------------------------------
    try:
        raw_input = sys.stdin.read()
        data = json.loads(raw_input)
    except Exception:
        sys.exit(0)

    tool_name: str = data.get("tool_name", "")
    tool_input: dict = data.get("tool_input", {})
    session_id: str = data.get("session_id", "")

    # ------------------------------------------------------------------
    # 2. Only validate Write operations on .md files
    # ------------------------------------------------------------------
    if tool_name != "Write":
        sys.exit(0)

    file_path: str = tool_input.get("file_path", "")
    if not file_path.endswith(".md"):
        sys.exit(0)

    # ------------------------------------------------------------------
    # 2b. Skip internal project files — memory, docs, hooks, CLAUDE.md
    #     These contain automotive keywords but are NOT diagnostic reports.
    # ------------------------------------------------------------------
    _EXCLUDED_PATH_FRAGMENTS = (
        "/memory/",
        "/.claude/",
        "/docs/",
        "/tests/",
        "CLAUDE.md",
        "MEMORY.md",
        "LESSONS.md",
        "ARCHITECT.md",
        "DOMAIN.md",
        "DIAGRAMS.md",
    )
    if any(frag in file_path for frag in _EXCLUDED_PATH_FRAGMENTS):
        sys.exit(0)

    # ------------------------------------------------------------------
    # 3. Get file content
    # ------------------------------------------------------------------
    content: str = tool_input.get("content", "")
    if not content:
        sys.exit(0)

    # ------------------------------------------------------------------
    # 4. Import utils — if unavailable, exit silently
    # ------------------------------------------------------------------
    try:
        from utils.diagnostic_validator import is_diagnostic_content, run_content_invariants
        from utils.session_state import set_violations
    except Exception:
        sys.exit(0)

    # ------------------------------------------------------------------
    # 5. Skip non-diagnostic files
    # ------------------------------------------------------------------
    try:
        if not is_diagnostic_content(content):
            sys.exit(0)
    except Exception:
        sys.exit(0)

    # ------------------------------------------------------------------
    # 6. Run content invariants
    # ------------------------------------------------------------------
    try:
        violations = run_content_invariants(content)
    except Exception:
        sys.exit(0)

    if not violations:
        sys.exit(0)

    # ------------------------------------------------------------------
    # 7a. Persist violations to session state (best-effort)
    # ------------------------------------------------------------------
    if session_id:
        try:
            set_violations(session_id, violations)
        except Exception:
            pass  # Never block on state write failure

    # ------------------------------------------------------------------
    # 7b. Emit block decision with actionable message
    # ------------------------------------------------------------------
    bullet_lines = "\n".join(f"  \u2022 {v}" for v in violations)
    reason = (
        "Diagnostic content validation failed. Add the following missing "
        "sections before writing:\n\n"
        f"{bullet_lines}\n\n"
        "These sections are MANDATORY per skills/SKILL.md. Add them and retry."
    )

    print(json.dumps({"decision": "block", "reason": reason}))
    sys.exit(0)


if __name__ == "__main__":
    main()
