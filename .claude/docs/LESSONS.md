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

### uv run Has No Access to requirements.txt Without pyproject.toml

**Symptom**: `uv run python scripts/foo.py` fails with `ModuleNotFoundError` for packages in requirements.txt.

**Root Cause**: This project has no `pyproject.toml` or `uv.lock`. `uv run` only resolves deps from pyproject.toml — it ignores requirements.txt entirely.

**Fix**: Use `uv run --with <package>` for one-offs:
```bash
uv run --with requests python -u scripts/import_nhtsa_recalls_api.py --full
```
Or for scripts with many deps, run them with the system python that has the venv active, or create a pyproject.toml.

**Note**: Always add `-u` flag for unbuffered output when running long jobs to background (`> logfile 2>&1 &`).

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

---

## NHTSA vPIC API — Field Names Use Spaces and Parentheses, Not camelCase

**Symptom**: VIN decode returns `valid: true` but `year`, `engine`, `drive_type`, `body_class`, `fuel_type` are all `null`.

**Root Cause**: NHTSA vPIC API returns variable names with spaces and punctuation (e.g. `"Model Year"`, `"Displacement (L)"`, `"Engine Number of Cylinders"`, `"Drive Type"`, `"Body Class"`, `"Fuel Type - Primary"`). Code was using camelCase keys (`"ModelYear"`, `"DisplacementL"`, etc.) that never matched.

**Fix**: Use exact NHTSA variable names as dictionary keys:
```python
fields.get("Model Year")          # not "ModelYear"
fields.get("Displacement (L)")    # not "DisplacementL"
fields.get("Engine Number of Cylinders")  # not "EngineCylinders"
fields.get("Drive Type")          # not "DriveType"
fields.get("Body Class")          # not "BodyClass"
fields.get("Fuel Type - Primary") # not "FuelTypePrimary"
```

**Rule**: Always inspect the raw NHTSA API response before writing field lookups — variable names are human-readable strings, not camelCase identifiers.

---

## NHTSA vPIC ErrorCode "1" is Non-Fatal (Check Digit Warning Only)

**Symptom**: Valid VIN for a known vehicle (e.g. 2020 Chevy Silverado) returns `valid: false` with "NHTSA could not decode VIN (error 1)".

**Root Cause**: Code blocked on any non-"0" error code. NHTSA error code `"1"` means "Check Digit (9th position) incorrect" — a warning only. The vehicle data (make, model, year, engine) is fully decoded. This is extremely common on trucks and older vehicles.

**Fix**: Only treat truly fatal codes as decode failures:
```python
FATAL_ERROR_CODES = {"7", "8", "14"}  # undecodable VINs
if error_code in FATAL_ERROR_CODES or (not fields.get("Make") and not fields.get("Model")):
    return {"valid": False, ...}
```

**Rule**: Check if make+model are populated rather than relying solely on error code. Codes 7 (incomplete), 8 (invalid), 14 (unknown make) are the only fatal failures.

---

## Diagnostic Skill Protocol — Three-Layer Enforcement Required

**Symptom**: Claude bypasses `skills/SKILL.md` for automotive diagnoses — skips routing header, categorical assessment levels, SOURCES/DISCLAIMER sections, and manufacturer protocols.

**Root Cause**: No automatic trigger exists to load skill files. Without explicit instruction, Claude defaults to direct API calls and ad-hoc responses rather than the structured 7-phase ASE framework.

**Fix**: Three enforcement layers (all required — each one alone is insufficient):

1. **CLAUDE.md mandatory section** — explicit trigger conditions + required steps loaded every session
2. **`/diagnose` slash command** — `.claude/commands/diagnose.md` with full protocol steps
3. **UserPromptSubmit hook** — 4-tier detection (DTC regex / strong keywords / year+make+symptom / multi-symptom) injects skill reminder as `context` into every diagnostic conversation automatically

**Rule**: Use `/diagnose` for all vehicle diagnostic conversations. The hook provides a safety net for implicit diagnostic messages, but the command is the most reliable enforcement path.

---

## NHTSA Recall Data — Bulk Flat File Blocked, Use Live API

**Symptom**: `https://static.nhtsa.gov/odi/ffdd/rcl/FLAT_RCL_POST_2010.zip` returns 403. `RCL.txt` data dictionary also blocked.

**Root Cause**: NHTSA S3 bucket restricts direct file access from non-browser clients. The bulk `FLAT_RCL.txt` was also deleted from S3 (known issue from prior session).

**Working Alternative**: Live API with User-Agent header:
```python
headers = {"User-Agent": "Mozilla/5.0"}
url = f"https://api.nhtsa.gov/recalls/recallsByVehicle?make={make}&model={model}&modelYear={year}"
```
Returns full recall records including `Summary`, `Consequence`, `Remedy`, `Component`, `NHTSACampaignNumber`.

**400 errors are benign**: NHTSA recalls API returns 400 for model years that predate or postdate a model's production run (e.g. Chrysler 200 for 2019 — discontinued 2017), or for sub-model variants from complaints_fts that don't exist in the recalls system (e.g. "CIVIC SEDAN" vs "CIVIC"). Script handles these gracefully and continues.

**Script**: `scripts/import_nhtsa_recalls_api.py` — checkpoint/resume, deduplicates by (campaign_no, make, model), aggregates year_from/year_to.

---

## NHTSA Recall PDFs (RCRIT) — No Public Document Index API

**Symptom**: Cannot programmatically list recall documents for a given campaign number.

**Root Cause**: The document-listing API (`/recalls/{campaignNo}/documents`) returns 403 — requires manufacturer portal auth. No public index exists.

**What Works**: Documents ARE on public S3 at a predictable path:
```
https://static.nhtsa.gov/odi/rcl/{YYYY}/RCRIT-{YYV###}-{doc_id}.PDF
```
Where `doc_id` is a timestamp-based sequence number (~1000–9999 range). Brute-force scanning ~400 IDs per campaign finds documents. Use S3 `x-amz-meta-doctype` header to identify document type.

**Document types**: `RCRIT` = repair instructions (what mechanics need), `RCLRPT` = Part 573 defect report, `RCMN` = dealer notice, `RCONL` = owner letter.

**Current status**: PDF pipeline deferred — live API `Remedy` text field covers ~80% of use case without PDF complexity.

---

## Automotive Diagnostic Patterns → Separate File

Confirmed vehicle diagnostic case patterns (AC, engine, transmission, etc.) are stored in:
`skills/references/case-patterns.md`

Load that file during `/diagnose` when a current case matches a known pattern. Do NOT add automotive failure patterns here — this file is for code/tool/process errors only.

---

## WSL Headless Chromium Crashes for PDF Generation — Use Node.js Playwright

**Symptom**: `Trace/breakpoint trap (core dumped)` when running Chromium `--headless=new --print-to-pdf` in WSL.

**Root Cause**: The Playwright Chromium binary (installed via `npx playwright install`) crashes in WSL headless mode when called directly via subprocess with `--print-to-pdf`.

**Wrong**:
```python
subprocess.run([chromium_path, "--headless=new", "--print-to-pdf=out.pdf", "file://in.html"])
# ❌ crashes in WSL with Trace/breakpoint trap
```

**Correct**: Use the Node.js Playwright API instead — it works correctly in WSL:
```javascript
// scripts/pdf_from_html.js
const { chromium } = require('../src/frontend/node_modules/@playwright/test');
const browser = await chromium.launch();
const page = await browser.newPage();
await page.setContent(html);
await page.pdf({ path: outputPdf, format: 'Letter', printBackground: true });
```
```python
subprocess.run(["node", "scripts/pdf_from_html.js", input_html, output_pdf])  # ✅
```

**Rule**: In WSL, always use `node` + Playwright API for HTML→PDF. Never call the Chromium binary directly for PDF generation.

---

## Delegation Hook — Acknowledgment Must Appear in Written Content

**Symptom**: Hook blocks Edit even though the acknowledgment comment exists at the top of the file.

**Root Cause**: The delegation hook reads `tool_input["content"]` (the new content being written in the Edit), not the full file. A comment at the top of the file is not visible to the hook when editing a different section.

**Fix**: Include the acknowledgment in the `new_string` of the specific Edit being blocked:
```python
# ✅ Include in the replacement string itself
"<!-- Checked AGENTS.md - implementing directly because [reason] -->\n"
```

**Rule**: When the delegation hook blocks an Edit, add the acknowledgment comment directly into the `new_string`, not just at the top of the file.

---

## archive.org Downloads — Use `internetarchive` Package, Not wget

**Symptom**: `wget` downloads a 0-byte file; CDN server returns 404 even though metadata confirms the file exists.

**Root Cause**: archive.org redirects to CDN nodes, but the specific node selected may not have the file cached/available at that moment. Plain `wget` follows the redirect to a 404-returning node.

**Wrong**:
```bash
wget -O file.7z "https://archive.org/download/collection_id/file.7z"  # ❌ 404 from CDN
```

**Correct**: Use the `internetarchive` Python package — it handles node selection and retries internally:
```python
import internetarchive as ia
item = ia.get_item('stackexchange_20250331')
item.download(
    files=['stackexchange_20250331/mechanics.stackexchange.com.7z'],  # ← full prefixed name
    destdir='data/raw_imports/stackexchange_dump/',
    no_directory=True,
    verbose=True
)
```

**Key**: the `files` list must use the **full prefixed filename** (as returned by `item.files`) — e.g. `stackexchange_20250331/mechanics.stackexchange.com.7z`, not just `mechanics.stackexchange.com.7z`. Download lands in a `stackexchange_20250331/` subdirectory.

**Install**: `.venv/bin/pip install internetarchive`

---

## Import Scripts — `ensure_schema` vs `drop_and_recreate_schema`

**Symptom**: Resume/checkpoint run wipes all previously imported data and only imports the newly-added records.

**Root Cause**: `drop_and_recreate_schema()` called unconditionally at startup — runs before checkpoint loading, so data is destroyed before the checkpoint can prevent re-fetching.

**Fix**: Add a non-destructive `ensure_schema()` that only creates tables if they don't exist, and call it on normal runs; reserve `drop_and_recreate_schema()` for `--reset` only:
```python
if reset:
    drop_and_recreate_schema(conn)
else:
    ensure_schema(conn)  # CREATE TABLE IF NOT EXISTS — preserves existing data
```

**Rule**: Any import script with checkpoint/resume MUST use non-destructive schema creation on normal runs. `DROP TABLE` should only happen on explicit `--reset`.

---

## NHTSA Recalls API — Year Range vs Exact Year

**Symptom**: Dashboard shows 0 recalls for a vehicle year even though recalls exist in the DB.

**Root Cause**: `nhtsa_recalls` uses `year_from`/`year_to` INTEGER range fields (a recall covers multiple years). Querying `WHERE year = ?` (exact match) returns 0 rows because that column doesn't exist. The complaints/TSBs tables use a single `year` TEXT column — different schema.

**Correct query**:
```sql
WHERE UPPER(make) = ? AND UPPER(model) = ?
  AND (year_from IS NULL OR year_from <= ?)
  AND (year_to IS NULL OR year_to >= ?)
```

**Rule**: Recall year filtering always requires range logic (`year_from <= target_year AND year_to >= target_year`). Never use exact year match on `nhtsa_recalls`.

---

## NHTSA Recalls API — Sub-Variant Model Names Return 0 Results

**Symptom**: FORD, HONDA, CHEVROLET imported 0 recalls even though data exists.

**Root Cause**: `complaints_fts` stores sub-variant model names ("F-150 REGULAR CAB", "CIVIC SEDAN", "EQUINOX EV") but the NHTSA recalls API only recognises base model names ("F-150", "CIVIC", "EQUINOX"). All API calls for sub-variant names return 0 records.

**Fix**: Normalise model names before querying the recalls API — strip cab designators (REGULAR CAB, CREW CAB, etc.), fuel/powertrain suffixes (GAS, HEV, PHEV, BEV, EV, HYBRID), and body styles (SEDAN, HATCHBACK, COUPE). Use word-boundary regex to avoid stripping substrings (e.g. "abs" in "absolute"). Deduplicate normalised names before querying.

**Rule**: Never pass raw `complaints_fts` model names directly to the NHTSA recalls API. Always call `normalize_model()` first.

---

## Security — 2026-03-29 Audit Findings

### Wildcard Allow Rules Are a Critical Attack Surface

**Root cause**: `settings.local.json` entries like `Bash(sudo sh:*)`, `Bash(curl:*)`, `Bash(chmod:*)` grant unbounded capability to any prompt injection that clears the PreToolUse gate.

**Fix**: Use specific patterns (`Bash(curl:https://api.nhtsa.gov:*)`) or remove the rule entirely. One-off session commands must be removed after use — they accumulate and widen the attack surface with each session.

**Rule**: Audit `settings.local.json` after every session that adds allow rules. No wildcard rules for root shells, network fetch, or file permissions.

---

### Hook Self-Sabotage Bypasses Write/Edit Protection

**Root cause**: `pre_tool_use.py` blocked Write/Edit to `.claude/hooks/` but not Bash commands. An injected `chmod 777 .claude/hooks/pre_tool_use.py && echo "exit 0" > .claude/hooks/pre_tool_use.py` would disable the hook entirely via Bash.

**Fix**: `check_hooks_modification()` now also intercepts Bash commands containing `chmod`, `echo`, `printf`, `tee`, or `sed -i` that target `.claude/hooks/` paths.

**Rule**: Any protection for a file path must cover both Write/Edit tool calls AND Bash write operations (redirection, in-place sed, chmod). Covering only one channel leaves the other open.

---

### MCP Tool Responses Are a Blind Spot for Injection Scanning

**Root cause**: The PostToolUse prompt-injection-defender was registered only for `Write|Edit`. MCP tool responses (Telegram, Gmail, Zapier, Figma, Canva, etc.) returned arbitrary external content that was never scanned.

**Fix**: Added `"matcher": "mcp__.*"` PostToolUse entry in `.claude/settings.json` pointing to `post-tool-defender.py`.

**Rule**: Any new MCP integration is automatically covered by the `mcp__.*` matcher. If the defender is ever moved or renamed, update both the `Write|Edit` and `mcp__.*` entries together.

---

### Multi-Line Injection Evades Single-Line Regex

**Root cause**: Injection patterns split across newlines (e.g. `ignore\nprevious instructions`) bypassed all `re.search()` calls in `post-tool-defender.py` because Python regex does not match `.` across newlines by default.

**Fix**: Added `re.DOTALL` flag to all pattern matching in `post-tool-defender.py`.

**Rule**: All regex used for security scanning must include `re.DOTALL`. Single-line mode is the wrong default when scanning multi-line tool output from external sources.

---

### Hardcoded Key Fallbacks Defeat Key Rotation

**Root cause**: `process.env.API_KEY ?? 'mechanic-secret-key-123'` in 10 API proxy routes meant rotating the `.env` key had no effect — the old key remained active in the fallback.

**Fix**: All fallbacks changed to `?? ''`. A missing `API_KEY` now causes requests to fail with 401 rather than silently using a known-bad key.

**Rule**: Fallback values for secrets must always be `''` or equivalent failure-mode values, never a default key string. A 401 failure is visible and fixable; a silently accepted insecure key is not.

---

*Add new entries above this line. Keep entries concise — root cause + fix only.*
