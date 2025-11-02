# Setup Guide - Automotive Diagnostic Skills

**Last Updated**: November 2, 2025
**Target Platform**: Windows 10/11
**Prerequisites**: Python 3.8+, SQLite 3.x (included with Python)

---

## Table of Contents

1. [System Requirements](#system-requirements)
2. [Installation](#installation)
3. [Database Setup](#database-setup)
4. [Data Import](#data-import)
5. [Verification](#verification)
6. [Usage Examples](#usage-examples)
7. [Troubleshooting](#troubleshooting)
8. [Backup and Sync](#backup-and-sync)

---

## System Requirements

### Minimum Requirements

- **Operating System**: Windows 10 or later
- **Python**: Python 3.8 or later
- **RAM**: 1 GB available
- **Disk Space**: 2 GB free (1 GB for database, 1 GB for backups)
- **Display**: Any resolution (CLI-based tools)

### Recommended Requirements

- **Operating System**: Windows 11
- **Python**: Python 3.11 or later
- **RAM**: 4 GB available
- **Disk Space**: 5 GB free (for database, backups, and source data)
- **Storage**: SSD for optimal query performance

### Software Dependencies

**Core**:
- Python 3.8+ (includes SQLite 3.x)
- No additional libraries required for basic functionality

**Optional**:
- Claude Code CLI (for AI-powered diagnostics)
- Text editor (VS Code, Notepad++, etc.)
- Git (for version control)

---

## Installation

### Step 1: Verify Python Installation

Open Command Prompt (cmd.exe) and verify Python is installed:

```bash
python --version
```

**Expected Output**:
```
Python 3.11.x
```

If Python is not installed:
1. Download from [python.org](https://www.python.org/downloads/)
2. Run installer
3. **Important**: Check "Add Python to PATH" during installation
4. Restart Command Prompt

### Step 2: Verify SQLite

SQLite is included with Python. Verify it's available:

```bash
python -c "import sqlite3; print(sqlite3.sqlite_version)"
```

**Expected Output**:
```
3.x.x
```

### Step 3: Clone or Download Project

**Option A: Using Git**:
```bash
cd C:\Users\YourUsername\Documents
git clone [repository-url] automotive-diagnostic-skills
cd automotive-diagnostic-skills
```

**Option B: Manual Download**:
1. Download project ZIP file
2. Extract to `C:\Users\YourUsername\Documents\automotive-diagnostic-skills`
3. Open Command Prompt in that directory

### Step 4: Verify Project Structure

```bash
dir
```

**Expected Output**:
```
Directory of C:\Users\YourUsername\Documents\automotive-diagnostic-skills

<DIR>          databases
<DIR>          docs
<DIR>          skills
<DIR>          tools
               README.md
```

---

## Database Setup

### Step 1: Navigate to Database Directory

```bash
cd databases
```

### Step 2: Create Database from Schema

```bash
python init_database_simple.py --force
```

**Expected Output**:
```
[INFO] Creating database from schema.sql
[INFO] Reading schema file...
[INFO] Executing schema SQL...
[SUCCESS] Database created successfully!
          Schema version: 1.0
          Tables created: 33
          Indexes created: 28
```

**What This Does**:
- Creates `automotive_diagnostics.db` file
- Creates 33 tables for vehicle data, DTCs, failures, etc.
- Creates 28 optimized indexes for fast queries
- Enables foreign key constraints

### Step 3: Verify Database Schema

```bash
python init_database_simple.py --verify
```

**Expected Output**:
```
[INFO] Verifying database schema...
[SUCCESS] Schema verification complete!
          Tables found: 33
          Indexes found: 28
          Foreign keys: ENABLED
```

### Step 4: Check Database Statistics

```bash
python init_database_simple.py --stats
```

**Expected Output**:
```
[STATS] Database Statistics
        File size: 0.25 MB
        Tables: 33
        Total rows: 0
        Schema version: 1.0
```

---

## Data Import

### Step 1: Prepare Vehicle Data Files

Ensure you have vehicle data files in pipe-delimited format:

```
Make|Model|Year|Engine Size
FORD|F-150|2005|5.4/8
TOYOTA|Camry|2005|2.4L 4-Cyl
CHEVROLET|Silverado 1500|2005|5.3L V8
```

Place files in a `data/` directory (create if needed):

```bash
cd ..
mkdir data
```

### Step 2: Import Single Year

Import a single year of vehicle data:

```bash
cd databases
python import_vehicles.py --file "..\data\2005_vehicles.txt" --year 2005
```

**Expected Output**:
```
[IMPORT] Processing file: ..\data\2005_vehicles.txt
[INFO] Total lines: 1,143
[INFO] Parsed vehicles: 1,125
[INFO] Skipped lines: 18 (headers, blank lines)

[STATS] Import Summary
  Inserted:        792
  Duplicates:      333
  Errors:            0
  Total:         1,125

Top 10 Manufacturers:
  CHEVROLET           87
  GMC                 67
  FORD                59
  MERCEDES-BENZ       47
  TOYOTA              36
  ...
```

### Step 3: Import Multiple Years (Bulk Import)

Import entire directory of vehicle files:

```bash
python import_vehicles.py --directory "..\data" --pattern "*_vehicles.txt"
```

**Expected Output**:
```
[INFO] Found 20 files matching pattern
[IMPORT] Processing 2005_vehicles.txt...
[STATS] 2005: 792 vehicles imported
[IMPORT] Processing 2006_vehicles.txt...
[STATS] 2006: 834 vehicles imported
...
[SUCCESS] Bulk import complete!
          Total files processed: 20
          Total vehicles imported: 22,847
          Total time: 45.2 seconds
```

### Step 4: Verify Import

Check database statistics after import:

```bash
python init_database_simple.py --stats
```

**Expected Output**:
```
[STATS] Database Statistics
        File size: 12.5 MB
        Tables: 33
        Total rows: 22,847

        Vehicles by manufacturer (top 10):
          FORD                1,234
          CHEVROLET           1,187
          TOYOTA              1,045
          ...
```

---

## Verification

### Test Database Connectivity

Create a test script `test_connection.py`:

```python
import sqlite3

# Connect to database
conn = sqlite3.connect('automotive_diagnostics.db')
conn.row_factory = sqlite3.Row
conn.execute("PRAGMA foreign_keys = ON")

# Query vehicles
cursor = conn.cursor()
cursor.execute("""
    SELECT make, model, year, engine
    FROM vehicles
    WHERE year = 2005
    LIMIT 5
""")

print("Sample Vehicles (2005):")
print("-" * 60)
for row in cursor.fetchall():
    print(f"{row['year']} {row['make']} {row['model']} - {row['engine']}")

# Get total count
cursor.execute("SELECT COUNT(*) as total FROM vehicles")
total = cursor.fetchone()['total']
print(f"\nTotal vehicles in database: {total:,}")

conn.close()
```

Run the test:

```bash
python test_connection.py
```

**Expected Output**:
```
Sample Vehicles (2005):
------------------------------------------------------------
2005 FORD F-150 - 5.4L V8
2005 TOYOTA Camry - 2.4L 4-Cyl
2005 CHEVROLET Silverado 1500 - 5.3L V8
2005 HONDA Accord - 2.4L 4-Cyl
2005 NISSAN Altima - 2.5L 4-Cyl

Total vehicles in database: 792
```

### Verify Foreign Key Constraints

```python
import sqlite3

conn = sqlite3.connect('automotive_diagnostics.db')
cursor = conn.cursor()

# Check if foreign keys are enabled
cursor.execute("PRAGMA foreign_keys")
result = cursor.fetchone()
print(f"Foreign Keys Enabled: {result[0] == 1}")

conn.close()
```

**Expected Output**:
```
Foreign Keys Enabled: True
```

---

## Usage Examples

### Example 1: Find Vehicles by Make and Model

```python
import sqlite3

conn = sqlite3.connect('automotive_diagnostics.db')
conn.row_factory = sqlite3.Row
cursor = conn.cursor()

# Find all Ford F-150 vehicles
cursor.execute("""
    SELECT year, engine, displacement_liters, cylinders
    FROM vehicles
    WHERE make = 'FORD' AND model = 'F-150'
    ORDER BY year DESC
""")

print("Ford F-150 Vehicles:")
for row in cursor.fetchall():
    print(f"{row['year']}: {row['engine']} "
          f"({row['displacement_liters']}L, {row['cylinders']} cylinders)")

conn.close()
```

### Example 2: Search Vehicles by Year Range

```python
import sqlite3

conn = sqlite3.connect('automotive_diagnostics.db')
conn.row_factory = sqlite3.Row
cursor = conn.cursor()

# Find all Toyota vehicles from 2015-2020
cursor.execute("""
    SELECT year, model, engine
    FROM vehicles
    WHERE make = 'TOYOTA' AND year BETWEEN 2015 AND 2020
    ORDER BY year, model
""")

print("Toyota Vehicles (2015-2020):")
for row in cursor.fetchall():
    print(f"{row['year']} {row['model']}: {row['engine']}")

conn.close()
```

### Example 3: Count Vehicles by Manufacturer

```python
import sqlite3

conn = sqlite3.connect('automotive_diagnostics.db')
conn.row_factory = sqlite3.Row
cursor = conn.cursor()

# Count vehicles by manufacturer
cursor.execute("""
    SELECT make, COUNT(*) as count
    FROM vehicles
    GROUP BY make
    ORDER BY count DESC
    LIMIT 10
""")

print("Top 10 Manufacturers:")
for row in cursor.fetchall():
    print(f"{row['make']:20} {row['count']:5,}")

conn.close()
```

---

## Troubleshooting

### Issue: "Python is not recognized"

**Symptom**: Command Prompt says `'python' is not recognized`

**Solution**:
1. Verify Python installation
2. Add Python to PATH:
   - Search "Environment Variables" in Windows
   - Edit "Path" variable
   - Add Python installation directory (e.g., `C:\Python311`)
   - Restart Command Prompt

### Issue: "No such file or directory: schema.sql"

**Symptom**: `init_database_simple.py` cannot find schema file

**Solution**:
1. Verify you're in the `databases/` directory:
   ```bash
   cd databases
   ```
2. Verify `schema.sql` exists:
   ```bash
   dir schema.sql
   ```

### Issue: "Database is locked"

**Symptom**: `sqlite3.OperationalError: database is locked`

**Solution**:
1. Close any programs accessing the database
2. Close all Command Prompt windows
3. Restart and try again
4. If persistent, restart computer

### Issue: Import Shows Many Duplicates

**Symptom**: Import reports high duplicate count

**Explanation**: This is normal behavior. The database has a UNIQUE constraint
on (make, model, year, engine). If you run the same import twice, all records
will be marked as duplicates.

**Solution**: This is expected. If intentional, no action needed. If
accidental, database integrity is preserved.

### Issue: Slow Query Performance

**Symptom**: Queries take longer than expected

**Solution**:
1. Run ANALYZE to update statistics:
   ```sql
   PRAGMA analyze;
   ```
2. Verify indexes exist:
   ```bash
   python init_database_simple.py --verify
   ```
3. Check database size - may need VACUUM:
   ```sql
   VACUUM;
   ```

### Issue: Import Fails with Encoding Error

**Symptom**: `UnicodeDecodeError` during import

**Solution**:
1. Verify file is UTF-8 encoded
2. Convert file encoding if needed
3. Remove special characters from manufacturer/model names

---

## Backup and Sync

### Manual Backup

**Create Backup**:
```bash
copy automotive_diagnostics.db automotive_diagnostics_backup.db
```

**Restore from Backup**:
```bash
copy automotive_diagnostics_backup.db automotive_diagnostics.db
```

### Automated Backup Script

Create `backup_database.bat`:

```batch
@echo off
set TIMESTAMP=%date:~-4%%date:~-10,2%%date:~-7,2%_%time:~0,2%%time:~3,2%%time:~6,2%
set TIMESTAMP=%TIMESTAMP: =0%
copy automotive_diagnostics.db backups\automotive_diagnostics_%TIMESTAMP%.db
echo Backup created: automotive_diagnostics_%TIMESTAMP%.db
```

Run daily via Task Scheduler.

### Cloud Sync Setup

#### OneDrive Setup

1. Move database to OneDrive folder:
   ```bash
   move automotive_diagnostics.db C:\Users\YourName\OneDrive\AutoDiag\
   ```

2. Create symbolic link (junction):
   ```bash
   mklink automotive_diagnostics.db C:\Users\YourName\OneDrive\AutoDiag\automotive_diagnostics.db
   ```

3. OneDrive will automatically sync changes

#### Dropbox Setup

1. Move database to Dropbox folder:
   ```bash
   move automotive_diagnostics.db C:\Users\YourName\Dropbox\AutoDiag\
   ```

2. Create symbolic link:
   ```bash
   mklink automotive_diagnostics.db C:\Users\YourName\Dropbox\AutoDiag\automotive_diagnostics.db
   ```

3. Dropbox will automatically sync changes

### Shop PC Deployment

**Initial Deployment**:

1. Copy database file to USB drive
2. On shop PC, create project directory:
   ```bash
   mkdir C:\AutoDiag
   ```
3. Copy database from USB:
   ```bash
   copy E:\automotive_diagnostics.db C:\AutoDiag\
   ```
4. Verify database:
   ```bash
   cd C:\AutoDiag
   python -c "import sqlite3; conn = sqlite3.connect('automotive_diagnostics.db'); print('Vehicles:', conn.execute('SELECT COUNT(*) FROM vehicles').fetchone()[0])"
   ```

**Update Deployment**:

1. Copy updated database to USB
2. On shop PC, backup existing database:
   ```bash
   copy C:\AutoDiag\automotive_diagnostics.db C:\AutoDiag\automotive_diagnostics_old.db
   ```
3. Copy new database:
   ```bash
   copy E:\automotive_diagnostics.db C:\AutoDiag\
   ```

---

## Next Steps

After completing setup:

1. **Import Remaining Data**
   - Import all 20 years of vehicle data
   - Import common failures database
   - Import OBD-II diagnostic codes

2. **Configure Claude Code**
   - Install Claude Code CLI
   - Configure diagnostic skills
   - Test end-to-end diagnostic workflow

3. **Set Up Backup Strategy**
   - Choose cloud sync provider (OneDrive/Dropbox)
   - Configure automatic backups
   - Test restore procedure

4. **Deploy to Shop PC**
   - Follow shop PC deployment steps
   - Train shop personnel
   - Establish update schedule

---

## Additional Resources

### Documentation
- [Project Status](PROJECT_STATUS.md) - Current status and roadmap
- [Database Architecture](DATABASE_ARCHITECTURE.md) - Schema design details
- [Main README](../README.md) - Project overview

### Database Scripts
- `databases/schema.sql` - Complete database schema
- `databases/init_database_simple.py` - Database initialization
- `databases/import_vehicles.py` - Vehicle data importer

### Support

For issues or questions:
1. Check troubleshooting section above
2. Review database architecture documentation
3. Verify all prerequisites are met
4. Check Python and SQLite versions

---

## Appendix: Quick Reference

### Common Commands

**Create database**:
```bash
python init_database_simple.py --force
```

**Verify schema**:
```bash
python init_database_simple.py --verify
```

**Import vehicles**:
```bash
python import_vehicles.py --file "data.txt" --year 2005
```

**Show statistics**:
```bash
python init_database_simple.py --stats
```

**Backup database**:
```bash
copy automotive_diagnostics.db automotive_diagnostics_backup.db
```

### Directory Structure

```
automotive-diagnostic-skills/
├── databases/
│   ├── schema.sql                    # Database schema
│   ├── init_database_simple.py       # Database initialization
│   ├── import_vehicles.py            # Vehicle importer
│   └── automotive_diagnostics.db     # SQLite database (not in git)
├── docs/
│   ├── PROJECT_STATUS.md             # Project status
│   ├── DATABASE_ARCHITECTURE.md      # Schema documentation
│   └── SETUP_GUIDE.md                # This file
├── skills/                            # Claude skills (future)
├── tools/                             # Helper utilities (future)
└── README.md                          # Project overview
```

---

**Setup Guide Version**: 1.0
**Last Updated**: November 2, 2025
**Compatible With**: Schema version 1.0
