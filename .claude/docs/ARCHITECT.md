# System Architecture

## Overview
Automotive Diagnostic AI System using RAG (Retrieval-Augmented Generation)
- **User**: Professional mechanics (non-programmers)
- **Safety Critical**: Incorrect diagnoses affect vehicle safety
- **Stack**: Python 3.11+, SQLite, ChromaDB, FastAPI

## RAG Pipeline Flow

```
User Query (vehicle + symptoms + optional DTC codes)
    ↓
engine_agent.diagnose()
    ↓
[Forum Search] ← ChromaDB (553,960 docs: Reddit + mechanics.SE) — confidence 0.5
[Symptom Match] ← SQLite FTS5 (562K NHTSA complaints) — confidence 0.7–1.0
[Recall Lookup] ← SQLite nhtsa_recalls (2,711 campaigns) — confidence 0.9
    ↓
merge candidates (NHTSA primary, forum fills gaps)
    ↓
Confidence Scoring (source reliability × vehicle match)
    ↓
Safety Check (brakes/airbag/steering → require ≥ 0.9, else warn)
Park-It Recalls → top-level WARNINGS
    ↓
Trend Analysis + TSB Lookup (211K TSBs)
    ↓
Diagnostic Response {candidates, recalls, warnings, data_sources}
```

## Component Architecture

| Layer | Component | Files | Responsibility |
|-------|-----------|-------|----------------|
| **Server Layer** | RAG Dashboard | `server/rag_dashboard.py` | Web UI for diagnostic queries |
| | Home Server | `server/home_server.py` | FastAPI: `GET /`, `GET /search`, `GET /search_tsbs`, `GET /vehicles`, `POST /diagnose`, `GET /vehicle/dashboard`, `GET /vehicle/recalls`, `GET /vehicle/tsbs`, `GET /vehicle/complaints` |
| | Learning Loop | `server/demo_learning_loop.py` | Feedback integration |
| **Frontend API Routes** | Diagnose Proxy | `src/frontend/app/api/diagnose/route.ts` | Server-side POST proxy → `/diagnose` (adds API key) |
| | Search Proxy | `src/frontend/app/api/search/route.ts` | Server-side GET proxy → `/search` |
| | TSB Proxy | `src/frontend/app/api/search_tsbs/route.ts` | Server-side GET proxy → `/search_tsbs` |
| | Vehicles Proxy | `src/frontend/app/api/vehicles/route.ts` | Server-side GET proxy → `/vehicles` |
| | VIN Proxy | `src/frontend/app/api/vin/route.ts` | Server-side GET proxy → `/vin/decode` (NHTSA vPIC) |
| | Dashboard Proxy | `src/frontend/app/api/vehicle/dashboard/route.ts` | Server-side GET proxy → `/vehicle/dashboard` |
| | Recalls Proxy | `src/frontend/app/api/vehicle/recalls/route.ts` | Server-side GET proxy → `/vehicle/recalls` |
| | Report Proxy | `src/frontend/app/api/vehicle/report/route.ts` | Server-side POST proxy → `/vehicle/report` |
| | History Proxy | `src/frontend/app/api/history/route.ts` | Server-side GET+POST proxy → `/history` |
| **Skills Layer** | Router | `skills/router_skill/` | Classifies DTC codes by system |
| | Engine | `skills/engine_skill/` | Powertrain diagnostics (P-codes) |
| | Transmission | `skills/transmission_skill/` | Transmission diagnostics |
| | Electrical | `skills/electrical_skill/` | Electrical system diagnostics |
| | Chassis | `skills/chassis_skill/` | Chassis/brake diagnostics (C-codes) |
| **Diagnostic Engine** (Phase 3) | Engine Agent | `src/diagnostic/engine_agent.py` | Orchestrator — `diagnose()` entry point |
| | Symptom Matcher | `src/diagnostic/symptom_matcher.py` | Maps symptoms → NHTSA complaint components |
| | Confidence Scorer | `src/diagnostic/confidence_scorer.py` | Source reliability × vehicle match |
| | Alert System | `src/safety/alert_system.py` | Safety-critical component detection |
| | Trend Analyzer | `src/analysis/trend_analyzer.py` | Year-over-year complaint trends |
| | DB Service | `src/data/db_service.py` | DiagnosticDB wrapper (FTS5 queries) |
| | Chroma Service | `src/data/chroma_service.py` | Forum semantic search (Phase 4) |
| **Data Layer** | Complaints DB | `database/automotive_complaints.db` | 562K NHTSA complaints, 211K TSBs (FTS5) |
| | Diagnostics DB | `database/automotive_diagnostics.db` | 792 vehicles, 3,071 DTC codes, diagnosis_history |
| | ChromaDB | `data/vector_store/chroma/` | 539,277 docs (r/MechanicAdvice + r/AskMechanics) |
| | Raw Imports | `data/raw_imports/` | **NEVER MODIFY** - Original sources |

## Data Flow: Query to Response

1. **Input**: Mechanic submits vehicle info + symptoms/DTC code
2. **Classification**: Router skill identifies system (P/C/B/U)
3. **Retrieval**:
   - Vector search: Semantic similarity in ChromaDB
   - SQL search: Exact matches in NHTSA complaints/TSBs
4. **Ranking**: Confidence scoring (source reliability × vehicle match)
5. **Response**: Specialized skill generates diagnostic guidance

## Database Schema (Runtime-Verified)

**automotive_complaints.db** (843 MB — primary diagnostic source):
- `complaints_fts` (FTS5, **562,667 rows**) — `make, model, year, component, summary`
- `processed_complaints` (**1,564,487 rows**) — raw NHTSA flat file source
- `nhtsa_tsbs` (**211,640 rows**) — Technical Service Bulletins
- `tsbs_fts` (FTS5 mirror of nhtsa_tsbs)
- `nhtsa_recalls` (**7,117 rows**, last import 2026-03-22) — NHTSA recall campaigns; `UNIQUE(campaign_no, make, model)`; `year_from/year_to` range fields; `park_it` flag for park-it safety recalls; 43 makes, years 2000–2025
- `nhtsa_investigations` (**5,329 rows**) — NHTSA investigations
- `canada_recalls` (**17,774 rows**) — Transport Canada recalls
- `epa_vehicles` (**49,806 rows**, 1984–2026, 44 makes) — EPA fuel economy / vehicle specs
- `recalls_fts` (FTS5 mirror of nhtsa_recalls)
- Note: `year` column is TEXT in complaints/tsbs — always `CAST(year AS INTEGER)` when filtering; recalls use `year_from`/`year_to` INTEGER range fields

**automotive_diagnostics.db** (1.1 MB — secondary):
- `vehicles` (**792 rows, 2005 ONLY — KNOWN GAP**) — should be ~49K rows 1984–2026; fix with `scripts/import_epa_vehicles.py --full`
- `dtc_codes` (**3,073 rows**) — OBD-II codes with severity, safety_critical, system, subsystem
- `diagnosis_history` (**48 rows**) — one row per diagnosis session (vin, year, make, model, symptoms, findings, dtc_codes JSON, candidate_count, has_warnings)
- `failure_patterns` (**0 rows — KNOWN GAP**) — schema exists, never populated
- Other junction tables (vehicle_failures, vehicle_recalls, vehicle_tsbs) exist but are empty pending failure_patterns population

**ChromaDB** (`data/vector_store/chroma/`):
- Collection: `mechanics_forum` — **rebuilding after 2026-03 disk crash**; HNSW index was corrupted, SQLite intact; new content being added via `bulk_ingest.py`
- Embedding: `all-MiniLM-L6-v2` (ONNX, cached at `~/.cache/chroma/`)
- chromadb version: **1.5.5** (updated 2026-03-26; DB schema migration version 10)

See `memory/MEMORY.md` for runtime-verified facts and known discrepancies.

## Project Structure

```
automotive-diagnostic-skills/
├── .claude/               # Configuration & docs
│   └── docs/              # ARCHITECT, DOMAIN, AGENTS, TESTING, DATA, HOOKS, GEMINI_WORKFLOW
├── skills/                # Diagnostic skills (v3.1)
├── server/                # FastAPI servers
├── src/                   # Diagnostic engine (Phase 3+)
│   ├── diagnostic/        # engine_agent, symptom_matcher, confidence_scorer
│   ├── safety/            # alert_system
│   ├── analysis/          # trend_analyzer
│   └── data/              # db_service, chroma_service
├── tests/
│   ├── unit/              # 280 unit tests (fully mocked)
│   └── integration/       # 20 integration tests (real DB)
│   # Python total: 300 | Frontend (Vitest in src/frontend/): 100 tests
├── database/              # SQLite DBs + import scripts
├── scripts/               # index_forum_data.py + utilities
├── data/
│   ├── raw_imports/       # ⚠️ NEVER MODIFY - Original sources
│   ├── vector_store/      # ChromaDB (553K forum docs: Reddit + mechanics.SE)
│   └── processed/         # AI-ready documents
└── docs/                  # Project documentation
```
