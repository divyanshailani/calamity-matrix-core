import os
import sys
import argparse
import pandas as pd
from psycopg2 import pool

# Add root directory to python path
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.abspath(os.path.join(SCRIPT_DIR, '..')))

from src.config import DB_CONFIG

def load_csv_mappings():
    csv_path = os.path.join(SCRIPT_DIR, "..", "data", "raw", "hdx_corpus", "reliefweb-disasters-list.csv")
    if not os.path.exists(csv_path):
        print(f"[-] CSV file not found at {csv_path}")
        return {}, {}
        
    df = pd.read_csv(csv_path, low_memory=False)
    
    country_cache = {}
    for _, row in df.iterrows():
        href = row.get("primary_country-href")
        if pd.notna(href):
            country_cache[str(href).strip()] = (
                str(row.get("primary_country-name")),
                float(row.get("primary_country-location-lat")) if pd.notna(row.get("primary_country-location-lat")) else None,
                float(row.get("primary_country-location-lon")) if pd.notna(row.get("primary_country-location-lon")) else None
            )
            
    disaster_cache = {}
    for _, row in df.iterrows():
        tid = row.get("primary_type-id")
        tname = row.get("primary_type-name")
        if pd.notna(tid) and pd.notna(tname):
            disaster_cache[str(int(tid))] = str(tname)
            
    return country_cache, disaster_cache

def main():
    parser = argparse.ArgumentParser(description="Resolve HDX metadata using local CSV mapping")
    parser.add_argument("--execute", action="store_true", help="Execute the updates (disables dry-run)")
    args = parser.parse_args()
    
    dry_run = not args.execute
    if dry_run:
        print("[*] Running in DRY-RUN mode. No changes will be committed.")
        print("[*] Use --execute to commit changes to the database.\n")
    else:
        print("[!] Running in EXECUTE mode. Changes will be committed!\n")
        
    print("[*] Loading offline metadata from CSV...")
    country_cache, disaster_cache = load_csv_mappings()
    print(f"  -> Loaded {len(country_cache)} country mappings and {len(disaster_cache)} disaster type mappings.")
    
    print("[*] Connecting to PostgreSQL...")
    db_pool = pool.SimpleConnectionPool(1, 2, **DB_CONFIG)
    conn = db_pool.getconn()
    
    updates = []
    
    try:
        with conn.cursor() as cur:
            print("[*] Ensuring lat/lng columns exist...")
            cur.execute("ALTER TABLE disaster_narratives ADD COLUMN IF NOT EXISTS lat FLOAT, ADD COLUMN IF NOT EXISTS lng FLOAT;")
            if not dry_run:
                conn.commit()
            
            # 1. Resolve Countries
            print("[*] Finding unresolved countries...")
            cur.execute("SELECT id, country FROM disaster_narratives WHERE country LIKE 'http%';")
            country_rows = cur.fetchall()
            print(f"  -> Found {len(country_rows)} rows with raw country URLs.")
            
            for row_id, raw_url in country_rows:
                if raw_url in country_cache:
                    resolved_name, lat, lon = country_cache[raw_url]
                    print(f"  [+] Mapped country {raw_url} -> {resolved_name} (lat: {lat}, lng: {lon})")
                    updates.append((row_id, "country_coords", (resolved_name, lat, lon)))
                else:
                    print(f"  [-] Failed to resolve country locally: {raw_url}")
                    
            # 2. Resolve Disasters
            print("\n[*] Finding unresolved disaster types...")
            cur.execute("SELECT id, disaster_type FROM disaster_narratives WHERE disaster_type ~ '^\\d+$';")
            disaster_rows = cur.fetchall()
            print(f"  -> Found {len(disaster_rows)} rows with raw disaster IDs.")
            
            for row_id, raw_id in disaster_rows:
                if raw_id in disaster_cache:
                    resolved_name = disaster_cache[raw_id]
                    print(f"  [+] Mapped disaster {raw_id} -> {resolved_name}")
                    updates.append((row_id, "disaster_type", resolved_name))
                else:
                    print(f"  [-] Failed to resolve disaster ID locally: {raw_id}")
            
            # 3. Apply Updates
            if updates:
                print(f"\n[*] Applying {len(updates)} metadata updates...")
                for item in updates:
                    row_id = item[0]
                    update_type = item[1]
                    
                    if update_type == "country_coords":
                        name, lat, lon = item[2]
                        query = "UPDATE disaster_narratives SET country = %s, lat = %s, lng = %s WHERE id = %s;"
                        if dry_run:
                            print(f"  [DRY-RUN] Would update Row {row_id} | country='{name}', lat={lat}, lng={lon}")
                        else:
                            cur.execute(query, (name, lat, lon, row_id))
                    elif update_type == "disaster_type":
                        val = item[2]
                        query = "UPDATE disaster_narratives SET disaster_type = %s WHERE id = %s;"
                        if dry_run:
                            print(f"  [DRY-RUN] Would update Row {row_id} | disaster_type='{val}'")
                        else:
                            cur.execute(query, (val, row_id))
                
                if not dry_run:
                    conn.commit()
                    print("[+] Transactions committed successfully.")
            else:
                print("\n[*] No updates required.")
                
    except Exception as e:
        print(f"[-] Database error: {e}")
        if not dry_run:
            conn.rollback()
    finally:
        db_pool.putconn(conn)
        print("\n[*] Script execution complete.")

if __name__ == "__main__":
    main()
