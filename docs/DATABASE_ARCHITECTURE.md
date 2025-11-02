# Database Architecture

**Database System**: SQLite 3.x
**Schema Version**: 1.0
**Last Updated**: November 2, 2025

---

## Overview

The Automotive Diagnostic Skills system uses a SQLite database to manage
vehicle configurations, diagnostic trouble codes, failure patterns, and
repair procedures. The database is designed to handle 22,800+ vehicle
configurations spanning 20 years while maintaining sub-50ms query performance.

### Design Principles

- **Single Responsibility**: Each table has a focused purpose
- **Referential Integrity**: Foreign key constraints enforce data consistency
- **Performance First**: 28 optimized indexes for fast queries
- **Full-Text Search**: FTS5 virtual tables for symptom-based searches
- **Scalability**: Designed for 500-600 MB with 22,800+ vehicles

---

## Database Schema

### Schema Statistics
- **Total Tables**: 33
- **Indexes**: 28
- **Foreign Key Constraints**: 15+
- **Full-Text Search Tables**: 3
- **Views**: Multiple (for common queries)

---

## Core Tables

### 1. Vehicles Table

**Purpose**: Store vehicle configurations (make, model, year, engine)

```sql
CREATE TABLE vehicles (
    vehicle_id INTEGER PRIMARY KEY AUTOINCREMENT,
    make TEXT NOT NULL,
    model TEXT NOT NULL,
    year INTEGER NOT NULL,
    engine TEXT NOT NULL,
    displacement_liters REAL,
    cylinders INTEGER,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(make, model, year, engine)
);
```

**Indexes**:
```sql
CREATE INDEX idx_vehicles_make_model ON vehicles(make, model);
CREATE INDEX idx_vehicles_year ON vehicles(year);
CREATE INDEX idx_vehicles_engine ON vehicles(engine);
```

**Key Features**:
- UNIQUE constraint prevents duplicate vehicle configurations
- Supports displacement and cylinder count for engine specifications
- Optimized for lookups by make/model and year range queries

**Example Data**:
| vehicle_id | make | model | year | engine | displacement_liters | cylinders |
|------------|------|-------|------|--------|---------------------|-----------|
| 1 | FORD | F-150 | 2005 | 5.4L V8 | 5.4 | 8 |
| 2 | TOYOTA | Camry | 2005 | 2.4L 4-Cyl | 2.4 | 4 |

---

### 2. DTC Codes Table

**Purpose**: Store OBD-II diagnostic trouble codes

```sql
CREATE TABLE dtc_codes (
    code_id INTEGER PRIMARY KEY AUTOINCREMENT,
    code TEXT UNIQUE NOT NULL,
    system TEXT NOT NULL,
    description TEXT NOT NULL,
    severity TEXT CHECK(severity IN ('LOW', 'MEDIUM', 'HIGH', 'CRITICAL')),
    safety_critical INTEGER DEFAULT 0,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);
```

**Indexes**:
```sql
CREATE INDEX idx_dtc_system ON dtc_codes(system);
CREATE INDEX idx_dtc_severity ON dtc_codes(severity);
CREATE INDEX idx_dtc_safety ON dtc_codes(safety_critical) WHERE safety_critical = 1;
```

**Key Features**:
- Severity classification for prioritization
- Safety-critical flag for urgent issues
- System categorization (Powertrain, Chassis, Body, Network)

**Example Data**:
| code_id | code | system | description | severity | safety_critical |
|---------|------|--------|-------------|----------|-----------------|
| 1 | P0300 | Powertrain | Random/Multiple Cylinder Misfire Detected | HIGH | 0 |
| 2 | C0561 | Chassis | System Disabled Information Stored | CRITICAL | 1 |

---

### 3. Failure Patterns Table

**Purpose**: Store common automotive failure patterns with diagnostic information

```sql
CREATE TABLE failure_patterns (
    failure_id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    category TEXT NOT NULL,
    symptom_description TEXT,
    root_cause TEXT,
    confidence TEXT CHECK(confidence IN ('LOW', 'MEDIUM', 'HIGH')),
    frequency TEXT CHECK(frequency IN ('RARE', 'OCCASIONAL', 'COMMON', 'VERY_COMMON')),
    safety_critical INTEGER DEFAULT 0,
    estimated_repair_time_hours REAL,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);
```

**Indexes**:
```sql
CREATE INDEX idx_failures_category ON failure_patterns(category);
CREATE INDEX idx_failures_confidence ON failure_patterns(confidence);
CREATE INDEX idx_failures_safety ON failure_patterns(safety_critical) WHERE safety_critical = 1;
```

**Full-Text Search**:
```sql
CREATE VIRTUAL TABLE failure_patterns_fts USING fts5(
    name,
    symptom_description,
    root_cause,
    content='failure_patterns',
    content_rowid='failure_id'
);
```

**Key Features**:
- Confidence ratings for diagnostic accuracy
- Frequency data for probability assessment
- Safety-critical flagging
- Full-text search on symptoms and root causes

**Example Data**:
| failure_id | name | category | symptom_description | confidence | frequency |
|------------|------|----------|---------------------|------------|-----------|
| 1 | Ignition Coil Failure | Engine | Rough idle, misfiring, lack of power | HIGH | COMMON |
| 2 | Mass Air Flow Sensor | Engine | Stalling, poor acceleration | MEDIUM | OCCASIONAL |

---

### 4. Parts Table

**Purpose**: Catalog parts required for repairs

```sql
CREATE TABLE parts (
    part_id INTEGER PRIMARY KEY AUTOINCREMENT,
    part_number TEXT UNIQUE NOT NULL,
    part_name TEXT NOT NULL,
    category TEXT NOT NULL,
    manufacturer TEXT,
    estimated_cost REAL,
    notes TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);
```

**Indexes**:
```sql
CREATE INDEX idx_parts_category ON parts(category);
CREATE INDEX idx_parts_manufacturer ON parts(manufacturer);
```

**Key Features**:
- Universal part numbers
- Cost estimation for quotes
- Manufacturer tracking for OEM vs aftermarket

---

### 5. Diagnostic Tests Table

**Purpose**: Store step-by-step diagnostic procedures

```sql
CREATE TABLE diagnostic_tests (
    test_id INTEGER PRIMARY KEY AUTOINCREMENT,
    test_name TEXT NOT NULL,
    category TEXT NOT NULL,
    description TEXT,
    required_tools TEXT,
    estimated_time_minutes INTEGER,
    difficulty TEXT CHECK(difficulty IN ('BASIC', 'INTERMEDIATE', 'ADVANCED', 'PROFESSIONAL')),
    safety_warnings TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);
```

**Key Features**:
- Difficulty ratings for skill assessment
- Tool requirements for preparation
- Safety warnings for hazardous procedures

---

### 6. Service Procedures Table

**Purpose**: Link to MyFixit repair manuals

```sql
CREATE TABLE service_procedures (
    procedure_id INTEGER PRIMARY KEY AUTOINCREMENT,
    procedure_name TEXT NOT NULL,
    category TEXT NOT NULL,
    json_file_path TEXT,
    description TEXT,
    estimated_time_hours REAL,
    difficulty TEXT CHECK(difficulty IN ('BASIC', 'INTERMEDIATE', 'ADVANCED', 'PROFESSIONAL')),
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);
```

**Key Features**:
- Links to existing JSON-based manuals
- Time estimates for labor quotes
- Difficulty assessment

---

### 7. Technical Service Bulletins (TSBs) Table

**Purpose**: Store manufacturer technical service bulletins

```sql
CREATE TABLE tsbs (
    tsb_id INTEGER PRIMARY KEY AUTOINCREMENT,
    tsb_number TEXT UNIQUE NOT NULL,
    manufacturer TEXT NOT NULL,
    issue_date TEXT,
    title TEXT NOT NULL,
    summary TEXT,
    affected_systems TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);
```

**Key Features**:
- Manufacturer-specific bulletins
- Issue tracking by date
- System categorization

---

### 8. Recalls Table

**Purpose**: Track NHTSA safety recalls

```sql
CREATE TABLE recalls (
    recall_id INTEGER PRIMARY KEY AUTOINCREMENT,
    recall_number TEXT UNIQUE NOT NULL,
    manufacturer TEXT NOT NULL,
    recall_date TEXT,
    component TEXT NOT NULL,
    summary TEXT,
    consequence TEXT,
    remedy TEXT,
    safety_critical INTEGER DEFAULT 1,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);
```

**Key Features**:
- Safety recall tracking
- Component and consequence documentation
- Remedy procedures

---

## Relationship Tables (Many-to-Many)

### 1. Vehicle-Failure Relationships

```sql
CREATE TABLE vehicle_failures (
    vehicle_id INTEGER NOT NULL,
    failure_id INTEGER NOT NULL,
    frequency_rating INTEGER,
    notes TEXT,
    FOREIGN KEY (vehicle_id) REFERENCES vehicles(vehicle_id),
    FOREIGN KEY (failure_id) REFERENCES failure_patterns(failure_id),
    PRIMARY KEY (vehicle_id, failure_id)
);
```

**Purpose**: Link specific vehicles to common failure patterns

---

### 2. DTC-Failure Correlations

```sql
CREATE TABLE dtc_failure_correlations (
    code_id INTEGER NOT NULL,
    failure_id INTEGER NOT NULL,
    correlation_strength REAL CHECK(correlation_strength BETWEEN 0.0 AND 1.0),
    notes TEXT,
    FOREIGN KEY (code_id) REFERENCES dtc_codes(code_id),
    FOREIGN KEY (failure_id) REFERENCES failure_patterns(failure_id),
    PRIMARY KEY (code_id, failure_id)
);
```

**Index**:
```sql
CREATE INDEX idx_dtc_correlations_strength
  ON dtc_failure_correlations(correlation_strength DESC);
```

**Purpose**: Link DTCs to probable failure patterns with confidence scores

**Example**:
- Code P0300 (Random Misfire) → Ignition Coil Failure (correlation: 0.85)
- Code P0300 (Random Misfire) → Spark Plug Fouling (correlation: 0.70)

---

### 3. Failure-Parts Relationships

```sql
CREATE TABLE failure_parts (
    failure_id INTEGER NOT NULL,
    part_id INTEGER NOT NULL,
    quantity INTEGER DEFAULT 1,
    required INTEGER DEFAULT 1,
    FOREIGN KEY (failure_id) REFERENCES failure_patterns(failure_id),
    FOREIGN KEY (part_id) REFERENCES parts(part_id),
    PRIMARY KEY (failure_id, part_id)
);
```

**Purpose**: Link failure patterns to required repair parts

---

### 4. Vehicle-Procedure Relationships

```sql
CREATE TABLE vehicle_procedures (
    vehicle_id INTEGER NOT NULL,
    procedure_id INTEGER NOT NULL,
    notes TEXT,
    FOREIGN KEY (vehicle_id) REFERENCES vehicles(vehicle_id),
    FOREIGN KEY (procedure_id) REFERENCES service_procedures(procedure_id),
    PRIMARY KEY (vehicle_id, procedure_id)
);
```

**Purpose**: Link vehicles to applicable service procedures

---

### 5. Vehicle-TSB Relationships

```sql
CREATE TABLE vehicle_tsbs (
    vehicle_id INTEGER NOT NULL,
    tsb_id INTEGER NOT NULL,
    applies_to_vin_range TEXT,
    FOREIGN KEY (vehicle_id) REFERENCES vehicles(vehicle_id),
    FOREIGN KEY (tsb_id) REFERENCES tsbs(tsb_id),
    PRIMARY KEY (vehicle_id, tsb_id)
);
```

**Purpose**: Link vehicles to applicable technical service bulletins

---

### 6. Vehicle-Recall Relationships

```sql
CREATE TABLE vehicle_recalls (
    vehicle_id INTEGER NOT NULL,
    recall_id INTEGER NOT NULL,
    vin_range TEXT,
    completion_status TEXT,
    FOREIGN KEY (vehicle_id) REFERENCES vehicles(vehicle_id),
    FOREIGN KEY (recall_id) REFERENCES recalls(recall_id),
    PRIMARY KEY (vehicle_id, recall_id)
);
```

**Purpose**: Link vehicles to applicable safety recalls

---

## Full-Text Search Implementation

### FTS5 Virtual Tables

The database implements full-text search using SQLite's FTS5 extension:

1. **Vehicles FTS**:
```sql
CREATE VIRTUAL TABLE vehicles_fts USING fts5(
    make, model, engine,
    content='vehicles',
    content_rowid='vehicle_id'
);
```

2. **DTC Codes FTS**:
```sql
CREATE VIRTUAL TABLE dtc_codes_fts USING fts5(
    code, description,
    content='dtc_codes',
    content_rowid='code_id'
);
```

3. **Failure Patterns FTS**:
```sql
CREATE VIRTUAL TABLE failure_patterns_fts USING fts5(
    name, symptom_description, root_cause,
    content='failure_patterns',
    content_rowid='failure_id'
);
```

### Search Examples

**Search by symptom**:
```sql
SELECT f.* FROM failure_patterns f
JOIN failure_patterns_fts fts ON f.failure_id = fts.rowid
WHERE fts.failure_patterns_fts MATCH 'rough idle cold start'
ORDER BY f.confidence DESC;
```

**Search by vehicle**:
```sql
SELECT v.* FROM vehicles v
JOIN vehicles_fts fts ON v.vehicle_id = fts.rowid
WHERE fts.vehicles_fts MATCH 'ford f150 5.4'
ORDER BY v.year DESC;
```

---

## Query Optimization

### Index Strategy

1. **Primary Indexes**: Automatically created on PRIMARY KEY columns
2. **Foreign Key Indexes**: Created on all FK columns for join performance
3. **Lookup Indexes**: Created on frequently queried columns (make, model, year)
4. **Composite Indexes**: Created for multi-column WHERE clauses
5. **Partial Indexes**: Created for filtered queries (e.g., safety_critical = 1)

### Query Performance Targets

| Query Type | Target Performance | Example |
|------------|-------------------|---------|
| Simple Lookup | 1-5ms | Find vehicle by make/model/year |
| Complex Join | 10-50ms | Find failures by DTC code |
| Full-Text Search | 50-200ms | Search symptoms |
| Aggregate Query | 50-100ms | Count vehicles by manufacturer |

---

## Data Integrity

### Foreign Key Constraints

Foreign keys are enforced to maintain referential integrity:

```sql
PRAGMA foreign_keys = ON;
```

**Cascade Rules**:
- `ON DELETE CASCADE`: Delete related records when parent is deleted
- `ON DELETE RESTRICT`: Prevent deletion if child records exist

### Check Constraints

Data validation via CHECK constraints:

```sql
-- Severity must be valid value
CHECK(severity IN ('LOW', 'MEDIUM', 'HIGH', 'CRITICAL'))

-- Correlation must be between 0.0 and 1.0
CHECK(correlation_strength BETWEEN 0.0 AND 1.0)

-- Difficulty must be valid value
CHECK(difficulty IN ('BASIC', 'INTERMEDIATE', 'ADVANCED', 'PROFESSIONAL'))
```

### Unique Constraints

Prevent duplicate data:

```sql
-- Prevent duplicate vehicles
UNIQUE(make, model, year, engine)

-- Prevent duplicate DTC codes
UNIQUE(code)

-- Prevent duplicate part numbers
UNIQUE(part_number)
```

---

## Database Maintenance

### Vacuum Operation

Reclaim unused space and defragment:

```sql
VACUUM;
```

**Recommended Frequency**: After bulk deletes or updates

### Integrity Check

Verify database integrity:

```sql
PRAGMA integrity_check;
```

**Recommended Frequency**: Before backup operations

### Optimize

Update table statistics for query optimization:

```sql
ANALYZE;
```

**Recommended Frequency**: After bulk imports

---

## Backup and Recovery

### Backup Strategy

1. **SQLite Backup API**: Use `.backup` command
   ```sql
   .backup automotive_diagnostics_backup.db
   ```

2. **File Copy**: Copy .db file while database is not in use
   ```bash
   copy automotive_diagnostics.db automotive_diagnostics_backup.db
   ```

3. **Cloud Sync**: Automatic backup via OneDrive/Dropbox

### Recovery Process

1. Verify backup integrity:
   ```sql
   PRAGMA integrity_check;
   ```

2. Restore from backup:
   ```bash
   copy automotive_diagnostics_backup.db automotive_diagnostics.db
   ```

---

## Schema Evolution

### Version Management

```sql
CREATE TABLE schema_version (
    version TEXT PRIMARY KEY,
    applied_at TEXT DEFAULT CURRENT_TIMESTAMP,
    description TEXT
);

INSERT INTO schema_version (version, description)
VALUES ('1.0', 'Initial schema with 33 tables and 28 indexes');
```

### Migration Strategy

1. Create migration script for schema changes
2. Test migration on backup copy
3. Update schema_version table
4. Document changes in migration log

---

## Performance Considerations

### Database Size Projections

- **Empty Schema**: 0.25 MB
- **792 Vehicles (2005)**: ~1 MB
- **22,800 Vehicles (Full)**: ~500-600 MB
- **With Full Diagnostic Data**: ~500-600 MB total

### Hardware Requirements

**Minimum**:
- 1 GB RAM
- 1 GB free disk space
- Any modern Windows PC

**Recommended**:
- 4 GB RAM
- 5 GB free disk space (for backups)
- SSD storage for optimal performance

---

## Database Connection Examples

### Python Connection

```python
import sqlite3

def get_connection():
    """Create database connection with foreign keys enabled."""
    conn = sqlite3.connect('automotive_diagnostics.db')
    conn.row_factory = sqlite3.Row  # Enable column access by name
    conn.execute("PRAGMA foreign_keys = ON")
    return conn

# Usage
conn = get_connection()
cursor = conn.cursor()
cursor.execute("SELECT * FROM vehicles WHERE make = ?", ('FORD',))
for row in cursor.fetchall():
    print(f"{row['year']} {row['make']} {row['model']}")
conn.close()
```

### Context Manager Pattern

```python
from contextlib import contextmanager

@contextmanager
def database_connection():
    """Context manager for database connections."""
    conn = sqlite3.connect('automotive_diagnostics.db')
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()

# Usage
with database_connection() as conn:
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM vehicles")
    results = cursor.fetchall()
```

---

## Future Enhancements

### Planned Improvements

1. **Diagnostic History Table**: Track diagnostic sessions and outcomes
2. **Labor Rate Tables**: Store regional labor rates for quotes
3. **Customer Data**: Link vehicles to customer records (shop mode)
4. **Inventory Tracking**: Parts inventory management
5. **Warranty Tracking**: Parts and labor warranty tracking

### Scalability Considerations

- Database designed to handle 10x current projections
- Index optimization for >100,000 vehicles
- Partitioning strategy for large datasets
- Read-only replicas for multi-user access

---

## Related Documentation

- [Project Status](PROJECT_STATUS.md) - Current project status and roadmap
- [Setup Guide](SETUP_GUIDE.md) - Installation and configuration
- [README](../README.md) - Project overview

---

**Schema Version**: 1.0
**Last Review**: November 2, 2025
**Next Review**: After Phase 2 data import
