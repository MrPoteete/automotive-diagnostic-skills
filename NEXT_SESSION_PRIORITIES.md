# Next Session Priorities - Phase 3 Implementation

**Last Updated**: February 8, 2026
**Current Phase**: Phase 3 - Agent Framework & Diagnostic Engine

---

## Foundation Status (Complete)

**Data Layer** - All sources loaded and operational:
- 18,607 vehicles (2005-2025)
- 270 OBD-II diagnostic codes
- 65 failure patterns with 1,994 vehicle links
- 2,144,604 NHTSA complaints with FTS5 search
- ChromaDB vector store (Reddit + Stack Exchange forums)
- 1,135 iFixit service manuals (107 Ford/GM/RAM specific)

**Diagnostic Skill v3.1** - Deployed to `skills/`:
- Progressive disclosure routing (6 request types)
- Categorical assessment system (replaces percentage confidence)
- Anti-hallucination protocols with 3-tier source attribution
- CO-STAR persona framework for ASE technicians
- Mandatory SOURCES and DISCLAIMER sections
- Expected grade: B+ (87.5/100), up from C (76.5/100)

**Immediate Priority**: Validate skill v3.1 with test scenarios before proceeding to Phase 3 code

---

## Pre-Phase 3: Skill Validation (Do First)

### 0. Validate Diagnostic Skill v3.1 (Immediate Priority)
**Goal**: Confirm skill produces expected output improvements before building engine code

**Test Cases** (from `skills/CHANGELOG_v3.1.md`):
1. **Categorical Assessment**: "Diagnose: 2019 Chevy Silverado, misfire cylinder 1, P0300 P0301" → Should use PROBABLE, not 75%
2. **Specification Attribution**: "What's normal compression for L86 6.2L?" → Should cite source or say "verify specification"
3. **Data Level**: "Diagnose: 2018 Civic won't start, cranks fine, no codes" → Should state Data Level: PARTIAL
4. **Evidence FOR/AGAINST**: "Diagnose: Toyota Sienna, driver side no heat, passenger OK" → Should show both
5. **Mandatory Sections**: Any Type 1 diagnostic → Must include SOURCES and DISCLAIMER

**Success Criteria**: All 5 test cases pass, overall score >= 80/100

---

## Phase 3 Implementation Priorities

### 1. Enhanced Confidence Scoring Engine (High Priority)
**Goal**: Implement the NHTSA-boosted confidence scoring algorithm

The formula is documented in `docs/NHTSA_INTEGRATION_STRATEGY.md`. Key factors:
- Base confidence from source reliability (NHTSA > TSB > Forum)
- NHTSA complaint frequency boost (+0.05 to +0.15)
- ChromaDB forum similarity boost (+0.05 to +0.10)
- Vehicle match specificity adjustment
- Safety-critical system bonus

**Implementation**: Create `src/scoring/confidence.py`

### 2. Symptom Matching Engine (High Priority)
**Goal**: Match customer symptoms to known failure patterns

Two-pronged approach:
- **FTS5 search** on NHTSA complaint narratives (exact keyword matching)
- **ChromaDB semantic search** on forum data (meaning-based matching)
- Combine results with weighted scoring

**Implementation**: Create `src/matching/symptom_matcher.py`

### 3. Safety Alert System (High Priority)
**Goal**: Automatically flag safety-critical diagnoses

Query NHTSA data for:
- Fire incidents per vehicle+component
- Crash incidents
- Injury/death history
- Active recalls

Flag any diagnosis involving safety-critical systems (brakes, airbags,
steering, throttle, fuel pump, TIPM) with appropriate warnings.

**Implementation**: Create `src/safety/alert_system.py`

### 4. Trend Analysis (Medium Priority)
**Goal**: Show if vehicle issues are increasing or decreasing

Compare complaint frequency across model years to provide context:
- "This issue affects 340 vehicles and is increasing year-over-year"
- "Complaints for this component peaked in 2019 and are declining"

**Implementation**: Create `src/analysis/trend_analyzer.py`

### 5. Master Coordinator Agent (Medium Priority)
**Goal**: Build the orchestration layer

Design documented in `docs/SYSTEM_INTEGRATION_ARCHITECTURE.md`:
- Input Router: Parse symptoms, validate DTCs, classify domain
- Agent dispatch: Route to specialized agents by domain
- Result aggregation: Rank and merge diagnostic recommendations
- Output formatting: Generate mechanic-friendly reports

### 6. First Specialized Agent - Engine (Medium Priority)
**Goal**: Build the engine diagnostic agent as proof-of-concept

Workflow:
1. Query SQLite for DTC-failure correlations
2. Check NHTSA complaint frequency for the vehicle+component
3. Search ChromaDB for similar forum cases
4. Run safety-critical checks
5. Calculate enhanced confidence scores
6. Generate differential diagnosis (top 5)
7. Provide testing sequence

---

## Architecture Reference

See these docs for implementation details:
- `skills/SKILL.md` - Diagnostic skill v3.1 definition
- `skills/references/anti-hallucination.md` - Source grounding protocols
- `skills/CHANGELOG_v3.1.md` - v3.1 change documentation
- `docs/SYSTEM_INTEGRATION_ARCHITECTURE.md` - Full agent hierarchy design
- `docs/NHTSA_INTEGRATION_STRATEGY.md` - 7 integration patterns with code
- `docs/NHTSA_QUICK_REFERENCE.md` - Query templates
- `docs/DATABASE_ARCHITECTURE.md` - Schema reference

---

## Questions to Resolve During Implementation

1. Should confidence scoring use a linear or weighted model?
2. What minimum confidence threshold triggers "consult professional" warning?
3. How many differential diagnoses to show (top 3? top 5?)?
4. Should forum data boost be capped to prevent over-weighting anecdotal evidence?
5. What format works best for the mechanic output report?

---

**Recovery Phrase**: "Implement Phase 3 diagnostic engine starting with confidence scoring and symptom matching"
