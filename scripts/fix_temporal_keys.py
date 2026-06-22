import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from src.config import DB_CONFIG

import psycopg2
import pandas as pd
import os
import re
from collections import Counter
from psycopg2.extras import execute_batch

DB_PARAMS = DB_CONFIG

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
ATMOSPHERIC_CSV = os.path.join(SCRIPT_DIR, "..", "data", "processed", "atmospheric_impact_matrix.csv")

def extract_year_regex(text):
    if not isinstance(text, str) or not text:
        return None
    matches = re.findall(r'\b(19\d{2}|20\d{2})\b', text)
    if matches:
        # Return the most frequently mentioned year in the text
        return int(Counter(matches).most_common(1)[0][0])
    return None

def fix_temporal_keys():
    print("==================================================")
    print("  CALAMITY AI: Temporal Key Rectification         ")
    print("==================================================")
    
    # 1. DB Schema Update
    print("[*] Connecting to database and adding 'event_year' column...")
    try:
        conn = psycopg2.connect(**DB_PARAMS)
        cur = conn.cursor()
    except Exception as e:
        print(f"[-] Database connection failed: {e}")
        return
        
    cur.execute("ALTER TABLE disaster_narratives ADD COLUMN IF NOT EXISTS event_year INTEGER;")
    conn.commit()
    
    # Load DB Records
    cur.execute("SELECT id, country, disaster_type, narrative_text FROM disaster_narratives;")
    db_records = cur.fetchall()
    df_db = pd.DataFrame(db_records, columns=['id', 'country', 'disaster_type', 'narrative_text'])
    
    # 2. Load EM-DAT / Atmospheric Impact Matrix
    print("[*] Loading Atmospheric Impact Matrix for fuzzy join...")
    df_emdat = pd.read_csv(ATMOSPHERIC_CSV)
    
    # Prepare lowercase columns for fuzzy matching
    if 'Country' in df_emdat.columns:
        df_emdat['country_lower'] = df_emdat['Country'].astype(str).str.lower()
    else:
        df_emdat['country_lower'] = ""
        
    if 'Disaster Type' in df_emdat.columns:
        df_emdat['type_lower'] = df_emdat['Disaster Type'].astype(str).str.lower()
    else:
        df_emdat['type_lower'] = ""
        
    # Standardize the year column name based on previous extractions
    year_col = 'Start Year' if 'Start Year' in df_emdat.columns else 'year'
    
    print("[*] Cross-referencing narratives against EM-DAT ground-truth and running Regex Fallback...")
    
    emdat_matches = 0
    regex_matches = 0
    unmatched = 0
    updates = []
    
    for idx, row in df_db.iterrows():
        db_id = row['id']
        c = str(row['country']).lower()
        t = str(row['disaster_type']).lower()
        text = str(row['narrative_text'])
        
        assigned_year = None
        
        # Try Fuzzy Join if the country field is an actual text string (not an API URL or numeric ID)
        if len(c) > 3 and not c.startswith('http'):
            # Simple substring match for country and disaster type
            match = df_emdat[
                (df_emdat['country_lower'].str.contains(c, regex=False, na=False)) & 
                (df_emdat['type_lower'].str.contains(t, regex=False, na=False))
            ]
            
            if not match.empty and year_col in match.columns:
                mode_year = match[year_col].mode()
                if not mode_year.empty:
                    assigned_year = int(mode_year.iloc[0])
                    emdat_matches += 1
                        
        # 3. Regex Fallback
        if assigned_year is None:
            assigned_year = extract_year_regex(text)
            if assigned_year is not None:
                regex_matches += 1
            else:
                unmatched += 1
                
        if assigned_year is not None:
            updates.append((assigned_year, db_id))
            
    # 4. Update DB
    print(f"[*] Committing {len(updates)} rectified temporal keys to PostgreSQL...")
    update_query = "UPDATE disaster_narratives SET event_year = %s WHERE id = %s"
    execute_batch(cur, update_query, updates)
    conn.commit()
    
    print("\n==================================================")
    print("  RECTIFICATION SUMMARY                           ")
    print("==================================================")
    print(f"  Total Records Processed : {len(df_db)}")
    print(f"  EM-DAT Matrix Matches   : {emdat_matches}")
    print(f"  Regex Fallback Matches  : {regex_matches}")
    print(f"  Unmatched (No Year)     : {unmatched}")
    print("==================================================")
    
    cur.close()
    conn.close()

if __name__ == "__main__":
    fix_temporal_keys()
