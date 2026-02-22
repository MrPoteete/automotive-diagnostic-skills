
# Checked AGENTS.md - implementing directly because:
# 1. sys.path wiring and import plumbing is structural, not auth/security logic
# 2. Pydantic models and thin endpoint wrapper delegated via Gemini (gemini-2.5-flash) per GEMINI_WORKFLOW.md
# 3. Safety-critical logic lives entirely in engine_agent.diagnose() — reviewed and tested in Phase 3/4
# 4. This file already has security middleware (CORS, API key) — no new auth logic added here
import pathlib
import sys

# Add project root to sys.path so `src.*` imports work when running from server/
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from fastapi import FastAPI, HTTPException, Depends
from fastapi.security import APIKeyHeader
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
import sqlite3
import uvicorn
import os
import logging
from logging.handlers import RotatingFileHandler
from typing import Any

from src.diagnostic.engine_agent import diagnose as run_diagnosis

# Checked AGENTS.md - implementing CORS directly because:
# 1. This is security-critical middleware (access control)
# 2. Using explicit allowlist (no wildcards) per security best practices
# 3. Minimal permissions (only GET/POST, specific headers)
# 4. Added security warnings for hardcoded API key (separate issue)
# 5. Configuration is production-ready with clear comments for deployment
#
# SECURITY CONTROLS IMPLEMENTED:
# - Explicit origin allowlist (localhost:3000 only in dev)
# - Credentials enabled (required for API key header)
# - Method restriction (GET, POST only)
# - Header restriction (X-API-KEY, Content-Type only)
# - Preflight caching (10 min) to reduce OPTIONS overhead
#
# PRODUCTION NOTES:
# - Replace ALLOWED_ORIGINS with actual frontend domain
# - Move API_KEY to environment variable (see warning below)

# --- LOGGING CONFIGURATION ---
# Rotate log file at 5MB, keep 3 backups.
LOG_FILE = "server.log"
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        RotatingFileHandler(LOG_FILE, maxBytes=5*1024*1024, backupCount=3),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger("server")

app = FastAPI(title="Automotive Diagnostic RAG Server")

# --- CORS CONFIGURATION (SECURITY-CRITICAL) ---
# Only allow localhost:3000 (Next.js dev server) to prevent unauthorized access.
# In production, replace with actual frontend domain.
ALLOWED_ORIGINS = [
    "http://localhost:3000",  # Next.js dev server
]

# Add CORS middleware with explicit allow list (NO wildcards)
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,  # Explicit origins only (no "*")
    allow_credentials=True,  # Required for X-API-KEY header
    allow_methods=["GET", "POST"],  # Only necessary methods
    allow_headers=["X-API-KEY", "Content-Type"],  # Only necessary headers
    max_age=600,  # Cache preflight requests for 10 minutes
)

logger.info(f"CORS enabled for origins: {ALLOWED_ORIGINS}")

@app.on_event("startup")
async def startup_event():
    logger.info("Server starting up...")
    logger.info(f"Database Path: {DB_PATH}")

# 🔒 SECURITY
# ⚠️ SECURITY WARNING: API key hardcoded in source code.
# RECOMMENDED: Move to environment variable before production deployment:
#   API_KEY = os.getenv("API_KEY", "fallback-key-for-dev")
# See: .claude/docs/DOMAIN.md - Data Source Standards
API_KEY = "mechanic-secret-key-123"
api_key_header = APIKeyHeader(name="X-API-KEY")

def get_api_key(api_key: str = Depends(api_key_header)):
    if api_key == API_KEY:
        return api_key
    raise HTTPException(status_code=403, detail="Invalid API Key")

# Path to the NEW fast database we just built
DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "database", "automotive_complaints.db")

@app.get("/")
async def root():
    return {"status": "online", "message": "Automotive Diagnostic Server is running."}

@app.get("/search")
async def search_complaints(query: str, limit: int = 20, api_key: str = Depends(get_api_key)):
    if not os.path.exists(DB_PATH):
        raise HTTPException(status_code=500, detail="Database not indexed yet.")

    try:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        # Super fast FTS5 search
        # FTS5 requires careful handling of special characters.
        # We replace non-alphanumeric characters with spaces to avoid syntax errors.
        # This treats "6.2L" as "6 2L", which works well with standard tokenizers.
        import re
        clean_query = re.sub(r'[^a-zA-Z0-9\s]', ' ', query)

        # Collapse multiple spaces
        clean_query = re.sub(r'\s+', ' ', clean_query).strip()

        # If query becomes empty after cleaning (e.g. only symbols), fall back to original (or handle gracefully)
        # If query becomes empty after cleaning (e.g. only symbols), fall back to original (or handle gracefully)
        if not clean_query:
             clean_query = query

        logger.info(f"Search: '{query}' -> '{clean_query}'")

        search_sql = """
            SELECT make, model, year, component, summary
            FROM complaints_fts
            WHERE complaints_fts MATCH ?
            ORDER BY rank
            LIMIT ?
        """
        cursor.execute(search_sql, (clean_query, limit))
        results = [dict(row) for row in cursor.fetchall()]
        conn.close()

        logger.info(f"Found {len(results)} matches.")

        return {
            "query": query,
            "sanitized_query": clean_query,
            "results": results,
            "source": "NHTSA Complaints Index"
        }

    except Exception as e:
        logger.error(f"Search Error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Server Error: {str(e)}")

@app.get("/search_tsbs")
async def search_tsbs(query: str, limit: int = 20, api_key: str = Depends(get_api_key)):
    """
    Search specifically for Technical Service Bulletins (TSBs) and Manufacturer Communications.
    """
    if not os.path.exists(DB_PATH):
        raise HTTPException(status_code=500, detail="Database not indexed yet.")

    try:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        # FTS5 requires careful handling of special characters.
        import re
        clean_query = re.sub(r'[^a-zA-Z0-9\s]', ' ', query)
        clean_query = re.sub(r'\s+', ' ', clean_query).strip()

        if not clean_query:
             clean_query = query

        logger.info(f"TSB Search: '{query}' -> '{clean_query}'")

        # Check if TSB table exists (graceful degradation)
        cursor.execute("SELECT count(*) FROM sqlite_master WHERE type='table' AND name='tsbs_fts'")
        if cursor.fetchone()[0] == 0:
             conn.close()
             return {"results": [], "message": "TSB data not available yet."}

        search_sql = """
            SELECT nhtsa_id, make, model, year, component, summary
            FROM tsbs_fts
            WHERE tsbs_fts MATCH ?
            ORDER BY rank
            LIMIT ?
        """
        cursor.execute(search_sql, (clean_query, limit))
        results = [dict(row) for row in cursor.fetchall()]
        conn.close()

        logger.info(f"Found {len(results)} TSB matches.")

        return {
            "query": query,
            "sanitized_query": clean_query,
            "results": results,
            "source": "NHTSA TSB Index"
        }

    except Exception as e:
        logger.error(f"TSB Search Error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Server Error: {str(e)}")

# --- Pydantic models for /diagnose (generated via Gemini, reviewed by Claude) ---

class VehicleInfo(BaseModel):
    make: str = Field(..., description="Vehicle make (e.g. 'FORD')")
    model: str = Field(..., description="Vehicle model (e.g. 'F-150')")
    year: int = Field(..., ge=1990, le=2030, description="Model year")


class DiagnosticRequest(BaseModel):
    vehicle: VehicleInfo
    symptoms: str = Field(..., min_length=3, description="Free-text symptom description")
    dtc_codes: list[str] = Field(default_factory=list, description="OBD-II DTC codes e.g. ['P0300']")


@app.post("/diagnose")
async def diagnose_endpoint(
    request: DiagnosticRequest,
    api_key: str = Depends(get_api_key),
) -> dict[str, Any]:
    """Run a full differential diagnosis via the RAG diagnostic engine."""
    symptom_summary = request.symptoms[:100] + "..." if len(request.symptoms) > 100 else request.symptoms
    logger.info(
        "Diagnose request: %s %s (%d) — symptoms: %r — DTCs: %s",
        request.vehicle.make, request.vehicle.model, request.vehicle.year,
        symptom_summary, request.dtc_codes or "none",
    )
    try:
        result: dict[str, Any] = run_diagnosis(
            vehicle=request.vehicle.model_dump(),
            symptoms=request.symptoms,
            dtc_codes=request.dtc_codes,
        )
        return result
    except Exception as e:
        logger.error("Diagnosis failed: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    # Host on 0.0.0.0 for Tailscale remote access
    import socket

    def is_port_in_use(port: int) -> bool:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            return s.connect_ex(('localhost', port)) == 0

    if is_port_in_use(8000):
        logger.warning("Port 8000 is already in use. Assuming server is already running via Auto-Start.")
        sys.exit(0)

    uvicorn.run(app, host="0.0.0.0", port=8000)

