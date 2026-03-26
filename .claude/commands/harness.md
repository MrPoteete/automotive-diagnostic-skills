# /harness — Autonomous Feature Development Harness

Runs the Planner → Generator → Evaluator → Doc Updater pipeline.
Acceptance criteria are locked by a separate Planner agent before any code is written.

## Usage

```
/harness <task description>
/harness <task> --plan-only       # inspect spec before generating
/harness --eval-only              # re-evaluate current branch
```

## What happens

1. **Planner (Claude Opus)** — expands task into spec + locked acceptance criteria + identifies boilerplate
2. **Boilerplate pre-gen (Gemini Flash)** — generates routine subtasks before generation starts
3. **Generator (Claude Sonnet)** — implements feature on a new branch with boilerplate context
4. **Evaluator (Claude Sonnet)** — scores diff against frozen criteria (loops up to 3x with feedback)
5. **Doc Updater (Gemini Flash)** — patches DIAGRAMS.md, ARCHITECT.md, CLAUDE.md if stale

## Examples

```bash
uv run python scripts/coding_harness.py "Add endpoint to search recalls by component keyword"
uv run python scripts/coding_harness.py "Add Vitest tests for ChecklistPanel component"
uv run python scripts/coding_harness.py "Refactor db_service.py to add connection pooling"
```

## Plans are stored in `.harness/plans/` — never modify them after generation starts.

$ARGUMENTS
