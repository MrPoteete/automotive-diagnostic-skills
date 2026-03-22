# Current Project Status - Dual-Agent Collaboration

**Date**: 2026-02-24
**Phase**: Phase 4: Modular Skill Implementation & Agent Hardening (In Progress)
**Last Agent**: Cortana / Claude Code Army

## 🔄 Dual-Agent Workflow Established
*   **Source of Truth**: `PROJECT_STATUS.md` (This file).
*   **Standardized Commands**: `tasks.py` (Setup, Tests, DB Stats).
*   **Documentation**: `DUAL_AGENT_WORKFLOW.md` and `CLAUDE.md`.

## 📍 Where We Are Now

### ✅ RECENTLY COMPLETED (2026-02-24):
1.  **API Client Graceful Fallback**: Implemented strict timeouts (5s GET, 15s POST) and structured error handling (`SERVER_UNREACHABLE_MSG`) in `src/frontend/lib/api.ts` to fail gracefully when the Home Server/Tailscale is unreachable.
2.  **Engine Agent Hardening**: Bulletproofed `src/diagnostic/engine_agent.py` and `src/diagnostic/confidence_scorer.py` by adding strict input coercion helpers (`_coerce_vehicle`, `_coerce_symptoms`, `_coerce_dtc_codes`) and comprehensive DB/validation guards.
3.  **Improved RAG Chunking Strategy**: Validated and implemented a superior ChromaDB chunking strategy via `test_rag_chunking.py`. The production pipeline (`scripts/index_forum_data.py`) now embeds the question body symptom language alongside the accepted answer, significantly improving semantic relevance scores.
4.  **ChromaDB Index Rebuilt**: Wiped and rebuilt the production ChromaDB collection with the new chunking strategy.

### 🎯 CURRENT OBJECTIVE:
**Solidify Client-Side Resiliency & Expand Diagnostic Domain**
*   Ensure the web UI cleanly displays the new `SERVER_UNREACHABLE_MSG` and offers a retry/troubleshooting workflow.
*   Integrate the newly improved ChromaDB semantic search directly into the `symptom_matcher.py` pipeline to feed the `engine_agent.py`.

### 📋 NEXT STEPS:
(See `NEXT_SESSION_PRIORITIES.md` for detailed tasks)
1.  **UI Error State Integration**: Hook up the Next.js UI to properly render the new `SERVER_UNREACHABLE_MSG` when Tailscale/Home Server drops.
2.  **Semantic Search Integration**: Wire up `chroma_service.py` to the `symptom_matcher.py` so the `engine_agent` leverages the newly rebuilt forum embeddings.
3.  **Create Transmission/Electrical Agents**: Once the `engine_agent` is perfectly utilizing both SQLite and ChromaDB, clone its architecture to handle Transmission and Electrical domains.

## Key Files:
- `DUAL_AGENT_WORKFLOW.md` - **READ THIS FIRST** if you are a new agent.
- `tasks.py` - Run standard project commands.
- `skills/SKILL.md` - The definitive guide to agent behavior.
- `database/automotive_diagnostics.db` - The core data.

## Tech Stack:
- **Backend**: Python 3.11+, SQLite (FTS5), ChromaDB.
- **Frontend**: Next.js (React), CLI.
- **AI**: Claude/Gemini via Skill Interface.

---
**Recovery Phrase**: "dual-agent automotive diagnostic framework phase 4"