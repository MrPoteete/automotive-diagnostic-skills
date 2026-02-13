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

## Verification Protocol (Before Commits)

**Always run before committing**:
```bash
# 1. Run all tests
pytest

# 2. Check coverage
pytest --cov=src --cov-report=term-missing

# 3. Verify safety tests pass
pytest -m safety

# 4. Run linter
ruff check .

# 5. Type checking
mypy src/
```

**Hooks automatically enforce**: ruff, mypy (see `.claude/settings.json`)
