# Automotive Diagnostic Skills - Project Status

**Last Updated**: February 22, 2026
**Project Phase**: Phase 5c — Integration Testing / UI Polish
**Overall Status**: On Track

---

## Executive Summary

The system is functionally complete end-to-end. A RAG diagnostic engine queries
562K NHTSA complaints and 24K forum posts, scores candidates by confidence,
enforces safety thresholds, and serves results via a FastAPI REST API. A
cyberpunk-styled Next.js UI connects to that API and renders ranked diagnostic
candidates with confidence bars and safety warnings. 300 unit + integration tests
pass. The next step is smoke-testing the full stack and polishing UX.

---

## Phase Status

| Phase | Description | Status | Date |
|-------|-------------|--------|------|
| 1 | Database Foundation | ✅ Complete | Nov 2025 |
| 2 | Data Integration | ✅ Complete | Nov 2025 |
| 3 | Diagnostic Engine | ✅ Complete | Feb 22, 2026 |
| 4 | ChromaDB Forum Integration | ✅ Complete | Feb 22, 2026 |
| 5a | Backend REST API | ✅ Complete | Feb 22, 2026 |
| 5b | Frontend Wiring | ✅ Complete | Feb 22, 2026 |
| 5c | Integration Testing / Polish | 🔄 Current | — |

---

## Completed Phases

### Phase 1–2: Data Foundation (COMPLETE)

- **SQLite** (`database/automotive_complaints.db`):
  - `complaints_fts` (FTS5): 562K NHTSA complaints
  - `nhtsa_tsbs` / `tsbs_fts`: 211K Technical Service Bulletins
  - `year` column is TEXT — always `CAST(year AS INTEGER)` when filtering
- **SQLite** (`database/automotive_diagnostics.db`):
  - `vehicles`: 792 rows (make/model/year/engine)
  - DTC/failure tables: schema exists, data not yet imported
- **ChromaDB** (`data/vector_store/chroma/`):
  - `mechanics_forum` collection: 24,353 StackExchange Q&A docs (2015–2025)
  - Embedding model: `all-MiniLM-L6-v2` (ONNX, cached at `~/.cache/chroma/`)

### Phase 3: Diagnostic Engine (COMPLETE)

Core Python modules in `src/`:

| File | Responsibility |
|------|---------------|
| `src/data/db_service.py` | DiagnosticDB wrapper (FTS5 queries) |
| `src/diagnostic/symptom_matcher.py` | Symptom → NHTSA component mapping |
| `src/diagnostic/confidence_scorer.py` | Source reliability × vehicle match |
| `src/diagnostic/engine_agent.py` | Orchestrator — `diagnose()` entry point |
| `src/safety/alert_system.py` | Two-layer safety alert detection |
| `src/analysis/trend_analyzer.py` | Year-over-year trend analysis |

**Key API**:
```python
from src.diagnostic.engine_agent import diagnose
result = diagnose(
    vehicle={'make': 'FORD', 'model': 'F-150', 'year': 2019},
    symptoms='engine shaking at idle, misfire',
    dtc_codes=['P0300', 'P0301']
)
# Returns: {vehicle, symptoms, dtc_codes, candidates[], warnings[], data_sources}
```

### Phase 4: ChromaDB Forum Integration (COMPLETE)

- `src/data/chroma_service.py` — semantic forum search, boosts candidates with forum signal
- Forum data re-indexed from `data/raw_imports/` StackExchange JSON files
- ChromaDB 1.0.x (Rust backend) — incompatible with pre-1.0 schemas; wipe + rebuild if corrupted:
  ```bash
  find data/vector_store/chroma -type f -delete
  python scripts/index_forum_data.py
  ```

### Phase 5a: Backend REST API (COMPLETE)

- `server/home_server.py` — FastAPI server on port 8000
- Endpoints: `GET /`, `GET /search`, `GET /search_tsbs`, `POST /diagnose`
- Auth: `X-API-KEY` header (dev key: `mechanic-secret-key-123`)
- CORS: localhost:3000 only
- Live tested: 10 candidates returned for Ford F-150 misfire query

### Phase 5b: Frontend Wiring (COMPLETE)

- `src/frontend/app/api/diagnose/route.ts` — POST proxy (SSRF protection, server-side API key injection)
- `src/frontend/lib/api.ts` — `DiagnoseRequest/Response` types, `diagnose()` method, `formatDiagnosis()` renderer
- `src/frontend/app/page.tsx` — `parseVehicleInput()` parser; `handleSend` routes to `POST /diagnose`
  when year + make are detected; falls back to FTS search for unstructured queries

**Input routing**:
- `"2018 Ford F-150 engine shaking"` → `POST /diagnose` with `{vehicle, symptoms}`
- `"TSB Chevy Silverado"` → GET `/search_tsbs` fallback
- `"P0300 misfire"` (no make/year) → GET `/search` fallback

---

## Test Suite

| Suite | Count | Type |
|-------|-------|------|
| `tests/unit/test_confidence_scorer.py` | 74 | Unit (mocked) |
| `tests/unit/test_alert_system.py` | 55 | Unit (mocked) |
| `tests/unit/test_engine_agent.py` | 51 | Unit (mocked) |
| `tests/unit/test_symptom_matcher.py` | 36 | Unit (mocked) |
| `tests/unit/test_trend_analyzer.py` | ~33 | Unit (mocked) |
| `tests/unit/test_chroma_service.py` | 31 | Unit (mocked) |
| `tests/integration/test_engine_agent.py` | 20 | Integration (real DB) |
| **Total** | **300** | **All passing** |

Run: `.venv/bin/pytest --tb=no -q`

---

## Phase 5c: Current Work

### Pre-requisites
Create `src/frontend/.env.local`:
```
API_KEY=mechanic-secret-key-123
BACKEND_URL=http://localhost:8000
```

### Startup
```bash
# Terminal 1 — backend
cd server && python home_server.py

# Terminal 2 — frontend
cd src/frontend && npm run dev
```

### Smoke Test
1. Open http://localhost:3000
2. Type: `2018 Ford F-150 engine shaking`
3. Expected: ranked candidates with confidence bars and safety warnings

### Optional Improvements
- Structured vehicle form (year/make/model dropdowns) for better input UX
- Loading indicator per-candidate vs. full response
- Pagination for large result sets

---

## Technology Stack

| Layer | Technology |
|-------|-----------|
| Database | SQLite 3.x with FTS5 |
| Vector Search | ChromaDB 1.0.x (Rust backend) |
| Embeddings | all-MiniLM-L6-v2 (ONNX) |
| Backend | Python 3.11+, FastAPI, uvicorn |
| Frontend | Next.js 14, TypeScript, Tailwind CSS |
| Testing | pytest, 300 tests |
| Platform | WSL2 Ubuntu 24.04 |

---

## Known Issues / Discrepancies

1. `fire_flag`, `crash_flag`, `num_injuries`, `num_deaths` in `schema.sql` but **not** in the running DB
2. `automotive_diagnostics.db` DTC/failure tables are empty (import scripts exist but not run)
3. NHTSA complaint dataset is partial (562K, not 2.1M) — full import pending
4. Frontend `.env.local` must be created manually before first run (not committed to git)

---

**Status Summary**: Core system complete (Phases 1–5b). 300 tests passing.
Next: smoke test the full stack end-to-end.
