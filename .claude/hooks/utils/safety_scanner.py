# Checked AGENTS.md - implementing directly because this is safety-critical
# automotive logic that must stay with Claude per GEMINI_WORKFLOW.md.
"""safety_scanner.py — Safety flag extraction for the diagnostic harness.

Phase 4 feature: auto-populates session_state.safety_flags by scanning
incoming prompts for safety-critical keywords. Each matched pattern
produces a structured flag string that is persisted to session state.

The Human-in-the-Loop (HitL) gate in user_prompt_submit.py reads these
flags and injects a mandatory acknowledgment request until the mechanic
runs /confirm-safety.

Pure functions — no I/O, no side effects.
"""

from __future__ import annotations

import re

# ---------------------------------------------------------------------------
# Pattern → flag string mapping
# Each tuple: (regex_pattern, human-readable flag string)
# Patterns use word boundaries to avoid false substring matches.
# ---------------------------------------------------------------------------

_SAFETY_PATTERNS: list[tuple[re.Pattern[str], str]] = [
    (re.compile(r"\bbrakes?\b", re.IGNORECASE),
     "Braking system — verify full brake function before vehicle movement"),

    (re.compile(r"\babs\b", re.IGNORECASE),
     "ABS / Anti-lock braking — verify ABS operation before driving"),

    (re.compile(r"\bairbag\b|\bsrs\b|\bair\s+bag\b", re.IGNORECASE),
     "Airbag / SRS — do not operate until hands-on inspection confirms safe"),

    (re.compile(r"\bsteering\b|\beps\b|\bpower\s+steering\b", re.IGNORECASE),
     "Steering system — verify directional control before driving"),

    (re.compile(r"\btires?\b|\bblowout\b|\btread\b|\bsidewall\b", re.IGNORECASE),
     "Tire / wheel safety concern — inspect before driving"),

    (re.compile(r"\bfire\b|\bsmoke\b|\bburning\s+smell\b", re.IGNORECASE),
     "Fire / smoke hazard — do NOT operate vehicle"),

    (re.compile(r"\bfuel\s+leak\b|\bgas\s+leak\b|\bfuel\s+drip", re.IGNORECASE),
     "Fuel leak — fire hazard, do NOT operate vehicle"),

    (re.compile(r"\bloss\s+of\s+control\b|\bcontrol\s+loss\b", re.IGNORECASE),
     "Loss of vehicle control reported — do NOT operate until root cause confirmed"),

    (re.compile(r"\bpark.?it\b|\bdo\s+not\s+driv|\bdon.?t\s+driv", re.IGNORECASE),
     "Park-it advisory or do-not-drive condition — vehicle must not be moved"),

    (re.compile(r"\brollover\b|\btip\s*over\b", re.IGNORECASE),
     "Rollover / stability risk — do NOT operate until inspected"),

    (re.compile(r"\bmaster\s+cylinder\b|\bbrake\s+fluid\b|\bbrake\s+line\b",
                re.IGNORECASE),
     "Hydraulic brake system component — verify brake pedal feel and fluid level"),

    (re.compile(r"\btie\s+rod\b|\bball\s+joint\b|\bcontrol\s+arm\b|\bsteering\s+rack\b",
                re.IGNORECASE),
     "Steering / suspension safety component — verify alignment and handling before driving"),

    (re.compile(r"\bframe\b|\bsubframe\b|\brust\s+through\b|\bstructural\b",
                re.IGNORECASE),
     "Structural integrity concern — vehicle may not be safe to operate"),
]

# Flags that indicate the vehicle should NOT be driven at all
_NO_DRIVE_FLAGS: frozenset[str] = frozenset({
    "Airbag / SRS — do not operate until hands-on inspection confirms safe",
    "Fire / smoke hazard — do NOT operate vehicle",
    "Fuel leak — fire hazard, do NOT operate vehicle",
    "Loss of vehicle control reported — do NOT operate until root cause confirmed",
    "Park-it advisory or do-not-drive condition — vehicle must not be moved",
    "Rollover / stability risk — do NOT operate until inspected",
})


def extract_safety_flags(text: str) -> list[str]:
    """Scan *text* for safety-critical keywords and return a list of flag strings.

    Args:
        text: Prompt or message text to scan.

    Returns:
        Deduplicated list of safety flag strings. Empty list if no flags found.
    """
    found: list[str] = []
    seen: set[str] = set()
    for pattern, flag in _SAFETY_PATTERNS:
        if pattern.search(text) and flag not in seen:
            found.append(flag)
            seen.add(flag)
    return found


def is_no_drive(flags: list[str]) -> bool:
    """Return True if any flag in *flags* indicates the vehicle must not be driven.

    Args:
        flags: List of safety flag strings from session state.

    Returns:
        True if any flag is a no-drive condition.
    """
    return any(f in _NO_DRIVE_FLAGS for f in flags)


def build_hitl_gate(flags: list[str], vehicle_desc: str = "") -> str:
    """Build the Human-in-the-Loop gate injection string.

    Injected into context when safety flags are present and the mechanic
    has not yet acknowledged them via /confirm-safety.

    Args:
        flags: Active safety flags from session state.
        vehicle_desc: Human-readable vehicle description (e.g. "2018 Ford F-150").

    Returns:
        Formatted gate string for context injection.
    """
    no_drive = is_no_drive(flags)
    vehicle_line = f"Vehicle: {vehicle_desc}\n" if vehicle_desc else ""

    flag_lines = "\n".join(f"  ⚠️  {f}" for f in flags)

    drive_advisory = (
        "\n🚫 DO NOT DRIVE ADVISORY: One or more flags indicate the vehicle must "
        "not be operated until a hands-on inspection is completed."
        if no_drive
        else "\n⚠️  DRIVE WITH CAUTION: Verify safety-critical system before vehicle movement."
    )

    return (
        "🛑 SAFETY GATE — HUMAN ACKNOWLEDGMENT REQUIRED\n\n"
        f"{vehicle_line}"
        "Active safety flags:\n"
        f"{flag_lines}\n"
        f"{drive_advisory}\n\n"
        "REQUIRED BEFORE PROCEEDING:\n"
        "• Inform the mechanic of the above safety concerns explicitly\n"
        "• Do NOT recommend test procedures requiring vehicle movement until acknowledged\n"
        "• Mechanic must run /confirm-safety to acknowledge and clear this gate\n"
        "• If vehicle is customer-facing, recommend DO NOT DRIVE until inspection complete"
    )
