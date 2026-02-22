"""
Engine Diagnostic Agent — orchestrator for differential diagnosis.

Checked AGENTS.md - implementing directly because:
1. This is the safety-critical orchestration path (per GEMINI_WORKFLOW.md)
2. Integrates confidence scoring, safety alerts, and symptom matching
3. Must enforce confidence thresholds and safety checks end-to-end

Orchestrates: db_service → symptom_matcher → confidence_scorer
              → alert_system → trend_analyzer → TSB lookup
              → chroma_service (Phase 4: forum data boost)

Returns a complete ranked differential diagnosis dict.
"""

import logging
import re
from typing import Any

from src.data.db_service import DiagnosticDB
from src.diagnostic.confidence_scorer import score_results  # type: ignore[attr-defined]
from src.diagnostic.symptom_matcher import match_symptoms  # type: ignore[attr-defined]
from src.safety.alert_system import check_safety_alerts, requires_high_confidence as safety_requires_high_conf
from src.analysis.trend_analyzer import get_trend_summary  # type: ignore[attr-defined]

logger = logging.getLogger(__name__)

# OBD-II DTC validation pattern (DOMAIN.md)
DTC_PATTERN = re.compile(r"^[PCBU][0-3][0-9A-F]{3}$", re.IGNORECASE)

# Minimum confidence for safety-critical component diagnosis
SAFETY_MIN_CONFIDENCE = 0.9


def _validate_dtc_codes(dtc_codes: list[str]) -> list[str]:
    """Validate and filter DTC codes, returning only valid ones."""
    valid = []
    for code in dtc_codes:
        clean = code.strip().upper()
        if DTC_PATTERN.match(clean):
            valid.append(clean)
        else:
            logger.warning("Invalid DTC code ignored: %r", code)
    return valid


def diagnose(
    vehicle: dict,
    symptoms: str,
    dtc_codes: list[str] | None = None,
    db: DiagnosticDB | None = None,
) -> dict[str, Any]:
    """
    Run a complete differential diagnosis for a vehicle and symptoms.

    Args:
        vehicle: Dict with 'make', 'model', 'year' (str or int)
        symptoms: Free-text symptom description from the mechanic
        dtc_codes: Optional list of OBD-II DTC codes (e.g. ['P0300', 'P0301'])
        db: Optional DiagnosticDB instance (creates one if not provided)

    Returns:
        Diagnostic result dict:
        {
            "vehicle": {...},
            "symptoms": str,
            "dtc_codes": [...],
            "candidates": [
                {
                    "component": str,
                    "count": int,
                    "confidence": float,
                    "confidence_sufficient": bool,
                    "safety_alert": dict | None,
                    "trend": str,
                    "tsbs": [...],
                    "samples": [...],
                }
            ],
            "warnings": [...],
            "data_sources": {...},
        }
    """
    _owns_db = db is None
    owned_db: DiagnosticDB = db if db is not None else DiagnosticDB()

    try:
        return _run_diagnosis(vehicle, symptoms, dtc_codes or [], owned_db)
    finally:
        if _owns_db:
            owned_db.close()


def _run_diagnosis(
    vehicle: dict,
    symptoms: str,
    dtc_codes: list[str],
    db: DiagnosticDB,
) -> dict[str, Any]:
    """Internal diagnosis logic — runs inside managed DB context."""
    # Normalize vehicle fields
    make = str(vehicle.get("make", "")).upper().strip()
    model = str(vehicle.get("model", "")).upper().strip()
    year = int(vehicle.get("year", 0))

    if not make or not model or not year:
        return _error_result(vehicle, symptoms, "Vehicle make, model, and year are required.")

    normalized_vehicle = {"make": make, "model": model, "year": year}

    # Validate DTC codes
    valid_dtcs = _validate_dtc_codes(dtc_codes)
    if dtc_codes and not valid_dtcs:
        logger.warning("All provided DTC codes were invalid: %s", dtc_codes)

    warnings: list[str] = []

    # Step 1a: Forum semantic search (Phase 4 — optional, degrades gracefully)
    forum_candidates: list[dict] = []
    try:
        from src.data.chroma_service import ChromaService  # type: ignore[attr-defined]
        chroma = ChromaService()
        if chroma.document_count > 0:
            forum_candidates = chroma.search_for_components(
                query=f"{make} {model} {symptoms}",
                n_results=20,
            )
            logger.info("Forum search returned %d candidate components", len(forum_candidates))
    except Exception as exc:
        logger.debug("Forum search unavailable (ChromaDB not ready?): %s", exc)

    # Step 1b: Symptom matching → candidate components
    logger.info("Matching symptoms for %s %s %d: %r", make, model, year, symptoms)
    candidates = match_symptoms(
        make=make,
        model=model,
        year=year,
        description=symptoms,
        db=db,
        limit=30,
    )

    # Merge forum candidates into NHTSA results (forum adds context, doesn't replace)
    if forum_candidates:
        existing_components = {c["component"] for c in candidates}
        for fc in forum_candidates:
            if fc["component"] not in existing_components:
                candidates.append(fc)

    if not candidates:
        logger.info("No symptom matches found, trying DTC-based component lookup")
        candidates = _candidates_from_dtcs(valid_dtcs)

    if not candidates:
        return {
            "vehicle": normalized_vehicle,
            "symptoms": symptoms,
            "dtc_codes": valid_dtcs,
            "candidates": [],
            "warnings": ["No matching complaints found in NHTSA database for this vehicle/symptom combination."],
            "data_sources": {"complaints_searched": True, "tsbs_searched": False},
        }

    # Step 2: Confidence scoring
    logger.info("Scoring %d candidate components", len(candidates))
    scored = score_results(
        vehicle=normalized_vehicle,
        components=candidates,
        db=db,
        dtc_codes=valid_dtcs,
    )

    # Step 3: Safety alerts + confidence gating + trend analysis + TSB lookup
    enriched: list[dict] = []
    for candidate in scored[:10]:  # top 10 only
        component = candidate["component"]
        confidence = candidate["confidence"]

        # Safety check
        alert = check_safety_alerts(
            vehicle=normalized_vehicle,
            component=component,
            db=db,
        )

        # Confidence sufficiency — CRITICAL systems need >= 0.9
        needs_high_conf = safety_requires_high_conf(component)
        confidence_sufficient = (
            confidence >= SAFETY_MIN_CONFIDENCE
            if needs_high_conf
            else confidence >= 0.5
        )

        if needs_high_conf and not confidence_sufficient:
            warn_msg = (
                f"INSUFFICIENT CONFIDENCE for safety-critical component '{component}': "
                f"{confidence:.0%} < {SAFETY_MIN_CONFIDENCE:.0%} required. "
                "More data needed before repair recommendation."
            )
            warnings.append(warn_msg)
            logger.warning(warn_msg)

        # Trend analysis
        try:
            trend_data = get_trend_summary(make, model, component, db)
            trend = trend_data.get("trend", "INSUFFICIENT_DATA")
        except Exception as exc:
            logger.debug("Trend analysis failed for %s: %s", component, exc)
            trend = "INSUFFICIENT_DATA"
            trend_data = {}

        # TSB lookup
        try:
            tsbs = db.search_tsbs(
                make=make,
                model=model,
                year=year,
                component=component,
                limit=5,
            )
        except Exception as exc:
            logger.debug("TSB lookup failed for %s: %s", component, exc)
            tsbs = []

        enriched.append({
            "component": component,
            "complaint_count": candidate.get("count", 0),
            "confidence": round(confidence, 3),
            "confidence_sufficient": confidence_sufficient,
            "requires_high_confidence": needs_high_conf,
            "safety_alert": alert,
            "trend": trend,
            "trend_data": trend_data,
            "tsbs": tsbs,
            "samples": candidate.get("samples", []),
        })

    # Collect top-level safety warnings
    critical_alerts = [
        c["safety_alert"]["message"]
        for c in enriched
        if c["safety_alert"] and c["safety_alert"]["level"] == "CRITICAL"
    ]
    warnings = critical_alerts + warnings

    return {
        "vehicle": normalized_vehicle,
        "symptoms": symptoms,
        "dtc_codes": valid_dtcs,
        "candidates": enriched,
        "warnings": warnings,
        "data_sources": {
            "complaints_db": "automotive_complaints.db (562K NHTSA complaints)",
            "tsbs_db": "automotive_complaints.db (211K NHTSA TSBs)",
            "forum_db": f"ChromaDB mechanics_forum ({len(forum_candidates)} forum candidates)",
            "complaint_coverage": "Partial dataset — full import pending",
        },
    }


def _candidates_from_dtcs(dtc_codes: list[str]) -> list[dict]:
    """Generate minimal candidate list from DTC code system prefixes."""
    if not dtc_codes:
        return []

    dtc_component_map: dict[str, str] = {
        "P": "POWER TRAIN",
        "C": "CHASSIS",
        "B": "BODY",
        "U": "ELECTRICAL SYSTEM",
    }

    seen: set[str] = set()
    candidates = []
    for code in dtc_codes:
        prefix = code[0].upper()
        component = dtc_component_map.get(prefix)
        if component and component not in seen:
            seen.add(component)
            candidates.append({
                "component": component,
                "count": 1,
                "confidence_hint": 0.5,
                "samples": [],
            })
    return candidates


def _error_result(vehicle: dict, symptoms: str, message: str) -> dict[str, Any]:
    """Return a structured error result."""
    return {
        "vehicle": vehicle,
        "symptoms": symptoms,
        "dtc_codes": [],
        "candidates": [],
        "warnings": [message],
        "data_sources": {},
        "error": message,
    }
