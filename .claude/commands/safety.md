---
name: safety
description: "Force-output the safety assessment for the current diagnostic session. Shows safety flags, critical systems involved, and whether it is safe to operate the vehicle during diagnosis."
category: automotive
complexity: simple
---

# /safety — Safety Assessment Output

## What This Does
Reads the active session's safety flags from `diagnostic-session.json` and outputs a formatted safety assessment — regardless of what phase the session is in.

## Execution

1. Read `logs/{session_id}/diagnostic-session.json`
2. If no session file exists, output the default safety prompt and exit:

```
No active diagnostic session.
To assess safety, start with /diagnose and provide vehicle + symptoms.
```

3. If session exists, evaluate the `safety_flags` field:

### If safety_flags is EMPTY:
```
🚨 SAFETY ASSESSMENT

Status: Non-critical systems involved.
Safe to operate during diagnosis — no immediate safety risks identified.

Note: Safety assessment updates automatically as more information is provided.
Use /diagnose to continue the diagnostic session.
```

### If safety_flags is NON-EMPTY:
```
🚨 SAFETY ASSESSMENT — CRITICAL SYSTEMS INVOLVED

⚠️  [Flag 1]
⚠️  [Flag 2]
...

RECOMMENDATION: Do NOT operate vehicle until hands-on inspection confirms safe condition.
Diagnostic analysis will proceed, but physical inspection is required before driving.

Vehicle: [YEAR MAKE MODEL or "unidentified — provide vehicle info"]
```

4. Always end with the vehicle identification status and confidence ceiling reminder.
