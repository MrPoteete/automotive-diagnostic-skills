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

## ChromaDB — Prefer API Deletion Over File Wipe for Single Collection

**Symptom**: One ChromaDB collection is corrupted (HNSW index error) but other collections are healthy.

**Root Cause**: Large background imports can leave the HNSW index in an inconsistent state (ChromaDB 1.0.x Rust backend). The `mechanics_forum` collection fails with `Error loading hnsw index` while other collections (e.g., test collections) remain intact.

**Wrong** (nuclear — destroys ALL collections):
```bash
find data/vector_store/chroma -type f -delete  # ❌ wipes everything
```

**Correct** (surgical — only removes the broken collection):
```python
import chromadb
client = chromadb.PersistentClient(path='data/vector_store/chroma')
client.delete_collection('mechanics_forum')  # ✅ preserves other collections
```

Then re-run the import script. The file-wipe option in DATA.md is the last resort — use API deletion first.

---

## Frontend — Carbon + Tailwind Coexistence

**Symptom**: After adding `@carbon/react`, CSS resets conflict with Tailwind's base styles — buttons, inputs, and layout break in unpredictable ways.

**Root Cause**: `@tailwind base` and `@tailwind components` inject CSS resets that fight Carbon's own reset layer.

**Wrong**:
```css
@tailwind base;       /* ❌ fights Carbon's resets */
@tailwind components; /* ❌ fights Carbon's component styles */
@tailwind utilities;
@import '@carbon/styles/css/styles.css';
```

**Correct** — Carbon first, Tailwind utilities only:
```css
/* globals.css */
@import '@carbon/styles/css/styles.css';  /* ✅ Carbon resets and components */
@tailwind utilities;                       /* ✅ utilities only — no conflicts */
```

Also add to `next.config.mjs`:
```js
experimental: { transpilePackages: ['@carbon/react', '@carbon/icons-react'] }
```

---

## Playwright E2E — `<option>` Elements Are Never "Visible"

**Symptom**: `waitForSelector('#select option[value="X"]')` times out even though the option exists in the DOM.

**Root Cause**: Playwright's default `waitForSelector` state is `visible`. `<option>` elements inside `<select>` are always hidden in headless browsers — they only "appear" when the dropdown is open.

**Wrong**:
```typescript
await page.waitForSelector('#my-select option[value="FORD"]', { timeout: 5000 }); // ❌ always times out
```

**Correct**:
```typescript
await page.waitForSelector('#my-select option[value="FORD"]', { state: 'attached', timeout: 5000 }); // ✅
```

---

## Playwright E2E — Strict Mode Violation on Short Text Locators

**Symptom**: `Error: strict mode violation: locator('text=FORD') resolved to 3 elements`

**Root Cause**: Short text like `text=FORD` matches everywhere — dropdown options, summary bars, labels. Playwright strict mode rejects ambiguous locators.

**Wrong**:
```typescript
await expect(page.locator('text=FORD')).toBeVisible(); // ❌ may match option + summary bar + label
```

**Correct** — use a structurally unique element:
```typescript
// The "Change" button only appears in the vehicle summary bar after selection
await expect(page.locator('button:has-text("Change")')).toBeVisible(); // ✅
```

**Rule**: For short text that could appear in dropdowns, use a parent container or a unique sibling to scope the locator.

---

## Playwright E2E — Carbon `hasIconOnly` Buttons Need `data-testid`

**Symptom**: `button[aria-label="Close"]` selector never resolves — test times out.

**Root Cause**: Carbon's `Button` with `hasIconOnly` does not consistently expose `aria-label` across versions. The `iconDescription` prop may render as a tooltip/title, not an `aria-label`.

**Wrong**:
```typescript
await page.locator('button[aria-label="Close"]').click(); // ❌ unreliable across Carbon versions
```

**Correct** — add `data-testid` to the component:
```tsx
<Button data-testid="close-modal" hasIconOnly renderIcon={Close} iconDescription="Close" />
```
```typescript
await page.locator('[data-testid="close-modal"]').click(); // ✅ always works
```

**Rule**: Always add `data-testid` to Carbon `hasIconOnly` buttons that need e2e targeting.

---

---

## Playwright E2E — FORD F-150 2020 Has 0 Complaints in FTS Index

**Symptom**: Tests for `[data-testid="component-bar"]` time out even though the vehicle selects successfully and the dashboard loads.

**Root Cause**: `complaints_fts` only contains "F-150 REGULAR CAB", "F-150 EXTENDED CAB", etc. — NOT plain "F-150". The exact model value "F-150" returns 0 complaints for 2020 and the `top_components` array is empty, so the component bars never render.

**Fix**: Use **FORD ESCAPE 2020** (1,347 complaints) for tests that require the top-components bar:
```typescript
// Use FORD ESCAPE 2020 — FORD F-150 2020 has 0 complaints in complaints_fts
async function selectFordEscape2020(page) { ... }
await page.selectOption('#manual-model', 'ESCAPE');
await page.selectOption('#manual-year', '2020');
```

**Rule**: Before writing a complaint-based Playwright test, verify the test vehicle has data: `SELECT COUNT(*) FROM complaints_fts WHERE make=? AND model=? AND CAST(year AS INTEGER)=?`

---

*Add new entries above this line. Keep entries concise — root cause + fix only.*
