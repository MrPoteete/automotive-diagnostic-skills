# Testing Protocols

## Testing Framework

**Primary**: pytest with AAA pattern (Arrange-Act-Assert)

**Coverage Tool**: pytest-cov

---

## Coverage Targets

| Component | Target Coverage | Rationale |
|-----------|----------------|-----------|
| `diagnostic_engine` | 100% | Safety-critical logic |
| `safety_systems` | 100% | Safety-critical validation |
| `obd_parser` | 90% | Input validation, DTC parsing |
| `confidence_scoring` | 90% | Core business logic |
| `general utilities` | 80% | Support functions |

---

## Test Commands

### Run All Tests
```bash
pytest
```

### Run with Coverage
```bash
pytest --cov=src --cov-report=term-missing
```

### Run Specific Test Categories
```bash
# Unit tests only
pytest -m unit

# Integration tests only
pytest -m integration

# Safety-critical tests only
pytest -m safety
```

---

## Test Organization

Use `pytest.mark` for categorization:

```python
import pytest

@pytest.mark.unit
@pytest.mark.safety
def test_safety_critical_validation():
    """Test safety-critical system detection."""
    # Arrange
    component = "brake system"

    # Act
    is_critical, level = check_safety_critical(component)

    # Assert
    assert is_critical is True
    assert level == "CRITICAL"

@pytest.mark.integration
def test_dtc_code_lookup():
    """Test DTC code lookup in database."""
    # Arrange
    db = get_test_database()
    code = "P0300"

    # Act
    result = db.lookup_dtc(code)

    # Assert
    assert result is not None
    assert result['code'] == "P0300"
```

---

## Test Fixtures

**Database Fixture** (for integration tests):
```python
@pytest.fixture
def test_db():
    """Create test database with sample data."""
    db = create_test_database()
    db.load_test_data()
    yield db
    db.cleanup()
```

**Sample Data Fixture**:
```python
@pytest.fixture
def sample_vehicle():
    """Sample vehicle for testing."""
    return {
        'make': 'FORD',
        'model': 'F-150',
        'year': 2018,
        'engine': '5.0L V8'
    }
```

---

## Safety-Critical Testing Requirements

**For safety-critical systems** (brakes, airbags, steering):

1. **Test invalid inputs**: null, empty, malformed
2. **Test boundary conditions**: min/max values
3. **Test confidence thresholds**: Must reject < 0.9 confidence
4. **Test warning generation**: Verify warnings displayed

**Example**:
```python
@pytest.mark.safety
def test_brake_system_low_confidence_rejected():
    """Ensure low-confidence brake diagnostics are rejected."""
    # Arrange
    diagnosis = create_diagnosis(
        component="brake system",
        confidence=0.7  # Below 0.9 threshold
    )

    # Act & Assert
    with pytest.raises(ConfidenceError):
        validate_safety_critical_diagnosis(diagnosis)
```

---

## Frontend Testing (Vitest)

**Location**: `src/frontend/`
**Framework**: Vitest + React Testing Library + `@testing-library/user-event` v14

### Run Commands

```bash
# From project root
cd src/frontend && node_modules/.bin/vitest run

# Verbose output (shows each test name)
cd src/frontend && node_modules/.bin/vitest run --reporter=verbose
```

### Mock Setup Pattern

All frontend page tests mock three things:

```tsx
// 1. TypewriterText — bypass setInterval animation
vi.mock('../components/TypewriterText', () => ({
    TypewriterText: ({ text }: { text: string }) => <div>{text}</div>,
}));

// 2. VehicleForm — static placeholder (handleSearch tests)
vi.mock('../components/VehicleForm', () => ({
    default: () => <div data-testid="mock-vehicle-form" />,
    parseDtcInput: () => [],
}));

// 3. Full api module — every method is vi.fn()
vi.mock('../../lib/api', () => ({
    api: {
        healthCheck: vi.fn(),
        diagnose: vi.fn(),
        formatDiagnosis: vi.fn(),
        searchComplaints: vi.fn(),
        searchTSBs: vi.fn(),
        formatResults: vi.fn(),
        formatError: vi.fn(),
        fetchVehicles: vi.fn(),
    },
}));

import { api } from '../../lib/api';
// Always use vi.mocked() wrapper for TypeScript type safety:
vi.mocked(api.diagnose).mockResolvedValue(DIAG_RESPONSE);
```

### VehicleForm Callback Capture (handleDiagnose tests)

When testing `handleDiagnose`, replace the static VehicleForm mock with one that **captures the `onDiagnose` callback** so tests can trigger it directly:

```tsx
// ESBUILD RULE: Declare types BEFORE vi.mock() calls (top-to-bottom processing)
type OnDiagnose = (vehicle: VehicleInfo, symptoms: string, dtcCodes: string[]) => void;
let capturedOnDiagnose!: OnDiagnose;

vi.mock('../components/VehicleForm', () => ({
    default: ({ onDiagnose, isProcessing }: { onDiagnose: OnDiagnose; isProcessing: boolean }) => {
        capturedOnDiagnose = onDiagnose;  // captured on each render
        return (
            <button
                data-testid="trigger-diagnose"
                disabled={isProcessing}
                onClick={() => capturedOnDiagnose(
                    { make: 'FORD', model: 'F-150', year: 2020 },
                    'engine shaking at idle',
                    []
                )}
            >DIAGNOSE</button>
        );
    },
    parseDtcInput: (_raw: string) => [],
}));

// In tests — invoke handleDiagnose directly:
render(<Home />);
await act(async () => { capturedOnDiagnose(vehicle, symptoms, dtcCodes); });
```

### Deferred Promise (Loading State Tests)

```tsx
function makeDeferred<T>() {
    let resolve!: (value: T) => void;
    let reject!: (reason?: unknown) => void;
    const promise = new Promise<T>((res, rej) => { resolve = res; reject = rej; });
    return { promise, resolve, reject };
}

// Usage:
const { promise, resolve } = makeDeferred<DiagnoseResponse>();
vi.mocked(api.diagnose).mockReturnValue(promise);

render(<Home />);
await user.click(screen.getByTestId('trigger-diagnose'));
expect(screen.getByText(/ANALYZING_DATA_STREAMS/i)).toBeInTheDocument();  // loading visible

await act(async () => { resolve(DIAG_RESPONSE); });
await waitFor(() =>
    expect(screen.queryByText(/ANALYZING_DATA_STREAMS/i)).not.toBeInTheDocument()
);
```

---

## Verification Protocol (Before Commits)

**Always run before committing**:
```bash
# 1. Python unit tests (fast — skips ChromaDB-heavy integration tests)
.venv/bin/pytest --tb=no -q --ignore=tests/integration   # ~5s, 280 tests

# 2. Python integration tests (slow — ChromaDB init takes ~2 min; run before final commit)
.venv/bin/pytest --tb=no -q tests/integration/           # ~2 min, 20 tests

# 3. Frontend tests
cd src/frontend && node_modules/.bin/vitest run          # ~2s

# 4. Check coverage
uv run pytest --cov=src --cov-report=term-missing

# 5. Verify safety tests pass
uv run pytest -m safety

# 6. Run linter
uv run ruff check .

# 7. Type checking
uv run mypy src/
```

**Hooks automatically enforce**: ruff, mypy (see `.claude/settings.json`)

---

## Known Pitfalls

### Integration Tests Are Slow (ChromaDB init ~2 min)

Integration tests in `tests/integration/` load ChromaDB on startup. This takes 2+ minutes per run.

**Rule**: For baseline verification during development, use `--ignore=tests/integration`. Run the full suite (including integration) only before the final commit.

```bash
# Quick baseline (development loop)
.venv/bin/pytest --tb=no -q --ignore=tests/integration

# Full suite (pre-commit only)
.venv/bin/pytest --tb=no -q
```

If a background task waiting for pytest times out at 30s, it's the integration tests — check the output file rather than re-running.

---

### Ruff E702: No Semicolons Between Statements

The `ruff_validator` PostToolUse hook enforces E702 — never use semicolons to chain statements on a single line in Python. The plan pattern of `list.append(a); list.append(b)` will block the Edit.

```python
# ❌ Blocked by ruff hook (E702)
where_extra += " AND make = ?"; params.append(make)

# ✅ Correct
where_extra += " AND make = ?"
params.append(make)
```

This applies to all Python files including `server/home_server.py` SQL builder patterns.

---

### Ruff E701: No Single-Line `if` Statements

The `ruff_validator` PostToolUse hook enforces E701 — never put the body of an `if` statement on the same line as the condition in Python. This is commonly triggered by early-return guards in CLI scripts and utility code.

```python
# ❌ Blocked by ruff hook (E701)
if value.lower() == 'quit': return

# ✅ Correct
if value.lower() == 'quit':
    return
```

This applies to all Python files including `interactive_diagnostic.py` and scripts with early-exit guard clauses. E701 and E702 are in the same ruff rule family — both blocked by the same hook.
