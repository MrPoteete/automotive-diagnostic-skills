-- Additional Data Source Schema
-- Adds NHTSA recalls, investigations, EPA vehicle specs, and Transport Canada recalls
-- to the existing automotive_complaints.db

-- ============================================================
-- NHTSA RECALLS (FLAT_RCL)
-- Manufacturer-acknowledged defects / safety campaigns
-- Confidence: 0.9 (highest — official defect acknowledgment)
-- ============================================================
CREATE TABLE IF NOT EXISTS nhtsa_recalls (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    campaign_no TEXT UNIQUE,           -- CAMPNO: NHTSA recall number
    make TEXT,
    model TEXT,
    year_from INTEGER,
    year_to INTEGER,
    component TEXT,                    -- COMPNAME
    mfg_name TEXT,                     -- MFGNAME
    mfg_campaign_no TEXT,              -- MFGCAMPNO
    begin_mfg_date TEXT,               -- BGMAN (YYYYMM)
    end_mfg_date TEXT,                 -- ENDMAN (YYYYMM)
    vehicles_affected INTEGER,         -- POTAFF
    report_date TEXT,                  -- RCDATE
    description TEXT,                  -- DESCRIPT
    consequence TEXT,                  -- CONEQUENCE
    remedy TEXT,                       -- REMEDY
    notes TEXT,
    imported_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_recalls_vehicle
    ON nhtsa_recalls(make, model, year_from, year_to);
CREATE INDEX IF NOT EXISTS idx_recalls_component
    ON nhtsa_recalls(component);

-- FTS5 for full-text search of recall descriptions
CREATE VIRTUAL TABLE IF NOT EXISTS recalls_fts USING fts5(
    campaign_no UNINDEXED,
    make,
    model,
    component,
    description,
    consequence,
    remedy,
    tokenize='porter',
    content='nhtsa_recalls',
    content_rowid='id'
);

-- ============================================================
-- NHTSA INVESTIGATIONS (FLAT_INV)
-- Open defect investigations — pre-recall government watchlist
-- Confidence: 0.8 (government-flagged but not yet confirmed)
-- ============================================================
CREATE TABLE IF NOT EXISTS nhtsa_investigations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    inv_id TEXT UNIQUE,                -- NHTSA investigation number
    inv_type TEXT,                     -- PE=Preliminary Eval, EA=Engineering Analysis
    make TEXT,
    model TEXT,
    year_from INTEGER,
    year_to INTEGER,
    component TEXT,
    summary TEXT,
    open_date TEXT,
    close_date TEXT,
    status TEXT,                       -- OPEN / CLOSED
    vehicles_affected INTEGER,
    imported_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_inv_vehicle
    ON nhtsa_investigations(make, model, year_from, year_to);

-- ============================================================
-- EPA FUEL ECONOMY VEHICLES (fueleconomy.gov vehicles.csv)
-- Full powertrain specs: engine, transmission, drivetrain
-- ============================================================
CREATE TABLE IF NOT EXISTS epa_vehicles (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    year INTEGER,
    make TEXT,
    model TEXT,
    vehicle_class TEXT,
    fuel_type TEXT,
    engine_cylinders INTEGER,
    engine_displacement REAL,          -- Liters
    drive TEXT,                        -- FWD/RWD/AWD/4WD/2WD/Part-time 4WD
    transmission TEXT,                 -- AV=CVT, A4/A6/A8=auto, M5/M6=manual etc.
    transmission_descriptor TEXT,      -- Human-readable
    turbo INTEGER DEFAULT 0,           -- 1 if turbocharged
    supercharged INTEGER DEFAULT 0,
    mpg_city INTEGER,
    mpg_highway INTEGER,
    mpg_combined INTEGER,
    co2_gpm INTEGER,                   -- CO2 grams per mile
    annual_fuel_cost INTEGER,
    imported_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_epa_vehicle
    ON epa_vehicles(make, model, year);
CREATE INDEX IF NOT EXISTS idx_epa_drivetrain
    ON epa_vehicles(make, model, year, transmission, drive);

-- ============================================================
-- TRANSPORT CANADA VEHICLE RECALLS
-- Canadian market recalls — different coverage than NHTSA
-- ============================================================
CREATE TABLE IF NOT EXISTS canada_recalls (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    recall_no TEXT UNIQUE,
    make TEXT,
    model TEXT,
    year_from INTEGER,
    year_to INTEGER,
    system TEXT,                       -- Affected system
    description TEXT,
    consequence TEXT,
    remedy TEXT,
    recall_date TEXT,
    imported_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_canada_recalls_vehicle
    ON canada_recalls(make, model, year_from, year_to);
