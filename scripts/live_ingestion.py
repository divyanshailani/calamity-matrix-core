import os
import sys
import json
import requests
from datetime import datetime
import psycopg2
from psycopg2.extras import execute_values

# Config
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.abspath(os.path.join(SCRIPT_DIR, '..')))
from src.config import DATABASE_URL, DB_CONFIG, HF_TOKEN

def embed_text(text):
    if not HF_TOKEN:
        print("[!] Missing HF_TOKEN, cannot embed.")
        return None
        
    hf_api_url = "https://router.huggingface.co/hf-inference/models/BAAI/bge-large-en-v1.5"
    headers = {"Authorization": f"Bearer {HF_TOKEN}"}
    
    instruction = "Represent this sentence for searching relevant passages: "
    full_query = instruction + text
    
    try:
        resp = requests.post(hf_api_url, headers=headers, json={"inputs": full_query, "options": {"wait_for_model": True}})
        if resp.status_code == 200:
            embed_result = resp.json()
            if isinstance(embed_result, list) and len(embed_result) > 0 and isinstance(embed_result[0], list):
                embed_result = embed_result[0]
            
            # Normalize
            import numpy as np
            vec = np.array(embed_result, dtype=float)
            norm = np.linalg.norm(vec)
            if norm > 0:
                vec = vec / norm
            return vec.tolist()
        else:
            print(f"[-] HF API Error: {resp.text}")
    except Exception as e:
        print(f"[-] Request failed: {e}")
    return None

def main():
    print("[*] Starting Calamity Matrix Autonomous Crawler...")
    
    # 1. Fetch ReliefWeb Reports (Last 7 Days)
    url = "https://api.reliefweb.int/v1/reports"
    params = {
        "appname": "calamity-matrix",
        "profile": "full",
        "preset": "latest",
        "limit": 50,
        "query[value]": "date.created:>now-7d"
    }
    
    response = requests.get(url, params=params)
    if response.status_code != 200:
        print("[-] ReliefWeb API request failed.")
        return
        
    data = response.json()
    records_to_insert = []
    
    for item in data.get("data", []):
        fields = item.get("fields", {})
        
        # Extract data
        title = fields.get("title", "")
        body = fields.get("body", "")
        date_created = fields.get("date", {}).get("created", "")
        
        if not body:
            continue
            
        # Parse Country
        countries = fields.get("primary_country", [])
        country = countries[0].get("name") if countries else "Unknown"
        
        # Parse Disaster Type
        disaster_types = fields.get("disaster_type", [])
        disaster = disaster_types[0].get("name") if disaster_types else "Unknown"
        
        event_year = None
        if date_created:
            try:
                event_year = int(date_created[:4])
            except ValueError:
                event_year = datetime.now().year
                
        # Clean Body Text (Preview)
        narrative_text = f"Title: {title}\n\n{body}"
        if len(narrative_text) > 4000:
            narrative_text = narrative_text[:4000] + "..."
            
        # Generate Vector
        semantic_query = f"{disaster} in {country} (Year: {event_year}). Additional Context: {narrative_text[:500]}"
        embedding = embed_text(semantic_query)
        
        if embedding:
            records_to_insert.append((
                date_created[:10], # date
                country,
                disaster,
                narrative_text,
                event_year,
                None, # lat
                None, # lng
                embedding
            ))
            print(f"  [+] Embedded report: {title[:50]}...")
            
    if not records_to_insert:
        print("[!] No valid records to insert.")
        return
        
    # 2. Insert into PostgreSQL
    print(f"[*] Inserting {len(records_to_insert)} records into Database...")
    try:
        if DATABASE_URL:
            conn = psycopg2.connect(DATABASE_URL)
        else:
            conn = psycopg2.connect(**DB_CONFIG)
            
        cur = conn.cursor()
        
        # Insert without conflict handling if no unique constraint, assuming low volume
        insert_query = """
            INSERT INTO disaster_narratives (date, country, disaster_type, narrative_text, event_year, lat, lng, embedding)
            VALUES %s
        """
        execute_values(cur, insert_query, records_to_insert)
        conn.commit()
        
        cur.close()
        conn.close()
        print("[+] Ingestion Complete.")
    except Exception as e:
        print(f"[-] Database insertion failed: {e}")

if __name__ == "__main__":
    main()
