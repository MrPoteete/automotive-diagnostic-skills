
CREATE TABLE IF NOT EXISTS nhtsa_tsbs (
    nhtsa_id TEXT PRIMARY KEY,
    bulletin_no TEXT,
    bulletin_date TEXT,
    make TEXT,
    model TEXT,
    year INTEGER,
    component TEXT,
    summary TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_tsbs_make_model_year ON nhtsa_tsbs(make, model, year);
CREATE INDEX IF NOT EXISTS idx_tsbs_component ON nhtsa_tsbs(component);

-- Create a Virtual Table for Full Text Search on summaries and components
CREATE VIRTUAL TABLE IF NOT EXISTS tsbs_fts USING fts5(
    nhtsa_id UNINDEXED,
    make,
    model,
    year,
    component,
    summary,
    tokenize='porter'
);
