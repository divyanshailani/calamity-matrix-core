import os
import glob
import pandas as pd
import warnings

# Configuration
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
RAW_DIR = os.path.join(SCRIPT_DIR, "..", "data", "raw", "emdat")
PROCESSED_FILE = os.path.join(SCRIPT_DIR, "..", "data", "processed", "global_emdat_master.csv")

def process_emdat_data():
    print("==================================================")
    print("  CALAMITY AI: EM-DAT Matrix Fusion Node          ")
    print("==================================================")
    
    print("[*] Reading raw EM-DAT Excel datasets...")
    excel_files = glob.glob(os.path.join(RAW_DIR, "*.xlsx"))
    
    if not excel_files:
        print("[-] No EM-DAT XLSX files found.")
        return
        
    filepath = excel_files[0]
    try:
        # Suppress openpyxl warnings
        warnings.simplefilter(action='ignore', category=UserWarning)
        
        print(f"  [+] Loading {os.path.basename(filepath)}...")
        # EM-DAT standard files often have a metadata header block.
        # We will load the first 20 rows to detect where the actual header is (usually contains 'DisNo' or 'Year').
        df_preview = pd.read_excel(filepath, nrows=20, engine="openpyxl")
        
        header_row_idx = 0
        for idx, row in df_preview.iterrows():
            row_str = " ".join([str(x) for x in row.values])
            if 'DisNo' in row_str or 'Disaster Group' in row_str:
                # The index 'idx' in pandas is 0-based for the data rows (so the file's row is idx+2)
                # If we use header=idx+1, pandas uses that row as the header.
                header_row_idx = idx + 1
                break
                
        print(f"  [*] Detected data header at row index {header_row_idx}")
        df = pd.read_excel(filepath, header=header_row_idx, engine="openpyxl")
            
        print(f"  [+] Extracted {len(df)} raw disaster impact records.")
        
    except Exception as e:
        print(f"  [-] Error loading {filepath}: {e}")
        return
        
    print("[*] Applying The Cleaning Matrix...")
    
    # Standardize columns by stripping whitespace
    df.columns = [str(col).strip() for col in df.columns]
    
    # Target columns for the Math Engine (Regression Targets)
    target_columns = [
        'DisNo.', 'Disaster Group', 'Disaster Subgroup', 'Disaster Type',
        'Country', 'Region', 'Location', 'Latitude', 'Longitude',
        'Start Year', 'Start Month', 'Start Day',
        'End Year', 'End Month', 'End Day',
        'Total Deaths', 'No. Injured', 'No. Affected', 'Total Affected', "Total Damage ('000 US$)", "Total Damage, Adjusted ('000 US$)", "CPI"
    ]
    
    # Select only columns that exist in the downloaded file
    available_cols = [c for c in target_columns if c in df.columns]
    df = df[available_cols].copy()
    
    # Basic cleaning
    if 'DisNo.' in df.columns:
        # Drop empty rows and deduplicate
        df = df.dropna(subset=['DisNo.'])
        df = df.drop_duplicates(subset=['DisNo.'])
        
    print("[*] Exporting master analytical dataset...")
    df.to_csv(PROCESSED_FILE, index=False)
    
    total_unique = len(df)
    min_year = int(df['Start Year'].min()) if 'Start Year' in df.columns and not df['Start Year'].isnull().all() else "Unknown"
    max_year = int(df['Start Year'].max()) if 'Start Year' in df.columns and not df['Start Year'].isnull().all() else "Unknown"
    
    print("==================================================")
    print("  FUSION COMPLETE: MASTER EM-DAT DATASET READY    ")
    print("==================================================")
    print(f"Total Unique Impact Events  : {total_unique:,}")
    print(f"Chronological Range         : {min_year} to {max_year}")
    print(f"Saved To : {PROCESSED_FILE}")
    print("==================================================")

if __name__ == "__main__":
    process_emdat_data()
