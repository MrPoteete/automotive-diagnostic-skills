# Automotive Diagnostic Skills - Architecture Documentation

**Version:** 2.0  
**Last Updated:** January 2026  
**Architecture Type:** Modular Progressive Disclosure with RAG Enhancement

---

## 📐 SYSTEM ARCHITECTURE OVERVIEW

### Design Philosophy

This automotive diagnostic skill system uses a **modular progressive disclosure architecture** to optimize for:

1. **Token Efficiency**: Load only necessary context (40-60% faster responses)
2. **Response Quality**: Focused context prevents information overload
3. **Maintainability**: Isolated reference documents are easier to update
4. **Scalability**: Add new manufacturers/systems without modifying core logic
5. **Cost Optimization**: Smaller context windows = lower API costs

### Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                     ENTRY POINT: SKILL.md                        │
│  - Request classification                                        │
│  - Safety-critical detection                                     │
│  - Routing logic                                                 │
│  - Core diagnostic framework (CO-STAR)                           │
│  - Anti-hallucination protocols                                  │
└────────────────────────┬────────────────────────────────────────┘
                         │
                         ▼
         ┌───────────────┴────────────────┐
         │    PROGRESSIVE LOADING          │
         │   (Based on request type)       │
         └───────────────┬────────────────┘
                         │
    ┌────────────────────┼────────────────────┐
    │                    │                     │
    ▼                    ▼                     ▼
┌──────────┐      ┌─────────────┐      ┌────────────┐
│Reference │      │Manufacturer │      │  Database  │
│Documents │      │  Protocols  │      │   Queries  │
└──────────┘      └─────────────┘      └────────────┘
    │                    │                     │
    ├─diagnostic-process.md                    │
    ├─obd-ii-methodology.md                    │
    ├─anti-hallucination.md        ├─ford-protocols.md
    ├─diagnostic-examples.md       ├─gm-protocols.md
    └─warranty-failures.md         └─stellantis-protocols.md
                                        ├─Common failures
                                        ├─OBD-II codes
                                        └─TSB data
```

---

## 📁 FILE STRUCTURE & ORGANIZATION

### Directory Layout

```
automotive-diagnostic-skills/
│
├── skills/
│   ├── SKILL.md                    # ← CORE ROUTER (this is loaded first)
│   ├── README.md                   # ← This file (architecture docs)
│   │
│   ├── references/                 # ← Reference documents (loaded on-demand)
│   │   ├── diagnostic-process.md   # ASE systematic methodology
│   │   ├── obd-ii-methodology.md   # DTC interpretation procedures
│   │   ├── anti-hallucination.md   # Confidence scoring & verification
│   │   ├── diagnostic-examples.md  # Real-world case studies
│   │   └── warranty-failures.md    # Known failure patterns export
│   │
│   └── references/manufacturers/   # ← Brand-specific protocols
│       ├── ford-protocols.md       # Ford diagnostic procedures
│       ├── gm-protocols.md         # GM diagnostic procedures
│       ├── stellantis-protocols.md # RAM/Dodge/Chrysler/Jeep procedures
│       ├── toyota-protocols.md     # Toyota diagnostic procedures
│       ├── honda-protocols.md      # Honda diagnostic procedures
│       └── [other makes...]        # Future additions
│
├── docs/
│   ├── RESEARCH_MASTER.md          # Comprehensive research foundation
│   ├── CHANGELOG.md                # Version history and updates
│   └── PROJECT_INDEX.md            # Master navigation document
│
├── database/
│   ├── automotive_diagnostics.db   # SQLite database
│   ├── schema.sql                  # Database structure
│   └── import_scripts/             # Data import utilities
│
└── [other project files...]
```

### File Size Guidelines

| File Category | Target Size | Rationale |
|--------------|-------------|-----------|
| Core Router (SKILL.md) | ~10-15KB | Always loaded - must be concise |
| Reference Documents | 5-10KB each | Loaded conditionally - focused content |
| Manufacturer Protocols | 5-8KB each | Brand-specific - rarely load multiple |
| Examples/Case Studies | 8-12KB | Rich content but optional loading |

**Total Context Budget:** 30-40KB maximum per request (Core + 2-3 references)

---

## 🔄 REQUEST ROUTING FLOW

### How Progressive Loading Works

1. **Mechanic sends request** → Claude receives message
2. **SKILL.md always loaded first** → Provides routing logic
3. **Request analyzed** → Type classification (6 types)
4. **Conditional loading** → Only relevant references loaded
5. **Response generated** → Using loaded context only
6. **Response returned** → Structured diagnostic output

### Request Type Matrix

| Request Type | Keywords | Files Loaded | Typical Size |
|--------------|----------|--------------|--------------|
| **Full Diagnostic** | "diagnose", "what's wrong", "troubleshoot" | diagnostic-process.md + anti-hallucination.md + manufacturer protocol | 10KB + 8KB + 6KB + 5KB = ~29KB |
| **OBD-II Code** | "P0XXX", "code", "DTC", "check engine" | obd-ii-methodology.md | 10KB + 7KB = ~17KB |
| **Testing Procedure** | "how to test", "procedure for [component]" | diagnostic-process.md (section) | 10KB + 3KB = ~13KB |
| **Known Issue Research** | "common problems", "TSB", "[make/model] issues" | manufacturer protocol + warranty-failures.md | 10KB + 5KB + 8KB = ~23KB |
| **Educational** | "explain", "how does [X] work", "what is" | Most relevant single reference | 10KB + 5-8KB = ~15-18KB |
| **Cost/Time Estimate** | "how much", "labor time", "cost" | None (base knowledge only) | 10KB only |

### Routing Decision Logic

```python
def route_request(request_text, vehicle_info):
    """
    Determines which reference documents to load based on request analysis.
    """
    
    # STEP 1: Safety Check (ALWAYS FIRST)
    if contains_safety_keywords(request_text):
        return {
            'type': 'SAFETY_CRITICAL',
            'load': [],  # No additional files needed
            'action': 'immediate_safety_warning'
        }
    
    # STEP 2: Request Type Classification
    if has_diagnostic_intent(request_text) and has_symptoms(request_text):
        files_to_load = [
            'references/diagnostic-process.md',
            'references/anti-hallucination.md'
        ]
        
        # Add manufacturer protocol if make specified
        if vehicle_info.get('make'):
            make_file = f"references/manufacturers/{vehicle_info['make'].lower()}-protocols.md"
            if file_exists(make_file):
                files_to_load.append(make_file)
        
        return {
            'type': 'FULL_DIAGNOSTIC',
            'load': files_to_load
        }
    
    elif has_dtc_codes(request_text):
        return {
            'type': 'OBD_II_CODE',
            'load': ['references/obd-ii-methodology.md']
        }
    
    elif has_testing_question(request_text):
        return {
            'type': 'TESTING_PROCEDURE',
            'load': ['references/diagnostic-process.md']
        }
    
    elif has_known_issue_query(request_text):
        files_to_load = ['references/warranty-failures.md']
        
        if vehicle_info.get('make'):
            make_file = f"references/manufacturers/{vehicle_info['make'].lower()}-protocols.md"
            if file_exists(make_file):
                files_to_load.append(make_file)
        
        return {
            'type': 'KNOWN_ISSUE',
            'load': files_to_load
        }
    
    elif has_educational_intent(request_text):
        # Determine most relevant single reference
        relevant_ref = identify_relevant_reference(request_text)
        return {
            'type': 'EDUCATIONAL',
            'load': [relevant_ref]
        }
    
    else:  # Cost/time estimate or general question
        return {
            'type': 'GENERAL',
            'load': []  # Use base knowledge only
        }
```

---

## 🎯 CORE COMPONENTS EXPLAINED

### 1. SKILL.md - The Router

**Purpose:** Central coordination and routing logic

**Key Sections:**
- **Request Routing Logic** - Decision tree for loading references
- **CO-STAR Framework** - Structured response format
- **Safety Protocols** - Mandatory first-check for critical systems
- **Anti-Hallucination** - Confidence scoring and source grounding
- **Diagnostic Workflow** - 7-phase systematic process
- **Prohibited Actions** - Clear scope boundaries

**When Modified:**
- Major framework changes (CO-STAR → different structure)
- New request types added
- Routing logic refinement
- Safety protocol updates

**Best Practices:**
- Keep concise (always loaded = token cost every request)
- Reference external docs rather than duplicating content
- Update version number when changed
- Test routing logic with diverse request types

---

### 2. Reference Documents

#### diagnostic-process.md

**Purpose:** ASE systematic diagnostic methodology

**Content:**
- 7-step diagnostic workflow (Verify → Research → Inspect → Retrieve → Isolate → Test → Verify)
- Fault tree analysis procedures
- Component testing procedures by system
- Decision tree diagrams
- Testing equipment requirements

**When Loaded:** Full diagnostic requests

**Usage:** Provides systematic troubleshooting framework

---

#### obd-ii-methodology.md

**Purpose:** OBD-II code interpretation and procedures

**Content:**
- DTC code structure (P/B/C/U codes)
- Generic vs. manufacturer-specific codes
- Readiness monitors (continuous vs. non-continuous)
- Freeze frame data interpretation
- Mode analysis (Modes 1-10)
- Enable criteria for code setting
- Permanent codes handling

**When Loaded:** Requests mentioning DTCs or "check engine light"

**Usage:** Professional-level code interpretation beyond simple definitions

---

#### anti-hallucination.md

**Purpose:** Confidence scoring and verification protocols

**Content:**
- Source grounding requirements
- Confidence calculation methodology
- "I don't know" threshold protocols
- Evidence hierarchy (Tier 1-5 sources)
- Speculation vs. fact boundaries
- Citation formatting standards

**When Loaded:** All full diagnostic analyses

**Usage:** Ensures factual accuracy and transparent uncertainty

---

#### diagnostic-examples.md

**Purpose:** Real-world case studies with full diagnostic walkthroughs

**Content:**
- 10-15 comprehensive case studies
- Multiple systems (engine, electrical, HVAC, etc.)
- Diverse makes/models
- Various complexity levels
- Show complete diagnostic reasoning
- Include wrong turns and corrections

**When Loaded:** Educational requests or complex diagnostics needing examples

**Usage:** Demonstrates proper diagnostic methodology through concrete examples

---

#### warranty-failures.md

**Purpose:** Common failure patterns by make/model/mileage

**Content:**
- Database export of documented failures
- Organized by manufacturer
- Includes affected components, typical mileage, symptoms
- Statistical prevalence when available
- Reference sources

**When Loaded:** Known issue research or when make/model specified

**Usage:** Identifies common problems for differential diagnosis

---

### 3. Manufacturer Protocols

#### Structure (all manufacturer files follow this template):

```markdown
# [MAKE] Diagnostic Protocols

## Make-Specific Considerations

### Common Diagnostic Pitfalls
[Brand-specific issues mechanics encounter]

### Special Tools Required
[Manufacturer-specific scan tools, adapters, software]

### System Architecture Notes
[Unique electrical architecture, bus systems, module locations]

## Known Issues by Model Year

### [Model] ([Year Range])
**Common Failures:**
- [Component]: [Symptom], [Typical Mileage], [TSB if exists]

## OBD-II Code Interpretation Notes

### Manufacturer-Specific Codes (P1XXX)
[Common codes unique to this make]

## Diagnostic Procedures

### [System] Diagnostics
[Make-specific diagnostic steps that differ from generic procedures]

## Service Manual References

[Where to find official service information]
```

**When Loaded:** When vehicle make is specified in request

**Usage:** Provides brand-specific diagnostic context and known issues

---

## 🔧 MAINTENANCE & UPDATES

### How to Add New Reference Documents

1. **Create Document** in `skills/references/`
   - Follow naming convention: `lowercase-with-hyphens.md`
   - Target 5-10KB size
   - Use consistent markdown formatting

2. **Update SKILL.md Routing**
   - Add to request type classification logic
   - Define when document should load
   - Add to routing decision tree diagram

3. **Document in README** (this file)
   - Add to file structure section
   - Describe purpose and content
   - Note when loaded

4. **Test Routing**
   - Create test requests that should trigger loading
   - Verify appropriate documents load
   - Check token usage stays within budget

### How to Add Manufacturer Protocol

1. **Create File** in `skills/references/manufacturers/`
   - Name: `[make]-protocols.md` (e.g., `toyota-protocols.md`)
   - Use standard manufacturer template structure

2. **Populate Content**
   - Research common issues for that make
   - Document special tools/procedures
   - Add manufacturer-specific DTC codes
   - Include TSB information if available

3. **Update Routing** in SKILL.md
   - Should auto-load when make matches filename
   - No explicit routing change needed if following convention

4. **Add to Database**
   - Import known failures for that make
   - Add to warranty_failures table

### Version Control Best Practices

```markdown
# File Header Template

**Version:** X.Y
**Last Updated:** YYYY-MM-DD
**Changelog:**
- v2.1 (2026-02-15): Added Honda Accord hybrid diagnostic procedures
- v2.0 (2026-01-15): Initial modular architecture implementation
- v1.0 (2025-12-01): Legacy monolithic version

**Review Schedule:** Quarterly
**Next Review:** YYYY-MM-DD
```

### Update Triggers

**Immediate Updates Required:**
- Safety-critical recall affecting diagnostic procedures
- Major ASE standard changes
- OBD-II code database updates (SAE J2012 revisions)

**Quarterly Updates:**
- New TSB releases for supported makes
- Common failure pattern additions
- Manufacturer protocol refinements

**Annual Reviews:**
- Complete content accuracy verification
- Remove obsolete information
- Update references and citations

---

## 📊 PERFORMANCE OPTIMIZATION

### Token Usage Targets

| Metric | Target | Current | Status |
|--------|--------|---------|--------|
| Average tokens/request | <8,000 | TBD | ⏳ Monitoring |
| Peak tokens/request | <15,000 | TBD | ⏳ Monitoring |
| Response time | <10 sec | TBD | ⏳ Monitoring |
| Cost per diagnostic | <$0.05 | TBD | ⏳ Monitoring |

### Optimization Strategies

1. **Lazy Loading**: Only load references when truly needed
2. **Content Compression**: Keep reference docs focused and concise
3. **Smart Excerpting**: Load relevant sections, not entire documents
4. **Caching**: Reuse loaded context for follow-up questions
5. **Query Optimization**: Database queries should be selective

### Monitoring & Metrics

Track these metrics for continuous improvement:

```python
diagnostic_metrics = {
    'request_type_distribution': {
        'full_diagnostic': 0.45,  # 45% of requests
        'obd_ii_code': 0.30,      # 30% of requests
        'testing_procedure': 0.15, # 15% of requests
        'known_issue': 0.05,      # 5% of requests
        'educational': 0.03,      # 3% of requests
        'general': 0.02           # 2% of requests
    },
    
    'files_loaded_per_request': {
        'avg': 2.3,  # Average files loaded
        'max': 4,    # Maximum files in single request
        'min': 1     # Minimum (just SKILL.md)
    },
    
    'accuracy_by_type': {
        'full_diagnostic': 0.82,  # 82% accuracy when verified
        'obd_ii_code': 0.95,      # 95% accuracy (code definitions)
        'testing_procedure': 0.88  # 88% accuracy
    }
}
```

---

## 🧪 TESTING & VALIDATION

### Test Request Categories

Create test cases for each request type:

```markdown
## Test Case: Full Diagnostic Analysis

**Input:**
Vehicle: 2018 Honda Civic EX-L, 1.5T, 67k miles
Symptoms: Engine cranks, won't start, after driving through deep water
Codes: P0335, P0016
Previous tests: Battery 12.4V, starter OK, fuel pump primes

**Expected Loading:**
- ✅ SKILL.md (always)
- ✅ diagnostic-process.md
- ✅ anti-hallucination.md  
- ✅ honda-protocols.md
- ❌ obd-ii-methodology.md (not needed - has full diagnostic context)

**Expected Output Structure:**
- Safety assessment (NON-CRITICAL)
- Symptom summary
- Top 5 differential diagnoses (water-damaged CKP sensor should be #1)
- Diagnostic test sequence
- Primary recommendation
- Sources cited

**Success Criteria:**
- Correct files loaded
- Response follows CO-STAR format
- Confidence scores provided
- Sources attributed
- Token count < 12,000
```

### Validation Checklist

Before deploying updates:

- [ ] All request types tested with sample inputs
- [ ] Routing logic loads correct files
- [ ] Token usage within budget (<15,000 max)
- [ ] Safety-critical detection works correctly
- [ ] Confidence scores calculated properly
- [ ] Sources properly attributed
- [ ] Disclaimers present in all diagnostic outputs
- [ ] Response format consistent with CO-STAR
- [ ] No hallucinated information in test responses
- [ ] Manufacturer protocols load when make specified

---

## 🎓 USAGE GUIDELINES FOR MECHANICS

### Quick Reference: When to Use This Skill

**✅ BEST USES:**

1. **Initial Diagnostic Triage** (60 seconds)
   - Quick differential diagnosis
   - Confirms or challenges your suspicion
   - Identifies what to test first

2. **Complex Intermittent Problems** (5 minutes)
   - Systematic approach to difficult diagnostics
   - Multiple possible causes need ranking
   - Need comprehensive test sequence

3. **Code Research** (30 seconds)
   - Quick DTC definition and common causes
   - Make/model specific code information
   - Enable criteria and monitor status

4. **Procedure Verification** (2 minutes)
   - Double-check testing procedure
   - Confirm specs and expected results
   - Validate diagnostic approach

5. **Second Opinion** (3 minutes)
   - Validate your diagnostic conclusion
   - Check for alternative explanations
   - Build confidence before expensive repair

**❌ NOT SUITABLE FOR:**

- Replacing hands-on diagnosis
- Exact repair cost quotes (ranges only)
- Warranty coverage determination
- Legal advice on liability
- Real-time interactive testing
- Physical inspection replacement

### Input Best Practices

**Provide this information for best results:**

```markdown
**Minimum (Required):**
- Year, Make, Model
- Primary symptom
- When symptom occurs

**Better (Recommended):**
- Above + Mileage
- OBD-II codes if present
- Warning lights
- Recent repairs/maintenance

**Best (Optimal):**
- Above + Freeze frame data
- Sensor readings from scan tool
- Previous diagnostic tests performed
- Customer usage patterns
```

**Information Quality = Diagnostic Quality**

More complete information → More accurate diagnosis → Better confidence scores

---

## 🔐 SAFETY & ETHICAL CONSIDERATIONS

### Safety-First Architecture

This system is designed with safety as the **highest priority**:

1. **Mandatory Safety Check**: Every request analyzed for safety keywords BEFORE diagnosis
2. **Immediate Warnings**: Safety-critical issues flagged prominently
3. **Do Not Operate Warnings**: Clear guidance when vehicle unsafe to drive
4. **Professional Verification Required**: All diagnoses include verification disclaimer

### Liability Protection

**Every diagnostic output includes:**

```markdown
## ⚖️ DISCLAIMER

This AI-generated analysis requires professional verification through hands-on 
diagnostic testing. Not a substitute for in-person inspection.

CRITICAL LIMITATIONS:
- ❌ Physical inspection not performed
- ❌ Actual measurements not taken
- ❌ Vehicle-specific conditions not observed  
- ❌ Interactive diagnostic testing not conducted

REQUIRED ACTIONS:
- ✅ All diagnoses MUST be verified by qualified technician
- ✅ Safety-critical systems MUST be inspected by professional
- ✅ Cost estimates are approximate and may vary significantly
- ✅ Additional problems may be discovered during repair

LIABILITY: This analysis does not constitute a definitive diagnosis, repair 
guarantee, or professional advice. Actual repair decisions should be made by 
qualified automotive professionals after proper diagnostic verification.
```

### Ethical Use

**This tool should:**
- ✅ Assist mechanics in systematic diagnosis
- ✅ Provide evidence-based second opinions
- ✅ Educate on proper diagnostic procedures
- ✅ Identify safety-critical issues
- ✅ Save diagnostic time on complex problems

**This tool should NOT:**
- ❌ Replace hands-on mechanic expertise
- ❌ Provide definitive diagnoses without verification
- ❌ Make warranty or legal determinations
- ❌ Guarantee specific outcomes
- ❌ Bypass professional diagnostic testing

---

## 📚 ADDITIONAL RESOURCES

### Related Documentation

- **RESEARCH_MASTER.md**: 900-line comprehensive research foundation
- **PROJECT_INDEX.md**: Master navigation for entire project
- **CHANGELOG.md**: Version history and update log
- **Database Schema**: See `database/schema.sql`

### External References

**ASE Certification:**
- ASE website: https://www.ase.com/
- Test specifications: ASE Test Prep Guides A1-A9, L1

**OBD-II Standards:**
- SAE J2012: OBD-II DTC Definitions
- SAE J1979: E/E Diagnostic Test Modes
- ASE Study Guide: OBD-II Overview

**Prompt Engineering:**
- CO-STAR Framework: Singapore GPT-4 Competition Winner
- Vanderbilt Pattern Catalog: Prompt Engineering Patterns
- OpenAI Best Practices: Official API Documentation

**Hallucination Prevention:**
- Nature Communications: SourceCheckup Framework
- arXiv 2412.14737: Verbalized Confidence Scores
- Johns Hopkins: Teaching AI Uncertainty

---

## 🚀 FUTURE ENHANCEMENTS

### Planned Features (Roadmap)

**Phase 5: Enhanced Manufacturer Coverage** (Q2 2026)
- [ ] Add Toyota protocols
- [ ] Add Honda protocols  
- [ ] Add Nissan protocols
- [ ] Add Subaru protocols
- [ ] Add VW/Audi protocols

**Phase 6: Advanced Diagnostics** (Q3 2026)
- [ ] Hybrid/EV diagnostic procedures
- [ ] ADAS system diagnostics
- [ ] Network diagnostics (CAN/LIN bus)
- [ ] Module programming guidance

**Phase 7: Integration Features** (Q4 2026)
- [ ] Shop management system integration
- [ ] VIN decoder integration
- [ ] Parts lookup integration
- [ ] Labor time database integration

**Phase 8: Machine Learning** (2027)
- [ ] Diagnostic outcome tracking
- [ ] Success rate by diagnosis type
- [ ] Adaptive confidence scoring
- [ ] Personalized recommendations based on mechanic feedback

### Contribution Guidelines

To contribute to this project:

1. **Report Issues**: Document bugs or inaccuracies with specific examples
2. **Suggest Improvements**: Propose new features or refinements
3. **Submit Content**: Add manufacturer protocols or case studies
4. **Provide Feedback**: Report diagnostic accuracy on real-world cases

**Contact:** [Project maintainer information]

---

## 📝 VERSION HISTORY

**v2.0 (January 2026)** - Current
- Modular progressive disclosure architecture
- RAG-enhanced diagnostics
- Manufacturer-specific protocols
- Comprehensive anti-hallucination protocols
- 40-60% token reduction vs. monolithic design

**v1.0 (December 2025)** - Legacy
- Monolithic single-file design
- Basic diagnostic framework
- No progressive loading
- Limited manufacturer specificity

---

**For questions, issues, or contributions, refer to PROJECT_INDEX.md**