#!/usr/bin/env python3
"""Hook integration tests - validates all hooks work correctly in WSL."""

import json
import subprocess
import sys
from pathlib import Path

PROJECT_DIR = Path(__file__).resolve().parent.parent.parent
HOOKS_DIR = PROJECT_DIR / ".claude" / "hooks"
ENV = {"CLAUDE_PROJECT_DIR": str(PROJECT_DIR), "PATH": "/home/poteete/.local/bin:/usr/bin:/bin"}

PASS = "✅ PASS"
FAIL = "❌ FAIL"


def run_hook(hook_path: str, payload: dict) -> tuple[str, int]:
    """Run a hook with a JSON payload, return (stdout, exit_code)."""
    result = subprocess.run(
        ["uv", "run", hook_path],
        input=json.dumps(payload),
        capture_output=True,
        text=True,
        env=ENV,
    )
    return result.stdout.strip(), result.returncode


def expect_block(label: str, hook: str, payload: dict):
    out, _ = run_hook(hook, payload)
    try:
        decision = json.loads(out).get("decision") if out else None
    except json.JSONDecodeError:
        decision = None

    if decision == "block":
        print(f"{PASS}: {label}")
    else:
        print(f"{FAIL}: {label} — expected block, got: {out!r}")


def expect_allow(label: str, hook: str, payload: dict):
    out, _ = run_hook(hook, payload)
    try:
        decision = json.loads(out).get("decision") if out else None
    except json.JSONDecodeError:
        decision = None

    if decision == "block":
        print(f"{FAIL}: {label} — unexpectedly blocked: {out!r}")
    else:
        print(f"{PASS}: {label}")


def test_pre_tool_use():
    hook = str(HOOKS_DIR / "pre_tool_use.py")
    print("\n=== pre_tool_use.py ===")

    # Safe commands — allow
    expect_allow("safe echo command", hook,
        {"session_id": "test", "tool_name": "Bash", "tool_input": {"command": "echo hello"}})

    expect_allow("safe ls command", hook,
        {"session_id": "test", "tool_name": "Bash", "tool_input": {"command": "ls -la"}})

    expect_allow("normal python write", hook,
        {"session_id": "test", "tool_name": "Write",
         "tool_input": {"file_path": "src/main.py", "content": "print('hello')"}})

    expect_allow(".env.example write allowed", hook,
        {"session_id": "test", "tool_name": "Write",
         "tool_input": {"file_path": "/project/.env.example", "content": "SECRET=changeme"}})

    # Dangerous rm — block
    rm_rf = "rm -rf /tmp/test"
    expect_block("rm -rf blocked", hook,
        {"session_id": "test", "tool_name": "Bash", "tool_input": {"command": rm_rf}})

    rm_fr = "rm -fr important_stuff"
    expect_block("rm -fr blocked", hook,
        {"session_id": "test", "tool_name": "Bash", "tool_input": {"command": rm_fr}})

    # raw_imports protection — block
    expect_block("Write to raw_imports blocked", hook,
        {"session_id": "test", "tool_name": "Write",
         "tool_input": {"file_path": "data/raw_imports/file.txt", "content": "bad"}})

    raw_rm = "rm data/raw_imports/file.txt"
    expect_block("rm in raw_imports blocked", hook,
        {"session_id": "test", "tool_name": "Bash", "tool_input": {"command": raw_rm}})

    raw_mv = "mv data/raw_imports/a.txt /tmp/"
    expect_block("mv from raw_imports blocked", hook,
        {"session_id": "test", "tool_name": "Bash", "tool_input": {"command": raw_mv}})

    # .env protection — block
    expect_block("Write to .env blocked", hook,
        {"session_id": "test", "tool_name": "Write",
         "tool_input": {"file_path": "/project/.env", "content": "SECRET=bad"}})

    expect_block("Write to .env.local blocked", hook,
        {"session_id": "test", "tool_name": "Write",
         "tool_input": {"file_path": "/project/.env.local", "content": "SECRET=bad"}})


def test_delegation_check():
    hook = str(HOOKS_DIR / "delegation_check.py")
    print("\n=== delegation_check.py ===")

    # Non-code files — always allow
    expect_allow("markdown file skipped", hook,
        {"session_id": "test", "tool_name": "Write",
         "tool_input": {"file_path": "docs/README.md", "content": "# Docs"}})

    expect_allow("json config skipped", hook,
        {"session_id": "test", "tool_name": "Write",
         "tool_input": {"file_path": "settings.json", "content": "{}"}})

    # Code file, no matching patterns — allow
    expect_allow("simple util function, no patterns", hook,
        {"session_id": "test", "tool_name": "Write",
         "tool_input": {"file_path": "src/utils.py",
                        "content": "def add(a, b):\n    return a + b\n"}})

    # Code file with delegation acknowledged — allow
    expect_allow("security code with acknowledgment", hook,
        {"session_id": "test", "tool_name": "Write",
         "tool_input": {"file_path": "src/auth.py",
                        "content": "# Checked AGENTS.md - implementing directly because simple validation\ndef validate_input(data):\n    return bool(data)\n"}})

    expect_allow("task tool mention allows", hook,
        {"session_id": "test", "tool_name": "Write",
         "tool_input": {"file_path": "src/validator.py",
                        "content": "# Using Task tool for delegation\ndef check_auth(token): pass\n"}})

    # Code file with security keywords, no acknowledgment — block
    expect_block("security code without acknowledgment blocked", hook,
        {"session_id": "test", "tool_name": "Write",
         "tool_input": {"file_path": "src/validator.py",
                        "content": "def validate_sql_injection(query):\n    # auth validation security check\n    pass\n"}})

    # Code file with refactor/cleanup keywords — block
    expect_block("refactor keyword without acknowledgment blocked", hook,
        {"session_id": "test", "tool_name": "Write",
         "tool_input": {"file_path": "src/helper.py",
                        "content": "# refactor this code smell\ndef old_function(): pass\n"}})


def test_user_prompt_submit():
    hook = str(HOOKS_DIR / "user_prompt_submit.py")
    print("\n=== user_prompt_submit.py (non-blocking, just logs) ===")

    out, code = run_hook(hook, {
        "session_id": "test-wsl",
        "prompt": "Test prompt from WSL migration",
    })
    # This hook only logs — should never block
    if json.loads(out).get("decision") == "block" if out else False:
        print(f"{FAIL}: user_prompt_submit should never block")
    else:
        print(f"{PASS}: user_prompt_submit allows (exit={code})")


if __name__ == "__main__":
    print(f"Project: {PROJECT_DIR}")
    print("uv: ", end="")
    sys.stdout.flush()
    subprocess.run(["uv", "--version"], env=ENV)

    test_pre_tool_use()
    test_delegation_check()
    test_user_prompt_submit()

    print("\nDone.")
