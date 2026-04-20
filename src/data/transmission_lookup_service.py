"""
Transmission model lookup service.

Infers a transmission model code (e.g. "6L80E", "UA80E", "ZF8HP51") from
(make, model, year, optional engine_model) when the VIN decode does not include
a transmission field.  Used by PlatformService to match transmission-based
platform families (Honda BDGA/MPYA, Toyota UA80, Ford 10R80, GM 10L80, etc.).

Match priority (highest wins):
  1. make + model + year + engine_code prefix match → strongest signal
  2. make + model + year only                       → fallback
  3. No match                                       → returns None

Entries are evaluated top-to-bottom in the YAML file; the first match wins.
More-specific entries (with engine_codes) should appear before less-specific
entries for the same make/model/year range.
"""

from __future__ import annotations

import logging
import pathlib
from typing import Any

logger = logging.getLogger(__name__)

_DEFAULT_LOOKUP_PATH = (
    pathlib.Path(__file__).resolve().parent.parent.parent
    / "data"
    / "transmission_lookup.yaml"
)


def _load_entries(lookup_path: pathlib.Path) -> list[dict[str, Any]]:
    """Load and return the list of lookup entries from YAML."""
    try:
        import yaml  # type: ignore[import-untyped]
    except ImportError:
        logger.warning("PyYAML not installed — transmission lookup disabled")
        return []
    try:
        text = lookup_path.read_text(encoding="utf-8")
        data = yaml.safe_load(text)
        return data.get("entries", [])
    except Exception as exc:
        logger.warning("Could not load transmission_lookup.yaml: %s", exc)
        return []


def _extract_engine_code_prefix(engine_model: str) -> str:
    """Extract the RPO code prefix from a NHTSA VIN decode Engine Model string.

    Mirrors the same logic used in platform_service._extract_engine_code().

    Examples:
      "L87 - DI, AFM, ALUM, GEN 5"  → "L87"
      "2GR-FKS"                       → "2GR-FKS"
      "B58B30O0"                      → "B58B30O0"
    """
    if not engine_model:
        return ""
    return engine_model.split(" - ")[0].split(",")[0].strip().upper()


class TransmissionLookupService:
    """Infer transmission model code from vehicle identity."""

    def __init__(self, lookup_path: pathlib.Path | str | None = None) -> None:
        if lookup_path is not None:
            path = pathlib.Path(lookup_path)
        else:
            path = _DEFAULT_LOOKUP_PATH
        self._entries = _load_entries(path)
        logger.debug(
            "TransmissionLookupService loaded %d entries from %s",
            len(self._entries),
            path,
        )

    def lookup(
        self,
        make: str,
        model: str,
        year: int,
        engine_model: str | None = None,
    ) -> str | None:
        """Return transmission model code or None if unknown.

        Parameters
        ----------
        make:
            Vehicle make in any case (will be uppercased for matching).
        model:
            Vehicle model in any case (will be uppercased for matching).
        year:
            Four-digit model year.
        engine_model:
            NHTSA VIN decode "Engine Model" string (e.g. "L87 - DI, AFM …").
            Optional; when present enables engine-code-priority matching.

        Returns
        -------
        str | None
            Transmission model code string (e.g. "6L80E") or None.
        """
        make_up = make.strip().upper()
        model_up = model.strip().upper()
        engine_code = _extract_engine_code_prefix(engine_model or "")

        # Two-pass strategy:
        #   Pass 1 — entries that have engine_codes; match only if engine_code present.
        #   Pass 2 — all entries; match on make/model/year only (fallback).
        # This preserves the "engine_code match wins" priority while still allowing
        # a year-range fallback when no engine code is available.

        best_fallback: str | None = None

        for entry in self._entries:
            if entry.get("make", "").upper() != make_up:
                continue

            models_up = [m.upper() for m in entry.get("models", [])]
            if model_up not in models_up:
                continue

            year_from: int = entry.get("year_from", 0)
            year_to: int = entry.get("year_to", 9999)
            if not (year_from <= year <= year_to):
                continue

            tx_model: str = entry.get("transmission_model", "")
            if not tx_model:
                continue

            entry_codes: list[str] = [c.upper() for c in entry.get("engine_codes", [])]

            # Priority 1: engine_code match
            if engine_code and entry_codes and engine_code in entry_codes:
                logger.debug(
                    "Transmission match (engine code %s): %s %s %d → %s",
                    engine_code, make_up, model_up, year, tx_model,
                )
                return tx_model

            # Candidate for fallback — first year-range hit with no engine_codes (or
            # engine_codes present but our code didn't match yet).
            if best_fallback is None:
                if not entry_codes:
                    # Entries without engine_codes are universal fallbacks.
                    best_fallback = tx_model
                elif not engine_code:
                    # No engine_code supplied; treat first engine-coded entry as fallback.
                    best_fallback = tx_model

        if best_fallback is not None:
            logger.debug(
                "Transmission match (year-range fallback): %s %s %d → %s",
                make_up, model_up, year, best_fallback,
            )
        else:
            logger.debug(
                "No transmission match for %s %s %d (engine=%r)",
                make_up, model_up, year, engine_model,
            )

        return best_fallback
