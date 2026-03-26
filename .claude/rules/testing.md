---
description: Testing standards — full test gate commands, counts, and integration test rules
globs: tests/**/*.py, tests/**/*.ts, src/frontend/**/*.test.tsx, src/frontend/**/*.spec.tsx
alwaysApply: false
---

## Full Test Gate (must pass ALL three before merging)

```bash
# 1. Python — 280 tests as of 2026-03-26
uv run pytest --tb=no -q --ignore=tests/integration

# 2. Vitest unit — 142 tests as of 2026-03-26
cd src/frontend && node_modules/.bin/vitest run

# 3. Playwright e2e — 42 tests as of 2026-03-26 (requires both servers running)
cd src/frontend && node_modules/.bin/playwright test
```

Do NOT merge until all three suites pass.

## Integration Tests

- Never mock the database in integration tests — use the real SQLite files
- Integration tests live in `tests/integration/` and are excluded from the default pytest run
- Run integration tests explicitly: `uv run pytest tests/integration/ -v`

## Test Counts (verified 2026-03-26)

| Suite | Count | Command |
|-------|-------|---------|
| Python (unit) | 280 | `uv run pytest --ignore=tests/integration` |
| Vitest | 142 | `cd src/frontend && node_modules/.bin/vitest run` |
| Playwright | 42 | `cd src/frontend && node_modules/.bin/playwright test` |

## Python Test Conventions

- Use `uv run pytest` on the VM (no `.venv/bin/` prefix)
- Fixture DB path: `tests/fixtures/` — read-only copies, never live databases
- Safety-critical tests (brake, steering, fuel) require confidence >= 0.9 assertions
- DTC validation tests must cover regex `^[PCBU][0-3][0-9A-F]{3}$` boundary cases
