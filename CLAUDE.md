# Automotive Diagnostic System

## Session Startup (Read This First)

**New session? Orient yourself in 3 steps:**

1. **Current phase & next step** → Read `memory/MEMORY.md` (auto-loaded, check `## Phase Status` and `## Next Step`)
2. **Verify baseline** → Run `.venv/bin/pytest --tb=no -q` before making any changes
3. **Understand the system** → Consult `@.claude/docs/DIAGRAMS.md` for a visual overview

> `memory/MEMORY.md` is the single source of truth for runtime-verified facts (DB schema, test counts, known bugs). Prefer it over docs that may be outdated.

---

## Core Context

- **Type**: Automotive Diagnostic AI using RAG (Retrieval-Augmented Generation)
- **Purpose**: Help professional mechanics diagnose Ford/GM/RAM vehicles (2015-2025)
- **User**: Professional mechanic, non-programmer
- **Safety Critical**: Incorrect diagnoses can affect vehicle safety
- **Stack**: Python 3.11+, SQLite (2.1M NHTSA complaints), ChromaDB
- **Architecture**: See @.claude/docs/ARCHITECT.md
- **AI Architecture**: Two-tier (Claude: strategic/safety-critical, Gemini: tactical/routine)

## CRITICAL: Progressive Disclosure

**YOU MUST consult reference docs for detailed rules:**

- **Visual Architecture**: See @.claude/docs/DIAGRAMS.md (8 mermaid diagrams for quick system understanding)
- **Architecture & Data Flow**: See @.claude/docs/ARCHITECT.md
- **Automotive Domain Rules**: See @.claude/docs/DOMAIN.md
  - OBD-II validation, safety-critical systems, confidence scoring
- **Available Subagents**: See @.claude/docs/AGENTS.md
- **Skills Registry**: See @.claude/docs/SKILLS.md
- **Testing Protocols**: See @.claude/docs/TESTING.md
- **Data Source Standards**: See @.claude/docs/DATA.md
- **Hook Infrastructure**: See @.claude/docs/HOOKS.md
- **Gemini Delegation**: See @.claude/docs/GEMINI_WORKFLOW.md
  - When to delegate to Gemini vs. keep with Claude, token optimization

## Operational Standards

1. **Plan First**: Use Plan Mode (Shift+Tab x2) for non-trivial tasks
2. **Verify**: Follow @.claude/docs/TESTING.md protocols
3. **Safety Check**: Consult @.claude/docs/DOMAIN.md for safety-critical systems
4. **Data Integrity**: Read @.claude/docs/DATA.md before touching data files
5. **Agent Delegation**: See @.claude/docs/AGENTS.md for specialized subagents

## Key Rules

1. **NEVER MODIFY**: `data/raw_imports/` (see @.claude/docs/DATA.md)
2. **Validate Input**: All DTC codes via regex `^[PCBU][0-3][0-9A-F]{3}$`
3. **Safety-Critical**: Require confidence >= 0.9, explicit warnings
4. **Source Attribution**: Cite all diagnostic data (NHTSA/TSB/Forum)
5. **Ask for Clarification**: When requirements ambiguous or safety implications unclear

## Rule Evolution

**If I correct you**: Update the relevant @.claude/docs/ file immediately.

**Workflow**:
1. Identify which reference file contains the rule
2. Edit that file to add/update the rule
3. Document the correction in the file

**Examples**:
- Automotive logic error → Update @.claude/docs/DOMAIN.md
- Testing issue → Update @.claude/docs/TESTING.md
- Data handling mistake → Update @.claude/docs/DATA.md

**Treat this configuration as code**: Keep it lean, human-readable, and up-to-date.
