import os
import pandas as pd
import numpy as np

# Configuration
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROCESSED_DIR = os.path.join(SCRIPT_DIR, "..", "data", "processed")

def build_tectonic_matrix():
    print("[*] Building Tectonic Matrix (USGS + Smithsonian)...")
    df_seismic = pd.read_csv(os.path.join(PROCESSED_DIR, "global_seismic_master.csv"))
    df_volcano = pd.read_csv(os.path.join(PROCESSED_DIR, "global_volcano_master.csv"))
    
    # Standardize seismic
    df_seismic['date'] = pd.to_datetime(df_seismic['time'], utc=True, format='mixed')
    df_seismic['event_type'] = 'earthquake'
    df_seismic['severity'] = df_seismic['mag']  # Magnitude
    
    # Standardize volcano
    df_volcano['date'] = pd.to_datetime(df_volcano['start_date'], utc=True)
    df_volcano['event_type'] = 'volcano'
    df_volcano['severity'] = df_volcano['vei']  # VEI
    
    # Select common structural columns
    cols_s = ['date', 'latitude', 'longitude', 'event_type', 'severity', 'depth']
    cols_v = ['date', 'latitude', 'longitude', 'event_type', 'severity']
    
    df_s = df_seismic[cols_s].copy()
    df_v = df_volcano[cols_v].copy()
    df_v['depth'] = np.nan # Volcanoes don't have a focal depth in this dataset
    
    # Merge and sort
    df_tectonic = pd.concat([df_s, df_v], ignore_index=True)
    df_tectonic = df_tectonic.sort_values('date').reset_index(drop=True)
    
    # Grid Clustering (5x5 degree bins)
    df_tectonic['grid_lat'] = (df_tectonic['latitude'] / 5).round() * 5
    df_tectonic['grid_lon'] = (df_tectonic['longitude'] / 5).round() * 5
    
    # Output
    out_path = os.path.join(PROCESSED_DIR, "tectonic_matrix.csv")
    df_tectonic.to_csv(out_path, index=False)
    print(f"  [+] Tectonic Matrix saved to {out_path} ({len(df_tectonic)} rows)")

def build_atmospheric_impact_matrix():
    print("[*] Building Atmospheric Impact Matrix (NASA + EM-DAT)...")
    df_nasa = pd.read_csv(os.path.join(PROCESSED_DIR, "global_nasa_master.csv"))
    df_emdat = pd.read_csv(os.path.join(PROCESSED_DIR, "global_emdat_master.csv"))
    
    # Extract Year/Month from NASA
    df_nasa['start_date'] = pd.to_datetime(df_nasa['start_date'], utc=True, format='mixed')
    df_nasa['year'] = df_nasa['start_date'].dt.year
    df_nasa['month'] = df_nasa['start_date'].dt.month
    
    # Ensure Year/Month in EM-DAT
    df_emdat['year'] = df_emdat['Start Year']
    df_emdat['month'] = df_emdat['Start Month']
    
    # We drop rows without year/month to allow a clean join
    df_emdat = df_emdat.dropna(subset=['year', 'month'])
    df_nasa = df_nasa.dropna(subset=['year', 'month'])
    
    # Map EM-DAT disaster type to NASA Category to prevent Cartesian explosion
    def map_to_nasa_category(disaster_type):
        dt_lower = str(disaster_type).lower()
        if 'wildfire' in dt_lower or 'fire' in dt_lower:
            return 'Wildfires'
        elif 'storm' in dt_lower or 'cyclone' in dt_lower or 'hurricane' in dt_lower or 'typhoon' in dt_lower:
            return 'Severe Storms'
        elif 'volcan' in dt_lower:
            return 'Volcanoes'
        elif 'earthquake' in dt_lower:
            return 'Earthquakes'
        elif 'flood' in dt_lower:
            return 'Floods'
        elif 'extreme temperature' in dt_lower:
            return 'Extreme temperature' # NASA may not have this, but helps bound the join
        return 'Unknown'
        
    df_emdat['category'] = df_emdat['Disaster Type'].apply(map_to_nasa_category)
    
    # Spatial Temporal Join on Year + Month + Category
    # Note: We aggregate NASA events by year/month/category first to ensure 1:1 or N:1 clean joins.
    
    nasa_agg = df_nasa.groupby(['year', 'month', 'category']).agg(
        nasa_events_count=('event_id', 'count'),
        avg_lat=('latitude', 'mean'),
        avg_lon=('longitude', 'mean')
    ).reset_index()
    
    df_impact = pd.merge(df_emdat, nasa_agg, on=['year', 'month', 'category'], how='left')
    
    # Output
    out_path = os.path.join(PROCESSED_DIR, "atmospheric_impact_matrix.csv")
    df_impact.to_csv(out_path, index=False)
    print(f"  [+] Atmospheric Impact Matrix saved to {out_path} ({len(df_impact)} rows)")

if __name__ == "__main__":
    print("==================================================")
    print("  CALAMITY AI: Matrix Partitioning Node           ")
    print("==================================================")
    build_tectonic_matrix()
    build_atmospheric_impact_matrix()
    print("==================================================")
