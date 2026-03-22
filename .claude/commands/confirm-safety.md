---
name: confirm-safety
description: "Mechanic safety acknowledgment — clears the HitL safety gate after the mechanic confirms they understand the safety concerns. Use when a safety gate is blocking diagnostic progression."
category: automotive
complexity: simple
---

# /confirm-safety — Safety Acknowledgment

## What This Does

Marks the active diagnostic session's safety flags as acknowledged by the
mechanic. This clears the Human-in-the-Loop (HitL) safety gate so the
diagnostic session can progress to test procedures and recommendations.

**This does NOT remove the safety flags** — they remain in the session for
reference. It only records that the mechanic has been informed and acknowledged.

## Execution

1. Read `logs/{session_id}/diagnostic-session.json`

2. If no session or no safety flags:
```
No active safety gate to clear.
No safety flags are set in the current diagnostic session.
```

3. If safety flags exist and already acknowledged:
```
✅ Safety already acknowledged in this session.
Active flags remain on record:
  ⚠️  [flag 1]
  ⚠️  [flag 2]
```

4. If safety flags exist and NOT yet acknowledged:
   - Call `acknowledge_safety(session_id)` to set `safety_acknowledged = True`
   - Output confirmation:

```
✅ SAFETY ACKNOWLEDGMENT RECORDED

The following safety concerns have been acknowledged by the mechanic:

  ⚠️  [Flag 1]
  ⚠️  [Flag 2]
  ...

Recorded: [timestamp]
Session: Phase [N] — [Phase Name]

REMINDER: Safety flags are acknowledged, not resolved.
Physical inspection and testing are still required before clearing the vehicle.
The diagnostic analysis will now proceed to test procedures and recommendations.
```

## When to Use

Run `/confirm-safety` when:
- The safety gate is blocking diagnostic progression
- The mechanic has reviewed the safety concerns and understands the risks
- You are ready to proceed to test sequence recommendations

## Important

- Acknowledgment is session-scoped — a new diagnostic session (new vehicle or /reset-diag) starts with a fresh unacknowledged state
- Safety flags persist after acknowledgment — they appear in the session summary and final report
- If new safety keywords appear in later prompts, new flags may be added and the gate may re-engage
