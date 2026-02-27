
import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "database", "automotive_complaints.db")

def debug_search():
    if not os.path.exists(DB_PATH):
        print(f"Database not found at {DB_PATH}")
        return
        
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    # 1. Check counts
    print("--- COUNTS ---")
    try:
        cursor.execute("SELECT count(*) FROM nhtsa_tsbs")
        print(f"nhtsa_tsbs count: {cursor.fetchone()[0]}")
        
        cursor.execute("SELECT count(*) FROM tsbs_fts")
        print(f"tsbs_fts count: {cursor.fetchone()[0]}")
    except Exception as e:
        print(f"Error checking counts: {e}")

    # 2. Check sample data formatting
    print("\n--- SAMPLE DATA (Limit 3) ---")
    cursor.execute("SELECT make, model, year, summary FROM nhtsa_tsbs LIMIT 3")
    for row in cursor.fetchall():
        print(dict(row))

    # 3. Test specific queries
    test_queries = [
        "Ford F150",
        "Ford F-150", 
        "Silverado",
        "Chevy Silverado",
        "Chevrolet Silverado"
    ]
    
    print("\n--- TEST SEARCHES ---")
    for q in test_queries:
        print(f"Query: '{q}'")
        
        # Simulate logic from server
        import re
        clean_query = re.sub(r'[^a-zA-Z0-9\s]', ' ', q)
        clean_query = re.sub(r'\s+', ' ', clean_query).strip()
        print(f"  Clean: '{clean_query}'")
        
        sql = "SELECT count(*) FROM tsbs_fts WHERE tsbs_fts MATCH ?"
        try:
            cursor.execute(sql, (clean_query,))
            count = cursor.fetchone()[0]
            print(f"  Matches: {count}")
            
            if count == 0:
                # Try partial?
                print("  Trying wildcard search...")
                wildcard_query = f"{clean_query}*"
                cursor.execute(sql, (wildcard_query,))
                wc_count = cursor.fetchone()[0]
                print(f"  Wildcard Matches: {wc_count}")
                
        except Exception as e:
            print(f"  SQL Error: {e}")

    conn.close()

if __name__ == "__main__":
    debug_search()
