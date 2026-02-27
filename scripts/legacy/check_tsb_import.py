
import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "database", "automotive_complaints.db")

def check_db():
    if not os.path.exists(DB_PATH):
        print("Database not found!")
        return
        
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Check count
    try:
        cursor.execute("SELECT count(*) FROM nhtsa_tsbs")
        count = cursor.fetchone()[0]
        print(f"Total TSBs: {count}")
    except Exception as e:
        print(f"Error querying table: {e}")
        return

    # Check sample
    cursor.execute("SELECT * FROM nhtsa_tsbs LIMIT 5")
    rows = cursor.fetchall()
    print("\nSample Data:")
    for row in rows:
        print(row)
        
    conn.close()

if __name__ == "__main__":
    check_db()
