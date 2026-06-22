import os
import requests
import pandas as pd

# Configuration
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
RAW_DIR = os.path.join(SCRIPT_DIR, "..", "data", "raw", "hdx_corpus")
PROCESSED_DIR = os.path.join(SCRIPT_DIR, "..", "data", "processed", "rag_texts")
PROCESSED_FILE = os.path.join(PROCESSED_DIR, "hdx_baseline_corpus.csv")

os.makedirs(RAW_DIR, exist_ok=True)
os.makedirs(PROCESSED_DIR, exist_ok=True)

CKAN_URL = "https://data.humdata.org/api/3/action/package_search"

def search_hdx():
    """Queries HDX API for relevant disaster summary datasets."""
    print("[*] Querying HDX API for text narrative datasets...")
    params = {
        "q": "situation report OR disaster summary OR humanitarian needs",
        "rows": 30
    }
    
    response = requests.get(CKAN_URL, params=params, timeout=30)
    response.raise_for_status()
    return response.json().get("result", {}).get("results", [])

def download_resources(packages):
    """Extracts and downloads the top CSV/XLSX resources."""
    downloaded_files = []
    
    for pkg in packages:
        if len(downloaded_files) >= 5: # Bumped to 5 to get more chances of text
            break
            
        pkg_name = pkg.get("name", "unknown")
        resources = pkg.get("resources", [])
        
        target_res = next((r for r in resources if r.get("format", "").upper() in ["CSV", "XLSX"]), None)
        
        if target_res:
            res_url = target_res.get("download_url") or target_res.get("url")
            res_format = target_res.get("format", "CSV").lower()
            res_name = f"{pkg_name}.{res_format}"
            res_path = os.path.join(RAW_DIR, res_name)
            
            if not os.path.exists(res_path):
                print(f"  [+] Downloading {res_name}...")
                try:
                    r = requests.get(res_url, timeout=60)
                    r.raise_for_status()
                    
                    # Prevent downloading HTML landing pages disguised as datasets
                    if b"<!DOCTYPE html>" in r.content[:100].lower() or b"<html" in r.content[:100].lower():
                        print(f"  [-] {res_name} is an HTML page. Skipping.")
                        continue
                        
                    with open(res_path, "wb") as f:
                        f.write(r.content)
                    downloaded_files.append(res_path)
                except Exception as e:
                    print(f"  [-] Failed to download {res_url}: {e}")
            else:
                print(f"  [*] {res_name} already exists. Skipping download.")
                downloaded_files.append(res_path)
                
    return downloaded_files

def process_corpus(downloaded_files):
    """Loads datasets and extracts text narratives."""
    print("[*] Processing raw HDX datasets into baseline RAG corpus...")
    
    all_texts = []
    # Force openpyxl for xlsx to avoid dependency errors
    import warnings
    warnings.simplefilter(action='ignore', category=UserWarning)
    
    for f in downloaded_files:
        try:
            if f.endswith(".csv"):
                df = pd.read_csv(f, low_memory=False)
            elif f.endswith(".xlsx"):
                df = pd.read_excel(f, engine='openpyxl')
            else:
                continue
                
            # Flatten columns to lowercase for easier matching
            df.columns = [str(c).lower().strip() for c in df.columns]
            
            # Find probable text columns
            text_cols = [c for c in df.columns if any(keyword in c for keyword in ["narrative", "description", "summary", "impact", "severity", "notes", "overview", "details"])]
            country_cols = [c for c in df.columns if "country" in c]
            date_cols = [c for c in df.columns if "date" in c or "year" in c]
            type_cols = [c for c in df.columns if "type" in c or "hazard" in c or "disaster" in c]
            
            # If no obvious text column exists, skip
            if not text_cols:
                print(f"  [-] No text narrative column found in {os.path.basename(f)}")
                continue
                
            text_col = text_cols[0]
            country_col = country_cols[0] if country_cols else None
            date_col = date_cols[0] if date_cols else None
            type_col = type_cols[0] if type_cols else None
            
            # Extract
            count = 0
            for _, row in df.iterrows():
                narrative = str(row.get(text_col, "")).strip()
                if not narrative or narrative.lower() == "nan" or len(narrative) < 20:
                    continue
                    
                entry = {
                    "source_file": os.path.basename(f),
                    "date": str(row[date_col]) if date_col and pd.notna(row[date_col]) else "Unknown",
                    "country": str(row[country_col]) if country_col and pd.notna(row[country_col]) else "Unknown",
                    "disaster_type": str(row[type_col]) if type_col and pd.notna(row[type_col]) else "Unknown",
                    "narrative_text": narrative
                }
                all_texts.append(entry)
                count += 1
            print(f"  [+] Extracted {count} narratives from {os.path.basename(f)}")
                
        except Exception as e:
            print(f"  [-] Error processing {f}: {e}")
            
    if not all_texts:
        print("[-] No rich text narratives could be extracted from datasets.")
        return
        
    master_df = pd.DataFrame(all_texts)
    
    # Drop pure duplicates
    master_df = master_df.drop_duplicates(subset=["narrative_text"])
    
    master_df.to_csv(PROCESSED_FILE, index=False)
    
    print("==================================================")
    print("  FUSION COMPLETE: BASELINE RAG CORPUS READY      ")
    print("==================================================")
    print(f"Total Text Narratives Extracted : {len(master_df):,}")
    print(f"Saved To : {PROCESSED_FILE}")
    print("==================================================")

def main():
    print("==================================================")
    print("  CALAMITY AI: HDX Text Corpus Extraction Node")
    print("==================================================")
    
    packages = search_hdx()
    if not packages:
        print("[-] No packages found in HDX API.")
        return
        
    downloaded_files = download_resources(packages)
    if not downloaded_files:
        print("[-] No CSV/XLSX files could be downloaded.")
        return
        
    process_corpus(downloaded_files)

if __name__ == "__main__":
    main()
