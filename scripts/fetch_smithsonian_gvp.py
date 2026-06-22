import os
import requests
import pandas as pd
import numpy as np

# Configuration
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
RAW_DIR = os.path.join(SCRIPT_DIR, "..", "data", "raw", "smithsonian_gvp")
PROCESSED_FILE = os.path.join(SCRIPT_DIR, "..", "data", "processed", "global_volcano_master.csv")

os.makedirs(RAW_DIR, exist_ok=True)

# We use the highly reliable TidyTuesday mirror of the Smithsonian GVP Holocene dataset
URLS = {
    "volcano": "https://raw.githubusercontent.com/rfordatascience/tidytuesday/master/data/2020/2020-05-12/volcano.csv",
    "eruptions": "https://raw.githubusercontent.com/rfordatascience/tidytuesday/master/data/2020/2020-05-12/eruptions.csv"
}

def download_data():
    files = {}
    for name, url in URLS.items():
        filepath = os.path.join(RAW_DIR, f"{name}.csv")
        files[name] = filepath
        if not os.path.exists(filepath):
            print(f"  [+] Fetching {name} dataset...")
            response = requests.get(url, timeout=30)
            response.raise_for_status()
            with open(filepath, "wb") as f:
                f.write(response.content)
        else:
            print(f"  [*] {name} dataset already cached.")
    return files

def process_volcano_data(files):
    print("[*] Merging Smithsonian Global Volcanism data...")
    
    # Load data
    df_volcano = pd.read_csv(files["volcano"])
    df_eruptions = pd.read_csv(files["eruptions"])
    
    # Drop latitude/longitude from eruptions to avoid collision with the master volcano coordinates
    df_eruptions = df_eruptions.drop(columns=['latitude', 'longitude'], errors='ignore')
    
    # Merge on volcano_number
    df = pd.merge(
        df_eruptions,
        df_volcano[['volcano_number', 'primary_volcano_type', 'latitude', 'longitude']],
        on='volcano_number',
        how='inner'
    )
    
    print("  [+] Applying The Cleaning Matrix...")
    
    # Filter timeframe: 2000 to present
    df = df[df['start_year'] >= 2000].copy()
    
    # Build start_date safely
    def safe_date(row):
        year = str(int(row['start_year'])) if pd.notna(row['start_year']) else "2000"
        month = str(int(row['start_month'])).zfill(2) if pd.notna(row['start_month']) and row['start_month'] != 0 else "01"
        day = str(int(row['start_day'])).zfill(2) if pd.notna(row['start_day']) and row['start_day'] != 0 else "01"
        return f"{year}-{month}-{day}"
        
    df['start_date'] = df.apply(safe_date, axis=1)
    df['start_date'] = pd.to_datetime(df['start_date'], errors='coerce', utc=True)
    
    # Rename and select columns
    df = df.rename(columns={
        'primary_volcano_type': 'type'
    })
    
    target_columns = [
        'volcano_name', 'latitude', 'longitude', 'type', 'start_date', 'vei'
    ]
    df = df[target_columns].copy()
    
    # Sort chronologically
    df = df.sort_values(by='start_date').reset_index(drop=True)
    
    # Drop records that have absolutely no VEI or unknown dates if needed (but we keep them as baseline)
    # The prompt says: retain historical base-rate metadata. VEI is critical, but some minor eruptions might have NaN VEI.
    
    # Export
    df.to_csv(PROCESSED_FILE, index=False)
    
    total_unique = len(df)
    max_vei = df['vei'].max()
    max_vei_volcanoes = df[df['vei'] == max_vei]['volcano_name'].unique()
    
    print("==================================================")
    print("  FUSION COMPLETE: MASTER VOLCANO DATASET READY   ")
    print("==================================================")
    print(f"Total Century Eruptions Extracted : {total_unique:,}")
    print(f"Highest Century VEI Recorded      : {max_vei} (Found at: {', '.join(max_vei_volcanoes)})")
    print(f"Saved To : {PROCESSED_FILE}")
    print("==================================================")

def main():
    print("==================================================")
    print("  CALAMITY AI: Smithsonian GVP Extraction Node")
    print("==================================================")
    files = download_data()
    process_volcano_data(files)

if __name__ == "__main__":
    main()
