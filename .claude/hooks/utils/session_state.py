"""Diagnostic session state management for harness engineering.

Provides persistent JSON-based state tracking for active diagnostic sessions.
State files live alongside audit logs: logs/{session_id}/diagnostic-session.json
"""

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from utils.constants import ensure_session_log_dir


# ---------------------------------------------------------------------------
# Schema constants
# ---------------------------------------------------------------------------

DATA_LEVELS = ("COMPLETE", "STANDARD", "PARTIAL", "MINIMAL")

CONFIDENCE_CEILINGS = {
    "COMPLETE": "STRONG INDICATION",
    "STANDARD": "PROBABLE",
    "PARTIAL": "POSSIBLE",
    "MINIMAL": "INSUFFICIENT BASIS",
}

PHASES = {
    1: "Information Gathering",
    2: "Safety Assessment",
    3: "System Identification",
    4: "Differential Diagnosis",
    5: "Test Sequence",
    6: "Primary Recommendation",
    7: "Source Attribution & Disclaimer",
}

HYPOTHESIS_STATUSES = ("active", "eliminated", "confirmed")


# ---------------------------------------------------------------------------
# State schema (returned as plain dict for JSON serialization)
# ---------------------------------------------------------------------------

def new_session(session_id: str) -> dict[str, Any]:
    """Return a blank diagnostic session state dict."""
    now = datetime.now(timezone.utc).isoformat()
    return {
        "session_id": session_id,
        "vehicle": {
            "year": None,
            "make": None,
            "model": None,
            "engine": None,
            "mileage": None,
            "vin": None,
        },
        "dtc_codes": [],
        "symptoms": [],
        "phase": 1,
        "data_level": "MINIMAL",
        "confidence_ceiling": "INSUFFICIENT BASIS",
        "hypotheses": [],
        "tests_completed": [],
        "safety_flags": [],
        "safety_acknowledged": False,
        "violations": [],
        "created_at": now,
        "updated_at": now,
    }


# ---------------------------------------------------------------------------
# File I/O
# ---------------------------------------------------------------------------

def get_state_path(session_id: str) -> Path:
    """Return the path to the session state file."""
    log_dir = ensure_session_log_dir(session_id)
    return log_dir / "diagnostic-session.json"


def load_state(session_id: str) -> dict[str, Any] | None:
    """Load and return the session state, or None if no state exists."""
    path = get_state_path(session_id)
    if not path.exists():
        return None
    try:
        content = path.read_text(encoding="utf-8").strip()
        if not content:
            return None
        return json.loads(content)
    except (json.JSONDecodeError, OSError):
        return None


def save_state(session_id: str, state: dict[str, Any]) -> None:
    """Atomically write session state to disk."""
    state["updated_at"] = datetime.now(timezone.utc).isoformat()
    path = get_state_path(session_id)
    tmp_path = path.with_suffix(".tmp")
    try:
        tmp_path.write_text(
            json.dumps(state, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
        tmp_path.replace(path)
    except OSError:
        pass  # Never block on state write failure


def load_or_create(session_id: str) -> dict[str, Any]:
    """Load existing state or create a fresh one."""
    state = load_state(session_id)
    if state is None:
        state = new_session(session_id)
    return state


# ---------------------------------------------------------------------------
# Vehicle info helpers
# ---------------------------------------------------------------------------

def update_vehicle(session_id: str, **fields: Any) -> dict[str, Any]:
    """Update one or more vehicle fields. Returns updated state."""
    state = load_or_create(session_id)
    for key, value in fields.items():
        if key in state["vehicle"] and value is not None:
            state["vehicle"][key] = value
    _recalculate_data_level(state)
    save_state(session_id, state)
    return state


def is_vehicle_identified(state: dict[str, Any]) -> bool:
    """Return True if make, model, and year are all present."""
    v = state.get("vehicle", {})
    return bool(v.get("make") and v.get("model") and v.get("year"))


def _recalculate_data_level(state: dict[str, Any]) -> None:
    """Update data_level and confidence_ceiling based on available info."""
    v = state.get("vehicle", {})
    has_vehicle = bool(v.get("make") and v.get("model") and v.get("year"))
    has_dtcs = bool(state.get("dtc_codes"))
    has_symptoms = bool(state.get("symptoms"))

    if has_vehicle and has_dtcs and has_symptoms:
        level = "STANDARD"
    elif has_vehicle and has_symptoms:
        level = "PARTIAL"
    elif has_vehicle or has_symptoms:
        level = "MINIMAL"
    else:
        level = "MINIMAL"

    state["data_level"] = level
    state["confidence_ceiling"] = CONFIDENCE_CEILINGS[level]


# ---------------------------------------------------------------------------
# DTC / symptom helpers
# ---------------------------------------------------------------------------

def add_dtc_codes(session_id: str, codes: list[str]) -> dict[str, Any]:
    """Add DTC codes to the session (deduplicates). Returns updated state."""
    state = load_or_create(session_id)
    existing = set(state.get("dtc_codes", []))
    for code in codes:
        existing.add(code.upper())
    state["dtc_codes"] = sorted(existing)
    _recalculate_data_level(state)
    save_state(session_id, state)
    return state


def add_symptoms(session_id: str, symptoms: list[str]) -> dict[str, Any]:
    """Add symptoms to the session (deduplicates). Returns updated state."""
    state = load_or_create(session_id)
    existing = set(state.get("symptoms", []))
    for s in symptoms:
        s = s.strip()
        if s:
            existing.add(s.lower())
    state["symptoms"] = sorted(existing)
    _recalculate_data_level(state)
    save_state(session_id, state)
    return state


# ---------------------------------------------------------------------------
# Phase management
# ---------------------------------------------------------------------------

def update_phase(session_id: str, new_phase: int) -> dict[str, Any]:
    """Advance to a new phase. Enforces sequential progression."""
    state = load_or_create(session_id)
    current = state.get("phase", 1)
    # Allow only +1 increment (or stay the same)
    if new_phase == current + 1 and new_phase in PHASES:
        state["phase"] = new_phase
        save_state(session_id, state)
    return state


def auto_advance_phase(state: dict[str, Any]) -> dict[str, Any]:
    """Check phase advancement criteria and auto-advance if met."""
    phase = state.get("phase", 1)
    v = state.get("vehicle", {})

    if phase == 1:
        # 1→2: vehicle make + model + year present
        if v.get("make") and v.get("model") and v.get("year"):
            state["phase"] = 2
    elif phase == 2:
        # 2→3: safety_flags assessed (even if empty list, treat as done after vehicle ID)
        if is_vehicle_identified(state) and state.get("symptoms"):
            state["phase"] = 3
    elif phase == 3:
        # 3→4: 1+ symptoms mapped
        if state.get("symptoms") and is_vehicle_identified(state):
            if state.get("dtc_codes") or len(state.get("symptoms", [])) >= 1:
                state["phase"] = 4
    elif phase == 4:
        # 4→5: 2+ hypotheses added
        if len(state.get("hypotheses", [])) >= 2:
            state["phase"] = 5
    elif phase == 5:
        # 5→6: 1+ test completed
        if state.get("tests_completed"):
            state["phase"] = 6
    # Phase 6→7 left to manual update (primary recommendation complete)

    return state


# ---------------------------------------------------------------------------
# Hypothesis management
# ---------------------------------------------------------------------------

def add_hypothesis(session_id: str, description: str, assessment: str = "POSSIBLE") -> dict[str, Any]:
    """Add a diagnostic hypothesis. Returns updated state."""
    state = load_or_create(session_id)
    hypotheses = state.get("hypotheses", [])
    h_id = f"H{len(hypotheses) + 1}"
    hypotheses.append({
        "id": h_id,
        "description": description,
        "assessment": assessment,
        "status": "active",
        "eliminated_reason": None,
    })
    state["hypotheses"] = hypotheses
    state = auto_advance_phase(state)
    save_state(session_id, state)
    return state


def eliminate_hypothesis(session_id: str, hypothesis_id: str, reason: str) -> dict[str, Any]:
    """Mark a hypothesis as eliminated with a reason. Returns updated state."""
    state = load_or_create(session_id)
    for h in state.get("hypotheses", []):
        if h["id"] == hypothesis_id:
            h["status"] = "eliminated"
            h["eliminated_reason"] = reason
            break
    save_state(session_id, state)
    return state


def count_eliminated(state: dict[str, Any]) -> int:
    """Return count of eliminated hypotheses."""
    return sum(
        1 for h in state.get("hypotheses", [])
        if h.get("status") == "eliminated"
    )


# ---------------------------------------------------------------------------
# Safety flags
# ---------------------------------------------------------------------------

def add_safety_flag(session_id: str, flag: str) -> dict[str, Any]:
    """Add a safety flag to the session. Returns updated state."""
    state = load_or_create(session_id)
    flags = state.get("safety_flags", [])
    if flag not in flags:
        flags.append(flag)
    state["safety_flags"] = flags
    save_state(session_id, state)
    return state


def has_safety_flags(state: dict[str, Any]) -> bool:
    """Return True if any safety flags are set."""
    return bool(state.get("safety_flags"))


def acknowledge_safety(session_id: str) -> dict[str, Any]:
    """Mark safety flags as acknowledged by the mechanic. Returns updated state."""
    state = load_or_create(session_id)
    state["safety_acknowledged"] = True
    save_state(session_id, state)
    return state


# ---------------------------------------------------------------------------
# Violation tracking
# ---------------------------------------------------------------------------

def set_violations(session_id: str, violations: list[str]) -> dict[str, Any]:
    """Replace the violations list. Returns updated state."""
    state = load_or_create(session_id)
    state["violations"] = violations
    save_state(session_id, state)
    return state


def clear_violations(session_id: str) -> dict[str, Any]:
    """Clear all violations. Returns updated state."""
    return set_violations(session_id, [])
