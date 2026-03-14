#!/usr/bin/env python3
# Checked AGENTS.md - implementing directly because this is a standalone CLI batch
# orchestrator with no auth/sensitive data (read-only SQLite, pass-through to report_builder).
"""
Batch Report Generator — generates Template A reports for the top-complained-about vehicles.

Usage:
    # Generate all 20 reports with LLM polish (takes ~20 min):
    .venv/bin/python3 scripts/batch_report.py

    # Skip LLM polish — raw SQL output only (fast, ~2 min):
    .venv/bin/python3 scripts/batch_report.py --no-llm

    # Skip live NHTSA API calls too:
    .venv/bin/python3 scripts/batch_report.py --no-llm --no-api

    # Only generate missing reports (idempotent re-run):
    .venv/bin/python3 scripts/batch_report.py --skip-existing

    # Limit to first N vehicles (for testing):
    .venv/bin/python3 scripts/batch_report.py --limit 3 --no-llm --no-api

Outputs:
    reports/<make>_<model>_<yr_start>_<yr_end>.md   — one per vehicle
    reports/INDEX.md                                 — summary table
"""

import argparse
import sys
import time
import traceback
from datetime import datetime
from pathlib import Path

# ---------------------------------------------------------------------------
# Vehicle batch list — top 20 by NHTSA complaint volume (queried 2026-03-13)
# Year window chosen to capture peak complaint density while giving enough
# historical depth (5-year windows, centred on 2016-2020 generation).
# ---------------------------------------------------------------------------

BATCH_VEHICLES: list[tuple[str, str, int, int]] = [
    # (make, model, year_start, year_end)   — sorted by complaint volume desc
    ("FORD",       "ESCAPE",           2013, 2019),
    ("FORD",       "FUSION",           2013, 2020),
    ("JEEP",       "GRAND CHEROKEE",   2014, 2021),
    ("FORD",       "EXPLORER",         2011, 2019),
    ("FORD",       "F-150 REGULAR CAB",2015, 2022),
    ("FORD",       "FOCUS",            2012, 2018),
    ("HYUNDAI",    "SONATA",           2011, 2019),
    ("CHEVROLET",  "MALIBU",           2013, 2019),
    ("FORD",       "EDGE",             2015, 2021),
    ("JEEP",       "WRANGLER",         2014, 2021),
    ("HONDA",      "CR-V",             2015, 2022),
    ("NISSAN",     "ALTIMA",           2013, 2020),
    ("HONDA",      "ACCORD",           2013, 2020),
    ("TOYOTA",     "PRIUS",            2010, 2019),
    ("TOYOTA",     "CAMRY",            2012, 2020),
    ("RAM",        "1500",             2013, 2020),
    ("HONDA",      "CIVIC",            2016, 2022),
    ("CHEVROLET",  "SILVERADO 1500",   2014, 2021),
    ("JEEP",       "CHEROKEE",         2014, 2021),
    ("KIA",        "SORENTO",          2015, 2021),
]

PROJECT_ROOT = Path(__file__).parent.parent
REPORTS_DIR = PROJECT_ROOT / "reports"


def _output_path(make: str, model: str, yr_start: int, yr_end: int) -> Path:
    slug = f"{make.lower()}_{model.lower().replace(' ', '_').replace('-', '_')}_{yr_start}_{yr_end}"
    return REPORTS_DIR / f"{slug}.md"


def generate_one(
    make: str,
    model: str,
    yr_start: int,
    yr_end: int,
    *,
    no_llm: bool = False,
    no_api: bool = False,
) -> Path:
    """Import report_builder and run it programmatically for one vehicle."""
    # Import here so sys.path manipulation is isolated
    sys.path.insert(0, str(PROJECT_ROOT / "scripts"))
    import report_builder as rb  # noqa: PLC0415

    out = _output_path(make, model, yr_start, yr_end)
    out.parent.mkdir(parents=True, exist_ok=True)

    conn = rb.connect()

    volume      = rb.complaint_volume_by_year(conn, make, model, yr_start, yr_end)
    components  = rb.top_components(conn, make, model, yr_start, yr_end)
    top_comp    = components[0]["component"] if components else "POWER TRAIN"
    narratives  = rb.narratives_for_component(conn, make, model, yr_start, yr_end, top_comp)
    patterns    = rb.discover_failure_patterns(narratives)
    tsb_list    = rb.all_tsbs(conn, make, model, yr_start, yr_end)
    tsb_break   = rb.tsb_component_breakdown(conn, make, model, yr_start, yr_end)
    invest      = rb.query_investigations(conn, make, model, yr_start, yr_end)
    epa_specs   = rb.query_epa_specs(conn, make, model, yr_start, yr_end)
    canada      = rb.query_canada_recalls(conn, make, model, yr_start, yr_end)
    conn.close()

    dtc_codes = rb.query_relevant_dtcs(components)
    recalls: list[dict] = []
    if not no_api:
        recalls = rb.fetch_nhtsa_recalls_api(make, model, yr_start, yr_end)

    raw_md = rb.build_raw_markdown(
        make, model, yr_start, yr_end,
        volume, components, patterns, tsb_list, tsb_break,
        recalls, invest, epa_specs, canada,
        dtc_codes=dtc_codes,
    )

    final_md = raw_md if no_llm else rb.polish_with_claude(raw_md, make, model, yr_start, yr_end)
    out.write_text(final_md, encoding="utf-8")
    return out


def build_index(results: list[dict]) -> str:
    """Render reports/INDEX.md from batch results."""
    lines = [
        "# Automotive Diagnostic Report Index",
        "",
        f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}",
        "",
        "| # | Make | Model | Years | Complaints | Status | Report |",
        "|---|------|-------|-------|------------|--------|--------|",
    ]
    for i, r in enumerate(results, 1):
        status = r["status"]
        icon = "✅" if status == "ok" else ("⏭️" if status == "skipped" else "❌")
        link = f"[view]({r['file'].name})" if r.get("file") else "—"
        complaints = f"{r.get('complaint_hint', '—'):>8}"
        lines.append(
            f"| {i} | {r['make']} | {r['model']} | {r['yr_start']}–{r['yr_end']} "
            f"| {complaints} | {icon} {status} | {link} |"
        )

    lines += [
        "",
        "---",
        f"*{sum(1 for r in results if r['status'] == 'ok')} generated · "
        f"{sum(1 for r in results if r['status'] == 'skipped')} skipped · "
        f"{sum(1 for r in results if r['status'] == 'error')} errors*",
    ]
    return "\n".join(lines) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser(description="Batch-generate vehicle diagnostic reports.")
    parser.add_argument("--no-llm",        action="store_true", help="Skip LLM polish on every report")
    parser.add_argument("--no-api",        action="store_true", help="Skip live NHTSA recalls API")
    parser.add_argument("--skip-existing", action="store_true", help="Skip reports that already exist")
    parser.add_argument("--limit",         type=int, default=0, help="Only generate first N reports (0 = all)")
    args = parser.parse_args()

    vehicles = BATCH_VEHICLES
    if args.limit:
        vehicles = vehicles[: args.limit]

    REPORTS_DIR.mkdir(parents=True, exist_ok=True)

    total = len(vehicles)
    results: list[dict] = []

    print(f"Batch report — {total} vehicles | no-llm={args.no_llm} | no-api={args.no_api}")
    print("=" * 60)

    for idx, (make, model, yr_start, yr_end) in enumerate(vehicles, 1):
        label = f"[{idx}/{total}] {make} {model} {yr_start}–{yr_end}"
        out = _output_path(make, model, yr_start, yr_end)

        if args.skip_existing and out.exists():
            size_kb = out.stat().st_size // 1024
            print(f"{label} — ⏭️  SKIPPED (exists, {size_kb} KB)")
            results.append({
                "make": make, "model": model, "yr_start": yr_start, "yr_end": yr_end,
                "status": "skipped", "file": out,
            })
            continue

        print(f"{label} — generating...")
        t0 = time.time()
        try:
            out_path = generate_one(
                make, model, yr_start, yr_end,
                no_llm=args.no_llm,
                no_api=args.no_api,
            )
            elapsed = time.time() - t0
            size_kb = out_path.stat().st_size // 1024
            print(f"    ✅ {out_path.name}  ({size_kb} KB, {elapsed:.0f}s)")
            results.append({
                "make": make, "model": model, "yr_start": yr_start, "yr_end": yr_end,
                "status": "ok", "file": out_path,
            })
        except Exception:
            elapsed = time.time() - t0
            print(f"    ❌ ERROR after {elapsed:.0f}s:")
            traceback.print_exc()
            results.append({
                "make": make, "model": model, "yr_start": yr_start, "yr_end": yr_end,
                "status": "error",
            })

    print("=" * 60)
    ok  = sum(1 for r in results if r["status"] == "ok")
    skp = sum(1 for r in results if r["status"] == "skipped")
    err = sum(1 for r in results if r["status"] == "error")
    print(f"Done: {ok} generated · {skp} skipped · {err} errors")

    index_path = REPORTS_DIR / "INDEX.md"
    index_path.write_text(build_index(results), encoding="utf-8")
    print(f"Index: {index_path}")


if __name__ == "__main__":
    main()
