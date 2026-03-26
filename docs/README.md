# docs/ — Reference Index

> **Agents: do NOT load files from this directory speculatively.**
> For system architecture, DB schemas, row counts, and known gaps — go directly to:
> **`.claude/docs/DIAGRAMS.md`** (ground truth, verified 2026-03-26)

---

## Active Reference Docs (load on demand)

| File | What it covers | Load when |
|---|---|---|
| [SETUP_GUIDE.md](SETUP_GUIDE.md) | Full dev environment setup | Setting up a new machine |
| [ENVIRONMENT_SETUP.md](ENVIRONMENT_SETUP.md) | Quick environment reference | Environment questions |
| [NHTSA_COMPLAINTS_USAGE.md](NHTSA_COMPLAINTS_USAGE.md) | NHTSA query patterns + FTS5 tips | Writing DB queries |
| [NHTSA_QUICK_REFERENCE.md](NHTSA_QUICK_REFERENCE.md) | NHTSA data field reference | NHTSA data questions |
| [GEMINI_MCP_SETUP.md](GEMINI_MCP_SETUP.md) | Gemini MCP configuration | Gemini delegation setup |
| [GEMINI_QUICK_REFERENCE.md](GEMINI_QUICK_REFERENCE.md) | Gemini delegation quick ref | Delegation decisions |
| [CORS_SECURITY_VALIDATION.md](CORS_SECURITY_VALIDATION.md) | CORS security implementation | Touching API/middleware |
| [CORS_TESTING_GUIDE.md](CORS_TESTING_GUIDE.md) | CORS testing procedures | Testing API access |
| [CYBERPUNK_UI_DESIGN.md](CYBERPUNK_UI_DESIGN.md) | UI design system spec | Frontend UI work |
| [UI_VALIDATION_CRITERIA.md](UI_VALIDATION_CRITERIA.md) | UI acceptance criteria | Frontend testing |

---

## Archived (do not load — preserved for history only)

- `archive/stale-architecture-2025/` — architecture docs superseded by `.claude/docs/DIAGRAMS.md`
- `archive/historical-2025-2026/` — session summaries, import logs, one-off reports
- `archive/root-docs-2025/` — pre-2026 project docs
- `archive/` — other archived files

---

## Where to find things

| Need | Go to |
|---|---|
| System architecture diagrams | `.claude/docs/DIAGRAMS.md` |
| DB schema + exact row counts | `.claude/docs/DIAGRAMS.md` → Diagram 2 |
| Known gaps and bugs | `.claude/docs/DIAGRAMS.md` → Diagram 5, or `memory/cells/known_issues.yaml` |
| Automotive diagnostic rules | `.claude/docs/DOMAIN.md` |
| Testing protocols | `.claude/docs/TESTING.md` |
| Available agents | `.claude/docs/AGENTS.md` |
| Data import rules | `.claude/docs/DATA.md` |
| Error playbook | `.claude/docs/LESSONS.md` |
