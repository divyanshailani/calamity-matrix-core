import os
import time
import requests
import calendar
from datetime import datetime, timedelta

# Configuration
START_YEAR = 2000
END_YEAR = 2025
MIN_MAGNITUDE = 5.0
BASE_URL = "https://earthquake.usgs.gov/fdsnws/event/1/query"

# Output Directory Setup
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
OUTPUT_DIR = os.path.join(SCRIPT_DIR, "..", "data", "raw", "usgs_earthquakes")
os.makedirs(OUTPUT_DIR, exist_ok=True)
os.makedirs(os.path.join(SCRIPT_DIR, "..", "data", "processed"), exist_ok=True)
os.makedirs(os.path.join(SCRIPT_DIR, "..", "models"), exist_ok=True)
os.makedirs(os.path.join(SCRIPT_DIR, "..", "notebooks"), exist_ok=True)


def fetch_month_chunk(year, month):
    """Fetches a 1-month chunk of USGS earthquake data with exponential backoff."""
    # Determine the start and end dates for the month
    start_date = f"{year}-{month:02d}-01"
    _, last_day = calendar.monthrange(year, month)
    end_date = f"{year}-{month:02d}-{last_day}T23:59:59"
    
    filename = f"usgs_mag5_{year}_{month:02d}.csv"
    filepath = os.path.join(OUTPUT_DIR, filename)
    
    current_year = datetime.now().year
    current_month = datetime.now().month
    is_current_month = (year == current_year and month == current_month)
    
    # Checkpointing: Skip if already downloaded, UNLESS it's the current month (to fetch live updates)
    if not is_current_month and os.path.exists(filepath) and os.path.getsize(filepath) > 0:
        print(f"[*] Skipping {start_date} to {end_date} (Already downloaded: {filename})")
        return True

    print(f"[*] Fetching data from {start_date} to {end_date}...")
    
    params = {
        "format": "csv",
        "starttime": start_date,
        "endtime": end_date,
        "minmagnitude": MIN_MAGNITUDE
    }
    
    max_retries = 5
    base_wait = 5  # seconds
    
    for attempt in range(max_retries):
        try:
            # 15s timeout to prevent infinite hanging
            response = requests.get(BASE_URL, params=params, timeout=15)
            
            if response.status_code == 200:
                with open(filepath, "w", encoding="utf-8") as f:
                    f.write(response.text)
                print(f"  [+] Success! Saved to {filename}")
                return True
                
            elif response.status_code in [429, 500, 502, 503, 504]:
                wait_time = base_wait * (2 ** attempt)
                print(f"  [!] HTTP {response.status_code} received. Retrying in {wait_time}s... (Attempt {attempt+1}/{max_retries})")
                time.sleep(wait_time)
            else:
                print(f"  [-] Fatal HTTP {response.status_code}: {response.text}")
                return False
                
        except (requests.exceptions.Timeout, requests.exceptions.ConnectionError) as e:
            wait_time = base_wait * (2 ** attempt)
            print(f"  [!] Network Error ({type(e).__name__}). Retrying in {wait_time}s... (Attempt {attempt+1}/{max_retries})")
            time.sleep(wait_time)
            
    print(f"  [-] Failed to fetch {start_date} after {max_retries} attempts.")
    return False

def main():
    print("==================================================")
    print("  CALAMITY AI: USGS Seismic Data Extraction Node  ")
    print("==================================================")
    
    total_months = 0
    successful_months = 0
    
    # Temporal Chunking loop
    for year in range(START_YEAR, END_YEAR + 1):
        # Prevent fetching future months in the current year
        current_year = datetime.now().year
        current_month = datetime.now().month
        
        for month in range(1, 13):
            if year == current_year and month > current_month:
                break
                
            total_months += 1
            success = fetch_month_chunk(year, month)
            if success:
                successful_months += 1
            
            # Tiny sleep between healthy requests to be a good API citizen
            time.sleep(0.5)
            
    print("==================================================")
    print(f"Extraction Complete: {successful_months}/{total_months} months downloaded.")

if __name__ == "__main__":
    main()
