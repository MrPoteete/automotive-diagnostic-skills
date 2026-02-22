"""
Shared pytest fixtures for automotive diagnostic test suite.

Checked AGENTS.md - implementing directly because:
1. This is test infrastructure (conftest.py), not application business logic
2. quality-engineer agent IS the current agent — no delegation needed
3. data-engineer handles production DB pipelines; test fixtures are testing scope

Adds the project root to sys.path so tests can import from src/ without
an installed package.  Provides:

- mock_db  : A MagicMock that satisfies DiagnosticDB's interface for unit tests.
- real_db  : A live DiagnosticDB backed by the real SQLite databases.
             Skipped automatically when the database files are absent.
"""

import sys
from pathlib import Path
from unittest.mock import MagicMock

import pytest

# ---------------------------------------------------------------------------
# Ensure project root is importable as a package root.
# conftest.py lives at <project_root>/tests/conftest.py, so .parent.parent
# resolves to <project_root>.
# ---------------------------------------------------------------------------
PROJECT_ROOT = Path(__file__).parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# Database paths (absolute — do NOT rely on cwd).
COMPLAINTS_DB = PROJECT_ROOT / "database" / "automotive_complaints.db"
DIAGNOSTICS_DB = PROJECT_ROOT / "database" / "automotive_diagnostics.db"

# ---------------------------------------------------------------------------
# Pytest marker registration (suppresses PytestUnknownMarkWarning)
# ---------------------------------------------------------------------------


def pytest_configure(config: pytest.Config) -> None:
    config.addinivalue_line("markers", "unit: Pure unit tests with no I/O dependencies")
    config.addinivalue_line("markers", "integration: Integration tests that require real databases")
    config.addinivalue_line("markers", "safety: Tests covering safety-critical system validation")


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def mock_db() -> MagicMock:
    """Return a MagicMock that satisfies the DiagnosticDB interface.

    Default behaviour (overridable per test):
    - count_complaints       -> 0
    - search_complaints      -> []
    - search_tsbs            -> []
    - get_complaints_by_year -> []
    """
    db = MagicMock(name="DiagnosticDB")
    db.count_complaints.return_value = 0
    db.search_complaints.return_value = []
    db.search_tsbs.return_value = []
    db.get_complaints_by_year.return_value = []
    return db


@pytest.fixture
def real_db():
    """Return an open DiagnosticDB backed by the real SQLite databases.

    The fixture is skipped when either database file is missing so the test
    suite can still run in CI environments that only have source code.
    """
    if not COMPLAINTS_DB.exists():
        pytest.skip(
            f"Complaints database not found: {COMPLAINTS_DB} — skipping integration test"
        )
    if not DIAGNOSTICS_DB.exists():
        pytest.skip(
            f"Diagnostics database not found: {DIAGNOSTICS_DB} — skipping integration test"
        )

    from src.data.db_service import DiagnosticDB

    db = DiagnosticDB()
    yield db
    db.close()


@pytest.fixture
def ford_f150_2019() -> dict:
    """Sample Ford F-150 2019 vehicle dict."""
    return {"make": "FORD", "model": "F-150", "year": 2019}


@pytest.fixture
def ram_1500_2015() -> dict:
    """Sample RAM 1500 2015 vehicle dict."""
    return {"make": "RAM", "model": "1500", "year": 2015}
