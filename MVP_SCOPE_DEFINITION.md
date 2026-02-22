# MVP Scope Definition - Personal Automotive Diagnostic Assistant

## Project Overview
**User**: Single professional mechanic (personal use initially)
**Goal**: Prove the system works with domestic vehicles before expansion
**Success Metric**: Functional diagnostic assistant that actually helps daily work

## Vehicle Coverage (MVP)
- **Ford**: F-150, Explorer, Mustang, Focus, Fusion (2015-2025)
- **GM**: Silverado, Tahoe, Impala, Malibu, Cruze (2015-2025) 
- **RAM**: 1500, 2500, Journey, Grand Cherokee (2015-2025)

**Engine Focus**: Common powertrains per make
- **Ford**: EcoBoost 2.3L, EcoBoost 3.5L, 5.0L V8, 3.5L V6
- **GM**: 5.3L V8, 6.2L V8, 2.0L Turbo, 3.6L V6
- **RAM**: 5.7L HEMI, 3.6L V6, 6.4L V8

## Data Sources Available
### Service Manuals
- **GM service data**: $1200/yr (professional subscription available)
- **Ford/RAM**: Need to source similar professional data
- Focus on engine/transmission/electrical diagnostic sections

### Technical Service Bulletins (TSBs)
- **Data Collection Method**: Web scraping for high-quality sources
- **Target Sources**: 
  - Manufacturer official sites
  - Professional mechanic forums
  - Automotive databases (AllData, Mitchell, etc.)

### OBD-II Code Database
- **Current Asset**: User has "pretty good list of codes"
- **Enhancement Plan**: Search and compile comprehensive manufacturer-specific variations
- **Priority**: P-codes (powertrain) first, then expand to B/C/U codes

### Failure Pattern Data
- **Major Asset**: User has common failures file for 14 manufacturers, 20 years
- **Coverage**: Extensive real-world failure patterns
- **Value**: Critical for probability ranking in differential diagnosis

### Diagnostic Methodology Training
- **Need**: Teach AI proper fault diagnosis procedures
- **Challenge**: Limited tokens in current session
- **Solution**: Document for next session implementation

## MVP Technical Features
### Core Diagnostic Flow
1. **Vehicle Identification**
   - Year, Make, Model, Engine selection
   - VIN decoder integration (future)

2. **Problem Input**
   - Customer complaint (structured)
   - DTC codes with freeze frame data
   - Symptom checklist + free text

3. **AI Analysis Engine**
   - RAG-based knowledge retrieval
   - Differential diagnosis (Top 5 probable causes)
   - Confidence scoring per diagnosis
   - Safety-critical system flagging

4. **Testing Guidance**
   - Specific diagnostic test procedures
   - Expected results for pass/fail scenarios
   - Tool requirements and safety warnings

5. **Results Integration**
   - Update probability ranking based on test results
   - Iterative refinement of diagnosis
   - Final repair recommendation

### Data Architecture (MVP) - IMPLEMENTED
```
Data Layer (Complete):
├── database/automotive_diagnostics.db    # SQLite: vehicles, DTCs, failures, NHTSA
├── data/vector_store/chroma/             # ChromaDB: forum semantic search
├── data/service_manuals/                 # JSON: 1,135 iFixit procedures
└── data/raw_imports/                     # Source files (never modify)

Application Layer (In Development):
├── src/scoring/confidence.py             # NHTSA-boosted confidence scoring
├── src/matching/symptom_matcher.py       # FTS5 + ChromaDB hybrid search
├── src/safety/alert_system.py            # Safety-critical flagging
├── src/analysis/trend_analyzer.py        # Complaint trend analysis
└── src/agents/                           # Diagnostic agent framework
```

## Implementation Priority
### Phase 1: Data Foundation (COMPLETE)
1. ~~**Import user's failure patterns file**~~ - 65 patterns, 1,994 vehicle links
2. ~~**Compile OBD-II code database**~~ - 270 codes imported
3. ~~**Import vehicle data**~~ - 18,607 vehicles (2005-2025)
4. ~~**Import NHTSA complaints**~~ - 2,144,604 records with FTS5 search
5. ~~**Set up vector store**~~ - ChromaDB with forum data (Reddit, Stack Exchange)
6. ~~**Architecture documentation**~~ - Agent hierarchy, NHTSA integration strategy

### Phase 2: Core Engine (CURRENT - Phase 3 in project roadmap)
1. **Implement confidence scoring** - NHTSA-boosted algorithm (formula documented)
2. **Build symptom matching engine** - FTS5 + ChromaDB hybrid search
3. **Create safety alert system** - Fire/crash/injury flagging
4. **Build diagnostic agent framework** - Master coordinator + specialized agents
5. **Develop testing sequence generation**

### Phase 3: User Interface
1. **Web-based diagnostic interface**
2. **Vehicle selection and validation**
3. **Symptom input forms**
4. **Results display and iteration**

## Success Criteria
- **Functional**: Can diagnose common domestic vehicle issues
- **Accurate**: >80% correct primary diagnosis on test cases
- **Useful**: Actually saves time vs manual diagnosis
- **Safe**: Properly flags safety-critical issues
- **Iterative**: Improves diagnosis with additional test results

## Next Priorities
1. **Implement confidence scoring engine** (high priority)
2. **Build symptom matching** (FTS5 + ChromaDB hybrid)
3. **Create safety alert system** (high priority - safety critical)
4. **Build first diagnostic agent** (Engine domain as proof-of-concept)

## Notes
- No cost analysis features needed in MVP
- Focus on functionality over scalability initially
- Personal use allows rapid iteration and feedback
- Success here enables future commercial considerations
- All data foundation work is complete - focus is now on the diagnostic engine

---
**Status**: Data foundation complete. Ready for diagnostic engine implementation.
**Next**: Build confidence scoring and symptom matching engines.