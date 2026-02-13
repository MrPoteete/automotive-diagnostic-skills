# System Architecture

## Overview
Automotive Diagnostic AI System using RAG (Retrieval-Augmented Generation)
- **User**: Professional mechanics (non-programmers)
- **Safety Critical**: Incorrect diagnoses affect vehicle safety
- **Stack**: Python 3.11+, SQLite, ChromaDB, FastAPI

## RAG Pipeline Flow

```
User Query
    ↓
Router Skill (classifies problem type: P/C/B/U codes)
    ↓
[Vector DB Search] ← ChromaDB (Reddit, Stack Exchange forum data)
[SQL Search] ← SQLite (2.1M NHTSA complaints, 211K TSBs, 18K vehicles)
    ↓
Specialized Skill (Engine/Transmission/Electrical/Chassis)
    ↓
Confidence Scoring (Source reliability + Vehicle match)
    ↓
Diagnostic Response (with source attribution)
```

## Component Architecture

| Layer | Component | Files | Responsibility |
|-------|-----------|-------|----------------|
| **Server Layer** | RAG Dashboard | `server/rag_dashboard.py` | Web UI for diagnostic queries |
| | Home Server | `server/home_server.py` | FastAPI backend |
| | Learning Loop | `server/demo_learning_loop.py` | Feedback integration |
| **Skills Layer** | Router | `skills/router_skill/` | Classifies DTC codes by system |
| | Engine | `skills/engine_skill/` | Powertrain diagnostics (P-codes) |
| | Transmission | `skills/transmission_skill/` | Transmission diagnostics |
| | Electrical | `skills/electrical_skill/` | Electrical system diagnostics |
| | Chassis | `skills/chassis_skill/` | Chassis/brake diagnostics (C-codes) |
| **Data Layer** | SQLite DB | `database/automotive_diagnostics.db` | Structured data (500KB) |
| | ChromaDB | `data/vector_store/chroma/` | Vector embeddings |
| | Raw Imports | `data/raw_imports/` | **NEVER MODIFY** - Original sources |

## Data Flow: Query to Response

1. **Input**: Mechanic submits vehicle info + symptoms/DTC code
2. **Classification**: Router skill identifies system (P/C/B/U)
3. **Retrieval**:
   - Vector search: Semantic similarity in ChromaDB
   - SQL search: Exact matches in NHTSA complaints/TSBs
4. **Ranking**: Confidence scoring (source reliability × vehicle match)
5. **Response**: Specialized skill generates diagnostic guidance

## Database Schema (33 tables)

**Core Tables**:
- `vehicles` (18,607 records) - Make/model/year/engine configurations
- `nhtsa_complaints` (2,144,604 records) - Real-world failure reports
- `nhtsa_tsbs` (211,640 records) - Technical Service Bulletins
- `dtc_codes` (270 records) - OBD-II diagnostic trouble codes
- `failure_patterns` (65 records) - Common failures with confidence ratings

See `docs/DATABASE_ARCHITECTURE.md` for complete schema.

## Project Structure

```
automotive-diagnostic-skills/
├── .claude/               # Configuration & subagents
├── skills/                # Diagnostic skills (v3.1)
├── server/                # FastAPI servers
├── database/              # SQLite DB + import scripts
├── data/
│   ├── raw_imports/       # ⚠️ NEVER MODIFY - Original sources
│   ├── service_manuals/   # iFixit JSON data
│   ├── vector_store/      # ChromaDB
│   └── processed/         # AI-ready documents
├── scripts/               # Utility scripts
└── docs/                  # Project documentation
```
