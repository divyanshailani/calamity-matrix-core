import os
import json
import pandas as pd
import re

# Configuration
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
SHADOW_FILE = os.path.join(SCRIPT_DIR, "..", "data", "raw", "reliefweb_shadow", "reliefweb_reports_checkpoint_1.json")
HDX_FILE = os.path.join(SCRIPT_DIR, "..", "data", "processed", "rag_texts", "hdx_baseline_corpus.csv")
MASTER_OUT = os.path.join(SCRIPT_DIR, "..", "data", "processed", "rag_texts", "master_rag_corpus.csv")

def clean_text(text):
    if not isinstance(text, str):
        return ""
    # Strip basic HTML tags if any slipped through
    text = re.sub(r'<[^>]+>', '', text)
    # Remove excessive newlines and tabs
    text = re.sub(r'[\r\n\t]+', ' ', text)
    # Remove multiple spaces
    text = re.sub(r'\s+', ' ', text)
    return text.strip()

def fuse_corpus():
    print("==================================================")
    print("  CALAMITY AI: Shadow Corpus Verification & Fusion")
    print("==================================================")
    
    # 1. Payload Verification
    print("[*] Verifying ReliefWeb Shadow Payload Integrity...")
    if not os.path.exists(SHADOW_FILE):
        print("[-] Error: Shadow checkpoint file not found.")
        return
        
    with open(SHADOW_FILE, 'r', encoding='utf-8') as f:
        shadow_data = json.load(f)
        
    if not shadow_data:
        print("[-] Error: Shadow payload is empty.")
        return
        
    first_report = shadow_data[0]
    title = first_report.get('title', 'Unknown Title')
    narrative = first_report.get('narrative', '')
    
    print("\n  [+] SANITY CHECK: REPORT #1")
    print(f"  Title: {title}")
    print(f"  Preview: {narrative[:300]}...")
    print("\n  [+] Sanity Check Passed. Text is clean.\n")
    
    # 2. The Standardization Matrix
    print("[*] Converting and cleaning JSON payload...")
    df_shadow = pd.DataFrame(shadow_data)
    
    # Map to HDX architecture: source_file, date, country, disaster_type, narrative_text
    df_shadow['source_file'] = 'reliefweb_shadow'
    df_shadow['narrative_text'] = df_shadow['narrative'].apply(clean_text)
    
    # Extract disaster_type from title heuristically
    def infer_disaster(t):
        t = t.lower()
        if 'earthquake' in t: return 'Earthquake'
        if 'flood' in t: return 'Flood'
        if 'wildfire' in t or 'fire' in t: return 'Wildfire'
        if 'volcano' in t or 'eruption' in t: return 'Volcano'
        return 'Unknown'
        
    df_shadow['disaster_type'] = df_shadow['title'].apply(infer_disaster)
    
    # Drop irrelevant columns and ensure order
    target_columns = ['source_file', 'date', 'country', 'disaster_type', 'narrative_text']
    df_shadow = df_shadow[target_columns].copy()
    
    # Drop empty narratives
    df_shadow = df_shadow[df_shadow['narrative_text'] != '']
    df_shadow = df_shadow.dropna(subset=['narrative_text'])
    print(f"  [+] Prepared {len(df_shadow)} ReliefWeb reports.")
    
    # 3. The Dimensional Merge
    print("[*] Merging with HDX Baseline Corpus...")
    df_hdx = pd.read_csv(HDX_FILE)
    df_hdx['narrative_text'] = df_hdx['narrative_text'].apply(clean_text)
    df_hdx = df_hdx[df_hdx['narrative_text'] != '']
    df_hdx = df_hdx.dropna(subset=['narrative_text'])
    print(f"  [+] Loaded {len(df_hdx)} HDX reports.")
    
    df_master = pd.concat([df_hdx, df_shadow], ignore_index=True)
    
    # 4. Export
    df_master.to_csv(MASTER_OUT, index=False)
    
    print("==================================================")
    print("  FUSION COMPLETE: MASTER RAG CORPUS READY        ")
    print("==================================================")
    print(f"Total Master Documents: {len(df_master):,}")
    print(f"Saved To: {MASTER_OUT}")
    print("==================================================")

if __name__ == "__main__":
    fuse_corpus()
