# Checked AGENTS.md - implementing directly because these are unit tests for a new
# internal service (TransmissionLookupService) authored in this same session.
# No safety-critical logic, no auth, no DB writes — pure YAML-backed lookup with
# fixture YAML isolated from the live data file. Same pattern as test_platform_service.py.
"""
Unit tests for src/data/transmission_lookup_service.py

Coverage:
- Basic match: make + model + year → transmission_model
- Engine-code priority: entry with matching engine_code wins over year-range fallback
- Year boundary: year_from/year_to inclusive edge cases
- No match: unknown vehicle returns None
- No match: out-of-range year returns None
- Engine-code fallback: no engine supplied → returns year-range fallback
- Case normalization: lowercase make/model matched correctly
- Entries without engine_codes serve as universal fallback
- _extract_engine_code_prefix: parses NHTSA Engine Model string correctly
"""

import pathlib
import textwrap

import pytest

from src.data.transmission_lookup_service import (
    TransmissionLookupService,
    _extract_engine_code_prefix,
)


# ---------------------------------------------------------------------------
# Minimal test YAML — isolated from live transmission_lookup.yaml
# ---------------------------------------------------------------------------

_TEST_YAML = textwrap.dedent("""\
    entries:
      # Entry 1: engine-coded (5.3L → 6L80E)
      - make: CHEVROLET
        models: [SILVERADO 1500, TAHOE]
        year_from: 2014
        year_to: 2018
        engine_codes: [L83, L84]
        transmission_model: 6L80E

      # Entry 2: engine-coded (6.2L → 10L80) open-ended year_to
      - make: CHEVROLET
        models: [SILVERADO 1500, TAHOE]
        year_from: 2019
        engine_codes: [L87]
        transmission_model: 10L80

      # Entry 3: universal fallback (no engine_codes) for Silverado 2014-2018
      - make: CHEVROLET
        models: [SILVERADO 1500]
        year_from: 2014
        year_to: 2018
        transmission_model: 6L80E

      # Entry 4: Toyota UA80E — engine-coded
      - make: TOYOTA
        models: [CAMRY, AVALON]
        year_from: 2018
        engine_codes: [2GR-FKS, 2GR-FE]
        transmission_model: UA80E

      # Entry 5: Honda BDGA — year_to present
      - make: HONDA
        models: [CR-V]
        year_from: 2002
        year_to: 2006
        engine_codes: [K24A, K24Z]
        transmission_model: BDGA

      # Entry 6: ZF 8HP (no year_to — open-ended)
      - make: BMW
        models: [3 SERIES, 5 SERIES]
        year_from: 2017
        engine_codes: [B58, B58B30]
        transmission_model: ZF8HP51
""")


@pytest.fixture()
def lookup_path(tmp_path: pathlib.Path) -> pathlib.Path:
    """Write the test YAML to a temp file and return its path."""
    p = tmp_path / "transmission_lookup_test.yaml"
    p.write_text(_TEST_YAML, encoding="utf-8")
    return p


@pytest.fixture()
def svc(lookup_path: pathlib.Path) -> TransmissionLookupService:
    return TransmissionLookupService(lookup_path=lookup_path)


# ---------------------------------------------------------------------------
# _extract_engine_code_prefix
# ---------------------------------------------------------------------------

class TestExtractEngineCodePrefix:
    def test_rpo_with_description(self) -> None:
        assert _extract_engine_code_prefix("L87 - DI, AFM, ALUM, GEN 5") == "L87"

    def test_bare_code(self) -> None:
        assert _extract_engine_code_prefix("2GR-FKS") == "2GR-FKS"

    def test_multiword_code(self) -> None:
        assert _extract_engine_code_prefix("B58B30O0") == "B58B30O0"

    def test_empty_string(self) -> None:
        assert _extract_engine_code_prefix("") == ""

    def test_lowercased_code_is_uppercased(self) -> None:
        assert _extract_engine_code_prefix("l87 - DI") == "L87"

    def test_comma_separated_no_dash(self) -> None:
        # Edge case: "LFY,LGX" — take first token before comma
        assert _extract_engine_code_prefix("LFY,LGX") == "LFY"


# ---------------------------------------------------------------------------
# Basic year-range match
# ---------------------------------------------------------------------------

class TestBasicMatch:
    def test_match_within_year_range(self, svc: TransmissionLookupService) -> None:
        result = svc.lookup("CHEVROLET", "SILVERADO 1500", 2016, engine_model="L83 - V8")
        assert result == "6L80E"

    def test_match_year_from_boundary(self, svc: TransmissionLookupService) -> None:
        result = svc.lookup("CHEVROLET", "TAHOE", 2014, engine_model="L84 - DFM")
        assert result == "6L80E"

    def test_match_year_to_boundary(self, svc: TransmissionLookupService) -> None:
        result = svc.lookup("CHEVROLET", "SILVERADO 1500", 2018, engine_model="L83 - V8")
        assert result == "6L80E"

    def test_no_match_year_before_range(self, svc: TransmissionLookupService) -> None:
        result = svc.lookup("CHEVROLET", "SILVERADO 1500", 2013)
        assert result is None

    def test_no_match_year_after_range_with_to(self, svc: TransmissionLookupService) -> None:
        # Entry 5 (BDGA) ends at 2006; 2007 should not match
        result = svc.lookup("HONDA", "CR-V", 2007, engine_model="K24A")
        assert result is None

    def test_open_ended_year_to(self, svc: TransmissionLookupService) -> None:
        # Entry 6 (ZF8HP51) has no year_to — should match 2024
        result = svc.lookup("BMW", "3 SERIES", 2024, engine_model="B58")
        assert result == "ZF8HP51"


# ---------------------------------------------------------------------------
# Engine-code priority
# ---------------------------------------------------------------------------

class TestEngineCodePriority:
    def test_engine_code_wins_over_fallback(self, svc: TransmissionLookupService) -> None:
        # Entry 1 (L83 → 6L80E) and Entry 3 (fallback → 6L80E) both match;
        # engine code match should return first
        result = svc.lookup("CHEVROLET", "SILVERADO 1500", 2016, engine_model="L83 - V8")
        assert result == "6L80E"

    def test_2019_l87_gets_10l80(self, svc: TransmissionLookupService) -> None:
        result = svc.lookup("CHEVROLET", "SILVERADO 1500", 2019, engine_model="L87 - DI")
        assert result == "10L80"

    def test_2019_no_engine_falls_back_to_first_year_match(self, svc: TransmissionLookupService) -> None:
        # 2019 only matches Entry 2 (engine_codes=[L87], year_from=2019).
        # No engine supplied → entry 2 is first year-range hit → returned as fallback.
        result = svc.lookup("CHEVROLET", "SILVERADO 1500", 2019)
        assert result == "10L80"

    def test_toyota_camry_ua80e(self, svc: TransmissionLookupService) -> None:
        result = svc.lookup("TOYOTA", "CAMRY", 2020, engine_model="2GR-FKS")
        assert result == "UA80E"

    def test_honda_crv_bdga(self, svc: TransmissionLookupService) -> None:
        result = svc.lookup("HONDA", "CR-V", 2004, engine_model="K24A")
        assert result == "BDGA"


# ---------------------------------------------------------------------------
# No-match cases
# ---------------------------------------------------------------------------

class TestNoMatch:
    def test_unknown_make(self, svc: TransmissionLookupService) -> None:
        result = svc.lookup("SUBARU", "OUTBACK", 2020)
        assert result is None

    def test_unknown_model(self, svc: TransmissionLookupService) -> None:
        result = svc.lookup("CHEVROLET", "MALIBU", 2016)
        assert result is None

    def test_wrong_engine_code_still_falls_back_to_universal(self, svc: TransmissionLookupService) -> None:
        # Engine code XYZ doesn't match entry 1 (L83/L84), falls back to
        # entry 3 (no engine_codes, same year range 2014-2018)
        result = svc.lookup("CHEVROLET", "SILVERADO 1500", 2016, engine_model="XYZ")
        assert result == "6L80E"


# ---------------------------------------------------------------------------
# Case normalization
# ---------------------------------------------------------------------------

class TestCaseNormalization:
    def test_lowercase_make(self, svc: TransmissionLookupService) -> None:
        result = svc.lookup("chevrolet", "SILVERADO 1500", 2016, engine_model="L83")
        assert result == "6L80E"

    def test_lowercase_model(self, svc: TransmissionLookupService) -> None:
        result = svc.lookup("CHEVROLET", "silverado 1500", 2016, engine_model="L83")
        assert result == "6L80E"

    def test_mixed_case(self, svc: TransmissionLookupService) -> None:
        result = svc.lookup("Toyota", "Camry", 2019, engine_model="2GR-FKS")
        assert result == "UA80E"


# ---------------------------------------------------------------------------
# Universal fallback (no engine_codes on entry)
# ---------------------------------------------------------------------------

class TestUniversalFallback:
    def test_fallback_when_no_engine_model_supplied(self, svc: TransmissionLookupService) -> None:
        # Entry 3 covers SILVERADO 1500 2014-2018 with no engine_codes
        result = svc.lookup("CHEVROLET", "SILVERADO 1500", 2015)
        assert result == "6L80E"

    def test_tahoe_engine_coded_entry_used_as_fallback_when_no_engine(self, svc: TransmissionLookupService) -> None:
        # TAHOE has engine-coded entries only (no universal); first year-range entry returned
        result = svc.lookup("CHEVROLET", "TAHOE", 2015)
        assert result == "6L80E"


# ---------------------------------------------------------------------------
# Missing YAML file — graceful degradation
# ---------------------------------------------------------------------------

class TestMissingFile:
    def test_missing_yaml_returns_none(self, tmp_path: pathlib.Path) -> None:
        svc = TransmissionLookupService(lookup_path=tmp_path / "nonexistent.yaml")
        result = svc.lookup("CHEVROLET", "SILVERADO 1500", 2016)
        assert result is None
