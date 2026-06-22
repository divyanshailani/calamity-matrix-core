import os
import time
import requests
import json

# Configuration
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
OUTPUT_DIR = os.path.join(SCRIPT_DIR, "..", "data", "raw", "nasa_eonet")
os.makedirs(OUTPUT_DIR, exist_ok=True)

BASE_URL = "https://eonet.gsfc.nasa.gov/api/v3/events"
CATEGORIES = "wildfires,severeStorms,floods,volcanoes"
START_YEAR = 2000
END_YEAR = 2025

def fetch_year(year):
    """Fetches NASA EONET events for a given year."""
    filename = f"nasa_eonet_{year}.json"
    filepath = os.path.join(OUTPUT_DIR, filename)
    
    # Checkpointing: Skip if already fetched successfully
    if os.path.exists(filepath):
        print(f"[*] {year}: Skipping. File {filename} already exists.")
        return "SKIPPED"
        
    start_date = f"{year}-01-01"
    end_date = f"{year}-12-31"
    
    params = {
        "category": CATEGORIES,
        "start": start_date,
        "end": end_date
    }
    
    print(f"[*] Fetching {year} (Dates: {start_date} to {end_date})...")
    
    max_retries = 5
    base_wait = 5  # seconds
    
    for attempt in range(max_retries):
        try:
            response = requests.get(BASE_URL, params=params, timeout=30)
            
            if response.status_code == 200:
                data = response.json()
                events = data.get("events", [])
                
                with open(filepath, "w", encoding="utf-8") as f:
                    json.dump(events, f, ensure_ascii=False, indent=2)
                    
                print(f"  [+] Success! Saved {len(events)} events to {filename}")
                return "SUCCESS"
                
            elif response.status_code in [429, 500, 502, 503, 504]:
                wait_time = base_wait * (2 ** attempt)
                print(f"  [!] HTTP {response.status_code} received. Retrying in {wait_time}s... (Attempt {attempt+1}/{max_retries})")
                time.sleep(wait_time)
            else:
                print(f"  [-] Fatal HTTP {response.status_code}: {response.text}")
                return "FATAL"
                
        except (requests.exceptions.Timeout, requests.exceptions.ConnectionError) as e:
            wait_time = base_wait * (2 ** attempt)
            print(f"  [!] Network Error ({type(e).__name__}). Retrying in {wait_time}s... (Attempt {attempt+1}/{max_retries})")
            time.sleep(wait_time)
            
    print(f"  [-] Failed to fetch year {year} after {max_retries} attempts.")
    return "FATAL"

def main():
    print("==================================================")
    print("  CALAMITY AI: NASA EONET Spatial Extraction Node")
    print("==================================================")
    
    for year in range(START_YEAR, END_YEAR + 1):
        status = fetch_year(year)
        
        if status == "FATAL":
            print("[-] Extraction aborted due to fatal error.")
            break
            
        # Polite delay to prevent rate-limiting
        time.sleep(1)
        
    print("==================================================")
    print("  EXTRACTION CYCLE FINISHED")
    print("==================================================")

if __name__ == "__main__":
    main()
