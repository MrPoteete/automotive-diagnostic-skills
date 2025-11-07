# NHTSA Complaints - Quick Reference Guide

**Database**: `database/automotive_diagnostics.db`
**Total Records**: 2,144,604 vehicle complaints
**Table**: `nhtsa_complaints`

---

## Quick Commands (Copy & Paste)

### Explore Your Data (Easiest!)

```powershell
# Run the data explorer - shows everything
python scripts\explore_complaints.py
```

This shows:
- Total complaints
- Most complained-about vehicles
- Safety statistics
- Top manufacturers
- Your focus vehicles (F-150, RAM 1500, Silverado)
- Common component failures

---

## Custom Queries (Python One-Liners)

### Count Complaints for Specific Vehicle

```powershell
# Ford F-150 complaints (all years)
python -c "import sqlite3; conn = sqlite3.connect('database/automotive_diagnostics.db'); cursor = conn.execute('SELECT COUNT(*) FROM nhtsa_complaints WHERE make=? AND model=?', ('FORD', 'F-150')); print('Ford F-150 complaints:', cursor.fetchone()[0])"
```

```powershell
# RAM 1500 (2015-2020)
python -c "import sqlite3; conn = sqlite3.connect('database/automotive_diagnostics.db'); cursor = conn.execute('SELECT COUNT(*) FROM nhtsa_complaints WHERE make=? AND model=? AND year BETWEEN ? AND ?', ('RAM', '1500', 2015, 2020)); print('RAM 1500 (2015-2020):', cursor.fetchone()[0])"
```

### Search for Specific Problems

```powershell
# Brake problems on any vehicle
python -c "import sqlite3; conn = sqlite3.connect('database/automotive_diagnostics.db'); cursor = conn.execute('SELECT make, model, year, complaint_narrative FROM nhtsa_complaints WHERE component_description LIKE ? LIMIT 10', ('%BRAKE%',)); print('\n'.join([f'{r[0]} {r[1]} {r[2]}: {r[3][:100]}...' for r in cursor.fetchall()]))"
```

### Safety-Critical Issues

```powershell
# Count fires, crashes, injuries, deaths
python -c "import sqlite3; conn = sqlite3.connect('database/automotive_diagnostics.db'); cursor = conn.execute('SELECT SUM(CASE WHEN fire_flag=\"Y\" THEN 1 ELSE 0 END) as fires, SUM(CASE WHEN crash_flag=\"Y\" THEN 1 ELSE 0 END) as crashes, SUM(num_injuries) as injuries, SUM(num_deaths) as deaths FROM nhtsa_complaints'); print('Safety Stats:', cursor.fetchone())"
```

---

## Using Python Scripts Directly

### Create a Custom Query Script

Save this as `my_query.py`:

```python
import sqlite3
from pathlib import Path

# Connect to database
db = Path('database/automotive_diagnostics.db')
conn = sqlite3.connect(db)

# Your custom query
make = 'FORD'
model = 'F-150'
year = 2018

query = """
SELECT
    component_description,
    COUNT(*) as complaint_count
FROM nhtsa_complaints
WHERE make = ? AND model = ? AND year = ?
GROUP BY component_description
ORDER BY complaint_count DESC
LIMIT 10
"""

cursor = conn.execute(query, (make, model, year))

print(f"\nTop 10 Component Issues for {year} {make} {model}:\n")
for row in cursor:
    print(f"  {row[1]:4d} complaints - {row[0]}")

conn.close()
```

Run it:
```powershell
python my_query.py
```

---

## Common Use Cases

### For a Customer's Vehicle

**Customer has: 2018 Ford F-150, complaining about transmission**

```python
# save as check_vehicle.py
import sqlite3

conn = sqlite3.connect('database/automotive_diagnostics.db')

# Search for similar complaints
query = """
SELECT
    complaint_narrative,
    component_description,
    fire_flag,
    crash_flag
FROM nhtsa_complaints
WHERE make = 'FORD'
  AND model = 'F-150'
  AND year = 2018
  AND (component_description LIKE '%TRANSMISSION%'
       OR complaint_narrative LIKE '%transmission%')
LIMIT 20
"""

cursor = conn.execute(query)
for i, row in enumerate(cursor, 1):
    print(f"\n{i}. Component: {row[1]}")
    print(f"   Description: {row[0][:200]}...")
    if row[2] == 'Y' or row[3] == 'Y':
        print(f"   ⚠️  SAFETY ISSUE: Fire={row[2]}, Crash={row[3]}")

conn.close()
```

### Find Pattern Across Years

**Check if problem is widespread across model years:**

```python
# save as year_pattern.py
import sqlite3

conn = sqlite3.connect('database/automotive_diagnostics.db')

query = """
SELECT
    year,
    COUNT(*) as total_complaints,
    SUM(CASE WHEN component_description LIKE '%TRANSMISSION%' THEN 1 ELSE 0 END) as trans_issues
FROM nhtsa_complaints
WHERE make = 'FORD' AND model = 'F-150'
  AND year BETWEEN 2015 AND 2025
GROUP BY year
ORDER BY year DESC
"""

cursor = conn.execute(query)
print("\nFord F-150 Transmission Complaints by Year:")
print("Year | Total | Transmission")
print("-" * 30)
for row in cursor:
    print(f"{row[0]} | {row[1]:5d} | {row[2]:5d}")

conn.close()
```

---

## Most Useful Queries

### 1. Search Complaint Narratives

```python
import sqlite3

conn = sqlite3.connect('database/automotive_diagnostics.db')

# Search for specific symptoms
search_term = '%stalling%'  # Use % as wildcard

query = """
SELECT make, model, year, complaint_narrative
FROM nhtsa_complaints
WHERE complaint_narrative LIKE ?
LIMIT 20
"""

cursor = conn.execute(query, (search_term,))
for row in cursor:
    print(f"{row[0]} {row[1]} {row[2]}: {row[3][:150]}...")
    print()

conn.close()
```

### 2. Component Frequency Analysis

```python
import sqlite3

conn = sqlite3.connect('database/automotive_diagnostics.db')

# Most complained-about components for a vehicle
query = """
SELECT
    component_description,
    COUNT(*) as frequency,
    SUM(CASE WHEN crash_flag = 'Y' THEN 1 ELSE 0 END) as crashes
FROM nhtsa_complaints
WHERE make = ? AND model = ?
GROUP BY component_description
ORDER BY frequency DESC
LIMIT 15
"""

cursor = conn.execute(query, ('FORD', 'F-150'))
print("\nTop 15 Components with Complaints:")
for row in cursor:
    crash_marker = " ⚠️" if row[2] > 0 else ""
    print(f"{row[1]:5d} - {row[0]}{crash_marker}")

conn.close()
```

### 3. Safety-Critical Alerts

```python
import sqlite3

conn = sqlite3.connect('database/automotive_diagnostics.db')

# Check for safety issues on specific vehicle
query = """
SELECT
    component_description,
    complaint_narrative,
    fire_flag,
    crash_flag,
    num_injuries,
    num_deaths
FROM nhtsa_complaints
WHERE make = ? AND model = ? AND year = ?
  AND (fire_flag = 'Y' OR crash_flag = 'Y' OR num_injuries > 0 OR num_deaths > 0)
ORDER BY num_deaths DESC, num_injuries DESC
LIMIT 20
"""

cursor = conn.execute(query, ('RAM', '1500', 2018))

print("\n⚠️  SAFETY-CRITICAL COMPLAINTS:\n")
for row in cursor:
    print(f"Component: {row[0]}")
    print(f"Issue: {row[1][:200]}...")
    print(f"Fire: {row[2]} | Crash: {row[3]} | Injuries: {row[4]} | Deaths: {row[5]}")
    print("-" * 80)

conn.close()
```

---

## File Locations

- **Main Database**: `database/automotive_diagnostics.db`
- **Schema**: `database/schema_nhtsa_complaints.sql`
- **Explorer Tool**: `scripts/explore_complaints.py`
- **Full Documentation**: `docs/NHTSA_COMPLAINTS_USAGE.md`

---

## Need More?

See **`docs/NHTSA_COMPLAINTS_USAGE.md`** for:
- Advanced queries
- Full-text search examples
- Integration patterns
- Performance tips

---

## Quick Tips

1. **Always filter by make/model first** - much faster
2. **Use LIKE '%keyword%'** for text searches (case-insensitive)
3. **Check component_description** for system-level issues
4. **Check complaint_narrative** for specific symptoms
5. **Safety-critical view exists**: `safety_critical_complaints`

---

**Last Updated**: After importing 2,144,604 NHTSA complaints
