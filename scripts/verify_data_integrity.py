import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from src.config import DB_CONFIG

import psycopg2

DB_PARAMS = DB_CONFIG

def verify_integrity():
    print("==================================================")
    print("  CALAMITY AI: Data Integrity Post-Mortem         ")
    print("==================================================")
    
    try:
        conn = psycopg2.connect(**DB_PARAMS)
        cur = conn.cursor()
    except Exception as e:
        print(f"[-] Database connection failed: {e}")
        return

    print("\n[*] 1. The Boundary Test (Chronological Range):")
    cur.execute("SELECT COUNT(*), MIN(date), MAX(date) FROM disaster_narratives;")
    count, min_date, max_date = cur.fetchone()
    print(f"    Total Documents : {count}")
    print(f"    Oldest Record   : {min_date}")
    print(f"    Newest Record   : {max_date}")
    
    print("\n[*] 2. The Anomaly Extraction (Irian Jaya):")
    cur.execute("SELECT date, country, disaster_type, narrative_text FROM disaster_narratives WHERE narrative_text ILIKE '%Irian Jaya%' LIMIT 3;")
    results = cur.fetchall()
    
    for i, row in enumerate(results, 1):
        date, country, dtype, text = row
        print(f"\n  [Anomaly #{i}]")
        print(f"    Date    : {date}")
        print(f"    Country : {country}")
        print(f"    Type    : {dtype}")
        print(f"    Preview : {text[:400].replace(chr(10), ' ')}...")

    cur.close()
    conn.close()
    print("\n==================================================")

if __name__ == "__main__":
    verify_integrity()
