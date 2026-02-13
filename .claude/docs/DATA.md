# Data Source Standards

## NEVER MODIFY Rule

**CRITICAL**: Files in `data/raw_imports/` are **IMMUTABLE**

```python
# ⛔ NEVER DO THIS
with open('data/raw_imports/Common_Automotive_failures.md', 'w') as f:
    f.write(modified_content)  # VIOLATION

# ✅ CORRECT APPROACH
# 1. Read from raw_imports
with open('data/raw_imports/Common_Automotive_failures.md', 'r') as f:
    raw_data = f.read()

# 2. Process data
processed_data = transform(raw_data)

# 3. Write to processed/
with open('data/processed/failures_processed.json', 'w') as f:
    json.dump(processed_data, f)
```

---

## Data Directory Structure

```
data/
├── raw_imports/              # ⛔ NEVER MODIFY - Original sources
│   ├── Common_Automotive_failures.md
│   ├── OBD_II_Diagnostic_Codes.txt
│   ├── FLAT_CMPL.txt         # NHTSA complaints (raw)
│   └── forum_data/           # Reddit, Stack Exchange
│       ├── stackexchange_mechanics_2015.json
│       ├── stackexchange_mechanics_2016.json
│       └── ... (2015-2025)
├── service_manuals/          # iFixit JSON (can modify)
│   ├── Car and Truck.json
│   └── Vehicle.json
├── processed/                # AI-ready processed documents (can modify)
│   └── diagnostic_documents.json
├── vector_store/chroma/      # ChromaDB (generated, can rebuild)
└── scraped/                  # Scraped data (can modify)
    ├── reddit_raw.json
    ├── reddit_filtered.json
    └── quality_report.json
```

---

## Data Source Hierarchy

### Tier 1: Official Data (HIGH confidence)
- **NHTSA Complaints** (`nhtsa_complaints` table) - 2.1M records
- **NHTSA TSBs** (`nhtsa_tsbs` table) - 211K records
- **EPA Vehicles** (`vehicles` table) - 18K records
- **OBD-II Codes** (`dtc_codes` table) - 270 codes

**Confidence**: 0.9 (HIGH)
**Source**: Government databases, manufacturer bulletins

### Tier 2: Curated Data (MEDIUM confidence)
- **Common Failures** (`failure_patterns` table) - 65 patterns
- **Service Manuals** (iFixit JSON) - Repair procedures

**Confidence**: 0.7 (MEDIUM)
**Source**: Professional repair databases, verified manuals

### Tier 3: Community Data (LOW confidence)
- **Reddit Posts** (ChromaDB) - Filtered discussions
- **Stack Exchange** (ChromaDB) - Mechanics Q&A

**Confidence**: 0.5 (LOW)
**Source**: User-generated content, anecdotal

---

## Data Processing Pipeline

### 1. Import (Raw → Database)

**Scripts** (in `database/`):
- `init_database_simple.py` - Create schema
- `import_vehicles.py` - Load EPA vehicles
- `import_dtc_codes.py` - Load OBD-II codes
- `import_failure_data.py` - Load common failures
- `import_nhtsa_complaints.py` - Load 2.1M complaints (scripts/)
- `import_tsbs.py` - Load 211K TSBs (scripts/)

**Rule**: Import scripts READ from `data/raw_imports/`, WRITE to `database/automotive_diagnostics.db`

### 2. Process (Raw → Processed)

**Not yet implemented** - Future pipeline:
- Text normalization
- Entity extraction
- Embedding generation

**Output**: `data/processed/` (JSON files for AI consumption)

### 3. Index (Processed → Vector DB)

**ChromaDB** (`data/vector_store/chroma/`):
- Forum discussions embedded for semantic search
- Can be rebuilt from raw data if corrupted

---

## Data Validation

**Before importing data**:
1. Validate file exists in `data/raw_imports/`
2. Check file integrity (size > 0, valid format)
3. Verify schema matches expected structure
4. Log import statistics

**Example**:
```python
def validate_import_file(file_path: Path) -> bool:
    """Validate file before import."""
    if not file_path.exists():
        logger.error(f"File not found: {file_path}")
        return False

    if file_path.stat().st_size == 0:
        logger.error(f"File is empty: {file_path}")
        return False

    # Additional validation...
    return True
```

---

## Data Source Attribution

**When citing data in diagnostics**:

```python
def format_source_attribution(source_type: str, record_id: int) -> str:
    """Format source citation for diagnostics."""
    sources = {
        'nhtsa_complaint': f"NHTSA Complaint #{record_id}",
        'nhtsa_tsb': f"TSB #{record_id}",
        'failure_pattern': f"Known Failure Pattern #{record_id}",
        'forum_post': f"Community Discussion (ID: {record_id})"
    }
    return sources.get(source_type, f"Unknown Source ({record_id})")
```

**Always include**:
- Source type (NHTSA/TSB/Forum)
- Confidence level (HIGH/MEDIUM/LOW)
- Record ID for traceability
