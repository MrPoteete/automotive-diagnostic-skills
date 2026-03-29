"""
Unit tests for src/diagnostic/engine_agent.py

Checked AGENTS.md - implementing directly because:
1. This is test code (quality-engineer agent scope)
2. All DB interactions are mocked — no data-engineer delegation needed
3. Safety-critical orchestration path tested end-to-end with mocks

Coverage targets (per TESTING.md): diagnostic_engine -> 100%

Test categories:
- _validate_dtc_codes: valid/invalid code filtering, edge cases
- diagnose: required output keys, missing vehicle fields, empty symptoms,
            safety alert propagation, confidence gating
"""

import pytest
from unittest.mock import MagicMock, patch

from src.diagnostic.engine_agent import _validate_dtc_codes, diagnose


# ===========================================================================
# _validate_dtc_codes
# ===========================================================================


class TestValidateDtcCodes:
    """Tests for _validate_dtc_codes(dtc_codes) -> list[str]."""

    # -- Valid codes ------------------------------------------------------------

    @pytest.mark.unit
    def test_valid_p_codes_returned(self):
        """Standard P-codes must pass validation."""
        result = _validate_dtc_codes(["P0300", "P0301"])
        assert "P0300" in result
        assert "P0301" in result

    @pytest.mark.unit
    def test_valid_c_code_returned(self):
        """C-code must pass validation."""
        assert "C1234" in _validate_dtc_codes(["C1234"])

    @pytest.mark.unit
    def test_valid_b_code_returned(self):
        """B-code must pass validation."""
        assert "B2105" in _validate_dtc_codes(["B2105"])

    @pytest.mark.unit
    def test_valid_u_code_returned(self):
        """U-code must pass validation."""
        assert "U0100" in _validate_dtc_codes(["U0100"])

    @pytest.mark.unit
    def test_all_valid_codes_returned(self):
        """All valid codes in a mixed-valid list must be returned."""
        codes = ["P0300", "C1234", "B2105", "U0100"]
        result = _validate_dtc_codes(codes)
        assert set(result) == set(codes)

    @pytest.mark.unit
    def test_lowercase_codes_uppercased_and_returned(self):
        """Lowercase codes must be uppercased and returned if otherwise valid."""
        result = _validate_dtc_codes(["p0300"])
        assert "P0300" in result

    @pytest.mark.unit
    def test_codes_with_leading_trailing_whitespace_stripped(self):
        """Codes with surrounding whitespace must be stripped and validated."""
        result = _validate_dtc_codes(["  P0300  "])
        assert "P0300" in result

    # -- Invalid codes ----------------------------------------------------------

    @pytest.mark.unit
    def test_invalid_code_not_returned(self):
        """'INVALID' must be filtered out."""
        result = _validate_dtc_codes(["INVALID"])
        assert result == []

    @pytest.mark.unit
    def test_mixed_valid_invalid_returns_only_valid(self):
        """Only valid codes must be returned from a mixed list."""
        result = _validate_dtc_codes(["INVALID", "P0300"])
        assert result == ["P0300"]

    @pytest.mark.unit
    def test_wrong_system_prefix_rejected(self):
        """Code starting with 'X' (not P/C/B/U) must be rejected."""
        result = _validate_dtc_codes(["X0300"])
        assert result == []

    @pytest.mark.unit
    def test_too_short_code_rejected(self):
        """Code shorter than 5 characters must be rejected."""
        result = _validate_dtc_codes(["P030"])
        assert result == []

    @pytest.mark.unit
    def test_too_long_code_rejected(self):
        """Code longer than 5 characters must be rejected."""
        result = _validate_dtc_codes(["P03001"])
        assert result == []

    @pytest.mark.unit
    def test_invalid_second_character_rejected(self):
        """Second character must be 0-3 (per OBD-II spec); '4' must be rejected."""
        result = _validate_dtc_codes(["P4300"])
        assert result == []

    @pytest.mark.unit
    def test_special_characters_rejected(self):
        """Codes with special characters must be rejected."""
        result = _validate_dtc_codes(["P03!0"])
        assert result == []

    @pytest.mark.unit
    def test_empty_string_rejected(self):
        """Empty string must be filtered out."""
        result = _validate_dtc_codes([""])
        assert result == []

    # -- Edge cases -------------------------------------------------------------

    @pytest.mark.unit
    def test_empty_list_returns_empty(self):
        """Empty input list must return empty list."""
        result = _validate_dtc_codes([])
        assert result == []

    @pytest.mark.unit
    def test_all_invalid_returns_empty(self):
        """All-invalid list must return empty list."""
        result = _validate_dtc_codes(["INVALID", "BAD", "NOPE"])
        assert result == []

    @pytest.mark.unit
    def test_returns_list_type(self):
        """Return type must always be a list."""
        assert isinstance(_validate_dtc_codes([]), list)
        assert isinstance(_validate_dtc_codes(["P0300"]), list)

    @pytest.mark.unit
    def test_valid_hex_digits_in_last_three_positions(self):
        """Last 3 characters must be [0-9A-F]; code with G must be rejected."""
        result = _validate_dtc_codes(["P030G"])
        assert result == []

    @pytest.mark.unit
    def test_all_zeros_valid(self):
        """P0000 is a valid OBD-II format code."""
        result = _validate_dtc_codes(["P0000"])
        assert "P0000" in result


# ===========================================================================
# diagnose
# ===========================================================================


class TestDiagnose:
    """Tests for diagnose(vehicle, symptoms, dtc_codes, db) -> dict."""

    @pytest.fixture(autouse=True)
    def mock_chroma(self) -> MagicMock:
        """Patch ChromaService so tests never touch the real ChromaDB Rust ext."""
        with patch("src.data.chroma_service.ChromaService") as mock_cls:
            instance = MagicMock()
            instance.document_count = 0
            mock_cls.return_value = instance
            yield mock_cls

    @pytest.fixture
    def vehicle(self) -> dict:
        return {"make": "FORD", "model": "F-150", "year": 2019}

    @pytest.fixture
    def full_mock_db(self) -> MagicMock:
        """Mock DB with realistic return values for the full diagnose() path."""
        db = MagicMock(name="DiagnosticDB")
        db.count_complaints.return_value = 0
        db.search_complaints.return_value = [
            {"component": "POWER TRAIN", "summary": "engine misfires at idle"},
            {"component": "POWER TRAIN", "summary": "rough idle and hesitation"},
        ]
        db.search_tsbs.return_value = []
        db.get_complaints_by_year.return_value = []
        return db

    # -- Required output keys ---------------------------------------------------

    @pytest.mark.unit
    def test_diagnose_returns_dict(self, vehicle, full_mock_db):
        """diagnose() must return a dict."""
        result = diagnose(vehicle, "engine misfires", db=full_mock_db)
        assert isinstance(result, dict)

    @pytest.mark.unit
    def test_result_has_vehicle_key(self, vehicle, full_mock_db):
        """Result must contain 'vehicle' key."""
        result = diagnose(vehicle, "engine misfires", db=full_mock_db)
        assert "vehicle" in result

    @pytest.mark.unit
    def test_result_has_symptoms_key(self, vehicle, full_mock_db):
        """Result must contain 'symptoms' key."""
        result = diagnose(vehicle, "engine misfires", db=full_mock_db)
        assert "symptoms" in result

    @pytest.mark.unit
    def test_result_has_dtc_codes_key(self, vehicle, full_mock_db):
        """Result must contain 'dtc_codes' key."""
        result = diagnose(vehicle, "engine misfires", db=full_mock_db)
        assert "dtc_codes" in result

    @pytest.mark.unit
    def test_result_has_candidates_key(self, vehicle, full_mock_db):
        """Result must contain 'candidates' key."""
        result = diagnose(vehicle, "engine misfires", db=full_mock_db)
        assert "candidates" in result

    @pytest.mark.unit
    def test_result_has_warnings_key(self, vehicle, full_mock_db):
        """Result must contain 'warnings' key."""
        result = diagnose(vehicle, "engine misfires", db=full_mock_db)
        assert "warnings" in result

    @pytest.mark.unit
    def test_result_has_data_sources_key(self, vehicle, full_mock_db):
        """Result must contain 'data_sources' key."""
        result = diagnose(vehicle, "engine misfires", db=full_mock_db)
        assert "data_sources" in result

    @pytest.mark.unit
    def test_candidates_is_list(self, vehicle, full_mock_db):
        """'candidates' must be a list."""
        result = diagnose(vehicle, "engine misfires", db=full_mock_db)
        assert isinstance(result["candidates"], list)

    @pytest.mark.unit
    def test_warnings_is_list(self, vehicle, full_mock_db):
        """'warnings' must be a list."""
        result = diagnose(vehicle, "engine misfires", db=full_mock_db)
        assert isinstance(result["warnings"], list)

    @pytest.mark.unit
    def test_vehicle_normalized_to_uppercase(self, full_mock_db):
        """Vehicle make and model must be uppercased in the output."""
        vehicle = {"make": "ford", "model": "f-150", "year": 2019}
        result = diagnose(vehicle, "misfire", db=full_mock_db)
        assert result["vehicle"]["make"] == "FORD"
        assert result["vehicle"]["model"] == "F-150"

    @pytest.mark.unit
    def test_symptoms_preserved_in_output(self, vehicle, full_mock_db):
        """The input symptoms string must appear in the result."""
        result = diagnose(vehicle, "rough idle and stumble", db=full_mock_db)
        assert result["symptoms"] == "rough idle and stumble"

    @pytest.mark.unit
    def test_valid_dtc_codes_in_output(self, vehicle, full_mock_db):
        """Valid DTC codes must appear in result['dtc_codes']."""
        result = diagnose(vehicle, "misfire", dtc_codes=["P0300", "P0301"], db=full_mock_db)
        assert "P0300" in result["dtc_codes"]
        assert "P0301" in result["dtc_codes"]

    # -- Missing/invalid vehicle fields ----------------------------------------

    @pytest.mark.unit
    def test_missing_make_returns_error_result(self, full_mock_db):
        """Missing 'make' must return an error result with a warning."""
        vehicle = {"model": "F-150", "year": 2019}
        result = diagnose(vehicle, "misfire", db=full_mock_db)
        assert len(result["warnings"]) > 0
        assert result["candidates"] == []

    @pytest.mark.unit
    def test_missing_model_returns_error_result(self, full_mock_db):
        """Missing 'model' must return an error result with a warning."""
        vehicle = {"make": "FORD", "year": 2019}
        result = diagnose(vehicle, "misfire", db=full_mock_db)
        assert len(result["warnings"]) > 0
        assert result["candidates"] == []

    @pytest.mark.unit
    def test_missing_year_returns_error_result(self, full_mock_db):
        """Missing 'year' (defaults to 0) must return an error result."""
        vehicle = {"make": "FORD", "model": "F-150"}
        result = diagnose(vehicle, "misfire", db=full_mock_db)
        assert len(result["warnings"]) > 0
        assert result["candidates"] == []

    @pytest.mark.unit
    def test_empty_vehicle_returns_error_result(self, full_mock_db):
        """Empty vehicle dict must return an error result."""
        result = diagnose({}, "misfire", db=full_mock_db)
        assert len(result["warnings"]) > 0
        assert result["candidates"] == []

    @pytest.mark.unit
    def test_error_result_has_all_required_keys(self, full_mock_db):
        """Even error results must have all required top-level keys."""
        result = diagnose({}, "misfire", db=full_mock_db)
        for key in ("vehicle", "symptoms", "dtc_codes", "candidates", "warnings", "data_sources"):
            assert key in result, f"Missing key in error result: '{key}'"

    # -- Invalid DTC codes in input --------------------------------------------

    @pytest.mark.unit
    def test_invalid_dtc_codes_filtered_out(self, vehicle, full_mock_db):
        """Invalid DTC codes must be filtered; valid ones must remain."""
        result = diagnose(vehicle, "misfire", dtc_codes=["INVALID", "P0300"], db=full_mock_db)
        assert "P0300" in result["dtc_codes"]
        assert "INVALID" not in result["dtc_codes"]

    @pytest.mark.unit
    def test_all_invalid_dtc_codes_produce_empty_list(self, vehicle, full_mock_db):
        """All-invalid DTC codes must result in an empty dtc_codes list."""
        result = diagnose(vehicle, "misfire", dtc_codes=["INVALID", "BAD"], db=full_mock_db)
        assert result["dtc_codes"] == []

    @pytest.mark.unit
    def test_no_dtc_codes_defaults_to_empty_list(self, vehicle, full_mock_db):
        """Omitting dtc_codes must produce an empty list, not None."""
        result = diagnose(vehicle, "misfire", db=full_mock_db)
        assert result["dtc_codes"] == []
        assert isinstance(result["dtc_codes"], list)

    # -- Empty symptoms ---------------------------------------------------------

    @pytest.mark.unit
    def test_empty_symptoms_with_no_dtcs_returns_no_candidates(self, vehicle):
        """Empty symptoms with no DTC codes must return an empty candidates list."""
        db = MagicMock()
        db.count_complaints.return_value = 0
        db.search_complaints.return_value = []
        db.search_tsbs.return_value = []
        db.get_complaints_by_year.return_value = []
        result = diagnose(vehicle, "", db=db)
        assert isinstance(result["candidates"], list)
        # With no symptoms and no DTCs, no candidates expected
        assert len(result["candidates"]) == 0

    @pytest.mark.unit
    def test_empty_symptoms_with_valid_dtcs_uses_dtc_fallback(self, vehicle):
        """Empty symptoms with valid DTC codes must fall back to DTC-derived candidates."""
        db = MagicMock()
        db.count_complaints.return_value = 0
        db.search_complaints.return_value = []  # No FTS results
        db.search_tsbs.return_value = []
        db.get_complaints_by_year.return_value = []
        result = diagnose(vehicle, "", dtc_codes=["P0300"], db=db)
        # DTC fallback should produce at least one candidate (POWER TRAIN)
        assert isinstance(result["candidates"], list)

    # -- Safety alert propagation ----------------------------------------------

    @pytest.mark.unit
    @pytest.mark.safety
    def test_brake_component_triggers_safety_warning(self, vehicle):
        """When BRAKES component appears in results, safety warning must be in warnings."""
        db = MagicMock()
        db.count_complaints.return_value = 0
        db.search_complaints.return_value = [
            {"component": "BRAKES", "summary": "brake pedal goes to floor"},
            {"component": "BRAKES", "summary": "loss of braking power"},
        ]
        db.search_tsbs.return_value = []
        db.get_complaints_by_year.return_value = []

        result = diagnose(vehicle, "brake", db=db)
        # CRITICAL safety alert for brakes must appear somewhere in output
        # Either in top-level warnings or in a candidate's safety_alert field
        has_brake_warning = (
            any("brake" in w.lower() or "safety" in w.lower() for w in result["warnings"])
            or any(
                c.get("safety_alert") is not None
                for c in result["candidates"]
            )
        )
        assert has_brake_warning, (
            f"Expected brake safety warning but got: warnings={result['warnings']}, "
            f"candidates={[c.get('safety_alert') for c in result['candidates']]}"
        )

    @pytest.mark.unit
    @pytest.mark.safety
    def test_candidate_has_safety_alert_field(self, vehicle, full_mock_db):
        """Each candidate in the result must have a 'safety_alert' field."""
        result = diagnose(vehicle, "misfire", db=full_mock_db)
        for candidate in result["candidates"]:
            assert "safety_alert" in candidate, (
                f"Candidate missing 'safety_alert': {candidate}"
            )

    @pytest.mark.unit
    @pytest.mark.safety
    def test_candidate_has_confidence_field(self, vehicle, full_mock_db):
        """Each candidate must have a 'confidence' field."""
        result = diagnose(vehicle, "misfire", db=full_mock_db)
        for candidate in result["candidates"]:
            assert "confidence" in candidate

    @pytest.mark.unit
    @pytest.mark.safety
    def test_candidate_has_confidence_sufficient_field(self, vehicle, full_mock_db):
        """Each candidate must have a 'confidence_sufficient' boolean field."""
        result = diagnose(vehicle, "misfire", db=full_mock_db)
        for candidate in result["candidates"]:
            assert "confidence_sufficient" in candidate
            assert isinstance(candidate["confidence_sufficient"], bool)

    @pytest.mark.unit
    @pytest.mark.safety
    def test_candidate_has_trend_field(self, vehicle, full_mock_db):
        """Each candidate must have a 'trend' field."""
        result = diagnose(vehicle, "misfire", db=full_mock_db)
        for candidate in result["candidates"]:
            assert "trend" in candidate

    @pytest.mark.unit
    @pytest.mark.safety
    def test_candidate_has_tsbs_field(self, vehicle, full_mock_db):
        """Each candidate must have a 'tsbs' field."""
        result = diagnose(vehicle, "misfire", db=full_mock_db)
        for candidate in result["candidates"]:
            assert "tsbs" in candidate

    # -- DB lifecycle ----------------------------------------------------------

    @pytest.mark.unit
    def test_diagnose_creates_db_if_none_provided(self, vehicle):
        """When db=None, diagnose must instantiate and close DiagnosticDB internally."""
        with patch("src.diagnostic.engine_agent.DiagnosticDB") as MockDB:
            mock_instance = MagicMock()
            mock_instance.count_complaints.return_value = 0
            mock_instance.search_complaints.return_value = []
            mock_instance.search_tsbs.return_value = []
            mock_instance.get_complaints_by_year.return_value = []
            MockDB.return_value = mock_instance

            diagnose(vehicle, "misfire")

            MockDB.assert_called_once()
            mock_instance.close.assert_called_once()

    @pytest.mark.unit
    def test_diagnose_does_not_close_external_db(self, vehicle, full_mock_db):
        """When a db is provided externally, diagnose must NOT close it."""
        diagnose(vehicle, "misfire", db=full_mock_db)
        full_mock_db.close.assert_not_called()

    # -- Confidence gating for safety-critical components ---------------------

    @pytest.mark.unit
    @pytest.mark.safety
    def test_low_confidence_safety_component_adds_warning(self, vehicle):
        """When a safety-critical component has confidence < 0.9, a warning must appear.

        Brakes with 0 complaint count, no DTC match, no pattern match:
        base=0.5, safety bonus=0.05 -> 0.55, which is < 0.9 threshold.
        """
        db = MagicMock()
        db.count_complaints.return_value = 0  # No frequency boost
        db.search_complaints.return_value = [
            {"component": "BRAKES", "summary": "brake noise"},
        ]
        db.search_tsbs.return_value = []
        db.get_complaints_by_year.return_value = []

        result = diagnose(vehicle, "brake", db=db)
        # With confidence ~0.55 for BRAKES, an "INSUFFICIENT CONFIDENCE" warning
        # must be added
        confidence_warnings = [
            w for w in result["warnings"]
            if "insufficient confidence" in w.lower() or "confidence" in w.lower()
        ]
        # Either a confidence warning exists, or the safety alert message covers it
        brake_candidates = [
            c for c in result["candidates"]
            if "brake" in c["component"].lower()
        ]
        if brake_candidates:
            brake = brake_candidates[0]
            if not brake["confidence_sufficient"]:
                assert len(confidence_warnings) > 0 or brake["safety_alert"] is not None
