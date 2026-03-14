# Lessons Learned — Error Playbook

**Purpose**: Record errors, their root causes, and proven solutions to prevent repetition.

**How to use**:
- When a mistake is corrected, add an entry here immediately
- Reference this file at session start for known pitfalls
- Format: `## [Category] — [Short Description]`

---

## Hook Development

### Exit Code Controls Blocking (NOT JSON decision)

**Symptom**: Hook blocks when it shouldn't, or allows when it should block.

**Root Cause**: Confusion between exit code behavior and JSON `decision` field.

**Wrong**:
```python
if should_block:
    print(json.dumps({"decision": "block", "reason": "..."}))
    sys.exit(1)  # exit code does NOT control blocking
```

**Correct**:
```python
if should_block:
    print(json.dumps({"decision": "block", "reason": "..."}))
    sys.exit(0)  # ALWAYS exit(0); JSON decision field controls blocking

sys.exit(0)  # Allow
```

**Rule**: Exit code `0` = hook ran successfully. The `decision: "block"` JSON output controls whether the tool is blocked. A non-zero exit code signals hook *failure*, not intentional blocking.

---

### Hooks Cannot Read Conversation History

**Symptom**: Hook logic tries to check previous messages or conversation context.

**Root Cause**: Hooks only receive `tool_name`, `tool_input`, and `session_id`.

**Correct approach**: Analyze `tool_input["content"]`, `tool_input["description"]`, or read the target file directly.

---

## Python / Type Checking

### mypy Strict Mode Requires Explicit Return Types

**Symptom**: `mypy_validator.py` blocks after editing a function — "Missing return type annotation".

**Fix**: Always annotate return types on functions in `.py` files:
```python
def validate_dtc(code: str) -> bool:  # ✅
def validate_dtc(code: str):           # ❌ mypy strict will reject
```

---

### Ruff F401 — Unused Import After Refactor

**Symptom**: `ruff_validator.py` blocks with "F401 imported but unused".

**Fix**: Remove the unused import. Do not suppress with `# noqa` unless it's a re-export.

---

## Automotive Domain

### DTC Regex Pattern

**Correct pattern**: `^[PCBU][0-3][0-9A-F]{3}$`

| Position | Valid values | Meaning |
|----------|-------------|---------|
| 0 | P, C, B, U | Powertrain, Chassis, Body, Network |
| 1 | 0–3 | Code type |
| 2–4 | 0–9, A–F | Specific fault |

**Common mistake**: Using `[0-9a-f]` (lowercase) — DTC codes use uppercase hex only.

---

### Safety-Critical Confidence Threshold

**Rule**: Confidence must be `>= 0.9` for safety-critical systems (brakes, airbags, steering).

**Common mistake**: Using `> 0.9` (strict greater-than) which rejects valid 0.9 scores.

---

## Data Integrity

### NEVER Modify `data/raw_imports/`

**Symptom**: Processed data diverges from source, reproducibility lost.

**Rule**: `data/raw_imports/` is immutable source truth. Write processed outputs to `data/processed/`.

---

## Gemini Delegation

### Gemini MCP Lacks Vision/Image Tools

**Symptom**: Delegating image analysis to Gemini via MCP returns empty or error.

**Rule**: Image analysis stays with Claude. Gemini MCP does not have vision capabilities.

---

## Session Management

### Run pytest Before Any Changes

**Rule**: Always run `.venv/bin/pytest --tb=no -q` at session start to establish a baseline.

**Why**: Changes made without a passing baseline make it impossible to attribute regressions.

---

## Data Import / CSV Parsing

### csv.DictReader Uses First Row as Header by Default

**Symptom**: All rows skipped during import — column lookups return empty strings.

**Root Cause**: `csv.DictReader(f)` treats the first data row as column names when the file has no header row. Every subsequent `row.get("Code", "")` returns `""` because the column names are the first data values.

**Wrong**:
```python
reader = csv.DictReader(f)  # ❌ first data row becomes the header
```

**Correct**:
```python
reader = csv.DictReader(f, fieldnames=["Code", "Description"])  # ✅ explicit names
```

**Applies to**: Any CSV without a header row (e.g. `obd-trouble-codes.csv`, some NHTSA flat files).

---

## Python / String Matching

### Substring `in` Check Matches Partial Words

**Symptom**: DTC subsystem classifier tagged `P0106` (MAP/Manifold Absolute Pressure sensor) as `ABS` subsystem.

**Root Cause**: `"abs" in "manifold absolute pressure..."` is `True` because "abs" is a substring of "absolute". Same issue with `"map" in "remap"` or `"can" in "scan"`.

**Wrong**:
```python
if "abs" in description.lower():  # ❌ matches "absolute", "absorption"
    return "ABS"
```

**Correct**:
```python
import re
if re.search(r"\babs\b", description.lower()):  # ✅ word boundary — "abs" only
    return "ABS"
```

**Rule**: Use `re.search(r"\b<word>\b", text)` whenever matching short acronyms or words that could appear as substrings (abs, map, can, cat, egr, tcs, etc.).

---

## Hook Development — precommit_validator Falls Back to `python3 -m pytest` When No Venv

**Symptom**: Pre-commit hook blocks with "No module named pytest" even though `pytest` is installed system-wide.

**Root Cause**: The hook only checks `.venv/bin/pytest`, then falls back to `python3 -m pytest`. If the venv doesn't exist and pytest is installed as a standalone binary (e.g., `/root/.local/bin/pytest`), it's never found.

**Fix**: Add `shutil.which("pytest")` as a middle fallback in `precommit_validator.py`:
```python
if venv_pytest.exists():
    pytest_cmd = [str(venv_pytest), ...]
elif shutil.which("pytest"):
    pytest_cmd = [shutil.which("pytest"), ...]
else:
    pytest_cmd = ["python3", "-m", "pytest", ...]
```

---

*Add new entries above this line. Keep entries concise — root cause + fix only.*
