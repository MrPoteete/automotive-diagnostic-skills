# Dual-Agent Collaboration Workflow

This project is developed collaboratively by **Gemini (Antigravity)** and **Claude (Anthropic)**. To ensure seamless handoffs and avoid "reinventing the wheel," both agents MUST adhere to this workflow.

## 1. The Single Source of Truth

**`PROJECT_STATUS.md` is the absolute source of truth.**

*   **Upon Start**: Every agent MUST read `PROJECT_STATUS.md` first to understand the current state, active tasks, and recent changes.
*   **Upon Finish**: Every agent MUST update `PROJECT_STATUS.md` with:
    *   **Current Phase**: e.g., "Phase 3: Agent Framework"
    *   **Completed Tasks**: Explicitly list what was done.
    *   **Next Steps**: Clearly define what the *next* agent should do.
    *   **Last Agent**: "Gemini" or "Claude" + Timestamp.

## 2. Standardized Commands (`tasks.py`)

Do not rely on agent-specific memory for commands. Use the standardized `tasks.py` script for all common operations.

*   **Setup Encironment**: `python tasks.py setup`
*   **Run Tests**: `python tasks.py test`
*   **Check DB Status**: `python tasks.py db-stats`
*   **Run Diagnostic**: `python tasks.py diagnose` (Future)

If a new common task is needed, **add it to `tasks.py`** instead of just running a one-off shell command. This ensures the other agent can also run it easily.

## 3. Architecture & Code Style

*   **Follow `CLAUDE.md`**: This file contains the project's coding standards, safety protocols (Safety Critical Systems), and OBD-II validation rules. **Both** agents must respect these rules.
*   **Skill Definitions**: The `skills/SKILL.md` file defines the agent's behavior. If you change the behavior, update this file.
*   **No Hidden Context**: Do not rely on internal "memory" for critical architectural decisions. Document them in `docs/` or `PROJECT_STATUS.md`.

## 4. Handoff Checklist

Before ending a session, verify:
1.  [ ] Code is saved and runnable.
2.  [ ] `PROJECT_STATUS.md` is updated.
3.  [ ] No loose ends (e.g., half-written files).
4.  [ ] If a task is incomplete, explicitly state "IN PROGRESS" in the status file.

---
**Goal**: Any agent should be able to pick up the project from any state and immediately be productive.
