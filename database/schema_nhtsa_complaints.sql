-- NHTSA Vehicle Complaint Database Schema
-- Source: NHTSA FLAT_CMPL file (Flat Complaint File)
-- Contains consumer complaints about vehicle safety issues

CREATE TABLE IF NOT EXISTS nhtsa_complaints (
    -- Primary identifiers
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    record_number INTEGER,
    complaint_id INTEGER UNIQUE NOT NULL,  -- CMPLID from NHTSA

    -- Vehicle information
    manufacturer_name TEXT,
    make TEXT NOT NULL,
    model TEXT NOT NULL,
    year INTEGER NOT NULL,
    vin_partial TEXT,  -- Partial VIN (first 11 characters typically)

    -- Incident details
    failure_date DATE,
    crash_flag TEXT CHECK(crash_flag IN ('Y', 'N', '')),
    fire_flag TEXT CHECK(fire_flag IN ('Y', 'N', '')),
    num_injuries INTEGER DEFAULT 0,
    num_deaths INTEGER DEFAULT 0,

    -- Component and failure information
    component_description TEXT,  -- COMPDESC - hierarchical component path
    complaint_narrative TEXT,    -- CDESCR - full description from consumer

    -- Location and timing
    city TEXT,
    state TEXT,
    date_received DATE,
    date_opened DATE,

    -- Data quality
    imported_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    -- Indexes for common queries
    CONSTRAINT valid_year CHECK(year >= 1900 AND year <= 2100)
);

-- Index for vehicle lookups (most common query pattern)
CREATE INDEX IF NOT EXISTS idx_vehicle_lookup
ON nhtsa_complaints(make, model, year);

-- Index for component searches
CREATE INDEX IF NOT EXISTS idx_component
ON nhtsa_complaints(component_description);

-- Index for safety-critical searches
CREATE INDEX IF NOT EXISTS idx_safety_critical
ON nhtsa_complaints(fire_flag, crash_flag, num_injuries, num_deaths)
WHERE fire_flag = 'Y' OR crash_flag = 'Y' OR num_injuries > 0 OR num_deaths > 0;

-- Index for date-based analysis
CREATE INDEX IF NOT EXISTS idx_failure_date
ON nhtsa_complaints(failure_date);

-- Full-text search index for complaint narratives
CREATE VIRTUAL TABLE IF NOT EXISTS nhtsa_complaints_fts USING fts5(
    complaint_id UNINDEXED,
    make,
    model,
    component_description,
    complaint_narrative,
    content='nhtsa_complaints',
    content_rowid='id'
);

-- Trigger to keep FTS index in sync
CREATE TRIGGER IF NOT EXISTS nhtsa_complaints_ai AFTER INSERT ON nhtsa_complaints BEGIN
    INSERT INTO nhtsa_complaints_fts(rowid, complaint_id, make, model, component_description, complaint_narrative)
    VALUES (new.id, new.complaint_id, new.make, new.model, new.component_description, new.complaint_narrative);
END;

CREATE TRIGGER IF NOT EXISTS nhtsa_complaints_ad AFTER DELETE ON nhtsa_complaints BEGIN
    DELETE FROM nhtsa_complaints_fts WHERE rowid = old.id;
END;

CREATE TRIGGER IF NOT EXISTS nhtsa_complaints_au AFTER UPDATE ON nhtsa_complaints BEGIN
    DELETE FROM nhtsa_complaints_fts WHERE rowid = old.id;
    INSERT INTO nhtsa_complaints_fts(rowid, complaint_id, make, model, component_description, complaint_narrative)
    VALUES (new.id, new.complaint_id, new.make, new.model, new.component_description, new.complaint_narrative);
END;

-- View for safety-critical complaints only
CREATE VIEW IF NOT EXISTS safety_critical_complaints AS
SELECT
    complaint_id,
    manufacturer_name,
    make,
    model,
    year,
    component_description,
    complaint_narrative,
    fire_flag,
    crash_flag,
    num_injuries,
    num_deaths,
    failure_date
FROM nhtsa_complaints
WHERE
    fire_flag = 'Y'
    OR crash_flag = 'Y'
    OR num_injuries > 0
    OR num_deaths > 0
ORDER BY
    num_deaths DESC,
    num_injuries DESC,
    fire_flag DESC;

-- View for aggregated complaint statistics by vehicle
CREATE VIEW IF NOT EXISTS complaint_stats_by_vehicle AS
SELECT
    make,
    model,
    year,
    COUNT(*) as total_complaints,
    SUM(CASE WHEN fire_flag = 'Y' THEN 1 ELSE 0 END) as fire_incidents,
    SUM(CASE WHEN crash_flag = 'Y' THEN 1 ELSE 0 END) as crash_incidents,
    SUM(num_injuries) as total_injuries,
    SUM(num_deaths) as total_deaths,
    COUNT(DISTINCT component_description) as unique_components_affected
FROM nhtsa_complaints
GROUP BY make, model, year
HAVING total_complaints > 0
ORDER BY total_complaints DESC;
