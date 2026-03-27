# System Architecture Diagrams

> **GROUND TRUTH — verified 2026-03-26**
> All row counts and paths are runtime-verified against live databases.
> Any agent reading this file should trust these numbers over comments in code.
> If numbers look wrong, run: `sqlite3 database/automotive_complaints.db "SELECT COUNT(*) FROM complaints_fts;"` to re-verify.

---

## 1. High-Level System Architecture

```mermaid
graph TB
    User[👨‍🔧 Mechanic / User]

    subgraph "Frontend — port 3000"
        NextUI["Next.js UI\nsrc/frontend/\nnpm run dev"]
    end

    subgraph "Backend — port 8000"
        API["FastAPI Server\nserver/home_server.py\nuvicorn :8000"]
        Auth["API Key Auth\nX-API-KEY header"]
    end

    subgraph "Diagnostic Engine"
        EngineAgent["engine_agent.diagnose()\nsrc/diagnostic/engine_agent.py"]
        SymptomMatcher["symptom_matcher.py\nNHTSA component mapping"]
        ConfidenceScorer["confidence_scorer.py\nsource × vehicle match"]
        AlertSystem["alert_system.py\nsafety-critical gate"]
        TrendAnalyzer["trend_analyzer.py\nyear-over-year trends"]
    end

    subgraph "Skills Layer — skills/"
        MainSkill["SKILL.md\nASE 7-phase protocol"]
        RouterSkill["router_skill/\nDTC classifier"]
        EngineSkill["engine_skill/\nP-codes / powertrain"]
        TransSkill["transmission_skill/\ntrans diagnostics"]
        ElecSkill["electrical_skill/\nB/U-codes"]
        ChassisSkill["chassis_skill/\nC-codes / brakes"]
    end

    subgraph "Data Layer — VERIFIED COUNTS"
        ComplaintsDB[("automotive_complaints.db\n843 MB PRIMARY\n562K complaints FTS5\n211K TSBs\n7,166 recalls\n5,329 investigations\n49,806 EPA vehicles\n17,774 Canada recalls")]
        DiagnosticsDB[("automotive_diagnostics.db\n1.1 MB SECONDARY\n34,394 vehicles 1984–2026 145 makes\n3,073 DTC codes\n48 diagnosis history\n0 failure_patterns ⚠️")]
        ChromaDB[("ChromaDB Vector Store\ndata/vector_store/chroma/\nmechanics_forum collection\n561,254 docs · 18 channels")]
    end

    subgraph "AI Tier"
        Claude["Claude Sonnet 4.6 1M\nArchitect / Safety-Critical\nStrategic decisions"]
        Gemini["Gemini 2.5 Flash/Pro\nTactical / Boilerplate\nImplementation"]
        Haiku["Claude Haiku 4.5\nLow-effort agent tasks"]
    end

    User --> NextUI
    NextUI -->|"API proxy routes\n/api/*"| API
    API --> Auth
    Auth --> EngineAgent
    EngineAgent --> SymptomMatcher
    EngineAgent --> ConfidenceScorer
    EngineAgent --> AlertSystem
    EngineAgent --> TrendAnalyzer
    EngineAgent --> MainSkill
    MainSkill --> RouterSkill
    RouterSkill --> EngineSkill & TransSkill & ElecSkill & ChassisSkill
    EngineAgent -->|"DiagnosticDB wrapper\nsrc/data/db_service.py"| ComplaintsDB
    EngineAgent -->|"vehicle lookup\nDTC codes"| DiagnosticsDB
    EngineAgent -->|"forum semantic search\nchroma_service.py"| ChromaDB
    Claude -->|"delegates tactical"| Gemini
    Claude -->|"delegates low-effort"| Haiku

    style ComplaintsDB fill:#4ecdc4
    style DiagnosticsDB fill:#f9ca24
    style ChromaDB fill:#f9ca24
    style AlertSystem fill:#ff6b6b
    style Claude fill:#4ecdc4
    style Gemini fill:#95e1d3
    style Haiku fill:#95e1d3
```

---

## 2. Both Databases — Schema & Relationships

```mermaid
graph TB
    subgraph "automotive_complaints.db  843 MB  PRIMARY"
        direction TB
        CF["complaints_fts\n562,667 rows FTS5\nmake · model · year\ncomponent · summary"]
        NT["nhtsa_tsbs\n211,640 rows\nbulletin_no · make · model\nyear · component · summary"]
        NR["nhtsa_recalls\n7,166 rows\ncampaign_no · make · model\nyear_from/to · summary\nremedy · park_it flag"]
        NI["nhtsa_investigations\n5,329 rows\naction_no · make · model\ncomponent · summary"]
        CR["canada_recalls\n17,774 rows"]
        EV["epa_vehicles\n49,806 rows\nyears 1984–2026\n44 makes"]
        PC["processed_complaints\n1,564,487 rows\nraw NHTSA flat file"]
        TF["tsbs_fts  FTS5 mirror of nhtsa_tsbs"]
        RF["recalls_fts  FTS5 mirror of nhtsa_recalls"]
        NT --> TF
        NR --> RF
        CF -.->|"source data"| PC
    end

    subgraph "automotive_diagnostics.db  1.1 MB  SECONDARY"
        direction TB
        VH["vehicles\n792 rows\n⚠️ 2005 ONLY — gap\nshould be 49K rows 1984–2026"]
        DC["dtc_codes\n3,073 rows\nP/C/B/U codes\nFTS5 enabled"]
        FP["failure_patterns\n0 rows ⚠️ empty\ncommon failure library"]
        DH["diagnosis_history\n48 rows\nper-session records"]
        VF["vehicle_failures  junction"]
        VR["vehicle_recalls  junction"]
        VT["vehicle_tsbs  junction"]
        VH --> VF & VR & VT
        FP --> VF
    end

    subgraph "ChromaDB  data/vector_store/chroma/"
        MF["mechanics_forum collection\n561,254 docs · 18 YT channels\n547 videos ingested 2026-03-27\nbulk_ingest.py"]
    end

    subgraph "Backup — database/backups/"
        BK["Rotating backups\nkeep last 5 sets\n~845 MB per set\nscripts/backup_databases.py"]
    end

    style VH fill:#ff6b6b
    style FP fill:#ff6b6b
    style MF fill:#f9ca24
    style BK fill:#4ecdc4
```

---

## 3. Query Routing — Request to Response

```mermaid
flowchart TD
    Q["User Query\nVehicle + Symptoms + optional DTC"]

    Q --> V["Validate DTC\n^[PCBU][0-3][0-9A-F]{3}$"]
    V --> R["Router Skill\nclassify system P/C/B/U"]

    R --> S1["Symptom Matcher\nmap symptoms → NHTSA components"]
    R --> S2["FTS5 Search\ncomplaints_fts + tsbs_fts"]
    R --> S3["Vector Search\nChromaDB forum data"]
    R --> S4["Recall Lookup\nnhtsa_recalls by make/model/year"]

    S1 & S2 & S3 & S4 --> CS["Confidence Scorer\nbase score × vehicle match bonus"]

    CS --> SC{"Safety-Critical\nSystem?"}
    SC -->|"brakes/airbag/steering"| GT{"Confidence\n≥ 0.9?"}
    SC -->|"non-safety"| OUT

    GT -->|"yes"| OUT["Build Response\nSpecialized Skill"]
    GT -->|"no"| WARN["⚠️ WARN: insufficient\nevidence for safety system"]

    OUT --> ATTR["Source Attribution\nNHTSA / TSB / Forum / Recall"]
    ATTR --> DISC["DISCLAIMER block\nASE format output"]

    style SC fill:#ff6b6b
    style GT fill:#ff6b6b
    style WARN fill:#e74c3c,color:#fff
```

---

## 4. Data Ingestion Pipeline

```mermaid
flowchart LR
    subgraph "Sources"
        N1["NHTSA API\napi.nhtsa.gov\nno key required"]
        N2["NHTSA Flat Files\nFLAT_CMPL.txt 1.4 GB\ndata/raw_imports/"]
        N3["YouTube Transcripts\nbulk_ingest.py\nPhase 1: transcript only\nPhase 2: worstaudio fallback"]
        N4["EPA FuelEconomy\nvehicles.csv 1984–2026\ndata/raw_imports/epa/"]
        N5["Canada Recalls\ndata/raw_imports/canada/"]
    end

    subgraph "Guardrails"
        DG["Disk Check\nabort if < 5 GB free\nscripts/bulk_ingest.py\nscripts/ingest_url.py"]
        BK["Backup First\nscripts/backup_databases.py\nverify row counts\nkeep 5 rotated sets"]
    end

    subgraph "Import Scripts — scripts/"
        I1["import_nhtsa_recalls_api.py\n→ automotive_complaints.db\nnhtsa_recalls table\ncheckpoint resume"]
        I2["import_complaints_full.py\n→ automotive_complaints.db\nprocessed_complaints\ncomplaints_fts"]
        I3["bulk_ingest.py\n→ ChromaDB\nmechanics_forum collection\n18 curated YT channels"]
        I4["import_epa_vehicles.py\n→ automotive_diagnostics.db\nvehicles table\n⚠️ currently only 2005 imported"]
        I5["import_canada_recalls.py\n→ automotive_complaints.db\ncanada_recalls table"]
    end

    subgraph "Target DBs"
        CD[("automotive_complaints.db\nPRIMARY")]
        DD[("automotive_diagnostics.db\nSECONDARY")]
        CH[("ChromaDB\nVector Store")]
    end

    N1 --> DG --> BK --> I1 --> CD
    N2 --> DG --> BK --> I2 --> CD
    N3 --> DG --> I3 --> CH
    N4 --> DG --> BK --> I4 --> DD
    N5 --> DG --> BK --> I5 --> CD

    style DG fill:#ff6b6b
    style BK fill:#4ecdc4
    style CD fill:#4ecdc4
    style DD fill:#f9ca24
    style CH fill:#f9ca24
```

---

## 5. Data Freshness & Known Gaps

```mermaid
graph LR
    subgraph "CURRENT STATE — 2026-03-27"
        G1["✅ nhtsa_recalls\n7,166 rows\nlast import: 2026-03-27\n43 makes · 2000–2026"]
        G2["✅ nhtsa_tsbs\n211,640 rows\nNHTSA flat file import"]
        G3["✅ complaints_fts\n562,667 rows\nNHTSA complaints FTS5"]
        G4["✅ epa_vehicles\n49,806 rows\n1984–2026 in complaints.db"]
        G5["✅ vehicles table\n34,394 rows · 1984–2026\n145 makes · migrated 2026-03-26"]
        G6["⚠️ failure_patterns\n0 rows · empty\ndiagnostics.db"]
        G7["✅ ChromaDB\n561,254 docs · 18 channels\n547 videos ingested 2026-03-27"]
        G8["✅ Weekly cron\nnhtsa-recall-refresh.timer\nSun 03:00 UTC"]
    end

    style G1 fill:#4ecdc4
    style G2 fill:#4ecdc4
    style G3 fill:#4ecdc4
    style G4 fill:#4ecdc4
    style G5 fill:#ff6b6b
    style G6 fill:#ff6b6b
    style G7 fill:#f9ca24
    style G8 fill:#f9ca24
```

---

## 6. Agent Orchestration & Model Tiers

```mermaid
graph TD
    Task["Incoming Task"]

    Task --> T1{"Task complexity?"}

    T1 -->|"Low effort\nboilerplate/docs/lookup"| HA["Haiku 4.5\nor Gemini MCP\nFast · cheap"]
    T1 -->|"Standard"| SO["Sonnet 4.6 1M\nDefault ceiling\nAll standard work"]
    T1 -->|"Explicit opus request"| OP["Opus 4.6\nOnly when user says so"]

    SO --> AG{"Agent type needed?"}

    AG -->|"Security review"| SE["security-engineer"]
    AG -->|"Bug investigation"| RC["root-cause-analyst"]
    AG -->|"Architecture"| SA["system-architect"]
    AG -->|"Data/SQL"| DE["data-engineer"]
    AG -->|"Testing"| QE["quality-engineer"]
    AG -->|"Frontend"| FA["frontend-architect"]
    AG -->|"Backend"| BA["backend-architect"]
    AG -->|"Writing"| TW["technical-writer"]

    SO -->|"Safety-critical\nautomotive logic"| CL["Claude NEVER delegates\nautomotive safety decisions\nconfidence scoring\nrecall/TSB interpretation"]

    style CL fill:#ff6b6b
    style HA fill:#95e1d3
    style SO fill:#4ecdc4
    style OP fill:#f9ca24
```

---

## 7. Backup & Safety Infrastructure

```mermaid
flowchart TD
    T["Any import / schema change"]

    T --> PRE["Pre-flight checks\n1. git status — must be on feature branch\n2. backup_databases.py — verify both DBs\n3. disk check — abort if < 5 GB free\n4. baseline tests pass"]

    PRE --> OP["Run operation\nINSERT OR IGNORE / upsert only\nNEVER DROP TABLE\nNEVER DELETE without WHERE"]

    OP --> POST["Post-flight checks\n1. row count ≥ pre-count\n2. spot-check query\n3. run baseline tests"]

    POST --> OK{"All checks\npassed?"}

    OK -->|"yes"| CM["Commit + tag\ngit tag v1.X-feature"]
    OK -->|"no"| RB["ROLLBACK\nrestore from backup\ngit reset to last tag"]

    subgraph "Backup Rotation — database/backups/"
        B1["2026-03-26T04-22-37/\nautomotive_complaints.db 843MB\nautomotive_diagnostics.db 1MB"]
        B2["... up to 5 sets kept ..."]
        B3["Oldest auto-deleted\nwhen 6th backup created"]
    end

    CM --> B1

    style PRE fill:#4ecdc4
    style RB fill:#e74c3c,color:#fff
    style OP fill:#f9ca24
```

---

## 8. File Structure

```mermaid
graph TB
    Root["automotive-diagnostic-skills/"]

    Root --> CL[".claude/\nagent framework\nhooks · docs · skills"]
    Root --> SK["skills/\nSKILL.md master protocol\nrouter/engine/trans/elec/chassis"]
    Root --> SRC["src/\ndiagnostic/ · data/ · safety/ · analysis/\nfrontend/ Next.js :3000"]
    Root --> SRV["server/\nhome_server.py FastAPI :8000"]
    Root --> DB["database/\nautomotive_complaints.db 843MB PRIMARY\nautomotive_diagnostics.db 1.1MB SECONDARY\nbackups/ rotating 5 sets"]
    Root --> DAT["data/\nraw_imports/ ⚠️ NEVER MODIFY\nvector_store/chroma/ ChromaDB\nservice_manuals/"]
    Root --> SCR["scripts/\nbackup_databases.py ← run before any import\nimport_nhtsa_recalls_api.py\nimport_epa_vehicles.py\nbulk_ingest.py · ingest_url.py"]
    Root --> TST["tests/\nunit/ · integration/\n280 Python · 142 Vitest · 42 Playwright"]

    CL --> CD[".claude/docs/\nDIAGRAMS.md ← YOU ARE HERE\nARCHITECT.md · DOMAIN.md\nDATA.md · TESTING.md\nAGENTS.md · HOOKS.md"]

    style DB fill:#4ecdc4
    style DAT fill:#f9ca24
    style CD fill:#95e1d3
    style SCR fill:#4ecdc4
```

---

## Quick Reference for Agents

| Need to know | Go to |
|---|---|
| System overview | Diagram 1 |
| Exact DB table names + row counts | Diagram 2 |
| How a query gets answered | Diagram 3 |
| How data gets into the system | Diagram 4 |
| What's current vs broken | Diagram 5 |
| Which model/agent to use | Diagram 6 |
| Before touching the DB | Diagram 7 |
| File locations | Diagram 8 |

**Critical rules for any agent touching data:**
1. Run `scripts/backup_databases.py` before any import
2. Never use `DROP TABLE` — use `INSERT OR IGNORE` / upsert
3. Never write to `data/raw_imports/`
4. Always verify row counts after import (post ≥ pre)
5. Check disk: abort if < 5 GB free
