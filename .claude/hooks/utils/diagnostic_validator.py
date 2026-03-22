# Checked AGENTS.md - implementing directly because this is safety-critical quality enforcement logic
"""
diagnostic_validator.py — Phase 3 Harness: Diagnostic Session Invariant Checks

Validates diagnostic sessions (state-based) and written diagnostic content (content-based).
Called by the harness layer to enforce 5 structural invariants before output is accepted.
"""

from __future__ import annotations

import re
from typing import Any

# ---------------------------------------------------------------------------
# Phase constants
# ---------------------------------------------------------------------------

_PHASE_SYSTEM_IDENTIFICATION = 3
_PHASE_TEST_SEQUENCE_DESIGN = 5

# ---------------------------------------------------------------------------
# Invariant 1: vehicle_phase_coherence
# ---------------------------------------------------------------------------

def _check_vehicle_phase_coherence(state: dict[str, Any]) -> list[str]:
    """Return violation if phase >= 3 but vehicle fields are incomplete."""
    phase: int = state.get("phase", 0)
    if phase < _PHASE_SYSTEM_IDENTIFICATION:
        return []

    vehicle: dict[str, Any] = state.get("vehicle") or {}
    missing: list[str] = [
        field
        for field in ("make", "model", "year")
        if not vehicle.get(field)
    ]

    if missing:
        return [
            f"Phase {phase} reached without identified vehicle "
            f"(missing: {', '.join(missing)})"
        ]
    return []


# ---------------------------------------------------------------------------
# Invariant 2: safety_gate_respected
# ---------------------------------------------------------------------------

def _check_safety_gate_respected(state: dict[str, Any]) -> list[str]:
    """Return violation if safety flags are active and unacknowledged at phase >= 5."""
    phase: int = state.get("phase", 0)
    if phase < _PHASE_TEST_SEQUENCE_DESIGN:
        return []

    safety_flags: list[str] = state.get("safety_flags") or []
    safety_acknowledged: bool = state.get("safety_acknowledged", False)

    if safety_flags and not safety_acknowledged:
        flag_count = len(safety_flags)
        return [
            f"Safety gate not cleared before test sequence "
            f"(phase {phase}): {flag_count} flag{'s' if flag_count != 1 else ''} active"
        ]
    return []


# ---------------------------------------------------------------------------
# Invariant 3: hypothesis_coverage
# ---------------------------------------------------------------------------

def _check_hypothesis_coverage(state: dict[str, Any]) -> list[str]:
    """Return violation if phase >= 5 but no hypotheses are documented."""
    phase: int = state.get("phase", 0)
    if phase < _PHASE_TEST_SEQUENCE_DESIGN:
        return []

    hypotheses: list[Any] = state.get("hypotheses") or []
    if len(hypotheses) < 1:
        return [
            f"Test sequence reached without documented hypotheses (phase {phase})"
        ]
    return []


# ---------------------------------------------------------------------------
# Invariant 4: required_sections
# ---------------------------------------------------------------------------

_REQUIRED_SECTIONS: list[str] = [
    "📚 SOURCES",
    "⚖️ DISCLAIMER",
]


def _check_required_sections(content: str) -> list[str]:
    """Return one violation per missing required section marker."""
    violations: list[str] = []
    for section in _REQUIRED_SECTIONS:
        if section not in content:
            violations.append(f"Missing required section: {section}")
    return violations


# ---------------------------------------------------------------------------
# Invariant 5: assessment_level_present
# ---------------------------------------------------------------------------

_ASSESSMENT_LEVELS: list[str] = [
    "STRONG INDICATION",
    "PROBABLE",
    "POSSIBLE",
    "INSUFFICIENT BASIS",
]


def _check_assessment_level_present(content: str) -> list[str]:
    """Return violation if no categorical assessment level is present in content."""
    for level in _ASSESSMENT_LEVELS:
        if level in content:
            return []
    return [
        "No categorical assessment level found "
        "(STRONG INDICATION / PROBABLE / POSSIBLE / INSUFFICIENT BASIS)"
    ]


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def run_state_invariants(state: dict[str, Any]) -> list[str]:
    """Run all 3 state-based invariants. Return list of violation strings (empty = pass)."""
    violations: list[str] = []
    violations.extend(_check_vehicle_phase_coherence(state))
    violations.extend(_check_safety_gate_respected(state))
    violations.extend(_check_hypothesis_coverage(state))
    return violations


def run_content_invariants(content: str) -> list[str]:
    """Run both content-based invariants on text. Return list of violation strings."""
    violations: list[str] = []
    violations.extend(_check_required_sections(content))
    violations.extend(_check_assessment_level_present(content))
    return violations


# ---------------------------------------------------------------------------
# Diagnostic content detector
# ---------------------------------------------------------------------------

_DTC_PATTERN: re.Pattern[str] = re.compile(r"\b[PCBU][0-3][0-9A-Fa-f]{3}\b")

_DIAGNOSTIC_KEYWORDS: list[str] = [
    # Vehicle identification signals
    "make", "model", "year", "vin",
    # Symptom signals
    "symptom", "misfire", "stall", "surge", "shudder", "hesitation",
    "check engine", "dtc", "obd", "scan tool", "live data",
    # Diagnostic output signals
    "tsb", "recall", "nhtsa", "diagnosis", "diagnostic",
    "STRONG INDICATION", "PROBABLE", "POSSIBLE", "INSUFFICIENT BASIS",
    "📚 SOURCES", "⚖️ DISCLAIMER",
]

_KEYWORD_THRESHOLD = 2


def is_diagnostic_content(content: str) -> bool:
    """Return True if text looks like a diagnostic response.

    Detects DTC codes (e.g. P0300) or at least two diagnostic keywords.
    Used to avoid false-positive validation on unrelated file writes.
    """
    if _DTC_PATTERN.search(content):
        return True

    content_lower = content.lower()
    matched = sum(
        1
        for kw in _DIAGNOSTIC_KEYWORDS
        if kw.lower() in content_lower
    )
    return matched >= _KEYWORD_THRESHOLD
