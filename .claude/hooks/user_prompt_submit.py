#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# ///
"""UserPromptSubmit hook: audit logging + diagnostic skill injection.

1. Logs every user prompt to logs/{session_id}/prompts.json.
2. Detects automotive diagnostic requests and injects a skill reminder
   via the context field so Claude loads skills/SKILL.md before responding.
"""

import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from utils.constants import ensure_session_log_dir
from utils.session_state import (
    add_dtc_codes,
    add_symptoms,
    auto_advance_phase,
    load_or_create,
    save_state,
    update_vehicle,
    PHASES,
)

# ---------------------------------------------------------------------------
# Diagnostic detection patterns
# ---------------------------------------------------------------------------

# Vehicle year: 4 digits in range 1980–2030
_YEAR_RE = re.compile(r"\b(19[89]\d|20[0-3]\d)\b")

# Vehicle makes (common North American makes, case-insensitive)
_MAKES = {
    "ford", "lincoln", "chevrolet", "chevy", "gmc", "buick", "cadillac",
    "dodge", "jeep", "ram", "chrysler", "stellantis", "toyota", "lexus",
    "honda", "acura", "nissan", "infiniti", "hyundai", "kia", "genesis",
    "subaru", "mazda", "volkswagen", "vw", "audi", "bmw", "mercedes",
    "benz", "volvo", "fiat", "alfa", "porsche", "land rover", "jaguar",
}

# DTC code pattern: P/C/B/U + 4 hex digits
_DTC_RE = re.compile(r"\b[PCBU][0-3][0-9A-F]{3}\b", re.IGNORECASE)

# Symptom / diagnostic keywords — 2+ hits trigger even without year/make
_SYMPTOM_KEYWORDS = {
    "diagnose", "diagnosis", "troubleshoot", "what's wrong", "whats wrong",
    "check engine", "cel", "mil", "dtc", "code", "misfire", "stall", "surge",
    "hesitation", "hesitate", "rough idle", "idle", "shudder", "vibration",
    "noise", "knock", "tick", "rattle", "squeal", "grind", "whoosh",
    "overheat", "overheating", "leak", "smoke", "burning smell",
    "no start", "crank no start", "hard start", "limp mode", "limp home",
    "loss of power", "lack of power", "sluggish", "bog",
    "tsb", "technical service bulletin", "recall", "known issue",
    "scan tool", "live data", "freeze frame", "psi", "psia", "boost",
    "fuel pressure", "compression", "cylinder", "injector", "throttle",
    "transmission", "shifts", "slips", "neutral drop",
    "abs", "traction control", "brake", "steering",
}

# High-confidence single-word triggers — 1 hit alone is enough
# These are unambiguously automotive-diagnostic terms
_STRONG_KEYWORDS = {
    "wastegate", "actuator", "turbocharger", "turbo", "intercooler",
    "ecoboost", "ecotec", "hemi", "vortec", "coyote",
    "pcm", "ecm", "tcm", "bcm",
    "fuel trim", "ltft", "stft", "o2 sensor", "lambda",
    "map sensor", "maf sensor", "tps", "iac", "egr",
    "compression test", "leak down", "smoke test", "power balance",
    "freeze frame", "mode 6", "mode6",
    "boost pressure", "intake manifold", "exhaust manifold",
    "crankshaft position", "camshaft position", "ckp", "cmp",
    "knock sensor", "cam phaser", "vvt", "variable valve",
    "catalytic converter", "o2 sensor", "oxygen sensor",
    "abs module", "traction control module", "wheel speed sensor",
    "tie rod", "ball joint", "control arm", "cv axle", "cv joint",
}

# Manufacturer name → protocol file mapping
_MAKE_TO_PROTOCOL = {
    "ford": "ford-protocols.md",
    "lincoln": "ford-protocols.md",
    "chevrolet": "gm-protocols.md",
    "chevy": "gm-protocols.md",
    "gmc": "gm-protocols.md",
    "buick": "gm-protocols.md",
    "cadillac": "gm-protocols.md",
    "dodge": "stellantis-protocols.md",
    "jeep": "stellantis-protocols.md",
    "ram": "stellantis-protocols.md",
    "chrysler": "stellantis-protocols.md",
    "toyota": "toyota-protocols.md",
    "lexus": "toyota-protocols.md",
    "honda": "honda-protocols.md",
    "acura": "honda-protocols.md",
    "nissan": "nissan-protocols.md",
    "infiniti": "nissan-protocols.md",
    "hyundai": "hyundai-kia-protocols.md",
    "kia": "hyundai-kia-protocols.md",
    "genesis": "hyundai-kia-protocols.md",
    "volkswagen": "vw-audi-protocols.md",
    "vw": "vw-audi-protocols.md",
    "audi": "vw-audi-protocols.md",
    "bmw": "bmw-protocols.md",
    "mercedes": "mercedes-protocols.md",
    "benz": "mercedes-protocols.md",
    "subaru": "subaru-protocols.md",
}


def detect_diagnostic_request(prompt: str) -> tuple[bool, str | None]:
    """
    Returns (is_diagnostic, detected_make_or_None).

    Triggers if ANY of:
    - DTC code present (P/C/B/U + 4 hex digits)
    - 1 strong-signal keyword (wastegate, turbo, pcm, fuel trim, etc.)
    - Vehicle year + make/model context + at least 1 symptom keyword
    - 2+ general symptom keywords (catches follow-up messages)
    """
    lower = prompt.lower()

    # Tier 1: DTC code
    if _DTC_RE.search(prompt):
        return True, _detect_make(lower)

    # Tier 2: Single strong-signal keyword (unambiguously automotive-diagnostic)
    for kw in _STRONG_KEYWORDS:
        if re.search(r"\b" + re.escape(kw) + r"\b", lower):
            return True, _detect_make(lower)

    # Tier 3: Year + make/model context + any symptom
    has_year = bool(_YEAR_RE.search(prompt))
    keyword_hits = sum(1 for kw in _SYMPTOM_KEYWORDS if kw in lower)
    has_make = _detect_make(lower) is not None

    if has_year and (has_make or keyword_hits >= 1):
        return True, _detect_make(lower)

    # Tier 4: 2+ general symptom keywords (catches follow-up in diagnostic session)
    if keyword_hits >= 2:
        return True, _detect_make(lower)

    return False, None


def _detect_make(lower: str) -> str | None:
    """Return the first vehicle make found in the text, or None."""
    for make in _MAKES:
        if re.search(r"\b" + re.escape(make) + r"\b", lower):
            return make
    return None


def build_skill_context(make: str | None, phase: int = 1, violations: list[str] | None = None) -> str:
    """Build the skill reminder context string to inject."""
    protocol_line = ""
    if make and make in _MAKE_TO_PROTOCOL:
        proto = _MAKE_TO_PROTOCOL[make]
        protocol_line = (
            f"\n- Also load: skills/references/manufacturers/{proto} (detected make: {make.upper()})"
        )

    phase_name = PHASES.get(phase, "Information Gathering")
    phase_line = f"Current session phase: {phase} — {phase_name}\n"

    violation_block = ""
    if violations:
        violation_block = (
            "\n⚠️ DIAGNOSTIC QUALITY VIOLATIONS FROM PREVIOUS RESPONSE:\n"
            + "\n".join(f"  - {v}" for v in violations)
            + "\nPlease address these violations in your current response.\n"
        )

    return (
        "🔧 DIAGNOSTIC SKILL REMINDER — MANDATORY PROTOCOL\n\n"
        f"{phase_line}"
        "A vehicle diagnostic request has been detected. Before responding, you MUST:\n\n"
        "1. Read skills/SKILL.md — master protocol and output format\n"
        f"2. Load required reference files from skills/references/{protocol_line}\n"
        "3. Classify request type (Type 1–6 per SKILL.md)\n"
        "4. Output routing header as FIRST LINE:\n"
        "   [Request Type: X | Loading: skill.md, ...]\n"
        "5. Apply the full CO-STAR diagnostic framework\n"
        "6. Use categorical assessment levels ONLY (STRONG INDICATION / PROBABLE / POSSIBLE / INSUFFICIENT BASIS)\n"
        "7. Include mandatory 📚 SOURCES and ⚖️ DISCLAIMER sections\n"
        "8. Update logs/{session_id}/diagnostic-session.json after each phase\n\n"
        "Shortcut: /diagnose command enforces all of this automatically.\n"
        "Skipping this protocol violates safety standards for this project."
        + violation_block
    )


def _extract_vehicle_year(prompt: str) -> str | None:
    """Extract a vehicle year from the prompt text."""
    m = _YEAR_RE.search(prompt)
    return m.group(1) if m else None


def _extract_dtc_codes(prompt: str) -> list[str]:
    """Extract all DTC codes from the prompt text."""
    return [m.upper() for m in _DTC_RE.findall(prompt)]


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    try:
        raw_input = sys.stdin.read()
        data = json.loads(raw_input)
    except (json.JSONDecodeError, Exception):
        sys.exit(0)

    session_id = data.get("session_id", "unknown")
    prompt = data.get("prompt", "")

    # ── Audit logging ──────────────────────────────────────────────────────
    try:
        log_dir = ensure_session_log_dir(session_id)
        log_file = log_dir / "prompts.json"

        entries: list[dict] = []
        if log_file.exists():
            content = log_file.read_text(encoding="utf-8").strip()
            if content:
                entries = json.loads(content)

        entries.append({
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "session_id": session_id,
            "prompt_length": len(prompt),
            "prompt_preview": prompt[:200] if prompt else "",
        })

        log_file.write_text(
            json.dumps(entries, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
    except Exception:
        pass  # Never block on logging failure

    # ── Diagnostic skill injection + session state ─────────────────────────
    is_diagnostic, detected_make = detect_diagnostic_request(prompt)

    if is_diagnostic:
        # Update session state with any extractable info from the prompt
        phase = 1
        violations: list[str] = []
        try:
            # Extract vehicle info and DTCs from prompt
            year = _extract_vehicle_year(prompt)
            dtcs = _extract_dtc_codes(prompt)

            # Build vehicle kwargs (only include non-None values)
            vehicle_fields: dict[str, str] = {}
            if year:
                vehicle_fields["year"] = year
            if detected_make:
                vehicle_fields["make"] = detected_make

            # Update state with extracted info
            if vehicle_fields:
                state = update_vehicle(session_id, **vehicle_fields)
            else:
                state = load_or_create(session_id)

            if dtcs:
                state = add_dtc_codes(session_id, dtcs)

            # Extract symptoms from prompt keywords for state tracking
            lower = prompt.lower()
            detected_symptoms = [
                kw for kw in _SYMPTOM_KEYWORDS
                if kw in lower and len(kw) > 5  # skip very short generic words
            ]
            if detected_symptoms:
                state = add_symptoms(session_id, detected_symptoms[:5])  # cap at 5

            # Auto-advance phase based on updated state
            state = auto_advance_phase(state)
            save_state(session_id, state)

            phase = state.get("phase", 1)
            violations = state.get("violations", [])
        except Exception:
            pass  # Never block on state management failure

        context = build_skill_context(detected_make, phase=phase, violations=violations)
        print(json.dumps({"context": context}))

    sys.exit(0)


if __name__ == "__main__":
    main()
