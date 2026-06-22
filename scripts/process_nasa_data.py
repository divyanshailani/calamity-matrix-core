import os
import glob
import json
import pandas as pd

# Configuration
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
RAW_DIR = os.path.join(SCRIPT_DIR, "..", "data", "raw", "nasa_eonet")
PROCESSED_FILE = os.path.join(SCRIPT_DIR, "..", "data", "processed", "global_nasa_master.csv")

def get_coords(geometry_entry):
    """Safely extracts longitude and latitude from Point or Polygon geometries."""
    coords = geometry_entry.get("coordinates")
    if not coords:
        return None, None
        
    # If Point: [lon, lat]
    if isinstance(coords[0], (int, float)):
        return coords[0], coords[1]
        
    # If Polygon / MultiPolygon: Drill down to first pair
    while isinstance(coords, list) and isinstance(coords[0], list):
        coords = coords[0]
        
    if isinstance(coords, list) and len(coords) >= 2 and isinstance(coords[0], (int, float)):
        return coords[0], coords[1]
        
    return None, None

def process_nasa_data():
    print("==================================================")
    print("  CALAMITY AI: NASA EONET Matrix Fusion Node      ")
    print("==================================================")
    
    print("[*] Reading raw JSON chunks...")
    json_files = glob.glob(os.path.join(RAW_DIR, "*.json"))
    
    if not json_files:
        print("[-] No JSON files found in NASA EONET raw directory.")
        return
        
    parsed_events = []
    
    for filepath in json_files:
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                events = json.load(f)
                
            for event in events:
                event_id = event.get("id")
                title = event.get("title")
                
                # Extract primary category
                categories = event.get("categories", [])
                category = categories[0].get("title") if categories else "Unknown"
                
                # Flatten geometry to find start_date, end_date, and coords
                geometry = event.get("geometry", [])
                if not geometry:
                    continue # Skip events with absolutely no spatial data
                    
                dates = []
                for geo in geometry:
                    dt = geo.get("date")
                    if dt:
                        dates.append(dt)
                        
                if not dates:
                    continue
                    
                dates.sort()
                start_date = dates[0]
                end_date = dates[-1]
                
                # Extract coordinates from the first geometry entry (which represents initial location)
                lon, lat = get_coords(geometry[0])
                
                parsed_events.append({
                    "event_id": event_id,
                    "title": title,
                    "category": category,
                    "start_date": start_date,
                    "end_date": end_date,
                    "latitude": lat,
                    "longitude": lon
                })
        except Exception as e:
            print(f"  [-] Error parsing {filepath}: {e}")
            
    print(f"  [+] Loaded {len(parsed_events)} raw event entries.")
    
    if not parsed_events:
        print("[-] No valid events could be parsed.")
        return
        
    print("[*] Applying The Cleaning Matrix...")
    df = pd.DataFrame(parsed_events)
    
    # Drop duplicates
    df = df.drop_duplicates(subset=["event_id"])
    
    # Drop rows without valid coordinates
    df = df.dropna(subset=["latitude", "longitude"])
    
    print("  [+] Converting timestamps to UTC...")
    df['start_date'] = pd.to_datetime(df['start_date'], utc=True)
    df['end_date'] = pd.to_datetime(df['end_date'], utc=True)
    
    print("  [+] Sorting chronologically (oldest to newest)...")
    df = df.sort_values(by='start_date').reset_index(drop=True)
    
    print("[*] Exporting master analytical dataset...")
    df.to_csv(PROCESSED_FILE, index=False)
    
    # Final Summary
    total_unique = len(df)
    min_date = df['start_date'].min().strftime('%Y-%m-%d')
    max_date = df['start_date'].max().strftime('%Y-%m-%d')
    category_counts = df['category'].value_counts()
    
    print("==================================================")
    print("  FUSION COMPLETE: MASTER NASA DATASET READY      ")
    print("==================================================")
    print(f"Total Unique Spatial Events : {total_unique:,}")
    print(f"Chronological Range         : {min_date} to {max_date}")
    print("--------------------------------------------------")
    print("Category Breakdown:")
    for cat, count in category_counts.items():
        print(f"  - {cat}: {count:,}")
    print("==================================================")

if __name__ == "__main__":
    process_nasa_data()
