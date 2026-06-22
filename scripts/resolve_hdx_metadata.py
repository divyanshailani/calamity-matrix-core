import os
import sys
import time
import requests
import argparse
from psycopg2 import pool

# Add root directory to python path
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.abspath(os.path.join(SCRIPT_DIR, '..')))

from src.config import DB_CONFIG, _require

APPNAME = os.getenv("RELIEFWEB_APPNAME")
if not APPNAME:
    print("[-] Warning: RELIEFWEB_APPNAME is not set. API calls will fail with 403.")

def fetch_with_backoff(url: str, max_retries: int = 5) -> dict:
    base_wait = 1  # seconds
    
    for attempt in range(max_retries):
        try:
            # We append appname to the URL if APPNAME is present
            separator = "&" if "?" in url else "?"
            req_url = f"{url}{separator}appname={APPNAME}" if APPNAME else url
            
            response = requests.get(req_url, timeout=10)
            
            if response.status_code == 200:
                time.sleep(0.4) # Normal rate limit compliance
                return response.json()
                
            elif response.status_code in [429, 500, 502, 503, 504]:
                wait_time = base_wait * (2 ** attempt)
                print(f"  [!] HTTP {response.status_code} received. Retrying in {wait_time} seconds (Attempt {attempt+1}/{max_retries})")
                time.sleep(wait_time)
            elif response.status_code == 403:
                print("  [!] HTTP 403: Appname missing or invalid.")
                break
            else:
                print(f"  [!] HTTP {response.status_code} received for {url}. Giving up.")
                break
                
        except requests.exceptions.RequestException as e:
            wait_time = base_wait * (2 ** attempt)
            print(f"  [!] Request error: {e}. Retrying in {wait_time}s.")
            time.sleep(wait_time)
            
    return None

def resolve_country(country_url: str, cache: dict) -> str:
    if country_url in cache:
        return cache[country_url]
    
    data = fetch_with_backoff(country_url)
    if data and "data" in data and len(data["data"]) > 0:
        name = data["data"][0].get("fields", {}).get("name")
        if name:
            cache[country_url] = name
            return name
    return None

def resolve_disaster(disaster_id: str, cache: dict) -> str:
    if disaster_id in cache:
        return cache[disaster_id]
        
    url = f"https://api.reliefweb.int/v2/disaster_types/{disaster_id}"
    data = fetch_with_backoff(url)
    if data and "data" in data and len(data["data"]) > 0:
        name = data["data"][0].get("fields", {}).get("name")
        if name:
            cache[disaster_id] = name
            return name
    return None

def main():
    parser = argparse.ArgumentParser(description="Resolve HDX metadata using ReliefWeb API")
    parser.add_argument("--execute", action="store_true", help="Execute the updates (disables dry-run)")
    args = parser.parse_args()
    
    dry_run = not args.execute
    if dry_run:
        print("[*] Running in DRY-RUN mode. No changes will be committed.")
        print("[*] Use --execute to commit changes to the database.\n")
    else:
        print("[!] Running in EXECUTE mode. Changes will be committed!\n")
        
    print("[*] Connecting to PostgreSQL...")
    db_pool = pool.SimpleConnectionPool(1, 2, **DB_CONFIG)
    conn = db_pool.getconn()
    
    country_cache = {}
    disaster_cache = {}
    updates = []
    
    try:
        with conn.cursor() as cur:
            # 1. Resolve Countries
            print("[*] Finding unresolved countries...")
            cur.execute("SELECT id, country FROM disaster_narratives WHERE country LIKE 'http%';")
            country_rows = cur.fetchall()
            print(f"  -> Found {len(country_rows)} rows with raw country URLs.")
            
            for row_id, raw_url in country_rows:
                resolved_name = resolve_country(raw_url, country_cache)
                if resolved_name:
                    print(f"  [+] Mapped country {raw_url} -> {resolved_name}")
                    updates.append((row_id, "country", resolved_name))
                else:
                    print(f"  [-] Failed to resolve country: {raw_url}")
                    
            # 2. Resolve Disasters
            print("\n[*] Finding unresolved disaster types...")
            # We look for purely numeric strings
            cur.execute("SELECT id, disaster_type FROM disaster_narratives WHERE disaster_type ~ '^\\d+$';")
            disaster_rows = cur.fetchall()
            print(f"  -> Found {len(disaster_rows)} rows with raw disaster IDs.")
            
            for row_id, raw_id in disaster_rows:
                resolved_name = resolve_disaster(raw_id, disaster_cache)
                if resolved_name:
                    print(f"  [+] Mapped disaster {raw_id} -> {resolved_name}")
                    updates.append((row_id, "disaster_type", resolved_name))
                else:
                    print(f"  [-] Failed to resolve disaster ID: {raw_id}")
            
            # 3. Apply Updates
            if updates:
                print(f"\n[*] Applying {len(updates)} metadata updates...")
                for row_id, col, val in updates:
                    query = f"UPDATE disaster_narratives SET {col} = %s WHERE id = %s;"
                    if dry_run:
                        print(f"  [DRY-RUN] Would update Row {row_id} | {col} = '{val}'")
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
