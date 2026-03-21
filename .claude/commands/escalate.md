---
name: escalate
description: "Mark the current diagnostic session as requiring human expert review. Use when 3+ hypotheses have been eliminated without resolution, when safety-critical systems are involved with unidentified vehicle, or when the case exceeds remote diagnostic capability."
category: automotive
complexity: simple
---

# /escalate — Escalate Diagnostic Session

## What This Does
Marks the active session as requiring hands-on expert review and outputs a structured escalation summary. The session state is preserved — escalation does not reset it.

## Execution

1. Read `logs/{session_id}/diagnostic-session.json`

2. Build the escalation summary and output it:

```
🚨 ESCALATION SUMMARY
══════════════════════════════════════════════

Vehicle: [YEAR MAKE MODEL ENGINE or "UNIDENTIFIED — vehicle info required"]
Session Phase: [N] — [Phase Name]
Data Level: [LEVEL]

ESCALATION REASON(S):
[Auto-detect from state and list applicable reasons:]

  □ Safety-critical system involved with unidentified vehicle
    → System: [safety_flags list]
    → Action: Identify vehicle before remote diagnosis

  □ [N] hypotheses eliminated without confirmed root cause
    → Eliminated: [list hypothesis names + reasons]
    → Action: Hands-on inspection required; remote analysis exhausted

  □ Data level too low for confident diagnosis
    → Current level: [LEVEL] (ceiling: [CEILING])
    → Action: Perform scan tool analysis and provide freeze frame data

  □ Manual escalation requested
    → Action: Consult senior technician or OEM technical assistance

ACTIVE HYPOTHESES REMAINING: [count]
  [list each active hypothesis with assessment level]

RECOMMENDED NEXT STEPS:
1. [Context-appropriate step based on escalation reason]
2. Contact OEM technical assistance if applicable
3. Consult labor information system (Mitchell/AllData) for known patterns

⚖️ DISCLAIMER: This AI-assisted analysis has reached the limits of remote
diagnosis. Hands-on inspection by a qualified technician is required.
══════════════════════════════════════════════
```

3. Write `"escalated": true` to the session state file.

4. If no session exists, output:
```
No active diagnostic session to escalate.
Use /diagnose to start a diagnostic session first.
```
