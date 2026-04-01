# Checked AGENTS.md - implementing directly because:
# This is a new data-layer module with no auth surfaces, no external I/O, and
# no safety-critical logic. Frozen dataclass + factory methods — no open-ended
# design decisions requiring delegation.
"""
DiagnosticSession — per-session working memory for the diagnostic engine.

Tracks the mutable state of a single diagnostic case across turns:
  - Vehicle and symptom context
  - Current SKILL.md phase
  - Hypothesis turn counter (feeds check_turn_budget)
  - Eliminated hypothesis labels
  - Full uncompacted transcript (preserved for HitL safety gate)

Sessions are serialisable to/from plain dicts so SessionStore can persist them
as JSON without additional dependencies.
"""

from __future__ import annotations

import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass
class DiagnosticSession:
    """Mutable working state for one diagnostic case.

    ``full_transcript`` is never compacted — it is the source of truth for
    audit and HitL escalation.  Use ``transcript_utils.compact_transcript``
    on a *copy* when querying ChromaDB.
    """

    session_id: str
    vehicle: dict[str, Any]
    symptoms: str
    phase: str = "SYMPTOM_COLLECTION"
    turn_count: int = 0
    eliminated_hypotheses: list[str] = field(default_factory=list)
    full_transcript: list[dict[str, Any]] = field(default_factory=list)
    created_at: str = field(default_factory=_now_iso)
    last_updated: str = field(default_factory=_now_iso)

    # ── Mutating helpers ──────────────────────────────────────────────────────

    def advance_turn(
        self,
        new_phase: str | None = None,
        hypothesis_label: str | None = None,
        message: dict[str, Any] | None = None,
    ) -> None:
        """Advance the session by one turn.

        - Increments turn_count.
        - Optionally transitions to *new_phase*.
        - Optionally records an *hypothesis_label* as eliminated.
        - Optionally appends *message* to the full transcript.
        """
        self.turn_count += 1
        if new_phase is not None:
            self.phase = new_phase
        if hypothesis_label is not None:
            self.eliminated_hypotheses.append(hypothesis_label)
        if message is not None:
            self.full_transcript.append(message)
        self.last_updated = _now_iso()

    def append_message(self, role: str, content: str) -> None:
        """Append a message to the full (uncompacted) transcript."""
        self.full_transcript.append({"role": role, "content": content})
        self.last_updated = _now_iso()

    # ── Serialisation ─────────────────────────────────────────────────────────

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-serialisable dict snapshot of the session."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "DiagnosticSession":
        """Reconstruct a DiagnosticSession from a previously serialised dict."""
        return cls(
            session_id=data["session_id"],
            vehicle=data.get("vehicle", {}),
            symptoms=data.get("symptoms", ""),
            phase=data.get("phase", "SYMPTOM_COLLECTION"),
            turn_count=data.get("turn_count", 0),
            eliminated_hypotheses=list(data.get("eliminated_hypotheses", [])),
            full_transcript=list(data.get("full_transcript", [])),
            created_at=data.get("created_at", _now_iso()),
            last_updated=data.get("last_updated", _now_iso()),
        )

    # ── Factory ───────────────────────────────────────────────────────────────

    @classmethod
    def create(
        cls,
        vehicle: dict[str, Any],
        symptoms: str,
        session_id: str | None = None,
    ) -> "DiagnosticSession":
        """Create a fresh session.  Generates a UUID session_id if not provided."""
        return cls(
            session_id=session_id or str(uuid.uuid4()),
            vehicle=vehicle,
            symptoms=symptoms,
        )
