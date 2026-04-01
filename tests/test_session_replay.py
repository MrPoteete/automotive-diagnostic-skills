# Checked AGENTS.md - implementing directly because:
# Tests are mocked at the diagnose() boundary — no DB, no network. Pure logic
# validation with no open-ended coverage decisions.
"""Tests for session_replay — replay_session() and batch_replay()."""

import json
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from src.diagnostic.session_state import DiagnosticSession
from src.diagnostic.session_store import SessionStore
from src.diagnostic.session_replay import (
    BatchReplayReport,
    ReplayResult,
    _candidates_diverged,
    _extract_top_candidate_from_transcript,
    batch_replay,
    replay_session,
)


# ── Helpers ───────────────────────────────────────────────────────────────────

def _save_session(tmp_path: Path, vehicle: dict, symptoms: str, transcript=None) -> DiagnosticSession:
    store = SessionStore(sessions_dir=tmp_path / "sessions")
    s = DiagnosticSession.create(vehicle, symptoms)
    if transcript:
        s.full_transcript = transcript
    store.save(s)
    return s


MOCK_DIAGNOSE_RESULT = {
    "candidates": [{"component": "ENGINE COOLING", "confidence": 0.75}],
    "warnings": [],
    "data_sources": {},
}


# ── replay_session ────────────────────────────────────────────────────────────

class TestReplaySession:

    def test_returns_error_for_missing_session(self, tmp_path: Path) -> None:
        result = replay_session("ghost-id", sessions_dir=str(tmp_path / "sessions"))
        assert result.error is not None
        assert "not found" in result.error.lower()

    def test_stable_result_when_top_candidate_unchanged(self, tmp_path: Path) -> None:
        transcript = [{"role": "assistant", "content": "[{'component': 'ENGINE COOLING', 'confidence': 0.8}]"}]
        s = _save_session(tmp_path, {"make": "FORD", "year": 2015}, "overheating", transcript)
        with patch("src.diagnostic.session_replay.diagnose", return_value=MOCK_DIAGNOSE_RESULT):
            result = replay_session(s.session_id, sessions_dir=str(tmp_path / "sessions"))
        assert result.diverged is False
        assert result.error is None
        assert result.replay_top_candidate == "ENGINE COOLING"

    def test_diverged_when_top_candidate_changes(self, tmp_path: Path) -> None:
        transcript = [{"role": "assistant", "content": "[{'component': 'FUEL SYSTEM', 'confidence': 0.8}]"}]
        s = _save_session(tmp_path, {"make": "GM"}, "no start", transcript)
        with patch("src.diagnostic.session_replay.diagnose", return_value=MOCK_DIAGNOSE_RESULT):
            result = replay_session(s.session_id, sessions_dir=str(tmp_path / "sessions"))
        assert result.diverged is True  # FUEL SYSTEM vs ENGINE COOLING

    def test_error_field_set_when_diagnose_raises(self, tmp_path: Path) -> None:
        s = _save_session(tmp_path, {"make": "TOYOTA"}, "stall")
        with patch("src.diagnostic.session_replay.diagnose", side_effect=RuntimeError("DB offline")):
            result = replay_session(s.session_id, sessions_dir=str(tmp_path / "sessions"))
        assert result.error is not None
        assert "DB offline" in result.error

    def test_result_contains_vehicle_and_symptoms(self, tmp_path: Path) -> None:
        vehicle = {"make": "HONDA", "year": 2020, "model": "CIVIC"}
        s = _save_session(tmp_path, vehicle, "rough idle")
        with patch("src.diagnostic.session_replay.diagnose", return_value=MOCK_DIAGNOSE_RESULT):
            result = replay_session(s.session_id, sessions_dir=str(tmp_path / "sessions"))
        assert result.vehicle == vehicle
        assert result.symptoms == "rough idle"

    def test_summary_includes_status(self, tmp_path: Path) -> None:
        s = _save_session(tmp_path, {}, "")
        with patch("src.diagnostic.session_replay.diagnose", return_value=MOCK_DIAGNOSE_RESULT):
            result = replay_session(s.session_id, sessions_dir=str(tmp_path / "sessions"))
        summary = result.summary()
        assert "STABLE" in summary or "DIVERGED" in summary or "ERROR" in summary


# ── batch_replay ──────────────────────────────────────────────────────────────

class TestBatchReplay:

    def test_empty_store_returns_zero_total(self, tmp_path: Path) -> None:
        report = batch_replay(sessions_dir=str(tmp_path / "sessions"))
        assert report.total == 0
        assert report.pass_rate == 1.0

    def test_counts_stable_correctly(self, tmp_path: Path) -> None:
        for i in range(3):
            _save_session(tmp_path, {"make": "FORD"}, f"symptom {i}")
        with patch("src.diagnostic.session_replay.diagnose", return_value=MOCK_DIAGNOSE_RESULT):
            report = batch_replay(sessions_dir=str(tmp_path / "sessions"))
        assert report.total == 3
        assert report.errors == 0

    def test_limit_respected(self, tmp_path: Path) -> None:
        for i in range(10):
            _save_session(tmp_path, {}, f"s{i}")
        with patch("src.diagnostic.session_replay.diagnose", return_value=MOCK_DIAGNOSE_RESULT):
            report = batch_replay(limit=4, sessions_dir=str(tmp_path / "sessions"))
        assert report.total == 4

    def test_report_summary_shows_pass_rate(self, tmp_path: Path) -> None:
        for i in range(5):
            _save_session(tmp_path, {}, f"s{i}")
        with patch("src.diagnostic.session_replay.diagnose", return_value=MOCK_DIAGNOSE_RESULT):
            report = batch_replay(sessions_dir=str(tmp_path / "sessions"))
        summary = report.summary()
        assert "%" in summary


# ── Internal helpers ──────────────────────────────────────────────────────────

class TestInternalHelpers:

    def test_extract_top_candidate_from_transcript(self) -> None:
        transcript = [
            {"role": "user", "content": "engine shudder"},
            {"role": "assistant", "content": "[{'component': 'POWER TRAIN', 'confidence': 0.7}]"},
        ]
        assert _extract_top_candidate_from_transcript(transcript) == "POWER TRAIN"

    def test_extract_returns_none_for_empty_transcript(self) -> None:
        assert _extract_top_candidate_from_transcript([]) is None

    def test_extract_returns_none_when_no_candidate_in_content(self) -> None:
        transcript = [{"role": "assistant", "content": "No idea what's wrong."}]
        assert _extract_top_candidate_from_transcript(transcript) is None

    def test_candidates_diverged_false_when_same(self) -> None:
        assert _candidates_diverged("ENGINE COOLING", "ENGINE COOLING") is False

    def test_candidates_diverged_true_when_different(self) -> None:
        assert _candidates_diverged("FUEL SYSTEM", "ENGINE COOLING") is True

    def test_candidates_diverged_case_insensitive(self) -> None:
        assert _candidates_diverged("engine cooling", "ENGINE COOLING") is False

    def test_candidates_diverged_false_when_both_none(self) -> None:
        assert _candidates_diverged(None, None) is False

    def test_candidates_diverged_false_when_one_none(self) -> None:
        # Can't determine divergence without both sides
        assert _candidates_diverged("FUEL SYSTEM", None) is False
        assert _candidates_diverged(None, "ENGINE COOLING") is False
