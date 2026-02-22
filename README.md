# Automotive Diagnostic Skills

A modular system of Claude skills for automotive fault diagnosis and
troubleshooting, powered by a comprehensive SQLite database containing **2.1 MILLION+
real-world vehicle complaints** from NHTSA plus vehicle specifications and diagnostic data.

## About

This project provides AI-powered automotive diagnostic capabilities through
Claude Code, combining structured vehicle data with intelligent reasoning to
deliver fast, accurate diagnostic recommendations.

### Key Features

- **🔥 NHTSA Complaint Database**: **2,144,604 real-world complaints** from vehicle owners (1995-2025)
- **Comprehensive Vehicle Database**: 22,800+ vehicles (2005-2025) with engine
  specifications
- **SQLite Architecture**: Sub-50ms query performance with full-text search
- **OBD-II Integration**: Diagnostic trouble code (DTC) interpretation and
  correlation
- **Failure Pattern Analysis**: Common failures with confidence ratings
- **Service Procedures**: Integration with MyFixit repair manuals
- **Technical Service Bulletins**: **211,000+ Manufacturer Communications** (2005-2025)
- **Safety-Critical Tracking**: Fire, crash, injury, and death incidents
- **Diagnostic Skill v3.1**: Progressive disclosure architecture with categorical assessment, anti-hallucination protocols, and source attribution

### Current Status

**Phase 1: Complete** - Database foundation implemented
- 33 tables with full relational integrity
- 28 optimized indexes for fast queries
- Full-text search capabilities (FTS5)

**Phase 2: Complete** - Data integration
- 18,607 vehicles loaded (2005-2025)
- 270 OBD-II diagnostic trouble codes imported
- 65 failure patterns with 1,994 vehicle links
- 2,144,604 NHTSA complaints integrated with FTS5 search
- **211,640 TSBs and Manufacturer Communications integrated**
- ChromaDB vector store with forum data (Reddit, Stack Exchange)

**Phase 3: Agent Framework & Diagnostic Engine (In Progress)**
- **Phase 3.1: Remote RAG Infrastructure (Complete)**
  - API Server: `server/home_server.py` with FastAPI & API Key
  - Data Indexing: `database/automotive_complaints.db` with FTS5
  - Connectivity: Remote access via Tailscale validated
  - Dashboard: RAG testing UI (`server/rag_dashboard.py`)
- **Phase 3.2: Client-Side Agent (Current Focus)**
  - Implementing Client Agent on Work Laptop
  - Connecting `symptom_matcher.py` to remote API

See [PROJECT_STATUS.md](docs/PROJECT_STATUS.md) for detailed roadmap.

## Technology Stack

- **Database**: SQLite 3.x (500-600 MB projected size)
- **Language**: Python 3.8+
- **AI Framework**: Claude Code (Anthropic)
- **Platform**: Windows 10/11
- **Query Performance**: <50ms for complex diagnostic queries

## Project Structure

```
automotive-diagnostic-skills/
├── .claude/                # SuperClaude agent framework (15 personas, 18 commands)
├── skills/                 # Diagnostic skill v3.1 (Claude Desktop skill architecture)
│   ├── SKILL.md                      # Main skill definition (v3.1)
│   ├── CHANGELOG_v3.1.md             # Detailed change documentation
│   ├── references/                   # Loaded by progressive disclosure routing
│   │   ├── anti-hallucination.md     # Source grounding & confidence protocols (v2.1)
│   │   └── response-framework.md    # CO-STAR persona & output templates
│   └── backups/v3.0/                # Previous version backups
├── database/               # SQLite database and import scripts
│   ├── schema.sql                    # Complete database schema (33 tables)
│   ├── schema_nhtsa_complaints.sql   # NHTSA-specific tables
│   ├── schema_nhtsa_tsbs.sql         # TSB-specific tables
│   ├── init_database_simple.py       # Database initialization
│   ├── import_vehicles.py            # Vehicle data importer
│   ├── import_dtc_codes.py           # DTC code importer
│   ├── import_failure_data.py        # Failure pattern importer
│   └── automotive_diagnostics.db     # SQLite database
├── data/
│   ├── raw_imports/                  # Original source files (never modify)
│   ├── service_manuals/              # iFixit repair procedures (JSON)
│   ├── vector_store/chroma/          # ChromaDB semantic search database
│   └── processed/                    # AI-ready processed documents
├── server/                 # RAG API Server & Dashboard
│   ├── home_server.py                # FastAPI server implementation
│   ├── rag_dashboard.py              # Streamlit testing dashboard
│   ├── data_miner.py                 # NHTSA data fetcher
│   └── start_full_system.bat         # One-click launcher
├── scripts/                # Utility and exploration scripts
│   ├── import_nhtsa_complaints.py    # NHTSA complaint importer
│   ├── import_tsbs.py                # TSB data importer
│   └── explore_complaints.py         # Interactive data explorer
├── src/                    # Application source code (in development)
├── docs/                   # Comprehensive documentation
│   ├── archive/                      # Deprecated documentation
│   ├── PROJECT_STATUS.md             # Current status and roadmap
│   ├── DATABASE_ARCHITECTURE.md      # Schema design and details
│   ├── SYSTEM_INTEGRATION_ARCHITECTURE.md  # Agent hierarchy design
│   ├── NHTSA_INTEGRATION_STRATEGY.md # 7 integration patterns
│   ├── NHTSA_QUICK_REFERENCE.md      # Copy-paste query commands
│   └── SETUP_GUIDE.md               # Installation and setup
└── README.md               # This file
```

## Quick Start

### Prerequisites

- Python 3.8 or later (includes SQLite)
- Windows 10 or later
- 2 GB free disk space

### Installation

1. Clone or download this repository:
   ```bash
   cd C:\Users\YourUsername\Documents
   git clone [repository-url] automotive-diagnostic-skills
   cd automotive-diagnostic-skills
   ```

2. Create and activate virtual environment:
   ```bash
   python -m venv .venv
   .venv\Scripts\activate
   ```

3. Create the database:
   ```bash
   cd database
   python init_database_simple.py --force
   ```

4. Import data (vehicles, DTCs, failure patterns):
   ```bash
   python import_vehicles.py
   python import_dtc_codes.py
   python import_failure_data.py
   ```

5. Verify installation:
   ```bash
   python init_database_simple.py --stats
   ```

For detailed installation instructions, see [SETUP_GUIDE.md](docs/SETUP_GUIDE.md).

## 🔥 Using the NHTSA Complaints Database (2.1M+ Records)

### Quick Start - View Your Data

**Easiest way - Run the explorer:**
```powershell
python scripts\explore_complaints.py
```

This shows you everything: top complaints, safety stats, vehicle breakdowns, and more!

### Search for a Specific Vehicle

**Find all complaints for a 2018 Ford F-150:**
```python
# Save as search_vehicle.py
import sqlite3

conn = sqlite3.connect('database/automotive_diagnostics.db')
cursor = conn.execute("""
    SELECT component_description, COUNT(*) as complaints
    FROM nhtsa_complaints
    WHERE make = 'FORD' AND model = 'F-150' AND year = 2018
    GROUP BY component_description
    ORDER BY complaints DESC
    LIMIT 10
""")

print("\nTop 10 Issues for 2018 Ford F-150:\n")
for row in cursor:
    print(f"  {row[1]:3d} complaints - {row[0]}")

conn.close()
```

### Search for Technical Service Bulletins (TSBs)

**Find TSBs for a specific issue:**
```python
# Save as search_tsbs.py
import sqlite3

conn = sqlite3.connect('database/automotive_diagnostics.db')
cursor = conn.execute("""
    SELECT year, make, model, component, summary
    FROM nhtsa_tsbs
    WHERE make = 'CHEVROLET' AND model LIKE 'SILVERADO%' AND summary LIKE '%SHUDDER%'
    LIMIT 5
""")

print("\nTop TSBs for Silverado Shudder:\n")
for row in cursor:
    print(f"  {row[0]} {row[1]} {row[2]} - {row[4][:100]}...")

conn.close()
```

### Documentation

- **📋 Quick Reference**: [docs/NHTSA_QUICK_REFERENCE.md](docs/NHTSA_QUICK_REFERENCE.md) - **START HERE!**
  - Copy/paste commands
  - Common queries
  - Usage examples

- **📚 Full Documentation**: [docs/NHTSA_COMPLAINTS_USAGE.md](docs/NHTSA_COMPLAINTS_USAGE.md)
  - Advanced queries
  - Full-text search
  - Integration patterns

### What's In The Database

- **2,144,604 complaints** from real vehicle owners
- **Decades of data** (1995-2025)
- **All manufacturers**: Ford, GM, RAM, Chevrolet, Dodge, Toyota, Honda, etc.
- **Component-level details**: Engine, brakes, transmission, airbags, etc.
- **Safety incidents**: Fires, crashes, injuries, deaths
- **Full narratives**: Searchable complaint descriptions
- **Fast queries**: Full-text search with FTS5

---

## Database Overview

### Core Tables

- **nhtsa_complaints** - 🔥 **2.1M+ real-world complaints** from vehicle owners (ACTIVE)
- **vehicles** - Vehicle configurations (make, model, year, engine)
- **dtc_codes** - OBD-II diagnostic trouble codes
- **failure_patterns** - Common failures with confidence ratings
- **parts** - Parts catalog for repairs
- **diagnostic_tests** - Step-by-step diagnostic procedures
- **service_procedures** - Repair procedures
- **tsbs** - Technical Service Bulletins
- **recalls** - NHTSA safety recalls

### Performance

- **Simple Queries**: 1-5ms (vehicle lookup)
- **Complex Queries**: 10-50ms (DTC correlation)
- **Full-Text Search**: 50-200ms (symptom search)
- **Database Size**: 500-600 MB (full dataset)

For complete schema documentation, see
[DATABASE_ARCHITECTURE.md](docs/DATABASE_ARCHITECTURE.md).

## Usage Example

```python
import sqlite3

# Connect to database
conn = sqlite3.connect('automotive_diagnostics.db')
conn.row_factory = sqlite3.Row
conn.execute("PRAGMA foreign_keys = ON")

# Find vehicles by make and model
cursor = conn.cursor()
cursor.execute("""
    SELECT year, model, engine, displacement_liters, cylinders
    FROM vehicles
    WHERE make = 'FORD' AND model = 'F-150'
    ORDER BY year DESC
""")

for row in cursor.fetchall():
    print(f"{row['year']} Ford F-150: {row['engine']}")

conn.close()
```

## Roadmap

### Phase 1: Database Foundation (Complete)
- [x] Database schema design (33 tables, 28 indexes)
- [x] Database initialization scripts
- [x] Vehicle data importer
- [x] Full-text search (FTS5) enabled

### Phase 2: Data Integration (Complete)
- [x] Import all vehicle data - 18,607 vehicles (2005-2025)
- [x] Import OBD-II diagnostic codes (270 codes)
- [x] Import common failures database (65 patterns, 1,994 vehicle links)
- [x] Import NHTSA complaints (2,144,604 records)
- [x] ChromaDB vector store with forum data
- [x] Architecture documentation (agent hierarchy, NHTSA integration strategy)

### Phase 3: Agent Framework & Diagnostic Engine (Current)
- [x] **Phase 3.1: Remote RAG Infrastructure**
    - [x] API Server (FastAPI) implementation
    - [x] RAG Dashboard (Streamlit) for testing
    - [x] Data Indexing (FTS5 + ChromaDB)
    - [x] Remote Access via Tailscale
- [ ] **Phase 3.2: Client-Side Components**
    - [ ] `symptom_matcher.py` connecting to remote API
    - [ ] Coordinator Agent logic
    - [ ] Diagnostic Skill v3.1 integration
- [ ] **Phase 3.3: Advanced Features**
    - [ ] Enhanced confidence scoring
    - [ ] Safety alert system
    - [ ] Trend analysis queries

### Phase 4: Output & Interface
- [ ] Build output formatter (mechanic reports, customer explanations)
- [ ] Web-based diagnostic interface
- [ ] Vehicle selection and symptom input

### Phase 5: Testing and Deployment
- [ ] End-to-end testing with real diagnostic scenarios
- [ ] Performance validation
- [ ] Shop PC deployment and cloud sync

## Documentation

- [Project Status](docs/PROJECT_STATUS.md) - Current status, achievements, and
  next steps
- [Database Architecture](docs/DATABASE_ARCHITECTURE.md) - Complete schema
  design and implementation details
- [System Integration Architecture](docs/SYSTEM_INTEGRATION_ARCHITECTURE.md) -
  Agent hierarchy and data flow design
- [NHTSA Integration Strategy](docs/NHTSA_INTEGRATION_STRATEGY.md) - 7
  integration patterns with code examples
- [NHTSA Quick Reference](docs/NHTSA_QUICK_REFERENCE.md) - Copy-paste
  commands for querying complaints
- [Setup Guide](docs/SETUP_GUIDE.md) - Installation, configuration, and
  troubleshooting
- [Skill v3.1 Changelog](skills/CHANGELOG_v3.1.md) - Diagnostic skill
  changes and improvements

## Architecture Decision: SQLite vs JSON

Initially considered JSON-based storage, but analysis revealed:

- **Scale**: 1,142 vehicles for 2005 alone = 22,840 vehicles over 20 years
- **Performance**: JSON requires scanning ~500 files per query (2-5 seconds)
- **SQLite**: Indexed queries complete in <50ms (60x faster)

**Hybrid Approach**:
- SQLite for vehicle data, DTCs, failures (structured queries)
- JSON retained for service manuals (already optimized)

## Contributing

This project is developed by MrPoteete for use in automotive repair shops.

### Development Principles

This project follows professional software engineering practices:

- **KISS**: Keep solutions simple and maintainable
- **DRY**: Avoid code duplication
- **SOLID**: Modular, testable architecture
- **Security by Design**: Input validation, parameterized queries
- **Documentation**: Comprehensive inline and API documentation

See [.claude/CLAUDE.md](.claude/CLAUDE.md) for complete development directives.

## License

Proprietary - For use in automotive repair shop operations.

## Acknowledgments

- Claude Code (Anthropic) for AI-powered diagnostic capabilities
- SQLite for robust, embedded database functionality
- Python community for excellent database tools