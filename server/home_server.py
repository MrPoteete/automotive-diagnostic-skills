
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

# Checked AGENTS.md - history endpoints implemented via Gemini delegation per GEMINI_WORKFLOW.md.
# Startup migration and endpoint wiring done directly (structural plumbing, not domain logic).
@app.on_event("startup")
async def startup_event():
    logger.info("Server starting up...")
    logger.info(f"Database Path: {DB_PATH}")
    # Create diagnosis_history table if not exists
    _conn = sqlite3.connect(str(DIAG_DB_PATH))
    _conn.execute("""
        CREATE TABLE IF NOT EXISTS diagnosis_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            created_at TEXT NOT NULL,
            vin TEXT,
            year INTEGER NOT NULL,
            make TEXT NOT NULL,
            model TEXT NOT NULL,
            engine TEXT,
            symptoms TEXT NOT NULL,
            dtc_codes TEXT NOT NULL DEFAULT '[]',
            findings TEXT NOT NULL,
            candidate_count INTEGER NOT NULL DEFAULT 0,
            has_warnings INTEGER NOT NULL DEFAULT 0
        )
    """)
    _conn.commit()
    _conn.close()
    logger.info("diagnosis_history table ready in %s", DIAG_DB_PATH)

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
DIAG_DB_PATH = pathlib.Path(__file__).resolve().parent.parent / "database" / "automotive_diagnostics.db"

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


# Checked AGENTS.md - implementing via Gemini delegation per GEMINI_WORKFLOW.md.
# No safety logic — simple proxy to NHTSA vPIC API with VIN validation.
@app.get("/vin/decode")
async def decode_vin(
    vin: str = Query(..., min_length=17, max_length=17),
    api_key: str = Depends(get_api_key),
) -> dict[str, object]:
    """Decode a VIN using the NHTSA vPIC API. Returns vehicle details or valid=false on error."""
    import re as _re
    import httpx

    vin = vin.upper().strip()
    if not _re.match(r"^[0-9A-HJ-NPR-Z]{17}$", vin):
        return {"vin": vin, "valid": False, "error": "Invalid VIN format (17 alphanumeric chars, no I/O/Q)"}

    nhtsa_url = f"https://vpic.nhtsa.dot.gov/api/vehicles/DecodeVin/{vin}?format=json"
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(nhtsa_url)
            resp.raise_for_status()
            data = resp.json()
    except httpx.HTTPStatusError as exc:
        logger.error("NHTSA HTTP error for VIN %s: %s", vin, exc)
        return {"vin": vin, "valid": False, "error": f"NHTSA API error: {exc.response.status_code}"}
    except httpx.RequestError as exc:
        logger.error("NHTSA network error for VIN %s: %s", vin, exc)
        return {"vin": vin, "valid": False, "error": "Failed to reach NHTSA API"}

    results: list[dict[str, object]] = data.get("Results", [])

    # Build lookup: Variable → Value
    fields: dict[str, str] = {}
    for item in results:
        var = str(item.get("Variable") or "")
        val = str(item.get("Value") or "")
        if var and val and val not in ("Not Applicable", "0", ""):
            fields[var] = val

    # Check NHTSA error code — only fail on fatal codes where no data was returned.
    # Code "1" = check digit incorrect (very common on trucks/older vehicles) — data is still valid.
    # Codes 7, 8, 14 = truly undecodable VINs.
    error_code = fields.get("ErrorCode", "0")
    FATAL_ERROR_CODES = {"7", "8", "14"}
    if error_code in FATAL_ERROR_CODES or (not fields.get("Make") and not fields.get("Model")):
        logger.warning("NHTSA returned error code %s for VIN %s", error_code, vin)
        return {"vin": vin, "valid": False, "error": f"NHTSA could not decode VIN (error {error_code})"}

    # Build engine string: "5.3L V8" — NHTSA variable names use spaces/parens
    displacement = fields.get("Displacement (L)", "")
    cylinders_str = fields.get("Engine Number of Cylinders", "")
    engine: str | None = None
    if displacement or cylinders_str:
        cyl_map = {"4": "I4", "6": "V6", "8": "V8", "10": "V10", "12": "V12", "3": "I3", "5": "I5"}
        cyl_label = cyl_map.get(cylinders_str, f"{cylinders_str}cyl" if cylinders_str else "")
        parts = []
        if displacement:
            try:
                parts.append(f"{float(displacement):.1f}L")
            except ValueError:
                parts.append(f"{displacement}L")
        if cyl_label:
            parts.append(cyl_label)
        engine = " ".join(parts) if parts else None

    year_val: int | None = None
    raw_year = fields.get("Model Year", "")
    if raw_year:
        try:
            year_val = int(raw_year)
        except ValueError:
            pass

    logger.info("VIN decoded: %s → %s %s %s %s", vin, year_val, fields.get("Make"), fields.get("Model"), engine)

    return {
        "vin": vin,
        "valid": True,
        "year": year_val,
        "make": fields.get("Make"),
        "model": fields.get("Model"),
        "engine": engine,
        "drive_type": fields.get("Drive Type"),
        "body_class": fields.get("Body Class"),
        "trim": fields.get("Trim"),
        "fuel_type": fields.get("Fuel Type - Primary"),
        "raw": data,
    }


class ReportRequest(BaseModel):
    make: str
    model: str
    year_start: int = Field(..., ge=1900, le=2030)
    year_end: int = Field(..., ge=1900, le=2030)
    no_llm: bool = True
    no_api: bool = False


# Checked AGENTS.md - implementing via Gemini delegation per GEMINI_WORKFLOW.md.
# Runs report_builder.py as subprocess — no safety logic, read-only data access.
@app.post("/vehicle/report")
async def generate_vehicle_report(
    request: ReportRequest,
    api_key: str = Depends(get_api_key),
) -> dict[str, object]:
    """Run report_builder.py as a subprocess and return generated markdown."""
    import asyncio  # noqa: PLC0415
    import time     # noqa: PLC0415

    make = request.make.upper().replace(" ", "_")
    model = request.model.upper().replace(" ", "_")

    if request.year_start > request.year_end:
        raise HTTPException(status_code=400, detail="year_start cannot be greater than year_end")

    reports_dir = pathlib.Path(__file__).resolve().parent.parent / "reports"
    reports_dir.mkdir(exist_ok=True)
    output_path = reports_dir / f"report_{make}_{model}_{request.year_start}_{request.year_end}.md"
    project_root = pathlib.Path(__file__).resolve().parent.parent
    python_exe = project_root / ".venv" / "bin" / "python3"
    script = project_root / "scripts" / "report_builder.py"

    args = [
        str(python_exe), str(script),
        "--make", make,
        "--model", model,
        "--year-start", str(request.year_start),
        "--year-end", str(request.year_end),
        "--output", str(output_path),
    ]
    if request.no_llm:
        args.append("--no-llm")
    if request.no_api:
        args.append("--no-api")

    t0 = time.monotonic()
    proc = None
    try:
        proc = await asyncio.create_subprocess_exec(
            *args,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        _stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=180.0)

        if proc.returncode != 0:
            err_text = stderr.decode().strip()[-500:]
            logger.error("Report failed for %s %s: %s", make, model, err_text)
            raise HTTPException(status_code=500, detail=f"Report generation failed: {err_text}")

        content = output_path.read_text(encoding="utf-8")
        logger.info("Report done: %s %s %d-%d in %.1fs", make, model, request.year_start, request.year_end, time.monotonic() - t0)
        return {
            "content": content,
            "filename": f"{make}_{model}_{request.year_start}_{request.year_end}.md",
            "make": make,
            "model": model,
            "year_start": request.year_start,
            "year_end": request.year_end,
        }

    except asyncio.TimeoutError:
        if proc:
            proc.kill()
            await proc.wait()
        raise HTTPException(status_code=504, detail="Report generation timed out (180s)")
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Report error: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail=str(exc))
    finally:
        if output_path.exists():
            output_path.unlink(missing_ok=True)


# Checked AGENTS.md - implementing via Gemini delegation per GEMINI_WORKFLOW.md.
# Read-only SQL queries against complaints_fts and nhtsa_tsbs — no safety logic.
@app.get("/vehicle/dashboard")
async def get_vehicle_dashboard(
    make: str,
    model: str,
    year: int = Query(..., ge=1900, le=2030),
    api_key: str = Depends(get_api_key),
) -> dict[str, object]:
    """Return dashboard stats for a specific vehicle year/make/model."""
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        make_upper = make.upper()
        model_upper = model.upper()

        # 1. Total complaint count for this year
        cursor.execute(
            "SELECT COUNT(*) FROM complaints_fts"
            " WHERE make = ? AND model = ? AND CAST(year AS INTEGER) = ?",
            (make_upper, model_upper, year),
        )
        complaint_count: int = cursor.fetchone()[0]

        # 2. TSB count
        cursor.execute(
            "SELECT COUNT(*) FROM nhtsa_tsbs"
            " WHERE UPPER(make) = ? AND UPPER(model) = ? AND CAST(year AS INTEGER) = ?",
            (make_upper, model_upper, year),
        )
        tsb_count: int = cursor.fetchone()[0]

        # 2b. Recall count
        cursor.execute(
            "SELECT COUNT(*) FROM nhtsa_recalls"
            " WHERE UPPER(make) = ? AND UPPER(model) = ?"
            " AND ((year_from IS NULL OR year_from <= ?) AND (year_to IS NULL OR year_to >= ?))",
            (make_upper, model_upper, year, year),
        )
        recall_count: int = cursor.fetchone()[0]

        # 3. Top 5 failure components
        cursor.execute(
            "SELECT component, COUNT(*) AS cnt FROM complaints_fts"
            " WHERE make = ? AND model = ? AND CAST(year AS INTEGER) = ?"
            " GROUP BY component ORDER BY cnt DESC LIMIT 5",
            (make_upper, model_upper, year),
        )
        top_components = [{"component": row["component"], "count": row["cnt"]} for row in cursor.fetchall()]

        # 4. Prior-year count for trend
        cursor.execute(
            "SELECT COUNT(*) FROM complaints_fts"
            " WHERE make = ? AND model = ? AND CAST(year AS INTEGER) = ?",
            (make_upper, model_upper, year - 1),
        )
        prior_year_count: int = cursor.fetchone()[0]

        conn.close()

        if complaint_count > prior_year_count:
            trend = "increasing"
        elif complaint_count < prior_year_count:
            trend = "decreasing"
        else:
            trend = "stable"

        logger.info(
            "Dashboard: %s %s %d — complaints=%d tsbs=%d recalls=%d trend=%s",
            make_upper, model_upper, year, complaint_count, tsb_count, recall_count, trend,
        )

        return {
            "make": make_upper,
            "model": model_upper,
            "year": year,
            "complaint_count": complaint_count,
            "tsb_count": tsb_count,
            "recall_count": recall_count,
            "top_components": top_components,
            "trend": trend,
            "trend_current_year_count": complaint_count,
            "trend_prior_year_count": prior_year_count,
        }

    except Exception as exc:
        logger.error("Dashboard error for %s %s %d: %s", make, model, year, exc, exc_info=True)
        raise HTTPException(status_code=500, detail=str(exc))


# Checked AGENTS.md - implementing via Gemini delegation per GEMINI_WORKFLOW.md.
@app.get("/vehicle/complaints")
async def get_vehicle_complaints(
    make: str,
    model: str,
    component: str,
    year: int = Query(..., ge=1900, le=2030),
    page: int = Query(1, ge=1),
    limit: int = Query(10, ge=1, le=100),
    api_key: str = Depends(get_api_key),
) -> dict[str, object]:
    """Return paginated complaint summaries for a specific vehicle + component."""
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        make_upper = make.upper()
        model_upper = model.upper()
        component_like = f"%{component}%"
        offset = (page - 1) * limit

        cursor.execute(
            "SELECT COUNT(*) FROM complaints_fts"
            " WHERE make = ? AND model = ? AND CAST(year AS INTEGER) = ? AND component LIKE ?",
            (make_upper, model_upper, year, component_like),
        )
        total_count: int = cursor.fetchone()[0]

        cursor.execute(
            "SELECT year, component, summary FROM complaints_fts"
            " WHERE make = ? AND model = ? AND CAST(year AS INTEGER) = ? AND component LIKE ?"
            " LIMIT ? OFFSET ?",
            (make_upper, model_upper, year, component_like, limit, offset),
        )
        results = [dict(row) for row in cursor.fetchall()]

        conn.close()

        total_pages = math.ceil(total_count / limit) if total_count > 0 else 1

        logger.info(
            "ComponentComplaints: %s %s %d component=%s — %d results (page %d/%d)",
            make_upper, model_upper, year, component, total_count, page, total_pages,
        )

        return {
            "make": make_upper,
            "model": model_upper,
            "year": year,
            "component": component,
            "results": results,
            "total_count": total_count,
            "page": page,
            "total_pages": total_pages,
        }

    except Exception as exc:
        logger.error("ComponentComplaints error for %s %s %d: %s", make, model, year, exc, exc_info=True)
        raise HTTPException(status_code=500, detail=str(exc))


# Checked AGENTS.md - implementing via Gemini delegation per GEMINI_WORKFLOW.md.
@app.get("/vehicle/tsbs")
async def get_vehicle_tsbs(
    make: str,
    model: str,
    year: int = Query(..., ge=1900, le=2030),
    page: int = Query(1, ge=1),
    limit: int = Query(10, ge=1, le=100),
    api_key: str = Depends(get_api_key),
) -> dict[str, object]:
    """Return paginated TSB summaries for a specific vehicle."""
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        make_upper = make.upper()
        model_upper = model.upper()
        offset = (page - 1) * limit

        cursor.execute(
            "SELECT COUNT(*) FROM nhtsa_tsbs"
            " WHERE UPPER(make) = ? AND UPPER(model) = ? AND year = ?",
            (make_upper, model_upper, year),
        )
        total_count: int = cursor.fetchone()[0]

        cursor.execute(
            "SELECT bulletin_no, bulletin_date, component, summary"
            " FROM nhtsa_tsbs"
            " WHERE UPPER(make) = ? AND UPPER(model) = ? AND year = ?"
            " ORDER BY bulletin_date DESC"
            " LIMIT ? OFFSET ?",
            (make_upper, model_upper, year, limit, offset),
        )
        results = [dict(row) for row in cursor.fetchall()]
        conn.close()

        total_pages = math.ceil(total_count / limit) if total_count > 0 else 1

        logger.info(
            "VehicleTSBs: %s %s %d — %d results (page %d/%d)",
            make_upper, model_upper, year, total_count, page, total_pages,
        )

        return {
            "make": make_upper,
            "model": model_upper,
            "year": year,
            "results": results,
            "total_count": total_count,
            "page": page,
            "total_pages": total_pages,
        }

    except Exception as exc:
        logger.error("VehicleTSBs error for %s %s %d: %s", make, model, year, exc, exc_info=True)
        raise HTTPException(status_code=500, detail=str(exc))


# Checked AGENTS.md - implementing directly: simple read-only SQL query, no auth changes, no safety logic
@app.get("/vehicle/recalls")
async def get_vehicle_recalls(
    make: str,
    model: str,
    year: int = Query(..., ge=1900, le=2030),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    api_key: str = Depends(get_api_key),
) -> dict[str, object]:
    """Return paginated NHTSA recalls for a vehicle."""
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        make_upper = make.upper()
        model_upper = model.upper()
        offset = (page - 1) * page_size

        cursor.execute(
            "SELECT COUNT(*) FROM nhtsa_recalls"
            " WHERE UPPER(make) = ? AND UPPER(model) = ?"
            " AND ((year_from IS NULL OR year_from <= ?) AND (year_to IS NULL OR year_to >= ?))",
            (make_upper, model_upper, year, year),
        )
        total_count: int = cursor.fetchone()[0]

        cursor.execute(
            "SELECT campaign_no, component, manufacturer, vehicles_affected,"
            " report_date, summary, consequence, remedy, park_it, park_outside,"
            " year_from, year_to"
            " FROM nhtsa_recalls"
            " WHERE UPPER(make) = ? AND UPPER(model) = ?"
            " AND ((year_from IS NULL OR year_from <= ?) AND (year_to IS NULL OR year_to >= ?))"
            " ORDER BY report_date DESC"
            " LIMIT ? OFFSET ?",
            (make_upper, model_upper, year, year, page_size, offset),
        )
        rows = cursor.fetchall()
        conn.close()

        total_pages = math.ceil(total_count / page_size) if total_count > 0 else 1

        logger.info(
            "VehicleRecalls: %s %s %d — %d results (page %d/%d)",
            make_upper, model_upper, year, total_count, page, total_pages,
        )

        return {
            "make": make_upper,
            "model": model_upper,
            "year": year,
            "total": total_count,
            "page": page,
            "page_size": page_size,
            "recalls": [
                {
                    "campaign_no": row["campaign_no"],
                    "component": row["component"],
                    "manufacturer": row["manufacturer"],
                    "vehicles_affected": row["vehicles_affected"],
                    "report_date": row["report_date"],
                    "summary": row["summary"],
                    "consequence": row["consequence"],
                    "remedy": row["remedy"],
                    "park_it": bool(row["park_it"]),
                    "park_outside": bool(row["park_outside"]),
                    "year_from": row["year_from"],
                    "year_to": row["year_to"],
                }
                for row in rows
            ],
        }

    except Exception as exc:
        logger.error("VehicleRecalls error for %s %s %d: %s", make, model, year, exc, exc_info=True)
        raise HTTPException(status_code=500, detail=str(exc))


class HistoryEntry(BaseModel):
    vin: str | None = None
    year: int = Field(..., ge=1900, le=2030)
    make: str
    model: str
    engine: str | None = None
    symptoms: str
    dtc_codes: list[str] = Field(default_factory=list)
    findings: str
    candidate_count: int = 0
    has_warnings: bool = False


# Checked AGENTS.md - implementing via Gemini delegation per GEMINI_WORKFLOW.md.
# Simple INSERT into diagnosis_history — no safety logic.
@app.post("/history")
async def save_history(
    entry: HistoryEntry,
    api_key: str = Depends(get_api_key),
) -> dict[str, object]:
    """Save a diagnosis session to history."""
    import json as _json  # noqa: PLC0415
    from datetime import datetime as _dt  # noqa: PLC0415

    created_at = _dt.utcnow().isoformat()
    try:
        conn = sqlite3.connect(str(DIAG_DB_PATH))
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO diagnosis_history (
                created_at, vin, year, make, model, engine,
                symptoms, dtc_codes, findings, candidate_count, has_warnings
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                created_at, entry.vin, entry.year, entry.make.upper(), entry.model.upper(),
                entry.engine, entry.symptoms, _json.dumps(entry.dtc_codes),
                entry.findings, entry.candidate_count, 1 if entry.has_warnings else 0,
            ),
        )
        conn.commit()
        row_id = cursor.lastrowid
        conn.close()
        logger.info("History saved id=%s %s %s %d", row_id, entry.make, entry.model, entry.year)
        return {"id": row_id, "created_at": created_at}
    except Exception as exc:
        logger.error("History save error: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail=str(exc))


# Checked AGENTS.md - implementing via Gemini delegation per GEMINI_WORKFLOW.md.
# Simple SELECT from diagnosis_history — no safety logic.
@app.get("/history")
async def get_history(
    make: str,
    model: str,
    year: int | None = Query(default=None),
    vin: str | None = Query(default=None),
    limit: int = Query(default=20, ge=1, le=100),
    api_key: str = Depends(get_api_key),
) -> dict[str, object]:
    """Retrieve diagnosis history for a vehicle."""
    import json as _json  # noqa: PLC0415

    try:
        conn = sqlite3.connect(str(DIAG_DB_PATH))
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        where: list[str] = []
        params: list[Any] = []

        if vin:
            where.append("vin = ?")
            params.append(vin)
        else:
            where.append("UPPER(make) = UPPER(?)")
            params.append(make)
            where.append("UPPER(model) = UPPER(?)")
            params.append(model)
            if year is not None:
                where.append("year = ?")
                params.append(year)

        where_sql = " AND ".join(where) if where else "1=1"
        cursor.execute(
            f"SELECT * FROM diagnosis_history WHERE {where_sql} ORDER BY created_at DESC LIMIT ?",
            params + [limit],
        )
        rows = cursor.fetchall()

        entries = []
        for row in rows:
            d = dict(row)
            d["dtc_codes"] = _json.loads(d["dtc_codes"])
            d["has_warnings"] = bool(d["has_warnings"])
            entries.append(d)

        cursor.execute(
            f"SELECT COUNT(*) FROM diagnosis_history WHERE {where_sql}",
            params,
        )
        total: int = cursor.fetchone()[0]
        conn.close()

        logger.info("History GET %s %s: %d entries", make, model, len(entries))
        return {"entries": entries, "total": total}

    except Exception as exc:
        logger.error("History GET error: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail=str(exc))


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

