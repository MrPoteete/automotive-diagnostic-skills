# Linting Errors - TODO for Gemini

**Date**: 2026-02-13
**Status**: ⏳ Pending - Deferred to next session
**Assignee**: Gemini Flash (routine code cleanup)

---

## Summary

Pre-commit hook caught **30 linting errors** in 12 Python files. Ruff auto-fixed **21 errors**, leaving **18 errors** for manual fixing.

**Task**: Delegate these mechanical fixes to Gemini Flash tomorrow.

---

## Error Categories

| Error Code | Count | Description | Auto-fixable? |
|------------|-------|-------------|---------------|
| E701 | 13 | Multiple statements on one line (colon) | ❌ Manual |
| F401 | 13 | Unused imports | ✅ Auto-fixed |
| F541 | 3 | f-string without placeholders | ✅ Auto-fixed |
| E722 | 1 | Bare except clause | ❌ Manual |
| F841 | 1 | Unused variable | ❌ Manual |
| F811 | 1 | Duplicate function definition | ❌ Manual |

**Total Remaining**: 16 manual fixes needed

---

## Files Needing Fixes

### 1. `skills/router_skill/scripts/classify_problem.py` (13 E701 errors)

**Error**: Multiple statements on one line (colon)

**Lines with Issues**:
```python
# Line 240
if year: search_parts.append(str(year))

# Line 241
if make: search_parts.append(make)

# Line 242
if model: search_parts.append(model)

# Line 246
if symptoms: search_parts.append(symptoms)

# Line 264
if year: fallback_parts.append(str(year))

# Line 265
if make: fallback_parts.append(make)

# Line 266
if model: fallback_parts.append(model)

# Line 268
if symptoms: fallback_parts.append(symptoms)

# Line 291
if year: tsb_parts.append(str(year))

# Line 292
if make: tsb_parts.append(make)

# Line 293
if model: tsb_parts.append(model)

# Line 294
if obd_code: tsb_parts.append(obd_code)

# Line 295
if domain and domain != "unknown": tsb_parts.append(domain)
```

**Solution**: Split each onto separate lines:
```python
# BEFORE (wrong)
if year: search_parts.append(str(year))

# AFTER (correct)
if year:
    search_parts.append(str(year))
```

**Gemini Prompt**:
```
Fix all E701 errors in skills/router_skill/scripts/classify_problem.py by
splitting one-line if statements onto separate lines. Maintain exact logic
and formatting except for the colon placement.
```

---

### 2. `server/rag_dashboard.py` (1 E722 error)

**Error**: Bare except clause

**Line 69-71**:
```python
    except:
        st.error("❌ Server Offline")
        st.info("Run 'start_server.bat' to fix.")
```

**Solution**: Specify exception type:
```python
    except Exception as e:
        st.error("❌ Server Offline")
        st.info("Run 'start_server.bat' to fix.")
```

**Gemini Prompt**:
```
Fix bare except clause at line 69 in server/rag_dashboard.py by
specifying 'except Exception as e:' instead of bare 'except:'
```

---

### 3. `server/scripts/teacher_analyze.py` (1 F841 error)

**Error**: Unused variable

**Line 54**:
```python
trace = latest['error'].get('traceback', 'No traceback')
```

**Solution**: Remove assignment or use the variable:
```python
# Option 1: Remove it (if truly unused)
# Delete line 54

# Option 2: Use it in error message
_trace = latest['error'].get('traceback', 'No traceback')
```

**Gemini Prompt**:
```
Fix unused variable 'trace' at line 54 in server/scripts/teacher_analyze.py
by either removing it or prefixing with underscore if it's for future use.
```

---

### 4. `scripts/inspect_tsb_file.py` (1 E701 error)

**Error**: Multiple statements on one line

**Line 7**:
```python
if i >= 50: break
```

**Solution**:
```python
if i >= 50:
    break
```

**Gemini Prompt**:
```
Fix E701 error at line 7 in scripts/inspect_tsb_file.py by splitting
'if i >= 50: break' onto separate lines.
```

---

### 5. `scripts/inspect_tsb_file_v2.py` (1 E701 error)

**Error**: Multiple statements on one line

**Line 8**:
```python
if i >= 20: break
```

**Solution**:
```python
if i >= 20:
    break
```

**Gemini Prompt**:
```
Fix E701 error at line 8 in scripts/inspect_tsb_file_v2.py by splitting
'if i >= 20: break' onto separate lines.
```

---

### 6. `server/data_miner.py` (1 F811 error)

**Error**: Duplicate function definition

**Line 168**:
```python
def save_complaints(conn, complaints, make, model, year):
    # Redefinition of function from line 72
```

**Solution**:
- Either remove one definition
- Or rename one if both are needed
- Check which one is the correct implementation

**Gemini Prompt**:
```
Fix duplicate function 'save_complaints' in server/data_miner.py
(defined at lines 72 and 168). Compare implementations and remove
the incorrect/outdated one or rename if both are needed.
```

---

## MyPy Type Errors (Lower Priority)

**File**: `skills/router_skill/scripts/classify_problem.py`

**Errors**:
1. Line 17: Missing type stubs for `requests` library
2. Line 92: Incompatible return value (returns None, expects str)
3. Line 151: Incompatible default for `year` parameter
4. Line 151: Incompatible default for `engine` parameter
5. Line 180: Incompatible default for `year` parameter

**File**: `server/rag_dashboard.py`
1. Line 3: Missing type stubs for `requests` library

**Solution**: Add type annotations and install type stubs:
```bash
pip install types-requests
```

**Note**: These are warnings, not blocking errors. Can be deferred.

---

## Gemini Flash Workflow for Tomorrow

### Step 1: Review Errors
```
Gemini, review the linting errors in .claude/LINTING_ERRORS_TODO.md
and understand what needs to be fixed.
```

### Step 2: Generate Fixes
```
For each file with E701 errors:
1. Read the file
2. Identify all one-line if statements
3. Generate fixed version with proper formatting
4. Show me the diff
```

### Step 3: Apply Fixes
```
After review, apply all fixes to:
- skills/router_skill/scripts/classify_problem.py
- server/rag_dashboard.py
- server/scripts/teacher_analyze.py
- scripts/inspect_tsb_file.py
- scripts/inspect_tsb_file_v2.py
- server/data_miner.py
```

### Step 4: Validate
```bash
# Run linting after Gemini fixes
ruff check scripts/ server/ skills/
mypy scripts/ server/ skills/ --ignore-missing-imports
```

### Step 5: Commit
```bash
git add -A
git commit -m "fix: Resolve linting errors (E701, E722, F841, F811)

- Split one-line if statements onto separate lines (E701)
- Replace bare except with Exception (E722)
- Remove unused variables (F841)
- Remove duplicate function definitions (F811)

Fixed by: Gemini Flash
Validated by: Claude

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>"
```

---

## Lessons Learned

### What Worked ✅
- Pre-commit hooks caught issues before commit
- Ruff auto-fixed 21/30 errors automatically
- Unstaging problematic files allowed clean commit tonight

### What to Improve ⏳
- Delegate linting fixes to Gemini Flash upfront
- Set up formatter to auto-fix on save (VS Code/Cursor)
- Add ruff format to pre-commit hook

### Process Improvement
**Tomorrow's workflow**:
1. Claude identifies files needing fixes
2. **Gemini Flash**: Reads files and generates fixes
3. Claude reviews fixes for correctness
4. Gemini applies fixes
5. Claude validates with ruff/mypy
6. Commit and push

**Token savings**: ~80% (Gemini does mechanical work, Claude validates)

---

## Reference

**Ruff Documentation**: https://docs.astral.sh/ruff/rules/
- E701: https://docs.astral.sh/ruff/rules/multiple-statements-on-one-line-colon/
- E722: https://docs.astral.sh/ruff/rules/bare-except/
- F401: https://docs.astral.sh/ruff/rules/unused-import/
- F541: https://docs.astral.sh/ruff/rules/f-string-missing-placeholders/
- F841: https://docs.astral.sh/ruff/rules/unused-variable/

**MyPy**: https://mypy.readthedocs.io/

---

## Status

- [x] Errors logged
- [x] Solutions documented
- [x] Gemini prompts prepared
- [ ] Fixes applied (tomorrow)
- [ ] Validation passed (tomorrow)
- [ ] Committed and pushed (tomorrow)

**Ready for**: Gemini Flash to handle tomorrow morning! ☕
