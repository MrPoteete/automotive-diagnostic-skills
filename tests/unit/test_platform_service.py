"""
Unit tests for src/data/platform_service.py

Coverage:
- PlatformService.find_family: engine code match, alias match, no match, non-generalizable component
- PlatformService.get_sibling_vehicles: excludes query vehicle, returns all siblings
- PlatformService.expand_vehicle_list: end-to-end convenience method
- _extract_engine_code: code prefix extraction from NHTSA Engine Model strings
- _component_is_generalizable: component type filter
"""

import pathlib
import textwrap

import pytest

from src.data.platform_service import (
    PlatformService,
    _component_is_generalizable,
    _extract_engine_code,
)


# ---------------------------------------------------------------------------
# Minimal test YAML — isolated from the live platform_families.yaml
# ---------------------------------------------------------------------------

_TEST_YAML = textwrap.dedent("""\
    families:
      - family: GM Gen V 6.2L V8
        engine_codes: [L87, LT1]
        displacement_aliases: ["6.2l", "6.2 liter", "l87"]
        component_types:
          - ENGINE AND ENGINE COOLING
          - POWER TRAIN
        members:
          - make: CHEVROLET
            models: [SILVERADO 1500, TAHOE, CAMARO]
            year_from: 2014
          - make: GMC
            models: [SIERRA 1500, YUKON]
            year_from: 2014

      - family: GM 10-Speed Automatic (10L80/10L90)
        engine_codes: []
        transmission_codes: [10L80, 10L90]
        displacement_aliases: ["10l80", "10-speed"]
        component_types:
          - POWER TRAIN
        members:
          - make: CHEVROLET
            models: [SILVERADO 1500, TAHOE]
            year_from: 2019
          - make: GMC
            models: [SIERRA 1500]
            year_from: 2019
""")


@pytest.fixture
def yaml_path(tmp_path: pathlib.Path) -> pathlib.Path:
    p = tmp_path / "platform_families.yaml"
    p.write_text(_TEST_YAML)
    return p


@pytest.fixture
def svc(yaml_path: pathlib.Path) -> PlatformService:
    return PlatformService(families_path=str(yaml_path))


# ===========================================================================
# _extract_engine_code
# ===========================================================================

class TestExtractEngineCode:
    @pytest.mark.unit
    def test_gm_rpo_with_descriptor(self):
        assert _extract_engine_code("L87 - DI, AFM, ALUM, GEN 5") == "L87"

    @pytest.mark.unit
    def test_bare_code(self):
        assert _extract_engine_code("2GR-FE") == "2GR-FE"

    @pytest.mark.unit
    def test_empty_string(self):
        assert _extract_engine_code("") == ""

    @pytest.mark.unit
    def test_comma_separated(self):
        assert _extract_engine_code("LT1, SOME VARIANT") == "LT1"


# ===========================================================================
# _component_is_generalizable
# ===========================================================================

class TestComponentIsGeneralizable:
    @pytest.mark.unit
    @pytest.mark.parametrize("component", [
        "ENGINE AND ENGINE COOLING",
        "ENGINE",
        "POWER TRAIN",
        "LUBRICATION",
        "VEHICLE SPEED CONTROL",
        "FUEL SYSTEM",
    ])
    def test_generalizable_types(self, component: str):
        assert _component_is_generalizable(component) is True

    @pytest.mark.unit
    @pytest.mark.parametrize("component", [
        "BODY",
        "AIR BAGS",
        "ELECTRICAL SYSTEM",
        "HVAC",
        "SEATS",
        "EXTERIOR LIGHTING",
    ])
    def test_non_generalizable_types(self, component: str):
        assert _component_is_generalizable(component) is False


# ===========================================================================
# PlatformService.find_family
# ===========================================================================

class TestFindFamily:
    @pytest.mark.unit
    def test_engine_code_match(self, svc: PlatformService):
        family = svc.find_family(
            make="CHEVROLET", model="SILVERADO 1500", year=2021,
            engine_model="L87 - DI, AFM, ALUM, GEN 5",
        )
        assert family is not None
        assert family["family"] == "GM Gen V 6.2L V8"

    @pytest.mark.unit
    def test_alias_fallback_match(self, svc: PlatformService):
        family = svc.find_family(
            make="CHEVROLET", model="TAHOE", year=2020,
            engine_model="6.2L V8",  # no RPO code, but alias matches
        )
        assert family is not None
        assert family["family"] == "GM Gen V 6.2L V8"

    @pytest.mark.unit
    def test_no_match_wrong_make(self, svc: PlatformService):
        family = svc.find_family(
            make="FORD", model="F-150", year=2021,
            engine_model="L87 - DI, AFM, ALUM, GEN 5",
        )
        assert family is None

    @pytest.mark.unit
    def test_no_match_year_out_of_range(self, svc: PlatformService):
        family = svc.find_family(
            make="CHEVROLET", model="SILVERADO 1500", year=2010,
            engine_model="L87 - DI",
        )
        assert family is None

    @pytest.mark.unit
    def test_non_generalizable_component_returns_none(self, svc: PlatformService):
        family = svc.find_family(
            make="CHEVROLET", model="SILVERADO 1500", year=2021,
            engine_model="L87 - DI, AFM, ALUM, GEN 5",
            component_type="BODY",
        )
        assert family is None

    @pytest.mark.unit
    def test_generalizable_component_allowed(self, svc: PlatformService):
        family = svc.find_family(
            make="CHEVROLET", model="SILVERADO 1500", year=2021,
            engine_model="L87 - DI",
            component_type="ENGINE AND ENGINE COOLING",
        )
        assert family is not None


# ===========================================================================
# PlatformService.get_sibling_vehicles
# ===========================================================================

class TestGetSiblingVehicles:
    @pytest.mark.unit
    def test_excludes_query_vehicle(self, svc: PlatformService):
        family = svc.find_family("CHEVROLET", "SILVERADO 1500", 2021, "L87 - DI")
        assert family is not None
        siblings = svc.get_sibling_vehicles(family, exclude_make="CHEVROLET", exclude_model="SILVERADO 1500")
        names = [(s["make"], s["model"]) for s in siblings]
        assert ("CHEVROLET", "SILVERADO 1500") not in names

    @pytest.mark.unit
    def test_includes_cross_brand_siblings(self, svc: PlatformService):
        family = svc.find_family("CHEVROLET", "SILVERADO 1500", 2021, "L87 - DI")
        assert family is not None
        siblings = svc.get_sibling_vehicles(family, exclude_make="CHEVROLET", exclude_model="SILVERADO 1500")
        makes = {s["make"] for s in siblings}
        assert "GMC" in makes

    @pytest.mark.unit
    def test_year_from_preserved(self, svc: PlatformService):
        family = svc.find_family("CHEVROLET", "SILVERADO 1500", 2021, "L87 - DI")
        assert family is not None
        siblings = svc.get_sibling_vehicles(family)
        for s in siblings:
            assert s["year_from"] is not None


# ===========================================================================
# PlatformService.expand_vehicle_list
# ===========================================================================

class TestExpandVehicleList:
    @pytest.mark.unit
    def test_full_match_returns_family_and_siblings(self, svc: PlatformService):
        name, siblings = svc.expand_vehicle_list(
            make="CHEVROLET", model="SILVERADO 1500", year=2021,
            engine_model="L87 - DI, AFM",
            component_type="ENGINE AND ENGINE COOLING",
        )
        assert name == "GM Gen V 6.2L V8"
        assert len(siblings) > 0

    @pytest.mark.unit
    def test_no_match_returns_none_and_empty(self, svc: PlatformService):
        name, siblings = svc.expand_vehicle_list(
            make="TOYOTA", model="CAMRY", year=2021,
            engine_model="2AR-FE",
        )
        assert name is None
        assert siblings == []

    @pytest.mark.unit
    def test_displacement_hint_fallback(self, svc: PlatformService):
        # No engine_model, but displacement_hint in symptoms
        name, siblings = svc.expand_vehicle_list(
            make="CHEVROLET", model="TAHOE", year=2020,
            engine_model="",
            component_type="ENGINE AND ENGINE COOLING",
            displacement_hint="engine knocking on the 6.2L V8",
        )
        assert name == "GM Gen V 6.2L V8"
        assert len(siblings) > 0

    @pytest.mark.unit
    def test_non_generalizable_component_returns_empty(self, svc: PlatformService):
        name, siblings = svc.expand_vehicle_list(
            make="CHEVROLET", model="SILVERADO 1500", year=2021,
            engine_model="L87 - DI",
            component_type="EXTERIOR LIGHTING",
        )
        assert name is None
        assert siblings == []


# ===========================================================================
# New platform families — BMW B47/B58, Honda BDGA/MPYA, Toyota UA80
# These tests use the live platform_families.yaml (no inline fixture needed).
# ===========================================================================

_LIVE_YAML = (
    pathlib.Path(__file__).resolve().parent.parent.parent
    / "data"
    / "platform_families.yaml"
)


@pytest.fixture
def live_svc() -> PlatformService:
    return PlatformService(families_path=str(_LIVE_YAML))


# ---------------------------------------------------------------------------
# BMW B47/B58 Powertrain
# ---------------------------------------------------------------------------

class TestBMWB47B58Family:
    @pytest.mark.unit
    def test_engine_code_b58_match(self, live_svc: PlatformService):
        family = live_svc.find_family(
            make="BMW", model="3 SERIES", year=2020,
            engine_model="B58B30",
        )
        assert family is not None
        assert family["family"] == "BMW B47/B58 Powertrain"

    @pytest.mark.unit
    def test_engine_code_b47_match(self, live_svc: PlatformService):
        family = live_svc.find_family(
            make="BMW", model="X3", year=2019,
            engine_model="B47D20",
        )
        assert family is not None
        assert family["family"] == "BMW B47/B58 Powertrain"

    @pytest.mark.unit
    def test_alias_diesel_match(self, live_svc: PlatformService):
        family = live_svc.find_family(
            make="BMW", model="5 SERIES", year=2021,
            engine_model="2.0l diesel",
        )
        assert family is not None
        assert family["family"] == "BMW B47/B58 Powertrain"

    @pytest.mark.unit
    def test_toyota_supra_is_sibling(self, live_svc: PlatformService):
        family = live_svc.find_family(
            make="BMW", model="Z4", year=2021,
            engine_model="B58B30",
        )
        assert family is not None
        siblings = live_svc.get_sibling_vehicles(family, exclude_make="BMW", exclude_model="Z4")
        makes = {s["make"] for s in siblings}
        assert "TOYOTA" in makes

    @pytest.mark.unit
    def test_no_match_wrong_year(self, live_svc: PlatformService):
        # B47/B58 introduced 2014; pre-2014 should not match
        family = live_svc.find_family(
            make="BMW", model="3 SERIES", year=2012,
            engine_model="B58B30",
        )
        assert family is None

    @pytest.mark.unit
    def test_non_generalizable_body_component_blocked(self, live_svc: PlatformService):
        family = live_svc.find_family(
            make="BMW", model="X5", year=2022,
            engine_model="B58B30",
            component_type="BODY",
        )
        assert family is None

    @pytest.mark.unit
    def test_fuel_system_component_generalizable(self, live_svc: PlatformService):
        # HPFP failures are FUEL SYSTEM — must be generalizable for this family
        family = live_svc.find_family(
            make="BMW", model="X5", year=2022,
            engine_model="B58B30",
            component_type="FUEL SYSTEM",
        )
        assert family is not None

    @pytest.mark.unit
    def test_expand_vehicle_list_returns_siblings(self, live_svc: PlatformService):
        name, siblings = live_svc.expand_vehicle_list(
            make="BMW", model="5 SERIES", year=2021,
            engine_model="B58B30",
            component_type="ENGINE AND ENGINE COOLING",
        )
        assert name == "BMW B47/B58 Powertrain"
        assert len(siblings) > 0
        # Query vehicle excluded
        assert not any(
            s["make"] == "BMW" and s["model"] == "5 SERIES" for s in siblings
        )


# ---------------------------------------------------------------------------
# Honda BDGA/MPYA 4-Speed Automatic
# ---------------------------------------------------------------------------

class TestHondaBDGAFamily:
    @pytest.mark.unit
    def test_transmission_code_bdga_match(self, live_svc: PlatformService):
        family = live_svc.find_family(
            make="HONDA", model="CR-V", year=2005,
            engine_model="BDGA",
        )
        assert family is not None
        assert family["family"] == "Honda BDGA/MPYA 4-Speed Automatic"

    @pytest.mark.unit
    def test_transmission_code_mpya_match(self, live_svc: PlatformService):
        family = live_svc.find_family(
            make="HONDA", model="ACCORD", year=2004,
            engine_model="MPYA",
        )
        assert family is not None
        assert family["family"] == "Honda BDGA/MPYA 4-Speed Automatic"

    @pytest.mark.unit
    def test_acura_tsx_in_family(self, live_svc: PlatformService):
        family = live_svc.find_family(
            make="ACURA", model="TSX", year=2006,
            engine_model="BDGA",
        )
        assert family is not None
        assert family["family"] == "Honda BDGA/MPYA 4-Speed Automatic"

    @pytest.mark.unit
    def test_no_match_year_too_new(self, live_svc: PlatformService):
        # year_to is 2007 for HONDA members; 2009 should not match
        family = live_svc.find_family(
            make="HONDA", model="CR-V", year=2009,
            engine_model="BDGA",
        )
        assert family is None

    @pytest.mark.unit
    def test_no_match_year_too_old(self, live_svc: PlatformService):
        family = live_svc.find_family(
            make="HONDA", model="ACCORD", year=2001,
            engine_model="MPYA",
        )
        assert family is None

    @pytest.mark.unit
    def test_honda_element_is_member(self, live_svc: PlatformService):
        family = live_svc.find_family(
            make="HONDA", model="ELEMENT", year=2004,
            engine_model="BDGA",
        )
        assert family is not None

    @pytest.mark.unit
    def test_cross_brand_siblings_include_acura(self, live_svc: PlatformService):
        family = live_svc.find_family(
            make="HONDA", model="CR-V", year=2005,
            engine_model="BDGA",
        )
        assert family is not None
        siblings = live_svc.get_sibling_vehicles(family, exclude_make="HONDA", exclude_model="CR-V")
        makes = {s["make"] for s in siblings}
        assert "ACURA" in makes

    @pytest.mark.unit
    def test_expand_vehicle_list_power_train(self, live_svc: PlatformService):
        name, siblings = live_svc.expand_vehicle_list(
            make="HONDA", model="ACCORD", year=2005,
            engine_model="MPYA",
            component_type="POWER TRAIN",
        )
        assert name == "Honda BDGA/MPYA 4-Speed Automatic"
        assert len(siblings) > 0


# ---------------------------------------------------------------------------
# Toyota UA80 8-Speed Automatic
# ---------------------------------------------------------------------------

class TestToyotaUA80Family:
    @pytest.mark.unit
    def test_transmission_code_ua80e_match(self, live_svc: PlatformService):
        family = live_svc.find_family(
            make="TOYOTA", model="CAMRY", year=2020,
            engine_model="UA80E",
        )
        assert family is not None
        assert family["family"] == "Toyota UA80 8-Speed Automatic"

    @pytest.mark.unit
    def test_transmission_code_ua80f_match(self, live_svc: PlatformService):
        family = live_svc.find_family(
            make="TOYOTA", model="RAV4", year=2021,
            engine_model="UA80F",
        )
        assert family is not None
        assert family["family"] == "Toyota UA80 8-Speed Automatic"

    @pytest.mark.unit
    def test_alias_8speed_match(self, live_svc: PlatformService):
        family = live_svc.find_family(
            make="TOYOTA", model="AVALON", year=2022,
            engine_model="8-speed automatic",
        )
        assert family is not None
        assert family["family"] == "Toyota UA80 8-Speed Automatic"

    @pytest.mark.unit
    def test_toyota_crown_is_member(self, live_svc: PlatformService):
        family = live_svc.find_family(
            make="TOYOTA", model="CROWN", year=2023,
            engine_model="UA80E",
        )
        assert family is not None

    @pytest.mark.unit
    def test_toyota_venza_is_member(self, live_svc: PlatformService):
        family = live_svc.find_family(
            make="TOYOTA", model="VENZA", year=2022,
            engine_model="UA80E",
        )
        assert family is not None

    @pytest.mark.unit
    def test_no_match_year_too_old(self, live_svc: PlatformService):
        # year_from is 2018
        family = live_svc.find_family(
            make="TOYOTA", model="CAMRY", year=2017,
            engine_model="UA80E",
        )
        assert family is None

    @pytest.mark.unit
    def test_sibling_includes_avalon_when_querying_camry(self, live_svc: PlatformService):
        family = live_svc.find_family(
            make="TOYOTA", model="CAMRY", year=2020,
            engine_model="UA80E",
        )
        assert family is not None
        siblings = live_svc.get_sibling_vehicles(family, exclude_make="TOYOTA", exclude_model="CAMRY")
        models = {s["model"] for s in siblings}
        assert "AVALON" in models

    @pytest.mark.unit
    def test_expand_vehicle_list_returns_correct_family(self, live_svc: PlatformService):
        name, siblings = live_svc.expand_vehicle_list(
            make="TOYOTA", model="RAV4", year=2022,
            engine_model="UA80F",
            component_type="POWER TRAIN",
        )
        assert name == "Toyota UA80 8-Speed Automatic"
        assert len(siblings) > 0
        # RAV4 itself excluded
        assert not any(
            s["make"] == "TOYOTA" and s["model"] == "RAV4" for s in siblings
        )
