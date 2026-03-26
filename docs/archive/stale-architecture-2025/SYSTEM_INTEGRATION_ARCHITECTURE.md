> ⚠️ **DEPRECATED — DO NOT USE FOR CURRENT SYSTEM STATE**
> This document has stale data and was archived on 2026-03-26.
> For accurate architecture, DB schemas, and row counts, use:
> **`.claude/docs/DIAGRAMS.md`** (ground truth)

---

# Automotive Diagnostic System - Complete Integration Architecture

**Status**: Integration Planning Phase
**Date**: November 8, 2025
**Objective**: Unify all data sources, tools, and AI agents into a cohesive diagnostic system

---

## 📊 Current System Inventory

### 1. **SQLite Relational Database** (PRIMARY STRUCTURED DATA)
**Location**: `database/automotive_diagnostics.db`
**Size**: ~500-800MB

**Contents**:
- ✅ **18,607 vehicles** (2005-2025) - Make/Model/Year/Engine
- ✅ **65 failure patterns** with vehicle links (1,994 links)
- ✅ **270 DTC codes** (SAE J2012 generic codes) with intelligent classification
- ✅ **2,144,604 NHTSA complaints** - Real-world failure data (1995-2025)
  - Full-text search enabled (FTS5)
  - Component-level details
  - Safety-critical tracking (fires, crashes, injuries, deaths)
  - Searchable complaint narratives

**Performance**: <50ms queries, full-text search 50-200ms

---

### 2. **Vector Database** (SEMANTIC SEARCH)
**Technology**: ChromaDB (mentioned by user, not yet visible in repo)
**Purpose**: Forum data semantic search

**Contents** (based on user description):
- Reddit automotive community data
- Mechanic Stack Exchange discussions
- Real-world diagnostic conversations
- Community-sourced solutions

**Use Case**: Match customer symptoms to similar forum discussions

---

### 3. **Service Manual Data** (REPAIR PROCEDURES)
**Location**: `data/service_manuals/`
**Format**: JSON
**Source**: iFixit MyFixit Dataset

**Contents**:
- 1,135 repair procedure manuals
- 107 Ford/GM/RAM specific procedures
- Step-by-step instructions with images
- Tool requirements and torque specs

---

### 4. **Web Scrapers** (DATA COLLECTION)
**Status**: Created but not visible in repo
**Sources**:
- Reddit automotive communities
- Mechanic Stack Exchange
- (Potentially) Technical Service Bulletins
- (Potentially) Manufacturer forums

**Purpose**: Continuously update knowledge base with real-world cases

---

### 5. **SuperClaude Agent Framework** (AI ORCHESTRATION)
**Location**: `.claude/`

**Available Agents** (15 personas):
- System Architect
- Backend Architect
- Frontend Architect
- Python Expert
- Quality Engineer
- Security Engineer
- DevOps Architect
- Performance Engineer
- Root Cause Analyst
- Requirements Analyst
- Refactoring Expert
- Technical Writer
- Learning Guide
- Socratic Mentor
- Business Panel Experts

**Available Commands** (18 slash commands):
- `/analyze`, `/build`, `/implement`, `/design`, `/improve`
- `/troubleshoot`, `/explain`, `/cleanup`, `/test`
- `/document`, `/estimate`, `/task`, `/git`
- `/index`, `/load`, `/spawn`, `/workflow`
- `/brainstorm`, `/reflect`, `/save`, `/select-tool`

---

## 🎯 Proposed Integration Architecture

### **Layer 1: Data Foundation** (EXISTING)

```
┌─────────────────────────────────────────────────────────────┐
│                    DATA LAYER                               │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌──────────────────┐  ┌──────────────────┐               │
│  │  SQLite Database │  │  ChromaDB Vector │               │
│  │  (Structured)    │  │  (Unstructured)  │               │
│  ├──────────────────┤  ├──────────────────┤               │
│  │ • Vehicles       │  │ • Reddit forums  │               │
│  │ • DTC codes      │  │ • Stack Exchange │               │
│  │ • Failures       │  │ • Community Q&A  │               │
│  │ • NHTSA (2.1M)   │  │ • Real cases     │               │
│  │ • Correlations   │  │ • Symptom match  │               │
│  └──────────────────┘  └──────────────────┘               │
│           ↕                     ↕                          │
│  ┌──────────────────────────────────────────┐              │
│  │      Service Manuals (JSON)              │              │
│  │  • iFixit repair procedures              │              │
│  │  • 1,135 manuals                         │              │
│  └──────────────────────────────────────────┘              │
└─────────────────────────────────────────────────────────────┘
```

---

### **Layer 2: Integration Services** (TO BUILD)

```
┌─────────────────────────────────────────────────────────────┐
│              INTEGRATION SERVICES LAYER                     │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌─────────────────────────────────────────────────────┐   │
│  │  Data Access Layer (src/data/)                      │   │
│  ├─────────────────────────────────────────────────────┤   │
│  │  • SQLiteService      - Structured queries          │   │
│  │  • ChromaDBService    - Semantic search             │   │
│  │  • ManualService      - Repair procedures           │   │
│  │  • NHTSAService       - Complaint integration       │   │
│  └─────────────────────────────────────────────────────┘   │
│           ↓                                                 │
│  ┌─────────────────────────────────────────────────────┐   │
│  │  Correlation Engine (src/diagnostic/)               │   │
│  ├─────────────────────────────────────────────────────┤   │
│  │  • DTC → Failure correlations                       │   │
│  │  │  Layer 1: Expert rules (85-95% confidence)       │   │
│  │  │  Layer 2: Subsystem matching (70-85%)            │   │
│  │  │  Layer 3: Keyword overlap (50-70%)               │   │
│  │  │                                                   │   │
│  │  • Symptom → Forum matching (ChromaDB)              │   │
│  │  • Vehicle → NHTSA complaint frequency              │   │
│  │  • Component → Safety alert checking                │   │
│  └─────────────────────────────────────────────────────┘   │
│           ↓                                                 │
│  ┌─────────────────────────────────────────────────────┐   │
│  │  Enhanced Confidence Scoring                        │   │
│  ├─────────────────────────────────────────────────────┤   │
│  │  Base factors:                                      │   │
│  │  • DTC match                                        │   │
│  │  • Failure pattern match                            │   │
│  │  • Vehicle specificity                              │   │
│  │                                                      │   │
│  │  NHTSA boost:                                       │   │
│  │  • 100+ complaints: +15%                            │   │
│  │  • 50-100: +10%                                     │   │
│  │  • 10-50: +5%                                       │   │
│  │  • Safety-critical: +5%                             │   │
│  │                                                      │   │
│  │  Forum boost:                                       │   │
│  │  • High similarity match: +10%                      │   │
│  │  • Multiple matches: +5%                            │   │
│  └─────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
```

---

### **Layer 3: AI Agent Hierarchy** (ORCHESTRATION)

```
┌──────────────────────────────────────────────────────────────────┐
│                    AGENT ORCHESTRATION LAYER                     │
├──────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │  MASTER DIAGNOSTIC COORDINATOR                             │ │
│  │  (Root Agent - Orchestrates all sub-agents)                │ │
│  └────────────────────────────────────────────────────────────┘ │
│                           ↓                                      │
│  ┌──────────────────┬──────────────────┬──────────────────┐    │
│  │   Input Agent    │  Analysis Agent  │  Output Agent    │    │
│  │  (Router)        │  (Diagnostic)    │  (Formatter)     │    │
│  └──────────────────┴──────────────────┴──────────────────┘    │
│                                                                  │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │  Level 1: INPUT ROUTER AGENT                               │ │
│  ├────────────────────────────────────────────────────────────┤ │
│  │  Responsibilities:                                         │ │
│  │  • Parse customer symptoms                                 │ │
│  │  │  ├─ Extract key terms                                   │ │
│  │  │  └─ Normalize descriptions                              │ │
│  │  │                                                          │ │
│  │  • Validate DTC codes                                      │ │
│  │  │  ├─ Format validation (regex)                           │ │
│  │  │  ├─ Code family identification (P/C/B/U)                │ │
│  │  │  └─ SQLite lookup for code details                      │ │
│  │  │                                                          │ │
│  │  • Classify problem domain                                 │ │
│  │  │  ├─ Engine/Powertrain                                   │ │
│  │  │  ├─ Transmission                                        │ │
│  │  │  ├─ Electrical/Network                                  │ │
│  │  │  ├─ Chassis/Suspension                                  │ │
│  │  │  └─ Body/HVAC                                           │ │
│  │  │                                                          │ │
│  │  • Route to specialized diagnostic agent                   │ │
│  │                                                             │ │
│  │  Tools Used:                                               │ │
│  │  • SQLiteService → DTC validation                          │ │
│  │  • NLP term extraction                                     │ │
│  └────────────────────────────────────────────────────────────┘ │
│                           ↓                                      │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │  Level 2: SPECIALIZED DIAGNOSTIC AGENTS                    │ │
│  ├────────────────────────────────────────────────────────────┤ │
│  │  (One agent per major domain)                              │ │
│  │                                                             │ │
│  │  ┌──────────────────────────────────────────────────────┐  │ │
│  │  │  ENGINE DIAGNOSTIC AGENT                             │  │ │
│  │  ├──────────────────────────────────────────────────────┤  │ │
│  │  │  Persona: Python Expert + Backend Architect          │  │ │
│  │  │                                                       │  │ │
│  │  │  Sub-agents:                                         │  │ │
│  │  │  ├─ Misfire Specialist                               │  │ │
│  │  │  ├─ Timing/Cam Phaser Specialist                     │  │ │
│  │  │  ├─ Fuel System Specialist                           │  │ │
│  │  │  └─ Emissions Specialist                             │  │ │
│  │  │                                                       │  │ │
│  │  │  Workflow:                                           │  │ │
│  │  │  1. Query SQLite for DTC-failure correlations       │  │ │
│  │  │  2. Check NHTSA for complaint frequency             │  │ │
│  │  │  3. Search ChromaDB for similar forum cases         │  │ │
│  │  │  4. Run safety-critical checks                      │  │ │
│  │  │  5. Calculate enhanced confidence scores            │  │ │
│  │  │  6. Generate differential diagnosis (top 5)         │  │ │
│  │  │  7. Provide testing sequence                        │  │ │
│  │  └──────────────────────────────────────────────────────┘  │ │
│  │                                                             │ │
│  │  ┌──────────────────────────────────────────────────────┐  │ │
│  │  │  TRANSMISSION DIAGNOSTIC AGENT                       │  │ │
│  │  ├──────────────────────────────────────────────────────┤  │ │
│  │  │  Persona: System Architect + Root Cause Analyst      │  │ │
│  │  │                                                       │  │ │
│  │  │  Sub-agents:                                         │  │ │
│  │  │  ├─ Shift Quality Specialist                         │  │ │
│  │  │  ├─ Torque Converter Specialist                      │  │ │
│  │  │  ├─ Solenoid/Valve Body Specialist                   │  │ │
│  │  │  └─ CVT Specialist (Nissan focus)                    │  │ │
│  │  │                                                       │  │ │
│  │  │  (Same workflow as Engine agent)                     │  │ │
│  │  └──────────────────────────────────────────────────────┘  │ │
│  │                                                             │ │
│  │  ┌──────────────────────────────────────────────────────┐  │ │
│  │  │  ELECTRICAL/NETWORK DIAGNOSTIC AGENT                 │  │ │
│  │  ├──────────────────────────────────────────────────────┤  │ │
│  │  │  Persona: Backend Architect + Security Engineer      │  │ │
│  │  │                                                       │  │ │
│  │  │  Sub-agents:                                         │  │ │
│  │  │  ├─ CAN Bus Specialist (U-codes)                     │  │ │
│  │  │  ├─ Module Communication Specialist                  │  │ │
│  │  │  ├─ TIPM Specialist (RAM critical)                   │  │ │
│  │  │  └─ BCM/PCM Specialist                               │  │ │
│  │  │                                                       │  │ │
│  │  │  (Same workflow as Engine agent)                     │  │ │
│  │  └──────────────────────────────────────────────────────┘  │ │
│  │                                                             │ │
│  │  [Additional agents for Chassis, Body, HVAC, etc.]         │ │
│  └────────────────────────────────────────────────────────────┘ │
│                           ↓                                      │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │  Level 3: SUPPORT AGENTS                                   │ │
│  ├────────────────────────────────────────────────────────────┤ │
│  │                                                             │ │
│  │  ┌────────────────────────────────────────────┐            │ │
│  │  │  SAFETY VERIFICATION AGENT                 │            │ │
│  │  │  Persona: Security Engineer               │            │ │
│  │  │  • Check for safety-critical components   │            │ │
│  │  │  • Query NHTSA for fire/crash history     │            │ │
│  │  │  • Flag recalls                            │            │ │
│  │  │  • Generate safety alerts                  │            │ │
│  │  └────────────────────────────────────────────┘            │ │
│  │                                                             │ │
│  │  ┌────────────────────────────────────────────┐            │ │
│  │  │  FORUM CONTEXT AGENT                       │            │ │
│  │  │  Persona: Learning Guide                   │            │ │
│  │  │  • Search ChromaDB for similar cases       │            │ │
│  │  │  • Extract community solutions             │            │ │
│  │  │  • Provide "mechanics have seen this"     │            │ │
│  │  └────────────────────────────────────────────┘            │ │
│  │                                                             │ │
│  │  ┌────────────────────────────────────────────┐            │ │
│  │  │  TREND ANALYSIS AGENT                      │            │ │
│  │  │  Persona: Performance Engineer            │            │ │
│  │  │  • Analyze NHTSA trends by year           │            │ │
│  │  │  • Identify increasing/decreasing issues  │            │ │
│  │  │  • Compare to similar vehicles             │            │ │
│  │  └────────────────────────────────────────────┘            │ │
│  │                                                             │ │
│  │  ┌────────────────────────────────────────────┐            │ │
│  │  │  TESTING SEQUENCE GENERATOR                │            │ │
│  │  │  Persona: Quality Engineer                │            │ │
│  │  │  • Generate step-by-step tests             │            │ │
│  │  │  • Provide expected results                │            │ │
│  │  │  • Tool requirements                       │            │ │
│  │  └────────────────────────────────────────────┘            │ │
│  └────────────────────────────────────────────────────────────┘ │
│                           ↓                                      │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │  Level 4: OUTPUT FORMATTER AGENT                           │ │
│  ├────────────────────────────────────────────────────────────┤ │
│  │  Persona: Technical Writer                                 │ │
│  │                                                             │ │
│  │  Outputs:                                                  │ │
│  │  ┌──────────────────────────────────────────────────────┐  │ │
│  │  │  1. DIAGNOSTIC REPORT (Mechanic Version)             │  │ │
│  │  │  ────────────────────────────────────────             │  │ │
│  │  │  • Differential diagnosis ranked by confidence       │  │ │
│  │  │  • Data source attribution (NHTSA, forums, TSBs)     │  │ │
│  │  │  • Safety alerts                                     │  │ │
│  │  │  • Testing sequence                                  │  │ │
│  │  │  • Similar NHTSA complaint stats                     │  │ │
│  │  │  • Forum discussion links                            │  │ │
│  │  │  • Trend analysis (getting worse/better?)            │  │ │
│  │  └──────────────────────────────────────────────────────┘  │ │
│  │                                                             │ │
│  │  ┌──────────────────────────────────────────────────────┐  │ │
│  │  │  2. CUSTOMER EXPLANATION (Simple Version)            │  │ │
│  │  │  ────────────────────────────────────────             │  │ │
│  │  │  • Plain English description                         │  │ │
│  │  │  • What likely caused it                             │  │ │
│  │  │  • Safety concerns (if any)                          │  │ │
│  │  │  • Next steps                                        │  │ │
│  │  └──────────────────────────────────────────────────────┘  │ │
│  │                                                             │ │
│  │  ┌──────────────────────────────────────────────────────┐  │ │
│  │  │  3. REPAIR GUIDE (from MyFixit)                      │  │ │
│  │  │  ────────────────────────────────────────             │  │ │
│  │  │  • Relevant service manual procedures                │  │ │
│  │  │  • Step-by-step repair instructions                  │  │ │
│  │  │  • Tool requirements                                 │  │ │
│  │  │  • Torque specifications                             │  │ │
│  │  └──────────────────────────────────────────────────────┘  │ │
│  └────────────────────────────────────────────────────────────┘ │
└──────────────────────────────────────────────────────────────────┘
```

---

## 🔧 Implementation Phases

### **Phase 1: Core Integration** (Week 1-2)

**Files to Create**:

```
src/
├── data/
│   ├── __init__.py
│   ├── sqlite_service.py          # SQLite abstraction
│   ├── chromadb_service.py        # Vector DB abstraction
│   ├── manual_service.py          # MyFixit JSON access
│   └── nhtsa_service.py           # NHTSA integration (already started)
│
├── diagnostic/
│   ├── __init__.py
│   ├── correlation_engine.py      # DTC-Failure correlations (planned)
│   ├── symptom_matcher.py         # ChromaDB symptom search
│   ├── confidence_scorer.py       # Enhanced confidence calculation
│   └── safety_checker.py          # Safety-critical validation
│
└── utils/
    ├── __init__.py
    ├── nlp_helpers.py             # Text processing
    └── validators.py              # Input validation
```

**Tasks**:
1. ✅ NHTSA integration strategy (DONE - documented)
2. Create ChromaDB service wrapper
3. Implement enhanced confidence scoring
4. Build symptom → forum matching
5. Create unified data access layer

---

### **Phase 2: Agent Framework** (Week 3-4)

**Files to Create**:

```
src/agents/
├── __init__.py
├── master_coordinator.py          # Root orchestrator
├── input_router.py                # Level 1: Input parsing & routing
│
├── specialized/
│   ├── __init__.py
│   ├── engine_agent.py            # Engine diagnostics
│   ├── transmission_agent.py      # Transmission diagnostics
│   ├── electrical_agent.py        # Electrical/network diagnostics
│   ├── chassis_agent.py           # Chassis/suspension
│   └── body_agent.py              # Body/HVAC
│
├── support/
│   ├── __init__.py
│   ├── safety_agent.py            # Safety verification
│   ├── forum_context_agent.py     # Forum search
│   ├── trend_agent.py             # NHTSA trend analysis
│   └── testing_agent.py           # Test sequence generation
│
└── output_formatter.py            # Level 4: Report generation
```

**Tasks**:
1. Define agent communication protocol
2. Implement master coordinator
3. Build input router with domain classification
4. Create specialized diagnostic agents
5. Implement support agents
6. Build output formatter

---

### **Phase 3: Web Scraper Integration** (Week 5)

**Files to Create**:

```
scripts/scrapers/
├── __init__.py
├── reddit_scraper.py              # Reddit automotive communities
├── stackexchange_scraper.py       # Mechanic Stack Exchange
├── tsb_scraper.py                 # TSB sources (if available)
│
└── data_ingestion/
    ├── chromadb_loader.py         # Load scraped data to ChromaDB
    ├── deduplication.py           # Remove duplicate forum posts
    └── embedding_generator.py     # Generate vector embeddings
```

**Tasks**:
1. Locate existing scraper code
2. Integrate with ChromaDB ingestion
3. Set up scheduled scraping
4. Implement deduplication
5. Test embedding quality

---

### **Phase 4: Testing & Refinement** (Week 6-7)

**Files to Create**:

```
tests/
├── integration/
│   ├── test_full_diagnostic_flow.py
│   ├── test_agent_coordination.py
│   └── test_data_sources.py
│
├── unit/
│   ├── test_sqlite_service.py
│   ├── test_chromadb_service.py
│   ├── test_correlation_engine.py
│   └── test_agents/
│       ├── test_engine_agent.py
│       ├── test_router.py
│       └── test_safety_agent.py
│
└── scenarios/
    ├── ford_f150_misfire.py       # Real-world test cases
    ├── ram_tipm_failure.py
    └── gm_afm_failure.py
```

**Tasks**:
1. Create test scenarios from real cases
2. Validate agent coordination
3. Test data source integration
4. Performance benchmarking
5. Refine confidence scoring

---

### **Phase 5: UI Development** (Week 8-10)

**Files to Create**:

```
web/
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   │   ├── VehicleSelector.jsx
│   │   │   ├── SymptomInput.jsx
│   │   │   ├── DTCInput.jsx
│   │   │   └── DiagnosticReport.jsx
│   │   │
│   │   └── pages/
│   │       ├── DiagnosticSession.jsx
│   │       └── Results.jsx
│   │
│   └── package.json
│
└── backend/
    ├── api/
    │   ├── __init__.py
    │   ├── main.py                # FastAPI/Flask app
    │   ├── routes/
    │   │   ├── diagnostic.py
    │   │   ├── vehicles.py
    │   │   └── reports.py
    │   │
    │   └── models/
    │       ├── request.py
    │       └── response.py
    │
    └── requirements.txt
```

---

## 🎯 Proposed Changes to Current Architecture

### 1. **Hybrid Data Strategy** ✅ (CONFIRMED)

**Current Decision**: Rule-based correlation for DTC-Failure mapping (NOT vector DB)
**Rationale**: Explainable, auditable, fast, offline-ready

**Amendment**:
- ✅ Keep rule-based for structured correlations
- ➕ ADD ChromaDB for unstructured forum/symptom matching
- **Result**: Best of both worlds

### 2. **Enhanced Confidence Scoring** 📝 (NEW)

**Current**: Basic confidence from failure patterns
**Proposed**: Multi-source confidence calculation

```python
def calculate_confidence(diagnosis):
    base = 0.5

    # Existing factors
    if diagnosis.has_dtc_match: base += 0.2
    if diagnosis.has_pattern_match: base += 0.15

    # NEW: NHTSA factor
    nhtsa_count = get_nhtsa_complaint_count(diagnosis)
    if nhtsa_count > 100: base += 0.15
    elif nhtsa_count > 50: base += 0.10
    elif nhtsa_count > 10: base += 0.05

    # NEW: Forum similarity factor
    forum_similarity = search_chromadb(diagnosis.symptoms)
    if forum_similarity > 0.9: base += 0.10
    elif forum_similarity > 0.7: base += 0.05

    # NEW: Safety boost (well-documented)
    if is_safety_critical(diagnosis): base += 0.05

    return min(base, 1.0)
```

### 3. **Agent Hierarchy Implementation** 📝 (NEW)

**Current**: SuperClaude command-based
**Proposed**: Persistent agent hierarchy

**Structure**:
```
Master Coordinator (orchestrates)
├─ Input Router (classifies domain)
├─ Specialized Agents (by domain)
│  ├─ Engine Agent
│  │  ├─ Misfire Sub-agent
│  │  ├─ Timing Sub-agent
│  │  └─ Fuel Sub-agent
│  ├─ Transmission Agent
│  └─ Electrical Agent
├─ Support Agents (cross-cutting)
│  ├─ Safety Agent
│  ├─ Forum Context Agent
│  └─ Trend Agent
└─ Output Formatter (reports)
```

### 4. **Data Pipeline Automation** 📝 (NEW)

**Current**: Manual imports
**Proposed**: Automated pipelines

```
Scrapers → Raw Data → Processing → Vector DB/SQLite
   ↓
Scheduling (cron/scheduled tasks)
   ↓
Deduplication → Quality Check → Ingestion
```

### 5. **Cross-Session State Management** 📝 (NEW)

**Use**: Serena MCP for session persistence
**Purpose**:
- Remember previous diagnostic sessions
- Learn from outcomes
- Build mechanic-specific knowledge
- Track which diagnoses were correct

---

## 🚀 Immediate Next Steps

### Week 1: Foundation Integration

1. **Locate/Create ChromaDB Setup**
   ```bash
   # Find existing ChromaDB or create new
   # Document forum data structure
   # Test semantic search capabilities
   ```

2. **Create Data Service Layer**
   ```python
   # src/data/sqlite_service.py
   # src/data/chromadb_service.py
   # src/data/nhtsa_service.py
   ```

3. **Implement Enhanced Confidence Scoring**
   ```python
   # src/diagnostic/confidence_scorer.py
   # Integrate NHTSA + Forum data
   ```

4. **Document Agent Communication Protocol**
   ```
   # Define how agents pass data
   # Standard message format
   # Error handling
   ```

---

## 📋 Integration Checklist

### Data Integration
- [ ] Locate/document ChromaDB forum data
- [ ] Create unified data access layer
- [ ] Implement NHTSA integration (strategy done)
- [ ] Test cross-database queries
- [ ] Benchmark performance

### Agent Framework
- [ ] Define agent hierarchy
- [ ] Create master coordinator
- [ ] Build input router
- [ ] Implement specialized agents (start with Engine)
- [ ] Add support agents (Safety first)
- [ ] Create output formatter

### Web Scrapers
- [ ] Locate existing scraper code
- [ ] Document data sources
- [ ] Set up ingestion pipeline
- [ ] Test ChromaDB loading
- [ ] Schedule automated updates

### Testing
- [ ] Create real-world test scenarios
- [ ] Validate agent coordination
- [ ] Performance benchmarks
- [ ] Confidence score accuracy
- [ ] End-to-end diagnostic flow

### Deployment
- [ ] API development (FastAPI/Flask)
- [ ] Frontend UI (React/Vue)
- [ ] Authentication/security
- [ ] Cloud deployment
- [ ] Shop PC installation package

---

## 💡 Key Benefits of This Architecture

1. **Unified Knowledge Base**: All data sources accessible through single interface
2. **Explainable AI**: Every diagnosis shows WHY (sources, confidence factors)
3. **Multi-Modal**: Structured (SQLite) + Unstructured (ChromaDB) + Procedures (JSON)
4. **Scalable**: Agent hierarchy allows adding new domains/manufacturers
5. **Maintainable**: Clear separation of concerns, modular design
6. **Offline-Capable**: SQLite + ChromaDB work without internet
7. **Real-World Grounded**: NHTSA complaints + forum discussions = actual failures
8. **Safety-First**: Dedicated safety verification agent

---

## 🎓 Questions for Clarification

1. **ChromaDB Status**: Where is the existing ChromaDB? What forum data is already loaded?
2. **Scrapers**: Where is the scraper code? Reddit/Stack Exchange specific or general?
3. **Agent Preferences**: Any specific SuperClaude personas you want to use for agents?
4. **Deployment Target**: Web app? Desktop app? API only?
5. **Timeline**: What's the target launch date for MVP?

---

**Status**: Architecture designed, ready for implementation
**Next Action**: Locate ChromaDB and scraper code, begin data service layer
**Document Version**: 1.0
**Last Updated**: November 8, 2025
