# Checked AGENTS.md - implementing directly because this is a standalone CLI
# with no auth/sensitive data (read-only SQLite queries).
"""
Pre-Purchase Inspection Checklist generator for automotive mechanics.

Given a vehicle (make/model/year range), generates a one-page markdown
inspection checklist based on real NHTSA complaint, recall, and TSB data.

Run:
  .venv/bin/python3 scripts/generate_checklist.py --make FORD --model F-150 --year-start 2018 --year-end 2022
  .venv/bin/python3 scripts/generate_checklist.py --make HONDA --model CR-V --year-start 2017 --year-end 2020 --output /tmp/checklist.md
  .venv/bin/python3 scripts/generate_checklist.py --make FORD --model F-150 --year-start 2018 --year-end 2022 --format json
  .venv/bin/python3 scripts/generate_checklist.py --make FORD --model F-150 --year-start 2018 --year-end 2022 --format html
"""
from __future__ import annotations

import argparse
import json
import sqlite3
import sys
import textwrap
from datetime import datetime
from pathlib import Path
from typing import Any, TypedDict

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DB_PATH = PROJECT_ROOT / "database" / "automotive_complaints.db"

# ---------------------------------------------------------------------------
# Typed structures
# ---------------------------------------------------------------------------


class ChecklistRecall(TypedDict):
    campaign_no: str
    component: str
    summary: str
    park_it: bool
    year_from: int | None
    year_to: int | None


class ChecklistSection(TypedDict):
    component: str
    complaint_count: int
    checks: list[str]


class ChecklistTsb(TypedDict):
    bulletin_no: str
    component: str
    summary: str


class ChecklistData(TypedDict):
    make: str
    model: str
    year_start: int
    year_end: int
    generated_at: str
    has_park_it: bool
    recalls: list[ChecklistRecall]
    sections: list[ChecklistSection]
    tsbs: list[ChecklistTsb]
    standard_checks: list[str]


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

STANDARD_CHECKS: list[str] = [
    "VIN matches title and door jamb sticker",
    "CarFax/AutoCheck report reviewed for accidents, title issues, odometer rollback",
    "All recalls verified completed at nhtsa.gov/recalls (search by VIN)",
    "OBD-II scan: no active DTCs, no pending codes",
    "Fluid levels and condition: oil, coolant, brake fluid, trans fluid, power steering",
    "Battery voltage: 12.4V+ at rest · 13.8-14.4V with engine running",
    "Tire tread depth: >4/32\" recommended · >2/32\" legal minimum",
    "Brake pad thickness: >3mm front · >2mm rear",
    "Rust inspection: frame rails, rocker panels, wheel wells, trunk floor, spare tire well",
    "Test drive: cold start, acceleration, hard braking, highway, tight turns",
]

STANDARD_CHECKS_MD = """
---

### ✅ STANDARD CHECKS
- [ ] VIN matches title and door jamb sticker
- [ ] CarFax/AutoCheck report reviewed for accidents, title issues, odometer rollback
- [ ] All recalls verified completed at nhtsa.gov/recalls (search by VIN)
- [ ] OBD-II scan: no active DTCs, no pending codes
- [ ] Fluid levels and condition: oil, coolant, brake fluid, trans fluid, power steering
- [ ] Battery voltage: 12.4V+ at rest · 13.8-14.4V with engine running
- [ ] Tire tread depth: >4/32\" recommended · >2/32\" legal minimum
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
# Structured data builder (primary — everything else derives from this)
# ---------------------------------------------------------------------------


def build_checklist_data(make: str, model: str, year_start: int, year_end: int) -> ChecklistData:
    """Build structured checklist data dict from SQLite sources."""
    if not DB_PATH.exists():
        raise FileNotFoundError(f"Database not found at {DB_PATH}")

    with sqlite3.connect(f"file:{DB_PATH}?mode=ro", uri=True) as conn:
        representative_year = year_end
        complaints = get_top_complaints(conn, make, model, year_start, year_end)
        raw_recalls = get_recalls(conn, make, model, representative_year)
        raw_tsbs = get_tsbs(conn, make, model, representative_year)

    recalls: list[ChecklistRecall] = [
        {
            "campaign_no": r["campaign_no"],
            "component": r.get("component") or "N/A",
            "summary": r.get("summary") or "",
            "park_it": bool(r.get("park_it")),
            "year_from": r.get("year_from"),
            "year_to": r.get("year_to"),
        }
        for r in raw_recalls
    ]

    sections: list[ChecklistSection] = [
        {
            "component": component,
            "complaint_count": count,
            "checks": component_to_checks(component),
        }
        for component, count in complaints[:8]
    ]

    tsbs: list[ChecklistTsb] = [
        {
            "bulletin_no": t["bulletin_no"],
            "component": t.get("component") or "N/A",
            "summary": (t.get("summary") or "").replace("\n", " "),
        }
        for t in raw_tsbs
    ]

    return {
        "make": make.upper(),
        "model": model.upper(),
        "year_start": year_start,
        "year_end": year_end,
        "generated_at": datetime.now().strftime("%Y-%m-%d"),
        "has_park_it": any(r["park_it"] for r in recalls),
        "recalls": recalls,
        "sections": sections,
        "tsbs": tsbs,
        "standard_checks": STANDARD_CHECKS,
    }


# ---------------------------------------------------------------------------
# Markdown builder (derived from structured data)
# ---------------------------------------------------------------------------


def build_checklist(make: str, model: str, year_start: int, year_end: int) -> str:
    """Build the full markdown checklist string."""
    data = build_checklist_data(make, model, year_start, year_end)
    return _data_to_markdown(data)


def _data_to_markdown(data: ChecklistData) -> str:
    """Render ChecklistData as markdown."""
    make = data["make"]
    model = data["model"]
    year_start = data["year_start"]
    year_end = data["year_end"]
    recalls = data["recalls"]
    sections = data["sections"]
    tsbs = data["tsbs"]

    year_range_str = str(year_start) if year_start == year_end else f"{year_start}–{year_end}"
    parts: list[str] = []

    parts.append("# Pre-Purchase Inspection Checklist\n")
    parts.append(f"## {year_range_str} {make.title()} {model.title()}\n")
    parts.append(
        f"*Generated {data['generated_at']} | Based on {len(sections)} complaint categories, "
        f"{len(recalls)} recall(s), {len(tsbs)} TSB(s)*\n"
    )

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

    parts.append("\n---\n\n### 🔍 TOP INSPECTION PRIORITIES\n")
    parts.append("*Ranked by complaint frequency — focus here first*\n\n")
    if not sections:
        parts.append("No significant complaint patterns found for this vehicle range.\n")
    else:
        for i, section in enumerate(sections, 1):
            parts.append(f"**{i}. {section['component'].title()} ({section['complaint_count']:,} complaints)**\n")
            for check in section["checks"]:
                parts.append(f"- [ ] {check}\n")
            parts.append("\n")

    parts.append("---\n\n### 📋 TSBs TO PROBE\n")
    if not tsbs:
        parts.append("No specific TSBs found for this model year.\n")
    else:
        parts.append("| Bulletin | Component | Known Issue |\n")
        parts.append("|----------|-----------|-------------|\n")
        for t in tsbs:
            short = textwrap.shorten(t["summary"], width=80, placeholder="…")
            comp = textwrap.shorten(t["component"], width=25, placeholder="…")
            parts.append(f"| {t['bulletin_no']} | {comp} | {short} |\n")

    parts.append(STANDARD_CHECKS_MD)
    return "".join(parts)


# ---------------------------------------------------------------------------
# HTML builder (for print/PDF — derived from structured data)
# ---------------------------------------------------------------------------


def build_checklist_html(data: ChecklistData) -> str:
    """Render ChecklistData as print-ready HTML for PDF generation."""
    make = data["make"]
    model = data["model"]
    year_start = data["year_start"]
    year_end = data["year_end"]
    year_range_str = str(year_start) if year_start == year_end else f"{year_start}–{year_end}"
    recalls = data["recalls"]
    sections = data["sections"]
    tsbs = data["tsbs"]
    generated_at = data["generated_at"]

    def esc(s: str) -> str:
        return (
            s.replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
            .replace('"', "&quot;")
        )

    parts: list[str] = [
        """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>Pre-Purchase Checklist</title>
<style>
  *, *::before, *::after { box-sizing: border-box; }
  body {
    font-family: 'IBM Plex Sans', Arial, sans-serif;
    font-size: 10pt;
    color: #161616;
    margin: 0;
    padding: 0;
    background: #fff;
  }
  .page-header {
    border-bottom: 3px solid #0f62fe;
    padding: 12px 0 8px;
    margin-bottom: 16px;
  }
  h1 { font-size: 16pt; font-weight: 700; margin: 0 0 2px; color: #161616; }
  .subtitle { font-size: 9pt; color: #525252; margin: 0; }
  h2 {
    font-size: 10pt;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.06em;
    color: #0f62fe;
    margin: 18px 0 8px;
    border-bottom: 1px solid #e0e0e0;
    padding-bottom: 4px;
  }
  .park-it-banner {
    background: #fff1f1;
    border: 2px solid #da1e28;
    padding: 8px 12px;
    margin-bottom: 12px;
    font-weight: 700;
    color: #da1e28;
    font-size: 10pt;
  }
  table { width: 100%; border-collapse: collapse; margin-bottom: 12px; font-size: 9pt; }
  th {
    background: #e0e0e0;
    text-align: left;
    padding: 5px 8px;
    font-weight: 700;
    font-size: 8.5pt;
    text-transform: uppercase;
    letter-spacing: 0.04em;
  }
  td { padding: 4px 8px; border-bottom: 1px solid #e0e0e0; vertical-align: top; }
  tr:nth-child(even) td { background: #f4f4f4; }
  .park-it-row td { background: #fff1f1 !important; font-weight: 600; }
  .recall-badge {
    display: inline-block;
    background: #da1e28;
    color: #fff;
    font-size: 7.5pt;
    font-weight: 700;
    padding: 1px 5px;
    border-radius: 2px;
    margin-left: 4px;
  }
  .section-title {
    font-weight: 700;
    font-size: 10pt;
    margin: 14px 0 6px;
    color: #161616;
  }
  .section-count { font-weight: 400; color: #525252; font-size: 9pt; }
  .check-list { list-style: none; margin: 0 0 8px; padding: 0; }
  .check-list li {
    display: flex;
    align-items: flex-start;
    gap: 8px;
    margin-bottom: 5px;
    font-size: 9.5pt;
    line-height: 1.4;
  }
  .check-box {
    flex-shrink: 0;
    width: 12px;
    height: 12px;
    border: 1.5px solid #8d8d8d;
    display: inline-block;
    margin-top: 2px;
  }
  .standard-grid {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 4px 24px;
  }
  .footer {
    margin-top: 24px;
    padding-top: 8px;
    border-top: 1px solid #e0e0e0;
    font-size: 8pt;
    color: #8d8d8d;
    display: flex;
    justify-content: space-between;
  }
  @media print {
    body { font-size: 9.5pt; }
    .page-break { page-break-before: always; }
    a { color: inherit; text-decoration: none; }
  }
</style>
</head>
<body>
""",
    ]

    # Header
    parts.append(f"""<div class="page-header">
  <h1>Pre-Purchase Inspection Checklist</h1>
  <p class="subtitle">{esc(year_range_str)} {esc(make.title())} {esc(model.title())} &nbsp;·&nbsp; Generated {esc(generated_at)} &nbsp;·&nbsp; {len(sections)} complaint categories · {len(recalls)} recall(s) · {len(tsbs)} TSB(s)</p>
</div>
""")

    # Park-it banner
    if data["has_park_it"]:
        parts.append('<div class="park-it-banner">⛔ DO NOT DRIVE WARNING: One or more park-it safety recalls are active for this vehicle. Verify VIN at nhtsa.gov/recalls before purchase.</div>\n')

    # Recalls
    parts.append('<h2>⚠️ Active Safety Recalls (Verify Completion)</h2>\n')
    if not recalls:
        parts.append('<p style="color:#525252;font-size:9pt">No open recalls found — always verify VIN at <strong>nhtsa.gov/recalls</strong></p>\n')
    else:
        parts.append('<table><thead><tr><th>Campaign</th><th>Component</th><th>Years</th><th style="width:120px">Status</th></tr></thead><tbody>\n')
        for r in recalls:
            yf, yt = r.get("year_from"), r.get("year_to")
            affected = str(yf) if yf == yt else (f"{yf}–{yt}" if yf and yt else "Varies")
            row_cls = ' class="park-it-row"' if r["park_it"] else ""
            badge = '<span class="recall-badge">DO NOT DRIVE</span>' if r["park_it"] else ""
            comp = textwrap.shorten(r["component"], width=35, placeholder="…")
            camp = esc(r["campaign_no"])
            parts.append(f'<tr{row_cls}><td>{camp}{badge}</td><td>{esc(comp)}</td><td>{esc(affected)}</td><td><span class="check-box"></span> Verified</td></tr>\n')
        parts.append('</tbody></table>\n')

    # Inspection priorities
    parts.append('<h2>🔍 Top Inspection Priorities (by Complaint Frequency)</h2>\n')
    if not sections:
        parts.append('<p style="color:#525252;font-size:9pt">No significant complaint patterns found for this vehicle range.</p>\n')
    else:
        for i, section in enumerate(sections, 1):
            parts.append(f'<div class="section-title">{i}. {esc(section["component"].title())} <span class="section-count">({section["complaint_count"]:,} complaints)</span></div>\n')
            parts.append('<ul class="check-list">\n')
            for check in section["checks"]:
                parts.append(f'<li><span class="check-box"></span>{esc(check)}</li>\n')
            parts.append('</ul>\n')

    # TSBs
    parts.append('<h2>📋 Technical Service Bulletins to Probe</h2>\n')
    if not tsbs:
        parts.append('<p style="color:#525252;font-size:9pt">No specific TSBs found for this model year.</p>\n')
    else:
        parts.append('<table><thead><tr><th>Bulletin</th><th>Component</th><th>Known Issue</th></tr></thead><tbody>\n')
        for t in tsbs:
            short = textwrap.shorten(t["summary"], width=90, placeholder="…")
            comp = textwrap.shorten(t["component"], width=30, placeholder="…")
            parts.append(f'<tr><td>{esc(t["bulletin_no"])}</td><td>{esc(comp)}</td><td>{esc(short)}</td></tr>\n')
        parts.append('</tbody></table>\n')

    # Standard checks
    parts.append('<h2>✅ Standard Checks (Every Inspection)</h2>\n')
    parts.append('<div class="standard-grid">\n')
    parts.append('<ul class="check-list">\n')
    for check in STANDARD_CHECKS:
        parts.append(f'<li><span class="check-box"></span>{esc(check)}</li>\n')
    parts.append('</ul>\n</div>\n')

    # Footer
    parts.append(f'<div class="footer"><span>ADS Automotive Diagnostic System</span><span>Generated {esc(generated_at)} · nhtsa.gov/recalls for VIN verification</span></div>\n')
    parts.append('</body>\n</html>\n')

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
    parser.add_argument(
        "--format",
        choices=["md", "json", "html"],
        default="md",
        help="Output format: md (markdown), json (structured data), html (print-ready HTML)",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)

    if args.year_start > args.year_end:
        print("Error: --year-start cannot be after --year-end.", file=sys.stderr)
        return 1

    try:
        if args.format == "json":
            data = build_checklist_data(args.make, args.model, args.year_start, args.year_end)
            output = json.dumps(data, indent=2)
        elif args.format == "html":
            data = build_checklist_data(args.make, args.model, args.year_start, args.year_end)
            output = build_checklist_html(data)
        else:
            output = build_checklist(args.make, args.model, args.year_start, args.year_end)
    except FileNotFoundError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1
    except sqlite3.Error as exc:
        print(f"Database error: {exc}", file=sys.stderr)
        return 1

    if args.output:
        out = Path(args.output)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(output, encoding="utf-8")
        print(f"Checklist saved to: {out.resolve()}")
    else:
        print(output)

    return 0


if __name__ == "__main__":
    sys.exit(main())
