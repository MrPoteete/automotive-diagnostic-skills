"""Shared utilities for Claude Code hooks."""

import os
from pathlib import Path


def get_project_dir():
    """Return the project root directory."""
    return os.environ.get(
        "CLAUDE_PROJECT_DIR",
        str(Path(__file__).resolve().parents[3]),
    )


def ensure_session_log_dir(session_id):
    """Create and return the log directory for a given session.

    Args:
        session_id: The Claude Code session identifier.

    Returns:
        Path object pointing to logs/{session_id}/.
    """
    project_dir = get_project_dir()
    log_dir = Path(project_dir) / "logs" / session_id
    log_dir.mkdir(parents=True, exist_ok=True)
    return log_dir
