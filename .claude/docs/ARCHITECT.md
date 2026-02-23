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
[Forum Search] ← ChromaDB (24K StackExchange mechanics Q&A) — confidence 0.5
[Symptom Match] ← SQLite FTS5 (562K NHTSA complaints) — confidence 0.7–1.0
    ↓
merge candidates (NHTSA primary, forum fills gaps)
    ↓
Confidence Scoring (source reliability × vehicle match)
    ↓
Safety Check (brakes/airbag/steering → require ≥ 0.9, else warn)
    ↓
Trend Analysis + TSB Lookup (211K TSBs)
    ↓
Diagnostic Response {candidates, warnings, data_sources}
```

## Component Architecture

| Layer | Component | Files | Responsibility |
|-------|-----------|-------|----------------|
| **Server Layer** | RAG Dashboard | `server/rag_dashboard.py` | Web UI for diagnostic queries |
| | Home Server | `server/home_server.py` | FastAPI: `GET /`, `GET /search`, `GET /search_tsbs`, `GET /vehicles`, `POST /diagnose` |
| | Learning Loop | `server/demo_learning_loop.py` | Feedback integration |
| **Frontend API Routes** | Diagnose Proxy | `src/frontend/app/api/diagnose/route.ts` | Server-side POST proxy → `/diagnose` (adds API key) |
| | Search Proxy | `src/frontend/app/api/search/route.ts` | Server-side GET proxy → `/search` |
| | TSB Proxy | `src/frontend/app/api/search_tsbs/route.ts` | Server-side GET proxy → `/search_tsbs` |
| | Vehicles Proxy | `src/frontend/app/api/vehicles/route.ts` | Server-side GET proxy → `/vehicles` (Phase 5g) |
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
| | Diagnostics DB | `database/automotive_diagnostics.db` | 792 vehicles (DTC/failure tables empty) |
| | ChromaDB | `data/vector_store/chroma/` | 24,353 StackExchange mechanics Q&A |
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

**automotive_complaints.db** (primary diagnostic source):
- `complaints_fts` (FTS5, 562K rows) — `make, model, year, component, summary`
- `nhtsa_tsbs` (211K rows) — Technical Service Bulletins
- `tsbs_fts` (FTS5 mirror of nhtsa_tsbs)
- Note: `year` column is TEXT — always `CAST(year AS INTEGER)` when filtering

**automotive_diagnostics.db** (secondary):
- `vehicles` (792 rows) — make/model/year/engine
- DTC/failure tables exist in schema but are empty — import scripts not yet run

**ChromaDB** (`data/vector_store/chroma/`):
- Collection: `mechanics_forum` (24,353 documents)
- Embedding: `all-MiniLM-L6-v2` (ONNX, cached at `~/.cache/chroma/`)

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
├── database/              # SQLite DBs + import scripts
├── scripts/               # index_forum_data.py + utilities
├── data/
│   ├── raw_imports/       # ⚠️ NEVER MODIFY - Original sources
│   ├── vector_store/      # ChromaDB (24K forum docs)
│   └── processed/         # AI-ready documents
└── docs/                  # Project documentation
```
