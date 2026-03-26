#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# ///
"""PreToolUse hook: validate Python code before git commit.

Intercepts Bash commands containing 'git commit' and runs:
1. ruff check on all staged .py files
2. mypy type checking on all staged .py files
3. pytest (if available and tests exist)

Blocks the commit if any check fails.
"""

import json
import re
import subprocess
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent


def get_staged_python_files() -> list[str]:
    """Return list of staged .py files (excluding deleted)."""
    try:
        result = subprocess.run(
            ["git", "diff", "--cached", "--name-only", "--diff-filter=d"],
            capture_output=True,
            text=True,
            timeout=10,
            cwd=PROJECT_ROOT,
        )
        if result.returncode != 0:
            return []
        return [
            f for f in result.stdout.strip().splitlines() if f.endswith(".py")
        ]
    except Exception:
        return []


def run_ruff(files: list[str]) -> str | None:
    """Run ruff check on files. Returns error message or None."""
    if not files:
        return None
    try:
        result = subprocess.run(
            ["ruff", "check", "--no-fix", *files],
            capture_output=True,
            text=True,
            timeout=30,
            cwd=PROJECT_ROOT,
        )
        if result.returncode != 0 and result.stdout.strip():
            return result.stdout.strip()
    except (FileNotFoundError, subprocess.TimeoutExpired):
        pass
    return None


def run_mypy(files: list[str]) -> str | None:
    """Run mypy on files. Returns error message or None."""
    if not files:
        return None
    try:
        result = subprocess.run(
            ["mypy", "--ignore-missing-imports", "--no-error-summary", *files],
            capture_output=True,
            text=True,
            timeout=120,
            cwd=PROJECT_ROOT,
        )
        if result.returncode != 0 and result.stdout.strip():
            error_lines = [
                line
                for line in result.stdout.strip().splitlines()
                if ": error" in line
            ]
            if error_lines:
                return "\n".join(error_lines)
    except (FileNotFoundError, subprocess.TimeoutExpired):
        pass
    return None


def run_pytest() -> str | None:
    """Run pytest if available and tests exist. Returns error message or None."""
    # Check for test directories or files
    has_tests = any((PROJECT_ROOT / d).exists() for d in ("tests", "test"))
    if not has_tests:
        return None

    # Prefer venv pytest → uv run → bare python3 (in order of availability)
    venv_pytest = PROJECT_ROOT / ".venv" / "bin" / "pytest"
    if venv_pytest.exists():
        pytest_cmd = [str(venv_pytest), "--tb=short", "-q", "--ignore=tests/integration"]
    else:
        # VM has no venv — use uv run with inline deps
        pytest_cmd = [
            "uv", "run",
            "--with", "pytest",
            "--with", "pytest-asyncio",
            "--with", "pytest-mock",
            "python", "-m", "pytest", "--tb=short", "-q", "--ignore=tests/integration",
        ]

    try:
        result = subprocess.run(
            pytest_cmd,
            capture_output=True,
            text=True,
            timeout=300,
            cwd=PROJECT_ROOT,
        )
        if result.returncode != 0:
            output = result.stdout.strip()
            if result.stderr.strip():
                output += "\n" + result.stderr.strip()
            return output or "pytest exited with errors"
    except (FileNotFoundError, subprocess.TimeoutExpired):
        pass
    return None


def is_git_commit_command(command: str) -> bool:
    """Check if the command is a git commit."""
    return bool(re.search(r"\bgit\s+commit\b", command))


def main():
    try:
        raw_input = sys.stdin.read()
        data = json.loads(raw_input)
    except (json.JSONDecodeError, Exception):
        sys.exit(0)

    tool_name = data.get("tool_name", "")
    tool_input = data.get("tool_input", {})

    if tool_name != "Bash":
        sys.exit(0)

    command = tool_input.get("command", "")
    if not is_git_commit_command(command):
        sys.exit(0)

    # Get staged Python files
    py_files = get_staged_python_files()

    if not py_files:
        # No Python files staged — allow commit
        sys.exit(0)

    errors: list[str] = []

    # Skip legacy/one-time scripts that predate linting and type-checking
    # Note: git returns relative paths (no leading slash), so match without it
    SKIP_PREFIXES = ("database/", "scripts/legacy/")
    active_py_files = [f for f in py_files if not any(f.startswith(p) for p in SKIP_PREFIXES)]

    # Run ruff
    ruff_errors = run_ruff(active_py_files)
    if ruff_errors:
        errors.append(f"## ruff errors\n{ruff_errors}")

    # Run mypy
    mypy_files = active_py_files
    mypy_errors = run_mypy(mypy_files)
    if mypy_errors:
        errors.append(f"## mypy errors\n{mypy_errors}")

    # Run pytest
    pytest_errors = run_pytest()
    if pytest_errors:
        errors.append(f"## pytest failures\n{pytest_errors}")

    if errors:
        separator = "\n\n"
        print(
            json.dumps(
                {
                    "decision": "block",
                    "reason": (
                        f"Pre-commit validation failed for {len(py_files)} "
                        f"staged Python file(s):\n\n"
                        f"{separator.join(errors)}\n\n"
                        "Fix these issues before committing."
                    ),
                }
            )
        )
        sys.exit(0)

    # All checks passed
    sys.exit(0)


if __name__ == "__main__":
    main()
