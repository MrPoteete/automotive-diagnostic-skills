# Automotive Diagnostic AI

AI-powered diagnostic assistant for professional mechanics. Combines 2.1M+ real-world NHTSA complaints, 211K TSBs, safety recalls, and mechanic forum data with a structured 7-phase ASE diagnostic methodology to deliver evidence-based, safety-first diagnostic guidance.

Built for shop-floor use: works through a web UI, CLI, or Telegram.

---

## What It Does

A mechanic provides vehicle info + symptoms. The system:

1. Pulls matching complaints, TSBs, and recalls from the NHTSA database
2. Searches 553K mechanic forum posts (Reddit + Stack Exchange) for matching cases
3. Scores each candidate cause by source reliability × vehicle match
4. Flags safety-critical systems (brakes, airbags, steering) automatically
5. Returns a ranked differential diagnosis with categorical assessment levels, test sequence, and mandatory source attribution

Outputs include a web dashboard, customer-facing PDF reports, pre-purchase inspection checklists, and fleet trend reports.

---

## System Architecture

```
Mechanic → Web UI (Next.js + Carbon)
                ↓
         FastAPI Backend
          ↓           ↓
    ┌───────────────────────┐   ┌───────────────┐
    │   Diagnostic Engine   │   │ Firecrawl     │
    │  engine_agent.diagnose()│   │ (Web Scraper) │
    └───────────────────────┘   └───────────────┘
          ↙         ↘
  SQLite (FTS5)   ChromaDB
  562K complaints  553K forum docs
  211K TSBs        (Reddit + SE)
  2,711 recalls
          ↘         ↙
    Confidence Scoring
    Safety Alert System
    Trend Analyzer
          ↓
    Diagnostic Response
    (candidates + recalls + warnings)
```

### Two-Tier AI
- **Claude** — strategic decisions, safety-critical logic, architecture
- **Gemini** — routine code generation, docs, batch processing

---

## Data Sources

| Source | Records | Confidence |
|--------|---------|------------|
| NHTSA Complaints (FTS5) | 562,000 | 0.7–1.0 |
| NHTSA TSBs | 211,640 | 0.7–0.9 |
| NHTSA Recalls | 2,711 campaigns | 0.9 |
| Transport Canada Recalls | 17,774 | 0.9 |
| EPA Vehicle Specs | 49,806 configs | — |
| OBD-II DTC Codes | 3,071 codes | — |
| Reddit (r/MechanicAdvice + r/AskMechanics) | 539,277 docs | 0.5 |
| mechanics.StackExchange | 14,683 Q&As | 0.5 |

---

## Technology Stack

| Layer | Technology |
|-------|-----------|
| Language | Python 3.11+ |
| Package manager | `uv` |
| Backend API | FastAPI (port 8000) |
| Frontend | Next.js 14, TypeScript, IBM Carbon Design System |
| Primary DB | SQLite (FTS5) — `automotive_complaints.db` (830MB) |
| Secondary DB | SQLite — `automotive_diagnostics.db` |
| Web Scraping | Firecrawl (Docker Compose, Node.js, Playwright) |
| Vector Store | ChromaDB 1.0.x (Rust backend) |
| Embeddings | `all-MiniLM-L6-v2` (ONNX) |
| Environment | WSL2 Ubuntu 24.04 |

---

## Project Structure

```
automotive-diagnostic-skills/
├── .claude/                    # AI harness + dev tooling
│   ├── commands/               # 25 slash commands (/diagnose, /report, /status, etc.)
│   ├── hooks/                  # Quality enforcement hooks
│   │   ├── user_prompt_submit.py   # Diagnostic detection + phase-sliced injection
│   │   ├── utils/
│   │   │   ├── session_state.py    # Persistent JSON session tracking
│   │   │   ├── phase_context.py    # Phase→references map (ASE 7-phase)
│   │   │   ├── safety_scanner.py   # 13 safety keyword patterns + HitL gate
│   │   │   └── diagnostic_validator.py  # 5 protocol invariants
│   │   └── validators/
│   │       ├── ruff_validator.py
│   │       ├── mypy_validator.py
│   │       └── diagnostic_report_validator.py
│   └── docs/                   # Internal reference (ARCHITECT, DOMAIN, AGENTS, etc.)
│
├── skills/                     # Diagnostic skill v3.1
│   ├── SKILL.md                # Master protocol (7-phase ASE methodology)
│   └── references/             # Progressive disclosure refs
│       ├── diagnostic-process.md
│       ├── anti-hallucination.md
│       ├── obd-ii-methodology.md
│       ├── warranty-failures.md
│       └── manufacturers/      # Brand-specific protocols (Ford, GM, Toyota, etc.)
│
├── server/
│   └── home_server.py          # FastAPI: /diagnose, /search, /search_tsbs,
│                               #   /vehicle/dashboard, /vehicle/recalls,
│                               #   /vehicle/tsbs, /vehicle/complaints,
│                               #   /vehicle/report, /vehicle/checklist,
│                               #   /history, /vin/decode
│
├── src/
│   ├── diagnostic/
│   │   ├── engine_agent.py     # diagnose() orchestrator
│   │   ├── symptom_matcher.py  # Symptom → FTS5 complaint search
│   │   └── confidence_scorer.py
│   ├── safety/
│   │   └── alert_system.py     # Two-layer safety detection
│   ├── analysis/
│   │   └── trend_analyzer.py   # YoY complaint trend
│   ├── data/
│   │   ├── db_service.py       # DiagnosticDB wrapper
│   │   └── chroma_service.py   # Forum semantic search
│   └── frontend/               # Next.js app
│       ├── app/
│       │   ├── page.tsx        # Main diagnostic flow (vehicle → symptoms → diagnose)
│       │   ├── components/     # Carbon UI components
│       │   │   ├── VehicleIdentification.tsx  (VIN decode + manual selection)
│       │   │   ├── VehicleDashboard.tsx       (complaints, TSBs, recalls)
│       │   │   ├── DiagnosisHistory.tsx        (prior sessions panel)
│       │   │   ├── RecallDrillDown.tsx
│       │   │   ├── TsbDrillDown.tsx
│       │   │   └── ChecklistPanel.tsx         (pre-purchase inspection)
│       │   └── api/            # Server-side proxies (add API key)
│       └── tests/e2e/          # Playwright tests (55 tests)
│
├── scripts/
│   ├── report_builder.py       # Fleet trend report (MD) — NAS-routed
│   ├── generate_report.py      # Customer diagnostic PDF — NAS-routed
│   ├── generate_checklist.py   # Pre-purchase checklist (MD/HTML/PDF)
│   ├── batch_report.py         # Multi-vehicle batch reports
│   ├── nas_output.py           # Central NAS path resolver
│   └── pdf_from_html.js        # HTML→PDF via Node.js Playwright
│
├── database/                   # SQLite DBs + import scripts
│   ├── automotive_complaints.db    # PRIMARY (830MB): complaints, TSBs, recalls
│   └── automotive_diagnostics.db  # SECONDARY: vehicles, DTCs, diagnosis_history
│
├── data/
│   ├── raw_imports/            # ⚠️ IMMUTABLE — original source files
│   └── vector_store/chroma/    # ChromaDB (553K docs)
│
├── tests/
│   ├── unit/                   # 280 Python unit tests
│   └── integration/            # 20 integration tests (real DB)
│
└── reports/                    # Example outputs (fleet reports, sample PDFs)
```

---

## Quick Start

### Prerequisites

- WSL2 Ubuntu 24.04
- Python 3.11+ and `uv`
- Node.js 18+ and `npm`
- 10 GB free disk space minimum (databases not included in repo; yt-dlp transcript ingestion requires substantially more — the NAS Ubuntu VM runs a 300 GB disk for this purpose)

### Setup

```bash
# Clone and install
git clone git@github.com:MrPoteete/automotive-diagnostic-skills.git
cd automotive-diagnostic-skills
bash setup.sh          # Creates .venv, installs Python + Node deps

# Verify
.venv/bin/pytest --tb=no -q --ignore=tests/integration   # 280 tests
cd src/frontend && node_modules/.bin/vitest run           # 142 tests
```

### Run

```bash
# Backend (port 8000)
uv run python server/home_server.py

# Frontend (port 3000)
cd src/frontend && npm run dev

# Open http://localhost:3000
```

> Full shop setup: see [SHOP_SETUP.md](SHOP_SETUP.md)

---

## Using the Diagnostic Web UI

1. **Identify vehicle** — enter VIN (auto-decodes via NHTSA vPIC) or select make/model/year manually
2. **Review dashboard** — complaint count, TSB count, top failure systems, active recalls
3. **Enter symptoms** — free text + optional DTC codes
4. **Run Diagnostic** — returns ranked differential, test sequence, source citations
5. **Generate report** — customer-facing PDF or fleet trend report

### Navigation tabs

| Tab | What it shows |
|-----|--------------|
| Diagnose | Vehicle selection + diagnostic flow |
| Database | NHTSA complaint search |
| TSB Search | Technical service bulletin lookup |
| Recall Search | Keyword recall search |
| Pre-Purchase | Inspection checklist generator |

---

## Diagnostic Skill v3.1

The `/diagnose` command enforces a full structured diagnostic session:

- **7-phase ASE methodology**: Information Gathering → Safety → System ID → Differential → Test Sequence → Recommendation → Sources
- **Categorical assessment only**: STRONG INDICATION / PROBABLE / POSSIBLE / INSUFFICIENT BASIS (no percentages to user)
- **Mandatory sections**: `🚨 SAFETY`, `📋 DATA ASSESSMENT`, `📚 SOURCES`, `⚖️ DISCLAIMER`
- **Manufacturer protocols**: Brand-specific procedures for Ford, GM, Stellantis, Toyota, Honda, Nissan, VW/Audi, BMW, Mercedes, Subaru, Hyundai/Kia
- **Progressive disclosure**: Only loads reference files relevant to the current phase (40–60% token savings)

---

## AI Harness (v1.8+)

The harness wraps every diagnostic conversation with automated quality enforcement:

| Component | What it does |
|-----------|-------------|
| `user_prompt_submit.py` | Detects diagnostic prompts, injects phase-aware context, writes session state |
| `session_state.py` | Persistent JSON per session: vehicle, phase, DTCs, symptoms, hypotheses, safety flags |
| `phase_context.py` | Maps ASE phase 1–7 → minimal reference file set (phase-sliced injection) |
| `safety_scanner.py` | 13 regex patterns → auto-populates `safety_flags`; HitL gate until `/confirm-safety` |
| `diagnostic_validator.py` | 5 invariants: vehicle-phase coherence, safety gate, hypothesis coverage, required sections, assessment level |
| `diagnostic_report_validator.py` | PostToolUse hook: blocks `.md` writes that fail content invariants |

---

## Reports

Three report types, all NAS-routed (`/mnt/z/` when available, `reports/` fallback):

| Report | Script | Output | Route |
|--------|--------|--------|-------|
| Customer diagnostic PDF | `generate_report.py` | PDF | `Customer/` |
| Fleet trend report | `report_builder.py` | Markdown | `Fleet/` |
| Pre-purchase checklist | `generate_checklist.py` | MD/HTML/PDF | `Pre-Purchase/` |

Generate a fleet report:
```bash
.venv/bin/python3 scripts/report_builder.py \
    --make FORD --model F-150 --year-start 2018 --year-end 2022
```

---

## Test Suite

```bash
# Python unit tests (fast — ~8s)
.venv/bin/pytest --tb=no -q --ignore=tests/integration

# Python integration tests (slow — ~2 min, uses real DB)
.venv/bin/pytest --tb=no -q tests/integration/

# Frontend unit tests (Vitest)
cd src/frontend && node_modules/.bin/vitest run

# e2e tests (Playwright — requires both servers running)
cd src/frontend && node_modules/.bin/playwright test
```

| Suite | Count | Notes |
|-------|-------|-------|
| Python unit | 280 | Fully mocked |
| Python integration | 20 | Real SQLite DB |
| Vitest (frontend) | 142 | React components + API handlers |
| Playwright (e2e) | 55 | Full browser, requires servers |

---

## Key Rules

- `data/raw_imports/` is **immutable** — never modify source files
- `reports/Customer/`, `reports/Fleet/`, `reports/Pre-Purchase/` are gitignored (NAS fallback output)
- Safety-critical diagnoses require confidence ≥ 0.9
- DTC pattern: `^[PCBU][0-3][0-9A-F]{3}$`
- Recalls use `year_from`/`year_to` range fields — never exact year match

---

## License

Proprietary — for use in automotive repair shop operations.
