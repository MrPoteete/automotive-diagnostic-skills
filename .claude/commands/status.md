---
name: status
description: "Show the current diagnostic session state — vehicle, phase, hypotheses, safety flags, data level, and confidence ceiling. Use at any point to see where you are in the diagnostic process."
category: automotive
complexity: simple
---

# /status — Diagnostic Session Status

## What This Does
Reads `logs/{session_id}/diagnostic-session.json` and outputs a formatted summary of the active diagnostic session.

## Execution

1. Read the current session state file: `logs/{session_id}/diagnostic-session.json`
2. If no session file exists, output: "No active diagnostic session. Use /diagnose to start one."
3. If session exists, format and output the following:

```
═══ DIAGNOSTIC SESSION STATUS ═══

Vehicle:  [YEAR] [MAKE] [MODEL] [ENGINE] | [MILEAGE miles] | VIN: [VIN or "not provided"]

Phase:    [N] — [Phase Name]
          Progress: Phase 1 (Info) → 2 (Safety) → 3 (System ID) → 4 (Differential) → 5 (Testing) → 6 (Recommendation) → 7 (Attribution)

Data Level:    [LEVEL]
Confidence:    [CEILING]

DTCs:     [list or "none"]
Symptoms: [list or "none"]

Safety Flags:
  [list each flag, or "None — non-critical systems"]

Hypotheses:
  ✅ Active:     [list name + assessment level]
  ❌ Eliminated: [list name + reason]

Tests Completed: [list or "none"]

Violations: [list or "none"]

Session started: [created_at]
Last updated:    [updated_at]
═════════════════════════════════
```

4. After displaying status, ask: "What would you like to do next?"
