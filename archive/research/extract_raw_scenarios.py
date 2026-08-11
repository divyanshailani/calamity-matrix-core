"""
Calamity AI — Phase 18.1: Zero-Cost Training Data Extractor
============================================================
Connects to the disaster_narratives pgvector DB, draws ~50 diverse
scenarios, runs each through the local XGBoost Math Engine, and exports
a beautifully formatted Markdown file (raw_training_prompts.md) ready
to be pasted manually into any external LLM interface.

NO external LLM API is called. This script is purely extractive.

Usage:
    python3 scripts/extract_raw_scenarios.py
"""

import os
import sys
import re
import json
import random
import textwrap
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
OUTPUT_PATH = os.path.join(ROOT_DIR, "raw_training_prompts.md")

# ── Constants ─────────────────────────────────────────────────────────────────
TARGET_SCENARIOS = 50
RANDOM_SEED      = 42

# EM-DAT → ReliefWeb taxonomy bridge (mirrors api_orchestrator.py)
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
    "Flood":                 5.0,
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
    """Load XGBoost models into a simple dict cache. Mirrors orchestrator logic."""
    cache = {}

    # Universal fallback models
    for suffix, key in [("xgb_log_affected", "universal_affected"),
                        ("xgb_log_damage",   "universal_damage")]:
        path = os.path.join(MODEL_DIR, f"{suffix}.json")
        m = xgb.XGBRegressor()
        m.load_model(path)
        cache[key] = m
        with open(path.replace(".json", "_meta.json")) as f:
            cache[f"{key}_meta"] = json.load(f)

    # Pre-load all available domain-specific models
    for fname in os.listdir(MODEL_DIR):
        if not fname.endswith(".json") or "_meta" in fname:
            continue
        if fname.startswith("xgb_log"):
            continue
        key = fname.replace(".json", "")   # e.g. "earthquake_affected"
        m = xgb.XGBRegressor()
        m.load_model(os.path.join(MODEL_DIR, fname))
        cache[key] = m
        meta_path = os.path.join(MODEL_DIR, fname.replace(".json", "_meta.json"))
        if os.path.exists(meta_path):
            with open(meta_path) as f:
                cache[f"{key}_meta"] = json.load(f)

    return cache


def predict(cache: dict, country: str, disaster_type: str,
            month: int, year: int, severity: float):
    """Run Math Engine inference. Returns (est_affected, est_damage)."""
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

def get_top_analogy(conn, embedder, country: str, disaster_type: str,
                    year: int) -> dict | None:
    """Return the single best historical analogy from pgvector for a scenario."""
    dt_lower  = disaster_type.lower()
    rw_types  = TAXONOMY_BRIDGE.get(dt_lower, [disaster_type])

    query = (f"Represent this sentence for searching relevant passages: "
             f"{disaster_type} in {country} historical disaster impact narrative.")
    vec = embedder.encode(query, normalize_embeddings=True).tolist()

    cur = conn.cursor()

    # Pass 1 — strict year + country + type
    cur.execute("""
        SELECT country, disaster_type, narrative_text, event_year,
               1 - (embedding <=> %s::vector) AS sim
        FROM disaster_narratives
        WHERE event_year = %s AND disaster_type = ANY(%s) AND country ILIKE %s
        ORDER BY embedding <=> %s::vector
        LIMIT 1;
    """, (vec, year, rw_types, country, vec))
    row = cur.fetchone()

    # Pass 2 — relax year
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
    """
    Draw n diverse (country, disaster_type) pairs from the DB,
    then assign realistic simulation parameters.
    """
    rng = random.Random(RANDOM_SEED)

    cur = conn.cursor()
    cur.execute("""
        SELECT DISTINCT country, disaster_type
        FROM disaster_narratives
        WHERE country IS NOT NULL
          AND disaster_type IS NOT NULL
          AND disaster_type NOT IN ('Unknown', 'Other', 'Technological Disaster',
                                    'Insect Infestation')
          AND narrative_text IS NOT NULL
        ORDER BY disaster_type, country;
    """)
    pool_all = cur.fetchall()
    cur.close()

    # Group by disaster type to ensure diversity
    by_type: dict[str, list] = {}
    for country, dtype in pool_all:
        by_type.setdefault(dtype, []).append(country)

    scenarios = []
    types_ordered = sorted(by_type.keys())
    # Round-robin across types until we hit target
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
                # Add slight jitter ±0.5 to severity
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
        if idx > len(types_ordered) * 50:   # safety
            break

    rng.shuffle(scenarios)
    return scenarios[:n]


# ── Markdown Renderer ─────────────────────────────────────────────────────────

MONTH_NAMES = [
    "", "January", "February", "March", "April", "May", "June",
    "July", "August", "September", "October", "November", "December"
]


def fmt_number(n: float) -> str:
    if n >= 1_000_000:
        return f"{n / 1_000_000:.2f}M"
    if n >= 1_000:
        return f"{n / 1_000:.1f}K"
    return f"{n:.0f}"


def fmt_damage(usd_thousands: float) -> str:
    usd = usd_thousands * 1_000
    if usd >= 1_000_000_000:
        return f"${usd / 1_000_000_000:.2f}B"
    if usd >= 1_000_000:
        return f"${usd / 1_000_000:.2f}M"
    if usd >= 1_000:
        return f"${usd / 1_000:.1f}K"
    return f"${usd:.0f}"


def render_markdown(scenarios_data: list[dict]) -> str:
    now = datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")
    total = len(scenarios_data)

    lines = [
        "# Calamity AI — Raw Training Prompts",
        "",
        "> **Phase 18.1 — Zero-Cost Data Extraction**  ",
        f"> Generated: `{now}`  ",
        f"> Total Scenarios: **{total}**  ",
        "> Source: Local pgvector DB + XGBoost Math Engine (No external LLM called)",
        "",
        "---",
        "",
        "## How to Use This File",
        "",
        "Each scenario below is a complete, self-contained prompt.  ",
        "Copy the `### Prompt` block verbatim into your external LLM interface.  ",
        "Paste the LLM response into `### Expected Response (Fill In)`.  ",
        "When complete, these `(Prompt, Response)` pairs form the fine-tuning dataset.",
        "",
        "---",
        "",
    ]

    for i, s in enumerate(scenarios_data, 1):
        country       = s["country"]
        dtype         = s["disaster_type"]
        severity      = s["severity"]
        month         = s["month"]
        year          = s["year"]
        est_affected  = s["est_affected"]
        est_damage    = s["est_damage"]
        analogy       = s.get("analogy")

        month_name = MONTH_NAMES[month]

        # Format analogy block
        if analogy:
            analogy_text = analogy["text"][:400].strip()
            if len(analogy["text"]) > 400:
                analogy_text += "..."
            analogy_block = textwrap.dedent(f"""\
                - **Historical Event:** {analogy['disaster_type']} in {analogy['country']} ({analogy['event_year']})
                - **Semantic Similarity Score:** {analogy['similarity']:.4f}
                - **Situation Report Excerpt:**
                  > {analogy_text}
            """)
        else:
            analogy_block = "_No historical analogy found in corpus for this region/hazard combination._"

        prompt_body = textwrap.dedent(f"""\
            You are Calamity AI, a disaster impact analysis assistant trained on historical disaster data from USGS, NASA EONET, EM-DAT, and HDX/ReliefWeb.

            A simulation has been run for the following scenario. Using the Math Engine predictions and historical context provided, generate a structured, grounded impact assessment.

            **Simulation Parameters:**
            - Location: {country}
            - Hazard Type: {dtype}
            - Scenario Month: {month_name}
            - Scenario Year: {year}
            - Severity Index: {severity} / 10.0

            **Math Engine Predictions (XGBoost):**
            - Estimated Affected Population: {fmt_number(est_affected)} people
            - Estimated Economic Damage: {fmt_damage(est_damage)}

            **Closest Historical Analogy (RAG Engine):**
            {analogy_block}

            **Your Task:**
            Write a 3–4 sentence impact assessment that:
            1. Grounds the prediction in the historical analogy
            2. Contextualizes the severity and scale of impact
            3. Highlights the key humanitarian and economic risks
            4. Uses precise, factual language suitable for a disaster response briefing

            Do NOT invent specific casualty numbers beyond what is provided. Do NOT speculate about causes.
        """).strip()

        lines += [
            f"## Scenario {i:02d} — {dtype} | {country} ({year})",
            "",
            "| Field | Value |",
            "|---|---|",
            f"| **Country** | {country} |",
            f"| **Hazard** | {dtype} |",
            f"| **Month** | {month_name} {year} |",
            f"| **Severity** | {severity} / 10.0 |",
            f"| **Predicted Affected** | {fmt_number(est_affected)} |",
            f"| **Predicted Damage** | {fmt_damage(est_damage)} |",
            f"| **RAG Analogy** | {'✅ Found' if analogy else '❌ None'} |",
            "| **Analogy Similarity** | " + (f"{analogy['similarity']:.4f}" if analogy else "N/A") + " |",
            "",
            "### Prompt",
            "",
            "```",
            prompt_body,
            "```",
            "",
            "### Expected Response *(Fill In)*",
            "",
            "```",
            "",
            "```",
            "",
            "---",
            "",
        ]

    lines += [
        "## Summary Statistics",
        "",
        f"- **Total Scenarios:** {total}",
        f"- **Unique Disaster Types:** {len(set(s['disaster_type'] for s in scenarios_data))}",
        f"- **Unique Countries:** {len(set(s['country'] for s in scenarios_data))}",
        f"- **Scenarios With RAG Analogy:** {sum(1 for s in scenarios_data if s.get('analogy'))}",
        f"- **Scenarios Without Analogy:** {sum(1 for s in scenarios_data if not s.get('analogy'))}",
        f"- **Avg Semantic Similarity (where found):** "
        + (f"{np.mean([s['analogy']['similarity'] for s in scenarios_data if s.get('analogy')]):.4f}"
           if any(s.get('analogy') for s in scenarios_data) else "N/A"),
        "",
    ]

    return "\n".join(lines)


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    print("\n╔══════════════════════════════════════════════════════════════╗")
    print("║  Calamity AI — Phase 18.1: Training Data Extractor          ║")
    print("╚══════════════════════════════════════════════════════════════╝\n")

    # 1. Load Math Engine
    print("[1/4] Loading XGBoost Math Engine models...")
    cache = load_math_engine()
    domain_models = [k for k in cache if not k.startswith("universal") and not k.endswith("_meta")]
    print(f"      ✓ Loaded {len(domain_models)} domain-specific model files + universal fallback.\n")

    # 2. Connect to DB
    print("[2/4] Connecting to pgvector database...")
    conn = psycopg2.connect(**DB_CONFIG)
    print("      ✓ Connection established.\n")

    # 3. Load embedding model
    print("[3/4] Booting embedding engine (BAAI/bge-large-en-v1.5)...")
    embedder = SentenceTransformer("BAAI/bge-large-en-v1.5")
    print("      ✓ Embedder ready.\n")

    # 4. Sample scenarios
    print(f"[4/4] Sampling {TARGET_SCENARIOS} diverse scenarios & running inference...\n")
    scenarios = sample_scenarios(conn, TARGET_SCENARIOS)

    results = []
    max_country_len = max(len(s["country"]) for s in scenarios)

    for i, s in enumerate(scenarios, 1):
        country = s["country"]
        dtype   = s["disaster_type"]

        # Math Engine
        try:
            est_affected, est_damage = predict(
                cache, country, dtype, s["month"], s["year"], s["severity"]
            )
        except Exception as e:
            print(f"  [{i:02d}] ⚠ Math Engine error for {country}/{dtype}: {e}")
            est_affected, est_damage = 0.0, 0.0

        # RAG
        try:
            analogy = get_top_analogy(conn, embedder, country, dtype, s["year"])
        except Exception as e:
            print(f"  [{i:02d}] ⚠ RAG error for {country}/{dtype}: {e}")
            analogy = None

        rag_status = f"sim={analogy['similarity']:.3f}" if analogy else "no match"
        print(
            f"  [{i:02d}] {country:<{max_country_len}}  |  {dtype:<25}  |  "
            f"pop={fmt_number(est_affected):>8}  dmg={fmt_damage(est_damage):>10}  |  RAG: {rag_status}"
        )

        results.append({**s, "est_affected": est_affected,
                        "est_damage": est_damage, "analogy": analogy})

    conn.close()

    # 5. Render Markdown
    print(f"\n[✓] Rendering Markdown to: {OUTPUT_PATH}")
    md = render_markdown(results)
    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        f.write(md)

    rag_hits  = sum(1 for r in results if r.get("analogy"))
    print(f"\n╔══════════════════════════════════════════════════════════════╗")
    print(f"║  EXTRACTION COMPLETE                                         ║")
    print(f"╠══════════════════════════════════════════════════════════════╣")
    print(f"║  Scenarios extracted :  {len(results):<38}║")
    print(f"║  Unique disaster types: {len(set(r['disaster_type'] for r in results)):<38}║")
    print(f"║  Unique countries    :  {len(set(r['country'] for r in results)):<38}║")
    print(f"║  RAG analogies found :  {rag_hits} / {len(results):<35}║")
    print(f"║  Output file         :  raw_training_prompts.md              ║")
    print(f"╚══════════════════════════════════════════════════════════════╝\n")


if __name__ == "__main__":
    main()
