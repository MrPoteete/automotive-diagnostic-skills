
import sqlite3
import os
import glob

# Define database path relative to project root
DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "database", "automotive_complaints.db")
TSB_DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "TSB DATA")

def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def import_file(conn, filepath):
    print(f"Importing {os.path.basename(filepath)}...")
    cursor = conn.cursor()
    
    count = 0
    # Use latin-1 encoding as these are older legacy files often using that encoding
    # Use 'replace' to avoid crashing on random bad bytes
    with open(filepath, 'r', encoding='latin-1', errors='replace') as f:
        for line in f:
            parts = line.strip().split('\t')
            if len(parts) < 14:
                # Some lines might be malformed or empty
                continue
            
            # Extract fields
            # 0: RECORD_ID
            # 1: BULLETIN_NO
            # 4: BULLETIN_DATE
            # 7: MAKE
            # 8: MODEL
            # 9: YEAR
            # 10: COMPONENT
            # 13: SUMMARY
            
            data = (
                parts[0], # nhtsa_id
                parts[1], # bulletin_no
                parts[4], # bulletin_date
                parts[7], # make
                parts[8], # model
                parts[9] if parts[9].isdigit() else 0, # year
                parts[10], # component
                parts[13] # summary
            )
            
            try:
                cursor.execute("""
                    INSERT OR IGNORE INTO nhtsa_tsbs 
                    (nhtsa_id, bulletin_no, bulletin_date, make, model, year, component, summary)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, data)
                count += 1
            except Exception as e:
                print(f"Error inserting line: {e}")
                continue
                
            if count % 10000 == 0:
                print(f"  Processed {count} records...")
                conn.commit()

    conn.commit()
    print(f"Finished {os.path.basename(filepath)}. Total imported: {count}")

def main():
    if not os.path.exists(DB_PATH):
        print(f"Database not found at {DB_PATH}. Please run schema creation first.")
        # We can also attempt to run schema creation here if needed
        # but better to assume schema exists or run the sql file.
    
    # Run schema creation just in case (idempotent)
    schema_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "database", "schema_nhtsa_tsbs.sql")
    if os.path.exists(schema_path):
        print("Ensuring schema exists...")
        conn = get_db_connection()
        with open(schema_path, 'r') as f:
            conn.executescript(f.read())
        conn.close()
    
    conn = get_db_connection()
    
    # Find all txt files in subdirectories of TSB DATA
    pattern = os.path.join(TSB_DATA_DIR, "**", "*.txt")
    files = glob.glob(pattern, recursive=True)
    
    print(f"Found {len(files)} TSB data files.")
    
    for filepath in files:
        import_file(conn, filepath)
        
    # Rebuild FTS index if needed
    print("optimizing FTS index...")
    conn.execute("INSERT INTO tsbs_fts(tsbs_fts) VALUES('rebuild')")
    conn.commit()
    
    conn.close()
    print("Import complete.")

if __name__ == "__main__":
    main()
