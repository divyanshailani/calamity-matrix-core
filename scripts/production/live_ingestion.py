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
sys.path.insert(0, os.path.abspath(os.path.join(SCRIPT_DIR, '..', '..')))
from src.config import DATABASE_URL, DB_CONFIG, HF_TOKEN
import scripts.production.retrieval as retrieval

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

def embed_document(text):
    """Embed one narrative for every configured provider.

    Returns {"fireworks": vec|None, "huggingface": vec|None}. Each provider's
    vector goes to its own column — Qwen3 and BGE are different vector spaces,
    so one is never substituted for the other. Both use the canonical client in
    retrieval.py (bounded deadline, no retry on permanent 4xx, strict vector
    validation) instead of the old bespoke request in this file.
    """
    vectors = {"fireworks": None, "huggingface": None}

    if retrieval.FIREWORKS_API_KEY:
        vec, info = retrieval.embed_documents_fireworks([text], timeout=60)
        if vec:
            vectors["fireworks"] = vec[0]
        else:
            print(f"[-] Fireworks embedding failed: {info}")

    if HF_TOKEN:
        vec, info = retrieval._hf_embed(retrieval.INSTRUCTION_PREFIX + text, timeout=30)
        if vec:
            vectors["huggingface"] = vec
        else:
            print(f"[-] HF embedding failed: {info}")

    return vectors

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
            "semantic_query": f"{disaster} in {country} (Year: {event_year}). Additional Context: {narrative_text[:2000]}",
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
        try:
            if isinstance(coords, list) and len(coords) >= 2:
                if isinstance(coords[0], list): # Polygon
                    lng, lat = coords[0][0][0], coords[0][0][1]
                else: # Point
                    lng, lat = coords[0], coords[1]
            else:
                lat, lng = None, None
        except (IndexError, TypeError):
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
    skipped_no_vector = 0
    
    print(f"[*] Fetched {len(all_raw_records)} total records from APIs.")
    
    for rec in all_raw_records:
        if rec["unique_id"] in existing_ids:
            continue

        vectors = embed_document(rec["semantic_query"])
        fw_vec = vectors["fireworks"]
        hf_vec = vectors["huggingface"]

        # A row is worth keeping if at least one provider produced a vector; the
        # other column stays NULL until a backfill fills it. FTS/lexical
        # retrieval still works for rows with a missing vector.
        if fw_vec is None and hf_vec is None:
            skipped_no_vector += 1
            continue

        records_to_insert.append((
            rec["date"],
            rec["country"],
            rec["disaster_type"],
            rec["narrative_text"],
            rec["event_year"],
            rec["lat"],
            rec["lng"],
            hf_vec,      # embedding      (BGE space)
            hf_vec,      # embedding_v2   (BGE space)
            fw_vec,      # embedding_fireworks (Qwen3 space)
            rec["unique_id"]
        ))
        providers = ",".join(p for p, v in (("fw", fw_vec), ("hf", hf_vec)) if v)
        print(f"  [+] Embedded NEW report: {rec['unique_id']} [{providers}]")

    if skipped_no_vector:
        print(f"[!] {skipped_no_vector} record(s) skipped: no provider produced a vector.")

    if not records_to_insert:
        print("[!] No new records to insert. Entropy stabilized.")
        conn.close()
        return
        
    # Database Armor: ON CONFLICT DO NOTHING
    print(f"[*] Injecting {len(records_to_insert)} new vectors into Matrix...")
    try:
        cur = conn.cursor()
        
        insert_query = """
            INSERT INTO disaster_narratives (date, country, disaster_type, narrative_text, event_year, lat, lng, embedding, embedding_v2, embedding_fireworks, unique_id)
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
