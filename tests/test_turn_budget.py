"""Tests for session turn budgeting (engine_agent.check_turn_budget)."""

import pytest

from src.diagnostic.engine_agent import (
    MAX_HYPOTHESIS_TURNS,
    check_turn_budget,
)


# ── Constants ─────────────────────────────────────────────────────────────────

def test_max_hypothesis_turns_is_six() -> None:
    assert MAX_HYPOTHESIS_TURNS == 6


# ── Turn counter increments in hypothesis phases ──────────────────────────────

def test_budget_not_exceeded_in_hypothesis_generation_below_limit() -> None:
    result = check_turn_budget(turn_count=3, phase="HYPOTHESIS_GENERATION")
    assert result["budget_exceeded"] is False
    assert result["escalate_reason"] is None
    assert result["turns_remaining"] == 3


def test_budget_not_exceeded_in_hypothesis_testing_below_limit() -> None:
    result = check_turn_budget(turn_count=5, phase="HYPOTHESIS_TESTING")
    assert result["budget_exceeded"] is False
    assert result["turns_remaining"] == 1


def test_budget_exceeded_at_exactly_max_turns_hypothesis_generation() -> None:
    result = check_turn_budget(turn_count=MAX_HYPOTHESIS_TURNS, phase="HYPOTHESIS_GENERATION")
    assert result["budget_exceeded"] is True
    assert result["escalate_reason"] == "turn_budget_exceeded"
    assert result["turns_remaining"] == 0


def test_budget_exceeded_beyond_max_turns() -> None:
    result = check_turn_budget(turn_count=MAX_HYPOTHESIS_TURNS + 2, phase="HYPOTHESIS_TESTING")
    assert result["budget_exceeded"] is True
    assert result["turns_remaining"] == 0


# ── Turn counter does NOT increment in non-hypothesis phases ──────────────────

def test_symptom_collection_never_exceeds_budget() -> None:
    # Even with a high turn count, non-hypothesis phases never trigger escalation
    result = check_turn_budget(turn_count=100, phase="SYMPTOM_COLLECTION")
    assert result["budget_exceeded"] is False
    assert result["escalate_reason"] is None


def test_resolution_phase_never_exceeds_budget() -> None:
    result = check_turn_budget(turn_count=MAX_HYPOTHESIS_TURNS, phase="RESOLUTION")
    assert result["budget_exceeded"] is False


def test_escalation_phase_never_exceeds_budget() -> None:
    result = check_turn_budget(turn_count=MAX_HYPOTHESIS_TURNS, phase="ESCALATION")
    assert result["budget_exceeded"] is False


# ── Phase string normalisation ────────────────────────────────────────────────

def test_phase_matching_is_case_insensitive() -> None:
    result_upper = check_turn_budget(turn_count=MAX_HYPOTHESIS_TURNS, phase="HYPOTHESIS_GENERATION")
    result_lower = check_turn_budget(turn_count=MAX_HYPOTHESIS_TURNS, phase="hypothesis_generation")
    assert result_upper["budget_exceeded"] == result_lower["budget_exceeded"]


# ── Return structure completeness ─────────────────────────────────────────────

def test_return_dict_has_required_keys() -> None:
    result = check_turn_budget(turn_count=0, phase="HYPOTHESIS_GENERATION")
    assert "budget_exceeded" in result
    assert "escalate_reason" in result
    assert "turns_remaining" in result
