import psycopg2
import spacy
from collections import Counter
import re
import os

import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from src.config import DB_CONFIG as DB_PARAMS

def extract_temporal_nlp():
    print("==================================================")
    print("  CALAMITY AI: NLP Temporal Extraction (spaCy)    ")
    print("==================================================")
    
    # Load spaCy model
    print("[*] Loading en_core_web_sm NLP model...")
    nlp = spacy.load("en_core_web_sm")
    
    print("[*] Connecting to calamity_rag database...")
    conn = psycopg2.connect(**DB_PARAMS)
    cur = conn.cursor()
    
    # Fetch all rows to evaluate
    cur.execute("SELECT id, narrative_text, event_year FROM disaster_narratives;")
    rows = cur.fetchall()
    
    total_rows = len(rows)
    updated_count = 0
    failed_count = 0
    
    print(f"[*] Processing {total_rows} disaster narratives for temporal anomalies...")
    
    for row_id, text, current_year in rows:
        if not text:
            failed_count += 1
            continue
            
        doc = nlp(text)
        candidate_years = []
        
        # Extract DATE entities
        for ent in doc.ents:
            if ent.label_ == "DATE":
                # Strict 4-digit years bounded between 2000 and 2026
                matches = re.findall(r'\b(200[0-9]|201[0-9]|202[0-6])\b', ent.text)
                candidate_years.extend(matches)
                
        if candidate_years:
            # Pick the most frequent valid year in grammatical date contexts
            best_year = int(Counter(candidate_years).most_common(1)[0][0])
            
            # Update if it differs from what's in the DB or if current_year is None
            if current_year is None or best_year != int(current_year):
                cur.execute("UPDATE disaster_narratives SET event_year = %s WHERE id = %s", (best_year, row_id))
                updated_count += 1
        else:
            # Fallback if no valid date found in the grammatical 'DATE' entities
            failed_count += 1
            
    conn.commit()
    cur.close()
    conn.close()
    
    print("\n==================================================")
    print(f"  [+] NLP Extraction Complete.")
    print(f"    - Records Evaluated: {total_rows}")
    print(f"    - Temporal Keys Updated/Fixed: {updated_count}")
    print(f"    - No Valid Dates Found (Kept As-Is): {failed_count}")
    print("==================================================")

if __name__ == "__main__":
    extract_temporal_nlp()
