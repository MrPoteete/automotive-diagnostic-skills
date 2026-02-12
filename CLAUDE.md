# Automotive Diagnostic System

## Project Context
- **Type**: Automotive Diagnostic AI System using RAG (Retrieval-Augmented Generation)
- **Purpose**: Help professional mechanics diagnose Ford/GM/RAM vehicles (2015-2025)
- **User**: Professional mechanic, non-programmer
- **Safety Critical**: Incorrect diagnoses can affect vehicle safety
- **Language**: Python 3.11+
- **Data**: JSON for structured data, Markdown for docs
- **AI/ML**: Vector embeddings, semantic search, RAG pipeline

## Project Structure
```
automotive-diagnostic-skills/
├── data/
│   ├── raw_imports/              NEVER MODIFY - Original source files
│   ├── service_manuals/          iFixit repair procedures (JSON)
│   └── knowledge_base/           Processed data for AI
├── src/                          Application code
├── tests/                        Unit and integration tests
└── docs/                         Documentation
```

## Automotive Domain Rules

### OBD-II Code Validation
Valid DTC pattern: `^[PCBU][0-3][0-9A-F]{3}$`
- P = Powertrain, C = Chassis, B = Body, U = Network
- Always validate codes against this pattern before processing

### Safety-Critical Systems
These require confidence >= 0.9 and explicit warnings:
- Braking: brake, abs
- Restraints: airbag, srs
- Steering: steering, eps
- Power: tipm, throttle, pedal, fuel_pump

### Confidence Scoring
Source reliability:
- HIGH (0.9): NHTSA recalls, class action settlements, verified TSBs
- MEDIUM (0.7): TSBs, active class actions, manufacturer bulletins
- LOW (0.5): Forum reports, unverified claims

Vehicle match adjustments:
- Exact (make/model/year/engine): +0.1
- Make/model/year: +0.05
- Make/model: +0.0
- Make only: -0.1

### Vehicle Coverage (MVP)
- **Ford**: F-150, Explorer, Mustang, Focus, Fusion
- **GM**: Silverado, Tahoe, Impala, Malibu, Cruze
- **RAM**: 1500, 2500, Journey, Grand Cherokee
- **Years**: 2015-2025

## Data Source Standards
All failure patterns must include: source attribution, confidence level, affected vehicles, and repair cost range when available. Prefer NHTSA data over forum reports.

## Testing
- diagnostic_engine and safety_systems: 100% coverage
- obd_parser and confidence_scoring: 90% coverage
- general utilities: 80% coverage
- Use pytest with AAA pattern (Arrange-Act-Assert)

## Key Rules
1. Always provide complete, runnable code with full file paths
2. Validate all external input (especially DTC codes)
3. Flag safety-critical systems with warnings
4. Include source attribution for all diagnostic data
5. Ask for clarification when requirements are ambiguous or safety implications are unclear
