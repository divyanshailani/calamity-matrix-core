import os
import glob
import pandas as pd

# Configuration
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
RAW_DIR = os.path.join(SCRIPT_DIR, "..", "data", "raw", "usgs_earthquakes")
PROCESSED_FILE = os.path.join(SCRIPT_DIR, "..", "data", "processed", "global_seismic_master.csv")
COLUMNS_TO_KEEP = ['time', 'latitude', 'longitude', 'depth', 'mag', 'place', 'id']

def process_seismic_data():
    print("==================================================")
    print("  CALAMITY AI: Seismic Matrix Fusion Node         ")
    print("==================================================")
    
    # 1. Data Aggregation
    print("[*] Reading raw CSV chunks...")
    csv_files = glob.glob(os.path.join(RAW_DIR, "*.csv"))
    if not csv_files:
        print("[-] No CSV files found. Extraction must run first.")
        return
        
    df_list = []
    for f in csv_files:
        try:
            # low_memory=False to prevent mixed type inference warnings
            df_chunk = pd.read_csv(f, low_memory=False)
            df_list.append(df_chunk)
        except pd.errors.EmptyDataError:
            pass # Skip empty files
            
    df = pd.concat(df_list, ignore_index=True)
    print(f"  [+] Loaded {len(df)} total raw rows.")
    
    # 2. The Cleaning Matrix
    print("[*] Applying The Cleaning Matrix...")
    # Drop duplicates based on the unique USGS id
    df = df.drop_duplicates(subset=['id'])
    
    # Ensure all required columns exist
    missing_cols = [col for col in COLUMNS_TO_KEEP if col not in df.columns]
    if missing_cols:
        print(f"[-] Missing expected columns in raw data: {missing_cols}")
        return
        
    df = df[COLUMNS_TO_KEEP].copy()
    
    # Convert time to UTC datetime objects
    print("  [+] Converting timestamps to UTC...")
    df['time'] = pd.to_datetime(df['time'], utc=True)
    
    # Sort chronologically (oldest to newest)
    print("  [+] Sorting chronologically (oldest to newest)...")
    df = df.sort_values(by='time').reset_index(drop=True)
    
    # Clean null magnitudes or coordinates
    df = df.dropna(subset=['mag', 'latitude', 'longitude'])
    
    # 3. Baseline Feature Engineering
    print("[*] Engineering baseline statistical features...")
    df['year'] = df['time'].dt.year
    df['month'] = df['time'].dt.month
    
    # Global days_since_last_event
    df['global_days_since_last_event'] = (df['time'] - df['time'].shift(1)).dt.total_seconds() / 86400.0
    df['global_days_since_last_event'] = df['global_days_since_last_event'].fillna(0)
    
    # Localized days_since_last_event (Grid-based pressure build-up)
    # Round to 0 decimal places (~111km x 111km grid box)
    df['grid_lat'] = df['latitude'].round(0)
    df['grid_lon'] = df['longitude'].round(0)
    
    print("  [+] Calculating localized seismic pressure gradients...")
    # Group by the grid and calculate the time difference for each specific geographic grid box
    df['localized_days_since_last_event'] = df.groupby(['grid_lat', 'grid_lon'])['time'].diff().dt.total_seconds() / 86400.0
    df['localized_days_since_last_event'] = df['localized_days_since_last_event'].fillna(0)
    
    # 4. Export
    print("[*] Exporting master analytical dataset...")
    df.to_csv(PROCESSED_FILE, index=False)
    
    # Print Final Summary
    total_unique = len(df)
    min_date = df['time'].min().strftime('%Y-%m-%d')
    max_date = df['time'].max().strftime('%Y-%m-%d')
    
    print("==================================================")
    print("  FUSION COMPLETE: MASTER SEISMIC DATASET READY   ")
    print("==================================================")
    print(f"Total Unique Events : {total_unique:,}")
    print(f"Chronological Range : {min_date} to {max_date}")
    print("--------------------------------------------------")
    print("Top 3 Highest Magnitude Earthquakes:")
    
    top_3 = df.nlargest(3, 'mag')
    for i, (_, row) in enumerate(top_3.iterrows(), 1):
        event_date = row['time'].strftime('%Y-%m-%d %H:%M:%S UTC')
        print(f"  {i}. Magnitude {row['mag']:.1f} | {row['place']} | {event_date}")
    print("==================================================")

if __name__ == "__main__":
    process_seismic_data()
