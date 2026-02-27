
import sqlite3
import os

db_path = r"C:\Users\potee\Documents\GitHub\automotive-diagnostic-skills\database\automotive_complaints.db"

if not os.path.exists(db_path):
    print(f"Database not found at {db_path}")
    exit()

try:
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Get all tables
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = cursor.fetchall()
    print("Tables in database:", [t[0] for t in tables])
    
    for table in tables:
        table_name = table[0]
        try:
            cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
            count = cursor.fetchone()[0]
            print(f"Table '{table_name}': {count} entries")
        except Exception as e:
            print(f"Could not count table {table_name}: {e}")
            
    conn.close()
    
except Exception as e:
    print(f"Error inspecting database: {e}")
