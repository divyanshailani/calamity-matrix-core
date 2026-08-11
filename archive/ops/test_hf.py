import requests
import json
import time

hf_api_url = "https://router.huggingface.co/hf-inference/models/BAAI/bge-large-en-v1.5"
headers = {}
full_query = "Test query"

def fetch_hf():
    from requests.adapters import HTTPAdapter
    from urllib3.util.retry import Retry
    session = requests.Session()
    retries = Retry(total=3, backoff_factor=1, status_forcelist=[500, 502, 503, 504])
    session.mount('https://', HTTPAdapter(max_retries=retries))
    
    try:
        print("[DEBUG] Hitting HF API with urllib3.Retry...")
        resp = session.post(hf_api_url, headers=headers, json={"inputs": full_query, "options": {"wait_for_model": True}}, timeout=120)
        resp.raise_for_status()
        return resp.json()
    except requests.exceptions.Timeout:
        raise Exception("Hugging Face API timed out after 120s. Model may be fully cold.")
    except requests.exceptions.RequestException as e:
        raise Exception(f"Hugging Face API Request failed: {e}")

fetch_hf()
