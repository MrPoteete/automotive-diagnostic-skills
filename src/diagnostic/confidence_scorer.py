"""
Confidence scorer for automotive diagnostic results.

Implements the scoring formula from NHTSA_INTEGRATION_STRATEGY.md,
adapted for actual database schema (no fire_flag/crash_flag columns —
those exist only in schema.sql but not in the running database).

Scoring formula:
  base = 0.5
  + DTC match bonus  (+0.20)
  + pattern match bonus (+0.15)
  + complaint frequency bonus (0.05–0.15)
  + safety-critical keyword bonus (+0.05)
  capped at 1.0
"""

import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from src.data.db_service import DiagnosticDB

logger = logging.getLogger(__name__)

# Safety-critical component keywords (from DOMAIN.md)
SAFETY_CRITICAL_KEYWORDS: dict[str, list[str]] = {
    "CRITICAL": ["brake", "abs", "airbag", "srs", "steering", "eps"],
    "HIGH": ["tipm", "throttle", "pedal", "fuel pump", "fire", "crash"],
}

# Complaint frequency thresholds → confidence boost
FREQUENCY_THRESHOLDS: list[tuple[int, float]] = [
    (100, 0.15),
    (50, 0.10),
    (10, 0.05),
    (0, 0.0),
]


def is_safety_critical(component: str) -> tuple[bool, str | None]:
    """
    Check if a component is safety-critical.

    Returns (is_critical, level) where level is 'CRITICAL', 'HIGH', or None.
    """
    component_lower = component.lower()
    for level, keywords in SAFETY_CRITICAL_KEYWORDS.items():
        if any(keyword in component_lower for keyword in keywords):
            return True, level
    return False, None


def _frequency_boost(count: int) -> float:
    """Return confidence boost based on complaint frequency."""
    for threshold, boost in FREQUENCY_THRESHOLDS:
        if count > threshold:
            return boost
    return 0.0


def calculate_confidence(
    vehicle: dict,
    component: str,
    db: "DiagnosticDB",
    has_dtc_match: bool = False,
    has_pattern_match: bool = False,
) -> float:
    """
    Calculate diagnostic confidence score for a vehicle/component pair.

    Args:
        vehicle: Dict with keys 'make', 'model', 'year'
        component: Component name (e.g., 'POWER TRAIN', 'BRAKES')
        db: DiagnosticDB instance for complaint frequency lookup
        has_dtc_match: True if a matching DTC code was found
        has_pattern_match: True if a known failure pattern was matched

    Returns:
        Confidence score in [0.0, 1.0]
    """
    make = vehicle.get("make", "")
    model = vehicle.get("model", "")
    year = int(vehicle.get("year", 0))

    base = 0.5

    # DTC and pattern match bonuses
    if has_dtc_match:
        base += 0.20
    if has_pattern_match:
        base += 0.15

    # Complaint frequency boost (uses actual FTS5 complaint count)
    try:
        count = db.count_complaints(make, model, year, component)
        base += _frequency_boost(count)
        logger.debug(
            "Complaint count for %s %s %d / %s: %d",
            make, model, year, component, count,
        )
    except Exception as exc:
        logger.warning("Could not fetch complaint count: %s", exc)

    # Safety-critical keyword boost
    is_critical, _ = is_safety_critical(component)
    if is_critical:
        base += 0.05

    score = min(base, 1.0)
    logger.debug(
        "Confidence for %s %s %d / %s: %.2f "
        "(dtc=%s pattern=%s)",
        make, model, year, component, score,
        has_dtc_match, has_pattern_match,
    )
    return score


def score_results(
    vehicle: dict,
    components: list[dict],
    db: "DiagnosticDB",
    dtc_codes: list[str] | None = None,
) -> list[dict]:
    """
    Apply confidence scoring to a ranked list of candidate components.

    Args:
        vehicle: Dict with 'make', 'model', 'year'
        components: List of dicts from symptom_matcher, each has 'component', 'count', etc.
        db: DiagnosticDB instance
        dtc_codes: Optional list of OBD-II codes (e.g. ['P0300', 'P0301'])

    Returns:
        Same list with 'confidence' field added, sorted descending by confidence.
    """
    dtc_codes = dtc_codes or []
    scored = []

    for item in components:
        component = item.get("component", "")

        # Rough DTC-to-component heuristic (P-codes → power train, C-codes → chassis, etc.)
        has_dtc_match = _dtc_matches_component(dtc_codes, component)

        confidence = calculate_confidence(
            vehicle=vehicle,
            component=component,
            db=db,
            has_dtc_match=has_dtc_match,
            has_pattern_match=False,  # failure_patterns table empty in Phase 3
        )

        scored.append({**item, "confidence": confidence})

    return sorted(scored, key=lambda x: x["confidence"], reverse=True)


# DTC system code → complaint component keyword mapping
_DTC_COMPONENT_MAP: dict[str, list[str]] = {
    "P": ["power train", "engine", "fuel", "ignition", "exhaust"],
    "C": ["chassis", "brake", "suspension", "steering", "traction"],
    "B": ["body", "airbag", "srs", "climate", "electrical"],
    "U": ["network", "communication", "electrical", "module"],
}


def _dtc_matches_component(dtc_codes: list[str], component: str) -> bool:
    """Return True if any DTC code's system prefix maps to the component."""
    if not dtc_codes:
        return False
    component_lower = component.lower()
    for code in dtc_codes:
        if not code:
            continue
        prefix = code[0].upper()
        keywords = _DTC_COMPONENT_MAP.get(prefix, [])
        if any(kw in component_lower for kw in keywords):
            return True
    return False
