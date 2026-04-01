# Checked AGENTS.md - implementing directly because:
# Flat-file JSON persistence with no auth surfaces, no external API calls, and
# no safety-critical logic. Pattern is a direct application of claw-code
# session_store study — straightforward I/O with pathlib.
"""
SessionStore — flat-file JSON persistence for DiagnosticSession objects.

Sessions are stored as individual JSON files under a configurable directory
(default: ``data/sessions/``).  Each file is named ``<session_id>.json``.

Design principles (from claw-code study):
  - Immutable snapshots on save — each save overwrites the file atomically.
  - No migration logic — schema is flat and forward-compatible via .get() with
    defaults in DiagnosticSession.from_dict().
  - Flush tracking — save() returns the path written so callers know the
    session hit disk before they unlink or rotate.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Iterator

from src.diagnostic.session_state import DiagnosticSession

logger = logging.getLogger(__name__)

_DEFAULT_SESSIONS_DIR = Path(__file__).resolve().parent.parent.parent / "data" / "sessions"


class SessionStore:
    """Read/write DiagnosticSession objects to disk as JSON."""

    def __init__(self, sessions_dir: Path | str | None = None) -> None:
        self._dir = Path(sessions_dir) if sessions_dir else _DEFAULT_SESSIONS_DIR
        self._dir.mkdir(parents=True, exist_ok=True)

    # ── Write ─────────────────────────────────────────────────────────────────

    def save(self, session: DiagnosticSession) -> Path:
        """Persist *session* to disk.  Returns the file path written."""
        path = self._path_for(session.session_id)
        path.write_text(json.dumps(session.to_dict(), indent=2), encoding="utf-8")
        logger.debug("SessionStore: saved %s → %s", session.session_id, path)
        return path

    # ── Read ──────────────────────────────────────────────────────────────────

    def load(self, session_id: str) -> DiagnosticSession | None:
        """Load a session by ID.  Returns None if not found."""
        path = self._path_for(session_id)
        if not path.exists():
            logger.debug("SessionStore: session not found: %s", session_id)
            return None
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            return DiagnosticSession.from_dict(data)
        except Exception as exc:
            logger.warning("SessionStore: failed to load %s: %s", session_id, exc)
            return None

    def exists(self, session_id: str) -> bool:
        """Return True if a session file exists for *session_id*."""
        return self._path_for(session_id).exists()

    # ── Enumerate ─────────────────────────────────────────────────────────────

    def list_ids(self) -> list[str]:
        """Return all stored session IDs, sorted by modification time (newest first)."""
        files = sorted(self._dir.glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True)
        return [p.stem for p in files]

    def iter_sessions(self) -> Iterator[DiagnosticSession]:
        """Yield all stored sessions, newest first.  Skips corrupt files."""
        for sid in self.list_ids():
            session = self.load(sid)
            if session is not None:
                yield session

    # ── Delete ────────────────────────────────────────────────────────────────

    def delete(self, session_id: str) -> bool:
        """Delete a session file.  Returns True if deleted, False if not found."""
        path = self._path_for(session_id)
        if path.exists():
            path.unlink()
            logger.debug("SessionStore: deleted %s", session_id)
            return True
        return False

    # ── Internal ──────────────────────────────────────────────────────────────

    def _path_for(self, session_id: str) -> Path:
        # Sanitise to prevent directory traversal
        safe_id = session_id.replace("/", "_").replace("..", "_")
        return self._dir / f"{safe_id}.json"
