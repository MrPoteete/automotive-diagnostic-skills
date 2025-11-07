# NHTSA Complaints Database - Usage Guide

## Overview

You now have **2,144,604 vehicle complaints** from the NHTSA database, covering decades of real-world vehicle issues reported by consumers.

**Database Location**: `database/automotive_diagnostics.db`
**Table**: `nhtsa_complaints`
**Full-text Search**: `nhtsa_complaints_fts`

---

## Quick Statistics

```sql
-- Total complaints
SELECT COUNT(*) FROM nhtsa_complaints;
-- Result: 2,144,604

-- Date range coverage
SELECT MIN(failure_date) as earliest, MAX(failure_date) as latest
FROM nhtsa_complaints
WHERE failure_date IS NOT NULL;

-- Unique vehicle models
SELECT COUNT(DISTINCT make || ' ' || model) FROM nhtsa_complaints;

-- Safety-critical incidents
SELECT COUNT(*) FROM safety_critical_complaints;
```

---

## Example Queries for Diagnostics

### 1. Find Common Issues for a Specific Vehicle

**Find all complaints for 2018 Ford F-150:**

```sql
SELECT
    complaint_id,
    component_description,
    complaint_narrative,
    fire_flag,
    crash_flag,
    failure_date
FROM nhtsa_complaints
WHERE make = 'FORD'
  AND model = 'F-150'
  AND year = 2018
ORDER BY failure_date DESC
LIMIT 20;
```

### 2. Identify Most Common Component Failures

**Top 10 most complained-about components for RAM 1500 (2015-2020):**

```sql
SELECT
    component_description,
    COUNT(*) as complaint_count,
    SUM(CASE WHEN fire_flag = 'Y' THEN 1 ELSE 0 END) as fires,
    SUM(CASE WHEN crash_flag = 'Y' THEN 1 ELSE 0 END) as crashes,
    SUM(num_injuries) as total_injuries
FROM nhtsa_complaints
WHERE make = 'RAM'
  AND model = '1500'
  AND year BETWEEN 2015 AND 2020
GROUP BY component_description
ORDER BY complaint_count DESC
LIMIT 10;
```

### 3. Search for Specific Symptoms

**Find all brake-related complaints with "grinding" noise:**

```sql
SELECT
    make,
    model,
    year,
    component_description,
    complaint_narrative
FROM nhtsa_complaints
WHERE component_description LIKE '%BRAKE%'
  AND (
    complaint_narrative LIKE '%grinding%'
    OR complaint_narrative LIKE '%GRINDING%'
  )
LIMIT 20;
```

**Better: Use Full-Text Search (much faster!):**

```sql
SELECT
    c.make,
    c.model,
    c.year,
    c.component_description,
    snippet(nhtsa_complaints_fts, 4, '**', '**', '...', 50) as matched_text
FROM nhtsa_complaints_fts fts
JOIN nhtsa_complaints c ON c.id = fts.rowid
WHERE nhtsa_complaints_fts MATCH 'brake AND grinding'
LIMIT 20;
```

### 4. Safety-Critical Patterns

**All Ford complaints involving fires in the last 10 years:**

```sql
SELECT
    make,
    model,
    year,
    component_description,
    complaint_narrative,
    failure_date,
    num_injuries,
    num_deaths
FROM safety_critical_complaints
WHERE make = 'FORD'
  AND fire_flag = 'Y'
  AND failure_date >= date('now', '-10 years')
ORDER BY num_deaths DESC, num_injuries DESC, failure_date DESC
LIMIT 50;
```

### 5. Pattern Detection Across Years

**Track how complaints changed year-over-year for a specific model:**

```sql
SELECT
    year,
    COUNT(*) as total_complaints,
    SUM(CASE WHEN component_description LIKE '%TRANSMISSION%' THEN 1 ELSE 0 END) as transmission_issues,
    SUM(CASE WHEN component_description LIKE '%ENGINE%' THEN 1 ELSE 0 END) as engine_issues,
    SUM(CASE WHEN component_description LIKE '%BRAKE%' THEN 1 ELSE 0 END) as brake_issues
FROM nhtsa_complaints
WHERE make = 'CHEVROLET'
  AND model = 'SILVERADO'
  AND year BETWEEN 2015 AND 2025
GROUP BY year
ORDER BY year DESC;
```

### 6. Compare Similar Vehicles

**Compare complaint counts for similar trucks:**

```sql
SELECT
    make || ' ' || model as vehicle,
    COUNT(*) as complaints,
    SUM(CASE WHEN crash_flag = 'Y' THEN 1 ELSE 0 END) as crash_related,
    SUM(num_injuries) as injuries
FROM nhtsa_complaints
WHERE (
    (make = 'FORD' AND model = 'F-150')
    OR (make = 'CHEVROLET' AND model = 'SILVERADO')
    OR (make = 'RAM' AND model = '1500')
)
AND year BETWEEN 2015 AND 2025
GROUP BY make, model
ORDER BY complaints DESC;
```

### 7. Find Complaints Similar to Current Issue

**Given a symptom, find similar past complaints:**

```sql
-- Example: Customer reports "steering locked up while driving"
SELECT
    make,
    model,
    year,
    component_description,
    snippet(nhtsa_complaints_fts, 4, '>>', '<<', '...', 80) as context
FROM nhtsa_complaints_fts fts
JOIN nhtsa_complaints c ON c.id = fts.rowid
WHERE nhtsa_complaints_fts MATCH 'steering AND (locked OR lock OR locking) AND driving'
ORDER BY rank
LIMIT 30;
```

---

## Integration with Your Diagnostic System

### Step 1: Match Customer Vehicle

```python
customer_vehicle = {
    'make': 'FORD',
    'model': 'F-150',
    'year': 2018,
}

query = """
SELECT component_description, COUNT(*) as frequency
FROM nhtsa_complaints
WHERE make = ? AND model = ? AND year = ?
GROUP BY component_description
ORDER BY frequency DESC
LIMIT 20
"""

# Execute with customer_vehicle values
```

### Step 2: Match Symptoms to Complaints

```python
customer_symptoms = "engine stalls at idle"

# Use full-text search
query = """
SELECT
    c.component_description,
    c.complaint_narrative,
    COUNT(*) OVER (PARTITION BY c.component_description) as similar_count
FROM nhtsa_complaints_fts fts
JOIN nhtsa_complaints c ON c.id = fts.rowid
WHERE c.make = ?
  AND c.model = ?
  AND c.year BETWEEN ? AND ?
  AND nhtsa_complaints_fts MATCH ?
ORDER BY rank
LIMIT 50
"""
```

### Step 3: Calculate Confidence Score

```python
def calculate_confidence(nhtsa_matches, obd_codes, mileage):
    """
    Combine multiple data sources for diagnosis confidence.

    - NHTSA complaint frequency: Higher count = higher confidence
    - Safety-critical indicator: Fire/crash/injury = prioritize
    - Component match: Exact component match = boost confidence
    """
    base_confidence = 0.5

    if nhtsa_matches > 100:
        base_confidence += 0.2
    elif nhtsa_matches > 50:
        base_confidence += 0.1

    # Continue with your existing logic...
    return confidence_score
```

---

## PowerShell Quick Commands

**Count by manufacturer:**
```powershell
sqlite3 database\automotive_diagnostics.db "SELECT manufacturer_name, COUNT(*) as complaints FROM nhtsa_complaints GROUP BY manufacturer_name ORDER BY complaints DESC LIMIT 10;"
```

**Safety stats:**
```powershell
sqlite3 database\automotive_diagnostics.db "SELECT SUM(num_injuries) as injuries, SUM(num_deaths) as deaths FROM nhtsa_complaints;"
```

**Most complained-about vehicle:**
```powershell
sqlite3 database\automotive_diagnostics.db "SELECT make, model, year, COUNT(*) as complaints FROM nhtsa_complaints GROUP BY make, model, year ORDER BY complaints DESC LIMIT 10;"
```

---

## Next Steps for Your Diagnostic System

1. **Build Complaint Aggregator**: Group similar complaints to identify known patterns
2. **Symptom Matcher**: Use full-text search to match customer descriptions to past complaints
3. **Confidence Booster**: Increase diagnostic confidence when NHTSA data supports your findings
4. **Safety Alerts**: Flag safety-critical components (brakes, airbags, steering) automatically
5. **Trend Analysis**: Show mechanics "increasing complaints for this issue in recent years"

---

## Performance Tips

- **Always use indexes**: The schema includes optimized indexes for common queries
- **Use full-text search** for narrative searches (much faster than LIKE)
- **Filter by make/model/year first**, then search components
- **Limit results** for exploratory queries
- **Use views** for common patterns (e.g., `safety_critical_complaints`)

---

## Database Size

Check your database size:

```powershell
dir database\automotive_diagnostics.db
```

Expected: ~500MB-800MB depending on indexes and full-text search.

---

**Your diagnostic system now has access to 2.1 million real-world data points!** 🚀
