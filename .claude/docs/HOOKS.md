# Hook Infrastructure

## Overview

Hooks provide **deterministic enforcement** of quality standards. Unlike CLAUDE.md instructions (suggestions), hooks **force** compliance.

**Location**: `.claude/hooks/`
**Configuration**: `.claude/settings.json`

---

## Active Hooks

### PreToolUse Hooks

**Trigger**: Before any tool executes

| Hook | Matcher | Purpose | Blocks? |
|------|---------|---------|---------|
| `pre_tool_use.py` | All tools | Safety gate (rm, raw_imports, .env) | Yes (if dangerous) |
| `delegation_check.py` | Write/Edit | Enforce agent/Gemini delegation consideration | Yes (if not acknowledged) |
| `precommit_validator.py` | Bash only | Validates git commits | Yes (if errors) |

### PostToolUse Hooks

**Trigger**: After tool completes

| Hook | Matcher | Purpose | Blocks? |
|------|---------|---------|---------|
| `ruff_validator.py` | Write/Edit on .py | Lint Python files | Yes (if lint errors) |
| `mypy_validator.py` | Write/Edit on .py | Type check Python files | Yes (if type errors) |

### UserPromptSubmit Hook

**Trigger**: When user submits a prompt

| Hook | Purpose | Blocks? |
|------|---------|---------|
| `user_prompt_submit.py` | Audit log all prompts | No |

**Logging**: Saves to `logs/{session_id}/prompts.json`

### Stop Hook

**Trigger**: When session ends

| Hook | Purpose | Blocks? |
|------|---------|---------|
| `stop_hook.py` | Remind to document session | No (warning only) |

**Checks**: Looks for session docs in `docs/sessions/`

---

## Hook Configuration

**File**: `.claude/settings.json`

```json
{
  "hooks": {
    "PreToolUse": [
      {
        "matcher": "Bash",
        "hooks": [{
          "type": "command",
          "command": "uv run $CLAUDE_PROJECT_DIR/.claude/hooks/validators/precommit_validator.py"
        }]
      }
    ],
    "PostToolUse": [
      {
        "matcher": "Write|Edit",
        "hooks": [
          {
            "type": "command",
            "command": "uv run $CLAUDE_PROJECT_DIR/.claude/hooks/validators/ruff_validator.py"
          },
          {
            "type": "command",
            "command": "uv run $CLAUDE_PROJECT_DIR/.claude/hooks/validators/mypy_validator.py"
          }
        ]
      }
    ],
    "Stop": [{
      "hooks": [{
        "type": "command",
        "command": "uv run $CLAUDE_PROJECT_DIR/.claude/hooks/stop_hook.py"
      }]
    }]
  }
}
```

---

## Delegation Check Hook

**Purpose**: Ensure agent/Gemini delegation is considered before direct implementation

**Triggers on**: Write/Edit to code files (.py, .js, .ts, etc.)

**Detection patterns**:
- **Agent patterns**: Security keywords → security-engineer, testing keywords → quality-engineer, etc.
- **Gemini patterns**: "boilerplate", "simple function", "documentation" → Gemini delegation

**Bypass methods**:
1. Include acknowledgment in code/description: `"Checked AGENTS.md - implementing directly because..."`
2. Use delegation keywords: `"Task tool"`, `"delegate"`, `"mcp__gemini"`
3. Implement from within a subagent (auto-allowed)

**Example - Will block**:
```python
# Writing code with security keywords without acknowledgment
def validate_user_input(data):
    # SQL query here...
```

**Example - Will allow**:
```python
# Checked AGENTS.md - implementing directly because this is a simple validation
# that doesn't need security-engineer review (no auth/sensitive data)
def validate_user_input(data):
    # Input validation here...
```

---

## Deterministic Quality Gates

**Hooks vs. Instructions**:

| Method | Type | Reliability | Use Case |
|--------|------|-------------|----------|
| CLAUDE.md instructions | Suggestion | ~85% | General guidelines |
| Hooks | Enforcement | 100% | Critical standards |

**Example - Code Formatting**:

❌ **Bad** (instruction only):
```markdown
# CLAUDE.md
Always run `ruff format` after editing Python files.
```
→ Model may forget under high context pressure

✅ **Good** (hook enforcement):
```python
# .claude/hooks/validators/ruff_validator.py
# Automatically runs after Write/Edit on .py files
# Blocks if lint errors found
```
→ Guaranteed to run, cannot be forgotten

---

## Rule Evolution Hook (Planned)

**Purpose**: Automatically update CLAUDE.md or reference files when mistakes are corrected

**Workflow**:
1. User corrects a mistake: "No, don't do X. Always do Y instead."
2. Hook detects correction pattern
3. Prompts: "Update CLAUDE.md to prevent this mistake?"
4. If yes: Appends rule to `.claude/docs/LESSONS.md`

**Implementation** (future):
```python
# .claude/hooks/correction_detector.py
def detect_correction(user_message: str) -> bool:
    """Detect if user is correcting a mistake."""
    correction_patterns = [
        r"no,? (don't|do not)",
        r"actually,? (you should|do)",
        r"incorrect,? (the correct way is)"
    ]
    return any(re.search(pattern, user_message.lower())
               for pattern in correction_patterns)

def prompt_rule_update(correction: str):
    """Ask user if they want to save this correction as a rule."""
    print(f"Detected correction: {correction}")
    print("Update CLAUDE.md to prevent this mistake? (y/n)")
```

---

## Common Pitfalls

### Exit Code Confusion

**Wrong**:
```python
if should_block:
    sys.exit(1)  # ❌ Wrong - exit code doesn't control blocking
else:
    sys.exit(0)
```

**Correct**:
```python
if should_block:
    print(json.dumps({"decision": "block", "reason": "..."}))
    sys.exit(0)  # ✅ Always exit(0), JSON controls blocking
else:
    sys.exit(0)
```

### Context Limitations

**Hooks receive**:
- `tool_name` - The tool being called (Write, Edit, Bash, etc.)
- `tool_input` - Tool parameters (file_path, content, command, etc.)
- `session_id` - Current session identifier

**Hooks DO NOT receive**:
- Conversation history
- Recent user messages
- Previous tool results

**Solution**: Analyze `tool_input["content"]`, `tool_input["description"]`, or file content directly.

---

## Hook Development Guidelines

**Creating a new hook**:

1. **Location**: `.claude/hooks/your_hook.py`
2. **Shebang**: `#!/usr/bin/env -S uv run --script`
3. **Input**: Read JSON from stdin
4. **Output**: Write JSON to stdout
5. **Exit codes**:
   - `0` = Allow (continue)
   - `non-zero` = Block (show error)

**Template**:
```python
#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# ///
import json
import sys

def main():
    try:
        raw_input = sys.stdin.read()
        data = json.loads(raw_input)
    except (json.JSONDecodeError, Exception):
        sys.exit(0)  # Never block on hook failure

    # Your validation logic here

    if should_block:
        print(json.dumps({
            "decision": "block",
            "reason": "Explanation of why blocking"
        }))
        sys.exit(0)  # Always exit(0) — JSON controls blocking, not exit code

    sys.exit(0)  # Allow

if __name__ == "__main__":
    main()
```

**Register in `.claude/settings.json`**:
```json
{
  "hooks": {
    "PreToolUse": [{
      "matcher": "ToolName",
      "hooks": [{
        "type": "command",
        "command": "uv run $CLAUDE_PROJECT_DIR/.claude/hooks/your_hook.py"
      }]
    }]
  }
}
```
