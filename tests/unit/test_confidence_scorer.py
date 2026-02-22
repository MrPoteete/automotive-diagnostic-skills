"""
Unit tests for src/diagnostic/confidence_scorer.py

Checked AGENTS.md - implementing directly because:
1. This is test code (quality-engineer agent scope)
2. All mocking is self-contained — no security or data-engineer delegation needed
3. Tests validate existing logic; no new business logic is introduced here

Coverage targets (per TESTING.md): confidence_scoring -> 90%

Test categories:
- is_safety_critical: keyword detection for CRITICAL and HIGH levels
- calculate_confidence: base score, bonus stacking, frequency boost, cap
- _dtc_matches_component: DTC prefix -> component keyword heuristic
- score_results: returns sorted list with confidence field
"""

import pytest
from unittest.mock import MagicMock

from src.diagnostic.confidence_scorer import (
    is_safety_critical,
    calculate_confidence,
    score_results,
    _dtc_matches_component,
)


# ===========================================================================
# is_safety_critical
# ===========================================================================


class TestIsSafetyCritical:
    """Tests for is_safety_critical(component) -> tuple[bool, str | None]."""

    # -- CRITICAL level keywords -------------------------------------------------

    @pytest.mark.unit
    @pytest.mark.safety
    def test_brake_system_is_critical(self):
        """'brake system' must be flagged CRITICAL (contains 'brake')."""
        is_critical, level = is_safety_critical("brake system")
        assert is_critical is True
        assert level == "CRITICAL"

    @pytest.mark.unit
    @pytest.mark.safety
    def test_abs_pump_is_critical(self):
        """'abs pump' must be flagged CRITICAL (contains 'abs')."""
        is_critical, level = is_safety_critical("abs pump")
        assert is_critical is True
        assert level == "CRITICAL"

    @pytest.mark.unit
    @pytest.mark.safety
    def test_airbag_control_unit_is_critical(self):
        """'airbag control unit' must be flagged CRITICAL (contains 'airbag')."""
        is_critical, level = is_safety_critical("airbag control unit")
        assert is_critical is True
        assert level == "CRITICAL"

    @pytest.mark.unit
    @pytest.mark.safety
    def test_srs_module_is_critical(self):
        """'srs module' must be flagged CRITICAL (supplemental restraint system)."""
        is_critical, level = is_safety_critical("srs module")
        assert is_critical is True
        assert level == "CRITICAL"

    @pytest.mark.unit
    @pytest.mark.safety
    def test_steering_column_is_critical(self):
        """'steering column' must be flagged CRITICAL (contains 'steering')."""
        is_critical, level = is_safety_critical("steering column")
        assert is_critical is True
        assert level == "CRITICAL"

    @pytest.mark.unit
    @pytest.mark.safety
    def test_eps_motor_is_critical(self):
        """'eps motor' must be flagged CRITICAL (electric power steering)."""
        is_critical, level = is_safety_critical("eps motor")
        assert is_critical is True
        assert level == "CRITICAL"

    @pytest.mark.unit
    @pytest.mark.safety
    def test_keyword_match_is_case_insensitive(self):
        """Keyword matching must be case-insensitive ('BRAKE' == 'brake')."""
        is_critical, level = is_safety_critical("BRAKE CALIPER")
        assert is_critical is True
        assert level == "CRITICAL"

    @pytest.mark.unit
    @pytest.mark.safety
    def test_keyword_match_substring(self):
        """'abs' must match as a substring within a longer component string."""
        is_critical, level = is_safety_critical("abs modulator valve")
        assert is_critical is True
        assert level == "CRITICAL"

    # -- HIGH level keywords -----------------------------------------------------

    @pytest.mark.unit
    @pytest.mark.safety
    def test_tipm_is_high(self):
        """'tipm' (totally integrated power module) must be flagged HIGH."""
        is_critical, level = is_safety_critical("tipm relay")
        assert is_critical is True
        assert level == "HIGH"

    @pytest.mark.unit
    @pytest.mark.safety
    def test_throttle_body_is_high(self):
        """'throttle body' must be flagged HIGH (contains 'throttle')."""
        is_critical, level = is_safety_critical("throttle body")
        assert is_critical is True
        assert level == "HIGH"

    @pytest.mark.unit
    @pytest.mark.safety
    def test_pedal_sensor_is_high(self):
        """'accelerator pedal sensor' must be flagged HIGH (contains 'pedal')."""
        is_critical, level = is_safety_critical("accelerator pedal sensor")
        assert is_critical is True
        assert level == "HIGH"

    @pytest.mark.unit
    @pytest.mark.safety
    def test_fuel_pump_is_high(self):
        """'fuel pump module' must be flagged HIGH (phrase 'fuel pump' matches)."""
        is_critical, level = is_safety_critical("fuel pump module")
        assert is_critical is True
        assert level == "HIGH"

    @pytest.mark.unit
    @pytest.mark.safety
    def test_fire_keyword_is_high(self):
        """'fire' in component name must be flagged HIGH."""
        is_critical, level = is_safety_critical("engine compartment fire")
        assert is_critical is True
        assert level == "HIGH"

    @pytest.mark.unit
    @pytest.mark.safety
    def test_crash_keyword_is_high(self):
        """'crash' in component name must be flagged HIGH."""
        is_critical, level = is_safety_critical("crash sensor")
        assert is_critical is True
        assert level == "HIGH"

    # -- Not safety-critical -----------------------------------------------------

    @pytest.mark.unit
    def test_engine_not_critical(self):
        """'engine' alone is not in any safety keyword list."""
        is_critical, level = is_safety_critical("engine")
        assert is_critical is False
        assert level is None

    @pytest.mark.unit
    def test_power_train_not_critical(self):
        """'power train' is a NHTSA category but not a safety-critical keyword."""
        is_critical, level = is_safety_critical("power train")
        assert is_critical is False
        assert level is None

    @pytest.mark.unit
    def test_exhaust_not_critical(self):
        """'exhaust system' contains no safety-critical keywords."""
        is_critical, level = is_safety_critical("exhaust system")
        assert is_critical is False
        assert level is None

    @pytest.mark.unit
    def test_transmission_not_critical(self):
        """'transmission' is not in the safety keyword lists."""
        is_critical, level = is_safety_critical("transmission")
        assert is_critical is False
        assert level is None

    @pytest.mark.unit
    def test_empty_component_not_critical(self):
        """Empty string must not trigger a safety flag."""
        is_critical, level = is_safety_critical("")
        assert is_critical is False
        assert level is None

    @pytest.mark.unit
    def test_unknown_component_not_critical(self):
        """Arbitrary unknown text must not trigger a safety flag."""
        is_critical, level = is_safety_critical("widget xyz assembly")
        assert is_critical is False
        assert level is None

    @pytest.mark.unit
    def test_returns_two_tuple(self):
        """Return value must always be a 2-tuple."""
        result = is_safety_critical("brake")
        assert isinstance(result, tuple)
        assert len(result) == 2

    @pytest.mark.unit
    def test_non_critical_second_element_is_none(self):
        """Second element must be None when component is not safety-critical."""
        _, level = is_safety_critical("exhaust")
        assert level is None


# ===========================================================================
# calculate_confidence
# ===========================================================================


class TestCalculateConfidence:
    """Tests for calculate_confidence(vehicle, component, db, ...) -> float."""

    @pytest.fixture
    def vehicle(self) -> dict:
        return {"make": "FORD", "model": "F-150", "year": 2019}

    @pytest.fixture
    def zero_count_db(self) -> MagicMock:
        """DB that always reports 0 complaints — no frequency boost."""
        db = MagicMock(name="DiagnosticDB")
        db.count_complaints.return_value = 0
        return db

    # -- Base score -------------------------------------------------------------

    @pytest.mark.unit
    def test_base_score_is_0_5(self, vehicle, zero_count_db):
        """With no matches and zero complaints, base score must be exactly 0.5."""
        score = calculate_confidence(
            vehicle, "engine", zero_count_db,
            has_dtc_match=False, has_pattern_match=False
        )
        assert score == pytest.approx(0.5)

    # -- DTC match bonus (+0.20) ------------------------------------------------

    @pytest.mark.unit
    def test_dtc_match_adds_020(self, vehicle, zero_count_db):
        """has_dtc_match=True must add 0.20 to the base score."""
        score = calculate_confidence(
            vehicle, "engine", zero_count_db,
            has_dtc_match=True, has_pattern_match=False
        )
        assert score == pytest.approx(0.70)

    @pytest.mark.unit
    def test_dtc_match_false_no_bonus(self, vehicle, zero_count_db):
        """has_dtc_match=False must not change the base score."""
        score = calculate_confidence(
            vehicle, "engine", zero_count_db,
            has_dtc_match=False, has_pattern_match=False
        )
        assert score == pytest.approx(0.50)

    # -- Pattern match bonus (+0.15) --------------------------------------------

    @pytest.mark.unit
    def test_pattern_match_adds_015(self, vehicle, zero_count_db):
        """has_pattern_match=True must add 0.15 to the base score."""
        score = calculate_confidence(
            vehicle, "engine", zero_count_db,
            has_dtc_match=False, has_pattern_match=True
        )
        assert score == pytest.approx(0.65)

    @pytest.mark.unit
    def test_dtc_and_pattern_match_stack(self, vehicle, zero_count_db):
        """DTC bonus and pattern match bonus must both apply (0.5 + 0.20 + 0.15 = 0.85)."""
        score = calculate_confidence(
            vehicle, "engine", zero_count_db,
            has_dtc_match=True, has_pattern_match=True
        )
        assert score == pytest.approx(0.85)

    # -- Safety-critical keyword bonus (+0.05) ----------------------------------

    @pytest.mark.unit
    @pytest.mark.safety
    def test_safety_critical_adds_005(self, vehicle, zero_count_db):
        """Safety-critical component must add +0.05 on top of base 0.5."""
        score = calculate_confidence(
            vehicle, "brake system", zero_count_db,
            has_dtc_match=False, has_pattern_match=False
        )
        assert score == pytest.approx(0.55)

    @pytest.mark.unit
    @pytest.mark.safety
    def test_safety_critical_with_dtc_match(self, vehicle, zero_count_db):
        """Safety bonus stacks with DTC bonus (0.5 + 0.20 + 0.05 = 0.75)."""
        score = calculate_confidence(
            vehicle, "brake system", zero_count_db,
            has_dtc_match=True, has_pattern_match=False
        )
        assert score == pytest.approx(0.75)

    @pytest.mark.unit
    @pytest.mark.safety
    def test_safety_critical_all_bonuses(self, vehicle, zero_count_db):
        """All bonuses combined for safety-critical: 0.5 + 0.20 + 0.15 + 0.05 = 0.90."""
        score = calculate_confidence(
            vehicle, "brake system", zero_count_db,
            has_dtc_match=True, has_pattern_match=True
        )
        assert score == pytest.approx(0.90)

    # -- Frequency boost --------------------------------------------------------

    @pytest.mark.unit
    def test_frequency_boost_10_to_50_complaints(self, vehicle):
        """11 complaints (>10 threshold) must add +0.05 frequency boost."""
        db = MagicMock()
        db.count_complaints.return_value = 11
        score = calculate_confidence(
            vehicle, "engine", db,
            has_dtc_match=False, has_pattern_match=False
        )
        # 0.5 base + 0.05 freq
        assert score == pytest.approx(0.55)

    @pytest.mark.unit
    def test_frequency_boost_50_to_100_complaints(self, vehicle):
        """51 complaints (>50 threshold) must add +0.10 frequency boost."""
        db = MagicMock()
        db.count_complaints.return_value = 51
        score = calculate_confidence(
            vehicle, "engine", db,
            has_dtc_match=False, has_pattern_match=False
        )
        # 0.5 base + 0.10 freq
        assert score == pytest.approx(0.60)

    @pytest.mark.unit
    def test_frequency_boost_over_100_complaints(self, vehicle):
        """101 complaints (>100 threshold) must add +0.15 frequency boost."""
        db = MagicMock()
        db.count_complaints.return_value = 101
        score = calculate_confidence(
            vehicle, "engine", db,
            has_dtc_match=False, has_pattern_match=False
        )
        # 0.5 base + 0.15 freq
        assert score == pytest.approx(0.65)

    @pytest.mark.unit
    def test_frequency_boost_zero_complaints(self, vehicle, zero_count_db):
        """0 complaints must add no frequency boost."""
        score = calculate_confidence(
            vehicle, "engine", zero_count_db,
            has_dtc_match=False, has_pattern_match=False
        )
        assert score == pytest.approx(0.50)

    @pytest.mark.unit
    def test_frequency_boost_exactly_10_complaints(self, vehicle):
        """Exactly 10 complaints does not exceed the >10 threshold — no boost."""
        db = MagicMock()
        db.count_complaints.return_value = 10
        score = calculate_confidence(
            vehicle, "engine", db,
            has_dtc_match=False, has_pattern_match=False
        )
        assert score == pytest.approx(0.50)

    # -- Score capped at 1.0 ----------------------------------------------------

    @pytest.mark.unit
    def test_confidence_capped_at_1_0(self, vehicle):
        """Score must never exceed 1.0 regardless of bonus stacking."""
        db = MagicMock()
        db.count_complaints.return_value = 500  # +0.15 freq
        score = calculate_confidence(
            vehicle, "brake system", db,
            has_dtc_match=True,      # +0.20
            has_pattern_match=True,  # +0.15
        )
        # 0.5 + 0.20 + 0.15 + 0.15 + 0.05 = 1.05, capped to 1.0
        assert score == pytest.approx(1.0)

    @pytest.mark.unit
    def test_score_within_valid_range(self, vehicle, zero_count_db):
        """Confidence must always be in [0.0, 1.0]."""
        score = calculate_confidence(
            vehicle, "engine", zero_count_db,
            has_dtc_match=True, has_pattern_match=True
        )
        assert 0.0 <= score <= 1.0

    # -- DB exception resilience ------------------------------------------------

    @pytest.mark.unit
    def test_db_exception_falls_back_gracefully(self, vehicle):
        """If db.count_complaints raises, confidence must still return a valid score."""
        db = MagicMock()
        db.count_complaints.side_effect = RuntimeError("connection lost")
        # Should not raise; frequency boost simply not applied
        score = calculate_confidence(
            vehicle, "engine", db,
            has_dtc_match=False, has_pattern_match=False
        )
        assert score == pytest.approx(0.50)

    # -- Missing vehicle fields -------------------------------------------------

    @pytest.mark.unit
    def test_missing_year_defaults_to_0(self, zero_count_db):
        """Missing 'year' key must not raise — defaults to 0."""
        vehicle = {"make": "FORD", "model": "F-150"}
        score = calculate_confidence(vehicle, "engine", zero_count_db)
        assert isinstance(score, float)

    @pytest.mark.unit
    def test_empty_vehicle_does_not_raise(self, zero_count_db):
        """Empty vehicle dict must not raise an exception."""
        score = calculate_confidence({}, "engine", zero_count_db)
        assert isinstance(score, float)


# ===========================================================================
# _dtc_matches_component
# ===========================================================================


class TestDtcMatchesComponent:
    """Tests for _dtc_matches_component(dtc_codes, component) -> bool."""

    # -- P-codes (powertrain) ---------------------------------------------------

    @pytest.mark.unit
    def test_p_code_matches_power_train(self):
        """P-codes map to 'power train' keyword."""
        assert _dtc_matches_component(["P0300"], "power train") is True

    @pytest.mark.unit
    def test_p_code_matches_engine(self):
        """P-codes also map to 'engine'."""
        assert _dtc_matches_component(["P0301"], "engine compartment") is True

    @pytest.mark.unit
    def test_p_code_matches_fuel(self):
        """P-codes map to 'fuel' keyword."""
        assert _dtc_matches_component(["P0171"], "fuel system") is True

    @pytest.mark.unit
    def test_p_code_matches_ignition(self):
        """P-codes map to 'ignition' keyword."""
        assert _dtc_matches_component(["P0350"], "ignition coil") is True

    @pytest.mark.unit
    def test_p_code_does_not_match_chassis(self):
        """P-codes must NOT match 'chassis'."""
        assert _dtc_matches_component(["P0300"], "chassis") is False

    # -- C-codes (chassis) ------------------------------------------------------

    @pytest.mark.unit
    def test_c_code_matches_chassis(self):
        """C-codes map to 'chassis' keyword."""
        assert _dtc_matches_component(["C1234"], "chassis") is True

    @pytest.mark.unit
    def test_c_code_matches_brake(self):
        """C-codes also map to 'brake' keyword."""
        assert _dtc_matches_component(["C0040"], "brake system") is True

    @pytest.mark.unit
    def test_c_code_matches_suspension(self):
        """C-codes map to 'suspension' keyword."""
        assert _dtc_matches_component(["C0200"], "front suspension") is True

    @pytest.mark.unit
    def test_c_code_matches_steering(self):
        """C-codes map to 'steering' keyword."""
        assert _dtc_matches_component(["C0455"], "steering column") is True

    @pytest.mark.unit
    def test_c_code_does_not_match_engine(self):
        """C-codes must NOT match 'engine'."""
        assert _dtc_matches_component(["C1234"], "engine") is False

    # -- B-codes (body) ---------------------------------------------------------

    @pytest.mark.unit
    def test_b_code_matches_body(self):
        """B-codes map to 'body' keyword."""
        assert _dtc_matches_component(["B2105"], "body electrical") is True

    @pytest.mark.unit
    def test_b_code_matches_airbag(self):
        """B-codes map to 'airbag' keyword."""
        assert _dtc_matches_component(["B0050"], "airbag assembly") is True

    @pytest.mark.unit
    def test_b_code_matches_srs(self):
        """B-codes map to 'srs' keyword."""
        assert _dtc_matches_component(["B0082"], "srs control module") is True

    # -- U-codes (network) ------------------------------------------------------

    @pytest.mark.unit
    def test_u_code_matches_network(self):
        """U-codes map to 'network' keyword."""
        assert _dtc_matches_component(["U0100"], "can network") is True

    @pytest.mark.unit
    def test_u_code_matches_electrical(self):
        """U-codes map to 'electrical' keyword."""
        assert _dtc_matches_component(["U0155"], "electrical system") is True

    @pytest.mark.unit
    def test_u_code_matches_module(self):
        """U-codes map to 'module' keyword."""
        assert _dtc_matches_component(["U0073"], "control module") is True

    # -- Multiple codes ---------------------------------------------------------

    @pytest.mark.unit
    def test_any_matching_code_returns_true(self):
        """If at least one code maps to the component, return True."""
        assert _dtc_matches_component(["P0300", "C1234"], "chassis") is True

    @pytest.mark.unit
    def test_mixed_codes_no_match(self):
        """If no code maps to the component, return False."""
        assert _dtc_matches_component(["P0300", "P0301"], "chassis") is False

    # -- Edge cases -------------------------------------------------------------

    @pytest.mark.unit
    def test_empty_list_returns_false(self):
        """Empty DTC list must return False (no match possible)."""
        assert _dtc_matches_component([], "engine") is False

    @pytest.mark.unit
    def test_empty_code_string_skipped(self):
        """Empty string entries in the list must not cause errors."""
        assert _dtc_matches_component(["", "P0300"], "engine") is True

    @pytest.mark.unit
    def test_unknown_prefix_returns_false(self):
        """DTC prefix not in the mapping must return False."""
        assert _dtc_matches_component(["X0000"], "engine") is False

    @pytest.mark.unit
    def test_lowercase_code_handled(self):
        """The function uppercases the prefix, so lowercase codes still match."""
        assert _dtc_matches_component(["p0300"], "engine") is True

    @pytest.mark.unit
    def test_empty_component_returns_false(self):
        """Empty component string has no keywords to match against."""
        assert _dtc_matches_component(["P0300"], "") is False


# ===========================================================================
# score_results
# ===========================================================================


class TestScoreResults:
    """Tests for score_results(vehicle, components, db, dtc_codes) -> list[dict]."""

    @pytest.fixture
    def vehicle(self) -> dict:
        return {"make": "FORD", "model": "F-150", "year": 2019}

    @pytest.fixture
    def zero_count_db(self) -> MagicMock:
        db = MagicMock()
        db.count_complaints.return_value = 0
        return db

    @pytest.mark.unit
    def test_returns_list(self, vehicle, zero_count_db):
        """score_results must always return a list."""
        result = score_results(vehicle, [], zero_count_db)
        assert isinstance(result, list)

    @pytest.mark.unit
    def test_empty_components_returns_empty(self, vehicle, zero_count_db):
        """Empty component list must yield an empty scored list."""
        result = score_results(vehicle, [], zero_count_db)
        assert result == []

    @pytest.mark.unit
    def test_confidence_field_added(self, vehicle, zero_count_db):
        """Each result dict must gain a 'confidence' field."""
        components = [{"component": "engine", "count": 5}]
        result = score_results(vehicle, components, zero_count_db)
        assert len(result) == 1
        assert "confidence" in result[0]

    @pytest.mark.unit
    def test_original_fields_preserved(self, vehicle, zero_count_db):
        """Existing fields in the component dict must be preserved."""
        components = [{"component": "engine", "count": 42, "samples": ["foo"]}]
        result = score_results(vehicle, components, zero_count_db)
        assert result[0]["count"] == 42
        assert result[0]["samples"] == ["foo"]

    @pytest.mark.unit
    def test_sorted_by_confidence_descending(self, vehicle):
        """Results must be sorted by confidence in descending order."""
        db = MagicMock()
        # Return different complaint counts to force different confidence scores
        db.count_complaints.side_effect = [0, 101, 0]

        components = [
            {"component": "exhaust", "count": 1},     # low score (no freq boost)
            {"component": "engine", "count": 50},     # higher (freq boost)
            {"component": "fuel system", "count": 3}, # low score
        ]
        result = score_results(vehicle, components, db)

        confidences = [r["confidence"] for r in result]
        assert confidences == sorted(confidences, reverse=True), (
            f"Results not sorted descending: {confidences}"
        )

    @pytest.mark.unit
    def test_dtc_codes_influence_score(self, vehicle, zero_count_db):
        """Providing a P-code must boost confidence for an engine component."""
        components = [{"component": "engine", "count": 1}]

        without_dtc = score_results(vehicle, components, zero_count_db, dtc_codes=[])
        with_dtc = score_results(vehicle, components, zero_count_db, dtc_codes=["P0300"])

        assert with_dtc[0]["confidence"] > without_dtc[0]["confidence"]

    @pytest.mark.unit
    def test_none_dtc_codes_treated_as_empty(self, vehicle, zero_count_db):
        """dtc_codes=None must behave the same as dtc_codes=[]."""
        components = [{"component": "engine", "count": 1}]
        result_none = score_results(vehicle, components, zero_count_db, dtc_codes=None)
        result_empty = score_results(vehicle, components, zero_count_db, dtc_codes=[])
        assert result_none[0]["confidence"] == result_empty[0]["confidence"]

    @pytest.mark.unit
    def test_safety_critical_component_gets_higher_score(self, vehicle, zero_count_db):
        """Brake component must score higher than non-critical engine (safety bonus)."""
        components = [
            {"component": "engine", "count": 1},
            {"component": "brake system", "count": 1},
        ]
        result = score_results(vehicle, components, zero_count_db)
        brake_conf = next(r["confidence"] for r in result if r["component"] == "brake system")
        engine_conf = next(r["confidence"] for r in result if r["component"] == "engine")
        assert brake_conf > engine_conf

    @pytest.mark.unit
    def test_multiple_components_all_scored(self, vehicle, zero_count_db):
        """Every input component must appear in the output."""
        components = [
            {"component": "engine", "count": 1},
            {"component": "transmission", "count": 2},
            {"component": "fuel system", "count": 3},
        ]
        result = score_results(vehicle, components, zero_count_db)
        assert len(result) == 3

    @pytest.mark.unit
    def test_confidence_values_in_range(self, vehicle, zero_count_db):
        """All confidence scores must be between 0.0 and 1.0 inclusive."""
        components = [
            {"component": "brake system", "count": 10},
            {"component": "engine", "count": 1},
        ]
        result = score_results(vehicle, components, zero_count_db)
        for item in result:
            assert 0.0 <= item["confidence"] <= 1.0, (
                f"Out-of-range confidence for {item['component']}: {item['confidence']}"
            )

    @pytest.mark.unit
    def test_missing_component_key_handled(self, vehicle, zero_count_db):
        """A component dict without a 'component' key must not raise."""
        components = [{"count": 5}]  # no 'component' key
        result = score_results(vehicle, components, zero_count_db)
        assert len(result) == 1
        assert "confidence" in result[0]
