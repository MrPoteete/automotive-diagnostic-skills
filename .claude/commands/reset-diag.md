---
name: reset-diag
description: "Clear the current diagnostic session state and start fresh from Phase 1. Use when switching to a different vehicle or starting a new repair order."
category: automotive
complexity: simple
---

# /reset-diag — Reset Diagnostic Session

## What This Does
Clears the active `diagnostic-session.json` file, resetting the session to Phase 1 with a blank vehicle profile and no hypotheses. Use when switching vehicles or starting a new repair order.

## Execution

1. Read `logs/{session_id}/diagnostic-session.json` to check if an active session exists.

2. If an active session exists with vehicle info populated, confirm before clearing:

```
⚠️  RESET DIAGNOSTIC SESSION

Current session:
  Vehicle: [YEAR MAKE MODEL or "unidentified"]
  Phase: [N] — [Phase Name]
  Active hypotheses: [count]

Resetting will clear all session data including hypotheses and test results.

Type "CONFIRM RESET" to proceed, or press Enter to cancel.
```

3. On confirmation (or if session is empty), delete the `diagnostic-session.json` file and output:

```
✅ Diagnostic session reset.

Session state cleared. Ready to start a new diagnostic.
Use /diagnose [vehicle info] [symptoms] to begin.
```

4. If no session exists, output: "No active session to reset. Use /diagnose to start one."

## Note
This clears the session state file only. Audit logs (`prompts.json`) are preserved.
