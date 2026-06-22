import requests
import psycopg2
from src.config import DB_CONFIG

def main():
    conn = psycopg2.connect(**DB_CONFIG)
    cur = conn.cursor()
    cur.execute('SELECT DISTINCT country, disaster_type FROM disaster_narratives')
    rows = cur.fetchall()
    
    # We will just test a unique list of countries
    # To save time and not spam the API, we will just pick 1 disaster per country
    countries = {}
    for country, disaster_type in rows:
        if country not in countries:
            countries[country] = disaster_type
            
    print(f"Testing {len(countries)} unique regions...")
    
    results = []
    
    for country, disaster in countries.items():
        payload = {
            "query_text": f"{disaster} in {country}",
            "country": country,
            "disaster_type": disaster,
            "month": 1,
            "event_year": 2026,
            "severity": 5.0
        }
        
        try:
            res = requests.post("http://localhost:8000/api/v1/simulate_calamity", json=payload, timeout=10)
            if res.status_code == 200:
                data = res.json()
                if "historical_context" in data and len(data["historical_context"]) > 0:
                    status = "SUCCESS (Has Data)"
                else:
                    status = "SUCCESS (Empty Data)"
            else:
                status = f"ERROR {res.status_code}: {res.text[:100]}"
        except Exception as e:
            status = f"EXCEPTION: {str(e)}"
            
        results.append((country, disaster, status))
        print(f"{country} - {status}")

    with open("test_results.txt", "w") as f:
        for c, d, s in results:
            f.write(f"{c}|{d}|{s}\n")

if __name__ == '__main__':
    main()
