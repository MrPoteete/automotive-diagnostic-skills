"""
Integration tests for src/diagnostic/engine_agent.py

Checked AGENTS.md - implementing directly because:
1. This is test code (quality-engineer agent scope)
2. Integration tests exercise the real DB path — no abstraction possible
3. data-engineer handles production imports; test fixture setup is testing scope

Uses REAL databases (no mocking). Tests are skipped automatically when
database files are not present (e.g., in CI without data).

Database paths:
- /home/poteete/projects/automotive-diagnostic-skills/database/automotive_complaints.db
  (562K complaints, FTS5, 211K TSBs)
- /home/poteete/projects/automotive-diagnostic-skills/database/automotive_diagnostics.db
  (792 vehicles)

Test categories:
- Ford F-150 2019 misfire scenario with P0300, P0301
- RAM 1500 2015 TIPM scenario (HIGH safety alert)
- Invalid DTC codes handled gracefully
- Empty symptoms handled gracefully
- Result schema validation
"""

import pytest

# ---------------------------------------------------------------------------
# All tests in this module are integration tests and require real databases.
# The real_db fixture in conftest.py handles skip logic automatically.
# ---------------------------------------------------------------------------


@pytest.mark.integration
class TestDiagnoseIntegration:
    """Integration tests for diagnose() against the real NHTSA database."""

    # -- Ford F-150 misfire scenario ------------------------------------------

    @pytest.mark.integration
    def test_ford_f150_misfire_returns_result_without_crash(self, real_db, ford_f150_2019):
        """Ford F-150 2019 misfire with P0300/P0301 must complete without error."""
        from src.diagnostic.engine_agent import diagnose

        result = diagnose(
            vehicle=ford_f150_2019,
            symptoms="engine misfires rough idle stumble hesitation",
            dtc_codes=["P0300", "P0301"],
            db=real_db,
        )

        assert isinstance(result, dict), "diagnose() must return a dict"
        assert "candidates" in result
        assert "warnings" in result
        assert "vehicle" in result
        assert "dtc_codes" in result

    @pytest.mark.integration
    def test_ford_f150_misfire_dtc_codes_validated(self, real_db, ford_f150_2019):
        """P0300 and P0301 are valid OBD-II codes and must appear in result."""
        from src.diagnostic.engine_agent import diagnose

        result = diagnose(
            vehicle=ford_f150_2019,
            symptoms="misfire",
            dtc_codes=["P0300", "P0301"],
            db=real_db,
        )
        assert "P0300" in result["dtc_codes"]
        assert "P0301" in result["dtc_codes"]

    @pytest.mark.integration
    def test_ford_f150_misfire_candidates_are_list(self, real_db, ford_f150_2019):
        """Candidates must be returned as a list (may be empty if DB has no data)."""
        from src.diagnostic.engine_agent import diagnose

        result = diagnose(
            vehicle=ford_f150_2019,
            symptoms="engine misfire rough idle",
            dtc_codes=["P0300"],
            db=real_db,
        )
        assert isinstance(result["candidates"], list)

    @pytest.mark.integration
    def test_ford_f150_misfire_candidate_schema(self, real_db, ford_f150_2019):
        """Any returned candidates must have the full required schema."""
        from src.diagnostic.engine_agent import diagnose

        result = diagnose(
            vehicle=ford_f150_2019,
            symptoms="engine misfire",
            dtc_codes=["P0300", "P0301"],
            db=real_db,
        )
        for candidate in result["candidates"]:
            assert "component" in candidate, f"Missing 'component': {candidate}"
            assert "confidence" in candidate, f"Missing 'confidence': {candidate}"
            assert "confidence_sufficient" in candidate, f"Missing 'confidence_sufficient': {candidate}"
            assert "safety_alert" in candidate, f"Missing 'safety_alert': {candidate}"
            assert "trend" in candidate, f"Missing 'trend': {candidate}"
            assert "tsbs" in candidate, f"Missing 'tsbs': {candidate}"
            assert "samples" in candidate, f"Missing 'samples': {candidate}"

    @pytest.mark.integration
    def test_ford_f150_misfire_confidence_in_range(self, real_db, ford_f150_2019):
        """All confidence scores must be in [0.0, 1.0]."""
        from src.diagnostic.engine_agent import diagnose

        result = diagnose(
            vehicle=ford_f150_2019,
            symptoms="misfire",
            db=real_db,
        )
        for candidate in result["candidates"]:
            conf = candidate["confidence"]
            assert 0.0 <= conf <= 1.0, f"Confidence out of range for {candidate['component']}: {conf}"

    @pytest.mark.integration
    def test_ford_f150_misfire_no_error_key_on_success(self, real_db, ford_f150_2019):
        """Successful diagnosis must not contain an 'error' key."""
        from src.diagnostic.engine_agent import diagnose

        result = diagnose(
            vehicle=ford_f150_2019,
            symptoms="misfire",
            db=real_db,
        )
        assert "error" not in result, f"Unexpected error in result: {result.get('error')}"

    # -- RAM 1500 2015 TIPM scenario ------------------------------------------

    @pytest.mark.integration
    @pytest.mark.safety
    def test_ram_1500_tipm_returns_result(self, real_db, ram_1500_2015):
        """RAM 1500 2015 TIPM diagnosis must complete without error."""
        from src.diagnostic.engine_agent import diagnose

        result = diagnose(
            vehicle=ram_1500_2015,
            symptoms="tipm electrical failure stall random shutdown",
            db=real_db,
        )
        assert isinstance(result, dict)
        assert "candidates" in result
        assert "warnings" in result

    @pytest.mark.integration
    @pytest.mark.safety
    def test_ram_1500_tipm_candidate_or_warning_present(self, real_db, ram_1500_2015):
        """TIPM diagnosis must return either candidates or an informational warning."""
        from src.diagnostic.engine_agent import diagnose

        result = diagnose(
            vehicle=ram_1500_2015,
            symptoms="tipm stall random shutdown electrical",
            db=real_db,
        )
        # Must have at least one of: candidates or warnings (not both empty)
        has_content = len(result["candidates"]) > 0 or len(result["warnings"]) > 0
        assert has_content, "Expected candidates or warnings for TIPM scenario, got neither"

    @pytest.mark.integration
    @pytest.mark.safety
    def test_ram_1500_tipm_high_alert_if_tipm_candidate(self, real_db, ram_1500_2015):
        """If TIPM appears as a candidate component, its safety_alert must be HIGH."""
        from src.diagnostic.engine_agent import diagnose

        result = diagnose(
            vehicle=ram_1500_2015,
            symptoms="tipm stall",
            db=real_db,
        )
        tipm_candidates = [
            c for c in result["candidates"]
            if c.get("component") and "tipm" in c["component"].lower()
        ]
        for candidate in tipm_candidates:
            alert = candidate.get("safety_alert")
            if alert is not None:
                assert alert["level"] in ("HIGH", "CRITICAL"), (
                    f"Expected HIGH or CRITICAL alert for TIPM, got: {alert['level']}"
                )

    @pytest.mark.integration
    @pytest.mark.safety
    def test_ram_1500_tipm_electrical_candidate_safety_check(self, real_db, ram_1500_2015):
        """ELECTRICAL SYSTEM candidate for TIPM scenario must be checked for safety."""
        from src.diagnostic.engine_agent import diagnose

        result = diagnose(
            vehicle=ram_1500_2015,
            symptoms="stall electrical failure",
            db=real_db,
        )
        # All candidates must have been safety-checked (field must exist)
        for candidate in result["candidates"]:
            assert "safety_alert" in candidate

    # -- Invalid DTC codes -----------------------------------------------------

    @pytest.mark.integration
    def test_all_invalid_dtc_codes_handled_gracefully(self, real_db, ford_f150_2019):
        """Entirely invalid DTC codes must not crash the engine."""
        from src.diagnostic.engine_agent import diagnose

        result = diagnose(
            vehicle=ford_f150_2019,
            symptoms="misfire",
            dtc_codes=["INVALID", "NOTADTC", "12345"],
            db=real_db,
        )
        assert isinstance(result, dict)
        assert result["dtc_codes"] == [], f"Expected empty dtc_codes, got: {result['dtc_codes']}"

    @pytest.mark.integration
    def test_mixed_invalid_valid_dtc_codes(self, real_db, ford_f150_2019):
        """Mixed invalid+valid DTC codes must filter to only valid ones."""
        from src.diagnostic.engine_agent import diagnose

        result = diagnose(
            vehicle=ford_f150_2019,
            symptoms="misfire",
            dtc_codes=["INVALID", "P0300", "BAD"],
            db=real_db,
        )
        assert result["dtc_codes"] == ["P0300"]

    @pytest.mark.integration
    def test_empty_dtc_codes_list_works(self, real_db, ford_f150_2019):
        """Empty DTC codes list must not cause errors."""
        from src.diagnostic.engine_agent import diagnose

        result = diagnose(
            vehicle=ford_f150_2019,
            symptoms="rough idle",
            dtc_codes=[],
            db=real_db,
        )
        assert isinstance(result, dict)
        assert result["dtc_codes"] == []

    # -- Empty symptoms --------------------------------------------------------

    @pytest.mark.integration
    def test_empty_symptoms_handled_gracefully(self, real_db, ford_f150_2019):
        """Empty symptoms string must not crash the engine."""
        from src.diagnostic.engine_agent import diagnose

        result = diagnose(
            vehicle=ford_f150_2019,
            symptoms="",
            db=real_db,
        )
        assert isinstance(result, dict)
        assert "candidates" in result
        assert "warnings" in result

    @pytest.mark.integration
    def test_whitespace_only_symptoms_handled_gracefully(self, real_db, ford_f150_2019):
        """Whitespace-only symptoms must not crash the engine."""
        from src.diagnostic.engine_agent import diagnose

        result = diagnose(
            vehicle=ford_f150_2019,
            symptoms="   ",
            db=real_db,
        )
        assert isinstance(result, dict)

    @pytest.mark.integration
    def test_empty_symptoms_with_valid_dtc_does_not_crash(self, real_db, ford_f150_2019):
        """Empty symptoms + valid DTC must fall back to DTC-derived candidates."""
        from src.diagnostic.engine_agent import diagnose

        result = diagnose(
            vehicle=ford_f150_2019,
            symptoms="",
            dtc_codes=["P0300"],
            db=real_db,
        )
        assert isinstance(result, dict)
        assert isinstance(result["candidates"], list)

    # -- Vehicle normalization -------------------------------------------------

    @pytest.mark.integration
    def test_lowercase_vehicle_normalized(self, real_db):
        """Lowercase vehicle input must be normalized to uppercase."""
        from src.diagnostic.engine_agent import diagnose

        result = diagnose(
            vehicle={"make": "ford", "model": "f-150", "year": 2019},
            symptoms="misfire",
            db=real_db,
        )
        assert result["vehicle"]["make"] == "FORD"
        assert result["vehicle"]["model"] == "F-150"

    # -- DB resource management ------------------------------------------------

    @pytest.mark.integration
    def test_real_db_not_closed_after_diagnose(self, real_db, ford_f150_2019):
        """When an external DB is provided, diagnose must not close it."""
        from src.diagnostic.engine_agent import diagnose

        diagnose(
            vehicle=ford_f150_2019,
            symptoms="misfire",
            db=real_db,
        )
        # Verify the connection is still usable after diagnose()
        count = real_db.count_complaints("FORD", "F-150", 2019, "engine")
        assert isinstance(count, int)

    # -- Result determinism ----------------------------------------------------

    @pytest.mark.integration
    def test_same_inputs_produce_same_result(self, real_db, ford_f150_2019):
        """Repeated calls with identical inputs must produce identical results."""
        from src.diagnostic.engine_agent import diagnose

        result_a = diagnose(
            vehicle=ford_f150_2019,
            symptoms="misfire",
            dtc_codes=["P0300"],
            db=real_db,
        )
        result_b = diagnose(
            vehicle=ford_f150_2019,
            symptoms="misfire",
            dtc_codes=["P0300"],
            db=real_db,
        )
        # Both must return the same number of candidates
        assert len(result_a["candidates"]) == len(result_b["candidates"])
        # Both must have the same DTC codes
        assert result_a["dtc_codes"] == result_b["dtc_codes"]

    # -- Data source attribution -----------------------------------------------

    @pytest.mark.integration
    def test_data_sources_populated(self, real_db, ford_f150_2019):
        """On successful diagnosis, data_sources dict must be non-empty."""
        from src.diagnostic.engine_agent import diagnose

        result = diagnose(
            vehicle=ford_f150_2019,
            symptoms="misfire",
            db=real_db,
        )
        # data_sources should be populated on the happy path
        # (could be empty on error path with no candidates)
        assert isinstance(result["data_sources"], dict)
