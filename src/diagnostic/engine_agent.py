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

# Checked AGENTS.md - implementing session wiring directly because:
# 1. diagnose() is the safety-critical orchestration path (GEMINI_WORKFLOW.md: keep with Claude)
# 2. Session lifecycle touches confidence gating and error propagation — no delegation
# 3. Platform family expansion is a read-only diagnostic enrichment — same safety class
from src.data.db_service import DiagnosticDB
from src.data.platform_service import PlatformService
from src.diagnostic.confidence_scorer import score_results  # type: ignore[attr-defined]
from src.diagnostic.session_state import DiagnosticSession
from src.diagnostic.session_store import SessionStore
from src.diagnostic.symptom_matcher import match_symptoms  # type: ignore[attr-defined]
from src.safety.alert_system import check_safety_alerts, requires_high_confidence as safety_requires_high_conf
from src.analysis.trend_analyzer import get_trend_summary  # type: ignore[attr-defined]

logger = logging.getLogger(__name__)

# Checked AGENTS.md - implementing directly because:
# 1. Input coercion helpers are safety-critical validation (must not delegate)
# 2. Hardening the orchestration path requires full context of all pipeline steps
# 3. No open-ended design decisions — changes are mechanically specified


def _coerce_vehicle(raw: Any) -> dict:
    """Coerce the vehicle parameter to a plain dict, returning {} on bad input."""
    if raw is None or not isinstance(raw, dict):
        if raw is not None:
            logger.warning(
                "[diagnose] vehicle must be a dict, got %s — treating as empty",
                type(raw).__name__,
            )
        return {}
    return raw


def _coerce_symptoms(raw: Any) -> str:
    """Coerce the symptoms parameter to a stripped string."""
    if raw is None:
        logger.warning("[diagnose] symptoms is None — using empty string")
        return ""
    if isinstance(raw, str):
        return raw.strip()
    try:
        coerced = str(raw).strip()
        logger.warning(
            "[diagnose] symptoms was %s, coerced to str: %r",
            type(raw).__name__,
            coerced[:80],
        )
        return coerced
    except Exception:
        return ""


def _coerce_dtc_codes(raw: Any) -> list[str]:
    """Coerce dtc_codes to a list of strings."""
    if raw is None:
        return []
    if isinstance(raw, list):
        return raw
    if isinstance(raw, str):
        logger.warning("[diagnose] dtc_codes is a str %r — wrapping in list", raw)
        return [raw]
    if isinstance(raw, (set, tuple, frozenset)):
        logger.warning(
            "[diagnose] dtc_codes is %s — converting to list",
            type(raw).__name__,
        )
        return list(raw)
    logger.warning(
        "[diagnose] dtc_codes has unexpected type %s — ignoring",
        type(raw).__name__,
    )
    return []


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
    session_id: str | None = None,
    repair_order: str | None = None,
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
    # Coerce all inputs before any DB access so _run_diagnosis always
    # receives well-typed arguments.
    vehicle = _coerce_vehicle(vehicle)
    symptoms = _coerce_symptoms(symptoms)
    dtc_list = _coerce_dtc_codes(dtc_codes)

    # Session: load existing or create new
    store = SessionStore()
    session: DiagnosticSession
    if session_id:
        loaded = store.load(session_id)
        if loaded is not None:
            session = loaded
        else:
            logger.warning("[diagnose] session_id %r not found — creating new session", session_id)
            session = DiagnosticSession.create(vehicle=vehicle, symptoms=symptoms, repair_order=repair_order)
    else:
        session = DiagnosticSession.create(vehicle=vehicle, symptoms=symptoms, repair_order=repair_order)

    _owns_db = db is None
    if _owns_db:
        try:
            owned_db: DiagnosticDB = DiagnosticDB()
        except Exception as exc:
            logger.error("[diagnose] DiagnosticDB init failed: %s", exc)
            result = _error_result(vehicle, symptoms, "Database connection failed.")
            result["session_id"] = session.session_id
            return result
    else:
        owned_db = db  # type: ignore[assignment]

    result: dict[str, Any]
    try:
        result = _run_diagnosis(vehicle, symptoms, dtc_list, owned_db)
    finally:
        if _owns_db:
            owned_db.close()

    # Log the diagnostic turn and persist session
    session.append_message("user", symptoms)
    top_candidates = result.get("candidates") or []
    top_component: str | None = top_candidates[0].get("component") if top_candidates else None
    session.advance_turn(hypothesis_label=top_component)
    try:
        store.save(session)
    except Exception as exc:
        logger.warning("[diagnose] session save failed: %s", exc)

    result["session_id"] = session.session_id
    return result


def _run_diagnosis(
    vehicle: dict,
    symptoms: str,
    dtc_codes: list[str],
    db: DiagnosticDB,
) -> dict[str, Any]:
    """Internal diagnosis logic — runs inside managed DB context."""
    # Normalize vehicle fields
    make = str(vehicle.get("make", "") or "").upper().strip()
    model = str(vehicle.get("model", "") or "").upper().strip()
    try:
        year = int(vehicle.get("year", 0))
    except (ValueError, TypeError):
        raw_year = vehicle.get("year")
        logger.warning("[diagnose] Invalid year value %r — returning error", raw_year)
        return _error_result(
            vehicle, symptoms,
            f"Vehicle year must be a valid integer (e.g. 2019); got {raw_year!r}.",
        )

    if not make or not model or not year:
        return _error_result(vehicle, symptoms, "Vehicle make, model, and year are required.")

    engine_model = str(vehicle.get("engine_model") or "")
    normalized_vehicle = {"make": make, "model": model, "year": year, "engine_model": engine_model}

    # Validate DTC codes
    valid_dtcs = _validate_dtc_codes(dtc_codes)
    if dtc_codes and not valid_dtcs:
        logger.warning("All provided DTC codes were invalid: %s", dtc_codes)

    warnings: list[str] = []

    logger.info(
        "[diagnose] Input parsed — make=%r model=%r year=%d symptoms=%r dtcs=%s",
        make, model, year,
        (symptoms[:80] + "…") if len(symptoms) > 80 else symptoms,
        valid_dtcs,
    )

    # Step 1a: Forum + ebook semantic search (Phase 4 — optional, degrades gracefully)
    # Skip if no symptoms — make/model alone produces noise with no diagnostic value
    forum_candidates: list[dict] = []
    ebook_context: list[dict] = []
    try:
        from src.data.chroma_service import ChromaService  # type: ignore[attr-defined]
        chroma = ChromaService()
        if chroma.document_count > 0 and symptoms:
            rag_query = f"{make} {model} {symptoms}"
            forum_candidates = chroma.search_for_components(
                query=rag_query,
                n_results=20,
            )
            logger.info("Forum search returned %d candidate components", len(forum_candidates))
            ebook_hits = chroma.search_ebook(query=rag_query, n_results=5)
            ebook_context = [
                {
                    "frame": h["metadata"].get("frame", ""),
                    "text": h["document"],
                    "relevance": h["relevance"],
                    "confidence": h["confidence"],
                }
                for h in ebook_hits
            ]
            if ebook_context:
                logger.info("Ebook search returned %d relevant frames", len(ebook_context))
    except Exception as exc:
        logger.debug("Forum search unavailable (ChromaDB not ready?): %s", exc)

    # Step 1b: Symptom matching → candidate components
    logger.info(
        "[diagnose] Querying DB — make=%r model=%r year=%d symptoms=%r",
        make, model, year,
        (symptoms[:60] + "…") if len(symptoms) > 60 else symptoms,
    )
    try:
        candidates = match_symptoms(
            make=make,
            model=model,
            year=year,
            description=symptoms,
            db=db,
            limit=30,
        )
    except Exception as exc:
        logger.error("[diagnose] match_symptoms raised unexpectedly: %s", exc, exc_info=True)
        candidates = []

    logger.info(
        "[diagnose] DB queried — %d NHTSA candidates, %d forum candidates",
        len(candidates), len(forum_candidates),
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
    logger.info("[diagnose] Scoring %d candidate components", len(candidates))
    try:
        scored = score_results(
            vehicle=normalized_vehicle,
            components=candidates,
            db=db,
            dtc_codes=valid_dtcs,
        )
    except Exception as exc:
        logger.error("[diagnose] score_results raised unexpectedly: %s", exc, exc_info=True)
        scored = [{**c, "confidence": 0.5} for c in candidates]

    top = scored[0] if scored else {}
    logger.info(
        "[diagnose] Score calculated — %d candidates; top=%r conf=%.3f",
        len(scored),
        top.get("component", "—"),
        top.get("confidence", 0.0),
    )

    # Step 2b: Platform family resolution (engine/powertrain components only)
    platform_svc = PlatformService()
    platform_family_name: str | None = None
    platform_siblings: list[dict] = []
    try:
        platform_family_name, platform_siblings = platform_svc.expand_vehicle_list(
            make=make,
            model=model,
            year=year,
            engine_model=engine_model,
            component_type=top.get("component", ""),
            displacement_hint=symptoms,
        )
        if platform_family_name:
            logger.info(
                "[diagnose] Platform family resolved: %s (%d siblings)",
                platform_family_name, len(platform_siblings),
            )
    except Exception as exc:
        logger.debug("Platform family lookup failed: %s", exc)

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

        # TSB lookup — vehicle-specific
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

        # Platform TSBs — siblings that share the same engine/transmission family
        platform_tsbs: list[dict] = []
        if platform_siblings and platform_svc._component_is_generalizable(component):
            try:
                platform_tsbs = db.search_tsbs_for_platform(
                    siblings=platform_siblings,
                    component=component,
                    limit=5,
                )
            except Exception as exc:
                logger.debug("Platform TSB lookup failed for %s: %s", component, exc)

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
            "platform_tsbs": platform_tsbs,
            "samples": candidate.get("samples", []),
        })

    # Collect top-level safety warnings
    critical_alerts = [
        c["safety_alert"]["message"]
        for c in enriched
        if c["safety_alert"] and c["safety_alert"]["level"] == "CRITICAL"
    ]
    warnings = critical_alerts + warnings

    # Checked AGENTS.md - adding recall lookup directly; simple DB query, safety-relevant data
    # Fetch NHTSA recalls for this vehicle/year (confidence 0.9 — manufacturer-acknowledged defects)
    recalls: list[dict] = []
    try:
        recalls = db.get_recalls(make, model, year)
        logger.debug("[diagnose] %d recalls found for %s %s %d", len(recalls), make, model, year)
    except Exception as exc:
        logger.warning("[diagnose] recall lookup failed: %s", exc)

    # Surface park-it recalls as top-level safety warnings
    park_it_warnings = [
        f"⚠ SAFETY RECALL (Park It): {r['component']} — {r['campaign_no']}"
        for r in recalls
        if r.get("park_it")
    ]
    if park_it_warnings:
        warnings = park_it_warnings + warnings

    return {
        "vehicle": normalized_vehicle,
        "symptoms": symptoms,
        "dtc_codes": valid_dtcs,
        "candidates": enriched,
        "recalls": recalls,
        "warnings": warnings,
        "ebook_context": ebook_context,
        "platform_family": platform_family_name,
        "platform_siblings": [
            f"{s['make']} {s['model']}" for s in platform_siblings
        ] if platform_siblings else [],
        "data_sources": {
            "complaints_db": "automotive_complaints.db (562K NHTSA complaints)",
            "tsbs_db": "automotive_complaints.db (211K NHTSA TSBs)",
            "recalls_db": f"nhtsa_recalls ({len(recalls)} recall campaigns for this vehicle/year)",
            "forum_db": f"ChromaDB mechanics_forum ({len(forum_candidates)} forum candidates)",
            "ebook_db": f"ScannerDanner ebook ({len(ebook_context)} relevant frames)",
            "platform_db": f"Platform family: {platform_family_name} ({len(platform_siblings)} siblings)" if platform_family_name else "No platform family matched",
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
