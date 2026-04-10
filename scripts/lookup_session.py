#!/usr/bin/env python3
# Checked AGENTS.md - implementing directly because this is a read-only CLI
# query tool over local session files. No auth surfaces, no DB writes,
# no complex logic. Single-purpose search wrapper around SessionStore.
"""
lookup_session.py — Find past diagnostic sessions by VIN, RO number, or vehicle.

Usage:
    uv run python scripts/lookup_session.py --vin WBA3D5C52FK291262
    uv run python scripts/lookup_session.py --ro RO-1234
    uv run python scripts/lookup_session.py --make BMW --model 328d --year 2015
    uv run python scripts/lookup_session.py --recent 10
    uv run python scripts/lookup_session.py --list

Returns a human-readable summary of matching sessions with PDF paths.
"""

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.diagnostic.session_state import DiagnosticSession
from src.diagnostic.session_store import SessionStore


def _pdf_from_session(session: DiagnosticSession) -> str:
    """Extract PDF path from session log notes."""
    for entry in reversed(session.full_log):
        note = entry.get("note", "")
        if note.startswith("PDF: "):
            return note[5:].strip()
    return "not recorded"


def _diagnosis_from_session(session: DiagnosticSession) -> str:
    """Extract confirmed diagnosis label from session log."""
    for entry in reversed(session.full_log):
        if entry.get("type") == "hypothesis" and entry.get("status") == "confirmed":
            return entry.get("label", "")
    return ""


def _findings_from_session(session: DiagnosticSession) -> str:
    """Extract findings summary note."""
    for entry in session.full_log:
        note = entry.get("note", "")
        if note.startswith("Findings: "):
            return note[10:].strip()
    return ""


def _assessment_from_session(session: DiagnosticSession) -> str:
    """Extract assessment level."""
    for entry in session.full_log:
        note = entry.get("note", "")
        if note.startswith("Assessment level: "):
            return note[18:].strip()
    return ""


def format_session(session: DiagnosticSession, index: int | None = None) -> str:
    v = session.vehicle
    vehicle_str = f"{v.get('year', '')} {v.get('make', '')} {v.get('model', '')}"
    vin = v.get("vin", "N/A")
    mileage = v.get("mileage", "N/A")
    date = session.created_at[:10]
    ro = f"RO: {session.repair_order}" if session.repair_order else "No RO"
    diagnosis = _diagnosis_from_session(session)
    assessment = _assessment_from_session(session)
    pdf = _pdf_from_session(session)
    short_id = session.session_id[:8]

    prefix = f"[{index}] " if index is not None else ""
    lines = [
        f"{prefix}{vehicle_str}  |  {ro}  |  {date}",
        f"    VIN: {vin}  |  Mileage: {mileage}",
        f"    Symptoms: {session.symptoms}",
    ]
    if diagnosis:
        lines.append(f"    Diagnosis: {diagnosis}" + (f"  [{assessment}]" if assessment else ""))
    lines += [
        f"    Phase: {session.phase}",
        f"    Session ID: {session.session_id}  (short: {short_id})",
        f"    PDF: {pdf}",
    ]
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description="Look up past diagnostic sessions")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--vin",    help="Search by VIN")
    group.add_argument("--ro",     help="Search by repair order number")
    group.add_argument("--make",   help="Search by vehicle make (combine with --model, --year)")
    group.add_argument("--recent", type=int, metavar="N", help="Show N most recent sessions")
    group.add_argument("--list",   action="store_true", help="List all sessions (summary only)")
    parser.add_argument("--model", help="Vehicle model (used with --make)")
    parser.add_argument("--year",  type=int, help="Vehicle year (used with --make)")
    parser.add_argument(
        "--sessions-dir",
        help="Override sessions directory (default: data/sessions/)",
        default=None,
    )
    args = parser.parse_args()

    store = SessionStore(sessions_dir=args.sessions_dir)

    if store.count() == 0:
        print("No sessions found in data/sessions/")
        sys.exit(0)

    sessions: list[DiagnosticSession] = []

    if args.vin:
        sessions = store.find_by_vin(args.vin)
        label = f"VIN={args.vin}"

    elif args.ro:
        s = store.find_by_repair_order(args.ro)
        sessions = [s] if s else []
        label = f"RO={args.ro}"

    elif args.make:
        sessions = store.find_by_vehicle(
            make=args.make,
            model=args.model,
            year=args.year,
        )
        label = " ".join(filter(None, [
            args.make, args.model, str(args.year) if args.year else None
        ]))

    elif args.recent:
        sessions = store.find_recent(args.recent)
        label = f"recent {args.recent}"

    elif args.list:
        summaries = store.list_summaries()
        print(f"=== {len(summaries)} session(s) in data/sessions/ ===\n")
        for i, fm in enumerate(summaries, 1):
            year  = fm.get("vehicle_year", "")
            make  = fm.get("vehicle_make", "")
            model = fm.get("vehicle_model", "")
            ro    = fm.get("repair_order", "—")
            date  = str(fm.get("created_at", ""))[:10]
            phase = fm.get("phase", "")
            sid   = fm.get("session_id", "")[:8]
            print(f"  {i:3}. {date}  {year} {make} {model}  RO:{ro}  {phase}  [{sid}]")
        return

    if not sessions:
        print(f"No sessions found for {label}")
        sys.exit(0)

    print(f"=== {len(sessions)} session(s) found for {label} ===\n")
    for i, session in enumerate(sessions, 1):
        print(format_session(session, index=i if len(sessions) > 1 else None))
        if i < len(sessions):
            print()


if __name__ == "__main__":
    main()
