#!/usr/bin/env python3
# Checked AGENTS.md - implementing directly because this is a standalone HTML/PDF
# generator with no auth, no DB writes, and no security-sensitive logic.
"""
Automotive Diagnostic Report Generator
Generates professional PDF reports for customer presentation.

Usage:
    python3 scripts/generate_report.py report_data.json
    python3 scripts/generate_report.py report_data.json --output reports/my_report.pdf
"""

import json
import sys
import os
import subprocess
import tempfile
import argparse
from pathlib import Path
from datetime import datetime

SCRIPT_DIR = Path(__file__).parent
NODE_PDF_HELPER = SCRIPT_DIR / "pdf_from_html.js"
FRONTEND_NODE = SCRIPT_DIR.parent / "src" / "frontend" / "node_modules" / ".bin" / "node"


def find_node() -> str:
    """Find node binary."""
    for candidate in ["node", "/usr/bin/node"]:
        try:
            result = subprocess.run(
                [candidate, "--version"], capture_output=True, text=True
            )
            if result.returncode == 0:
                return candidate
        except FileNotFoundError:
            continue
    raise RuntimeError("node not found. Install Node.js to generate PDFs.")


def html_to_pdf(html_content: str, output_path: str) -> None:
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".html", delete=False, encoding="utf-8"
    ) as f:
        f.write(html_content)
        tmp_html = f.name

    try:
        node = find_node()
        result = subprocess.run(
            [node, str(NODE_PDF_HELPER), tmp_html, output_path],
            capture_output=True,
            text=True,
            timeout=60,
        )
        if result.returncode != 0:
            raise RuntimeError(
                f"PDF generation failed:\n{result.stdout}\n{result.stderr}"
            )
    finally:
        os.unlink(tmp_html)


def escape(text: str) -> str:
    """Minimal HTML escaping."""
    return (
        str(text)
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


def render_list(items: list[str], icon: str = "✓") -> str:
    if not items:
        return "<p class='none'>None</p>"
    return "".join(
        f"<li><span class='icon'>{icon}</span>{escape(item)}</li>" for item in items
    )


def render_tests(tests: list[dict]) -> str:
    if not tests:
        return "<p class='none'>No tests recorded.</p>"
    html = ""
    for t in tests:
        procedure = t.get("procedure", "")
        significance = t.get("significance", "")
        html += f"""
        <div class="test-block">
            <div class="test-name">{escape(t.get('test_name', ''))}</div>
            {"<div class='test-procedure'><strong>Procedure:</strong> " + escape(procedure) + "</div>" if procedure else ""}
            <div class="test-result"><strong>Result:</strong> {escape(t.get('result', ''))}</div>
            {"<div class='test-sig'><em>" + escape(significance) + "</em></div>" if significance else ""}
        </div>"""
    return html


def generate_html(data: dict) -> str:
    shop = escape(data.get("shop_name", "YOUR SHOP NAME"))
    tech = escape(data.get("technician_name", ""))
    ro = escape(data.get("ro_number", ""))
    date = escape(data.get("date", datetime.today().strftime("%B %d, %Y")))
    is_pre = data.get("report_type", "post_repair") == "pre_repair"
    doc_title = "DIAGNOSTIC ASSESSMENT" if is_pre else "DIAGNOSTIC REPAIR REPORT"

    v = data.get("vehicle", {})
    year = escape(str(v.get("year", "")))
    make = escape(v.get("make", ""))
    model = escape(v.get("model", ""))
    vin = escape(v.get("vin", "N/A"))
    mileage = escape(str(v.get("mileage", "N/A")))

    concern = escape(data.get("customer_concern", ""))
    findings = escape(data.get("findings", ""))
    diagnosis = escape(data.get("diagnosis", ""))
    assessment = escape(data.get("assessment_level", ""))
    verification = escape(data.get("verification", ""))
    notes = escape(data.get("notes", ""))

    tests_html = render_tests(data.get("diagnostic_tests", []))
    recs_html = render_list(data.get("recommendations", []), "→")
    work_html = render_list(data.get("work_performed", []), "✓")
    declined_html = render_list(data.get("declined_services", []), "⚠")

    action_section = (
        f"""
        <div class="section">
            <div class="section-title">Recommended Repairs</div>
            <ul class="item-list">{recs_html}</ul>
        </div>"""
        if is_pre
        else f"""
        <div class="section">
            <div class="section-title">Work Performed</div>
            <ul class="item-list">{work_html}</ul>
        </div>"""
    )

    verify_section = (
        f"""
        <div class="section">
            <div class="section-title">Verification</div>
            <p>{verification}</p>
        </div>"""
        if verification and not is_pre
        else ""
    )

    declined_section = (
        f"""
        <div class="section declined">
            <div class="section-title">Declined Services</div>
            <ul class="item-list">{declined_html}</ul>
            <p class="declined-note">
                Customer was advised of the above recommendations. Technician is not
                responsible for conditions that may arise from declined services.
            </p>
        </div>"""
        if data.get("declined_services")
        else ""
    )

    notes_section = (
        f"""
        <div class="section">
            <div class="section-title">Additional Notes</div>
            <p>{notes}</p>
        </div>"""
        if notes
        else ""
    )

    ro_line = f"<div><strong>RO #:</strong> {ro}</div>" if ro else ""
    tech_line = f"<div><strong>Technician:</strong> {tech}</div>" if tech else ""
    assess_badge = (
        f"<div class='assessment-badge'>{assessment}</div>" if assessment else ""
    )

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>{doc_title}</title>
<style>
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{
    font-family: Arial, sans-serif;
    font-size: 11pt;
    color: #1a1a1a;
    background: white;
  }}
  @page {{
    size: Letter;
    margin: 0.75in 0.75in 0.85in 0.75in;
  }}

  .header {{
    display: flex;
    justify-content: space-between;
    align-items: flex-start;
    border-bottom: 3px solid #1a1a1a;
    padding-bottom: 12px;
    margin-bottom: 16px;
  }}
  .shop-name {{
    font-size: 20pt;
    font-weight: 800;
    text-transform: uppercase;
  }}
  .doc-title {{
    font-size: 9pt;
    color: #555;
    text-transform: uppercase;
    letter-spacing: 1px;
    margin-top: 3px;
  }}
  .header-meta {{
    text-align: right;
    font-size: 10pt;
    line-height: 1.7;
  }}

  .vehicle-bar {{
    background: #1a1a1a;
    color: white;
    padding: 10px 14px;
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 18px;
    border-radius: 2px;
  }}
  .vehicle-name {{
    font-size: 14pt;
    font-weight: 700;
    text-transform: uppercase;
  }}
  .vehicle-details {{
    font-size: 9pt;
    text-align: right;
    line-height: 1.6;
    opacity: 0.9;
  }}

  .section {{
    margin-bottom: 18px;
    page-break-inside: avoid;
  }}
  .section-title {{
    font-size: 8pt;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 1.5px;
    color: #555;
    border-bottom: 1px solid #ccc;
    padding-bottom: 4px;
    margin-bottom: 8px;
  }}
  .section p {{ line-height: 1.6; }}

  .diagnosis-block {{
    background: #f7f7f7;
    border-left: 4px solid #1a1a1a;
    padding: 10px 14px;
    margin: 8px 0;
  }}
  .diagnosis-label {{
    font-size: 8pt;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 1px;
    color: #555;
    margin-bottom: 4px;
  }}
  .diagnosis-text {{
    font-size: 12pt;
    font-weight: 700;
  }}
  .assessment-badge {{
    display: inline-block;
    margin-top: 6px;
    padding: 2px 10px;
    font-size: 8pt;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 1px;
    border: 1.5px solid #1a1a1a;
    border-radius: 2px;
  }}

  .test-block {{
    border: 1px solid #ddd;
    border-radius: 3px;
    padding: 8px 12px;
    margin-bottom: 8px;
    page-break-inside: avoid;
  }}
  .test-name {{ font-weight: 700; font-size: 10.5pt; margin-bottom: 3px; }}
  .test-procedure {{ color: #333; margin-bottom: 2px; }}
  .test-result {{ margin-bottom: 2px; }}
  .test-sig {{ color: #555; font-size: 9.5pt; }}

  .item-list {{ list-style: none; padding: 0; }}
  .item-list li {{
    padding: 4px 0;
    line-height: 1.5;
    border-bottom: 1px dotted #e0e0e0;
    display: flex;
    gap: 8px;
  }}
  .item-list li:last-child {{ border-bottom: none; }}
  .icon {{ min-width: 18px; }}

  .declined {{
    background: #fffbf0;
    padding: 12px;
    border: 1px solid #e8d080;
    border-radius: 3px;
  }}
  .declined .section-title {{ color: #7a5f00; border-color: #e8d080; }}
  .declined-note {{
    margin-top: 8px;
    font-size: 9pt;
    color: #7a5f00;
    font-style: italic;
    line-height: 1.5;
  }}
  .none {{ color: #999; font-style: italic; }}


  .footer {{
    margin-top: 20px;
    padding-top: 8px;
    border-top: 1px solid #ddd;
    font-size: 8pt;
    color: #888;
    text-align: center;
    line-height: 1.5;
  }}
</style>
</head>
<body>

<div class="header">
  <div>
    <div class="shop-name">{shop}</div>
    <div class="doc-title">{doc_title}</div>
  </div>
  <div class="header-meta">
    <div><strong>Date:</strong> {date}</div>
    {ro_line}
    {tech_line}
  </div>
</div>

<div class="vehicle-bar">
  <div class="vehicle-name">{year} {make} {model}</div>
  <div class="vehicle-details">
    <div>VIN: {vin}</div>
    <div>Mileage: {mileage}</div>
  </div>
</div>

<div class="section">
  <div class="section-title">Customer Concern</div>
  <p>{concern}</p>
</div>

<div class="section">
  <div class="section-title">Diagnostic Tests Performed</div>
  {tests_html}
</div>

<div class="section">
  <div class="section-title">Findings</div>
  <p>{findings}</p>
</div>

<div class="section">
  <div class="section-title">Diagnosis</div>
  <div class="diagnosis-block">
    <div class="diagnosis-label">Root Cause Identified</div>
    <div class="diagnosis-text">{diagnosis}</div>
    {assess_badge}
  </div>
</div>

{action_section}
{verify_section}
{declined_section}
{notes_section}

<!-- Checked AGENTS.md - implementing directly, no security concerns, removing signature block per user request -->

<div class="footer">
  This report documents diagnostic findings and work performed. All diagnoses are based on
  observed symptoms, physical testing, and technician expertise. Additional issues may be
  discovered during repair. Estimates are subject to change upon further inspection.
</div>

</body>
</html>"""


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Generate automotive diagnostic PDF report"
    )
    parser.add_argument("input", help="JSON file containing report data")
    parser.add_argument(
        "--output", "-o", help="Output PDF path (default: reports/<auto>.pdf)"
    )
    args = parser.parse_args()

    input_path = Path(args.input)
    if not input_path.exists():
        print(f"ERROR: Input file not found: {input_path}", file=sys.stderr)
        sys.exit(1)

    with open(input_path, encoding="utf-8") as f:
        data = json.load(f)

    if args.output:
        output_path = args.output
    else:
        reports_dir = Path(__file__).parent.parent / "reports"
        reports_dir.mkdir(exist_ok=True)
        v = data.get("vehicle", {})
        slug = "_".join(
            filter(
                None,
                [
                    str(v.get("year", "")),
                    v.get("make", "").upper(),
                    v.get("model", "").upper().replace(" ", "-"),
                    data.get("ro_number", ""),
                ],
            )
        )
        timestamp = datetime.now().strftime("%Y%m%d_%H%M")
        output_path = str(reports_dir / f"diag_report_{slug}_{timestamp}.pdf")

    print("Generating HTML...")
    html = generate_html(data)

    print("Converting to PDF...")
    html_to_pdf(html, output_path)

    print(f"Report saved: {output_path}")


if __name__ == "__main__":
    main()
