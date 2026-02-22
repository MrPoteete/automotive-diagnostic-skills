# System Architecture Diagrams

**Purpose**: Visual reference for agents to quickly understand system structure and data flow.

---

## 1. High-Level System Architecture

```mermaid
graph TB
    User[Mechanic User]

    subgraph "Frontend Layer"
        Dashboard[RAG Dashboard<br/>Streamlit]
        NextUI[Next.js UI<br/>src/frontend/]
    end

    subgraph "Server Layer"
        API[FastAPI Server<br/>home_server.py]
        Auth[API Key Auth]
    end

    subgraph "Skills Layer"
        MainSkill[Diagnostic Skill v3.1<br/>skills/SKILL.md]
        Router[Router Skill]
        EngineSkill[Engine Skill]
        TransSkill[Transmission Skill]
        ElecSkill[Electrical Skill]
        ChassisSkill[Chassis Skill]
    end

    subgraph "Data Layer"
        SQLite[(SQLite DB<br/>2.1M complaints<br/>211K TSBs<br/>18K vehicles)]
        ChromaDB[(ChromaDB<br/>Vector Store<br/>Forum Data)]
        FTS5[FTS5 Full-Text<br/>Search Engine]
    end

    subgraph "Agent Layer"
        Claude[Claude Sonnet 4.5<br/>Strategic Decisions]
        Gemini[Gemini 2.5<br/>Tactical Execution]
        SubAgents[15 Specialized Agents<br/>.claude/agents/]
    end

    User --> Dashboard
    User --> NextUI
    Dashboard --> API
    NextUI --> API
    API --> Auth
    Auth --> MainSkill
    MainSkill --> Router
    Router --> EngineSkill
    Router --> TransSkill
    Router --> ElecSkill
    Router --> ChassisSkill

    MainSkill --> SQLite
    MainSkill --> ChromaDB
    SQLite --> FTS5

    MainSkill --> Claude
    Claude --> Gemini
    Claude --> SubAgents

    style SQLite fill:#ff6b6b
    style ChromaDB fill:#ff6b6b
    style Claude fill:#4ecdc4
    style Gemini fill:#95e1d3
    style MainSkill fill:#f9ca24
```

---

## 2. RAG Pipeline Data Flow

```mermaid
graph LR
    Query[User Query:<br/>Vehicle + Symptoms]

    subgraph "Classification"
        Router[Router Skill<br/>Classify by DTC System]
        ValidateDTC[Validate DTC Code<br/>^[PCBU][0-3][0-9A-F]3$]
    end

    subgraph "Retrieval"
        VectorSearch[Vector Search<br/>ChromaDB<br/>Forum Data]
        SQLSearch[SQL Search<br/>SQLite<br/>NHTSA/TSBs]
        FTS5Search[FTS5 Full-Text<br/>Complaints/TSBs]
    end

    subgraph "Ranking"
        ConfScore[Confidence Scoring<br/>Source Reliability<br/>+ Vehicle Match]
        SafetyCheck[Safety-Critical Check<br/>Brakes/Airbags/Steering<br/>Min 0.9 confidence]
    end

    subgraph "Response Generation"
        SpecSkill[Specialized Skill<br/>Engine/Trans/Elec/Chassis]
        Attribution[Source Attribution<br/>NHTSA/TSB/Forum]
        Warning[Safety Warnings<br/>If applicable]
    end

    Query --> Router
    Query --> ValidateDTC
    Router --> VectorSearch
    Router --> SQLSearch
    Router --> FTS5Search

    VectorSearch --> ConfScore
    SQLSearch --> ConfScore
    FTS5Search --> ConfScore

    ConfScore --> SafetyCheck
    SafetyCheck --> SpecSkill
    SpecSkill --> Attribution
    Attribution --> Warning
    Warning --> Response[Diagnostic Response]

    style SafetyCheck fill:#ff6b6b
    style Warning fill:#ff6b6b
    style ConfScore fill:#f9ca24
```

---

## 3. Database Schema Architecture

```mermaid
graph TB
    subgraph "Core Tables (18K+ records)"
        Vehicles[vehicles<br/>18,607 records<br/>Make/Model/Year/Engine]
        DTCCodes[dtc_codes<br/>270 records<br/>OBD-II Codes]
        FailurePatterns[failure_patterns<br/>65 records<br/>Common Failures]
    end

    subgraph "NHTSA Data (2.3M+ records)"
        Complaints[nhtsa_complaints<br/>2,144,604 records<br/>Owner Complaints]
        TSBs[nhtsa_tsbs<br/>211,640 records<br/>Technical Bulletins]
        Recalls[recalls<br/>Safety Recalls]
    end

    subgraph "Relationship Tables"
        VehicleFailures[vehicle_failures<br/>1,994 links]
        DTCCorrelations[dtc_failure_correlations<br/>DTC → Failure mapping]
        FailureParts[failure_parts<br/>Parts needed]
        VehicleTSBs[vehicle_tsbs<br/>Vehicle → TSB links]
    end

    subgraph "Support Tables"
        Parts[parts<br/>OEM/Aftermarket]
        DiagTests[diagnostic_tests<br/>Procedures]
        ServiceProc[service_procedures<br/>Repair manuals]
    end

    subgraph "Full-Text Search (FTS5)"
        VehicleFTS[vehicles_fts<br/>Virtual Table]
        ComplaintsFTS[complaints_fts<br/>Virtual Table]
        TSBFTS[tsbs_fts<br/>Virtual Table]
        FailureFTS[failure_patterns_fts<br/>Virtual Table]
    end

    Vehicles --> VehicleFailures
    Vehicles --> VehicleTSBs
    Vehicles --> VehicleFTS

    FailurePatterns --> VehicleFailures
    FailurePatterns --> DTCCorrelations
    FailurePatterns --> FailureParts
    FailurePatterns --> FailureFTS

    DTCCodes --> DTCCorrelations

    Parts --> FailureParts

    Complaints --> ComplaintsFTS
    TSBs --> TSBFTS
    TSBs --> VehicleTSBs

    style VehicleFTS fill:#95e1d3
    style ComplaintsFTS fill:#95e1d3
    style TSBFTS fill:#95e1d3
    style FailureFTS fill:#95e1d3
    style Complaints fill:#ff6b6b
    style TSBs fill:#ff6b6b
```

---

## 4. Agent Orchestration Flow

```mermaid
graph TB
    UserRequest[User Request]

    subgraph "Decision Layer - Claude"
        Classify[Classify Task Type]
        Safety{Safety-Critical?}
        Complexity{Task Complexity?}
    end

    subgraph "Execution Layer - Gemini"
        GeminiFlash[Gemini 2.5 Flash<br/>Simple Tasks<br/>Fast & Cost-Effective]
        GeminiPro[Gemini 2.5 Pro<br/>Complex Tasks<br/>Deep Analysis]
    end

    subgraph "Specialized Agents - Claude"
        SecurityAgent[security-engineer<br/>Auth/Validation]
        QualityAgent[quality-engineer<br/>Testing/Coverage]
        PythonAgent[python-expert<br/>Code Review]
        DataAgent[data-engineer<br/>SQLite/Data]
        ArchitectAgent[system-architect<br/>Design Decisions]
    end

    subgraph "Validation Layer - Claude"
        ClaudeReview[Claude Validates<br/>Gemini Output]
        SafetyValidation[Safety Validation<br/>Min 0.9 Confidence]
        ConfidenceScore[Confidence Scoring<br/>Source Reliability]
    end

    UserRequest --> Classify
    Classify --> Safety

    Safety -->|Yes| ArchitectAgent
    Safety -->|No| Complexity

    Complexity -->|Simple| GeminiFlash
    Complexity -->|Complex| GeminiPro

    GeminiFlash --> ClaudeReview
    GeminiPro --> ClaudeReview

    ClaudeReview --> SafetyValidation
    SafetyValidation --> ConfidenceScore

    ArchitectAgent --> SecurityAgent
    SecurityAgent --> QualityAgent
    QualityAgent --> PythonAgent
    PythonAgent --> DataAgent

    ConfidenceScore --> Response[Final Response]
    DataAgent --> Response

    style Safety fill:#ff6b6b
    style SafetyValidation fill:#ff6b6b
    style GeminiFlash fill:#95e1d3
    style GeminiPro fill:#95e1d3
    style ClaudeReview fill:#4ecdc4
```

---

## 5. Progressive Disclosure Architecture

```mermaid
graph LR
    UserQuery[User Query]

    subgraph "Main Skill - skills/SKILL.md"
        RequestType[Classify Request Type:<br/>1. Full Diagnostic<br/>2. DTC Interpretation<br/>3. Component Testing<br/>4. Known Issues<br/>5. Technical Explanation<br/>6. Cost/Time Estimate]
    end

    subgraph "Reference Files - Progressive Load"
        AntiHalluc[anti-hallucination.md<br/>Source attribution<br/>Confidence protocols]
        ResponseFW[response-framework.md<br/>CO-STAR personas<br/>Output templates]
    end

    subgraph "Specialized Skills"
        EngineSkill[engine_skill/SKILL.md<br/>P-codes<br/>Powertrain]
        TransSkill[transmission_skill/SKILL.md<br/>Trans diagnostics]
        ElecSkill[electrical_skill/SKILL.md<br/>B/U-codes<br/>Networks]
        ChassisSkill[chassis_skill/SKILL.md<br/>C-codes<br/>Brakes/Suspension]
    end

    UserQuery --> RequestType

    RequestType -->|Load if needed| AntiHalluc
    RequestType -->|Load if needed| ResponseFW

    RequestType -->|P-code| EngineSkill
    RequestType -->|Trans issue| TransSkill
    RequestType -->|B/U-code| ElecSkill
    RequestType -->|C-code| ChassisSkill

    style AntiHalluc fill:#f9ca24
    style ResponseFW fill:#f9ca24
```

---

## 6. Data Source Hierarchy

```mermaid
graph TB
    subgraph "Tier 1: Official Data (HIGH - 0.9)"
        NHTSA[NHTSA Complaints<br/>2.1M records<br/>Government source]
        TSB[TSBs<br/>211K records<br/>Manufacturer bulletins]
        EPA[EPA Vehicles<br/>18K records<br/>Official specs]
        OBDII[OBD-II Codes<br/>270 codes<br/>SAE standard]
    end

    subgraph "Tier 2: Curated Data (MEDIUM - 0.7)"
        Failures[Common Failures<br/>65 patterns<br/>Professional databases]
        Manuals[Service Manuals<br/>iFixit JSON<br/>Verified procedures]
    end

    subgraph "Tier 3: Community Data (LOW - 0.5)"
        Reddit[Reddit Posts<br/>ChromaDB<br/>User discussions]
        StackEx[Stack Exchange<br/>ChromaDB<br/>Mechanics Q&A]
    end

    subgraph "Processing Pipeline"
        RawImports[data/raw_imports/<br/>⚠️ IMMUTABLE]
        Processed[data/processed/<br/>AI-ready JSON]
        VectorDB[data/vector_store/chroma/<br/>Embeddings]
    end

    NHTSA --> RawImports
    TSB --> RawImports
    Reddit --> RawImports
    StackEx --> RawImports

    RawImports --> Processed
    Processed --> VectorDB

    style NHTSA fill:#4ecdc4
    style TSB fill:#4ecdc4
    style EPA fill:#4ecdc4
    style OBDII fill:#4ecdc4
    style Failures fill:#f9ca24
    style Manuals fill:#f9ca24
    style Reddit fill:#ff6b6b
    style StackEx fill:#ff6b6b
    style RawImports fill:#e74c3c
```

---

## 7. File Structure Overview

```mermaid
graph TB
    Root[automotive-diagnostic-skills/]

    subgraph "Configuration & Docs"
        Claude[.claude/<br/>Agent framework]
        ClaudeDocs[.claude/docs/<br/>Reference files]
        Skills[skills/<br/>Diagnostic skills v3.1]
        Docs[docs/<br/>Project documentation]
    end

    subgraph "Data & Database"
        Data[data/<br/>Raw + processed]
        Database[database/<br/>SQLite + importers]
        RawImports[data/raw_imports/<br/>⚠️ NEVER MODIFY]
        VectorStore[data/vector_store/chroma/<br/>Embeddings]
    end

    subgraph "Application Code"
        Server[server/<br/>FastAPI + Streamlit]
        Src[src/<br/>Application source]
        Frontend[src/frontend/<br/>Next.js UI]
        Scripts[scripts/<br/>Utilities]
    end

    Root --> Claude
    Root --> Skills
    Root --> Docs
    Root --> Data
    Root --> Database
    Root --> Server
    Root --> Src
    Root --> Scripts

    Claude --> ClaudeDocs
    Data --> RawImports
    Data --> VectorStore
    Src --> Frontend

    style RawImports fill:#e74c3c
    style Claude fill:#4ecdc4
    style Skills fill:#f9ca24
```

---

## 8. Confidence Scoring Flow

```mermaid
graph LR
    Source[Data Source]

    subgraph "Base Confidence Assignment"
        Recall[NHTSA Recall<br/>0.9]
        ClassAction[Class Action<br/>0.9]
        VerifiedTSB[Verified TSB<br/>0.9]
        ActiveTSB[Active TSB<br/>0.7]
        MfgBulletin[Mfg Bulletin<br/>0.7]
        Forum[Forum Post<br/>0.5]
    end

    subgraph "Vehicle Match Bonus"
        ExactMatch[Exact Match<br/>Make/Model/Year/Engine<br/>+0.1]
        MMYMatch[Make/Model/Year<br/>+0.05]
        MMMatch[Make/Model<br/>+0.0]
        MakeOnly[Make Only<br/>-0.1]
    end

    subgraph "Final Confidence"
        Calculate[Calculate:<br/>min1.0, base + bonus]
        SafetyCheck{Safety-Critical<br/>System?}
        Threshold{Confidence<br/>>= 0.9?}
    end

    Source --> Recall
    Source --> ClassAction
    Source --> VerifiedTSB
    Source --> ActiveTSB
    Source --> MfgBulletin
    Source --> Forum

    Recall --> ExactMatch
    ClassAction --> ExactMatch
    VerifiedTSB --> MMYMatch
    ActiveTSB --> MMMatch
    MfgBulletin --> MMMatch
    Forum --> MakeOnly

    ExactMatch --> Calculate
    MMYMatch --> Calculate
    MMMatch --> Calculate
    MakeOnly --> Calculate

    Calculate --> SafetyCheck
    SafetyCheck -->|Yes| Threshold
    SafetyCheck -->|No| Accept[Accept Result]

    Threshold -->|Yes| Accept
    Threshold -->|No| Reject[Reject - Too Low<br/>Warn User]

    style SafetyCheck fill:#ff6b6b
    style Threshold fill:#ff6b6b
    style Reject fill:#e74c3c
    style Accept fill:#4ecdc4
```

---

## Quick Reference

**When to consult these diagrams**:
- New agent onboarding → Start with Diagram 1 (High-Level Architecture)
- Understanding data flow → Diagram 2 (RAG Pipeline)
- Database queries → Diagram 3 (Database Schema)
- Task delegation → Diagram 4 (Agent Orchestration)
- Skill routing → Diagram 5 (Progressive Disclosure)
- Data integrity → Diagram 6 (Data Source Hierarchy)
- File navigation → Diagram 7 (File Structure)
- Confidence validation → Diagram 8 (Confidence Scoring)

**Related Documentation**:
- @.claude/docs/ARCHITECT.md - Detailed architecture
- @.claude/docs/DOMAIN.md - Automotive domain rules
- @.claude/docs/AGENTS.md - Agent specifications
- @docs/DATABASE_ARCHITECTURE.md - Complete schema details
