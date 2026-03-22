# Checked AGENTS.md - implementing directly because this is a pure data/functions
# utility module with fully-specified constants and no safety-critical logic.
# Gemini delegation would add no value over a well-defined spec.
"""
phase_context.py — Phase-sliced context injection for the automotive diagnostic harness.

Instead of injecting a monolithic SKILL.md reminder on every diagnostic prompt,
this module maps each of the 7 ASE diagnostic phases to only the reference files
that are actually needed at that point in the workflow.

Pure data + functions: no side effects, no I/O, no external imports.
"""

from __future__ import annotations

# ---------------------------------------------------------------------------
# Reference file paths (relative to project root)
# ---------------------------------------------------------------------------

SKILL_OVERVIEW = "skills/SKILL.md"
DIAGNOSTIC_PROCESS = "skills/references/diagnostic-process.md"
ANTI_HALLUCINATION = "skills/references/anti-hallucination.md"
OBD_II = "skills/references/obd-ii-methodology.md"
WARRANTY_FAILURES = "skills/references/warranty-failures.md"

# Manufacturer protocol map: normalised make token → filename under
# skills/references/manufacturers/
_MFG_PROTOCOL_MAP: dict[str, str] = {
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

_MFG_DIR = "skills/references/manufacturers/"

# ---------------------------------------------------------------------------
# Phase → references mapping
# Phase numbers follow the 7-phase ASE methodology defined in SKILL.md.
# Each entry lists the base references to load (manufacturer protocol is
# added dynamically when the make is known).
# ---------------------------------------------------------------------------

_PHASE_REFERENCES: dict[int, list[str]] = {
    1: [SKILL_OVERVIEW],
    2: [],                                           # safety rules loaded via Phase 1 files
    3: [],                                           # manufacturer protocol injected dynamically
    4: [DIAGNOSTIC_PROCESS, ANTI_HALLUCINATION],    # + manufacturer protocol (dynamic)
    5: [DIAGNOSTIC_PROCESS],
    6: [ANTI_HALLUCINATION],
    7: [ANTI_HALLUCINATION],
}

# ---------------------------------------------------------------------------
# Phase → human-readable focus description
# ---------------------------------------------------------------------------

_PHASE_FOCUS: dict[int, str] = {
    1: "Gather all available vehicle info and symptoms. Do NOT diagnose yet.",
    2: (
        "Assess safety implications. Flag safety-critical systems "
        "(brakes, steering, airbags). Apply park-it criteria if applicable."
    ),
    3: (
        "Identify affected system (P/C/B/U). Load manufacturer-specific "
        "protocol for known make."
    ),
    4: (
        "Generate differential top-5. Apply Evidence FOR/AGAINST each candidate. "
        "Use categorical assessment levels only (STRONG INDICATION / PROBABLE / "
        "POSSIBLE / INSUFFICIENT BASIS — never percentages)."
    ),
    5: (
        "Design ordered test sequence. Most decisive, least invasive tests first. "
        "Include scan tool live data, component tests, and circuit checks."
    ),
    6: (
        "State primary recommendation. Include parts, labor estimate range, "
        "and confidence ceiling. Flag any remaining uncertainty."
    ),
    7: (
        "Cite every data source used (NHTSA complaint count, TSB numbers, "
        "recall campaign IDs, forum references). Include mandatory DISCLAIMER."
    ),
}

# ---------------------------------------------------------------------------
# Phase → required output sections (strings that MUST appear in the response)
# ---------------------------------------------------------------------------

_PHASE_REQUIRED_SECTIONS: dict[int, list[str]] = {
    1: ["[Request Type: X | Loading: Y]", "📋 DATA ASSESSMENT"],
    2: ["🚨 SAFETY"],
    3: ["## SYMPTOM SUMMARY"],
    4: ["## DIFFERENTIAL DIAGNOSIS", "Assessment Level:"],
    5: ["## DIAGNOSTIC TEST SEQUENCE"],
    6: ["## PRIMARY RECOMMENDATION"],
    7: ["📚 SOURCES", "⚖️ DISCLAIMER"],
}

# ---------------------------------------------------------------------------
# Request-type overrides
# When the request is NOT a full Type 1 diagnostic, these mappings replace
# the phase-based reference list with a more targeted set.
# ---------------------------------------------------------------------------

_REQUEST_TYPE_REFERENCES: dict[int, list[str]] = {
    1: [],                          # full diagnostic — use phase map
    2: [OBD_II],                    # DTC interpretation
    3: [DIAGNOSTIC_PROCESS],        # component testing procedure
    4: [WARRANTY_FAILURES],         # TSB / recall / known-issues research (+ mfg protocol dynamic)
    5: [],                          # educational — single most-relevant determined at runtime
    6: [],                          # cost/time estimate
}

_REQUEST_TYPE_FOCUS: dict[int, str] = {
    1: "Full 7-phase ASE diagnostic workflow.",
    2: "DTC interpretation: decode code, list likely causes, severity, next steps.",
    3: "Step-by-step component test procedure with expected values.",
    4: "TSB and recall research: list applicable bulletins, recall status, remedies.",
    5: "Explain the concept clearly for a professional mechanic audience.",
    6: "Provide cost and time range with appropriate caveats and confidence ceiling.",
}

# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _resolve_mfg_protocol(make: str) -> str | None:
    """Return the full relative path to the manufacturer protocol file, or None."""
    token = make.strip().lower()
    filename = _MFG_PROTOCOL_MAP.get(token)
    if filename is None:
        return None
    return _MFG_DIR + filename


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def get_phase_references(phase: int, make: str = "") -> list[str]:
    """Return the ordered list of reference file paths for the given diagnostic phase.

    Manufacturer protocol is appended when *make* is known and *phase* is 3 or 4.

    Args:
        phase: Diagnostic phase number (1-7).
        make: Vehicle make string (e.g. "Ford", "CHEVROLET"). Case-insensitive.

    Returns:
        List of relative file paths to load for this phase.
    """
    if phase not in _PHASE_REFERENCES:
        return [SKILL_OVERVIEW]

    refs: list[str] = list(_PHASE_REFERENCES[phase])

    if phase in (3, 4) and make:
        mfg = _resolve_mfg_protocol(make)
        if mfg and mfg not in refs:
            refs.append(mfg)

    return refs


def get_phase_focus(phase: int) -> str:
    """Return the single-sentence focus instruction for the given diagnostic phase.

    Args:
        phase: Diagnostic phase number (1-7).

    Returns:
        Focus string describing what the model should concentrate on.
    """
    return _PHASE_FOCUS.get(phase, "Follow SKILL.md protocol.")


def get_required_sections(phase: int) -> list[str]:
    """Return the list of output section headers that MUST appear in the response.

    Args:
        phase: Diagnostic phase number (1-7).

    Returns:
        List of required section marker strings.
    """
    return list(_PHASE_REQUIRED_SECTIONS.get(phase, []))


def get_request_type_references(request_type: int, make: str = "") -> list[str]:
    """Return reference paths for a specific request type (non-full-diagnostic).

    For Type 4 (known issues), the manufacturer protocol is also appended
    when *make* is known.

    Args:
        request_type: SKILL.md request type number (1-6).
        make: Vehicle make string. Case-insensitive.

    Returns:
        List of relative file paths to load.
    """
    if request_type not in _REQUEST_TYPE_REFERENCES:
        return [SKILL_OVERVIEW]

    refs: list[str] = list(_REQUEST_TYPE_REFERENCES[request_type])

    if request_type == 4 and make:
        mfg = _resolve_mfg_protocol(make)
        if mfg and mfg not in refs:
            refs.append(mfg)

    return refs


def get_request_type_focus(request_type: int) -> str:
    """Return the focus instruction for the given request type.

    Args:
        request_type: SKILL.md request type number (1-6).

    Returns:
        Focus string.
    """
    return _REQUEST_TYPE_FOCUS.get(request_type, "Follow SKILL.md protocol.")


def build_phase_context_block(
    phase: int,
    make: str = "",
    data_level: str = "STANDARD",
    confidence_ceiling: str = "PROBABLE",
) -> str:
    """Build the formatted context injection string for the given diagnostic phase.

    This string is inserted into the prompt as a lightweight reminder of what
    the model should load and produce — without re-injecting the full SKILL.md.

    Args:
        phase: Diagnostic phase number (1-7).
        make: Vehicle make string (e.g. "Ford"). Used to resolve manufacturer protocol.
        data_level: Evidence quality level (e.g. "STANDARD", "LIMITED", "RICH").
        confidence_ceiling: Maximum categorical confidence the evidence supports
            (e.g. "STRONG INDICATION", "PROBABLE", "POSSIBLE", "INSUFFICIENT BASIS").

    Returns:
        A formatted multi-line string ready for prompt injection.

    Example output::

        📍 PHASE 4: Differential Diagnosis
        Load: skills/references/diagnostic-process.md, skills/references/anti-hallucination.md, skills/references/manufacturers/ford-protocols.md
        Focus: Generate differential top-5. Apply Evidence FOR/AGAINST. Use categorical assessment levels only.
        Required output: ## DIFFERENTIAL DIAGNOSIS + Assessment Level:
        Data Level: STANDARD → Confidence Ceiling: PROBABLE
    """
    phase_names: dict[int, str] = {
        1: "Information Gathering",
        2: "Safety Assessment",
        3: "System Identification",
        4: "Differential Diagnosis",
        5: "Test Sequence Design",
        6: "Primary Recommendation",
        7: "Source Attribution",
    }
    name = phase_names.get(phase, f"Phase {phase}")

    refs = get_phase_references(phase, make)
    load_str = (
        ", ".join(refs) if refs
        else "(none — apply rules from Phase 1 loaded files)"
    )

    focus = get_phase_focus(phase)

    required = get_required_sections(phase)
    required_str = " + ".join(required) if required else "(none)"

    lines = [
        f"📍 PHASE {phase}: {name}",
        f"Load: {load_str}",
        f"Focus: {focus}",
        f"Required output: {required_str}",
        f"Data Level: {data_level} → Confidence Ceiling: {confidence_ceiling}",
    ]
    return "\n".join(lines)
