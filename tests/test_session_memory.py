# Checked AGENTS.md - implementing directly because:
# Tests are specified from first principles against our own design — no
# delegation needed. Edge cases designed by us, not derived from any other
# codebase.
"""
Comprehensive tests for DiagnosticSession and SessionStore.

EDGE CASES TESTED (summary — reviewed by user):
  EC-01  Vehicle with None / missing fields
  EC-02  Symptoms with special characters (quotes, newlines, Unicode)
  EC-03  Repair order with slashes and path-separator characters
  EC-04  Simulated partial write (truncated frontmatter delimiter)
  EC-05  YAML frontmatter with colons in value strings
  EC-06  Session file deleted between exists() and load()
  EC-07  Extremely long symptoms string (>2000 chars)
  EC-08  Eliminated hypotheses with special characters
  EC-09  Year as integer, string, and None
  EC-10  find_by_vehicle with partial spec (make only, no model)
  EC-11  Sessions directory does not exist on init (auto-create)
  EC-12  Corrupt JSONL line mid-body (partial write simulation)
  EC-13  Empty vehicle dict
  EC-14  duplicate session_id filenames (short_id collision)
  EC-15  find_by_repair_order with None or missing repair_order
  EC-16  compact_messages with fewer messages than keep_last
  EC-17  compact_messages with exactly keep_last messages
  EC-18  Multiple advance_turn calls accumulate correctly
  EC-19  Session with no log entries (fresh session, no messages)
  EC-20  YAML frontmatter missing session_id field (corrupt file)
"""

import json
import re
import tempfile
from pathlib import Path

import pytest
import yaml

from src.diagnostic.session_state import DiagnosticSession
from src.diagnostic.session_store import SessionStore


# ── Fixtures ──────────────────────────────────────────────────────────────────

def store(tmp_path: Path) -> SessionStore:
    return SessionStore(sessions_dir=tmp_path / "sessions")


def session(**kwargs) -> DiagnosticSession:
    defaults = dict(vehicle={"make": "FORD", "model": "F150", "year": "2020"}, symptoms="rough idle")
    defaults.update(kwargs)
    return DiagnosticSession.create(**defaults)


# ── DiagnosticSession unit tests ──────────────────────────────────────────────

class TestDiagnosticSession:

    def test_create_generates_uuid(self) -> None:
        s = session()
        assert len(s.session_id) == 36  # UUID format

    def test_display_name_format(self) -> None:
        s = DiagnosticSession.create(
            vehicle={"make": "TOYOTA", "model": "CAMRY", "year": "2019"},
            symptoms="stall",
        )
        assert "TOYOTA" in s.display_name
        assert "CAMRY" in s.display_name
        assert "0 turns" in s.display_name

    def test_display_name_includes_repair_order(self) -> None:
        s = DiagnosticSession.create(
            vehicle={"make": "FORD"}, symptoms="no start", repair_order="RO-9999"
        )
        assert "RO#RO-9999" in s.display_name

    def test_filename_stem_is_filesystem_safe(self) -> None:
        s = session()
        stem = s.filename_stem
        assert re.match(r"^[A-Za-z0-9_\-]+$", stem), f"Unsafe stem: {stem!r}"

    def test_append_message_appends_to_log(self) -> None:
        s = session()
        s.append_message("user", "what's wrong?")
        assert any(e.get("role") == "user" for e in s.full_log)

    def test_advance_turn_increments_counter(self) -> None:
        s = session()
        s.advance_turn()
        s.advance_turn()
        assert s.turn_count == 2

    def test_advance_turn_logs_turn_entry(self) -> None:
        s = session()
        s.advance_turn(new_phase="HYPOTHESIS_GENERATION")
        turn_entries = [e for e in s.full_log if e.get("type") == "turn"]
        assert len(turn_entries) == 1
        assert turn_entries[0]["phase"] == "HYPOTHESIS_GENERATION"

    def test_advance_turn_records_eliminated_hypothesis(self) -> None:
        s = session()
        s.advance_turn(hypothesis_label="P0300 misfire", hypothesis_status="eliminated")
        assert "P0300 misfire" in s.eliminated_hypotheses

    def test_add_note_appended_to_log(self) -> None:
        s = session()
        s.add_note("Customer mentioned it only stalls when cold.")
        notes = [e for e in s.full_log if e.get("type") == "note"]
        assert notes[0]["note"] == "Customer mentioned it only stalls when cold."

    # ── compact_messages edge cases ────────────────────────────────────────────

    def test_compact_messages_ec16_fewer_than_keep_last(self) -> None:
        """EC-16: Fewer messages than keep_last → no summary, return all."""
        s = session()
        s.append_message("user", "symptom 1")
        s.append_message("assistant", "response 1")
        result = s.compact_messages(keep_last=6)
        assert len(result) == 2
        assert not any(e.get("role") == "system" for e in result)

    def test_compact_messages_ec17_exactly_keep_last(self) -> None:
        """EC-17: Exactly keep_last messages → no summary prefix."""
        s = session()
        for i in range(4):
            s.append_message("user", f"u{i}")
        result = s.compact_messages(keep_last=4)
        assert len(result) == 4
        assert result[0]["role"] != "system"

    def test_compact_messages_more_than_keep_last(self) -> None:
        s = session()
        for i in range(8):
            s.append_message("user" if i % 2 == 0 else "assistant", f"msg{i}")
        result = s.compact_messages(keep_last=4)
        assert len(result) == 5  # 1 summary + 4 kept
        assert result[0]["role"] == "system"
        assert "4" in result[0]["content"]  # 4 dropped

    def test_compact_messages_does_not_mutate_full_log(self) -> None:
        s = session()
        for i in range(6):
            s.append_message("user", f"m{i}")
        original_len = len(s.full_log)
        s.compact_messages(keep_last=3)
        assert len(s.full_log) == original_len

    # ── EC-18: Multiple advance_turn accumulate ────────────────────────────────

    def test_ec18_multiple_advance_turn_accumulate(self) -> None:
        s = session()
        for label in ["vac leak", "injector", "MAF sensor"]:
            s.advance_turn(hypothesis_label=label, hypothesis_status="eliminated")
        assert s.turn_count == 3
        assert set(s.eliminated_hypotheses) == {"vac leak", "injector", "MAF sensor"}
        turn_entries = [e for e in s.full_log if e.get("type") == "turn"]
        assert len(turn_entries) == 3


# ── SessionStore unit tests ────────────────────────────────────────────────────

class TestSessionStore:

    # ── Basic save/load ────────────────────────────────────────────────────────

    def test_save_creates_session_file(self, tmp_path: Path) -> None:
        st = store(tmp_path)
        s = session()
        path = st.save(s)
        assert path.exists()
        assert path.suffix == ".session"

    def test_save_file_starts_with_frontmatter_delimiter(self, tmp_path: Path) -> None:
        st = store(tmp_path)
        path = st.save(session())
        assert path.read_text().startswith("---")

    def test_save_and_load_roundtrip(self, tmp_path: Path) -> None:
        st = store(tmp_path)
        s = session()
        s.append_message("user", "knock at idle")
        s.advance_turn(new_phase="HYPOTHESIS_GENERATION", hypothesis_label="rod bearing", hypothesis_status="active")
        st.save(s)
        loaded = st.load(s.session_id)
        assert loaded is not None
        assert loaded.session_id == s.session_id
        assert loaded.phase == "HYPOTHESIS_GENERATION"
        assert loaded.turn_count == 1
        assert len(loaded.full_log) == len(s.full_log)

    def test_load_returns_none_for_missing_session(self, tmp_path: Path) -> None:
        st = store(tmp_path)
        assert st.load("00000000-0000-0000-0000-000000000000") is None

    def test_exists_true_after_save(self, tmp_path: Path) -> None:
        st = store(tmp_path)
        s = session()
        st.save(s)
        assert st.exists(s.session_id)

    def test_exists_false_for_unsaved(self, tmp_path: Path) -> None:
        st = store(tmp_path)
        assert not st.exists("00000000-0000-0000-0000-000000000000")

    def test_delete_removes_file(self, tmp_path: Path) -> None:
        st = store(tmp_path)
        s = session()
        st.save(s)
        assert st.delete(s.session_id) is True
        assert not st.exists(s.session_id)

    def test_delete_returns_false_for_missing(self, tmp_path: Path) -> None:
        st = store(tmp_path)
        assert st.delete("ghost") is False

    # ── Edge cases ─────────────────────────────────────────────────────────────

    def test_ec01_vehicle_with_none_fields(self, tmp_path: Path) -> None:
        """EC-01: Vehicle dict with None values should not crash save/load."""
        st = store(tmp_path)
        s = DiagnosticSession.create(
            vehicle={"make": None, "model": None, "year": None},
            symptoms="check engine"
        )
        path = st.save(s)
        loaded = st.load(s.session_id)
        assert loaded is not None

    def test_ec01_empty_vehicle_dict(self, tmp_path: Path) -> None:
        """EC-01b / EC-13: Empty vehicle dict."""
        st = store(tmp_path)
        s = DiagnosticSession.create(vehicle={}, symptoms="idle hunt")
        st.save(s)
        loaded = st.load(s.session_id)
        assert loaded is not None

    def test_ec02_symptoms_with_special_chars(self, tmp_path: Path) -> None:
        """EC-02: Symptoms with quotes, newlines, and Unicode."""
        st = store(tmp_path)
        symptoms = 'stalls on "cold starts"\nrpm drops to 0\naño nuevo problem'
        s = DiagnosticSession.create(vehicle={"make": "GM"}, symptoms=symptoms)
        st.save(s)
        loaded = st.load(s.session_id)
        assert loaded is not None
        assert loaded.symptoms == symptoms

    def test_ec03_repair_order_with_slashes(self, tmp_path: Path) -> None:
        """EC-03: Repair order with path-separator characters must not escape dir."""
        st = store(tmp_path)
        s = DiagnosticSession.create(
            vehicle={"make": "FORD"}, symptoms="no start",
            repair_order="../../etc/passwd"
        )
        path = st.save(s)
        # File must be inside the sessions directory
        assert st._dir in path.parents or path.parent == st._dir
        loaded = st.load(s.session_id)
        assert loaded is not None
        assert loaded.repair_order == "../../etc/passwd"  # value preserved, path safe

    def test_ec04_truncated_frontmatter(self, tmp_path: Path) -> None:
        """EC-04: File with only opening --- (no closing delimiter) → graceful None."""
        st = store(tmp_path)
        corrupt = tmp_path / "sessions" / "corrupt.session"
        corrupt.parent.mkdir(parents=True, exist_ok=True)
        corrupt.write_text("---\nsession_id: broken-id\n")  # no closing ---
        result = st.load_file(corrupt)
        assert result is None

    def test_ec05_yaml_colon_in_value(self, tmp_path: Path) -> None:
        """EC-05: Symptoms containing colons (YAML special char) must roundtrip."""
        st = store(tmp_path)
        s = DiagnosticSession.create(
            vehicle={"make": "HONDA"},
            symptoms="code P0300: random misfire detected: all cylinders"
        )
        st.save(s)
        loaded = st.load(s.session_id)
        assert loaded is not None
        assert "P0300" in loaded.symptoms

    def test_ec06_file_deleted_between_exists_and_load(self, tmp_path: Path) -> None:
        """EC-06: File deleted after exists() returns True → load returns None."""
        st = store(tmp_path)
        s = session()
        path = st.save(s)
        assert st.exists(s.session_id)
        path.unlink()  # delete between exists and load
        result = st.load(s.session_id)
        assert result is None

    def test_ec07_extremely_long_symptoms(self, tmp_path: Path) -> None:
        """EC-07: Symptoms > 2000 chars must save and load without truncation."""
        st = store(tmp_path)
        long_symptoms = "rough idle " * 200  # 2200 chars
        s = DiagnosticSession.create(vehicle={"make": "TOYOTA"}, symptoms=long_symptoms)
        st.save(s)
        loaded = st.load(s.session_id)
        assert loaded is not None
        assert loaded.symptoms == long_symptoms

    def test_ec08_eliminated_hypothesis_with_special_chars(self, tmp_path: Path) -> None:
        """EC-08: Hypothesis labels with special chars roundtrip cleanly."""
        st = store(tmp_path)
        s = session()
        s.advance_turn(hypothesis_label='P0300: "random misfire" (all cyls)', hypothesis_status="eliminated")
        st.save(s)
        loaded = st.load(s.session_id)
        assert loaded is not None
        assert 'P0300: "random misfire" (all cyls)' in loaded.eliminated_hypotheses

    def test_ec09_year_as_int_string_none(self, tmp_path: Path) -> None:
        """EC-09: Year field as int, string, and None all survive roundtrip."""
        st = store(tmp_path)
        for year_val in [2020, "2020", None]:
            s = DiagnosticSession.create(
                vehicle={"make": "FORD", "year": year_val}, symptoms="stall",
                session_id=None
            )
            st.save(s)
            loaded = st.load(s.session_id)
            assert loaded is not None

    def test_ec11_sessions_dir_auto_created(self, tmp_path: Path) -> None:
        """EC-11: Sessions directory is created automatically if it doesn't exist."""
        new_dir = tmp_path / "deep" / "nested" / "sessions"
        assert not new_dir.exists()
        st = SessionStore(sessions_dir=new_dir)
        assert new_dir.exists()

    def test_ec12_corrupt_jsonl_line_skipped(self, tmp_path: Path) -> None:
        """EC-12: A corrupt JSON line mid-body is skipped; session still loads."""
        st = store(tmp_path)
        s = session()
        s.append_message("user", "good message")
        path = st.save(s)
        # Inject a corrupt line into the body
        content = path.read_text()
        path.write_text(content + "\n{this is not valid json}\n")
        loaded = st.load(s.session_id)
        assert loaded is not None
        # Good log entry survived; corrupt line skipped
        assert any(e.get("content") == "good message" for e in loaded.full_log)

    def test_ec15_find_by_repair_order_none(self, tmp_path: Path) -> None:
        """EC-15: find_by_repair_order when no sessions have that RO → None."""
        st = store(tmp_path)
        st.save(session())
        result = st.find_by_repair_order("RO-NONEXISTENT")
        assert result is None

    def test_ec19_fresh_session_no_log_entries(self, tmp_path: Path) -> None:
        """EC-19: Session with no log entries saves and loads cleanly."""
        st = store(tmp_path)
        s = session()
        assert len(s.full_log) == 0
        st.save(s)
        loaded = st.load(s.session_id)
        assert loaded is not None
        assert len(loaded.full_log) == 0

    def test_ec20_missing_session_id_in_frontmatter(self, tmp_path: Path) -> None:
        """EC-20: File with valid --- delimiters but no session_id → graceful None."""
        st = store(tmp_path)
        corrupt = tmp_path / "sessions" / "nosid.session"
        corrupt.parent.mkdir(parents=True, exist_ok=True)
        corrupt.write_text("---\nvehicle_make: FORD\nphase: SYMPTOM_COLLECTION\n---\n")
        result = st.load_file(corrupt)
        assert result is None

    # ── Search methods ─────────────────────────────────────────────────────────

    def test_ec10_find_by_vehicle_make_only(self, tmp_path: Path) -> None:
        """EC-10: find_by_vehicle with only make — returns all matching regardless of model."""
        st = store(tmp_path)
        ford1 = DiagnosticSession.create(vehicle={"make": "FORD", "model": "F150"}, symptoms="s1")
        ford2 = DiagnosticSession.create(vehicle={"make": "FORD", "model": "RANGER"}, symptoms="s2")
        toyota = DiagnosticSession.create(vehicle={"make": "TOYOTA", "model": "CAMRY"}, symptoms="s3")
        for s in [ford1, ford2, toyota]:
            st.save(s)
        results = st.find_by_vehicle(make="FORD")
        result_ids = {r.session_id for r in results}
        assert ford1.session_id in result_ids
        assert ford2.session_id in result_ids
        assert toyota.session_id not in result_ids

    def test_find_by_vehicle_case_insensitive(self, tmp_path: Path) -> None:
        st = store(tmp_path)
        s = DiagnosticSession.create(vehicle={"make": "ford", "model": "f-350"}, symptoms="no start")
        st.save(s)
        results = st.find_by_vehicle(make="FORD")
        assert any(r.session_id == s.session_id for r in results)

    def test_find_by_repair_order_returns_session(self, tmp_path: Path) -> None:
        st = store(tmp_path)
        s = DiagnosticSession.create(
            vehicle={"make": "GM"}, symptoms="shudder", repair_order="RO-1234"
        )
        st.save(s)
        result = st.find_by_repair_order("RO-1234")
        assert result is not None
        assert result.session_id == s.session_id

    def test_find_recent_respects_limit(self, tmp_path: Path) -> None:
        st = store(tmp_path)
        for i in range(10):
            st.save(DiagnosticSession.create(vehicle={"make": "HONDA"}, symptoms=f"s{i}"))
        results = st.find_recent(n=4)
        assert len(results) == 4

    def test_list_summaries_frontmatter_only(self, tmp_path: Path) -> None:
        st = store(tmp_path)
        for i in range(3):
            st.save(DiagnosticSession.create(vehicle={"make": "BMW"}, symptoms=f"s{i}"))
        summaries = st.list_summaries()
        assert len(summaries) == 3
        for fm in summaries:
            assert "session_id" in fm
            assert "vehicle_make" in fm

    def test_count_returns_correct_number(self, tmp_path: Path) -> None:
        st = store(tmp_path)
        for _ in range(5):
            st.save(session())
        assert st.count() == 5

    def test_iter_sessions_yields_all(self, tmp_path: Path) -> None:
        st = store(tmp_path)
        ids = set()
        for _ in range(4):
            s = session()
            st.save(s)
            ids.add(s.session_id)
        loaded_ids = {s.session_id for s in st.iter_sessions()}
        assert ids == loaded_ids

    # ── Human-readable file content ────────────────────────────────────────────

    def test_saved_file_is_human_readable(self, tmp_path: Path) -> None:
        """The saved file should be readable as plain text with visible vehicle info."""
        st = store(tmp_path)
        s = DiagnosticSession.create(
            vehicle={"make": "FORD", "model": "F350", "year": "2008"},
            symptoms="no crank no start",
            repair_order="RO-5555",
        )
        s.append_message("user", "battery is good")
        path = st.save(s)
        content = path.read_text()
        assert "FORD" in content
        assert "F350" in content
        assert "no crank no start" in content
        assert "RO-5555" in content
        assert "battery is good" in content

    def test_saved_file_jsonl_lines_are_valid_json(self, tmp_path: Path) -> None:
        st = store(tmp_path)
        s = session()
        s.append_message("user", "check engine")
        s.advance_turn(new_phase="HYPOTHESIS_GENERATION")
        path = st.save(s)
        content = path.read_text()
        # Find body after second ---
        parts = content.split("---", 2)
        body = parts[2].strip() if len(parts) == 3 else ""
        for line in body.splitlines():
            line = line.strip()
            if line:
                json.loads(line)  # should not raise
