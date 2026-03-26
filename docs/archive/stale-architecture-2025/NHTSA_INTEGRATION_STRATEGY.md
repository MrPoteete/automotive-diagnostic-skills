> ⚠️ **DEPRECATED — DO NOT USE FOR CURRENT SYSTEM STATE**
> This document has stale data and was archived on 2026-03-26.
> For accurate architecture, DB schemas, and row counts, use:
> **`.claude/docs/DIAGRAMS.md`** (ground truth)

---

# NHTSA Complaints Integration Strategy

**Goal**: Integrate 2.1M NHTSA complaints with existing diagnostic system to enhance accuracy, confidence scoring, and pattern detection.

---

## Integration Points

### 1. **Enhanced Failure Pattern Detection**
**What**: Automatically generate failure patterns from complaint clusters
**How**: Aggregate complaints by component + symptoms to identify common failures

```python
# Generate failure patterns from complaints
def generate_failure_patterns_from_complaints(make, model, year_range):
    """
    Analyze complaints to identify common failure patterns.

    Returns patterns that should be added to failure_patterns table.
    """
    query = """
    SELECT
        component_description,
        COUNT(*) as frequency,
        SUM(CASE WHEN fire_flag = 'Y' THEN 1 ELSE 0 END) as fires,
        SUM(CASE WHEN crash_flag = 'Y' THEN 1 ELSE 0 END) as crashes,
        SUM(num_injuries) as injuries,
        SUM(num_deaths) as deaths,
        GROUP_CONCAT(DISTINCT substr(complaint_narrative, 1, 200), ' | ') as symptom_samples
    FROM nhtsa_complaints
    WHERE make = ? AND model = ?
      AND year BETWEEN ? AND ?
    GROUP BY component_description
    HAVING frequency >= 10  -- Minimum threshold for pattern
    ORDER BY frequency DESC
    """

    # Results become entries in failure_patterns table
    # with confidence = HIGH if frequency > 100
```

**Benefit**: Auto-populate failure_patterns table with real-world data

---

### 2. **DTC Code Correlation**
**What**: Link OBD-II codes to real-world complaints that mention them
**How**: Extract DTC codes from complaint narratives and correlate

```python
def find_complaints_with_dtc(dtc_code):
    """
    Find all complaints that mention a specific DTC code.

    Example: P0300 (misfire) appears in narratives as "code P0300"
    """
    query = """
    SELECT
        make, model, year,
        component_description,
        complaint_narrative,
        fire_flag, crash_flag
    FROM nhtsa_complaints
    WHERE complaint_narrative LIKE ?
       OR complaint_narrative LIKE ?
    LIMIT 100
    """

    # Search for "P0300", "P-0300", "code 0300", etc.
    patterns = [f'%{dtc_code}%', f'%{dtc_code.replace("P", "P-")}%']

    return results

def enrich_dtc_diagnosis(dtc_code, vehicle):
    """
    When customer has a DTC code, show related complaints.

    Combines:
    - DTC definition from dtc_codes table
    - Failure patterns from failure_patterns table
    - Real complaints from nhtsa_complaints table
    """
    dtc_info = get_dtc_info(dtc_code)  # Existing function
    patterns = get_failure_patterns(vehicle, dtc_code)  # Existing
    complaints = find_complaints_with_dtc(dtc_code)  # New!

    return {
        'code': dtc_code,
        'definition': dtc_info,
        'known_patterns': patterns,
        'real_world_reports': len(complaints),
        'safety_critical': any(c['fire_flag'] == 'Y' for c in complaints)
    }
```

**Benefit**: See how often a DTC appears in real-world complaints

---

### 3. **Confidence Scoring Enhancement**
**What**: Use complaint frequency to boost diagnostic confidence
**How**: When your diagnosis matches high-frequency complaints, increase confidence

```python
def calculate_enhanced_confidence(diagnosis, vehicle, symptoms):
    """
    Calculate diagnostic confidence using multiple data sources.

    Factors:
    1. DTC code match (existing)
    2. Failure pattern match (existing)
    3. NHTSA complaint frequency (NEW)
    4. Safety-critical flags (NEW)
    """
    base_confidence = 0.5

    # Existing logic for DTC/patterns
    if diagnosis['dtc_match']:
        base_confidence += 0.2

    if diagnosis['pattern_match']:
        base_confidence += 0.15

    # NEW: Check NHTSA complaints
    complaint_count = count_similar_complaints(
        vehicle=vehicle,
        component=diagnosis['component'],
        symptoms=symptoms
    )

    if complaint_count > 100:
        base_confidence += 0.15  # Very common issue
    elif complaint_count > 50:
        base_confidence += 0.10
    elif complaint_count > 10:
        base_confidence += 0.05

    # NEW: Safety-critical boost (these are well-documented)
    if has_safety_complaints(vehicle, diagnosis['component']):
        base_confidence += 0.05

    return min(base_confidence, 1.0)

def count_similar_complaints(vehicle, component, symptoms):
    """Count complaints matching this diagnosis."""
    query = """
    SELECT COUNT(*)
    FROM nhtsa_complaints
    WHERE make = ? AND model = ?
      AND year BETWEEN ? AND ?
      AND component_description LIKE ?
    """

    return cursor.execute(query, (
        vehicle['make'],
        vehicle['model'],
        vehicle['year'] - 2,  # +/- 2 years
        vehicle['year'] + 2,
        f'%{component}%'
    )).fetchone()[0]
```

**Benefit**: More accurate confidence scores based on real-world data

---

### 4. **Symptom Matching with Full-Text Search**
**What**: Match customer's verbal description to past complaints
**How**: Use FTS5 to search complaint narratives for similar symptoms

```python
def match_customer_symptoms(customer_description, vehicle):
    """
    Find complaints with similar symptoms using full-text search.

    Example:
    Customer says: "Engine shakes when idling, check engine light on"

    Returns: Complaints mentioning "shake", "idle", "vibration", etc.
    """
    # Extract key terms from customer description
    search_terms = extract_symptom_keywords(customer_description)
    # e.g., ["engine", "shake", "idle", "check engine light"]

    # Build FTS5 query
    fts_query = ' OR '.join(search_terms)

    query = """
    SELECT
        c.component_description,
        c.complaint_narrative,
        COUNT(*) OVER (PARTITION BY c.component_description) as similar_count
    FROM nhtsa_complaints_fts fts
    JOIN nhtsa_complaints c ON c.id = fts.rowid
    WHERE c.make = ? AND c.model = ?
      AND c.year BETWEEN ? AND ?
      AND nhtsa_complaints_fts MATCH ?
    ORDER BY rank
    LIMIT 20
    """

    results = cursor.execute(query, (
        vehicle['make'],
        vehicle['model'],
        vehicle['year'] - 3,
        vehicle['year'] + 3,
        fts_query
    )).fetchall()

    return group_by_component(results)

def extract_symptom_keywords(description):
    """Extract relevant search terms from customer description."""
    # Common symptom keywords
    keywords = []

    symptom_map = {
        'shake': ['shake', 'shaking', 'vibration', 'vibrating'],
        'stall': ['stall', 'stalling', 'dies', 'shut off'],
        'noise': ['noise', 'sound', 'grinding', 'knocking', 'rattling'],
        'leak': ['leak', 'leaking', 'fluid', 'dripping'],
        # ... more mappings
    }

    # Extract and expand keywords
    # Return search-optimized terms
```

**Benefit**: Find similar cases even when customer uses different words

---

### 5. **Component Prioritization**
**What**: When multiple components could be faulty, prioritize by complaint frequency
**How**: Rank potential causes by how often they fail in real world

```python
def prioritize_diagnostic_paths(vehicle, symptoms, dtc_codes):
    """
    Given multiple possible causes, prioritize by real-world frequency.

    Example:
    DTC P0300 (misfire) could be:
    - Spark plugs
    - Ignition coils
    - Fuel injectors
    - Compression issues

    Which is most common for this vehicle?
    """
    possible_components = identify_possible_components(dtc_codes)

    # Check complaint frequency for each component
    component_stats = []
    for component in possible_components:
        stats = get_component_complaint_stats(vehicle, component)
        component_stats.append({
            'component': component,
            'complaint_count': stats['count'],
            'avg_mileage': stats['avg_mileage'],
            'safety_critical': stats['has_safety_issues'],
            'priority_score': calculate_priority(stats)
        })

    # Sort by priority score
    return sorted(component_stats, key=lambda x: x['priority_score'], reverse=True)

def get_component_complaint_stats(vehicle, component):
    """Get statistics for a specific component."""
    query = """
    SELECT
        COUNT(*) as complaint_count,
        SUM(CASE WHEN fire_flag = 'Y' OR crash_flag = 'Y' THEN 1 ELSE 0 END) as safety_issues
    FROM nhtsa_complaints
    WHERE make = ? AND model = ?
      AND year BETWEEN ? AND ?
      AND component_description LIKE ?
    """

    return cursor.execute(query, (
        vehicle['make'],
        vehicle['model'],
        vehicle['year'] - 2,
        vehicle['year'] + 2,
        f'%{component}%'
    )).fetchone()
```

**Benefit**: Start with most likely cause based on real failure rates

---

### 6. **Safety Alert System**
**What**: Automatically flag safety-critical components
**How**: Check if component has fire/crash/injury history

```python
def check_safety_alerts(vehicle, component):
    """
    Check if component has safety-critical history.

    Returns alert level: CRITICAL, WARNING, or None
    """
    query = """
    SELECT
        COUNT(*) as total,
        SUM(CASE WHEN fire_flag = 'Y' THEN 1 ELSE 0 END) as fires,
        SUM(CASE WHEN crash_flag = 'Y' THEN 1 ELSE 0 END) as crashes,
        SUM(num_injuries) as injuries,
        SUM(num_deaths) as deaths
    FROM nhtsa_complaints
    WHERE make = ? AND model = ?
      AND year BETWEEN ? AND ?
      AND component_description LIKE ?
      AND (fire_flag = 'Y' OR crash_flag = 'Y' OR num_injuries > 0 OR num_deaths > 0)
    """

    stats = cursor.execute(query, (...)).fetchone()

    # Determine alert level
    if stats['deaths'] > 0 or stats['fires'] > 5:
        return {
            'level': 'CRITICAL',
            'message': f'⚠️ SAFETY ALERT: {stats["deaths"]} deaths, {stats["fires"]} fires reported',
            'recommendation': 'Perform thorough inspection. Document all findings.'
        }
    elif stats['injuries'] > 10 or stats['crashes'] > 10:
        return {
            'level': 'WARNING',
            'message': f'⚠️ Safety concern: {stats["injuries"]} injuries, {stats["crashes"]} crashes',
            'recommendation': 'Extra caution recommended during diagnosis.'
        }

    return None
```

**Benefit**: Never miss a safety-critical issue

---

### 7. **Trend Analysis**
**What**: Show if problem is getting worse/better across years
**How**: Compare complaint frequency by model year

```python
def analyze_failure_trends(make, model, component, year_range):
    """
    Show how complaint frequency changes over model years.

    Useful for:
    - "Is this a known issue for 2018 models specifically?"
    - "Did manufacturer fix this in later years?"
    """
    query = """
    SELECT
        year,
        COUNT(*) as complaints,
        SUM(CASE WHEN fire_flag = 'Y' OR crash_flag = 'Y' THEN 1 ELSE 0 END) as safety_issues
    FROM nhtsa_complaints
    WHERE make = ? AND model = ?
      AND year BETWEEN ? AND ?
      AND component_description LIKE ?
    GROUP BY year
    ORDER BY year
    """

    results = cursor.execute(query, (...)).fetchall()

    # Analyze trend
    if is_increasing_trend(results):
        return "⚠️ Complaints INCREASING in recent years"
    elif is_decreasing_trend(results):
        return "✓ Complaints DECREASING (may be resolved in later models)"
    else:
        return "Stable frequency across years"
```

**Benefit**: Context about whether issue is widespread or year-specific

---

## Implementation Plan

### Phase 1: Core Integration Functions
Create `src/nhtsa_integration.py` with:
- `get_complaint_frequency(vehicle, component)`
- `match_symptoms(description, vehicle)`
- `check_safety_alerts(vehicle, component)`
- `calculate_enhanced_confidence(...)`

### Phase 2: Enhanced Diagnostic Workflow
Update existing diagnostic logic to call NHTSA functions:
1. Customer describes symptoms → match_symptoms()
2. Retrieve DTCs → enrich_dtc_diagnosis()
3. Generate diagnoses → calculate_enhanced_confidence()
4. Before repair → check_safety_alerts()

### Phase 3: Batch Processing
Generate failure_patterns table entries:
- Run nightly aggregation of complaints
- Auto-update failure_patterns with new patterns
- Flag outdated patterns if complaints drop off

### Phase 4: Reporting
Create diagnostic report that includes:
- Complaint frequency for identified issue
- Safety alerts
- Similar cases
- Trend information

---

## Database Schema Updates

### Link Tables (Optional but Recommended)

```sql
-- Link failure patterns to supporting complaints
CREATE TABLE failure_pattern_evidence (
    pattern_id INTEGER REFERENCES failure_patterns(id),
    complaint_id INTEGER REFERENCES nhtsa_complaints(complaint_id),
    relevance_score REAL,  -- How relevant this complaint is to pattern
    PRIMARY KEY (pattern_id, complaint_id)
);

-- Track which DTCs appear in complaints
CREATE TABLE dtc_complaint_mentions (
    dtc_code TEXT REFERENCES dtc_codes(code),
    complaint_id INTEGER REFERENCES nhtsa_complaints(complaint_id),
    PRIMARY KEY (dtc_code, complaint_id)
);
```

### Views for Common Queries

```sql
-- Most common issues by vehicle
CREATE VIEW vehicle_top_complaints AS
SELECT
    make, model, year,
    component_description,
    COUNT(*) as frequency,
    SUM(CASE WHEN fire_flag = 'Y' OR crash_flag = 'Y' THEN 1 ELSE 0 END) as safety_incidents
FROM nhtsa_complaints
GROUP BY make, model, year, component_description
HAVING frequency >= 5
ORDER BY make, model, year, frequency DESC;
```

---

## Example: Complete Diagnostic Flow

```python
def diagnose_vehicle_issue(vehicle, customer_symptoms, dtc_codes):
    """
    Complete diagnostic workflow with NHTSA integration.
    """
    results = {
        'vehicle': vehicle,
        'symptoms': customer_symptoms,
        'dtc_codes': dtc_codes,
        'diagnoses': []
    }

    # Step 1: Match symptoms to complaints
    similar_complaints = match_customer_symptoms(customer_symptoms, vehicle)

    # Step 2: Enrich DTC information
    dtc_details = []
    for dtc in dtc_codes:
        enriched = enrich_dtc_diagnosis(dtc, vehicle)
        dtc_details.append(enriched)

    # Step 3: Get failure patterns (existing + NHTSA-derived)
    patterns = get_failure_patterns(vehicle, dtc_codes)

    # Step 4: Combine all data sources for diagnosis
    for pattern in patterns:
        # Calculate confidence with NHTSA data
        confidence = calculate_enhanced_confidence(
            diagnosis=pattern,
            vehicle=vehicle,
            symptoms=customer_symptoms
        )

        # Check for safety alerts
        safety_alert = check_safety_alerts(vehicle, pattern['component'])

        # Get trend information
        trend = analyze_failure_trends(
            vehicle['make'],
            vehicle['model'],
            pattern['component'],
            (vehicle['year'] - 3, vehicle['year'] + 3)
        )

        results['diagnoses'].append({
            'component': pattern['component'],
            'description': pattern['description'],
            'confidence': confidence,
            'complaint_frequency': count_similar_complaints(vehicle, pattern['component'], customer_symptoms),
            'safety_alert': safety_alert,
            'trend': trend,
            'similar_cases': similar_complaints.get(pattern['component'], [])
        })

    # Step 5: Prioritize diagnoses
    results['diagnoses'] = prioritize_diagnostic_paths(vehicle, customer_symptoms, dtc_codes)

    return results
```

---

## Benefits Summary

✅ **Higher Accuracy**: Real-world data confirms/refutes diagnoses
✅ **Better Confidence Scores**: Based on actual failure frequencies
✅ **Safety First**: Automatic alerts for critical components
✅ **Faster Diagnosis**: Prioritize most likely causes
✅ **Customer Trust**: "This issue was reported 200+ times for your vehicle"
✅ **Competitive Edge**: Data most shops don't have

---

**Next Steps:**
1. Create `src/nhtsa_integration.py` with core functions
2. Test integration with sample diagnostic scenarios
3. Update diagnostic workflow to include NHTSA checks
4. Create reporting templates that show complaint data
