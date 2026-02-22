#!/usr/bin/env python3
"""
Vehicle Diagnostic Router - OBD-II Classification Engine
Purpose: Route diagnostic requests to appropriate domain-specific skills
Targets: Ford F150, Chevy Silverado 1500, Ram 1500

Usage:
    python classify_problem.py "P0335"
    python classify_problem.py "P0300 misfire rough idle" Ford F150 2020

Author: Professional Diagnostic System
Date: 2025-10-30

Checked AGENTS.md - implementing directly because this is a lint-only fix
(E701 one-liners, mypy Optional types, return type annotation). No logic
changes, no new security surface. security-engineer review not required.
"""

import json
import sys
import requests  # type: ignore[import-untyped]
from typing import Dict, Optional, Tuple

# RAG Server Configuration
RAG_SERVER_URL = "http://localhost:8000/search"
RAG_API_KEY = "mechanic-secret-key-123"

# OBD-II Domain Classification Map
OBD_DOMAIN_MAP = {
    "P00": "engine",       # Misfire
    "P01": "engine",       # Fuel/Air System
    "P02": "engine",       # Fuel System
    "P03": "engine",       # Ignition System
    "P04": "engine",       # Emissions Control
    "P05": "engine",       # Speed/Idle/Auxiliary Controls
    "P06": "electrical",   # PCM Issues
    "P07": "transmission", # Transmission
    "P08": "transmission", # Transmission
    "P09": "electrical",   # Reserved
    "P10": "engine",       # Manufacturer Specific (general engine)
    "P11": "engine",       # Manufacturer Specific (engine)
    "P12": "engine",       # Manufacturer Specific (engine)
    "P13": "transmission", # Manufacturer Specific (transmission)
    "B00": "electrical",   # Body Systems
    "B01": "electrical",   # Body Systems
    "B02": "electrical",   # Body Systems
    "C00": "chassis",      # Chassis (Brakes/Suspension)
    "C01": "chassis",      # Chassis (Brakes/Suspension)
    "C02": "chassis",      # Chassis (Brakes/Suspension)
    "C12": "chassis",      # Example: ABS/Dynamic Stability
    "U00": "electrical",   # Network / CAN Bus
    "U01": "electrical",   # Network / CAN Bus
    "U02": "electrical",   # Network / CAN Bus
}

# Vehicle-Specific Known Issues
VEHICLE_ISSUES = {
    "Ford": {
        "F150": {
            "default": ["intake valve carbon buildup", "fuel pump module failure", "EcoBoost knock"],
            "2017-2020": ["fuel pump internal failure (TSB 18-0108)", "extended injector pulse"],
            "5.0L": ["cylinder head thermal stress", "spark plug fouling"],
        }
    },
    "Chevrolet": {
        "Silverado 1500": {
            "default": ["AFM lifter collapse", "5.3L oil consumption", "P0335 CKP water damage"],
            "2014-2020": ["transmission shift quality issues", "torque converter shudder"],
            "5.3L": ["excessive oil consumption after 100K miles", "valve train noise"],
        }
    },
    "Ram": {
        "1500": {
            "default": ["TIPM electrical failures", "5.7L HEMI lifter problems", "transmission valve body wear"],
            "2009-2016": ["TIPM fuel pump relay failure", "random electrical gremlins"],
            "5.7L": ["VVT cam/lifter wear", "oil pump bypass valve sticking"],
        }
    }
}

# Critical Codes (Stop Drive)
CRITICAL_CODES = [
    "P0600", "P0601",  # PCM faults
    "C0040", "C0050",  # Brake system failure
    "U0100",           # CAN bus failure
    "U0402",           # CAN bus lost communication
    "U0100",           # CAN bus high/low
]


def extract_code(problem_string: str) -> Optional[str]:
    """Extract OBD code from input string (e.g. 'P0335' from 'P0335 misfire')"""
    parts = problem_string.upper().split()
    for part in parts:
        if len(part) >= 5 and part[0] in ["P", "B", "C", "U"] and part[1:].replace("X", "").isdigit():
            return part
    return None


def get_domain(obd_code: str) -> Tuple[str, float]:
    """
    Classify OBD code to diagnostic domain
    Returns: (domain, confidence)
    """
    if not obd_code or len(obd_code) < 3:
        return ("unknown", 0.0)

    obd_upper = obd_code.upper()
    code_prefix = obd_upper[:3] if len(obd_upper) >= 3 else obd_upper  # P0X, P1X, etc.

    # Exact match in map (for full 5-char codes like P0335)
    if len(obd_upper) >= 5 and code_prefix in OBD_DOMAIN_MAP:
        return (OBD_DOMAIN_MAP[code_prefix], 0.95)

    # Match for partial codes (P0, P03, etc.)
    if code_prefix in OBD_DOMAIN_MAP:
        confidence = 0.95 if len(obd_upper) >= 4 else 0.85
        return (OBD_DOMAIN_MAP[code_prefix], confidence)

    # Fallback: use first two characters
    short_prefix = obd_upper[:2]
    for key, domain in OBD_DOMAIN_MAP.items():
        if key.startswith(short_prefix):
            return (domain, 0.85)

    return ("unknown", 0.0)


def get_severity(obd_code: str, symptoms: str = "") -> str:
    """Classify problem severity"""
    obd_upper = obd_code.upper()

    if obd_upper in CRITICAL_CODES:
        return "CRITICAL"

    # Transmission codes are HIGH severity
    if obd_upper.startswith("P07") or obd_upper.startswith("P08"):
        return "HIGH"

    # Chassis/Brake codes are HIGH severity
    if obd_upper.startswith("C"):
        return "HIGH"

    # Check symptoms for severity escalation
    symptoms_lower = symptoms.lower()

    if "stall" in symptoms_lower or "no start" in symptoms_lower or "hard start" in symptoms_lower:
        return "HIGH"

    if "brake" in symptoms_lower or "steering" in symptoms_lower or "wobble" in symptoms_lower:
        return "CRITICAL"  # Safety issue

    if "rough" in symptoms_lower or "misfire" in symptoms_lower or "harsh" in symptoms_lower or "electrical" in symptoms_lower:
        return "MEDIUM"

    return "LOW"


def get_vehicle_context(make: str, model: str, year: Optional[int] = None, engine: Optional[str] = None) -> Dict:
    """Get vehicle-specific common issues"""
    if make not in VEHICLE_ISSUES:
        return {"make": make, "model": model, "common_issues": []}

    if model not in VEHICLE_ISSUES[make]:
        return {"make": make, "model": model, "common_issues": []}

    vehicle_data = VEHICLE_ISSUES[make][model]
    issues = vehicle_data.get("default", [])

    # Add year-specific issues
    if year and f"{year-1}-{year+1}" in vehicle_data:
        year_key = [k for k in vehicle_data.keys() if "-" in k and int(k.split("-")[0]) <= year <= int(k.split("-")[1])]
        if year_key:
            issues.extend(vehicle_data[year_key[0]])

    # Add engine-specific issues
    if engine and engine in vehicle_data:
        issues.extend(vehicle_data[engine])

    return {
        "make": make,
        "model": model,
        "year": year,
        "engine": engine,
        "common_issues": list(set(issues))  # Remove duplicates
    }


def route_diagnostic(obd_code: str, make: str = "", model: str = "", year: Optional[int] = None,
                     engine: str = "", symptoms: str = "") -> Dict:
    """
    Main routing function

    Args:
        obd_code: OBD-II code (e.g., 'P0335')
        make: Vehicle make (Ford, Chevrolet, Ram)
        model: Vehicle model (F150, Silverado 1500, Ram 1500)
        year: Model year
        engine: Engine size (e.g., '5.0L')
        symptoms: Symptom description

    Returns:
        Routing decision with domain, confidence, and vehicle context
    """
    # Extract code if not provided
    if not obd_code:
        return {
            "status": "error",
            "message": "No OBD code provided",
            "routing_decision": None
        }

    obd_upper = obd_code.upper()

    # Get domain and confidence
    domain, confidence = get_domain(obd_code)
    severity = get_severity(obd_code, symptoms)

    # Get vehicle context
    vehicle_context = get_vehicle_context(make, model, year, engine)

    # Determine if critical
    is_critical = obd_upper in CRITICAL_CODES or severity == "CRITICAL"

    # Build routing decision
    routing_decision = {
        "domain": domain,
        "reason": f"{obd_code} classified as {domain.upper()} system",
        "next_skill": f"{domain}_skill_v1" if domain != "unknown" else None,
        "confidence": confidence,
        "obd_code": obd_code,
        "severity": severity,
        "is_critical": is_critical,
    }

    # Add warning if critical
    if is_critical and severity == "CRITICAL":
        routing_decision["warning"] = "STOP-DRIVE: Safety-critical fault detected. Check brakes, airbags, or steering immediately."
    elif domain == "unknown":
        routing_decision["warning"] = "Unknown OBD code - may require manual review"

    # --- RAG INTEGRATION ---
    # Query the local knowledge base for real-world complaints
    rag_data = []
    try:
        # Construct a search query from available context
        search_parts = []
        if year:
            search_parts.append(str(year))
        if make:
            search_parts.append(make)
        if model:
            search_parts.append(model)

        # Use the raw input code (which might contain text) or just the clean code
        search_parts.append(obd_code)
        if symptoms:
            search_parts.append(symptoms)

        query_str = " ".join(search_parts)

        # Call the RAG Server (Attempt 1: Specific Code)
        resp = requests.get(
            RAG_SERVER_URL,
            headers={"X-API-KEY": RAG_API_KEY},
            params={"query": query_str, "limit": 3},
            timeout=2.0
        )
        if resp.status_code == 200:
            rag_data = resp.json().get("results", [])

        # --- FALLBACK SEARCH ---
        # If no results found for specific code, try broader search with Domain (e.g. "P0300" -> "engine")
        if not rag_data and domain != "unknown":
            fallback_parts = []
            if year:
                fallback_parts.append(str(year))
            if make:
                fallback_parts.append(make)
            if model:
                fallback_parts.append(model)
            fallback_parts.append(domain)  # Add "engine", "transmission", etc.
            if symptoms:
                fallback_parts.append(symptoms)

            fallback_query = " ".join(fallback_parts)

            resp = requests.get(
                RAG_SERVER_URL,
                headers={"X-API-KEY": RAG_API_KEY},
                params={"query": fallback_query, "limit": 3},
                timeout=2.0
            )
            if resp.status_code == 200:
                rag_data = resp.json().get("results", [])

    except Exception:
        # specific error handling or logging could go here
        pass

    # --- TSB INTEGRATION ---
    tsb_hits = []
    try:
        # Construct TSB query: Year Make Model + Code + Domain (Component)
        # TSBs are often indexed by component, so "engine" or "transmission" helps
        tsb_parts = []
        if year:
            tsb_parts.append(str(year))
        if make:
            tsb_parts.append(make)
        if model:
            tsb_parts.append(model)
        if obd_code:
            tsb_parts.append(obd_code)
        if domain and domain != "unknown":
            tsb_parts.append(domain)

        tsb_query = " ".join(tsb_parts)

        resp = requests.get(
            "http://localhost:8000/search_tsbs",
            headers={"X-API-KEY": RAG_API_KEY},
            params={"query": tsb_query, "limit": 3},
            timeout=2.0
        )
        if resp.status_code == 200:
            tsb_hits = resp.json().get("results", [])
    except Exception:
        pass

    return {
        "status": "success",
        "routing_decision": routing_decision,
        "vehicle_profile": vehicle_context,
        "knowledge_base_hits": rag_data,
        "tsb_hits": tsb_hits,
        "recommendation": f"Route to {domain} skill for detailed analysis" if domain != "unknown" else "Classify error - escalate",
    }


def main():
    """CLI entry point"""
    if len(sys.argv) < 2:
        print("Usage: python classify_problem.py <OBD_CODE> [MAKE] [MODEL] [YEAR] [ENGINE]")
        print("\nExamples:")
        print("  python classify_problem.py P0335")
        print("  python classify_problem.py P0300 Ford F150 2020 5.0L")
        print("  python classify_problem.py P0700 Chevrolet 'Silverado 1500' 2018 5.3L")
        sys.exit(1)

    obd_code = sys.argv[1].upper() if len(sys.argv) > 1 else None
    make = sys.argv[2] if len(sys.argv) > 2 else ""
    model = sys.argv[3] if len(sys.argv) > 3 else ""
    year = int(sys.argv[4]) if len(sys.argv) > 4 and sys.argv[4].isdigit() else None
    engine = sys.argv[5] if len(sys.argv) > 5 else ""

    result = route_diagnostic(obd_code, make, model, year, engine)

    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
