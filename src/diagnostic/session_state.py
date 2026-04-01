# Checked AGENTS.md - implementing directly because:
# New data-layer module with no auth surfaces, no external I/O, and no
# safety-critical logic. Designed from first principles using DDIA log/WAL
# patterns and the Google agent-memory taxonomy (episodic/semantic/procedural).
"""
DiagnosticSession — per-case working memory for the diagnostic engine.

Design principles (Kleppmann, DDIA Chapters 3 & 11):
  - The full_log is the source of truth — append-only, never modified.
  - Frontmatter is the materialized view — current state, updated on each turn.
  - Reads derive from the log; writes append to it (WAL pattern).

Google agent-memory taxonomy applied:
  - Episodic   → full_log (what happened, in order)
  - Semantic   → frontmatter (what is true NOW: phase, vehicle, turns)
  - Procedural → SKILL.md (how to diagnose — lives outside session state)

File format: YAML frontmatter + JSONL body
  <session-dir>/<date>_<MAKE>_<MODEL>_<short-id>.session
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _short_id(session_id: str) -> str:
    """First 8 chars of session_id, safe for filenames."""
    return session_id[:8].replace("-", "")


def _safe_field(value: str) -> str:
    """Sanitise a string for use in a filename."""
    import re
    return re.sub(r"[^A-Z0-9]", "", str(value).upper())[:12]


@dataclass
class LogEntry:
    """One immutable entry in the session log."""
    type: str                          # "message" | "turn" | "hypothesis" | "note"
    ts: str = field(default_factory=_now_iso)
    # type="message"
    role: str | None = None
    content: str | None = None
    # type="turn"
    phase: str | None = None
    n: int | None = None
    # type="hypothesis"
    label: str | None = None
    status: str | None = None          # "active" | "eliminated" | "confirmed"
    # type="note"
    note: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {k: v for k, v in self.__dict__.items() if v is not None}


@dataclass
class DiagnosticSession:
    """Working memory for one diagnostic case.

    Attributes:
        session_id   : UUID string, unique per case.
        vehicle      : Dict with make/model/year/engine (str values).
        symptoms     : Free-text mechanic description.
        repair_order : Optional RO/ticket number from the shop system.
        phase        : Current SKILL.md phase name.
        turn_count   : Hypothesis turns consumed (budget counter).
        eliminated_hypotheses : Labels of ruled-out hypotheses (semantic summary).
        full_log     : Ordered log entries — the source of truth. Never modified.
        created_at   : ISO timestamp of session creation.
        last_updated : ISO timestamp of last write.
    """

    session_id: str
    vehicle: dict[str, Any]
    symptoms: str
    repair_order: str | None = None
    phase: str = "SYMPTOM_COLLECTION"
    turn_count: int = 0
    eliminated_hypotheses: list[str] = field(default_factory=list)
    full_log: list[dict[str, Any]] = field(default_factory=list)
    created_at: str = field(default_factory=_now_iso)
    last_updated: str = field(default_factory=_now_iso)

    # ── Computed properties ───────────────────────────────────────────────────

    @property
    def display_name(self) -> str:
        """Human-readable label: '2026-04-01 FORD F-350 (3 turns, HYPOTHESIS_TESTING)'."""
        date = self.created_at[:10]
        make  = self.vehicle.get("make",  "UNKNOWN").upper()
        model = self.vehicle.get("model", "UNKNOWN").upper()
        ro    = f" RO#{self.repair_order}" if self.repair_order else ""
        return f"{date} {make} {model}{ro} ({self.turn_count} turns, {self.phase})"

    @property
    def filename_stem(self) -> str:
        """Deterministic, filesystem-safe filename (no extension).
        Format: YYYYMMDD_MAKE_MODEL_<short-id>
        """
        date  = self.created_at[:10].replace("-", "")
        make  = _safe_field(self.vehicle.get("make",  ""))  or "UNKNOWN"
        model = _safe_field(self.vehicle.get("model", ""))  or "UNKNOWN"
        return f"{date}_{make}_{model}_{_short_id(self.session_id)}"

    # ── Mutation helpers (append-only to full_log) ────────────────────────────

    def append_message(self, role: str, content: str) -> None:
        """Append a user or assistant message to the log."""
        entry = LogEntry(type="message", role=role, content=content)
        self.full_log.append(entry.to_dict())
        self.last_updated = _now_iso()

    def advance_turn(
        self,
        new_phase: str | None = None,
        hypothesis_label: str | None = None,
        hypothesis_status: str = "active",
    ) -> None:
        """Increment turn counter; optionally transition phase and log a hypothesis."""
        self.turn_count += 1
        if new_phase is not None:
            self.phase = new_phase
        # Log the turn event
        entry = LogEntry(type="turn", phase=self.phase, n=self.turn_count)
        self.full_log.append(entry.to_dict())
        # Log hypothesis state change if provided
        if hypothesis_label is not None:
            hyp = LogEntry(
                type="hypothesis",
                label=hypothesis_label,
                status=hypothesis_status,
            )
            self.full_log.append(hyp.to_dict())
            if hypothesis_status == "eliminated":
                self.eliminated_hypotheses.append(hypothesis_label)
        self.last_updated = _now_iso()

    def add_note(self, note: str) -> None:
        """Append a free-text technician note to the log."""
        entry = LogEntry(type="note", note=note)
        self.full_log.append(entry.to_dict())
        self.last_updated = _now_iso()

    # ── Compact view for RAG context ─────────────────────────────────────────

    def compact_messages(self, keep_last: int = 4) -> list[dict[str, Any]]:
        """Return a compacted message-only view for ChromaDB queries.

        Keeps only the last *keep_last* message entries (role=user|assistant).
        Prepends a system summary if messages were dropped.
        Does NOT modify full_log.
        """
        messages = [e for e in self.full_log if e.get("type") == "message"]
        if len(messages) <= keep_last:
            return list(messages)
        n_dropped = len(messages) - keep_last
        hyp_text = (
            ", ".join(self.eliminated_hypotheses) if self.eliminated_hypotheses
            else "none recorded"
        )
        summary = {
            "type": "message",
            "role": "system",
            "content": (
                f"[COMPACTED: {n_dropped} earlier message(s) omitted] "
                f"Eliminated hypotheses: {hyp_text}. "
                f"Current phase: {self.phase}."
            ),
        }
        return [summary, *messages[-keep_last:]]

    # ── Factory ───────────────────────────────────────────────────────────────

    @classmethod
    def create(
        cls,
        vehicle: dict[str, Any],
        symptoms: str,
        repair_order: str | None = None,
        session_id: str | None = None,
    ) -> "DiagnosticSession":
        """Create a fresh session. Generates a UUID session_id if not provided."""
        return cls(
            session_id=session_id or str(uuid.uuid4()),
            vehicle=dict(vehicle),        # defensive copy
            symptoms=symptoms,
            repair_order=repair_order,
        )
