---
name: pre-purchase
description: "Pre-purchase vehicle inspection report — queries NHTSA recalls/TSBs/complaints from DB, fetches KBB market values online, and generates a professional PDF saved to NAS."
category: automotive
complexity: standard
---

# /pre-purchase — Pre-Purchase Vehicle Inspection Report

## Usage
```
/pre-purchase [VIN or year/make/model] [mileage] [optional: condition good/fair/excellent]
```

Examples:
```
/pre-purchase 3MYDLBYV6KY507371 70000
/pre-purchase 2019 Toyota Yaris 70000 good
/pre-purchase 2016 Honda CR-V 85000 fair
```

---

## MANDATORY Protocol — Execute in Order

### Step 1 — Collect Vehicle Info

If not fully provided, ask for:
1. **VIN** (preferred) or Year / Make / Model / Trim
2. **Mileage**
3. **Condition** (Excellent / Good / Fair) — default: Good

If VIN provided, decode it:
```bash
curl -s "https://vpic.nhtsa.dot.gov/api/vehicles/decodevin/[VIN]?format=json" | \
  python3 -c "import sys,json; d=json.load(sys.stdin)['Results']; \
  [print(r['Variable'],':',r['Value']) for r in d if r['Value'] and r['Value'] not in ('null','Not Applicable','')]"
```

### Step 2 — Query the Database

Run these queries to pull all relevant safety and reliability data:

```bash
python3 << 'EOF'
import sqlite3, json
from pathlib import Path

DB = Path("database/automotive_complaints.db")
conn = sqlite3.connect(DB)
cur = conn.cursor()

MAKE = "TOYOTA"   # REPLACE
MODEL = "YARIS"   # REPLACE
YEAR = 2019       # REPLACE

# Recalls
cur.execute("""
    SELECT campaign_no, report_date, component, summary, consequence, remedy, park_it
    FROM nhtsa_recalls
    WHERE UPPER(make) = UPPER(?) AND UPPER(model) LIKE UPPER(?)
      AND year_from <= ? AND year_to >= ?
    ORDER BY report_date DESC
""", (MAKE, f"%{MODEL}%", YEAR, YEAR))
recalls = cur.fetchall()
print(f"RECALLS ({len(recalls)}):")
for r in recalls:
    print(f"  [{r[0]}] {r[2]} | PARK-IT: {r[6]} | {str(r[3])[:120]}")

# TSBs
cur.execute("""
    SELECT bulletin_date, component, summary FROM nhtsa_tsbs
    WHERE UPPER(make) = UPPER(?) AND UPPER(model) LIKE UPPER(?)
      AND CAST(year AS INTEGER) = ?
    ORDER BY bulletin_date DESC
""", (MAKE, f"%{MODEL}%", YEAR))
tsbs = cur.fetchall()
print(f"\nTSBs ({len(tsbs)}):")
for t in tsbs[:10]:
    print(f"  {t[0]} | {t[1]} | {str(t[2])[:100]}")

# Investigations
cur.execute("""
    SELECT inv_type, component, summary, status, open_date FROM nhtsa_investigations
    WHERE UPPER(make) = UPPER(?) AND UPPER(model) LIKE UPPER(?)
      AND CAST(year_from AS INTEGER) <= ?
      AND (year_to IS NULL OR CAST(year_to AS INTEGER) >= ?)
    ORDER BY open_date DESC
""", (MAKE, f"%{MODEL}%", YEAR, YEAR))
invs = cur.fetchall()
print(f"\nINVESTIGATIONS ({len(invs)}):")
for i in invs:
    print(f"  [{i[3]}] {i[1]} | {str(i[2])[:100]}")

# Top complaints
cur.execute("""
    SELECT component, COUNT(*) as cnt FROM complaints_fts
    WHERE make = UPPER(?) AND model LIKE UPPER(?) AND CAST(year AS INTEGER) = ?
    GROUP BY component ORDER BY cnt DESC LIMIT 8
""", (MAKE, f"%{MODEL}%", YEAR))
comps = cur.fetchall()
print(f"\nTOP COMPLAINT COMPONENTS:")
for c in comps:
    print(f"  {c[0]}: {c[1]} complaints")

conn.close()
EOF
```

### Step 3 — Fetch KBB Values Online

Use the `research-agent` (Agent tool) to look up current KBB values:

**Prompt:**
> Look up the current Kelley Blue Book value for a [YEAR] [MAKE] [MODEL] [TRIM if known] in [CONDITION] condition with [MILEAGE] miles. I need three figures: trade-in value, private party sale value, and dealer retail/suggested retail. Search kbb.com, Edmunds, or CarGurus. Return specific dollar ranges.

### Step 4 — Generate the PDF

```bash
uv run python scripts/pre_purchase_report.py \
  --vin "[VIN]" \
  --year [YEAR] \
  --make "[MAKE]" \
  --model "[MODEL]" \
  --trim "[TRIM or empty]" \
  --mileage [MILEAGE] \
  --kbb-trade-in "[e.g. \$7,800 – \$8,200]" \
  --kbb-private-party "[e.g. \$11,000 – \$11,500]" \
  --kbb-retail "[e.g. \$12,000 – \$12,800]" \
  --kbb-condition "[Good]" \
  --output "/mnt/nas-reports/Pre-Purchase/pre_purchase_[YEAR]_[MAKE]_[MODEL]_[VIN].pdf"
```

If KBB values could not be retrieved (network issue), omit the `--kbb-*` flags — the section will be skipped cleanly.

### Step 5 — Confirm Output

Report the exact path to the user:
```
Report saved: /mnt/nas-reports/Pre-Purchase/pre_purchase_2019_TOYOTA_YARIS_3MYDLBYV6KY507371.pdf

Sections included:
  ✓ Vehicle summary + Risk score
  ✓ KBB Market Values (Good condition, 70,000 miles)
  ✓ NHTSA Recalls (N found)
  ✓ NHTSA Investigations
  ✓ Technical Service Bulletins (N found)
  ✓ Known Issues + Inspection Focus
  ✓ Pre-Purchase Checklist
  ✓ Data Sources + Disclaimer
```

---

## Output Filename Convention

```
pre_purchase_[YEAR]_[MAKE]_[MODEL]_[VIN_LAST8].pdf
```

Example: `pre_purchase_2019_TOYOTA_YARIS_KY507371.pdf`

Save to: `/mnt/nas-reports/Pre-Purchase/`

---

## Risk Score Legend

| Score | Meaning |
|-------|---------|
| MINIMAL | No recalls, no open investigations |
| LOW | Minor/admin recalls only |
| MODERATE | Safety recalls present or open investigation |
| HIGH | Park-it recall or safety-critical open recall unresolved |

---

## Notes

- The report script (`scripts/pre_purchase_report.py`) pulls recalls, TSBs, investigations, and complaints live from `database/automotive_complaints.db`
- KBB values are fetched online at time of report generation and embedded in the PDF
- If `/mnt/nas-reports` is not mounted, save to `reports/` in the project directory and tell the user
- The report is designed to be printed and handed to the customer or kept on file
