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
