# Checked AGENTS.md - implementing directly because:
# Tests are locked by the harness AC (AC-4 through AC-7). Every test maps
# 1:1 to a specific criterion — no open-ended coverage decisions to delegate.
"""Tests for transcript compacting (transcript_utils.compact_transcript)."""

import pytest

from src.diagnostic.engine_agent import COMPACT_WINDOW_SIZE
from src.diagnostic.transcript_utils import compact_transcript


def _make_messages(n: int) -> list[dict]:
    """Helper: produce n user/assistant message pairs (2n messages total)."""
    msgs = []
    for i in range(n):
        msgs.append({"role": "user", "content": f"turn {i + 1} user"})
        msgs.append({"role": "assistant", "content": f"turn {i + 1} assistant"})
    return msgs


# ── AC-7: Edge case — fewer turns than window size ────────────────────────────

def test_short_session_returns_all_messages_unchanged() -> None:
    messages = _make_messages(2)  # 4 messages < window_size 6
    result = compact_transcript(messages, window_size=6)
    assert result == messages


def test_exactly_window_size_messages_no_summary_added() -> None:
    messages = _make_messages(2)  # 4 messages == window_size 4
    result = compact_transcript(messages, window_size=4)
    assert len(result) == len(messages)
    assert result[0]["role"] != "system"  # no summary prefix


# ── AC-4: Compacting produces correct window ──────────────────────────────────

def test_compacting_8_turn_history_yields_summary_plus_4() -> None:
    messages = _make_messages(4)  # 8 messages
    result = compact_transcript(messages, window_size=4)
    assert len(result) == 5  # 1 summary + 4 kept
    assert result[0]["role"] == "system"


def test_compacted_result_keeps_most_recent_messages() -> None:
    messages = _make_messages(4)  # 8 messages, indices 0-7
    result = compact_transcript(messages, window_size=4)
    kept = result[1:]
    assert kept == messages[-4:]


def test_original_messages_not_mutated() -> None:
    messages = _make_messages(4)
    original_len = len(messages)
    compact_transcript(messages, window_size=4)
    assert len(messages) == original_len


# ── AC-5: Summary message content ─────────────────────────────────────────────

def test_summary_contains_compacted_count() -> None:
    messages = _make_messages(4)  # 8 msgs, window=4 → 4 compacted
    result = compact_transcript(messages, window_size=4, current_phase="HYPOTHESIS_TESTING")
    summary = result[0]["content"]
    assert "4" in summary  # 4 turns compacted


def test_summary_contains_eliminated_hypotheses() -> None:
    messages = _make_messages(4)
    result = compact_transcript(
        messages,
        eliminated_hypotheses=["P0300 misfire", "vacuum leak"],
        window_size=4,
    )
    summary = result[0]["content"]
    assert "P0300 misfire" in summary
    assert "vacuum leak" in summary


def test_summary_contains_current_phase() -> None:
    messages = _make_messages(4)
    result = compact_transcript(messages, current_phase="HYPOTHESIS_TESTING", window_size=4)
    assert "HYPOTHESIS_TESTING" in result[0]["content"]


def test_summary_message_role_is_system() -> None:
    messages = _make_messages(4)
    result = compact_transcript(messages, window_size=4)
    assert result[0]["role"] == "system"


# ── AC-6: Full transcript preservation ────────────────────────────────────────

def test_compacting_does_not_destroy_original_list() -> None:
    """The caller's full_transcript reference must remain complete after compacting."""
    full = _make_messages(4)
    full_copy = list(full)
    compact_transcript(full, window_size=4)
    assert full == full_copy


# ── AC-7: no summary when at or below window size ─────────────────────────────

def test_no_summary_prefix_when_messages_equal_window() -> None:
    messages = [{"role": "user", "content": f"m{i}"} for i in range(COMPACT_WINDOW_SIZE)]
    result = compact_transcript(messages)
    assert result == messages
    assert not any(m["role"] == "system" for m in result)


def test_no_summary_prefix_when_messages_below_window() -> None:
    messages = [{"role": "user", "content": "only message"}]
    result = compact_transcript(messages)
    assert result == messages
