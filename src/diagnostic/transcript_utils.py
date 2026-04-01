# Checked AGENTS.md - implementing directly because:
# This is a pure utility module with no auth surfaces, no DB access, and no
# external I/O. All logic is deterministic list manipulation with no security
# implications. Harness AC-4 through AC-7 specify exact behaviour.
"""
Transcript compacting utilities for diagnostic session context management.

Before each ChromaDB RAG query the session message history is trimmed to a
synthetic summary prefix + the last COMPACT_WINDOW_SIZE turns so that old
eliminated hypotheses do not pollute the retrieval context.

The *full* uncompacted transcript is always preserved on the caller side and
must be passed to the HitL safety gate during escalation (never the compacted
view).
"""

from __future__ import annotations

from typing import Any

from src.diagnostic.engine_agent import COMPACT_WINDOW_SIZE


def compact_transcript(
    messages: list[dict[str, Any]],
    eliminated_hypotheses: list[str] | None = None,
    current_phase: str = "UNKNOWN",
    window_size: int = COMPACT_WINDOW_SIZE,
) -> list[dict[str, Any]]:
    """Return a compacted view of *messages* for RAG context.

    If ``len(messages) <= window_size`` the input is returned unchanged (no
    summary prefix is prepended — AC-7 edge case).

    Otherwise returns::

        [synthetic_summary_message, *messages[-window_size:]]

    The synthetic summary message has ``role="system"`` and its ``content``
    includes:

    * Number of compacted (dropped) turns.
    * List of eliminated hypothesis labels (if provided).
    * Current session phase.

    Args:
        messages: Full message list from the current session.
        eliminated_hypotheses: Optional list of hypothesis labels already ruled
            out.  Included in the summary for context.
        current_phase: Current SKILL.md phase name (e.g. ``"HYPOTHESIS_TESTING"``).
        window_size: How many recent messages to keep.  Defaults to the module
            constant ``COMPACT_WINDOW_SIZE``.

    Returns:
        Compacted message list ready to pass to ChromaDB / RAG pipeline.
        The original *messages* list is never mutated.
    """
    if len(messages) <= window_size:
        return list(messages)

    n_compacted = len(messages) - window_size
    hyp_text = (
        ", ".join(eliminated_hypotheses)
        if eliminated_hypotheses
        else "none recorded"
    )
    summary_content = (
        f"[COMPACTED: {n_compacted} earlier turn(s) removed] "
        f"Eliminated hypotheses: {hyp_text}. "
        f"Current phase: {current_phase}."
    )
    summary_message: dict[str, Any] = {"role": "system", "content": summary_content}
    return [summary_message, *messages[-window_size:]]
