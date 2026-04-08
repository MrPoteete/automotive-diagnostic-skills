#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# ///
"""PreToolUse hook: safety gate for dangerous operations.

Blocks:
- Dangerous rm commands (rm -rf, recursive rm on critical paths)
- Modification of data/raw_imports/ (Write, Edit, Bash rm/mv/cp)
- .env file access via Write/Edit (prevent credential leaks)

Logs all tool invocations to logs/{session_id}/pre_tool_use.json.
"""

import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

# Add parent for utils import
sys.path.insert(0, str(Path(__file__).resolve().parent))
from utils.constants import ensure_session_log_dir


def log_invocation(session_id, tool_name, tool_input, decision, reason=""):
    """Append tool invocation to the session log file."""
    try:
        log_dir = ensure_session_log_dir(session_id)
        log_file = log_dir / "pre_tool_use.json"

        entries = []
        if log_file.exists():
            content = log_file.read_text(encoding="utf-8").strip()
            if content:
                entries = json.loads(content)

        entries.append({
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "tool_name": tool_name,
            "tool_input_keys": list(tool_input.keys()) if isinstance(tool_input, dict) else [],
            "decision": decision,
            "reason": reason,
        })

        log_file.write_text(
            json.dumps(entries, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
    except Exception:
        pass  # Never let logging crash the hook


def deny(reason):
    """Output a deny decision and exit cleanly."""
    print(json.dumps({
        "decision": "block",
        "reason": reason,
    }))
    sys.exit(0)


def check_dangerous_rm(command):
    """Check if a Bash command contains dangerous rm operations."""
    # Dangerous rm patterns
    dangerous_patterns = [
        r"\brm\s+.*-[a-z]*r[a-z]*f",  # rm -rf, rm -rfi, etc.
        r"\brm\s+.*-[a-z]*f[a-z]*r",  # rm -fr, rm -fir, etc.
        r"\brm\s+.*\s+/\s*$",         # rm ... /
        r"\brm\s+.*\s+~/",            # rm ... ~/
        r"\brm\s+.*\s+\.\s*$",        # rm ... .
        r"\brm\s+.*\s+\.\.\s*$",      # rm ... ..
    ]
    for pattern in dangerous_patterns:
        if re.search(pattern, command):
            return True
    return False


def check_raw_imports_modification(tool_name, tool_input):
    """Check if the operation modifies data/raw_imports/."""
    raw_imports_pattern = r"data/raw_imports"

    if tool_name in ("Write", "Edit"):
        file_path = tool_input.get("file_path", "")
        if raw_imports_pattern in file_path:
            return True

    if tool_name == "Bash":
        command = tool_input.get("command", "")
        # Check if command targets raw_imports with modifying operations
        modify_commands = r"\b(rm|mv|cp|sed|awk|tee|cat\s*>|echo\s*>)\b"
        if re.search(modify_commands, command) and raw_imports_pattern in command:
            return True

    return False


def check_env_file_access(tool_name, tool_input):
    """Check if the operation writes to .env files.

    Covers both tool-based writes (Write/Edit) and Bash redirection
    (echo/printf/tee piped or redirected into .env files).
    """
    if tool_name in ("Write", "Edit"):
        file_path = tool_input.get("file_path", "")
        basename = Path(file_path).name if file_path else ""
        # Block .env and .env.* but allow .env.example (safe template)
        if basename == ".env" or (basename.startswith(".env.") and not basename.endswith(".example")):
            return True

    if tool_name == "Bash":
        command = tool_input.get("command", "")
        # Detect write redirection targeting .env files
        # Matches: echo ... > .env, printf ... >> .env, tee .env, tee -a .env
        env_target = r'\.env(?:\.[a-zA-Z]+)?\b'
        write_redirect = r'(?:echo|printf|tee)\b.*(?:>|>>|\|)'
        if re.search(write_redirect, command) and re.search(env_target, command):
            # Allow if only targeting .env.example
            if not re.search(r'\.env\.example', command):
                return True

    return False


def check_hooks_modification(tool_name, tool_input):
      """Block modifications to core hook entry points only.

      Validators, utils, and support files under .claude/hooks/ are editable.
      Only pre_tool_use.py and post_tool_use.py are protected.
      """
      _PROTECTED = {"pre_tool_use.py", "post_tool_use.py"}

      if tool_name in ("Write", "Edit"):
          file_path = tool_input.get("file_path", "")
          if ".claude/hooks" in file_path and Path(file_path).name in _PROTECTED:
              return True

      if tool_name == "Bash":
          command = tool_input.get("command", "")
          if re.search(r"\.claude/hooks", command):
              if re.search(r"\bchmod\b", command):
                  return True
              if re.search(r"\bsed\s+.*-i\b.*(?:pre_tool_use|post_tool_use)", command):
                  return True

      return False

def main():
    try:
        raw_input = sys.stdin.read()
        data = json.loads(raw_input)
    except (json.JSONDecodeError, Exception):
        sys.exit(0)

    tool_name = data.get("tool_name", "")
    tool_input = data.get("tool_input", {})
    session_id = data.get("session_id", "unknown")

    # Check dangerous rm commands
    if tool_name == "Bash":
        command = tool_input.get("command", "")
        if check_dangerous_rm(command):
            log_invocation(session_id, tool_name, tool_input, "deny", "Dangerous rm command blocked")
            deny(
                "BLOCKED: Dangerous recursive rm command detected. "
                "This could delete critical project files. "
                "Please use a more targeted delete command."
            )

    # Check raw_imports modification
    if check_raw_imports_modification(tool_name, tool_input):
        log_invocation(session_id, tool_name, tool_input, "deny", "raw_imports modification blocked")
        deny(
            "BLOCKED: Modification of data/raw_imports/ is not allowed. "
            "This directory contains original source files that must never be modified. "
            "Work with copies in data/knowledge_base/ instead."
        )

    # Check .env file access
    if check_env_file_access(tool_name, tool_input):
        log_invocation(session_id, tool_name, tool_input, "deny", ".env file write blocked")
        deny(
            "BLOCKED: Writing to .env files is not allowed via hooks. "
            "Credential files should be managed manually to prevent leaks."
        )

    # Check hooks directory modification (self-sabotage prevention)
    if check_hooks_modification(tool_name, tool_input):
        log_invocation(session_id, tool_name, tool_input, "deny", ".claude/hooks modification blocked")
        deny(
            "BLOCKED: Modification of .claude/hooks/ is not allowed. "
            "Hook files are security infrastructure and must not be altered by automated operations."
        )

    # Log allowed invocation
    log_invocation(session_id, tool_name, tool_input, "allow")
    sys.exit(0)


if __name__ == "__main__":
    main()
