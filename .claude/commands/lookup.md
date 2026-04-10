---
name: lookup
description: "Look up past diagnostic sessions by VIN, repair order, vehicle, or show recent cases. Returns session summary, diagnosis, assessment level, and PDF location."
category: automotive
complexity: simple
---

# /lookup — Diagnostic Session Lookup

Find any previously saved diagnostic session. Works by VIN, RO number, make/model, or shows recent cases.

## Usage

The mechanic can say any of:
- "look up VIN WBA3D5C52FK291262"
- "find RO 1234"
- "what did we do on that BMW 328"
- "show recent cases"
- "list all sessions"

## Execution

Run the appropriate lookup command based on what the mechanic provided:

### By VIN
```bash
uv run python scripts/lookup_session.py --vin <VIN>
```

### By RO number
```bash
uv run python scripts/lookup_session.py --ro <RO_NUMBER>
```

### By vehicle make/model/year
```bash
uv run python scripts/lookup_session.py --make <MAKE> --model <MODEL> --year <YEAR>
```
(--model and --year are optional filters)

### Recent sessions
```bash
uv run python scripts/lookup_session.py --recent 10
```

### All sessions (summary list)
```bash
uv run python scripts/lookup_session.py --list
```

## Output Format

The script returns session details including:
- Vehicle, VIN, mileage
- Date and RO number
- Customer symptoms
- Confirmed diagnosis and assessment level
- Phase (REPORT_GENERATED = fully closed case)
- Session ID (for reference)
- PDF path on NAS or local

## If No Sessions Found

```
No sessions found in data/sessions/
```

In that case, all diagnostic data is in conversation history or the Claude memory files.
The session system populates automatically each time /report is run going forward.
