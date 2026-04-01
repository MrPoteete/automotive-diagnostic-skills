# Checked AGENTS.md - implementing directly because:
# Pure data-layer tests with no auth surfaces. All behaviour is deterministic
# and fully specified by the DiagnosticSession/SessionStore contracts.
"""Tests for DiagnosticSession and SessionStore."""

import json
import tempfile
from pathlib import Path

import pytest

from src.diagnostic.session_state import DiagnosticSession
from src.diagnostic.session_store import SessionStore


# ── DiagnosticSession ─────────────────────────────────────────────────────────

class TestDiagnosticSession:

    def test_create_generates_session_id(self) -> None:
        s = DiagnosticSession.create({"make": "FORD"}, "rough idle")
        assert s.session_id
        assert len(s.session_id) > 8

    def test_create_accepts_explicit_session_id(self) -> None:
        s = DiagnosticSession.create({}, "", session_id="abc-123")
        assert s.session_id == "abc-123"

    def test_default_phase_is_symptom_collection(self) -> None:
        s = DiagnosticSession.create({}, "")
        assert s.phase == "SYMPTOM_COLLECTION"

    def test_default_turn_count_is_zero(self) -> None:
        s = DiagnosticSession.create({}, "")
        assert s.turn_count == 0

    def test_advance_turn_increments_counter(self) -> None:
        s = DiagnosticSession.create({}, "")
        s.advance_turn()
        assert s.turn_count == 1
        s.advance_turn()
        assert s.turn_count == 2

    def test_advance_turn_transitions_phase(self) -> None:
        s = DiagnosticSession.create({}, "")
        s.advance_turn(new_phase="HYPOTHESIS_GENERATION")
        assert s.phase == "HYPOTHESIS_GENERATION"

    def test_advance_turn_records_hypothesis_label(self) -> None:
        s = DiagnosticSession.create({}, "")
        s.advance_turn(hypothesis_label="P0300 misfire")
        assert "P0300 misfire" in s.eliminated_hypotheses

    def test_advance_turn_appends_message_to_full_transcript(self) -> None:
        s = DiagnosticSession.create({}, "")
        msg = {"role": "assistant", "content": "test"}
        s.advance_turn(message=msg)
        assert msg in s.full_transcript

    def test_append_message_adds_to_transcript(self) -> None:
        s = DiagnosticSession.create({}, "")
        s.append_message("user", "what's wrong?")
        assert s.full_transcript[-1] == {"role": "user", "content": "what's wrong?"}

    def test_full_transcript_not_compacted(self) -> None:
        """full_transcript must preserve all messages even after multiple turns."""
        s = DiagnosticSession.create({}, "")
        for i in range(10):
            s.append_message("user", f"message {i}")
        assert len(s.full_transcript) == 10

    def test_roundtrip_serialisation(self) -> None:
        s = DiagnosticSession.create({"make": "TOYOTA", "year": 2019}, "stall")
        s.advance_turn(new_phase="HYPOTHESIS_GENERATION", hypothesis_label="fuel pump")
        s.append_message("user", "stalls at idle")
        restored = DiagnosticSession.from_dict(s.to_dict())
        assert restored.session_id == s.session_id
        assert restored.phase == s.phase
        assert restored.turn_count == s.turn_count
        assert restored.eliminated_hypotheses == s.eliminated_hypotheses
        assert restored.full_transcript == s.full_transcript


# ── SessionStore ──────────────────────────────────────────────────────────────

class TestSessionStore:

    def _store(self, tmp_path: Path) -> SessionStore:
        return SessionStore(sessions_dir=tmp_path / "sessions")

    def test_save_creates_json_file(self, tmp_path: Path) -> None:
        store = self._store(tmp_path)
        s = DiagnosticSession.create({"make": "GM"}, "no start")
        path = store.save(s)
        assert path.exists()
        assert path.suffix == ".json"

    def test_load_returns_none_for_missing_session(self, tmp_path: Path) -> None:
        store = self._store(tmp_path)
        assert store.load("nonexistent") is None

    def test_save_and_load_roundtrip(self, tmp_path: Path) -> None:
        store = self._store(tmp_path)
        s = DiagnosticSession.create({"make": "HONDA"}, "check engine")
        s.advance_turn(new_phase="HYPOTHESIS_TESTING")
        store.save(s)
        loaded = store.load(s.session_id)
        assert loaded is not None
        assert loaded.session_id == s.session_id
        assert loaded.phase == "HYPOTHESIS_TESTING"
        assert loaded.turn_count == 1

    def test_exists_returns_true_after_save(self, tmp_path: Path) -> None:
        store = self._store(tmp_path)
        s = DiagnosticSession.create({}, "")
        store.save(s)
        assert store.exists(s.session_id)

    def test_exists_returns_false_for_unsaved(self, tmp_path: Path) -> None:
        store = self._store(tmp_path)
        assert not store.exists("not-saved")

    def test_list_ids_returns_saved_ids(self, tmp_path: Path) -> None:
        store = self._store(tmp_path)
        ids = [DiagnosticSession.create({}, "").session_id for _ in range(3)]
        for sid in ids:
            store.save(DiagnosticSession.create({}, "", session_id=sid))
        listed = store.list_ids()
        for sid in ids:
            assert sid in listed

    def test_delete_removes_file(self, tmp_path: Path) -> None:
        store = self._store(tmp_path)
        s = DiagnosticSession.create({}, "")
        store.save(s)
        assert store.delete(s.session_id) is True
        assert not store.exists(s.session_id)

    def test_delete_returns_false_for_missing(self, tmp_path: Path) -> None:
        store = self._store(tmp_path)
        assert store.delete("ghost") is False

    def test_path_traversal_sanitised(self, tmp_path: Path) -> None:
        """Directory traversal in session_id must not escape the sessions dir."""
        store = self._store(tmp_path)
        s = DiagnosticSession.create({}, "", session_id="../../../etc/passwd")
        path = store.save(s)
        assert store._dir in path.parents or path.parent == store._dir

    def test_iter_sessions_yields_all(self, tmp_path: Path) -> None:
        store = self._store(tmp_path)
        for i in range(4):
            store.save(DiagnosticSession.create({}, f"symptom {i}"))
        sessions = list(store.iter_sessions())
        assert len(sessions) == 4
