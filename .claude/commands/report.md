# /report — Automotive Diagnostic Report Generator

Generates a professional, print-ready PDF diagnostic report from the current conversation.
Can be run at any point — pre-repair (assessment + recommendation) or post-repair (findings + work performed).

---

## Workflow

### Step 1 — Ask the mechanic 4 quick questions

```
To generate your report I need a few details:

1. Shop name: (which shop — yours or the other?)
2. Your name / technician name:
3. RO number: (or leave blank)
4. Report type: pre-repair (recommendation) or post-repair (work completed)?

Vehicle info and diagnostic data I'll pull from our conversation.
```

### Step 2 — Collect mileage and VIN if not already provided

If VIN and mileage were not mentioned in the conversation, ask:
```
5. Vehicle mileage:
6. VIN: (or leave blank — will show N/A)
```

### Step 3 — Build the report JSON

Construct a JSON object from the conversation and the answers above.
Use this schema exactly:

```json
{
  "shop_name": "string",
  "technician_name": "string",
  "ro_number": "string or empty",
  "date": "Month DD, YYYY",
  "report_type": "pre_repair OR post_repair",
  "vehicle": {
    "year": 2016,
    "make": "HONDA",
    "model": "CR-V",
    "vin": "string or N/A",
    "mileage": "string or N/A"
  },
  "customer_concern": "One paragraph — customer's original complaint in plain language",
  "diagnostic_tests": [
    {
      "test_name": "Static Pressure Test",
      "procedure": "Connected manifold gauges with system off, waited 10 minutes for equalization",
      "result": "High side: 110 psi / Low side: 12 psi — failed to equalize",
      "significance": "Confirmed restriction preventing refrigerant equalization between high and low sides"
    }
  ],
  "findings": "One to two paragraphs — plain language summary of what was found and why it matters",
  "diagnosis": "Short phrase — e.g. Thermostatic Expansion Valve (TXV) — stuck closed",
  "assessment_level": "STRONG INDICATION",
  "recommendations": [
    "Replace Thermostatic Expansion Valve (TXV)",
    "Replace receiver-drier (mandatory when high side opened)",
    "Evacuate system minimum 45 minutes to remove moisture",
    "Recharge to factory specification"
  ],
  "work_performed": [
    "Recovered refrigerant (EPA compliant)",
    "Replaced Thermostatic Expansion Valve (TXV)",
    "Replaced receiver-drier",
    "Evacuated system 45 minutes — verified below 500 microns",
    "Recharged to factory specification"
  ],
  "declined_services": [
    "Receiver-drier replacement — recommended due to system opening and potential moisture; customer declined"
  ],
  "verification": "AC blowing cold at all vents on delivery. Pressures within normal operating range.",
  "notes": "Any additional context for the customer"
}
```

**Rules:**
- `recommendations` = pre-repair only (what you're recommending)
- `work_performed` = post-repair only (what was actually done)
- `declined_services` = include ONLY services that were explicitly declined
- `verification` = post-repair only — how you confirmed the repair worked
- Omit empty arrays — leave as `[]` rather than removing the key
- Write `customer_concern` and `findings` in plain language a customer can understand
- Do NOT include internal confidence percentages or technical jargon in customer-facing fields

### Step 4 — Write the JSON file and run the scripts

1. Write the JSON to a temp file: `/tmp/diag_report_data.json`
2. Run the PDF generator:

```bash
uv run python scripts/generate_report.py /tmp/diag_report_data.json
```

The PDF will be saved to the NAS (`/mnt/nas-reports/Customer/`) if mounted, otherwise to `reports/Customer/` locally.
Capture the exact output path from the last line of the script output (`Report saved: <path>`).

3. Save the session file (pass the PDF path captured above).
   Add `--ingest` to also push the confirmed case into the RAG knowledge base immediately:

```bash
uv run python scripts/save_session.py /tmp/diag_report_data.json --pdf <pdf_path_from_step_2> --ingest
```

Capture the `SESSION_ID:` and `SESSION_FILE:` values from the output.

### Step 5 — Confirm output

Tell the mechanic all three outputs:

```
PDF report:   <NAS or local path>
Session ID:   <uuid>
Session file: data/sessions/<filename>.session

Open it, review, and print or send to customer.
To regenerate with changes, just say what needs updating.
To look up this case later: session ID is <first 8 chars of UUID>
```

---

## Report Types

| Type | Use When | Sections Included |
|------|----------|-------------------|
| `pre_repair` | Before work is done — get authorization | Concern, Tests, Findings, Diagnosis, **Recommendations**, Declined, Signatures |
| `post_repair` | After work is complete — leave-behind for customer | Concern, Tests, Findings, Diagnosis, **Work Performed**, Declined, Verification, Signatures |

---

## Notes

- Shop name is asked every time — the mechanic works for two different shops
- The PDF uses Chromium (already installed via Playwright) — no extra dependencies
- Reports save to `reports/` in the project directory
- The customer signature line on pre-repair reports doubles as authorization
