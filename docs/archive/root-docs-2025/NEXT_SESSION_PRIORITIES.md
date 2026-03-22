# Next Session Priorities (Updated 2026-02-24)

## Recent Victories
- ✅ **API Fallback**: Client gracefully handles timeouts (5s GET / 15s POST) and network loss (`ECONNREFUSED` via Tailscale drops) returning structured error messages.
- ✅ **Engine Agent Hardening**: Robust input coercion and parameter validation before touching the SQLite FTS5 database to prevent unhandled exceptions.
- ✅ **ChromaDB Chunking Validation**: Implemented and proved a new chunking strategy that embeds question body text alongside the accepted answer, improving semantic matching. Wiped and rebuilt the entire `mechanics_forum` collection.

## 🎯 Next Steps for Upcoming Sessions

### 1. UI Error State Integration (Frontend)
The Next.js UI now receives the `SERVER_UNREACHABLE_MSG` when Tailscale is down.
- **Task**: Update the Next.js frontend components (e.g., `ErrorBoundary.tsx` or the main diagnostic UI) to cleanly display this message instead of a generic failed state.
- **Goal**: Make it obvious to the mechanic that the Home Server is unreachable, providing the Tailscale troubleshooting steps.

### 2. Semantic Search Integration (Backend / RAG)
The ChromaDB vector store is rebuilt with superior embeddings.
- **Task**: Wire `src/data/chroma_service.py` directly into `src/diagnostic/symptom_matcher.py` (or `engine_agent.py` directly).
- **Goal**: When the user describes a symptom, the `engine_agent` should fetch both SQLite FTS5 (NHTSA/Failures) AND ChromaDB semantic matches (Stack Exchange), feeding both sets of context to the LLM.

### 3. Expand Diagnostic Domains (Architecture)
Once the `engine_agent` is perfectly utilizing both structured DB data and semantic RAG data, it's time to clone its structure.
- **Task**: Create `transmission_agent.py` and `electrical_agent.py`.
- **Goal**: Ensure the routing logic (`coordinator.py` or the master skill) properly directs transmission and electrical symptoms to their respective sub-agents instead of the default engine agent.

### 4. Personal Branding (Marketing)
Michael needs to start building a brand (YouTube, LinkedIn) highlighting his unique intersection of skills: ASE Master Tech + AI/Python Engineering.
- **Task**: Brainstorm content ideas (e.g., "Why mechanics need local LLMs," "Building a 2.1M row SQLite DB for auto diagnostics," or "Diagnosing a Coyote V8 using Python").
- **Goal**: Establish thought leadership in the "AI for Blue Collar / Trades" space.
