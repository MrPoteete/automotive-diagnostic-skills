import requests
import sqlite3
import argparse
import os
import time

# NHTSA API Endpoint
API_URL = "https://api.nhtsa.gov/complaints/complaintsByVehicle"

# Database Path (Matches home_server.py)
DB_PATH = r"C:\Users\potee\Documents\GitHub\automotive-diagnostic-skills\database\automotive_complaints.db"

# Ensure database directory exists
os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)

def init_db():
    """Initialize the SQLite database with FTS5 and deduplication table."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # 1. Create Deduplication Table (odi_id is unique)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS processed_complaints (
            odi_id INTEGER PRIMARY KEY
        )
    """)
    
    # 2. Create FTS5 Table (if not exists)
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='complaints_fts'")
    if not cursor.fetchone():
        print(f"Creating new FTS database at {DB_PATH}...")
        cursor.execute("""
            CREATE VIRTUAL TABLE complaints_fts USING fts5(
                make, 
                model, 
                year, 
                component, 
                summary, 
                tokenize='porter'
            )
        """)
    
    conn.commit()
    return conn

def fetch_complaints(make, model, year):
    """Fetch complaints from NHTSA API."""
    print(f"Fetching complaints for {year} {make} {model}...")
    try:
        # NOTE: issueType='c' caused 400 errors, removed.
        # NHTSA API is case sensitive for some fields, best to use what worked in testing.
        params = {
            "make": make,
            "model": model,
            "modelYear": year,
        }
        response = requests.get(API_URL, params=params, timeout=10)
        
        if response.status_code != 200:
            print(f"Error: API returned status {response.status_code}")
            return []
            
        data = response.json()
        results = data.get("results", [])
        print(f"  Found {data.get('count', 0)} complaints.")
        return results
        
    except Exception as e:
        print(f"Error fetching data: {e}")
        return []

def save_complaints(conn, complaints, make, model, year):
    """Save complaints to the database, skipping duplicates."""
    cursor = conn.cursor()
    count_new = 0
    count_dup = 0
    
    for c in complaints:
        odi_id = c.get("odiNumber")
        if not odi_id:
            continue # Skip malformed records
            
        # Check for duplicate
        try:
            cursor.execute("INSERT INTO processed_complaints (odi_id) VALUES (?)", (odi_id,))
            
            # If we get here, it's a new record. Insert into FTS.
            summary = c.get("summary", "")
            # FIX: Field is 'components', not 'component'
            component = c.get("components", "Unknown") 
            
            cursor.execute("""
                INSERT INTO complaints_fts (make, model, year, component, summary)
                VALUES (?, ?, ?, ?, ?)
            """, (make, model, str(year), component, summary))
            
            count_new += 1
            
        except sqlite3.IntegrityError:
            # Duplicate ID
            count_dup += 1
            continue
        
    conn.commit()
    print(f"  Saved {count_new} new records. (Skipped {count_dup} duplicates)")

def get_models(make, year):
    """Fetch list of valid models for a make/year from SafetyRatings API."""
    url = f"https://api.nhtsa.gov/SafetyRatings/modelyear/{year}/make/{make}?format=json"
    try:
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            data = response.json()
            return [m["Model"] for m in data.get("Results", [])]
    except Exception as e:
        print(f"Warning: Could not fetch model list: {e}")
    return []

def load_targets():
    """Load mining targets from JSON file."""
    try:
        import json
        json_path = os.path.join(os.path.dirname(__file__), "mining_targets.json")
        with open(json_path, "r") as f:
            config = json.load(f)
        return config
    except Exception as e:
        print(f"Error loading mining_targets.json: {e}")
        return None

def process_targets(conn, targets, start_year, end_year):
    """Process a list of (Make, Model) tuples across a year range."""
    total_ops = len(targets) * (end_year - start_year + 1)
    current_op = 0
    
    print("\n--- STARTING FLEET MINING ---")
    print(f"Targeting {len(targets)} Models from {start_year} to {end_year}")
    print(f"Total Operations: {total_ops}\n")
    
    for make, model_input in targets:
        for year in range(start_year, end_year + 1):
            current_op += 1
            progress = (current_op / total_ops) * 100
            print(f"[{progress:.1f}%] Processing: {year} {make} {model_input}...")
            
            # 1. Get all valid variants for this specific year
            valid_models = get_models(make, year)
            
            # Fuzzy match variants
            matches = [m for m in valid_models if model_input in m.upper()]
            
            if not matches:
                # print(f"  No variants found. (Skipping)") 
                continue
            
            # 2. Fetch complaints for each variant
            total_saved = 0
            for model_variant in matches:
                complaints = fetch_complaints(make, model_variant, year)
                if complaints:
                    saved_count = save_complaints(conn, complaints, make, model_variant, year)
                    total_saved += saved_count
                time.sleep(1.5) # Extended sleep for fleet mode to avoid rate limits
            
            if total_saved > 0:
                 print(f"  -> Extracted {total_saved} unique records.")

def save_complaints(conn, complaints, make, model, year):
    """Save complaints to the database, skipping duplicates. Returns count of new records."""
    cursor = conn.cursor()
    count_new = 0
    count_dup = 0
    
    for c in complaints:
        odi_id = c.get("odiNumber")
        if not odi_id:
            continue # Skip malformed records
            
        # Check for duplicate
        try:
            cursor.execute("INSERT INTO processed_complaints (odi_id) VALUES (?)", (odi_id,))
            
            # If we get here, it's a new record. Insert into FTS.
            summary = c.get("summary", "")
            # FIX: Field is 'components', not 'component'
            component = c.get("components", "Unknown") 
            
            cursor.execute("""
                INSERT INTO complaints_fts (make, model, year, component, summary)
                VALUES (?, ?, ?, ?, ?)
            """, (make, model, str(year), component, summary))
            
            count_new += 1
            
        except sqlite3.IntegrityError:
            # Duplicate ID
            count_dup += 1
            continue
        
    conn.commit()
    # print(f"  Saved {count_new} new records. (Skipped {count_dup} duplicates)")
    return count_new

def main():
    parser = argparse.ArgumentParser(description="Automotive Diagnostic Data Miner")
    parser.add_argument("--make", help="Vehicle Make (e.g. Ford)")
    parser.add_argument("--model", help="Vehicle Model (e.g. F-150)")
    parser.add_argument("--year", help="Model Year (e.g. 2020)")
    parser.add_argument("--bulk", action="store_true", help="[DEPRECATED] Use --fleet instead")
    parser.add_argument("--fleet", action="store_true", help="Run comprehensive fleet mining from mining_targets.json")
    
    args = parser.parse_args()
    
    conn = init_db()
    
    if args.fleet:
        config = load_targets()
        if not config:
            return
            
        start_year = config.get("years", {}).get("start", 2005)
        end_year = config.get("years", {}).get("end", 2026)
        
        # Flatten config into list of (Make, Model)
        target_list = []
        for make, models in config.get("targets", {}).items():
            for model in models:
                target_list.append((make, model))
        
        process_targets(conn, target_list, start_year, end_year)
        
    elif args.make and args.model and args.year:
        # Single mode logic (simplified copy of process_targets logic for single item)
        valid = get_models(args.make, args.year)
        matches = [m for m in valid if args.model.upper() in m.upper()]
        if matches:
            print(f"Found variants: {matches}")
            for m in matches:
                complaints = fetch_complaints(args.make, m, args.year)
                if complaints:
                    save_complaints(conn, complaints, args.make, m, args.year)
        else:
            print("No matching models found.")

    else:
        parser.print_help()
        
    conn.close()
    print("Done.")

if __name__ == "__main__":
    main()
