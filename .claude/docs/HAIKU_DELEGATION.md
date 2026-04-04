# Haiku Delegation Workflow

**Purpose**: Define when Claude delegates to Haiku vs. handles tasks directly

> **Replaces**: GEMINI_WORKFLOW.md (Google AI Pro subscription discontinued 2026-04-04)
> **Low-effort tier**: `claude-haiku-4-5-20251001` (~25x cheaper than Sonnet)

---

## Philosophy

**Haiku = Junior Developer** (Tactical Execution)
- Routine code generation
- Documentation writing
- Simple refactoring
- Boilerplate implementation
- Content extraction from scraped markdown (Firecrawl pipeline)

**Claude Sonnet = Senior Developer** (Strategic Planning)
- Safety-critical validation
- Architecture decisions
- Complex debugging
- Security reviews
- Confidence scoring

**Claude Opus = Expert** (Explicit Only)
- Only when user explicitly requests it
- Never auto-delegated

---

## Delegation Matrix

### DELEGATE TO HAIKU

| Task Type | Example |
|-----------|---------|
| Simple functions | Parse DTC code format |
| Boilerplate | CRUD operations, endpoint stubs |
| Documentation | Docstrings, API docs, README sections |
| Basic tests | Unit tests for utils |
| Code cleanup | Remove dead code, rename variables |
| Simple refactoring | Extract repeated logic |
| Firecrawl extraction | Extract structured data from scraped markdown |
| Content summarization | Summarize forum posts, TSB PDFs |

### KEEP WITH CLAUDE SONNET

| Task Type | Reason |
|-----------|--------|
| Safety-critical code | Brakes, airbags, steering — confidence >= 0.9 required |
| Confidence scoring | Source reliability assessment is critical |
| Database schema | Long-term architectural impact |
| API design | System-wide implications |
| Security implementation | Input validation, auth, secrets |
| Complex debugging | Multi-system failures, race conditions |
| Root cause analysis | Deep reasoning required |
| Diagnostic reasoning | Final mechanic output must be Sonnet quality |

---

## Model Reference

| Model | ID | Use Case |
|-------|----|----------|
| Claude Haiku | `claude-haiku-4-5-20251001` | Low-effort tactical work |
| Claude Sonnet | `claude-sonnet-4-6` | Standard work (default) |
| Claude Opus | `claude-opus-4-6` | Explicit request only |

---

## Firecrawl → Haiku Extraction Pipeline

When Firecrawl returns scraped markdown from TSB portals, NHTSA pages, or forums:

```
Firecrawl (raw HTML → markdown)
    ↓
haiku_extractor.py (Haiku inference)
    ↓
Structured output: {vehicles, symptoms, procedure, source_url}
    ↓
ChromaDB / SQLite storage
```

Haiku handles the extraction because:
- Firecrawl output is noisy (nav, ads, boilerplate) — cheap model can strip it
- Volume: many pages per session — Sonnet would be expensive
- No safety-critical decisions are made at extraction time

---

## Delegation Decision Tree

1. Is it safety-critical (brakes/steering/airbag)? → **Sonnet only**
2. Is it architectural? → **Sonnet**
3. Is it security-related? → **Sonnet**
4. Is it complex debugging? → **Sonnet**
5. Is it Firecrawl content extraction? → **Haiku** via `haiku_extractor.py`
6. Is it docs/boilerplate/simple functions? → **Haiku** via Agent tool (haiku model)
7. Unsure? → **Sonnet** (err on side of caution)

---

## Acknowledging Delegation in Code

Add a comment when implementing directly:

```python
# Checked AGENTS.md - implementing directly because [reason]
# Checked HAIKU_DELEGATION.md - Sonnet handles this (safety-critical)
```

---

## Token Savings Strategy

| Role | Token Usage | % of Total |
|------|-------------|------------|
| Claude Sonnet (Strategic) | ~40% | Safety, architecture, complex work |
| Claude Haiku (Tactical) | ~60% | Docs, boilerplate, content extraction |

**Target**: Haiku handles all bulk/repetitive inference; Sonnet focuses on quality decisions.
