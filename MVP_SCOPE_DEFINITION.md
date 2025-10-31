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

### Data Architecture (MVP)
```
Knowledge Base Structure:
├── service_manuals/
│   ├── ford/
│   ├── gm/
│   └── ram/
├── tsbs/
│   ├── by_make/
│   └── by_symptom/
├── obd_codes/
│   ├── generic_p_codes.json
│   └── manufacturer_specific/
├── failure_patterns/
│   ├── common_failures_14_makes.json
│   └── probability_rankings/
└── diagnostic_procedures/
    ├── systematic_approaches/
    └── safety_protocols/
```

## Implementation Priority
### Phase 1: Data Foundation
1. **Import user's failure patterns file**
2. **Compile OBD-II code database**
3. **Structure diagnostic methodology documentation**
4. **Set up basic RAG pipeline**

### Phase 2: Core Engine
1. **Implement differential diagnosis logic**
2. **Create confidence scoring algorithms**
3. **Build safety-critical system detection**
4. **Develop testing sequence generation**

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

## Next Session Priorities
1. **Import failure patterns data** (high priority)
2. **Document diagnostic methodology** (critical knowledge transfer)
3. **Set up technical architecture** (database + RAG pipeline)
4. **Begin core diagnostic engine implementation**

## Notes
- No cost analysis features needed in MVP
- Focus on functionality over scalability initially
- Personal use allows rapid iteration and feedback
- Success here enables future commercial considerations

---
**Status**: MVP scope defined and ready for implementation
**Next**: Import user data and begin technical architecture setup