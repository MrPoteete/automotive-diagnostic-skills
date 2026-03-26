# Automotive Diagnostic System

## Session Startup (Read This First)

**New session? Orient yourself in 3 steps:**

1. **Current phase & next step** → Read `memory/MEMORY.md` (auto-loaded, check `## Phase Status` and `## Next Step`)
2. **Verify baseline** → Run `.venv/bin/pytest --tb=no -q` before making any changes
3. **Understand the system** → Consult `.claude/docs/DIAGRAMS.md` for a visual overview

> **DIAGRAMS.md is the single source of truth for system structure, DB row counts, and known gaps.**
> It was ground-truthed on 2026-03-26 against live databases. Trust it over code comments or other docs.
> If you see a number elsewhere that contradicts DIAGRAMS.md, DIAGRAMS.md wins — update the other doc.

---

## ⚠️ MANDATORY: Versioning Protocol (YOLO Mode — Non-Negotiable)

**These rules apply to EVERY task. No exceptions. No shortcuts.**

### Before starting any task
1. Ensure `main` is clean — commit any pending changes first
2. Create a feature branch: `git checkout -b feature/<task-name>`
3. Confirm baseline tests pass (see test commands below)

### While working
- Work only on the feature branch — **NEVER directly on `main`**
- Commit at logical checkpoints within the branch

### After completing any task — FULL TEST GATE (must pass ALL three)
```bash
.venv/bin/pytest --tb=no -q --ignore=tests/integration   # 280 Python tests must pass
cd src/frontend && node_modules/.bin/vitest run           # Vitest tests must pass
cd src/frontend && node_modules/.bin/playwright test      # e2e tests must pass (requires servers)
```
**Do NOT merge until all three suites pass.**

### After merging to main
```bash
git tag v1.X-<feature-name>   # e.g. v1.1-recall-search
git push origin main --tags
```

### Rollback (one command)
```bash
git reset --hard v1.X-<last-good-tag>   # or git revert HEAD to preserve history
```

---

## Core Context

- **Type**: Automotive Diagnostic AI using RAG (Retrieval-Augmented Generation)
- **Purpose**: Help professional mechanics diagnose multi-make vehicles (all years supported by data)
- **User**: Professional mechanic, non-programmer
- **Safety Critical**: Incorrect diagnoses can affect vehicle safety
- **Stack**: Python 3.11+, SQLite (two DBs — see below), ChromaDB 1.5.5
- **Architecture**: See `.claude/docs/DIAGRAMS.md` (ground truth) and `.claude/docs/ARCHITECT.md`
- **AI Architecture**: Three-tier (Claude Sonnet: standard / Claude Haiku or Gemini: low-effort / Claude Opus: explicit only)

### Database Quick Reference (verified 2026-03-26)
| Database | Size | Key Contents |
|---|---|---|
| `database/automotive_complaints.db` | 843 MB PRIMARY | 562K complaints FTS5, 211K TSBs, 7,117 recalls, 5,329 investigations, 49,806 EPA vehicles, 17,774 Canada recalls |
| `database/automotive_diagnostics.db` | 1.1 MB SECONDARY | 3,073 DTC codes, 792 vehicles ⚠️ 2005 only, 48 diagnosis history |

### Before ANY import or schema change
```bash
uv run python scripts/backup_databases.py   # ALWAYS run first — verifies + rotates
```

## CRITICAL: Progressive Disclosure

**Read reference docs on demand — do NOT auto-load:**

- **Visual Architecture**: `.claude/docs/DIAGRAMS.md` (8 mermaid diagrams)
- **Architecture & Data Flow**: `.claude/docs/ARCHITECT.md`
- **Automotive Domain Rules**: `.claude/docs/DOMAIN.md` — OBD-II validation, safety, confidence scoring
- **Available Subagents**: `.claude/docs/AGENTS.md`
- **Skills Registry**: `.claude/docs/SKILLS.md`
- **Testing Protocols**: `.claude/docs/TESTING.md`
- **Data Source Standards**: `.claude/docs/DATA.md`
- **Hook Infrastructure**: `.claude/docs/HOOKS.md`
- **Gemini Delegation**: `.claude/docs/GEMINI_WORKFLOW.md`
- **Error Playbook**: `.claude/docs/LESSONS.md` — check before debugging

## Operational Standards

1. **Plan First**: Use Plan Mode (Shift+Tab x2) for non-trivial tasks
2. **Verify**: Follow `.claude/docs/TESTING.md` protocols
3. **Safety Check**: Consult `.claude/docs/DOMAIN.md` for safety-critical systems
4. **Data Integrity**: Read `.claude/docs/DATA.md` before touching data files
5. **Agent Delegation**: See `.claude/docs/AGENTS.md` for specialized subagents

## ⚡ MANDATORY: Automotive Diagnostic Requests

**When the user provides vehicle info + symptoms OR asks about DTCs/TSBs/recalls/component testing, you MUST execute this protocol — no exceptions.**

### Trigger Conditions (ANY ONE is sufficient)
- Vehicle year + make/model mentioned with symptoms
- DTC code (P/C/B/U + digits) present in conversation
- Words: diagnose, troubleshoot, what's wrong, surge, misfire, stall, noise, leak, shudder, hesitation, check engine, scan tool, live data, TSB, recall

### Required Steps (in order)
1. **Read `skills/SKILL.md`** — master protocol, routing logic, output format
2. **Read manufacturer protocol** — `skills/references/manufacturers/[make]-protocols.md`
   - Ford/Lincoln → `ford-protocols.md`
   - GM/Chevrolet/Buick/Cadillac → `gm-protocols.md`
   - Stellantis/Dodge/Jeep/Ram → `stellantis-protocols.md`
   - Toyota/Lexus → `toyota-protocols.md`
   - Honda/Acura → `honda-protocols.md`
3. **Classify request type** (Type 1–6 per SKILL.md)
4. **Output routing header** as FIRST LINE of response:
   ```
   [Request Type: X | Loading: skill.md, manufacturer-protocols.md, ...]
   ```
5. **Follow the full CO-STAR output structure** including mandatory SOURCES and DISCLAIMER sections
6. **Use categorical assessment levels only** — STRONG INDICATION / PROBABLE / POSSIBLE / INSUFFICIENT BASIS (never percentages to user)

### Shortcut
`/diagnose` slash command auto-loads all context and enforces the full protocol.

### Why This Is Non-Negotiable
The skill framework exists because incorrect automotive diagnoses affect vehicle safety. The SOURCES and DISCLAIMER sections exist because ASE technicians need to know the evidence quality behind each recommendation. Skipping the protocol means skipping safety infrastructure.

---

## Key Rules

1. **NEVER MODIFY**: `data/raw_imports/` (see `.claude/docs/DATA.md`)
2. **Validate Input**: All DTC codes via regex `^[PCBU][0-3][0-9A-F]{3}$`
3. **Safety-Critical**: Require confidence >= 0.9, explicit warnings
4. **Source Attribution**: Cite all diagnostic data (NHTSA/TSB/Forum)
5. **Ask for Clarification**: When requirements ambiguous or safety implications unclear

## Rule Evolution

**If I correct you**: Update the relevant `.claude/docs/` file immediately.

**Workflow**:
1. Identify which reference file contains the rule
2. Edit that file to add/update the rule
3. Add the error + fix to `.claude/docs/LESSONS.md`

**Examples**:
- Automotive logic error → Update `.claude/docs/DOMAIN.md` + LESSONS.md
- Testing issue → Update `.claude/docs/TESTING.md` + LESSONS.md
- Data handling mistake → Update `.claude/docs/DATA.md` + LESSONS.md
- Hook/tooling error → Update `.claude/docs/HOOKS.md` + LESSONS.md

**Treat this configuration as code**: Keep it lean, human-readable, and up-to-date.
