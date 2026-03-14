
# Checked AGENTS.md - implementing directly because:
# 1. sys.path wiring and import plumbing is structural, not auth/security logic
# 2. Pydantic models and thin endpoint wrapper delegated via Gemini (gemini-2.5-flash) per GEMINI_WORKFLOW.md
# 3. Safety-critical logic lives entirely in engine_agent.diagnose() — reviewed and tested in Phase 3/4
# 4. This file already has security middleware (CORS, API key) — no new auth logic added here
import pathlib
import sys

# Add project root to sys.path so `src.*` imports work when running from server/
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

# Checked AGENTS.md - adding pagination (math import + Query param) directly; no new auth/security logic, pure read-only query change.
from fastapi import FastAPI, HTTPException, Depends, Query
from fastapi.security import APIKeyHeader
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
import sqlite3
import uvicorn
import os
import math
import logging
from logging.handlers import RotatingFileHandler
from typing import Any

from dotenv import load_dotenv

from src.diagnostic.engine_agent import diagnose as run_diagnosis

load_dotenv()

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
# Checked AGENTS.md - implementing directly: CORS config change, security-critical but
# simple env var extension of existing pattern (no new auth logic added).
#
# Base: localhost:3000 (Next.js dev server).
# Remote: Tailscale IP or custom origin via REMOTE_ORIGIN env var.
#   Set REMOTE_ORIGIN=http://100.x.x.x:3000 in .env for Tailscale access.
#   Multiple origins: comma-separated (e.g. http://100.1.2.3:3000,http://100.4.5.6:3000)
ALLOWED_ORIGINS = [
    "http://localhost:3000",  # Next.js dev server
]

_remote_origin_env = os.getenv("REMOTE_ORIGIN", "").strip()
if _remote_origin_env:
    for _origin in _remote_origin_env.split(","):
        _origin = _origin.strip()
        if _origin and _origin not in ALLOWED_ORIGINS:
            ALLOWED_ORIGINS.append(_origin)

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

# Checked AGENTS.md - removing duplicate import only; no auth/security logic changed.
# 🔒 SECURITY
# ⚠️ SECURITY WARNING: API key hardcoded in source code.
# RECOMMENDED: Move to environment variable before production deployment:
#   API_KEY = os.getenv("API_KEY", "fallback-key-for-dev")
# See: .claude/docs/DOMAIN.md - Data Source Standards
API_KEY = os.getenv("API_KEY", "fallback-key-for-dev")
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

# Checked AGENTS.md - implementing pagination directly; read-only SQL change (LIMIT/OFFSET/COUNT), no auth or security changes.
# SQL structure reviewed via Gemini (gemini-2.5-flash) per GEMINI_WORKFLOW.md.
@app.get("/search")
async def search_complaints(
    query: str,
    limit: int = 20,
    page: int = Query(1, ge=1),
    api_key: str = Depends(get_api_key),
):
    if not os.path.exists(DB_PATH):
        raise HTTPException(status_code=500, detail="Database not indexed yet.")

    try:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        import re
        clean_query = re.sub(r'[^a-zA-Z0-9\s]', ' ', query)
        clean_query = re.sub(r'\s+', ' ', clean_query).strip()
        if not clean_query:
            clean_query = query

        logger.info(f"Search p{page}: '{query}' -> '{clean_query}'")

        offset = (page - 1) * limit
        cursor.execute(
            "SELECT COUNT(*) FROM complaints_fts WHERE complaints_fts MATCH ?",
            (clean_query,),
        )
        total_count: int = cursor.fetchone()[0]
        total_pages = math.ceil(total_count / limit) if total_count > 0 else 1

        cursor.execute(
            "SELECT make, model, year, component, summary"
            " FROM complaints_fts WHERE complaints_fts MATCH ?"
            " ORDER BY rank LIMIT ? OFFSET ?",
            (clean_query, limit, offset),
        )
        results = [dict(row) for row in cursor.fetchall()]
        conn.close()

        logger.info(f"Found {total_count} total, page {page}/{total_pages}.")

        return {
            "query": query,
            "sanitized_query": clean_query,
            "results": results,
            "total_count": total_count,
            "page": page,
            "total_pages": total_pages,
            "source": "NHTSA Complaints Index",
        }

    except Exception as e:
        logger.error(f"Search Error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Server Error: {str(e)}")

# Checked AGENTS.md - adding vehicle filter params (make/model/year); read-only SQL change.
# 4-case SQL branching reviewed by Gemini (gemini-2.5-flash) per GEMINI_WORKFLOW.md.
@app.get("/search_tsbs")
async def search_tsbs(
    query: str = Query(default=""),
    make: str | None = Query(default=None),
    model: str | None = Query(default=None),
    year: int | None = Query(default=None, ge=1900, le=2030),
    limit: int = 20,
    page: int = Query(1, ge=1),
    api_key: str = Depends(get_api_key),
) -> dict[str, Any]:
    """Search Technical Service Bulletins by keyword and/or vehicle filter."""
    if not os.path.exists(DB_PATH):
        raise HTTPException(status_code=500, detail="Database not indexed yet.")

    try:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        import re
        clean_query = re.sub(r'[^a-zA-Z0-9\s]', ' ', query)
        clean_query = re.sub(r'\s+', ' ', clean_query).strip()

        logger.info(f"TSB Search p{page}: '{query}' -> '{clean_query}' make={make} model={model} year={year}")

        # Graceful degradation if TSB table missing
        cursor.execute("SELECT count(*) FROM sqlite_master WHERE type='table' AND name='tsbs_fts'")
        if cursor.fetchone()[0] == 0:
            conn.close()
            return {"results": [], "total_count": 0, "page": 1, "total_pages": 1, "message": "TSB data not available yet."}

        has_keyword = bool(clean_query)
        has_vehicle = bool(make)
        offset = (page - 1) * limit

        # Case D: nothing — return guard message
        if not has_keyword and not has_vehicle:
            conn.close()
            return {"results": [], "total_count": 0, "page": 1, "total_pages": 1,
                    "message": "Provide a keyword or a vehicle make filter."}

        total_count: int
        total_pages: int

        # Case A: keyword + vehicle → FTS MATCH + column filters
        if has_keyword and has_vehicle:
            where_extra = ""
            params_count: list[Any] = [clean_query]
            if make:
                where_extra += " AND make = ?"
                params_count.append(make)
            if model:
                where_extra += " AND model = ?"
                params_count.append(model)
            if year is not None:
                where_extra += " AND CAST(year AS INTEGER) = ?"
                params_count.append(year)
            cursor.execute(
                f"SELECT COUNT(*) FROM tsbs_fts WHERE tsbs_fts MATCH ?{where_extra}",
                params_count,
            )
            total_count = cursor.fetchone()[0]
            total_pages = math.ceil(total_count / limit) if total_count > 0 else 1
            cursor.execute(
                f"SELECT nhtsa_id, make, model, year, component, summary"
                f" FROM tsbs_fts WHERE tsbs_fts MATCH ?{where_extra}"
                f" ORDER BY rank LIMIT ? OFFSET ?",
                params_count + [limit, offset],
            )

        # Case B: keyword only → existing FTS path (unchanged)
        elif has_keyword:
            cursor.execute("SELECT COUNT(*) FROM tsbs_fts WHERE tsbs_fts MATCH ?", (clean_query,))
            total_count = cursor.fetchone()[0]
            total_pages = math.ceil(total_count / limit) if total_count > 0 else 1
            cursor.execute(
                "SELECT nhtsa_id, make, model, year, component, summary"
                " FROM tsbs_fts WHERE tsbs_fts MATCH ?"
                " ORDER BY rank LIMIT ? OFFSET ?",
                (clean_query, limit, offset),
            )

        # Case C: vehicle only → base table (avoids FTS empty-MATCH error)
        else:
            where_clauses = ["make = ?"]
            params_base: list[Any] = [make]
            if model:
                where_clauses.append("model = ?")
                params_base.append(model)
            if year is not None:
                # Include year=9999 sentinel (multi-year TSBs in some datasets)
                where_clauses.append("(year = ? OR year = 9999)")
                params_base.append(year)
            where_sql = " AND ".join(where_clauses)
            cursor.execute(f"SELECT COUNT(*) FROM nhtsa_tsbs WHERE {where_sql}", params_base)
            total_count = cursor.fetchone()[0]
            total_pages = math.ceil(total_count / limit) if total_count > 0 else 1
            cursor.execute(
                f"SELECT nhtsa_id, make, model, year, component, summary"
                f" FROM nhtsa_tsbs WHERE {where_sql} ORDER BY year DESC, nhtsa_id DESC LIMIT ? OFFSET ?",
                params_base + [limit, offset],
            )

        results = [dict(row) for row in cursor.fetchall()]
        conn.close()

        logger.info(f"Found {total_count} total TSBs, page {page}/{total_pages}.")

        return {
            "query": query,
            "sanitized_query": clean_query,
            "results": results,
            "total_count": total_count,
            "page": page,
            "total_pages": total_pages,
            "make": make,
            "model": model,
            "year": year,
            "source": "NHTSA TSB Index",
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


# Checked AGENTS.md - implementing GET /vehicles directly; simple read-only query, no safety logic, no auth changes.
# Boilerplate structure reviewed by Gemini (gemini-2.5-flash) per GEMINI_WORKFLOW.md.
@app.get("/vehicles")
async def get_vehicles(api_key: str = Depends(get_api_key)) -> dict[str, object]:
    """Return distinct makes and models from the complaints database."""
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        # Filter to 2005+ vehicles — older records are data noise for modern diagnostic queries.
        # year column is TEXT in this DB, so CAST(year AS INTEGER) is required.
        cursor.execute(
            "SELECT DISTINCT make, model FROM complaints_fts"
            " WHERE CAST(year AS INTEGER) >= 2005"
            " ORDER BY make, model"
        )
        rows = cursor.fetchall()
        conn.close()

        models_by_make: dict[str, list[str]] = {}
        for row in rows:
            make: str = row["make"]
            model: str = row["model"]
            if make not in models_by_make:
                models_by_make[make] = []
            models_by_make[make].append(model)

        # Exclude makes with fewer than 2 distinct models (data noise)
        filtered = {m: mods for m, mods in models_by_make.items() if len(mods) >= 2}
        sorted_makes = sorted(filtered.keys())
        total = sum(len(v) for v in filtered.values())
        logger.info("Vehicles request: %d makes, %d total models", len(sorted_makes), total)

        return {"makes": sorted_makes, "models_by_make": filtered}
    except Exception as e:
        logger.error("Vehicles error: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# Checked AGENTS.md - implementing GET /vehicles/years directly; simple read-only query, no safety logic.
# Endpoint structure reviewed via Gemini (gemini-2.5-flash) per GEMINI_WORKFLOW.md.
@app.get("/vehicles/years")
async def get_vehicle_years(make: str, model: str, api_key: str = Depends(get_api_key)) -> dict[str, object]:
    """Return distinct years with complaint data for a given make/model, sorted descending."""
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute(
            "SELECT DISTINCT CAST(year AS INTEGER) AS yr"
            " FROM complaints_fts"
            " WHERE make = ? AND model = ? AND CAST(year AS INTEGER) >= 2005"
            " ORDER BY yr DESC",
            (make, model),
        )
        years: list[int] = [row["yr"] for row in cursor.fetchall()]
        conn.close()
        logger.info("Years request: %s %s → %d years", make, model, len(years))
        return {"make": make, "model": model, "years": years}
    except Exception as e:
        logger.error("Years error: %s", e, exc_info=True)
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

