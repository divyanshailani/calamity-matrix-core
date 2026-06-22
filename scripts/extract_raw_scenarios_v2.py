"""
Calamity AI — Phase 18.1: Zero-Cost Training Data Extractor (v2)
"""
import os
import sys
import json
import random
import re
from datetime import datetime

import numpy as np
import pandas as pd
import psycopg2
import xgboost as xgb
from sentence_transformers import SentenceTransformer

# ── Path bootstrap ────────────────────────────────────────────────────────────
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR   = os.path.abspath(os.path.join(SCRIPT_DIR, ".."))
sys.path.insert(0, ROOT_DIR)
from src.config import DB_CONFIG

MODEL_DIR   = os.path.join(ROOT_DIR, "models")
OUTPUT_PATH = os.path.join(ROOT_DIR, "raw_training_prompts_v2.md")

# ── Constants ─────────────────────────────────────────────────────────────────
TARGET_SCENARIOS = 50
RANDOM_SEED      = 42

# EM-DAT → ReliefWeb taxonomy bridge
TAXONOMY_BRIDGE = {
    "extreme temperature": ["Heat Wave", "Cold Wave", "Extreme temperature"],
    "storm":               ["Storm", "Storm Surge", "Tropical Cyclone", "Extratropical Cyclone", "Severe Local Storm"],
    "mass movement (wet)": ["Mud Slide", "Land Slide", "Mass movement (wet)"],
    "volcanic activity":   ["Volcano", "Volcanic activity"],
    "wildfire":            ["Wild Fire", "Fire", "Wildfire"],
}

# Severity heuristics: realistic median severities per disaster type
SEVERITY_MAP = {
    "Earthquake":            6.2,
    "Flood":                 5.0,
    "Drought":               4.5,
    "Epidemic":              5.5,
    "Storm":                 5.8,
    "Tropical Cyclone":      6.5,
    "Hurricane":             6.8,
    "Volcano":               5.0,
    "Wildfire":              4.2,
    "Wild Fire":             4.2,
    "Fire":                  4.2,
    "Land Slide":            4.5,
    "Mud Slide":             4.0,
    "Tsunami":               7.5,
    "Cold Wave":             4.0,
    "Heat Wave":             4.5,
    "Flash Flood":           5.2,
    "Extratropical Cyclone": 5.5,
    "Severe Local Storm":    5.0,
    "Snow Avalanche":        4.0,
    "Storm Surge":           5.5,
    "Insect Infestation":    3.5,
    "Technological Disaster":4.0,
    "Other":                 4.0,
}
DEFAULT_SEVERITY = 5.0

# ── Model Loader ─────────────────────────────────────────────────────────────
def _slug(disaster_type: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", disaster_type.lower()).strip("_")

def load_math_engine() -> dict:
    cache = {}
    for suffix, key in [("xgb_log_affected", "universal_affected"),
                        ("xgb_log_damage",   "universal_damage")]:
        path = os.path.join(MODEL_DIR, f"{suffix}.json")
        m = xgb.XGBRegressor()
        m.load_model(path)
        cache[key] = m

    for fname in os.listdir(MODEL_DIR):
        if not fname.endswith(".json") or "_meta" in fname:
            continue
        if fname.startswith("xgb_log"):
            continue
        key = fname.replace(".json", "")
        m = xgb.XGBRegressor()
        m.load_model(os.path.join(MODEL_DIR, fname))
        cache[key] = m
    return cache

def predict(cache: dict, country: str, disaster_type: str,
            month: int, year: int, severity: float):
    input_df = pd.DataFrame({
        "Country":       [country],
        "Disaster Type": [disaster_type],
        "Start Month":   [month],
        "Start Year":    [year],
        "Severity":      [severity],
    })
    input_df["Country"]       = input_df["Country"].astype("category")
    input_df["Disaster Type"] = input_df["Disaster Type"].astype("category")

    s = _slug(disaster_type)
    aff_key = f"{s}_affected"
    dam_key = f"{s}_damage"

    if aff_key in cache and dam_key in cache:
        pred_aff = cache[aff_key].predict(input_df)[0]
        pred_dam = cache[dam_key].predict(input_df)[0]
    else:
        pred_aff = cache["universal_affected"].predict(input_df)[0]
        pred_dam = cache["universal_damage"].predict(input_df)[0]

    return float(np.expm1(pred_aff)), float(np.expm1(pred_dam))

# ── RAG Retriever ─────────────────────────────────────────────────────────────
def get_top_analogy(conn, embedder, country: str, disaster_type: str, year: int) -> dict | None:
    dt_lower  = disaster_type.lower()
    rw_types  = TAXONOMY_BRIDGE.get(dt_lower, [disaster_type])
    query = f"Represent this sentence for searching relevant passages: {disaster_type} in {country} historical disaster impact narrative."
    vec = embedder.encode(query, normalize_embeddings=True).tolist()

    cur = conn.cursor()
    cur.execute("""
        SELECT country, disaster_type, narrative_text, event_year,
               1 - (embedding <=> %s::vector) AS sim
        FROM disaster_narratives
        WHERE event_year = %s AND disaster_type = ANY(%s) AND country ILIKE %s
        ORDER BY embedding <=> %s::vector
        LIMIT 1;
    """, (vec, year, rw_types, country, vec))
    row = cur.fetchone()

    if row is None:
        cur.execute("""
            SELECT country, disaster_type, narrative_text, event_year,
                   1 - (embedding <=> %s::vector) AS sim
            FROM disaster_narratives
            WHERE disaster_type = ANY(%s) AND country ILIKE %s
            ORDER BY embedding <=> %s::vector
            LIMIT 1;
        """, (vec, rw_types, country, vec))
        row = cur.fetchone()

    cur.close()
    if row is None:
        return None
    return {
        "country":       row[0],
        "disaster_type": row[1],
        "text":          row[2],
        "event_year":    row[3],
        "similarity":    float(row[4]),
    }

# ── Scenario Sampler ──────────────────────────────────────────────────────────
def sample_scenarios(conn, n: int = TARGET_SCENARIOS) -> list[dict]:
    rng = random.Random(RANDOM_SEED)
    cur = conn.cursor()
    cur.execute("""
        SELECT DISTINCT country, disaster_type
        FROM disaster_narratives
        WHERE country IS NOT NULL AND disaster_type IS NOT NULL
          AND disaster_type NOT IN ('Unknown', 'Other', 'Technological Disaster', 'Insect Infestation')
          AND narrative_text IS NOT NULL
        ORDER BY disaster_type, country;
    """)
    pool_all = cur.fetchall()
    cur.close()

    by_type: dict[str, list] = {}
    for country, dtype in pool_all:
        by_type.setdefault(dtype, []).append(country)

    scenarios = []
    types_ordered = sorted(by_type.keys())
    idx = 0
    seen = set()
    while len(scenarios) < n:
        dtype = types_ordered[idx % len(types_ordered)]
        candidates = by_type[dtype]
        rng.shuffle(candidates)
        for country in candidates:
            key = (country, dtype)
            if key not in seen:
                seen.add(key)
                severity = SEVERITY_MAP.get(dtype, DEFAULT_SEVERITY)
                severity = round(severity + rng.uniform(-0.5, 0.5), 1)
                month    = rng.randint(1, 12)
                year     = rng.choice([2018, 2019, 2020, 2021, 2022, 2023, 2024, 2025])
                scenarios.append({
                    "country":       country,
                    "disaster_type": dtype,
                    "severity":      severity,
                    "month":         month,
                    "year":          year,
                })
                break
        idx += 1
        if idx > len(types_ordered) * 50:
            break

    rng.shuffle(scenarios)
    return scenarios[:n]

# ── Markdown Renderer ─────────────────────────────────────────────────────────
def fmt_number(n: float) -> str:
    if n >= 1_000_000:
        return f"{n / 1_000_000:.2f}M"
    if n >= 1_000:
        return f"{n / 1_000:.1f}K"
    return f"{n:,.0f}"

def fmt_damage(usd_thousands: float) -> str:
    usd = usd_thousands * 1_000
    if usd >= 1_000_000_000:
        return f"${usd / 1_000_000_000:.2f}B"
    if usd >= 1_000_000:
        return f"${usd / 1_000_000:.2f}M"
    if usd >= 1_000:
        return f"${usd / 1_000:.1f}K"
    return f"${usd:,.0f}"

def render_markdown(scenarios_data: list[dict]) -> str:
    lines = []
    for i, s in enumerate(scenarios_data, 1):
        country       = s["country"]
        dtype         = s["disaster_type"]
        est_affected  = s["est_affected"]
        est_damage    = s["est_damage"]
        analogy       = s.get("analogy")

        if analogy:
            rag_context = analogy["text"].strip()
        else:
            rag_context = "No historical analogy found in corpus."

        math_pred = f"{fmt_number(est_affected)} Affected, {fmt_damage(est_damage)} Damage."
        
        block = f"[Scenario {i}]\nLocation: {country}\nHazard: {dtype}\nMath Engine Prediction: {math_pred}\nRAG Context Retrieved: {rag_context}\n"
        lines.append(block)
    
    return "\n".join(lines)

# ── Main ──────────────────────────────────────────────────────────────────────
def main():
    print("Loading XGBoost Math Engine models...")
    cache = load_math_engine()
    
    print("Connecting to pgvector database...")
    conn = psycopg2.connect(**DB_CONFIG)
    
    print("Booting embedding engine (BAAI/bge-large-en-v1.5)...")
    embedder = SentenceTransformer("BAAI/bge-large-en-v1.5")
    
    print(f"Sampling {TARGET_SCENARIOS} diverse scenarios & running inference...")
    scenarios = sample_scenarios(conn, TARGET_SCENARIOS)

    results = []
    for i, s in enumerate(scenarios, 1):
        country = s["country"]
        dtype   = s["disaster_type"]

        try:
            est_affected, est_damage = predict(cache, country, dtype, s["month"], s["year"], s["severity"])
        except Exception:
            est_affected, est_damage = 0.0, 0.0

        try:
            analogy = get_top_analogy(conn, embedder, country, dtype, s["year"])
        except Exception:
            analogy = None

        results.append({**s, "est_affected": est_affected, "est_damage": est_damage, "analogy": analogy})
        print(f"Processed {i}/{TARGET_SCENARIOS}: {country} - {dtype}")

    conn.close()

    print(f"Rendering Markdown to: {OUTPUT_PATH}")
    md = render_markdown(results)
    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        f.write(md)
    print("Done!")

if __name__ == "__main__":
    main()
