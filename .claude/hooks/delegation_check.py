#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# ///
"""Delegation Check Hook: Ensure agent/Gemini delegation is considered.

Before implementing directly with Write/Edit, checks if:
1. A specialized agent should handle this (AGENTS.md)
2. Gemini should handle this (GEMINI_WORKFLOW.md)

Blocks if delegation wasn't explicitly considered.
Allows if delegation was mentioned or task is clearly direct implementation.
"""

import json
import sys
from pathlib import Path

# Add parent for utils import
sys.path.insert(0, str(Path(__file__).resolve().parent))
from utils.constants import ensure_session_log_dir
from datetime import datetime, timezone


def log_delegation_check(session_id, tool_name, file_path, decision, reason=""):
    """Log delegation check decisions."""
    try:
        log_dir = ensure_session_log_dir(session_id)
        log_file = log_dir / "delegation_check.json"

        entries = []
        if log_file.exists():
            content = log_file.read_text(encoding="utf-8").strip()
            if content:
                entries = json.loads(content)

        entries.append({
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "tool_name": tool_name,
            "file_path": file_path,
            "decision": decision,
            "reason": reason,
        })

        log_file.write_text(
            json.dumps(entries, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
    except Exception:
        pass  # Never let logging crash the hook


def block(reason):
    """Output a block decision and exit."""
    print(json.dumps({
        "decision": "block",
        "reason": reason,
    }))
    sys.exit(0)


# Agent/Gemini detection patterns
AGENT_PATTERNS = {
    "security-engineer": {
        "keywords": ["auth", "validation", "security", "input sanitization", "sql injection", "xss", "csrf"],
        "description": "Security review needed for auth/validation code"
    },
    "quality-engineer": {
        "keywords": ["test coverage", "edge case", "quality assurance", "testing strategy"],
        "description": "Quality review for test coverage and edge cases"
    },
    "python-expert": {
        "keywords": ["solid principles", "python best practice", "code review", "refactor"],
        "description": "Python expert review for SOLID principles and best practices"
    },
    "data-engineer": {
        "keywords": ["database optimization", "sqlite", "query performance", "data pipeline"],
        "description": "Data engineer for database/query work"
    },
    "system-architect": {
        "keywords": ["architecture decision", "system design", "architectural"],
        "description": "System architect for architectural decisions"
    },
    "refactoring-expert": {
        "keywords": ["refactor", "cleanup", "technical debt", "code smell"],
        "description": "Refactoring expert for code cleanup"
    },
    "performance-engineer": {
        "keywords": ["performance", "optimization", "bottleneck", "profiling"],
        "description": "Performance engineer for optimization work"
    }
}

GEMINI_SIMPLE_PATTERNS = [
    "boilerplate", "simple function", "basic implementation",
    "documentation", "docstring", "comment", "simple refactor",
    "utility function", "helper function"
]

GEMINI_COMPLEX_PATTERNS = [
    "research", "web lookup", "latest information",
    "analyze", "investigate", "complex analysis"
]

# Delegation acknowledgment patterns
DELEGATION_ACKNOWLEDGED = [
    "checked agents.md",
    "checked gemini_workflow",
    "consulted agents.md",
    "reviewed delegation",
    "handling directly because",
    "no agent needed because",
    "implementing directly because",
    "task tool",  # Using Task tool means delegation considered
    "mcp__gemini",  # Using Gemini MCP
    "delegate",
    "using.*agent",
]


def is_code_file(file_path):
    """Check if file is a code file (not docs/config)."""
    if not file_path:
        return False

    code_extensions = [".py", ".js", ".ts", ".tsx", ".jsx", ".java", ".go", ".rs", ".cpp", ".c", ".h"]
    docs_paths = ["docs/", "README", ".md", ".txt", ".json", ".yaml", ".yml", ".toml", ".env"]

    # Check if it's a code file
    if any(file_path.endswith(ext) for ext in code_extensions):
        # But not if it's in docs or a config file
        if any(path in file_path for path in docs_paths):
            return False
        return True

    return False


def detect_task_type(recent_context):
    """Detect if task matches agent or Gemini patterns."""
    context_lower = recent_context.lower()

    matching_agents = []
    for agent_name, agent_info in AGENT_PATTERNS.items():
        if any(keyword in context_lower for keyword in agent_info["keywords"]):
            matching_agents.append({
                "name": agent_name,
                "reason": agent_info["description"]
            })

    gemini_match = None
    if any(pattern in context_lower for pattern in GEMINI_SIMPLE_PATTERNS):
        gemini_match = "simple (gemini-2.5-flash)"
    elif any(pattern in context_lower for pattern in GEMINI_COMPLEX_PATTERNS):
        gemini_match = "complex (gemini-2.5-pro)"

    return matching_agents, gemini_match


def was_delegation_acknowledged(recent_context):
    """Check if I explicitly acknowledged checking delegation."""
    context_lower = recent_context.lower()
    return any(pattern in context_lower for pattern in DELEGATION_ACKNOWLEDGED)


def main():
    try:
        raw_input = sys.stdin.read()
        data = json.loads(raw_input)
    except (json.JSONDecodeError, Exception) as e:
        import sys as sys_stderr
        sys_stderr.stderr.write(f"ERROR parsing JSON: {e}\n")
        sys.exit(0)  # Never crash the hook

    tool_name = data.get("tool_name", "")
    tool_input = data.get("tool_input", {})
    session_id = data.get("session_id", "unknown")

    # Only check Write/Edit on code files
    if tool_name not in ["Write", "Edit"]:
        sys.exit(0)

    file_path = tool_input.get("file_path", "")

    # Skip if not a code file
    if not is_code_file(file_path):
        log_delegation_check(session_id, tool_name, file_path, "allow", "Not a code file")
        sys.exit(0)

    # Get the content being written/edited
    content = ""
    if tool_name == "Write":
        content = tool_input.get("content", "")
    elif tool_name == "Edit":
        content = tool_input.get("old_string", "") + " " + tool_input.get("new_string", "")

    # Check if delegation was acknowledged in the content or description
    description = tool_input.get("description", "")
    search_text = (content + " " + description).lower()

    if was_delegation_acknowledged(search_text):
        log_delegation_check(session_id, tool_name, file_path, "allow", "Delegation explicitly considered")
        sys.exit(0)

    # Detect if task matches agent/Gemini patterns
    matching_agents, gemini_match = detect_task_type(search_text)

    # If no strong matches, assume direct implementation is fine
    # We're being permissive here - only block if there's a clear pattern
    if not matching_agents and not gemini_match:
        log_delegation_check(session_id, tool_name, file_path, "allow", "No delegation patterns detected")
        sys.exit(0)

    # Build suggestion message
    suggestions = ["🤖 **Delegation Check Required**", ""]
    suggestions.append(f"Before implementing `{Path(file_path).name}`, verify delegation:")
    suggestions.append("")

    if matching_agents:
        suggestions.append("**Relevant Agents:**")
        for agent in matching_agents:
            suggestions.append(f"  • `{agent['name']}` - {agent['reason']}")
        suggestions.append("  • See `.claude/docs/AGENTS.md` for details")
        suggestions.append("")

    if gemini_match:
        suggestions.append(f"**Gemini Delegation:** {gemini_match} task detected")
        suggestions.append("  • See `.claude/docs/GEMINI_WORKFLOW.md` for delegation matrix")
        suggestions.append("")

    suggestions.append("**To proceed:**")
    suggestions.append("Add a comment explaining why you're implementing directly, e.g.:")
    suggestions.append("  \"Checked AGENTS.md - implementing directly because [reason]\"")
    suggestions.append("")
    suggestions.append("Then retry the operation.")

    reason = "\n".join(suggestions)
    log_delegation_check(session_id, tool_name, file_path, "block", "Delegation not acknowledged")
    block(reason)


if __name__ == "__main__":
    main()
