
from fastapi import FastAPI, HTTPException, Security, Depends
from fastapi.security import APIKeyHeader
import sqlite3
import uvicorn
import os
from typing import List, Optional

app = FastAPI(title="Automotive Diagnostic RAG Server")

# 🔒 SECURITY
API_KEY = "mechanic-secret-key-123" 
api_key_header = APIKeyHeader(name="X-API-KEY")

def get_api_key(api_key: str = Depends(api_key_header)):
    if api_key == API_KEY:
        return api_key
    raise HTTPException(status_code=403, detail="Invalid API Key")

# Path to the NEW fast database we just built
DB_PATH = r"C:\Users\potee\Documents\GitHub\automotive-diagnostic-skills\database\automotive_complaints.db"

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
        if not clean_query:
             clean_query = query # Let it fail or match nothing, but usually won't happen for valid inputs

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
        
        return {
            "query": query, 
            "sanitized_query": clean_query,
            "results": results,
            "source": "NHTSA Complaints Index"
        }
        
    except Exception as e:
        import traceback
        traceback.print_exc() # Print full stack trace to server logs
        raise HTTPException(status_code=500, detail=f"Server Error: {str(e)}")

if __name__ == "__main__":
    # Host on 0.0.0.0 for Tailscale remote access
    uvicorn.run(app, host="0.0.0.0", port=8000)
