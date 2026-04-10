#!/usr/bin/env python3
# Checked AGENTS.md - implementing directly because this is a thin persistence
# adapter between report JSON and SessionStore. No auth surfaces, no external
# API calls, no complex architecture decisions. Pure data mapping + file write.
"""
save_session.py — Persist a completed diagnostic session from report JSON.

Called by the /report command after PDF generation to close the loop between
diagnostic conversation and structured session storage.

Usage:
    uv run python scripts/save_session.py /tmp/diag_report_data.json
    uv run python scripts/save_session.py /tmp/diag_report_data.json --pdf /mnt/nas-reports/Customer/report.pdf

Output (stdout):
    SESSION_ID: <uuid>
    SESSION_FILE: <path>
"""

import argparse
import json
import sys
from pathlib import Path

# Allow running from project root
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.diagnostic.session_state import DiagnosticSession
from src.diagnostic.session_store import SessionStore


def build_session(data: dict, pdf_path: str | None = None) -> DiagnosticSession:
    """Map report JSON to a DiagnosticSession object."""

    v = data.get("vehicle", {})
    vehicle = {
        "year":   str(v.get("year", "")),
        "make":   str(v.get("make", "")).upper(),
        "model":  str(v.get("model", "")).upper(),
        "vin":    str(v.get("vin", "N/A")),
        "mileage": str(v.get("mileage", "N/A")),
    }

    symptoms = data.get("customer_concern", "").strip()
    ro_number = data.get("ro_number") or None

    session = DiagnosticSession.create(
        vehicle=vehicle,
        symptoms=symptoms,
        repair_order=ro_number,
    )

    # ── Populate the append-only log ─────────────────────────────────────────

    # Shop / technician context
    shop = data.get("shop_name", "")
    tech = data.get("technician_name", "")
    if shop or tech:
        session.add_note(f"Shop: {shop} | Technician: {tech}")

    # Diagnostic tests performed
    for test in data.get("diagnostic_tests", []):
        name   = test.get("test_name", "Test")
        result = test.get("result", "")
        sig    = test.get("significance", "")
        session.add_note(f"Test — {name}: {result}" + (f" | {sig}" if sig else ""))

    # Findings summary
    findings = data.get("findings", "").strip()
    if findings:
        session.add_note(f"Findings: {findings}")

    # Primary diagnosis as confirmed hypothesis
    diagnosis = data.get("diagnosis", "").strip()
    assessment = data.get("assessment_level", "").strip()
    if diagnosis:
        session.advance_turn(
            new_phase="REPORT_GENERATED",
            hypothesis_label=diagnosis,
            hypothesis_status="confirmed",
        )

    # Recommendations or work performed
    recs = data.get("recommendations", [])
    work = data.get("work_performed", [])
    action_items = recs or work
    if action_items:
        label = "Recommended" if recs else "Work performed"
        session.add_note(f"{label}: {' | '.join(action_items)}")

    # Declined services
    declined = data.get("declined_services", [])
    if declined:
        session.add_note(f"Declined: {' | '.join(declined)}")

    # Verification (post-repair)
    verification = data.get("verification", "").strip()
    if verification:
        session.add_note(f"Verification: {verification}")

    # Assessment level and PDF path
    if assessment:
        session.add_note(f"Assessment level: {assessment}")
    if pdf_path:
        session.add_note(f"PDF: {pdf_path}")

    return session


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Save a completed diagnostic session from report JSON"
    )
    parser.add_argument("input", help="Path to report JSON file")
    parser.add_argument("--pdf", help="Path to generated PDF report", default=None)
    parser.add_argument(
        "--ingest", action="store_true",
        help="Also ingest the session into the RAG vector store (ChromaDB)",
    )
    parser.add_argument(
        "--sessions-dir",
        help="Override sessions directory (default: data/sessions/)",
        default=None,
    )
    args = parser.parse_args()

    input_path = Path(args.input)
    if not input_path.exists():
        print(f"ERROR: Input file not found: {input_path}", file=sys.stderr)
        sys.exit(1)

    with open(input_path, encoding="utf-8") as f:
        data = json.load(f)

    session = build_session(data, pdf_path=args.pdf)

    store = SessionStore(sessions_dir=args.sessions_dir)
    session_file = store.save(session)

    print(f"SESSION_ID: {session.session_id}")
    print(f"SESSION_FILE: {session_file}")
    print(f"Vehicle: {session.vehicle.get('year')} {session.vehicle.get('make')} {session.vehicle.get('model')}")
    if session.repair_order:
        print(f"RO: {session.repair_order}")

    if args.ingest:
        import subprocess
        result = subprocess.run(
            [sys.executable, str(Path(__file__).parent / "ingest_session.py"), str(session_file)],
            capture_output=True, text=True,
        )
        print(result.stdout.strip())
        if result.returncode != 0:
            print(f"RAG ingest warning: {result.stderr.strip()}", file=sys.stderr)


if __name__ == "__main__":
    main()
