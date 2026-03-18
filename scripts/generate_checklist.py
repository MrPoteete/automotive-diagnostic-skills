# Checked AGENTS.md - implementing directly because this is a standalone CLI
# with no auth/sensitive data (read-only SQLite queries).
"""
Pre-Purchase Inspection Checklist generator for automotive mechanics.

Given a vehicle (make/model/year range), generates a one-page markdown
inspection checklist based on real NHTSA complaint, recall, and TSB data.

Run:
  .venv/bin/python3 scripts/generate_checklist.py --make FORD --model F-150 --year-start 2018 --year-end 2022
  .venv/bin/python3 scripts/generate_checklist.py --make HONDA --model CR-V --year-start 2017 --year-end 2020 --output /tmp/checklist.md
"""
from __future__ import annotations

import argparse
import sqlite3
import sys
import textwrap
from datetime import datetime
from pathlib import Path
from typing import Any

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DB_PATH = PROJECT_ROOT / "database" / "automotive_complaints.db"

# ---------------------------------------------------------------------------
# Component → Inspection checks mapping
# ---------------------------------------------------------------------------

COMPONENT_CHECKS_MAP: dict[str, list[str]] = {
    "ENGINE": [
        "Check for oil leaks (valve cover, oil pan, main seals).",
        "Inspect oil condition on dipstick (milky = coolant contamination, dark = overdue change).",
        "Listen for abnormal noises (knock, tick, whine) on cold start and warm idle.",
        "Check for blue (oil burning) or white (coolant) smoke from exhaust.",
    ],
    "POWER TRAIN": [
        "Check transmission fluid level and condition (dark/burnt smell = service needed).",
        "Test all gear ranges — smooth engagement, no hesitation or slipping.",
        "Inspect CV axle boots for tears or grease leaks at inner/outer joints.",
        "Check for vibration or clunking under acceleration and deceleration.",
    ],
    "TRANSMISSION": [
        "Check transmission fluid level and condition (dark/burnt smell = service needed).",
        "Test all gear ranges — smooth engagement, no hesitation or slipping.",
        "Check for transmission shudder at highway speeds or when warming up.",
    ],
    "BRAKES": [
        "Measure brake pad thickness (>3mm front, >2mm rear minimum).",
        "Inspect rotors for scoring, heat cracks, or thickness below discard spec.",
        "Test pedal feel — firm and consistent, not spongy or pulsating.",
        "Verify ABS warning light cycles on then off at startup.",
    ],
    "STEERING": [
        "Check for play at steering wheel center — no more than 1-2 inches free movement.",
        "Listen for whining or groaning from power steering pump when turning.",
        "Feel for pulling, darting, or vibration during test drive.",
        "Inspect tie rod ends and rack boots for tears or leaks.",
    ],
    "AIR BAG": [
        "Verify SRS/airbag warning light is NOT illuminated while driving.",
        "OBD-II scan for stored SRS codes — any codes require investigation.",
        "Visually inspect steering wheel and dash for signs of prior deployment or repair.",
    ],
    "FUEL": [
        "Check for raw fuel smell inside cabin, in engine bay, or near fuel tank.",
        "Inspect fuel lines, injectors, and tank for leaks, cracks, or corrosion.",
        "Listen for consistent fuel pump hum when key turns to ON position.",
    ],
    "ELECTRICAL": [
        "Test all exterior lights: headlights, tails, signals, reverse, brake.",
        "Verify power windows, locks, mirrors, and infotainment operate correctly.",
        "Check battery terminals for corrosion; test voltage (12.4V+ resting, 13.8-14.4V charging).",
    ],
    "STRUCTURE": [
        "Inspect frame rails, crossmembers, and subframes for cracks, corrosion, or repair welds.",
        "Check panel gaps and paint match for signs of collision repair.",
        "Look for overspray or body filler in engine bay, door jambs, and trunk.",
    ],
    "VISIBILITY": [
        "Inspect windshield for cracks, chips, or sandblasting that affects clarity.",
        "Test front and rear wipers, washers, and defrosters.",
        "Verify backup camera, blind-spot monitoring, and other driver aids function.",
    ],
    "SUSPENSION": [
        "Bounce test each corner — body should stop in 1-2 oscillations (bad shock = more).",
        "Inspect struts/shocks for oil leaks on the shaft.",
        "Check ball joints and control arm bushings for play or torn rubber.",
        "Inspect CV boots for cracks or grease slung onto surrounding components.",
    ],
    "TIRES": [
        "Measure tread depth at multiple points (>4/32\" recommended, >2/32\" legal minimum).",
        "Check for uneven wear: cupping (shocks), edge wear (alignment), center wear (overinflation).",
        "Inspect sidewalls for cracks, bulges, or impact damage.",
        "Confirm all four tires are the same size and type.",
    ],
    "COOLING": [
        "Check coolant level and condition (clear/green/orange — NOT rusty, oily, or milky).",
        "Inspect radiator hoses for softness, cracks, or swelling.",
        "Verify cooling fans activate when engine reaches operating temperature.",
    ],
    "EXHAUST": [
        "Listen for exhaust leaks: ticking or hissing that decreases as engine warms.",
        "Inspect manifold, flex pipe, catalytic converter, and muffler for rust-through or holes.",
        "Check exhaust tips — heavy black soot may indicate running rich.",
    ],
    "SEAT BELTS": [
        "Test all seat belt buckles: insert and release smoothly.",
        "Check belt retractors — belt should retract fully and lock under sharp pull.",
        "Inspect webbing for cuts, fraying, or burn marks.",
    ],
    "LATCHES": [
        "Open and close all doors, hood, and trunk from inside and outside.",
        "Check door striker alignment — no sag, rattles, or difficulty latching.",
        "Test child safety locks on rear doors.",
    ],
    "VEHICLE SPEED CONTROL": [
        "Test cruise control: set, resume, cancel, and brake override.",
        "Check for any hesitation or surge at steady highway speed.",
        "Verify throttle snaps back fully when released.",
    ],
}

STANDARD_CHECKS_MD = """
---

### ✅ STANDARD CHECKS
- [ ] VIN matches title and door jamb sticker
- [ ] CarFax/AutoCheck report reviewed for accidents, title issues, odometer rollback
- [ ] All recalls verified completed at nhtsa.gov/recalls (search by VIN)
- [ ] OBD-II scan: no active DTCs, no pending codes
- [ ] Fluid levels and condition: oil, coolant, brake fluid, trans fluid, power steering
- [ ] Battery voltage: 12.4V+ at rest · 13.8-14.4V with engine running
- [ ] Tire tread depth: >4/32" recommended · >2/32" legal minimum
- [ ] Brake pad thickness: >3mm front · >2mm rear
- [ ] Rust inspection: frame rails, rocker panels, wheel wells, trunk floor, spare tire well
- [ ] Test drive: cold start, acceleration, hard braking, highway, tight turns
"""

# ---------------------------------------------------------------------------
# Database queries
# ---------------------------------------------------------------------------


def get_top_complaints(
    conn: sqlite3.Connection,
    make: str,
    model: str,
    year_start: int,
    year_end: int,
    limit: int = 15,
) -> list[tuple[str, int]]:
    """Return (component, count) tuples ranked by complaint frequency."""
    cur = conn.execute(
        """
        SELECT component, COUNT(*) AS cnt
        FROM complaints_fts
        WHERE UPPER(make) = ? AND UPPER(model) = ?
          AND CAST(year AS INTEGER) BETWEEN ? AND ?
        GROUP BY component ORDER BY cnt DESC LIMIT ?
        """,
        (make.upper(), model.upper(), year_start, year_end, limit),
    )
    rows = cur.fetchall()
    if rows:
        return rows
    # Checked AGENTS.md - implementing directly; simple LIKE fallback for known sub-variant
    # model name issue documented in LESSONS.md (e.g. "F-150 REGULAR CAB" vs "F-150").
    like_model = model.upper() + "%"
    cur = conn.execute(
        """
        SELECT component, COUNT(*) AS cnt
        FROM complaints_fts
        WHERE UPPER(make) = ? AND UPPER(model) LIKE ?
          AND CAST(year AS INTEGER) BETWEEN ? AND ?
        GROUP BY component ORDER BY cnt DESC LIMIT ?
        """,
        (make.upper(), like_model, year_start, year_end, limit),
    )
    return cur.fetchall()


def get_recalls(
    conn: sqlite3.Connection,
    make: str,
    model: str,
    year: int,
) -> list[dict[str, Any]]:
    """Return recalls where year falls within year_from..year_to range."""
    conn.row_factory = sqlite3.Row
    cur = conn.execute(
        """
        SELECT campaign_no, component, summary, park_it, year_from, year_to
        FROM nhtsa_recalls
        WHERE UPPER(make) = ? AND UPPER(model) = ?
          AND (year_from IS NULL OR year_from <= ?)
          AND (year_to IS NULL OR year_to >= ?)
        ORDER BY park_it DESC, report_date DESC
        """,
        (make.upper(), model.upper(), year, year),
    )
    return [dict(row) for row in cur.fetchall()]


def get_tsbs(
    conn: sqlite3.Connection,
    make: str,
    model: str,
    year: int,
    limit: int = 8,
) -> list[dict[str, Any]]:
    """Return recent TSBs for the given vehicle year."""
    conn.row_factory = sqlite3.Row
    cur = conn.execute(
        """
        SELECT bulletin_no, component, summary
        FROM nhtsa_tsbs
        WHERE UPPER(make) = ? AND UPPER(model) = ?
          AND (year = ? OR year = 9999)
        ORDER BY bulletin_date DESC LIMIT ?
        """,
        (make.upper(), model.upper(), year, limit),
    )
    return [dict(row) for row in cur.fetchall()]


# ---------------------------------------------------------------------------
# Component → checks mapping
# ---------------------------------------------------------------------------


def component_to_checks(component: str) -> list[str]:
    """Map an NHTSA component name to 2-4 specific inspection steps."""
    upper = component.upper()
    for key, checks in COMPONENT_CHECKS_MAP.items():
        if key in upper:
            return checks[:3]  # cap at 3 per component for readability
    return [
        "Visually inspect for obvious damage, leaks, or wear.",
        "Listen for unusual noises from this area during operation.",
        "Check for related warning lights on the dashboard.",
    ]


# ---------------------------------------------------------------------------
# Checklist builder
# ---------------------------------------------------------------------------


def build_checklist(make: str, model: str, year_start: int, year_end: int) -> str:
    """Build the full markdown checklist string."""
    if not DB_PATH.exists():
        raise FileNotFoundError(f"Database not found at {DB_PATH}")

    with sqlite3.connect(f"file:{DB_PATH}?mode=ro", uri=True) as conn:
        representative_year = year_end
        complaints = get_top_complaints(conn, make, model, year_start, year_end)
        recalls = get_recalls(conn, make, model, representative_year)
        tsbs = get_tsbs(conn, make, model, representative_year)

    today = datetime.now().strftime("%Y-%m-%d")
    year_range_str = str(year_start) if year_start == year_end else f"{year_start}–{year_end}"
    parts: list[str] = []

    # ── Header ──────────────────────────────────────────────────────────────
    parts.append("# Pre-Purchase Inspection Checklist\n")
    parts.append(f"## {year_range_str} {make.title()} {model.title()}\n")
    parts.append(
        f"*Generated {today} | Based on {len(complaints)} complaint categories, "
        f"{len(recalls)} recall(s), {len(tsbs)} TSB(s)*\n"
    )

    # ── Recalls ─────────────────────────────────────────────────────────────
    parts.append("\n---\n\n### ⚠️ ACTIVE RECALLS (VERIFY COMPLETION)\n")
    if not recalls:
        parts.append(
            "No open recalls found for this model year — always verify VIN at **nhtsa.gov/recalls**\n"
        )
    else:
        parts.append("| Campaign | Component | Years Affected | Status |\n")
        parts.append("|----------|-----------|----------------|--------|\n")
        for r in recalls:
            yf, yt = r.get("year_from"), r.get("year_to")
            affected = str(yf) if yf == yt else (f"{yf}–{yt}" if yf and yt else "Varies")
            campaign = r["campaign_no"]
            if r.get("park_it"):
                campaign += " ⛔ DO NOT DRIVE"
            comp = textwrap.shorten(r.get("component") or "N/A", width=30, placeholder="…")
            parts.append(f"| {campaign} | {comp} | {affected} | [ ] Verified Completed |\n")

    # ── Top Inspection Priorities ────────────────────────────────────────────
    parts.append("\n---\n\n### 🔍 TOP INSPECTION PRIORITIES\n")
    parts.append("*Ranked by complaint frequency — focus here first*\n\n")
    if not complaints:
        parts.append("No significant complaint patterns found for this vehicle range.\n")
    else:
        for i, (component, count) in enumerate(complaints[:8], 1):
            parts.append(f"**{i}. {component.title()} ({count:,} complaints)**\n")
            for check in component_to_checks(component):
                parts.append(f"- [ ] {check}\n")
            parts.append("\n")

    # ── TSBs ─────────────────────────────────────────────────────────────────
    parts.append("---\n\n### 📋 TSBs TO PROBE\n")
    if not tsbs:
        parts.append("No specific TSBs found for this model year.\n")
    else:
        parts.append("| Bulletin | Component | Known Issue |\n")
        parts.append("|----------|-----------|-------------|\n")
        for t in tsbs:
            summary = (t.get("summary") or "").replace("\n", " ").replace("|", " ")
            short = textwrap.shorten(summary, width=80, placeholder="…")
            comp = textwrap.shorten(t.get("component") or "N/A", width=25, placeholder="…")
            parts.append(f"| {t['bulletin_no']} | {comp} | {short} |\n")

    # ── Standard Checks ───────────────────────────────────────────────────────
    parts.append(STANDARD_CHECKS_MD)

    return "".join(parts)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate a Pre-Purchase Inspection Checklist for a vehicle.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("--make", required=True, help="Vehicle make (e.g. FORD)")
    parser.add_argument("--model", required=True, help="Vehicle model (e.g. F-150)")
    parser.add_argument("--year-start", required=True, type=int, help="Start of model year range")
    parser.add_argument("--year-end", required=True, type=int, help="End of model year range")
    parser.add_argument("--output", default=None, metavar="PATH", help="Save to file (default: stdout)")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)

    if args.year_start > args.year_end:
        print("Error: --year-start cannot be after --year-end.", file=sys.stderr)
        return 1

    try:
        md = build_checklist(args.make, args.model, args.year_start, args.year_end)
    except FileNotFoundError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1
    except sqlite3.Error as exc:
        print(f"Database error: {exc}", file=sys.stderr)
        return 1

    if args.output:
        out = Path(args.output)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(md, encoding="utf-8")
        print(f"Checklist saved to: {out.resolve()}")
    else:
        print(md)

    return 0


if __name__ == "__main__":
    sys.exit(main())
