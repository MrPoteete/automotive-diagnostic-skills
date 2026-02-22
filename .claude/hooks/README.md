# Claude Code Hooks

This directory contains hooks that enforce quality standards and workflows.

## Active Hooks

### PreToolUse Hooks

| Hook | Matcher | Purpose |
|------|---------|---------|
| `pre_tool_use.py` | All tools | Safety gate for dangerous operations (rm -rf, raw_imports modification, .env access) |
| `delegation_check.py` | Write/Edit | Enforce agent/Gemini delegation consideration before direct implementation |
| `validators/precommit_validator.py` | Bash | Validate git commit operations |

### PostToolUse Hooks

| Hook | Matcher | Purpose |
|------|---------|---------|
| `validators/ruff_validator.py` | Write/Edit on .py | Python linting |
| `validators/mypy_validator.py` | Write/Edit on .py | Python type checking |

### Other Hooks

| Hook | Trigger | Purpose |
|------|---------|---------|
| `user_prompt_submit.py` | UserPromptSubmit | Audit log all user prompts |
| `stop_hook.py` | Stop | Remind to document session |

---

## Delegation Check Hook

**NEW**: Ensures agent/Gemini delegation is considered before direct implementation.

### How It Works

1. **Triggers**: Before Write/Edit to code files (.py, .js, .ts, etc.)
2. **Analyzes**: Content being written/edited for patterns
3. **Detects**:
   - Agent keywords (security, testing, refactoring, etc.)
   - Gemini keywords (boilerplate, simple function, documentation)
4. **Blocks**: If delegation patterns detected but not acknowledged
5. **Allows**: If delegation acknowledged or no patterns found

### Bypass Methods

Include any of these phrases in your code/comments/description:

- `"Checked AGENTS.md - implementing directly because [reason]"`
- `"Checked GEMINI_WORKFLOW.md - handling directly because [reason]"`
- `"No agent needed because [reason]"`
- `"Task tool"` (using Task tool means delegation considered)
- `"mcp__gemini"` (using Gemini MCP)

### Examples

#### ❌ Will Block

```python
# Writing security-related code without acknowledgment
def authenticate_user(username, password):
    query = f"SELECT * FROM users WHERE username='{username}'"
    # SQL injection risk - security-engineer should review
```

**Hook response**: "Delegation Check Required - security-engineer should review this"

#### ✅ Will Allow (Delegation Acknowledged)

```python
# Checked AGENTS.md - implementing directly because this is a simple
# validation helper that doesn't involve auth or sensitive data
def validate_username_format(username):
    return bool(re.match(r'^[a-zA-Z0-9_]{3,20}$', username))
```

#### ✅ Will Allow (Using Gemini)

```python
# Using Gemini MCP for simple boilerplate generation
# (Hook detects mcp__gemini keyword)
```

#### ✅ Will Allow (Using Agent)

```python
# Using Task tool to delegate to security-engineer
# (Hook detects Task tool usage)
```

---

## Detection Patterns

### Agent Patterns

| Agent | Keywords |
|-------|----------|
| security-engineer | auth, validation, security, input sanitization, sql injection, xss, csrf |
| quality-engineer | test coverage, edge case, quality assurance, testing strategy |
| python-expert | solid principles, python best practice, code review, refactor |
| data-engineer | database optimization, sqlite, query performance, data pipeline |
| system-architect | architecture decision, system design, architectural |
| refactoring-expert | refactor, cleanup, technical debt, code smell |
| performance-engineer | performance, optimization, bottleneck, profiling |

### Gemini Patterns

| Complexity | Keywords |
|------------|----------|
| Simple (flash) | boilerplate, simple function, basic implementation, documentation, docstring, utility function |
| Complex (pro) | research, web lookup, latest information, analyze, investigate, complex analysis |

---

## Logs

All delegation checks are logged to:
```
logs/{session_id}/delegation_check.json
```

Review logs to see when delegation was considered vs. bypassed.

---

## Configuration

Registered in `.claude/settings.json`:

```json
{
  "hooks": {
    "PreToolUse": [
      {
        "matcher": "Write|Edit",
        "hooks": [{
          "type": "command",
          "command": "uv run $CLAUDE_PROJECT_DIR/.claude/hooks/delegation_check.py"
        }]
      }
    ]
  }
}
```

---

## Benefits

1. **100% Reliability**: Deterministic enforcement (unlike CLAUDE.md suggestions)
2. **Token Efficiency**: Ensures Gemini delegation for tactical tasks
3. **Quality**: Ensures specialized agents review their domains
4. **Audit Trail**: Logs all delegation decisions
5. **Safety**: Prevents accidental direct implementation of safety-critical code

---

## Troubleshooting

### Hook blocks but I want to proceed

Add acknowledgment comment:
```python
# Checked AGENTS.md - implementing directly because this is a one-off
# utility that doesn't need specialized review
```

### Hook doesn't detect my pattern

The hook uses keyword matching. If your pattern isn't detected, it will allow.
This is intentional - we're permissive by default, only blocking clear matches.

### Want to disable temporarily

Edit `.claude/settings.json` and comment out the delegation_check hook.
**Not recommended** - defeats the purpose of deterministic enforcement.
