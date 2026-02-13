
import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "database", "automotive_complaints.db")

def rebuild_fts():
    if not os.path.exists(DB_PATH):
        print(f"Database not found at {DB_PATH}")
        return
        
    conn = sqlite3.connect(DB_PATH)
    print("Connecting to database...")
    
    try:
        # Clear existing FTS data
        print("Clearing FTS table...")
        conn.execute("DELETE FROM tsbs_fts")
        
        # Populate
        print("Populating FTS table from main table...")
        # Note: ensuring column order matches the FTS table definition
        conn.execute("""
            INSERT INTO tsbs_fts (nhtsa_id, make, model, year, component, summary)
            SELECT nhtsa_id, make, model, year, component, summary 
            FROM nhtsa_tsbs
        """)
        
        # Rebuild/Optimize
        print("Optimizing index...")
        conn.execute("INSERT INTO tsbs_fts(tsbs_fts) VALUES('rebuild')")
        
        conn.commit()
        
        # Verify
        cursor = conn.cursor()
        cursor.execute("SELECT count(*) FROM tsbs_fts")
        count = cursor.fetchone()[0]
        print(f"Success! FTS Table now has {count} records.")
        
    except Exception as e:
        print(f"Error rebuilding FTS: {e}")
        conn.rollback()
    finally:
        conn.close()

if __name__ == "__main__":
    rebuild_fts()
