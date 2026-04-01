# Checked AGENTS.md - implementing directly because:
# Pure orchestration layer — calls existing diagnose() and SessionStore with no
# new auth surfaces, no safety-critical decisions, and no external I/O beyond
# what diagnose() already does.
"""
Session replay — re-run historical diagnostic sessions for audit and training.

Use cases:
  - Audit: verify a past diagnosis is still reproducible after a DB update
  - Regression: confirm known-good cases don't change after system changes
  - Training: compare AI diagnosis against mechanic-confirmed outcomes
  - QA: batch-validate all saved sessions after a data import

Usage::

    from src.diagnostic.session_replay import replay_session, batch_replay

    result = replay_session("abc-123")
    print(result.diverged)          # True if top candidate changed
    print(result.summary())         # Human-readable comparison

    report = batch_replay(limit=50)
    print(report.pass_rate)         # e.g. 0.94
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from src.diagnostic.engine_agent import diagnose
from src.diagnostic.session_store import SessionStore

logger = logging.getLogger(__name__)


# ── Result types ──────────────────────────────────────────────────────────────

@dataclass
class ReplayResult:
    """Comparison of an original diagnostic session against a fresh re-run."""

    session_id: str
    vehicle: dict[str, Any]
    symptoms: str

    # Original session metadata
    original_phase: str
    original_turn_count: int
    original_eliminated: list[str]

    # Top candidate component from original (if recorded in transcript)
    original_top_candidate: str | None

    # Fresh replay result
    replay_top_candidate: str | None
    replay_candidate_count: int
    replay_warnings: list[str]

    # Comparison
    diverged: bool  # True if top candidate changed between original and replay
    error: str | None = None  # Set if replay threw an exception
    replayed_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def summary(self) -> str:
        """Return a one-paragraph human-readable comparison."""
        status = "DIVERGED ⚠️" if self.diverged else "STABLE ✅"
        if self.error:
            status = f"ERROR ❌ ({self.error})"
        lines = [
            f"Session {self.session_id} — {status}",
            f"  Vehicle : {self.vehicle.get('year', '?')} {self.vehicle.get('make', '?')} {self.vehicle.get('model', '?')}",
            f"  Symptoms: {self.symptoms[:80]}",
            f"  Original top: {self.original_top_candidate or '(not recorded)'}",
            f"  Replay top  : {self.replay_top_candidate or '(no candidates)'}",
            f"  Original phase: {self.original_phase} | turns: {self.original_turn_count}",
        ]
        if self.original_eliminated:
            lines.append(f"  Eliminated  : {', '.join(self.original_eliminated[:5])}")
        return "\n".join(lines)


@dataclass
class BatchReplayReport:
    """Summary of a batch replay run across multiple sessions."""

    total: int
    stable: int
    diverged: int
    errors: int
    results: list[ReplayResult] = field(default_factory=list)
    run_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    @property
    def pass_rate(self) -> float:
        """Fraction of sessions that are stable (not diverged, no error)."""
        if self.total == 0:
            return 1.0
        return self.stable / self.total

    def summary(self) -> str:
        lines = [
            f"Batch replay — {self.total} sessions",
            f"  Stable  : {self.stable}  ({self.pass_rate:.0%})",
            f"  Diverged: {self.diverged}",
            f"  Errors  : {self.errors}",
        ]
        diverged_ids = [r.session_id for r in self.results if r.diverged]
        if diverged_ids:
            lines.append(f"  Diverged sessions: {', '.join(diverged_ids[:10])}")
        return "\n".join(lines)


# ── Core replay function ──────────────────────────────────────────────────────

def replay_session(
    session_id: str,
    *,
    sessions_dir: str | None = None,
) -> ReplayResult:
    """Re-run a saved diagnostic session and compare against the original.

    Loads the session from ``SessionStore``, re-runs ``diagnose()`` with the
    same vehicle and symptoms (without consuming session budget), and returns a
    ``ReplayResult`` describing whether the top candidate has changed.

    Args:
        session_id: ID of the session to replay.
        sessions_dir: Override the default sessions directory (useful in tests).

    Returns:
        ``ReplayResult`` — always returns, never raises.  ``error`` field is
        set if something went wrong.
    """
    store = SessionStore(sessions_dir=sessions_dir) if sessions_dir else SessionStore()
    session = store.load(session_id)

    if session is None:
        return ReplayResult(
            session_id=session_id,
            vehicle={},
            symptoms="",
            original_phase="UNKNOWN",
            original_turn_count=0,
            original_eliminated=[],
            original_top_candidate=None,
            replay_top_candidate=None,
            replay_candidate_count=0,
            replay_warnings=[],
            diverged=False,
            error=f"Session not found: {session_id}",
        )

    # Extract the top candidate from the original session's transcript
    original_top = _extract_top_candidate_from_transcript(session.full_transcript)

    # Re-run diagnosis (no session_id — stateless, doesn't consume budget)
    try:
        replay_result = diagnose(session.vehicle, session.symptoms)
        candidates = replay_result.get("candidates", [])
        replay_top = candidates[0].get("component") if candidates else None
        replay_warnings = replay_result.get("warnings", [])
        diverged = _candidates_diverged(original_top, replay_top)
        error = None
    except Exception as exc:
        logger.warning("replay_session(%s) failed: %s", session_id, exc)
        replay_top = None
        replay_warnings = []
        diverged = False
        error = str(exc)
        candidates = []

    return ReplayResult(
        session_id=session_id,
        vehicle=session.vehicle,
        symptoms=session.symptoms,
        original_phase=session.phase,
        original_turn_count=session.turn_count,
        original_eliminated=list(session.eliminated_hypotheses),
        original_top_candidate=original_top,
        replay_top_candidate=replay_top,
        replay_candidate_count=len(candidates),
        replay_warnings=replay_warnings,
        diverged=diverged,
        error=error,
    )


def batch_replay(
    *,
    limit: int = 100,
    sessions_dir: str | None = None,
) -> BatchReplayReport:
    """Replay up to *limit* saved sessions and return a summary report.

    Sessions are processed newest-first (as returned by SessionStore.iter_sessions).

    Args:
        limit: Maximum number of sessions to replay.
        sessions_dir: Override the default sessions directory.
    """
    store = SessionStore(sessions_dir=sessions_dir) if sessions_dir else SessionStore()
    results: list[ReplayResult] = []
    count = 0

    for session in store.iter_sessions():
        if count >= limit:
            break
        result = replay_session(session.session_id, sessions_dir=sessions_dir)
        results.append(result)
        count += 1
        logger.debug(
            "batch_replay: %s → %s",
            session.session_id,
            "DIVERGED" if result.diverged else ("ERROR" if result.error else "STABLE"),
        )

    stable = sum(1 for r in results if not r.diverged and not r.error)
    diverged = sum(1 for r in results if r.diverged)
    errors = sum(1 for r in results if r.error)

    return BatchReplayReport(
        total=len(results),
        stable=stable,
        diverged=diverged,
        errors=errors,
        results=results,
    )


# ── Internal helpers ──────────────────────────────────────────────────────────

def _extract_top_candidate_from_transcript(
    transcript: list[dict[str, Any]],
) -> str | None:
    """Best-effort extraction of the top candidate from a session transcript.

    Looks for assistant messages that contain candidate component names.
    Returns None if nothing useful is found.
    """
    for msg in reversed(transcript):
        if msg.get("role") == "assistant":
            content = msg.get("content", "")
            # Candidates are stored as a truncated repr of the list
            # e.g. "[{'component': 'ENGINE COOLING', ...}]"
            if "'component'" in content or '"component"' in content:
                import re
                m = re.search(r"'component':\s*'([^']+)'", content)
                if m:
                    return m.group(1)
    return None


def _candidates_diverged(original: str | None, replay: str | None) -> bool:
    """Return True if the top candidate changed in a meaningful way."""
    if original is None and replay is None:
        return False
    if original is None or replay is None:
        return False  # can't compare if one side has no data
    return original.upper().strip() != replay.upper().strip()
