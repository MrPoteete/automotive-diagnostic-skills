-- Automotive Diagnostic System - SQLite Database Schema
-- Designed for 22,800+ vehicle configurations (2005-2025)
-- Optimized for <50ms query performance

-- ============================================================================
-- VEHICLE CONFIGURATION TABLES
-- ============================================================================

-- Core vehicle identification table
CREATE TABLE IF NOT EXISTS vehicles (
    vehicle_id INTEGER PRIMARY KEY AUTOINCREMENT,
    make TEXT NOT NULL COLLATE NOCASE,
    model TEXT NOT NULL COLLATE NOCASE,
    year INTEGER NOT NULL CHECK(year >= 2005 AND year <= 2025),
    engine TEXT,  -- Format: "3.5/6" or "3.5L V6"
    engine_displacement REAL,  -- Liters (extracted from engine field)
    engine_cylinders INTEGER,  -- Number of cylinders
    body_style TEXT,  -- "Sedan", "Truck", "SUV", etc.
    drive_type TEXT,  -- "2WD", "4WD", "AWD"
    transmission_type TEXT,  -- "Automatic", "Manual", "CVT"
    fuel_type TEXT,  -- "Gasoline", "Diesel", "Hybrid", "Electric"
    vin_pattern TEXT,  -- VIN prefix for identification
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(make, model, year, engine)
);

-- Indexes for fast vehicle lookups
CREATE INDEX IF NOT EXISTS idx_vehicles_make_model ON vehicles(make, model);
CREATE INDEX IF NOT EXISTS idx_vehicles_year ON vehicles(year);
CREATE INDEX IF NOT EXISTS idx_vehicles_make_year ON vehicles(make, year);
CREATE INDEX IF NOT EXISTS idx_vehicles_full ON vehicles(make, model, year);

-- Full-text search index for vehicle identification
CREATE VIRTUAL TABLE IF NOT EXISTS vehicles_fts USING fts5(
    make, model, year, engine, body_style,
    content='vehicles',
    content_rowid='vehicle_id'
);

-- Trigger to keep FTS index in sync
CREATE TRIGGER IF NOT EXISTS vehicles_fts_insert AFTER INSERT ON vehicles BEGIN
    INSERT INTO vehicles_fts(rowid, make, model, year, engine, body_style)
    VALUES (new.vehicle_id, new.make, new.model, new.year, new.engine, new.body_style);
END;

CREATE TRIGGER IF NOT EXISTS vehicles_fts_update AFTER UPDATE ON vehicles BEGIN
    UPDATE vehicles_fts SET
        make = new.make,
        model = new.model,
        year = new.year,
        engine = new.engine,
        body_style = new.body_style
    WHERE rowid = new.vehicle_id;
END;

CREATE TRIGGER IF NOT EXISTS vehicles_fts_delete AFTER DELETE ON vehicles BEGIN
    DELETE FROM vehicles_fts WHERE rowid = old.vehicle_id;
END;

-- ============================================================================
-- DIAGNOSTIC TROUBLE CODE (DTC) TABLES
-- ============================================================================

-- OBD-II diagnostic trouble codes
CREATE TABLE IF NOT EXISTS dtc_codes (
    code TEXT PRIMARY KEY COLLATE NOCASE,  -- "P0300", "P0335", etc.
    system TEXT NOT NULL,  -- "Powertrain", "Chassis", "Body", "Network"
    subsystem TEXT,  -- "Engine", "Transmission", "Fuel System", etc.
    description TEXT NOT NULL,
    full_description TEXT,  -- Detailed explanation
    severity TEXT CHECK(severity IN ('LOW', 'MEDIUM', 'HIGH', 'CRITICAL')),
    drivability_impact TEXT,  -- "SEVERE", "MODERATE", "MINOR", "NONE"
    emissions_impact TEXT,  -- "YES", "NO", "POSSIBLE"
    safety_critical INTEGER DEFAULT 0 CHECK(safety_critical IN (0, 1)),  -- Boolean
    standard TEXT DEFAULT 'SAE J2012',  -- Standard reference
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Indexes for DTC lookups
CREATE INDEX IF NOT EXISTS idx_dtc_system ON dtc_codes(system);
CREATE INDEX IF NOT EXISTS idx_dtc_severity ON dtc_codes(severity);
CREATE INDEX IF NOT EXISTS idx_dtc_safety ON dtc_codes(safety_critical) WHERE safety_critical = 1;

-- Full-text search for DTC descriptions
CREATE VIRTUAL TABLE IF NOT EXISTS dtc_codes_fts USING fts5(
    code, description, full_description,
    content='dtc_codes',
    content_rowid='rowid'
);

-- ============================================================================
-- FAILURE PATTERN TABLES
-- ============================================================================

-- Common failure patterns across vehicles
CREATE TABLE IF NOT EXISTS failure_patterns (
    failure_id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,  -- "CKP Sensor Failure", "AFM Lifter Collapse", etc.
    category TEXT,  -- "Engine", "Transmission", "Electrical", etc.
    symptom_description TEXT,  -- Customer-reported symptoms
    technical_description TEXT,  -- Technical explanation
    root_cause TEXT,  -- Underlying cause
    confidence TEXT CHECK(confidence IN ('HIGH', 'MEDIUM', 'LOW')) DEFAULT 'MEDIUM',
    frequency REAL CHECK(frequency >= 0 AND frequency <= 1),  -- 0.0-1.0 occurrence rate
    typical_mileage_min INTEGER,  -- Typical failure mileage range
    typical_mileage_max INTEGER,
    repair_cost_min INTEGER,  -- USD
    repair_cost_max INTEGER,
    labor_hours REAL,  -- Estimated repair time
    difficulty TEXT CHECK(difficulty IN ('Easy', 'Moderate', 'Difficult', 'Expert')),
    safety_critical INTEGER DEFAULT 0 CHECK(safety_critical IN (0, 1)),

    -- Source attribution
    source_type TEXT,  -- "NHTSA", "TSB", "Class Action", "Professional Experience"
    source_url TEXT,
    nhtsa_number TEXT,  -- Recall or complaint number
    tsb_number TEXT,  -- Technical Service Bulletin

    -- Fix information
    fix_type TEXT,  -- "Replacement", "Repair", "Reprogramming", "Adjustment"
    fix_permanence TEXT,  -- "Permanent", "Temporary", "Workaround"
    prevention_notes TEXT,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Indexes for failure pattern queries
CREATE INDEX IF NOT EXISTS idx_failures_category ON failure_patterns(category);
CREATE INDEX IF NOT EXISTS idx_failures_confidence ON failure_patterns(confidence);
CREATE INDEX IF NOT EXISTS idx_failures_safety ON failure_patterns(safety_critical) WHERE safety_critical = 1;

-- Full-text search for failure patterns
CREATE VIRTUAL TABLE IF NOT EXISTS failure_patterns_fts USING fts5(
    name, symptom_description, technical_description, root_cause,
    content='failure_patterns',
    content_rowid='failure_id'
);

-- ============================================================================
-- RELATIONSHIP TABLES (Many-to-Many Mappings)
-- ============================================================================

-- Link vehicles to failure patterns
CREATE TABLE IF NOT EXISTS vehicle_failures (
    vehicle_id INTEGER NOT NULL,
    failure_id INTEGER NOT NULL,
    applicability_notes TEXT,  -- Vehicle-specific notes
    frequency_override REAL,  -- Vehicle-specific frequency (overrides failure_patterns.frequency)
    PRIMARY KEY (vehicle_id, failure_id),
    FOREIGN KEY (vehicle_id) REFERENCES vehicles(vehicle_id) ON DELETE CASCADE,
    FOREIGN KEY (failure_id) REFERENCES failure_patterns(failure_id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_vehicle_failures_vehicle ON vehicle_failures(vehicle_id);
CREATE INDEX IF NOT EXISTS idx_vehicle_failures_failure ON vehicle_failures(failure_id);

-- Link DTCs to failure patterns (correlation)
CREATE TABLE IF NOT EXISTS dtc_failure_correlations (
    code TEXT NOT NULL COLLATE NOCASE,
    failure_id INTEGER NOT NULL,
    correlation_strength REAL NOT NULL CHECK(correlation_strength >= 0 AND correlation_strength <= 1),
    notes TEXT,  -- Why this DTC indicates this failure
    PRIMARY KEY (code, failure_id),
    FOREIGN KEY (code) REFERENCES dtc_codes(code) ON DELETE CASCADE,
    FOREIGN KEY (failure_id) REFERENCES failure_patterns(failure_id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_dtc_correlations_code ON dtc_failure_correlations(code);
CREATE INDEX IF NOT EXISTS idx_dtc_correlations_failure ON dtc_failure_correlations(failure_id);
CREATE INDEX IF NOT EXISTS idx_dtc_correlations_strength ON dtc_failure_correlations(correlation_strength DESC);

-- ============================================================================
-- PARTS AND REPAIR INFORMATION
-- ============================================================================

-- Parts catalog for repairs
CREATE TABLE IF NOT EXISTS parts (
    part_id INTEGER PRIMARY KEY AUTOINCREMENT,
    part_name TEXT NOT NULL,
    part_category TEXT,  -- "Sensor", "Module", "Mechanical", etc.
    oem_part_number TEXT,
    oem_manufacturer TEXT,
    oem_cost REAL,
    aftermarket_part_numbers TEXT,  -- JSON array of alt part numbers
    aftermarket_cost REAL,
    core_charge REAL,  -- Refundable core charge (if applicable)
    notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Link parts to failure patterns
CREATE TABLE IF NOT EXISTS failure_parts (
    failure_id INTEGER NOT NULL,
    part_id INTEGER NOT NULL,
    quantity INTEGER DEFAULT 1,
    part_role TEXT,  -- "Primary", "Secondary", "Optional"
    PRIMARY KEY (failure_id, part_id),
    FOREIGN KEY (failure_id) REFERENCES failure_patterns(failure_id) ON DELETE CASCADE,
    FOREIGN KEY (part_id) REFERENCES parts(part_id) ON DELETE CASCADE
);

-- ============================================================================
-- DIAGNOSTIC PROCEDURES
-- ============================================================================

-- Diagnostic testing procedures
CREATE TABLE IF NOT EXISTS diagnostic_tests (
    test_id INTEGER PRIMARY KEY AUTOINCREMENT,
    test_name TEXT NOT NULL,
    category TEXT,  -- "Visual", "Electrical", "Mechanical", "Software"
    purpose TEXT,  -- What the test determines
    procedure TEXT,  -- Step-by-step instructions (JSON array)
    tools_required TEXT,  -- JSON array of tools
    expected_result TEXT,  -- Pass criteria
    failure_indication TEXT,  -- Fail criteria
    estimated_time_minutes INTEGER,
    difficulty TEXT CHECK(difficulty IN ('Easy', 'Moderate', 'Difficult', 'Expert')),
    safety_warnings TEXT,  -- Important safety notes
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Link diagnostic tests to failures
CREATE TABLE IF NOT EXISTS failure_diagnostic_tests (
    failure_id INTEGER NOT NULL,
    test_id INTEGER NOT NULL,
    test_sequence INTEGER,  -- Order to perform tests
    PRIMARY KEY (failure_id, test_id),
    FOREIGN KEY (failure_id) REFERENCES failure_patterns(failure_id) ON DELETE CASCADE,
    FOREIGN KEY (test_id) REFERENCES diagnostic_tests(test_id) ON DELETE CASCADE
);

-- ============================================================================
-- SERVICE MANUALS AND PROCEDURES
-- ============================================================================

-- Service manual procedures (from MyFixit dataset)
CREATE TABLE IF NOT EXISTS service_procedures (
    procedure_id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    category TEXT,  -- "Brake", "Engine", "Transmission", etc.
    source TEXT DEFAULT 'MyFixit',  -- Data source
    source_url TEXT,
    difficulty TEXT,
    estimated_time_minutes INTEGER,
    tools_required TEXT,  -- JSON array
    steps TEXT,  -- JSON array of step-by-step instructions
    images TEXT,  -- JSON array of image URLs
    safety_warnings TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Link service procedures to vehicles
CREATE TABLE IF NOT EXISTS vehicle_procedures (
    vehicle_id INTEGER NOT NULL,
    procedure_id INTEGER NOT NULL,
    applicability_notes TEXT,
    PRIMARY KEY (vehicle_id, procedure_id),
    FOREIGN KEY (vehicle_id) REFERENCES vehicles(vehicle_id) ON DELETE CASCADE,
    FOREIGN KEY (procedure_id) REFERENCES service_procedures(procedure_id) ON DELETE CASCADE
);

-- ============================================================================
-- TSB (TECHNICAL SERVICE BULLETIN) TRACKING
-- ============================================================================

-- Technical Service Bulletins
CREATE TABLE IF NOT EXISTS tsbs (
    tsb_id INTEGER PRIMARY KEY AUTOINCREMENT,
    manufacturer TEXT NOT NULL,
    tsb_number TEXT NOT NULL,
    issue_date DATE,
    title TEXT NOT NULL,
    description TEXT,
    affected_systems TEXT,  -- "Engine", "Transmission", etc.
    symptom_keywords TEXT,  -- For search
    fix_description TEXT,
    bulletin_url TEXT,
    UNIQUE(manufacturer, tsb_number)
);

-- Link TSBs to vehicles
CREATE TABLE IF NOT EXISTS vehicle_tsbs (
    vehicle_id INTEGER NOT NULL,
    tsb_id INTEGER NOT NULL,
    PRIMARY KEY (vehicle_id, tsb_id),
    FOREIGN KEY (vehicle_id) REFERENCES vehicles(vehicle_id) ON DELETE CASCADE,
    FOREIGN KEY (tsb_id) REFERENCES tsbs(tsb_id) ON DELETE CASCADE
);

-- Link TSBs to failure patterns
CREATE TABLE IF NOT EXISTS failure_tsbs (
    failure_id INTEGER NOT NULL,
    tsb_id INTEGER NOT NULL,
    PRIMARY KEY (failure_id, tsb_id),
    FOREIGN KEY (failure_id) REFERENCES failure_patterns(failure_id) ON DELETE CASCADE,
    FOREIGN KEY (tsb_id) REFERENCES tsbs(tsb_id) ON DELETE CASCADE
);

-- ============================================================================
-- RECALLS
-- ============================================================================

-- NHTSA recalls
CREATE TABLE IF NOT EXISTS recalls (
    recall_id INTEGER PRIMARY KEY AUTOINCREMENT,
    manufacturer TEXT NOT NULL,
    nhtsa_campaign_number TEXT UNIQUE NOT NULL,
    recall_date DATE,
    component TEXT,
    summary TEXT,
    consequence TEXT,
    remedy TEXT,
    notes TEXT,
    recall_url TEXT
);

-- Link recalls to vehicles (by VIN range or year range)
CREATE TABLE IF NOT EXISTS vehicle_recalls (
    vehicle_id INTEGER NOT NULL,
    recall_id INTEGER NOT NULL,
    vin_range_start TEXT,
    vin_range_end TEXT,
    PRIMARY KEY (vehicle_id, recall_id),
    FOREIGN KEY (vehicle_id) REFERENCES vehicles(vehicle_id) ON DELETE CASCADE,
    FOREIGN KEY (recall_id) REFERENCES recalls(recall_id) ON DELETE CASCADE
);

-- ============================================================================
-- METADATA AND VERSIONING
-- ============================================================================

-- Database version and metadata
CREATE TABLE IF NOT EXISTS metadata (
    key TEXT PRIMARY KEY,
    value TEXT,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Initialize metadata
INSERT OR IGNORE INTO metadata (key, value) VALUES
    ('schema_version', '1.0'),
    ('created_date', datetime('now')),
    ('last_updated', datetime('now')),
    ('data_sources', 'Common_Automotive_failures.md, OBD_II_Diagnostic_Codes.txt, MyFixit_Dataset');

-- ============================================================================
-- VIEWS FOR COMMON QUERIES
-- ============================================================================

-- Complete vehicle diagnostic information
CREATE VIEW IF NOT EXISTS v_vehicle_diagnostics AS
SELECT
    v.vehicle_id,
    v.make,
    v.model,
    v.year,
    v.engine,
    COUNT(DISTINCT vf.failure_id) as total_known_failures,
    COUNT(DISTINCT vt.tsb_id) as total_tsbs,
    COUNT(DISTINCT vr.recall_id) as total_recalls
FROM vehicles v
LEFT JOIN vehicle_failures vf ON v.vehicle_id = vf.vehicle_id
LEFT JOIN vehicle_tsbs vt ON v.vehicle_id = vt.vehicle_id
LEFT JOIN vehicle_recalls vr ON v.vehicle_id = vr.vehicle_id
GROUP BY v.vehicle_id;

-- High-confidence failure patterns
CREATE VIEW IF NOT EXISTS v_high_confidence_failures AS
SELECT
    f.*,
    COUNT(DISTINCT vf.vehicle_id) as affected_vehicle_count
FROM failure_patterns f
LEFT JOIN vehicle_failures vf ON f.failure_id = vf.failure_id
WHERE f.confidence = 'HIGH'
GROUP BY f.failure_id
ORDER BY affected_vehicle_count DESC;

-- Safety-critical issues
CREATE VIEW IF NOT EXISTS v_safety_critical_issues AS
SELECT
    v.make,
    v.model,
    v.year,
    f.name as failure_name,
    f.symptom_description,
    f.confidence,
    f.source_type,
    f.nhtsa_number
FROM vehicles v
JOIN vehicle_failures vf ON v.vehicle_id = vf.vehicle_id
JOIN failure_patterns f ON vf.failure_id = f.failure_id
WHERE f.safety_critical = 1
ORDER BY v.make, v.model, v.year;

-- ============================================================================
-- PERFORMANCE OPTIMIZATION
-- ============================================================================

-- Analyze tables for query optimization
-- Run these after data import:
-- ANALYZE;
-- PRAGMA optimize;

-- ============================================================================
-- SCHEMA VALIDATION
-- ============================================================================

-- Ensure foreign key constraints are enforced
PRAGMA foreign_keys = ON;

-- Validate schema
SELECT 'Schema created successfully. Version 1.0' as status;
