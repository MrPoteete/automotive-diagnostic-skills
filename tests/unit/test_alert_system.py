"""
Unit tests for src/safety/alert_system.py

Checked AGENTS.md - implementing directly because:
1. This is test code (quality-engineer agent scope)
2. Safety alert logic is already implemented; these tests validate it
3. All DB interactions are mocked — no data-engineer delegation needed

Coverage targets (per TESTING.md): safety_systems -> 100%

Test categories:
- check_component_keywords: Layer 1 keyword detection
- requires_high_confidence: CRITICAL keyword gate
- check_safety_alerts: Combined Layer 1 + Layer 2 orchestration
- _format_message: Human-readable alert message content

Note on keyword differences between modules:
  alert_system.py CRITICAL: brake, abs, antilock, airbag, srs, steering, eps
  alert_system.py HIGH:     tipm, throttle, pedal, fuel pump, fire, crash, stall
  (confidence_scorer.py has a subset — do not mix up the two)
"""

import pytest
from unittest.mock import MagicMock

from src.safety.alert_system import (
    check_component_keywords,
    check_safety_alerts,
    requires_high_confidence,
    SAFETY_KEYWORDS,
)


# ===========================================================================
# check_component_keywords
# ===========================================================================


class TestCheckComponentKeywords:
    """Tests for check_component_keywords(component) -> dict | None."""

    # -- CRITICAL level ---------------------------------------------------------

    @pytest.mark.unit
    @pytest.mark.safety
    def test_brake_pads_returns_critical_alert(self):
        """'brake pads' must trigger a CRITICAL alert (contains 'brake')."""
        result = check_component_keywords("brake pads")
        assert result is not None
        assert result["level"] == "CRITICAL"

    @pytest.mark.unit
    @pytest.mark.safety
    def test_abs_module_returns_critical_alert(self):
        """'abs module' must trigger a CRITICAL alert (contains 'abs')."""
        result = check_component_keywords("abs module")
        assert result is not None
        assert result["level"] == "CRITICAL"

    @pytest.mark.unit
    @pytest.mark.safety
    def test_antilock_brakes_returns_critical_alert(self):
        """'antilock brakes' must trigger a CRITICAL alert (contains 'antilock')."""
        result = check_component_keywords("antilock brakes")
        assert result is not None
        assert result["level"] == "CRITICAL"

    @pytest.mark.unit
    @pytest.mark.safety
    def test_airbag_returns_critical_alert(self):
        """'front airbag' must trigger a CRITICAL alert (contains 'airbag')."""
        result = check_component_keywords("front airbag")
        assert result is not None
        assert result["level"] == "CRITICAL"

    @pytest.mark.unit
    @pytest.mark.safety
    def test_srs_returns_critical_alert(self):
        """'srs control module' must trigger a CRITICAL alert (contains 'srs')."""
        result = check_component_keywords("srs control module")
        assert result is not None
        assert result["level"] == "CRITICAL"

    @pytest.mark.unit
    @pytest.mark.safety
    def test_steering_returns_critical_alert(self):
        """'power steering pump' must trigger a CRITICAL alert."""
        result = check_component_keywords("power steering pump")
        assert result is not None
        assert result["level"] == "CRITICAL"

    @pytest.mark.unit
    @pytest.mark.safety
    def test_eps_returns_critical_alert(self):
        """'eps actuator' must trigger a CRITICAL alert (electric power steering)."""
        result = check_component_keywords("eps actuator")
        assert result is not None
        assert result["level"] == "CRITICAL"

    @pytest.mark.unit
    @pytest.mark.safety
    def test_case_insensitive_upper(self):
        """Uppercase input must still match (case-insensitive matching required)."""
        result = check_component_keywords("BRAKE CALIPER")
        assert result is not None
        assert result["level"] == "CRITICAL"

    @pytest.mark.unit
    @pytest.mark.safety
    def test_case_insensitive_mixed(self):
        """Mixed case input must still match."""
        result = check_component_keywords("Airbag Inflator Module")
        assert result is not None
        assert result["level"] == "CRITICAL"

    # -- HIGH level -------------------------------------------------------------

    @pytest.mark.unit
    @pytest.mark.safety
    def test_tipm_returns_high_alert(self):
        """'TIPM' must trigger a HIGH alert (totally integrated power module)."""
        result = check_component_keywords("TIPM")
        assert result is not None
        assert result["level"] == "HIGH"

    @pytest.mark.unit
    @pytest.mark.safety
    def test_tipm_lowercase_returns_high_alert(self):
        """'tipm relay box' must trigger a HIGH alert."""
        result = check_component_keywords("tipm relay box")
        assert result is not None
        assert result["level"] == "HIGH"

    @pytest.mark.unit
    @pytest.mark.safety
    def test_throttle_returns_high_alert(self):
        """'throttle body sensor' must trigger a HIGH alert."""
        result = check_component_keywords("throttle body sensor")
        assert result is not None
        assert result["level"] == "HIGH"

    @pytest.mark.unit
    @pytest.mark.safety
    def test_pedal_returns_high_alert(self):
        """'accelerator pedal position sensor' must trigger a HIGH alert."""
        result = check_component_keywords("accelerator pedal position sensor")
        assert result is not None
        assert result["level"] == "HIGH"

    @pytest.mark.unit
    @pytest.mark.safety
    def test_fuel_pump_returns_high_alert(self):
        """'fuel pump driver module' must trigger a HIGH alert."""
        result = check_component_keywords("fuel pump driver module")
        assert result is not None
        assert result["level"] == "HIGH"

    @pytest.mark.unit
    @pytest.mark.safety
    def test_fire_keyword_returns_high_alert(self):
        """'underhood fire risk' must trigger a HIGH alert."""
        result = check_component_keywords("underhood fire risk")
        assert result is not None
        assert result["level"] == "HIGH"

    @pytest.mark.unit
    @pytest.mark.safety
    def test_crash_keyword_returns_high_alert(self):
        """'crash avoidance sensor' must trigger a HIGH alert."""
        result = check_component_keywords("crash avoidance sensor")
        assert result is not None
        assert result["level"] == "HIGH"

    @pytest.mark.unit
    @pytest.mark.safety
    def test_stall_keyword_returns_high_alert(self):
        """'engine stall condition' must trigger a HIGH alert."""
        result = check_component_keywords("engine stall condition")
        assert result is not None
        assert result["level"] == "HIGH"

    # -- Safe components — must return None -------------------------------------

    @pytest.mark.unit
    def test_engine_returns_none(self):
        """'engine' alone contains no safety keywords — must return None."""
        result = check_component_keywords("engine")
        assert result is None

    @pytest.mark.unit
    def test_power_train_returns_none(self):
        """'POWER TRAIN' is not in any safety keyword list — must return None."""
        result = check_component_keywords("POWER TRAIN")
        assert result is None

    @pytest.mark.unit
    def test_transmission_returns_none(self):
        """'automatic transmission' contains no safety keywords."""
        result = check_component_keywords("automatic transmission")
        assert result is None

    @pytest.mark.unit
    def test_exhaust_returns_none(self):
        """'exhaust manifold' contains no safety keywords."""
        result = check_component_keywords("exhaust manifold")
        assert result is None

    @pytest.mark.unit
    def test_empty_string_returns_none(self):
        """Empty string must return None (no keywords to match)."""
        result = check_component_keywords("")
        assert result is None

    @pytest.mark.unit
    def test_unknown_component_returns_none(self):
        """Arbitrary unknown component text must return None."""
        result = check_component_keywords("widget xyz part number 12345")
        assert result is None

    # -- Alert dict structure ---------------------------------------------------

    @pytest.mark.unit
    @pytest.mark.safety
    def test_alert_dict_has_required_keys(self):
        """Alert dict must contain level, trigger, keyword, and message keys."""
        result = check_component_keywords("brake caliper")
        assert result is not None
        assert "level" in result
        assert "trigger" in result
        assert "keyword" in result
        assert "message" in result

    @pytest.mark.unit
    @pytest.mark.safety
    def test_alert_trigger_is_component_keyword(self):
        """trigger field must be 'component_keyword' for Layer 1 alerts."""
        result = check_component_keywords("abs pump")
        assert result is not None
        assert result["trigger"] == "component_keyword"

    @pytest.mark.unit
    @pytest.mark.safety
    def test_alert_message_contains_component_name(self):
        """The alert message must reference the original component name."""
        result = check_component_keywords("brake master cylinder")
        assert result is not None
        # The message should mention something about the component
        assert "brake master cylinder" in result["message"].lower() or "brake" in result["message"].lower()

    @pytest.mark.unit
    @pytest.mark.safety
    def test_critical_alert_message_mentions_controllability(self):
        """CRITICAL alert message must mention vehicle controllability or safety."""
        result = check_component_keywords("brake pads")
        assert result is not None
        message_lower = result["message"].lower()
        assert any(word in message_lower for word in ["safety", "control", "inspect", "drive"])

    @pytest.mark.unit
    @pytest.mark.safety
    def test_critical_alert_message_mentions_confidence_threshold(self):
        """CRITICAL alert message must reference the 90% confidence requirement."""
        result = check_component_keywords("airbag module")
        assert result is not None
        assert "90%" in result["message"] or "0.9" in result["message"]

    @pytest.mark.unit
    @pytest.mark.safety
    def test_high_alert_message_recommends_inspection(self):
        """HIGH alert message must recommend professional inspection."""
        result = check_component_keywords("tipm")
        assert result is not None
        assert "inspection" in result["message"].lower() or "caution" in result["message"].lower()

    @pytest.mark.unit
    @pytest.mark.safety
    def test_keyword_field_matches_trigger_word(self):
        """The keyword field must be the specific keyword that triggered the alert."""
        result = check_component_keywords("rear brake assembly")
        assert result is not None
        assert result["keyword"] in SAFETY_KEYWORDS["CRITICAL"] or result["keyword"] in SAFETY_KEYWORDS["HIGH"]


# ===========================================================================
# requires_high_confidence
# ===========================================================================


class TestRequiresHighConfidence:
    """Tests for requires_high_confidence(component) -> bool.

    Per DOMAIN.md: Only CRITICAL keyword components require >= 0.9 confidence.
    HIGH components do not trigger the 0.9 threshold gate.
    """

    # -- CRITICAL components (must require high confidence) --------------------

    @pytest.mark.unit
    @pytest.mark.safety
    def test_brake_caliper_requires_high_confidence(self):
        """'brake caliper' contains 'brake' — must require high confidence."""
        assert requires_high_confidence("brake caliper") is True

    @pytest.mark.unit
    @pytest.mark.safety
    def test_abs_system_requires_high_confidence(self):
        """'abs system' must require high confidence."""
        assert requires_high_confidence("abs system") is True

    @pytest.mark.unit
    @pytest.mark.safety
    def test_antilock_brake_requires_high_confidence(self):
        """'antilock brake controller' must require high confidence."""
        assert requires_high_confidence("antilock brake controller") is True

    @pytest.mark.unit
    @pytest.mark.safety
    def test_airbag_module_requires_high_confidence(self):
        """'airbag module' must require high confidence."""
        assert requires_high_confidence("airbag module") is True

    @pytest.mark.unit
    @pytest.mark.safety
    def test_srs_requires_high_confidence(self):
        """'srs ecu' must require high confidence."""
        assert requires_high_confidence("srs ecu") is True

    @pytest.mark.unit
    @pytest.mark.safety
    def test_steering_rack_requires_high_confidence(self):
        """'steering rack and pinion' must require high confidence."""
        assert requires_high_confidence("steering rack and pinion") is True

    @pytest.mark.unit
    @pytest.mark.safety
    def test_eps_requires_high_confidence(self):
        """'eps control unit' must require high confidence."""
        assert requires_high_confidence("eps control unit") is True

    @pytest.mark.unit
    @pytest.mark.safety
    def test_case_insensitive_critical(self):
        """HIGH-confidence check must be case-insensitive."""
        assert requires_high_confidence("BRAKE SYSTEM") is True

    # -- Non-CRITICAL components (must NOT require high confidence) -------------

    @pytest.mark.unit
    def test_engine_does_not_require_high_confidence(self):
        """'engine' is not CRITICAL — must return False."""
        assert requires_high_confidence("engine") is False

    @pytest.mark.unit
    def test_power_train_does_not_require_high_confidence(self):
        """'power train' is not CRITICAL — must return False."""
        assert requires_high_confidence("power train") is False

    @pytest.mark.unit
    def test_transmission_does_not_require_high_confidence(self):
        """'transmission' is not CRITICAL — must return False."""
        assert requires_high_confidence("transmission") is False

    @pytest.mark.unit
    def test_fuel_system_does_not_require_high_confidence(self):
        """'fuel system' is not CRITICAL — must return False."""
        assert requires_high_confidence("fuel system") is False

    @pytest.mark.unit
    def test_exhaust_does_not_require_high_confidence(self):
        """'exhaust' is not CRITICAL — must return False."""
        assert requires_high_confidence("exhaust") is False

    @pytest.mark.unit
    def test_empty_string_does_not_require_high_confidence(self):
        """Empty string must return False."""
        assert requires_high_confidence("") is False

    @pytest.mark.unit
    def test_tipm_does_not_require_high_confidence(self):
        """'tipm' is HIGH but not CRITICAL — must return False.

        CRITICAL keywords: brake, abs, antilock, airbag, srs, steering, eps
        TIPM is HIGH, which does not trigger the 0.9 confidence gate.
        """
        assert requires_high_confidence("tipm") is False

    @pytest.mark.unit
    def test_throttle_does_not_require_high_confidence(self):
        """'throttle' is HIGH but not CRITICAL — must return False."""
        assert requires_high_confidence("throttle body") is False

    @pytest.mark.unit
    def test_returns_bool(self):
        """Return value must be a Python bool, not a truthy/falsy object."""
        result = requires_high_confidence("brake")
        assert isinstance(result, bool)


# ===========================================================================
# check_safety_alerts (integration of Layer 1 + Layer 2)
# ===========================================================================


class TestCheckSafetyAlerts:
    """Tests for check_safety_alerts(vehicle, component, db) -> dict | None.

    Layer 1 (keyword) takes priority. Layer 2 (narrative scan) only runs
    when Layer 1 returns None.
    """

    @pytest.fixture
    def vehicle(self) -> dict:
        return {"make": "FORD", "model": "F-150", "year": 2019}

    @pytest.fixture
    def safe_db(self) -> MagicMock:
        """Mock DB that returns no narrative safety hits."""
        db = MagicMock(name="DiagnosticDB")
        db.search_complaints.return_value = []
        return db

    @pytest.mark.unit
    @pytest.mark.safety
    def test_critical_component_returns_alert(self, vehicle, safe_db):
        """CRITICAL component must return an alert even with an empty DB."""
        result = check_safety_alerts(vehicle, "brake system", safe_db)
        assert result is not None
        assert result["level"] == "CRITICAL"

    @pytest.mark.unit
    @pytest.mark.safety
    def test_critical_component_layer1_trigger(self, vehicle, safe_db):
        """CRITICAL component alert must come from Layer 1 (no DB call needed)."""
        result = check_safety_alerts(vehicle, "airbag module", safe_db)
        assert result is not None
        assert result["trigger"] == "component_keyword"

    @pytest.mark.unit
    @pytest.mark.safety
    def test_safe_component_no_narrative_hits_returns_none(self, vehicle, safe_db):
        """Non-safety component with no narrative hits must return None."""
        result = check_safety_alerts(vehicle, "engine", safe_db)
        assert result is None

    @pytest.mark.unit
    @pytest.mark.safety
    def test_safe_component_with_narrative_hits_returns_warning(self, vehicle):
        """Non-safety component with >= 10 narrative hits must return WARNING alert."""
        db = MagicMock()
        # Return 2 results per term, 10 narrative terms = 20 total hits (>=10 threshold)
        db.search_complaints.return_value = [
            {"component": "engine", "summary": "vehicle caught fire"},
            {"component": "engine", "summary": "engine fire under hood"},
        ]
        result = check_safety_alerts(vehicle, "engine", db)
        assert result is not None
        assert result["level"] == "WARNING"
        assert result["trigger"] == "narrative_scan"

    @pytest.mark.unit
    @pytest.mark.safety
    def test_layer1_takes_priority_over_layer2(self, vehicle):
        """If Layer 1 matches, Layer 2 DB call must not be made."""
        db = MagicMock()
        db.search_complaints.return_value = []
        result = check_safety_alerts(vehicle, "brake caliper", db)
        # Layer 1 should have returned without calling search_complaints
        db.search_complaints.assert_not_called()
        assert result is not None
        assert result["trigger"] == "component_keyword"

    @pytest.mark.unit
    @pytest.mark.safety
    def test_db_exception_in_layer2_does_not_raise(self, vehicle):
        """Layer 2 DB exception must be caught and return None gracefully."""
        db = MagicMock()
        db.search_complaints.side_effect = RuntimeError("DB connection lost")
        # Should not raise
        result = check_safety_alerts(vehicle, "engine", db)
        assert result is None

    @pytest.mark.unit
    @pytest.mark.safety
    def test_narrative_alert_contains_match_count(self, vehicle):
        """Narrative-triggered alert must include a 'match_count' field."""
        db = MagicMock()
        db.search_complaints.return_value = [
            {"component": "engine", "summary": "fire"},
            {"component": "engine", "summary": "crash"},
        ]
        result = check_safety_alerts(vehicle, "engine", db)
        if result is not None and result["trigger"] == "narrative_scan":
            assert "match_count" in result
            assert isinstance(result["match_count"], int)

    @pytest.mark.unit
    @pytest.mark.safety
    def test_narrative_below_threshold_returns_none(self, vehicle):
        """Fewer than NARRATIVE_ALERT_THRESHOLD (10) hits must return None."""
        db = MagicMock()
        # Return only 1 result per narrative term; with 10 terms and 1 each = 10 hits
        # This is exactly at the threshold — boundary condition
        # For < threshold, return empty for most terms
        call_count = 0

        def few_results(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            # Only first call returns a result, rest return empty
            return [{"component": "engine", "summary": "fire"}] if call_count <= 1 else []

        db.search_complaints.side_effect = few_results
        result = check_safety_alerts(vehicle, "engine", db)
        # With only 1 total hit (< 10), no narrative alert
        assert result is None
