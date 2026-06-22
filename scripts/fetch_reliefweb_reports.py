import os
import time
import requests
import json
import glob

# Configuration
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
OUTPUT_DIR = os.path.join(SCRIPT_DIR, "..", "data", "raw", "reliefweb_reports")
os.makedirs(OUTPUT_DIR, exist_ok=True)

# ReliefWeb v1 is decommissioned; v2 must be used with a pre-approved appname
BASE_URL = "https://api.reliefweb.int/v2/reports"
LIMIT = 1000

# You MUST provide your pre-approved ReliefWeb appname via environment variable
# due to the API security changes implemented in November 2025.
APPNAME = os.environ.get("RELIEFWEB_APPNAME")

def get_starting_offset():
    """Determine the next offset based on existing files."""
    files = glob.glob(os.path.join(OUTPUT_DIR, "reliefweb_reports_offset_*.json"))
    max_offset = -1
    for f in files:
        basename = os.path.basename(f)
        try:
            offset_str = basename.replace("reliefweb_reports_offset_", "").replace(".json", "")
            offset = int(offset_str)
            if offset > max_offset:
                max_offset = offset
        except ValueError:
            pass
    if max_offset == -1:
        return 0
    return max_offset + LIMIT

def fetch_chunk(offset):
    """Fetches a single offset chunk from the ReliefWeb API v2."""
    if not APPNAME:
        print("[-] FATAL: RELIEFWEB_APPNAME environment variable is missing.")
        print("    From Nov 1, 2025, ReliefWeb requires a pre-approved appname.")
        return "FATAL"

    print(f"[*] Fetching chunk with offset: {offset} (Limit: {LIMIT})")
    
    query_payload = {
        "limit": LIMIT,
        "offset": offset,
        "query": {
            "value": "date.created:[2000-01-01T00:00:00Z TO 2025-12-31T23:59:59Z]"
        },
        "filter": {
            "operator": "OR",
            "conditions": [
                {"field": "format.name", "value": "Situation Report"},
                {"field": "format.name", "value": "Appeal"}
            ]
        },
        "fields": {
            "include": [
                "id", 
                "date.created", 
                "title", 
                "body", 
                "primary_country.name", 
                "disaster.name", 
                "disaster.type.name"
            ]
        },
        "sort": ["date.created:asc"]
    }
    
    max_retries = 5
    base_wait = 5  # seconds
    
    # Appname must be in the URL parameters for v2
    request_url = f"{BASE_URL}?appname={APPNAME}"
    
    for attempt in range(max_retries):
        try:
            response = requests.post(request_url, json=query_payload, timeout=15)
            
            if response.status_code == 200:
                data = response.json()
                items = data.get("data", [])
                
                if not items:
                    print("  [+] No more items returned. Extraction complete.")
                    return "COMPLETE"
                
                filename = f"reliefweb_reports_offset_{offset}.json"
                filepath = os.path.join(OUTPUT_DIR, filename)
                with open(filepath, "w", encoding="utf-8") as f:
                    json.dump(items, f, ensure_ascii=False, indent=2)
                    
                print(f"  [+] Success! Saved {len(items)} items to {filename}")
                return "SUCCESS"
                
            elif response.status_code in [429, 500, 502, 503, 504]:
                wait_time = base_wait * (2 ** attempt)
                print(f"  [!] HTTP {response.status_code} received. Retrying in {wait_time}s... (Attempt {attempt+1}/{max_retries})")
                time.sleep(wait_time)
            elif response.status_code == 403:
                print(f"  [-] Fatal HTTP 403: Access Denied. Your appname '{APPNAME}' is not approved.")
                print(f"      Response: {response.text}")
                return "FATAL"
            else:
                print(f"  [-] Fatal HTTP {response.status_code}: {response.text}")
                return "FATAL"
                
        except (requests.exceptions.Timeout, requests.exceptions.ConnectionError) as e:
            wait_time = base_wait * (2 ** attempt)
            print(f"  [!] Network Error ({type(e).__name__}). Retrying in {wait_time}s... (Attempt {attempt+1}/{max_retries})")
            time.sleep(wait_time)
            
    print(f"  [-] Failed to fetch offset {offset} after {max_retries} attempts.")
    return "FATAL"

def main():
    print("==================================================")
    print("  CALAMITY AI: ReliefWeb RAG Corpus Extraction Node")
    print("==================================================")
    
    current_offset = get_starting_offset()
    print(f"[*] Resuming from offset: {current_offset}")
    
    while True:
        status = fetch_chunk(current_offset)
        
        if status == "COMPLETE":
            break
        elif status == "FATAL":
            print("[-] Extraction aborted due to fatal error.")
            break
            
        current_offset += LIMIT
        time.sleep(0.5)  # Be a good API citizen
        
    print("==================================================")
    print("  EXTRACTION CYCLE FINISHED")
    print("==================================================")

if __name__ == "__main__":
    main()
