"""
Safety alert system for automotive diagnostics.

Checked AGENTS.md - implementing directly because:
1. This is safety-critical automotive logic (brakes, airbags, steering)
2. Per GEMINI_WORKFLOW.md: safety-critical systems stay with Claude
3. No auth/secrets involved — pure keyword matching + DB read
4. Security-engineer agent is for auth/validation code, not domain safety logic

Two-layer detection adapted for actual database schema:
  Layer 1: Component name keyword matching (fast, no DB)
  Layer 2: Complaint narrative scan for safety terms (DB lookup)

NOTE: fire_flag, crash_flag, num_injuries, num_deaths columns exist in
schema.sql but are NOT present in the running automotive_complaints.db.
This module uses keyword detection as the authoritative safety signal.
"""

import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from src.data.db_service import DiagnosticDB

logger = logging.getLogger(__name__)

# Safety keywords — must stay in sync with DOMAIN.md
SAFETY_KEYWORDS: dict[str, list[str]] = {
    "CRITICAL": ["brake", "abs", "antilock", "airbag", "srs", "steering", "eps"],
    "HIGH": ["tipm", "throttle", "pedal", "fuel pump", "fire", "crash", "stall"],
}

# Terms to scan in complaint narratives for safety-related content
NARRATIVE_SAFETY_TERMS: list[str] = [
    "fire", "crash", "injury", "death", "fatality", "accident",
    "recall", "collision", "rollover", "loss of control",
]

# Minimum complaint count to trigger a narrative-based alert
NARRATIVE_ALERT_THRESHOLD = 10


def check_component_keywords(component: str) -> dict | None:
    """
    Layer 1: Match component name against safety keyword lists.

    Returns alert dict or None if not safety-critical.
    """
    component_lower = component.lower()
    for level, keywords in SAFETY_KEYWORDS.items():
        for kw in keywords:
            if kw in component_lower:
                return {
                    "level": level,
                    "trigger": "component_keyword",
                    "keyword": kw,
                    "message": _format_message(level, component, kw),
                }
    return None


def check_narrative_safety(
    vehicle: dict,
    component: str,
    db: "DiagnosticDB",
) -> dict | None:
    """
    Layer 2: Scan complaint summaries for safety-related terms.

    Returns alert dict if safety terms appear frequently enough, else None.
    """
    make = vehicle.get("make", "")
    model = vehicle.get("model", "")
    year = int(vehicle.get("year", 0))

    try:
        # Search for each safety term in complaint narratives
        total_safety_hits = 0
        triggered_terms: list[str] = []

        for term in NARRATIVE_SAFETY_TERMS:
            results = db.search_complaints(
                make=make,
                model=model,
                year=year,
                query=f"{component} {term}",
                limit=5,
            )
            if results:
                total_safety_hits += len(results)
                triggered_terms.append(term)

        if total_safety_hits >= NARRATIVE_ALERT_THRESHOLD:
            return {
                "level": "WARNING",
                "trigger": "narrative_scan",
                "terms": triggered_terms[:5],
                "match_count": total_safety_hits,
                "message": (
                    f"WARNING SAFETY: {total_safety_hits} complaints for "
                    f"{make} {model} {component} mention safety-related terms "
                    f"({', '.join(triggered_terms[:3])}). "
                    "Professional inspection recommended before driving."
                ),
            }
    except Exception as exc:
        logger.warning("Narrative safety scan failed: %s", exc)

    return None


def check_safety_alerts(
    vehicle: dict,
    component: str,
    db: "DiagnosticDB",
) -> dict | None:
    """
    Run both safety detection layers for a vehicle/component pair.

    Args:
        vehicle: Dict with 'make', 'model', 'year'
        component: Component name to check
        db: DiagnosticDB for narrative scanning

    Returns:
        Alert dict {level, trigger, message, ...} or None if safe.
        Layer 1 (keyword) takes priority over Layer 2 (narrative).
    """
    # Layer 1: keyword check (fastest, most reliable)
    keyword_alert = check_component_keywords(component)
    if keyword_alert:
        logger.warning(
            "SAFETY ALERT [%s]: %s for %s %s %s / %s",
            keyword_alert["level"],
            keyword_alert["keyword"],
            vehicle.get("make"), vehicle.get("model"), vehicle.get("year"),
            component,
        )
        return keyword_alert

    # Layer 2: narrative scan (broader net for non-obvious safety issues)
    narrative_alert = check_narrative_safety(vehicle, component, db)
    if narrative_alert:
        logger.warning(
            "SAFETY ALERT [narrative]: %s complaints for %s %s %s / %s",
            narrative_alert["match_count"],
            vehicle.get("make"), vehicle.get("model"), vehicle.get("year"),
            component,
        )
        return narrative_alert

    return None


def requires_high_confidence(component: str) -> bool:
    """
    Return True if this component requires confidence >= 0.9 before diagnosis.

    Per DOMAIN.md: CRITICAL systems require 0.9 minimum confidence.
    """
    component_lower = component.lower()
    critical_keywords = SAFETY_KEYWORDS["CRITICAL"]
    return any(kw in component_lower for kw in critical_keywords)


def _format_message(level: str, component: str, keyword: str) -> str:
    """Format a human-readable safety alert message."""
    if level == "CRITICAL":
        return (
            f"SAFETY-CRITICAL SYSTEM: {component.title()} "
            f"(matched: '{keyword}'). "
            "This system directly affects vehicle controllability. "
            "DO NOT drive until inspected by a qualified technician. "
            "Diagnosis requires >= 90% confidence before repair recommendation."
        )
    else:
        return (
            f"HIGH-RISK COMPONENT: {component.title()} "
            f"(matched: '{keyword}'). "
            "Exercise caution. Professional inspection recommended."
        )
