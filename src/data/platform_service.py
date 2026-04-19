"""
Platform family lookup service.

Resolves a vehicle (make/model/year + optional engine code from VIN decode)
to a platform family, then returns all sibling vehicles that share the same
powertrain. Used by engine_agent to expand TSB/complaint searches.

Generalization rules (per DOMAIN.md):
  - ENGINE / POWER TRAIN component types → cross-platform applicable
  - BODY / HVAC / ELECTRICAL → NOT generalizable; ignored here
"""

from __future__ import annotations

import logging
import pathlib
import re
from typing import Any

logger = logging.getLogger(__name__)

_FAMILIES_PATH = (
    pathlib.Path(__file__).resolve().parent.parent.parent / "data" / "platform_families.yaml"
)

# NHTSA component type prefixes where cross-platform generalization is valid
GENERALIZABLE_COMPONENTS = frozenset([
    "ENGINE",
    "ENGINE AND ENGINE COOLING",
    "POWER TRAIN",
    "LUBRICATION",
    "VEHICLE SPEED CONTROL",
    "FUEL SYSTEM",
])


def _load_families() -> list[dict[str, Any]]:
    try:
        import yaml  # type: ignore[import-untyped]
    except ImportError:
        logger.warning("PyYAML not installed — platform family lookup disabled")
        return []
    try:
        text = _FAMILIES_PATH.read_text(encoding="utf-8")
        data = yaml.safe_load(text)
        return data.get("families", [])
    except Exception as exc:
        logger.warning("Could not load platform_families.yaml: %s", exc)
        return []


def _extract_engine_code(engine_model_string: str) -> str:
    """Extract the RPO code prefix from a NHTSA VIN decode Engine Model string.

    Examples:
      "L87 - DI, AFM, ALUM, GEN 5"  → "L87"
      "2GR-FE"                        → "2GR-FE"
      "COYOTE 5.0L TI-VCT"           → "COYOTE"
    """
    if not engine_model_string:
        return ""
    return engine_model_string.split(" - ")[0].split(",")[0].strip().upper()


def _component_is_generalizable(component: str) -> bool:
    """Return True if the NHTSA component type supports platform-wide search."""
    c = component.upper()
    return any(g in c for g in GENERALIZABLE_COMPONENTS)


class PlatformService:
    """Resolve vehicles to platform families for cross-platform diagnostic search."""

    def __init__(self, families_path: str | None = None) -> None:
        if families_path:
            global _FAMILIES_PATH
            _FAMILIES_PATH = pathlib.Path(families_path)
        self._families = _load_families()
        logger.debug("PlatformService loaded %d families", len(self._families))

    def find_family(
        self,
        make: str,
        model: str,
        year: int,
        engine_model: str = "",
        component_type: str = "",
    ) -> dict[str, Any] | None:
        """
        Find the platform family for a vehicle.

        Lookup priority:
          1. engine_model code match (from VIN decode) — most precise
          2. displacement_aliases text match (fallback for manual entry)

        Returns None if no family matches or component_type is not generalizable.
        """
        if component_type and not _component_is_generalizable(component_type):
            return None

        make_up = make.upper()
        model_up = model.upper()
        engine_code = _extract_engine_code(engine_model)

        for family in self._families:
            # Check year range for this vehicle in any member group
            if not self._vehicle_in_family(make_up, model_up, year, family):
                continue

            # Priority 1: engine code match
            if engine_code:
                codes = [c.upper() for c in family.get("engine_codes", [])]
                tx_codes = [c.upper() for c in family.get("transmission_codes", [])]
                if engine_code in codes or engine_code in tx_codes:
                    logger.debug(
                        "Platform match (engine code): %s → %s",
                        engine_code, family["family"],
                    )
                    return family

            # Priority 2: displacement alias match from engine_model string
            em_lower = engine_model.lower()
            for alias in family.get("displacement_aliases", []):
                if alias.lower() in em_lower:
                    logger.debug(
                        "Platform match (alias %r): %s → %s",
                        alias, engine_model, family["family"],
                    )
                    return family

        return None

    def find_family_by_displacement(
        self,
        make: str,
        model: str,
        year: int,
        displacement_hint: str,
        component_type: str = "",
    ) -> dict[str, Any] | None:
        """
        Fallback lookup by displacement text when no VIN/engine_model is available.

        displacement_hint: free-text from user ("6.2L", "5.3 liter V8", "10-speed", etc.)
        """
        if component_type and not _component_is_generalizable(component_type):
            return None

        hint_lower = displacement_hint.lower()
        make_up = make.upper()
        model_up = model.upper()

        for family in self._families:
            if not self._vehicle_in_family(make_up, model_up, year, family):
                continue
            for alias in family.get("displacement_aliases", []):
                if alias.lower() in hint_lower:
                    return family
        return None

    def get_sibling_vehicles(
        self,
        family: dict[str, Any],
        exclude_make: str = "",
        exclude_model: str = "",
    ) -> list[dict[str, str | int | None]]:
        """
        Return all sibling vehicles in the family, optionally excluding the query vehicle.

        Returns list of {make, model, year_from, year_to} dicts.
        """
        siblings = []
        ex_make = exclude_make.upper()
        ex_model = exclude_model.upper()

        for member in family.get("members", []):
            m_make = member["make"].upper()
            for model in member.get("models", []):
                m_model = model.upper()
                if m_make == ex_make and m_model == ex_model:
                    continue
                siblings.append({
                    "make": m_make,
                    "model": m_model,
                    "year_from": member.get("year_from"),
                    "year_to": member.get("year_to"),
                })
        return siblings

    def expand_vehicle_list(
        self,
        make: str,
        model: str,
        year: int,
        engine_model: str = "",
        component_type: str = "",
        displacement_hint: str = "",
    ) -> tuple[str | None, list[dict[str, Any]]]:
        """
        High-level convenience: resolve family + return siblings in one call.

        Returns (family_name, sibling_list).
        family_name is None if no platform family found.
        sibling_list is empty if no family or component not generalizable.
        """
        family = self.find_family(make, model, year, engine_model, component_type)

        if family is None and displacement_hint:
            family = self.find_family_by_displacement(
                make, model, year, displacement_hint, component_type
            )

        if family is None:
            return None, []

        siblings = self.get_sibling_vehicles(family, exclude_make=make, exclude_model=model)
        return family["family"], siblings

    @staticmethod
    def _vehicle_in_family(make: str, model: str, year: int, family: dict[str, Any]) -> bool:
        """Return True if the make/model/year appears in any member group."""
        for member in family.get("members", []):
            if member["make"].upper() != make:
                continue
            models_up = [m.upper() for m in member.get("models", [])]
            if model not in models_up:
                continue
            year_from = member.get("year_from", 0)
            year_to = member.get("year_to", 9999)
            if year_from <= year <= year_to:
                return True
        return False
