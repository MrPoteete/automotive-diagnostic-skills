---
description: Python conventions — uv run, mypy strict, DTC validation, SQL gotchas
globs: **/*.py, scripts/**/*.py, src/**/*.py, server/**/*.py
alwaysApply: false
---

## Runtime

- **Use `uv run python`** — VM has no `.venv/`; never use `.venv/bin/python3`
- For scripts with external deps not in pyproject.toml: `uv run --with <pkg> python -u script.py`
- Always add `-u` flag for long-running scripts piped to log files (unbuffered output)

## Type Checking (mypy strict)

- Always annotate return types: `def foo(x: str) -> bool:` not `def foo(x: str):`
- Import types with `TYPE_CHECKING` guard for forward refs
- Validators in `.claude/hooks/validators/mypy_validator.py` will block on missing annotations

## SQL Gotchas

- `year` column is **TEXT** in `complaints_fts` and `nhtsa_tsbs` — always `CAST(year AS INTEGER)` when filtering
- Recalls use `year_from`/`year_to` INTEGER range fields, not a `year` column
- FTS5 queries use `complaints_fts MATCH ?` not `LIKE` — much faster on 562K rows
- Always use `INSERT OR IGNORE` / `ON CONFLICT` for idempotent imports

## DTC Validation

```python
import re
DTC_PATTERN = re.compile(r'^[PCBU][0-3][0-9A-F]{3}$')

def validate_dtc(code: str) -> bool:
    return bool(DTC_PATTERN.match(code.upper()))
```

## Data Protection

- **NEVER write to `data/raw_imports/`** — read-only original sources
- Backups before schema changes: `uv run python scripts/backup_databases.py`
- DB paths: `database/automotive_complaints.db` (843MB primary), `database/automotive_diagnostics.db` (secondary)

## Safety-Critical Code

- Confidence threshold for safety-critical systems (brakes/steering/airbag): >= 0.9
- Always emit explicit safety warnings; never suppress them for UX reasons
- See `.claude/docs/DOMAIN.md` for full safety rules
