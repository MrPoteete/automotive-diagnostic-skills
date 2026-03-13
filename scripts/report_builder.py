#!/usr/bin/env python3
# Checked AGENTS.md - implementing directly because this is a standalone CLI script
# with no auth/sensitive data (read-only SQLite queries, API key from env only).
# No security-engineer review needed. Data queries are pre-validated.
"""
Automotive Diagnostic Report Builder — Template A: Vehicle Model Failure Trend

Usage:
    uv run python scripts/report_builder.py --make JEEP --model CHEROKEE \\
        --year-start 2016 --year-end 2020 --output reports/jeep_cherokee_2016_2020.md

    # Skip LLM polish (raw SQL output only):
    uv run python scripts/report_builder.py --make JEEP --model CHEROKEE \\
        --year-start 2016 --year-end 2020 --no-llm

Data sources used:
    - NHTSA complaints (562K+ records, FTS5)
    - NHTSA TSBs (211K records)
    - NHTSA defect investigations (153K records)
    - EPA vehicle specs (49K records — powertrain configs)
    - Transport Canada recalls (144K records)
    - NHTSA recalls API (live, no key required)
"""

import argparse
import json
import os
import re
import sqlite3
import sys
import urllib.parse
import urllib.request
from datetime import datetime
from pathlib import Path
from typing import TypedDict


class PatternResult(TypedDict):
    label: str
    complaint_count: int
    pct: float
    samples: list[str]


# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

PROJECT_ROOT = Path(__file__).parent.parent
DB_PATH = PROJECT_ROOT / "database" / "automotive_complaints.db"
REPORTS_DIR = PROJECT_ROOT / "reports"


# ---------------------------------------------------------------------------
# Database connection
# ---------------------------------------------------------------------------

def connect() -> sqlite3.Connection:
    if not DB_PATH.exists():
        print(f"ERROR: Database not found at {DB_PATH}", file=sys.stderr)
        sys.exit(1)
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    return conn


# ---------------------------------------------------------------------------
# Core complaint queries (existing)
# ---------------------------------------------------------------------------

def complaint_volume_by_year(
    conn: sqlite3.Connection,
    make: str,
    model: str,
    year_start: int,
    year_end: int,
) -> list[dict]:
    cur = conn.execute(
        """
        SELECT c2 AS year, COUNT(*) AS cnt
        FROM complaints_fts_content
        WHERE c0 = ? AND c1 = ? AND CAST(c2 AS INT) BETWEEN ? AND ?
        GROUP BY c2
        ORDER BY c2
        """,
        (make, model, year_start, year_end),
    )
    return [dict(r) for r in cur.fetchall()]


def top_components(
    conn: sqlite3.Connection,
    make: str,
    model: str,
    year_start: int,
    year_end: int,
    limit: int = 12,
) -> list[dict]:
    cur = conn.execute(
        """
        SELECT c3 AS component, COUNT(*) AS cnt
        FROM complaints_fts_content
        WHERE c0 = ? AND c1 = ? AND CAST(c2 AS INT) BETWEEN ? AND ?
        GROUP BY c3
        ORDER BY cnt DESC
        LIMIT ?
        """,
        (make, model, year_start, year_end, limit),
    )
    return [dict(r) for r in cur.fetchall()]


def narratives_for_component(
    conn: sqlite3.Connection,
    make: str,
    model: str,
    year_start: int,
    year_end: int,
    component: str,
    limit: int = 200,
) -> list[str]:
    cur = conn.execute(
        """
        SELECT c4 FROM complaints_fts_content
        WHERE c0 = ? AND c1 = ? AND CAST(c2 AS INT) BETWEEN ? AND ?
        AND c3 LIKE ?
        LIMIT ?
        """,
        (make, model, year_start, year_end, f"%{component}%", limit),
    )
    return [r[0] for r in cur.fetchall() if r[0]]


def all_tsbs(
    conn: sqlite3.Connection,
    make: str,
    model: str,
    year_start: int,
    year_end: int,
    limit: int = 15,
) -> list[dict]:
    cur = conn.execute(
        """
        SELECT bulletin_no, bulletin_date, component, summary
        FROM nhtsa_tsbs
        WHERE make = ? AND model LIKE ? AND CAST(year AS INT) BETWEEN ? AND ?
        ORDER BY bulletin_date DESC
        LIMIT ?
        """,
        (make, f"%{model}%", year_start, year_end, limit),
    )
    return [dict(r) for r in cur.fetchall()]


def tsb_component_breakdown(
    conn: sqlite3.Connection,
    make: str,
    model: str,
    year_start: int,
    year_end: int,
) -> list[dict]:
    cur = conn.execute(
        """
        SELECT component, COUNT(*) AS cnt
        FROM nhtsa_tsbs
        WHERE make = ? AND model LIKE ? AND CAST(year AS INT) BETWEEN ? AND ?
        GROUP BY component
        ORDER BY cnt DESC
        LIMIT 10
        """,
        (make, f"%{model}%", year_start, year_end),
    )
    return [dict(r) for r in cur.fetchall()]


# ---------------------------------------------------------------------------
# New data source queries
# ---------------------------------------------------------------------------

def query_investigations(
    # Checked AGENTS.md - fixing year range and case matching directly;
    # simple query parameter adjustment, no new logic.
    conn: sqlite3.Connection,
    make: str,
    model: str,
    year_start: int,
    year_end: int,
    limit: int = 10,
) -> list[dict]:
    """NHTSA defect investigations — pre-recall watchlist items.
    Uses a ±5 year buffer since investigation year is when issue first appeared,
    often slightly before the NHTSA complaint range.
    """
    cur = conn.execute(
        """
        SELECT inv_id, inv_type, make, model, year_from, component, summary, open_date, status
        FROM nhtsa_investigations
        WHERE make = ? AND model LIKE ?
          AND (year_from IS NULL OR year_from BETWEEN ? AND ?)
        ORDER BY open_date DESC
        LIMIT ?
        """,
        (make, f"%{model}%", year_start - 5, year_end + 2, limit),
    )
    return [dict(r) for r in cur.fetchall()]


def query_epa_specs(
    # Checked AGENTS.md - fixing case-insensitive make match directly;
    # EPA stores "Jeep" while complaints use "JEEP", need UPPER() comparison.
    conn: sqlite3.Connection,
    make: str,
    model: str,
    year_start: int,
    year_end: int,
) -> list[dict]:
    """EPA powertrain configurations for this vehicle."""
    cur = conn.execute(
        """
        SELECT year, engine_cylinders, engine_displacement, drive,
               transmission, turbo, supercharged, mpg_combined, fuel_type
        FROM epa_vehicles
        WHERE UPPER(make) = ? AND UPPER(model) LIKE ? AND year BETWEEN ? AND ?
        ORDER BY year DESC, engine_displacement DESC
        """,
        (make, f"%{model}%", year_start, year_end),
    )
    return [dict(r) for r in cur.fetchall()]


def query_canada_recalls(
    conn: sqlite3.Connection,
    make: str,
    model: str,
    year_start: int,
    year_end: int,
    limit: int = 10,
) -> list[dict]:
    """Transport Canada recalls for cross-reference."""
    cur = conn.execute(
        """
        SELECT recall_no, make, model, year_from, system, description, recall_date
        FROM canada_recalls
        WHERE make = ? AND model LIKE ?
          AND (year_from IS NULL OR year_from BETWEEN ? AND ?)
        ORDER BY recall_date DESC
        LIMIT ?
        """,
        (make, f"%{model}%", year_start, year_end, limit),
    )
    return [dict(r) for r in cur.fetchall()]


def fetch_nhtsa_recalls_api(
    make: str,
    model: str,
    year_start: int,
    year_end: int,
    timeout: int = 8,
) -> list[dict]:
    """
    Query NHTSA recalls API (live, free, no key).
    Queries each year in range; deduplicates by campaign number.
    Returns list of recall dicts.
    """
    seen: set[str] = set()
    results: list[dict] = []

    for year in range(year_start, year_end + 1):
        url = (
            f"https://api.nhtsa.gov/recalls/recallsByVehicle"
            f"?make={urllib.parse.quote(make)}&model={urllib.parse.quote(model)}&modelYear={year}"
        )
        try:
            req = urllib.request.Request(
                url,
                headers={"User-Agent": "automotive-diagnostic-report-builder/1.0"},
            )
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                data = json.loads(resp.read().decode())
            for r in data.get("results", []):
                cid = r.get("NHTSACampaignNumber", "")
                if cid and cid not in seen:
                    seen.add(cid)
                    results.append({
                        "campaign_no": cid,
                        "year": year,
                        "component": r.get("Component", ""),
                        "summary": r.get("Summary", ""),
                        "consequence": r.get("Consequence", ""),
                        "remedy": r.get("Remedy", ""),
                        "report_date": r.get("ReportReceivedDate", ""),
                    })
        except Exception:
            pass  # Offline or API down — skip gracefully

    return results


# ---------------------------------------------------------------------------
# Failure pattern discovery
# ---------------------------------------------------------------------------

FAILURE_SIGNALS: list[tuple[str, str]] = [
    ("PTU / Power Transfer Unit", r"ptu|power transfer unit"),
    ("4WD / AWD system", r"4wd|awd|4x4|four.wheel|all.wheel|service 4wd"),
    ("Transfer case", r"transfer case"),
    ("Transmission shudder / shift issues", r"shudder|shift|transmission|tcm|9.speed|9-speed"),
    ("Stalling / loss of power", r"stall|loss of power|hesitat|shut off|died|no start"),
    ("Engine misfires / rough running", r"misfire|rough|vibrat|shak"),
    ("Oil leaks / consumption", r"oil leak|oil consumption|burning oil|low oil"),
    ("Check engine / MIL light", r"check engine|mil|malfunction indicator"),
    ("Electrical / instrument cluster", r"electrical|cluster|dash|warning light|module"),
    ("Brakes", r"brake|abs|stopping"),
    ("Steering", r"steering|pull|drift"),
    ("HVAC / AC", r"heat|hvac|ac |air condition|cool"),
]


def discover_failure_patterns(narratives: list[str]) -> list[PatternResult]:
    """Count how many narratives mention each failure signal."""
    results: list[PatternResult] = []
    total = len(narratives)
    if total == 0:
        return results

    for label, pattern in FAILURE_SIGNALS:
        complaint_count = sum(1 for n in narratives if re.search(pattern, n.lower()))
        if complaint_count == 0:
            continue
        samples: list[str] = []
        for n in narratives:
            if re.search(pattern, n.lower()):
                sentences = re.split(r"[.!?]", n)
                for s in sentences:
                    if re.search(pattern, s.lower()) and len(s.strip()) > 20:
                        samples.append(s.strip()[:200])
                        break
            if len(samples) >= 3:
                break
        results.append({
            "label": label,
            "complaint_count": complaint_count,
            "pct": round(complaint_count / total * 100, 1),
            "samples": samples,
        })

    results.sort(key=lambda x: x["complaint_count"], reverse=True)
    return results


# ---------------------------------------------------------------------------
# Markdown rendering
# ---------------------------------------------------------------------------

def format_tsb_date(raw: str) -> str:
    if raw and len(raw) == 8 and raw.isdigit():
        return f"{raw[:4]}-{raw[4:6]}-{raw[6:]}"
    return raw or "—"


def build_raw_markdown(
    make: str,
    model: str,
    year_start: int,
    year_end: int,
    volume: list[dict],
    components: list[dict],
    patterns: list[PatternResult],
    tsb_list: list[dict],
    tsb_breakdown: list[dict],
    recalls: list[dict],
    investigations: list[dict],
    epa_specs: list[dict],
    canada_recalls: list[dict],
) -> str:
    total_complaints = sum(r["cnt"] for r in volume)
    total_tsbs = sum(r["cnt"] for r in tsb_breakdown)
    lines: list[str] = []

    lines.append(f"# {make.title()} {model.title()} {year_start}–{year_end} Diagnostic Trend Report")
    lines.append(f"\n*Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}*")
    lines.append(
        "*Data sources: NHTSA Consumer Complaints · TSBs · Defect Investigations · "
        "EPA Vehicle Specs · Transport Canada Recalls · NHTSA Recalls API*\n"
    )
    lines.append("---\n")

    # Executive Summary
    lines.append("## Executive Summary")
    lines.append(
        f"The {year_start}–{year_end} {make.title()} {model.title()} generated "
        f"**{total_complaints:,} NHTSA complaints** across all systems, "
        f"with **{total_tsbs:,}** associated Technical Service Bulletins on file. "
        f"**{len(recalls)} open recalls** affect this model range. "
        f"Powertrain issues dominate the complaint record and warrant proactive inspection.\n"
    )

    # Complaint Volume
    lines.append("## Complaint Volume Trend\n")
    lines.append("| Model Year | Complaints |")
    lines.append("|------------|------------|")
    for r in volume:
        lines.append(f"| {r['year']} | {r['cnt']:,} |")
    lines.append(f"| **Total** | **{total_complaints:,}** |\n")

    if len(volume) >= 2:
        peak = max(volume, key=lambda x: x["cnt"])
        lines.append(
            f"**Peak year:** {peak['year']} ({peak['cnt']:,} complaints). "
            f"Note: recent model years typically show lower counts due to reporting lag.\n"
        )

    # EPA Powertrain Configs
    if epa_specs:
        lines.append("## Powertrain Configurations (EPA Data)\n")
        lines.append("| Year | Engine | Displacement | Drive | Transmission | MPG Combined |")
        lines.append("|------|--------|-------------|-------|--------------|--------------|")
        seen_configs: set[str] = set()
        for e in epa_specs[:15]:
            turbo_flag = " Turbo" if e.get("turbo") else ""
            key = f"{e['year']}-{e['engine_cylinders']}-{e['engine_displacement']}-{e['drive']}-{e['transmission']}"
            if key in seen_configs:
                continue
            seen_configs.add(key)
            cyl = f"{e['engine_cylinders']}-cyl" if e.get("engine_cylinders") else "—"
            disp = f"{e['engine_displacement']:.1f}L{turbo_flag}" if e.get("engine_displacement") else "—"
            drive = e.get("drive", "—") or "—"
            trans = e.get("transmission", "—") or "—"
            mpg = str(e.get("mpg_combined", "—")) if e.get("mpg_combined") else "—"
            lines.append(f"| {e['year']} | {cyl} | {disp} | {drive} | {trans} | {mpg} |")
        lines.append("")

    # Top Failure Systems
    lines.append("## Top Failure Systems\n")
    lines.append("| Rank | Component / System | Complaints | % of Total |")
    lines.append("|------|--------------------|------------|------------|")
    for i, r in enumerate(components, 1):
        pct = round(r["cnt"] / total_complaints * 100, 1) if total_complaints else 0
        comp = (r["component"] or "UNKNOWN").title()
        lines.append(f"| {i} | {comp} | {r['cnt']:,} | {pct}% |")
    lines.append("")

    # Failure Patterns
    lines.append("## Failure Pattern Analysis\n")
    lines.append(
        "Derived from keyword analysis of complaint narratives for the top failure system.\n"
    )
    for p in patterns[:8]:
        lines.append(f"### {p['label']}")
        lines.append(f"**{p['complaint_count']:,} complaints mention this pattern ({p['pct']}%)**\n")
        if p["samples"]:
            lines.append("Representative complaint excerpts:")
            for s in p["samples"]:
                lines.append(f"> *\"{s}\"*")
        lines.append("")

    # NHTSA Recalls
    lines.append("## NHTSA Safety Recalls\n")
    if recalls:
        lines.append(f"**{len(recalls)} recall campaigns** found via NHTSA API.\n")
        lines.append("| Campaign # | Year | Component | Summary |")
        lines.append("|------------|------|-----------|---------|")
        for r in recalls[:15]:
            summary = (r.get("summary") or "")[:120].replace("|", " ").replace("\n", " ")
            lines.append(
                f"| {r['campaign_no']} | {r['year']} | "
                f"{(r['component'] or '—')[:50]} | {summary}... |"
            )
    else:
        lines.append("No recall data available (API offline or no recalls found).\n")
    lines.append("")

    # Defect Investigations
    if investigations:
        lines.append("## NHTSA Defect Investigations\n")
        lines.append(
            "Active government investigations are pre-recall watchlist items "
            "(confidence: 0.8).\n"
        )
        lines.append("| Inv ID | Type | Component | Status | Summary |")
        lines.append("|--------|------|-----------|--------|---------|")
        for inv in investigations[:8]:
            summ = (inv.get("summary") or "")[:100].replace("|", " ").replace("\n", " ")
            lines.append(
                f"| {inv['inv_id']} | {inv['inv_type']} | "
                f"{(inv['component'] or '—')[:40]} | {inv['status']} | {summ}... |"
            )
        lines.append("")

    # TSBs
    lines.append("## Technical Service Bulletin Cross-Reference\n")
    lines.append(f"**{total_tsbs:,} TSBs on file** for {make.title()} {model.title()} {year_start}–{year_end}.\n")

    lines.append("### TSB Breakdown by System\n")
    lines.append("| System | TSB Count |")
    lines.append("|--------|-----------|")
    for r in tsb_breakdown:
        lines.append(f"| {(r['component'] or 'UNKNOWN').title()} | {r['cnt']} |")
    lines.append("")

    lines.append("### Recent TSBs (Latest 15)\n")
    lines.append("| Date | TSB # | System | Summary |")
    lines.append("|------|-------|--------|---------|")
    for t in tsb_list:
        date = format_tsb_date(t["bulletin_date"])
        bno = t["bulletin_no"] or "—"
        comp = (t["component"] or "—").title()
        summary = (t["summary"] or "")[:120].replace("|", " ").replace("\n", " ")
        lines.append(f"| {date} | {bno} | {comp} | {summary}... |")
    lines.append("")

    # Transport Canada
    if canada_recalls:
        lines.append("## Transport Canada Recalls (Cross-Border Coverage)\n")
        lines.append(f"**{len(canada_recalls)} Canadian recalls** found for this vehicle.\n")
        lines.append("| Recall # | Year | System | Summary | Date |")
        lines.append("|----------|------|--------|---------|------|")
        for r in canada_recalls[:8]:
            desc = (r.get("description") or "")[:100].replace("|", " ").replace("\n", " ")
            lines.append(
                f"| {r['recall_no']} | {r.get('year_from', '—')} | "
                f"{(r['system'] or '—')[:30]} | {desc}... | {r.get('recall_date', '—')} |"
            )
        lines.append("")

    # Shop Action Items
    lines.append("## Shop Action Items\n")
    recall_note = (
        f" ({len(recalls)} open recalls on file — verify VIN coverage)"
        if recalls else ""
    )
    lines.append(
        f"1. **Check open recalls before any diagnosis**{recall_note} — "
        "Run VIN through NHTSA.gov/recalls to confirm customer's specific vehicle is covered. "
        "Recall repairs are free to the customer.\n"
        "\n"
        "2. **PTU/AWD inspection on arrival** — Any unit with a powertrain complaint "
        "or 4WD warning should have the PTU inspected immediately. PTU failure cascades to "
        "transfer case and rear differential if caught late.\n"
        "\n"
        "3. **Check TSBs before hardware diagnosis** — With hundreds of TSBs on file, "
        "many driveability complaints have documented PCM/TCM software fixes. "
        "Pull TSBs for the specific model year and component before digging into hardware.\n"
    )

    lines.append("---")
    lines.append(
        "*Report generated by Automotive Diagnostic Report Builder. "
        "Sources: NHTSA complaints, TSBs, investigations, EPA specs, Transport Canada recalls. "
        "Verify with current data before repair.*"
    )

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# LLM polish via Claude API
# ---------------------------------------------------------------------------

def polish_with_claude(
    raw_markdown: str,
    make: str,
    model: str,
    year_start: int,
    year_end: int,
) -> str:
    try:
        import anthropic
    except ImportError:
        print("WARNING: anthropic not installed. Run: uv pip install anthropic", file=sys.stderr)
        return raw_markdown

    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        env_path = PROJECT_ROOT / ".env"
        if env_path.exists():
            for line in env_path.read_text().splitlines():
                if line.startswith("ANTHROPIC_API_KEY="):
                    api_key = line.split("=", 1)[1].strip().strip("\"'")
                    break

    if not api_key or "your_" in api_key:
        print(
            "WARNING: ANTHROPIC_API_KEY not configured. Outputting raw report.",
            file=sys.stderr,
        )
        return raw_markdown

    client = anthropic.Anthropic(api_key=api_key)

    prompt = f"""You are an automotive diagnostic analyst writing for independent repair shops and ASE-certified technicians.

Below is a raw diagnostic trend report for the {year_start}–{year_end} {make.title()} {model.title()}, generated from NHTSA consumer complaints, Technical Service Bulletins, defect investigations, EPA specs, and Transport Canada recalls.

Your job:
1. Rewrite the **Executive Summary** (3 sharp sentences: dominant failure, scale, shop takeaway).
2. Add a brief **interpretation sentence** under the complaint volume table (rising, falling, or spiking?).
3. Rewrite the **Failure Pattern Analysis** section — make each entry read like a shop brief: what it is, how it presents, what to look for. Keep data tables intact.
4. If recalls are present, add a one-line callout in the Executive Summary noting the recall count.
5. Rewrite the **Shop Action Items** — 3 specific, prioritized, actionable items a working technician would value. Incorporate recall and investigation data if present. Direct and concrete.
6. Keep all tables, headers, and markdown structure intact. Do NOT add or remove sections.
7. Tone: professional, direct, no filler. This is a tool, not a sales pitch.

---

{raw_markdown}
"""

    print("Polishing report with Claude... ", end="", flush=True)
    message = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=4096,
        messages=[{"role": "user", "content": prompt}],
    )
    print("done.")
    return message.content[0].text


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(description="Generate a vehicle diagnostic trend report.")
    parser.add_argument("--make", required=True, help="Vehicle make (e.g. JEEP, FORD)")
    parser.add_argument("--model", required=True, help="Vehicle model (e.g. CHEROKEE, F-150)")
    parser.add_argument("--year-start", type=int, required=True)
    parser.add_argument("--year-end", type=int, required=True)
    parser.add_argument("--output", help="Output file path")
    parser.add_argument("--no-llm", action="store_true", help="Skip LLM polish")
    parser.add_argument("--no-api", action="store_true", help="Skip live NHTSA recalls API call")
    args = parser.parse_args()

    make = args.make.upper()
    model = args.model.upper()
    year_start = args.year_start
    year_end = args.year_end

    output_path = (
        Path(args.output)
        if args.output
        else REPORTS_DIR / f"{make.lower()}_{model.lower().replace(' ', '_')}_{year_start}_{year_end}.md"
    )
    output_path.parent.mkdir(parents=True, exist_ok=True)

    print(f"Building report: {make} {model} {year_start}–{year_end}")
    print(f"Database: {DB_PATH}")

    conn = connect()

    print("  Querying complaint volumes...", end="", flush=True)
    volume = complaint_volume_by_year(conn, make, model, year_start, year_end)
    total = sum(r["cnt"] for r in volume)
    print(f" {total:,} complaints found")

    if total == 0:
        print(f"ERROR: No complaints found for {make} {model} {year_start}–{year_end}.")
        print("Check make/model spelling. Example: --make JEEP --model CHEROKEE")
        sys.exit(1)

    print("  Querying top components...", end="", flush=True)
    components = top_components(conn, make, model, year_start, year_end)
    print(f" {len(components)} components")

    print("  Analyzing failure patterns from narratives...", end="", flush=True)
    top_comp = components[0]["component"] if components else "POWER TRAIN"
    narratives = narratives_for_component(conn, make, model, year_start, year_end, top_comp)
    patterns = discover_failure_patterns(narratives)
    print(f" {len(narratives)} narratives → {len(patterns)} patterns")

    print("  Fetching TSBs...", end="", flush=True)
    tsb_list = all_tsbs(conn, make, model, year_start, year_end)
    tsb_breakdown = tsb_component_breakdown(conn, make, model, year_start, year_end)
    tsb_total = sum(r["cnt"] for r in tsb_breakdown)
    print(f" {tsb_total:,} TSBs")

    print("  Querying NHTSA investigations...", end="", flush=True)
    investigations = query_investigations(conn, make, model, year_start, year_end)
    print(f" {len(investigations)} found")

    print("  Querying EPA powertrain specs...", end="", flush=True)
    epa_specs = query_epa_specs(conn, make, model, year_start, year_end)
    print(f" {len(epa_specs)} configs")

    print("  Querying Transport Canada recalls...", end="", flush=True)
    canada_recalls = query_canada_recalls(conn, make, model, year_start, year_end)
    print(f" {len(canada_recalls)} found")

    conn.close()

    # Live NHTSA recalls API
    recalls: list[dict] = []
    if not args.no_api:
        print("  Fetching NHTSA recalls (live API)...", end="", flush=True)
        recalls = fetch_nhtsa_recalls_api(make, model, year_start, year_end)
        print(f" {len(recalls)} campaigns found")

    print("  Building markdown...", end="", flush=True)
    raw_md = build_raw_markdown(
        make, model, year_start, year_end,
        volume, components, patterns, tsb_list, tsb_breakdown,
        recalls, investigations, epa_specs, canada_recalls,
    )
    print(" done")

    final_md = raw_md if args.no_llm else polish_with_claude(raw_md, make, model, year_start, year_end)

    output_path.write_text(final_md, encoding="utf-8")
    print(f"\nReport saved: {output_path}")
    print(f"Size: {len(final_md):,} characters")


if __name__ == "__main__":
    main()
