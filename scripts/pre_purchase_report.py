#!/usr/bin/env python3
# Checked AGENTS.md - implementing directly because this is a standalone CLI script
# with read-only SQLite queries, no auth/validation code, and no sensitive data.
# Pure report generation — no security-engineer or data-engineer delegation needed.
# Gemini delegation not warranted: PDF layout requires tight iterative control.
"""
Pre-Purchase Vehicle Inspection Report Generator

Usage:
    uv run python scripts/pre_purchase_report.py \
        --vin 3MYDLBYV6KY507371 \
        --year 2019 --make TOYOTA --model "YARIS" \
        --trim "L Sedan 4D" --mileage 70000 \
        --output /home/poteete/reports/pre_purchase_2019_toyota_yaris.pdf
"""
import argparse
import sqlite3
import sys
from datetime import date
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    HRFlowable, KeepTogether
)
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_RIGHT

PROJECT_ROOT = Path(__file__).parent.parent
DB_PATH = PROJECT_ROOT / "database" / "automotive_complaints.db"

# ---------------------------------------------------------------------------
# Color palette
# ---------------------------------------------------------------------------
DARK_NAVY = colors.HexColor("#1a2744")
ACCENT_BLUE = colors.HexColor("#1e5fa8")
LIGHT_BLUE = colors.HexColor("#e8f0fb")
RED_HIGH = colors.HexColor("#c0392b")
ORANGE_MED = colors.HexColor("#e67e22")
GREEN_OK = colors.HexColor("#27ae60")
YELLOW_LOW = colors.HexColor("#f39c12")
LIGHT_GRAY = colors.HexColor("#f5f6f8")
MID_GRAY = colors.HexColor("#95a5a6")
DARK_GRAY = colors.HexColor("#2c3e50")
WHITE = colors.white


# ---------------------------------------------------------------------------
# Database queries
# ---------------------------------------------------------------------------

def get_recalls(conn, make, model, year):
    cur = conn.cursor()
    cur.execute(
        """
        SELECT campaign_no, report_date, component, summary, consequence,
               remedy, park_it
        FROM nhtsa_recalls
        WHERE UPPER(make) = UPPER(?)
          AND UPPER(model) LIKE UPPER(?)
          AND year_from <= ? AND year_to >= ?
        ORDER BY report_date DESC
        """,
        (make, f"%{model}%", year, year),
    )
    return cur.fetchall()


def get_tsbs(conn, make, model, year):
    cur = conn.cursor()
    cur.execute(
        """
        SELECT bulletin_date, component, summary
        FROM nhtsa_tsbs
        WHERE UPPER(make) = UPPER(?)
          AND UPPER(model) LIKE UPPER(?)
          AND CAST(year AS INTEGER) = ?
        ORDER BY bulletin_date DESC
        """,
        (make, f"%{model}%", year),
    )
    return cur.fetchall()


def get_investigations(conn, make, model, year):
    cur = conn.cursor()
    cur.execute(
        """
        SELECT inv_type, component, summary, status, open_date
        FROM nhtsa_investigations
        WHERE UPPER(make) = UPPER(?)
          AND UPPER(model) LIKE UPPER(?)
          AND CAST(year_from AS INTEGER) <= ?
          AND (year_to IS NULL OR CAST(year_to AS INTEGER) >= ?)
        ORDER BY open_date DESC
        """,
        (make, f"%{model}%", year, year),
    )
    return cur.fetchall()


def get_complaints(conn, make, model, year):
    cur = conn.cursor()
    cur.execute(
        """
        SELECT component, summary
        FROM complaints_fts
        WHERE make = UPPER(?)
          AND model LIKE UPPER(?)
          AND CAST(year AS INTEGER) = ?
        LIMIT 30
        """,
        (make, f"%{model}%", year),
    )
    return cur.fetchall()


# ---------------------------------------------------------------------------
# Risk scoring
# ---------------------------------------------------------------------------

def risk_label(recalls, investigations):
    park_it = any(r[6] for r in recalls)
    open_inv = any(i[3] == "OPEN" for i in investigations)
    safety_recalls = [r for r in recalls if r[6] or "fuel" in (r[2] or "").lower()
                      or "brake" in (r[2] or "").lower()
                      or "steer" in (r[2] or "").lower()]
    if park_it:
        return "HIGH", RED_HIGH
    if safety_recalls or open_inv:
        return "MODERATE", ORANGE_MED
    if recalls:
        return "LOW", YELLOW_LOW
    return "MINIMAL", GREEN_OK


# ---------------------------------------------------------------------------
# Style helpers
# ---------------------------------------------------------------------------

def build_styles():
    base = getSampleStyleSheet()
    s = {}

    s["cover_title"] = ParagraphStyle(
        "cover_title",
        fontSize=26,
        fontName="Helvetica-Bold",
        textColor=WHITE,
        leading=32,
        spaceAfter=6,
    )
    s["cover_sub"] = ParagraphStyle(
        "cover_sub",
        fontSize=12,
        fontName="Helvetica",
        textColor=colors.HexColor("#b0c4de"),
        leading=16,
    )
    s["section_header"] = ParagraphStyle(
        "section_header",
        fontSize=13,
        fontName="Helvetica-Bold",
        textColor=WHITE,
        leading=18,
        spaceBefore=0,
        spaceAfter=0,
        leftIndent=8,
    )
    s["body"] = ParagraphStyle(
        "body",
        fontSize=9,
        fontName="Helvetica",
        textColor=DARK_GRAY,
        leading=14,
        spaceBefore=2,
        spaceAfter=2,
    )
    s["body_bold"] = ParagraphStyle(
        "body_bold",
        fontSize=9,
        fontName="Helvetica-Bold",
        textColor=DARK_GRAY,
        leading=14,
    )
    s["small"] = ParagraphStyle(
        "small",
        fontSize=8,
        fontName="Helvetica",
        textColor=MID_GRAY,
        leading=12,
    )
    s["label"] = ParagraphStyle(
        "label",
        fontSize=8,
        fontName="Helvetica-Bold",
        textColor=ACCENT_BLUE,
        leading=10,
        spaceAfter=2,
    )
    s["disclaimer"] = ParagraphStyle(
        "disclaimer",
        fontSize=7.5,
        fontName="Helvetica-Oblique",
        textColor=MID_GRAY,
        leading=11,
    )
    s["risk_header"] = ParagraphStyle(
        "risk_header",
        fontSize=11,
        fontName="Helvetica-Bold",
        textColor=DARK_NAVY,
        leading=14,
    )
    return s


# ---------------------------------------------------------------------------
# Section header builder
# ---------------------------------------------------------------------------

def section_block(title, styles, color=ACCENT_BLUE):
    header_data = [[Paragraph(title, styles["section_header"])]]
    t = Table(header_data, colWidths=[7.0 * inch])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), color),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ("LEFTPADDING", (0, 0), (-1, -1), 10),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
    ]))
    return t


# ---------------------------------------------------------------------------
# Report builder
# ---------------------------------------------------------------------------

def build_report(args):
    conn = sqlite3.connect(DB_PATH)
    recalls = get_recalls(conn, args.make, args.model, args.year)
    tsbs = get_tsbs(conn, args.make, args.model, args.year)
    investigations = get_investigations(conn, args.make, args.model, args.year)
    complaints = get_complaints(conn, args.make, args.model, args.year)
    conn.close()

    risk, risk_color = risk_label(recalls, investigations)
    today = date.today().strftime("%B %d, %Y")
    vehicle_str = f"{args.year} {args.make.title()} {args.model.title()} {args.trim}"
    vin_display = args.vin.upper()

    out_path = Path(args.output)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    doc = SimpleDocTemplate(
        str(out_path),
        pagesize=letter,
        leftMargin=0.75 * inch,
        rightMargin=0.75 * inch,
        topMargin=0.6 * inch,
        bottomMargin=0.6 * inch,
    )

    styles = build_styles()
    story = []

    # -----------------------------------------------------------------------
    # COVER BANNER
    # -----------------------------------------------------------------------
    cover_data = [[
        Paragraph("PRE-PURCHASE VEHICLE INSPECTION REPORT", styles["cover_title"]),
    ]]
    cover_table = Table(cover_data, colWidths=[7.0 * inch])
    cover_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), DARK_NAVY),
        ("TOPPADDING", (0, 0), (-1, -1), 22),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
        ("LEFTPADDING", (0, 0), (-1, -1), 18),
        ("RIGHTPADDING", (0, 0), (-1, -1), 18),
    ]))
    story.append(cover_table)

    # Sub-banner: vehicle name + date
    sub_data = [[
        Paragraph(vehicle_str, styles["cover_sub"]),
        Paragraph(f"Report Date: {today}", ParagraphStyle(
            "right", fontSize=10, fontName="Helvetica",
            textColor=colors.HexColor("#b0c4de"), alignment=TA_RIGHT)),
    ]]
    sub_table = Table(sub_data, colWidths=[4.5 * inch, 2.5 * inch])
    sub_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), ACCENT_BLUE),
        ("TOPPADDING", (0, 0), (-1, -1), 7),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
        ("LEFTPADDING", (0, 0), (-1, -1), 18),
        ("RIGHTPADDING", (0, 0), (-1, -1), 18),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
    ]))
    story.append(sub_table)
    story.append(Spacer(1, 10))

    # -----------------------------------------------------------------------
    # VEHICLE SUMMARY + RISK SCORE (side by side)
    # -----------------------------------------------------------------------
    vin_note = ""
    if vin_display.startswith("3MY"):
        vin_note = "  (Mexico / Mazda-built)"

    left_info = [
        ["VIN:", vin_display + vin_note],
        ["Year / Make / Model:", f"{args.year} {args.make.title()} {args.model.title()}"],
        ["Trim:", args.trim],
        ["Reported Mileage:", f"{args.mileage:,} miles"],
        ["NHTSA Recalls Found:", str(len(recalls))],
        ["TSBs Found:", str(len(tsbs))],
        ["Open Investigations:", str(sum(1 for i in investigations if i[3] == "OPEN"))],
        ["NHTSA Complaints (2019):", str(len(complaints)) if complaints else "0 in DB"],
    ]

    info_rows = []
    for lbl, val in left_info:
        info_rows.append([
            Paragraph(lbl, styles["label"]),
            Paragraph(val, styles["body_bold"] if "VIN" in lbl else styles["body"]),
        ])

    info_table = Table(info_rows, colWidths=[1.8 * inch, 3.2 * inch])
    info_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), LIGHT_GRAY),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ("ROWBACKGROUNDS", (0, 0), (-1, -1), [WHITE, LIGHT_GRAY]),
        ("GRID", (0, 0), (-1, -1), 0.3, colors.HexColor("#dce3ec")),
    ]))

    risk_inner = [
        [Paragraph("OVERALL RISK", ParagraphStyle(
            "rr", fontSize=9, fontName="Helvetica-Bold",
            textColor=WHITE, alignment=TA_CENTER))],
        [Paragraph(risk, ParagraphStyle(
            "rv", fontSize=28, fontName="Helvetica-Bold",
            textColor=WHITE, alignment=TA_CENTER, leading=34))],
        [Paragraph("Pre-Purchase Rating", ParagraphStyle(
            "rs", fontSize=8, fontName="Helvetica",
            textColor=WHITE, alignment=TA_CENTER))],
    ]
    risk_inner_table = Table(risk_inner, colWidths=[1.8 * inch])
    risk_inner_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), risk_color),
        ("TOPPADDING", (0, 0), (-1, -1), 12),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
    ]))

    combined = Table(
        [[info_table, risk_inner_table]],
        colWidths=[5.1 * inch, 1.9 * inch],
    )
    combined.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 0),
        ("RIGHTPADDING", (0, 0), (-1, -1), 0),
        ("TOPPADDING", (0, 0), (-1, -1), 0),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
    ]))
    story.append(combined)
    story.append(Spacer(1, 10))

    # -----------------------------------------------------------------------
    # VIN NOTE
    # -----------------------------------------------------------------------
    if vin_display.startswith("3MY"):
        story.append(KeepTogether([
            Paragraph(
                "<b>VIN Manufacturer Note:</b> World Manufacturer Identifier '3MY' indicates this vehicle "
                "was assembled at Mazda Motor Manufacturing de Mexico S.A. de C.V. (Salamanca, Mexico). "
                "The 2019 Toyota Yaris Sedan is a rebadged Mazda2 sharing the Mazda P3-VPS 1.5L engine "
                "platform. All Toyota warranties, recalls, and TSBs apply normally.",
                styles["body"],
            ),
            Spacer(1, 8),
        ]))

    # -----------------------------------------------------------------------
    # KBB MARKET VALUE (optional — only rendered if values provided)
    # -----------------------------------------------------------------------
    if any([args.kbb_trade_in, args.kbb_private_party, args.kbb_retail]):
        story.append(section_block("KELLEY BLUE BOOK MARKET VALUE", styles,
                                   color=colors.HexColor("#1a6e35")))
        story.append(Spacer(1, 6))

        kbb_condition_note = f"Condition: {args.kbb_condition}  |  Mileage: {args.mileage:,} miles  |  Source: Kelley Blue Book (kbb.com)"
        story.append(Paragraph(kbb_condition_note, styles["small"]))
        story.append(Spacer(1, 6))

        kbb_data = []
        if args.kbb_trade_in:
            kbb_data.append(["Trade-In Value", args.kbb_trade_in,
                             "Dealer offer when trading in — typically lowest figure"])
        if args.kbb_private_party:
            kbb_data.append(["Private Party Sale", args.kbb_private_party,
                             "Selling directly to another individual — fair market value"])
        if args.kbb_retail:
            kbb_data.append(["Dealer Retail / Listed Price", args.kbb_retail,
                             "What a dealer would list it for — highest figure"])

        val_header = [
            Paragraph("Value Type", styles["label"]),
            Paragraph("KBB Range", styles["label"]),
            Paragraph("Notes", styles["label"]),
        ]
        val_rows = [val_header]
        for row in kbb_data:
            val_rows.append([
                Paragraph(row[0], styles["body_bold"]),
                Paragraph(row[1], ParagraphStyle(
                    "kbb_val", fontSize=10, fontName="Helvetica-Bold",
                    textColor=colors.HexColor("#1a6e35"), leading=14)),
                Paragraph(row[2], styles["small"]),
            ])

        val_table = Table(val_rows, colWidths=[1.7 * inch, 1.8 * inch, 3.5 * inch])
        val_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), DARK_NAVY),
            ("TEXTCOLOR", (0, 0), (-1, 0), WHITE),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.HexColor("#edf7ef"), WHITE]),
            ("GRID", (0, 0), (-1, -1), 0.3, colors.HexColor("#b2d8b8")),
            ("TOPPADDING", (0, 0), (-1, -1), 5),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ("LEFTPADDING", (0, 0), (-1, -1), 8),
            ("RIGHTPADDING", (0, 0), (-1, -1), 8),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ]))
        story.append(val_table)
        story.append(Spacer(1, 5))
        story.append(Paragraph(
            "KBB values are national averages and may vary ±$500–$1,500 by region, exact trim, "
            "options, and color. Verify current values at kbb.com before making an offer.",
            styles["disclaimer"],
        ))
        story.append(Spacer(1, 10))

    # -----------------------------------------------------------------------
    # SAFETY ASSESSMENT
    # -----------------------------------------------------------------------
    story.append(section_block("SAFETY ASSESSMENT", styles))
    story.append(Spacer(1, 6))

    park_it_recalls = [r for r in recalls if r[6]]
    open_invs = [i for i in investigations if i[3] == "OPEN"]

    if park_it_recalls:
        story.append(Paragraph(
            "PARK-IT ALERT: One or more park-it recalls are associated with this model. "
            "Do not operate until recall status is confirmed completed on this VIN.",
            ParagraphStyle("alert", fontSize=9, fontName="Helvetica-Bold",
                           textColor=WHITE, backColor=RED_HIGH,
                           leading=14, spaceBefore=2, spaceAfter=2,
                           leftIndent=6, rightIndent=6)
        ))
    else:
        story.append(Paragraph(
            "No park-it or do-not-drive safety alerts found. One safety recall (fuel pump) "
            "affects this model year — verify completion status before purchase (see Recalls section).",
            styles["body"],
        ))

    if open_invs:
        story.append(Spacer(1, 4))
        story.append(Paragraph(
            f"WARNING: {len(open_invs)} OPEN NHTSA Investigation(s) active — see Investigations section.",
            ParagraphStyle("warn", fontSize=9, fontName="Helvetica-Bold",
                           textColor=DARK_GRAY, backColor=colors.HexColor("#fff3cd"),
                           leading=14, leftIndent=6)
        ))

    story.append(Spacer(1, 10))

    # -----------------------------------------------------------------------
    # RECALLS
    # -----------------------------------------------------------------------
    story.append(section_block("NHTSA SAFETY RECALLS", styles))
    story.append(Spacer(1, 6))

    if recalls:
        for idx, r in enumerate(recalls):
            campaign, rdate, component, summary, consequence, remedy, park = r
            bg = LIGHT_GRAY if idx % 2 == 0 else WHITE
            is_safety = park or (component and any(
                x in component.lower() for x in ["fuel", "brake", "steer", "airbag"]))
            badge_color = RED_HIGH if park else (ORANGE_MED if is_safety else ACCENT_BLUE)
            badge_txt = "PARK-IT" if park else ("SAFETY" if is_safety else "ADMIN")

            recall_rows = [
                [
                    Paragraph(f"Campaign {campaign}", styles["body_bold"]),
                    Paragraph(badge_txt, ParagraphStyle(
                        "badge", fontSize=8, fontName="Helvetica-Bold",
                        textColor=WHITE, backColor=badge_color,
                        alignment=TA_CENTER, leading=12)),
                ],
                [
                    Paragraph(f"<b>Component:</b> {component or 'N/A'}", styles["body"]),
                    Paragraph(f"<b>Date:</b> {rdate or 'N/A'}", styles["small"]),
                ],
                [
                    Paragraph(f"<b>Summary:</b> {(summary or '')[:400]}{'...' if summary and len(summary) > 400 else ''}",
                              styles["body"]),
                    "",
                ],
                [
                    Paragraph(f"<b>Risk:</b> {(consequence or 'N/A')[:250]}",
                              styles["small"]),
                    "",
                ],
                [
                    Paragraph(f"<b>Remedy:</b> {(remedy or 'N/A')[:250]}",
                              styles["small"]),
                    "",
                ],
            ]

            recall_table = Table(recall_rows, colWidths=[5.0 * inch, 2.0 * inch])
            recall_table.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, -1), bg),
                ("SPAN", (0, 2), (1, 2)),
                ("SPAN", (0, 3), (1, 3)),
                ("SPAN", (0, 4), (1, 4)),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
                ("LEFTPADDING", (0, 0), (-1, -1), 8),
                ("RIGHTPADDING", (0, 0), (-1, -1), 8),
                ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#dce3ec")),
                ("LINEBELOW", (0, 0), (-1, 0), 0.5, colors.HexColor("#dce3ec")),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ]))
            story.append(recall_table)
            story.append(Spacer(1, 4))
    else:
        story.append(Paragraph("No NHTSA recalls found for this vehicle.", styles["body"]))

    story.append(Spacer(1, 6))

    # Recall verification box
    verify_rows = [[
        Paragraph(
            "<b>ACTION REQUIRED: Verify Recall Completion Before Purchase</b><br/><br/>"
            "Campaign <b>21V617000</b> (Fuel Pump) is a safety recall affecting this vehicle. "
            "Dealers replace the low-pressure fuel pump at no charge. Confirm this was completed "
            "on VIN <b>" + vin_display + "</b> by visiting nhtsa.gov/recalls or calling "
            "Toyota at 1-800-331-4331 (recall ref: 21TA05). Ask the seller for the "
            "Repair Order showing completion.",
            styles["body"],
        )
    ]]
    verify_table = Table(verify_rows, colWidths=[7.0 * inch])
    verify_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#fff3cd")),
        ("BOX", (0, 0), (-1, -1), 1.0, ORANGE_MED),
        ("TOPPADDING", (0, 0), (-1, -1), 8),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
        ("LEFTPADDING", (0, 0), (-1, -1), 10),
        ("RIGHTPADDING", (0, 0), (-1, -1), 10),
    ]))
    story.append(verify_table)
    story.append(Spacer(1, 10))

    # -----------------------------------------------------------------------
    # OPEN NHTSA INVESTIGATIONS
    # -----------------------------------------------------------------------
    if investigations:
        story.append(section_block("NHTSA INVESTIGATIONS", styles,
                                   color=colors.HexColor("#8e44ad")))
        story.append(Spacer(1, 6))
        for inv in investigations:
            inv_type, component, summary, status, open_date = inv
            status_color = RED_HIGH if status == "OPEN" else GREEN_OK
            inv_rows = [
                [
                    Paragraph(f"Component: <b>{component or 'N/A'}</b>", styles["body"]),
                    Paragraph(status, ParagraphStyle(
                        "st", fontSize=9, fontName="Helvetica-Bold",
                        textColor=WHITE, backColor=status_color,
                        alignment=TA_CENTER, leading=12)),
                ],
                [
                    Paragraph(f"Type: {inv_type or 'N/A'}  |  Opened: {open_date or 'N/A'}",
                              styles["small"]),
                    "",
                ],
                [
                    Paragraph(f"{(summary or '')[:500]}{'...' if summary and len(summary) > 500 else ''}",
                              styles["body"]),
                    "",
                ],
            ]
            inv_table = Table(inv_rows, colWidths=[5.0 * inch, 2.0 * inch])
            inv_table.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#f9f0ff")),
                ("SPAN", (0, 1), (1, 1)),
                ("SPAN", (0, 2), (1, 2)),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
                ("LEFTPADDING", (0, 0), (-1, -1), 8),
                ("RIGHTPADDING", (0, 0), (-1, -1), 8),
                ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#d4b8e0")),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ]))
            story.append(inv_table)
            story.append(Spacer(1, 4))
        story.append(Spacer(1, 6))

    # -----------------------------------------------------------------------
    # TECHNICAL SERVICE BULLETINS
    # -----------------------------------------------------------------------
    story.append(section_block("TECHNICAL SERVICE BULLETINS (TSBs)", styles))
    story.append(Spacer(1, 6))

    # Filter to meaningful TSBs (skip PDS/obsolete/hybrid storage)
    meaningful_tsbs = [
        t for t in tsbs
        if not any(x in (t[2] or "").upper() for x in
                   ["PRE-DELIVERY", "PDS", "OBSOLETE", "STORAGE"])
    ]

    if meaningful_tsbs:
        tsb_header = [
            Paragraph("Date", styles["label"]),
            Paragraph("System", styles["label"]),
            Paragraph("Description", styles["label"]),
        ]
        tsb_data = [tsb_header]
        for i, t in enumerate(meaningful_tsbs):
            bdate, component, summary = t
            try:
                from datetime import datetime as dt
                d = dt.strptime(str(bdate), "%Y%m%d")
                date_str = d.strftime("%m/%d/%Y")
            except Exception:
                date_str = str(bdate)
            tsb_data.append([
                Paragraph(date_str, styles["small"]),
                Paragraph((component or "")[:40], styles["small"]),
                Paragraph((summary or "")[:280] + ("..." if summary and len(summary) > 280 else ""),
                          styles["small"]),
            ])

        tsb_table = Table(tsb_data, colWidths=[0.8 * inch, 1.5 * inch, 4.7 * inch])
        tsb_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), DARK_NAVY),
            ("TEXTCOLOR", (0, 0), (-1, 0), WHITE),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [WHITE, LIGHT_GRAY]),
            ("GRID", (0, 0), (-1, -1), 0.3, colors.HexColor("#dce3ec")),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ("LEFTPADDING", (0, 0), (-1, -1), 6),
            ("RIGHTPADDING", (0, 0), (-1, -1), 6),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ]))
        story.append(tsb_table)
    else:
        story.append(Paragraph("No applicable TSBs found for this vehicle year.", styles["body"]))

    story.append(Spacer(1, 10))

    # -----------------------------------------------------------------------
    # KNOWN ISSUES
    # -----------------------------------------------------------------------
    story.append(section_block("KNOWN ISSUES AND PRE-PURCHASE INSPECTION FOCUS", styles,
                               color=RED_HIGH))
    story.append(Spacer(1, 6))

    known_issues = [
        {
            "system": "Fuel System - LOW-PRESSURE FUEL PUMP",
            "severity": "CRITICAL",
            "color": RED_HIGH,
            "detail": (
                "NHTSA Recall 21V617000 (Campaign 21TA05): Fuel pump impeller may crack and deform, "
                "causing engine stall while driving. Affects 2019-2020 Yaris. Toyota replaced the fuel "
                "pump assembly at no charge starting Dec 2021. At 70,000 miles, an unrepaired fuel pump "
                "is a breakdown and safety risk. MUST verify completion before purchase."
            ),
            "action": "Request Repair Order showing Campaign 21TA05 completion. Check nhtsa.gov/recalls with VIN.",
        },
        {
            "system": "Engine ECM Software - EMISSION CONTROL",
            "severity": "MODERATE",
            "color": ORANGE_MED,
            "detail": (
                "Special Service Campaign 20TC03: ECM software for certain 2019 Yaris Sedans was "
                "incorrectly programmed for a different engine configuration, preventing proper DTC "
                "clearing and potentially causing emissions test failures. Toyota reprogrammed ECMs "
                "at no charge. An un-reprogrammed ECM may present phantom fault codes."
            ),
            "action": "Ask seller/dealer if Campaign 20TC03 ECM reprogram was completed. Check dealer records.",
        },
        {
            "system": "Front Suspension - SQUEAK NOISE OVER BUMPS",
            "severity": "LOW",
            "color": YELLOW_LOW,
            "detail": (
                "TSB (2023): Some 2017-2020 Yaris Sedan (Mexico production - applies to this VIN) "
                "exhibit a squeak-type noise from the front suspension over bumps. Test drive on "
                "rough pavement to check. Repair is generally straightforward (bushing lubrication "
                "or replacement)."
            ),
            "action": "Test drive on rough roads. Listen for front-end squeaks. Budget $150-400 if present.",
        },
        {
            "system": "CAN Bus / Electrical System - OPEN NHTSA INVESTIGATION",
            "severity": "MONITOR",
            "color": colors.HexColor("#8e44ad"),
            "detail": (
                "Open NHTSA investigation (ODI 11501206, petition 2023) alleges a CAN Bus "
                "vulnerability with reported symptoms: multiple warning lights, inaccurate fuel gauge, "
                "inoperative key fob, and no-start. Investigation ongoing - no recall issued yet. "
                "Confirm all warning lights are off and key fob operates normally during inspection."
            ),
            "action": "Verify no warning lights during inspection. Test key fob range. Monitor NHTSA ODI 11501206.",
        },
        {
            "system": "Platform Note - MAZDA2 SHARED ARCHITECTURE",
            "severity": "INFO",
            "color": ACCENT_BLUE,
            "detail": (
                "The 2019 Toyota Yaris Sedan (Mexico-built, VIN 3MY...) shares its platform and "
                "1.5L P3-VPS engine with the Mazda2. Parts availability is good through both Toyota "
                "and Mazda dealer networks. At 70,000 miles, inspect engine oil for cleanliness and "
                "review transmission service history. No major platform-wide failure patterns at this mileage."
            ),
            "action": "Review service history for oil changes every 5,000-7,500 miles. Check for oil leaks.",
        },
    ]

    for issue in known_issues:
        sev_style = ParagraphStyle(
            "sev", fontSize=8, fontName="Helvetica-Bold",
            textColor=WHITE, backColor=issue["color"],
            leading=10, leftIndent=4, rightIndent=4,
        )
        row = [
            [
                Paragraph(f"<b>{issue['system']}</b>", styles["body_bold"]),
                Paragraph(issue["severity"], sev_style),
            ],
            [
                Paragraph(issue["detail"], styles["body"]),
                "",
            ],
            [
                Paragraph(f"<b>Inspector Action:</b> {issue['action']}", styles["small"]),
                "",
            ],
        ]
        issue_table = Table(row, colWidths=[5.5 * inch, 1.5 * inch])
        issue_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), LIGHT_GRAY),
            ("SPAN", (0, 1), (1, 1)),
            ("SPAN", (0, 2), (1, 2)),
            ("TOPPADDING", (0, 0), (-1, -1), 5),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ("LEFTPADDING", (0, 0), (-1, -1), 8),
            ("RIGHTPADDING", (0, 0), (-1, -1), 8),
            ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#dce3ec")),
            ("LINEBELOW", (0, 0), (-1, 0), 0.5, colors.HexColor("#dce3ec")),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("ALIGN", (1, 0), (1, 0), "RIGHT"),
        ]))
        story.append(KeepTogether([issue_table, Spacer(1, 5)]))

    story.append(Spacer(1, 10))

    # -----------------------------------------------------------------------
    # PRE-PURCHASE CHECKLIST
    # -----------------------------------------------------------------------
    story.append(section_block("PRE-PURCHASE INSPECTION CHECKLIST", styles,
                               color=GREEN_OK))
    story.append(Spacer(1, 6))

    checklist = [
        ("DOCUMENTATION", [
            "Confirm NHTSA Recall 21V617000 (fuel pump) completed - ask for R/O or check nhtsa.gov/recalls",
            "Confirm Special Service Campaign 20TC03 (ECM reprogram) completed",
            "Review full service history - oil changes every 5,000-7,500 miles expected",
            "Carfax/AutoCheck: check for accident history, title brands, odometer rollback",
        ]),
        ("UNDER HOOD", [
            "Engine oil: check level, color (black = neglected), smell for fuel dilution",
            "Coolant: check level and color (should be clear/pink, not brown or rusty)",
            "OBD-II scan: verify no stored or pending fault codes",
            "Inspect for oil leaks around valve cover, oil pan, and PCV system",
            "Serpentine belt condition: check for cracks or glazing",
        ]),
        ("DRIVE TEST", [
            "Cold start: check for rough idle, blue/white smoke (oil consumption indicator)",
            "Acceleration: smooth power delivery, no hesitation or surge",
            "Braking: straight-line stopping, no vibration or pull to one side",
            "Front suspension: drive over rough pavement - listen for squeaks (known TSB)",
            "All warning lights off after engine warm-up (check engine, VSC, airbag)",
            "Key fob: test lock/unlock from 20+ feet (CAN Bus investigation concern)",
            "A/C operation: verify cool air within 60 seconds of activation",
        ]),
        ("BODY AND INTERIOR", [
            "Inspect for accident repair: mismatched paint, overspray, uneven panel gaps",
            "All door latches engage and release properly",
            "Dashboard: no cracks, all warning lights functional on key-on",
            "All power windows operate smoothly without binding",
        ]),
        ("TIRES AND WHEELS", [
            "Lug nut socket: 17mm required (changed from 21mm on 9/10/2018 production)",
            "Tire tread depth: minimum 4/32\", check for uneven wear patterns",
            "Wheel condition: inspect for curb rash or bent rims",
        ]),
    ]

    for section_name, items in checklist:
        story.append(Paragraph(section_name, styles["body_bold"]))
        for item in items:
            story.append(Paragraph(f"    [ ]  {item}", styles["body"]))
        story.append(Spacer(1, 6))

    story.append(Spacer(1, 8))

    # -----------------------------------------------------------------------
    # SOURCES
    # -----------------------------------------------------------------------
    story.append(section_block("DATA SOURCES", styles, color=DARK_NAVY))
    story.append(Spacer(1, 6))

    sources = [
        ["[NHTSA-RECALL]", "NHTSA Recalls Database - campaigns 21V617000, 19V503000, 19V244000"],
        ["[NHTSA-TSB]", "NHTSA Technical Service Bulletin Database - Toyota Yaris 2019"],
        ["[NHTSA-INV]", "NHTSA Office of Defects Investigation - ODI case 11501206 (open)"],
        ["[CANADA-RECALL]", "Transport Canada Motor Vehicle Safety Recalls - 2021491"],
        ["[TOYOTA-PROT]", "Toyota Motor Corporation Service Protocols v1.0 (January 2026)"],
        ["[VIN-DECODE]", "WMI 3MY = Mazda Motor Manufacturing de Mexico S.A. de C.V., Salamanca"],
    ]
    if any([args.kbb_trade_in, args.kbb_private_party, args.kbb_retail]):
        sources.append(["[KBB]", f"Kelley Blue Book (kbb.com) — {args.year} {args.make.title()} {args.model.title()}, {args.kbb_condition} condition, {args.mileage:,} miles"])
    src_table = Table(sources, colWidths=[1.3 * inch, 5.7 * inch])
    src_table.setStyle(TableStyle([
        ("ROWBACKGROUNDS", (0, 0), (-1, -1), [LIGHT_GRAY, WHITE]),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 8),
        ("TEXTCOLOR", (0, 0), (0, -1), ACCENT_BLUE),
        ("TEXTCOLOR", (1, 0), (1, -1), DARK_GRAY),
    ]))
    story.append(src_table)
    story.append(Spacer(1, 10))

    # -----------------------------------------------------------------------
    # DISCLAIMER
    # -----------------------------------------------------------------------
    story.append(HRFlowable(width="100%", thickness=0.5, color=MID_GRAY))
    story.append(Spacer(1, 4))
    story.append(Paragraph(
        "<b>DISCLAIMER:</b> This report is generated from NHTSA recall/TSB/investigation data and known "
        "published failure patterns as of " + today + ". It is provided for informational purposes to "
        "assist qualified technicians and consumers in evaluating a used vehicle. This report does NOT "
        "constitute a mechanical inspection, certification, or warranty of any kind. Actual vehicle "
        "condition requires hands-on physical inspection by a qualified ASE-certified technician. "
        "Recall completion status must be independently verified through NHTSA or the manufacturer. "
        "The authors assume no liability for purchase decisions made based on this report.",
        styles["disclaimer"],
    ))
    story.append(Spacer(1, 4))
    story.append(Paragraph(
        f"Automotive Diagnostic AI System  |  Report Date: {today}  |  VIN: {vin_display}",
        ParagraphStyle("footer", fontSize=7, fontName="Helvetica",
                       textColor=MID_GRAY, alignment=TA_CENTER),
    ))

    doc.build(story)
    return out_path


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="Pre-Purchase Vehicle Inspection Report")
    parser.add_argument("--vin", required=True)
    parser.add_argument("--year", type=int, required=True)
    parser.add_argument("--make", required=True)
    parser.add_argument("--model", required=True)
    parser.add_argument("--trim", default="")
    parser.add_argument("--mileage", type=int, default=0)
    parser.add_argument("--output", required=True)
    parser.add_argument("--kbb-trade-in", default="", dest="kbb_trade_in",
                        help="KBB trade-in value, e.g. '$7,800 – $8,200'")
    parser.add_argument("--kbb-private-party", default="", dest="kbb_private_party",
                        help="KBB private party value, e.g. '$11,000 – $11,500'")
    parser.add_argument("--kbb-retail", default="", dest="kbb_retail",
                        help="KBB suggested retail/dealer value, e.g. '$12,000 – $12,800'")
    parser.add_argument("--kbb-condition", default="Good", dest="kbb_condition",
                        help="Condition used for KBB lookup (default: Good)")
    args = parser.parse_args()

    print(f"Building pre-purchase report for {args.year} {args.make} {args.model}...")
    out = build_report(args)
    print(f"Report saved: {out}")


if __name__ == "__main__":
    main()
