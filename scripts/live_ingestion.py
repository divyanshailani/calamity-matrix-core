import os
import sys
import json
import requests
import hashlib
from datetime import datetime, timedelta
import psycopg2
from psycopg2.extras import execute_values

# Config
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.abspath(os.path.join(SCRIPT_DIR, '..')))
from src.config import DATABASE_URL, DB_CONFIG, HF_TOKEN

def get_db_connection():
    if DATABASE_URL:
        return psycopg2.connect(DATABASE_URL)
    return psycopg2.connect(**DB_CONFIG)

def fetch_existing_ids(conn):
    """The Pre-Fetch Shield: Get all unique_ids from the last 14 days to prevent duplicate embedding compute."""
    print("[*] Engaging Pre-Fetch Shield (Querying existing DB records)...")
    cur = conn.cursor()
    # Fetching slightly more than 7 days to be safe
    query = "SELECT COALESCE(unique_id, id::text) FROM disaster_narratives WHERE event_year >= %s"
    cur.execute(query, (datetime.now().year - 1,))
    existing_ids = {row[0] for row in cur.fetchall()}
    cur.close()
    print(f"  [+] Shield loaded {len(existing_ids)} existing recent unique IDs.")
    return existing_ids

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

def generate_hash(text):
    return hashlib.md5(text.encode('utf-8')).hexdigest()

def fetch_reliefweb():
    print("[*] Fetching ReliefWeb Reports (Last 7 Days)...")
    url = "https://api.reliefweb.int/v1/reports"
    params = {
        "appname": "calamity-matrix",
        "profile": "full",
        "preset": "latest",
        "limit": 50,
        "query[value]": "date.created:>now-7d"
    }
    
    try:
        response = requests.get(url, params=params)
    except Exception as e:
        print(f"[-] ReliefWeb request failed: {e}")
        return []
        
    if response.status_code != 200:
        print("[-] ReliefWeb API request failed.")
        return []
        
    data = response.json()
    records = []
    
    for item in data.get("data", []):
        fields = item.get("fields", {})
        title = fields.get("title", "")
        body = fields.get("body", "")
        date_created = fields.get("date", {}).get("created", "")
        
        if not body:
            continue
            
        countries = fields.get("primary_country", [])
        country = countries[0].get("name") if countries else "Unknown"
        
        disaster_types = fields.get("disaster_type", [])
        disaster = disaster_types[0].get("name") if disaster_types else "Unknown"
        
        event_year = int(date_created[:4]) if date_created else datetime.now().year
            
        narrative_text = f"Title: {title}\n\n{body}"
        if len(narrative_text) > 4000:
            narrative_text = narrative_text[:4000] + "..."
            
        unique_id = f"rw_{item.get('id', generate_hash(title))}"
        
        records.append({
            "unique_id": unique_id,
            "date": date_created[:10] if date_created else None,
            "country": country,
            "disaster_type": disaster,
            "narrative_text": narrative_text,
            "semantic_query": f"{disaster} in {country} (Year: {event_year}). Additional Context: {narrative_text[:500]}",
            "event_year": event_year,
            "lat": None,
            "lng": None
        })
    return records

def fetch_usgs():
    print("[*] Fetching USGS Earthquakes (Last 7 Days, Mag >= 5.0)...")
    url = "https://earthquake.usgs.gov/fdsnws/event/1/query"
    end_time = datetime.now()
    start_time = end_time - timedelta(days=7)
    
    params = {
        "format": "geojson",
        "starttime": start_time.strftime("%Y-%m-%dT%H:%M:%S"),
        "endtime": end_time.strftime("%Y-%m-%dT%H:%M:%S"),
        "minmagnitude": 5.0
    }
    
    try:
        response = requests.get(url, params=params)
    except Exception as e:
        print(f"[-] USGS request failed: {e}")
        return []
        
    if response.status_code != 200:
        print("[-] USGS API request failed.")
        return []
        
    data = response.json()
    records = []
    
    for feature in data.get("features", []):
        props = feature.get("properties", {})
        geom = feature.get("geometry", {})
        
        mag = props.get("mag")
        place = props.get("place", "Unknown Location")
        time_ms = props.get("time")
        event_id = feature.get("id")
        
        coords = geom.get("coordinates", [None, None, None])
        lng = coords[0] if len(coords) > 0 else None
        lat = coords[1] if len(coords) > 1 else None
        depth = coords[2] if len(coords) > 2 else "Unknown"
        
        if not time_ms:
            continue
            
        date_obj = datetime.fromtimestamp(time_ms / 1000.0)
        date_str = date_obj.strftime("%Y-%m-%d")
        event_year = date_obj.year
        
        # Objective situation report formatting
        narrative_text = f"A Magnitude {mag} earthquake occurred in {place} at a depth of {depth} km."
        unique_id = f"usgs_{event_id}"
        
        records.append({
            "unique_id": unique_id,
            "date": date_str,
            "country": place.split(", ")[-1] if ", " in place else place,
            "disaster_type": "Earthquake",
            "narrative_text": narrative_text,
            "semantic_query": f"Earthquake in {place} (Year: {event_year}). Additional Context: {narrative_text}",
            "event_year": event_year,
            "lat": lat,
            "lng": lng
        })
    return records

def fetch_nasa_eonet():
    print("[*] Fetching NASA EONET Events (Last 7 Days)...")
    url = "https://eonet.gsfc.nasa.gov/api/v3/events"
    params = {
        "days": 7,
        "status": "all",
        "category": "wildfires,severeStorms,floods,volcanoes"
    }
    
    try:
        response = requests.get(url, params=params)
    except Exception as e:
        print(f"[-] NASA request failed: {e}")
        return []
        
    if response.status_code != 200:
        print("[-] NASA EONET API request failed.")
        return []
        
    data = response.json()
    records = []
    
    for event in data.get("events", []):
        title = event.get("title", "")
        event_id = event.get("id", "")
        
        categories = event.get("categories", [])
        category_name = categories[0].get("title") if categories else "Unknown Natural Event"
        
        geometry = event.get("geometry", [])
        if not geometry:
            continue
            
        latest_geom = geometry[-1]
        date_str = latest_geom.get("date", "")[:10]
        event_year = int(date_str[:4]) if date_str else datetime.now().year
        
        coords = latest_geom.get("coordinates", [])
        if isinstance(coords, list) and len(coords) >= 2:
            if isinstance(coords[0], list): # Polygon
                lng, lat = coords[0][0][0], coords[0][0][1]
            else: # Point
                lng, lat = coords[0], coords[1]
        else:
            lat, lng = None, None
            
        narrative_text = f"A {category_name} event titled '{title}' was recorded on {date_str}."
        unique_id = f"nasa_{event_id}"
        
        records.append({
            "unique_id": unique_id,
            "date": date_str,
            "country": "Unknown",
            "disaster_type": category_name,
            "narrative_text": narrative_text,
            "semantic_query": f"{category_name} (Year: {event_year}). Additional Context: {title}",
            "event_year": event_year,
            "lat": lat,
            "lng": lng
        })
    return records

def main():
    print("==================================================")
    print("  CALAMITY AI: Autonomous Tri-API Crawler")
    print("==================================================")
    
    try:
        conn = get_db_connection()
    except Exception as e:
        print(f"[-] Database connection failed: {e}")
        return
        
    existing_ids = fetch_existing_ids(conn)
    
    all_raw_records = []
    all_raw_records.extend(fetch_reliefweb())
    all_raw_records.extend(fetch_usgs())
    all_raw_records.extend(fetch_nasa_eonet())
    
    records_to_insert = []
    
    print(f"[*] Fetched {len(all_raw_records)} total records from APIs.")
    
    for rec in all_raw_records:
        if rec["unique_id"] in existing_ids:
            continue
            
        embedding = embed_text(rec["semantic_query"])
        if embedding:
            records_to_insert.append((
                rec["date"],
                rec["country"],
                rec["disaster_type"],
                rec["narrative_text"],
                rec["event_year"],
                rec["lat"],
                rec["lng"],
                embedding,
                rec["unique_id"]
            ))
            print(f"  [+] Embedded NEW report: {rec['unique_id']}")
            
    if not records_to_insert:
        print("[!] No new records to insert. Entropy stabilized.")
        conn.close()
        return
        
    # Database Armor: ON CONFLICT DO NOTHING
    print(f"[*] Injecting {len(records_to_insert)} new vectors into Matrix...")
    try:
        cur = conn.cursor()
        
        insert_query = """
            INSERT INTO disaster_narratives (date, country, disaster_type, narrative_text, event_year, lat, lng, embedding, unique_id)
            VALUES %s
            ON CONFLICT (unique_id) DO NOTHING
        """
        execute_values(cur, insert_query, records_to_insert)
        conn.commit()
        
        cur.close()
        print("[+] Injection Complete & Matrix Secured.")
    except Exception as e:
        print(f"[-] Database insertion failed: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    main()
