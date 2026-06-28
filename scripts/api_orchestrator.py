import os
import json
import uvicorn
import numpy as np
import pandas as pd
import xgboost as xgb
from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import requests
from psycopg2 import pool
from contextlib import asynccontextmanager
import openai

import sys

# Config
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.abspath(os.path.join(SCRIPT_DIR, '..')))
from src.config import DB_CONFIG, DATABASE_URL, HF_TOKEN, CLOUD_LLM_ENDPOINT
MODEL_DIR = os.path.join(SCRIPT_DIR, "..", "models")
XGB_AFFECTED_PATH = os.path.join(MODEL_DIR, "xgb_log_affected.json")
XGB_DAMAGE_PATH = os.path.join(MODEL_DIR, "xgb_log_damage.json")



# Global state container
models = {}

@asynccontextmanager
async def lifespan(app: FastAPI):
    print("\n[*] Initializing Calamity AI Neuro-Symbolic Orchestrator...")
    
    # 1. Load Universal XGBoost Predictors (Fallback)
    import json
    print("[*] Loading Universal XGBoost Predictors (v2 Fallback)...")
    models['universal_affected'] = xgb.XGBRegressor()
    models['universal_affected'].load_model(XGB_AFFECTED_PATH)
    with open(XGB_AFFECTED_PATH.replace('.json', '_meta.json'), 'r') as f:
        models['universal_affected_meta'] = json.load(f)
    
    models['universal_damage'] = xgb.XGBRegressor()
    models['universal_damage'].load_model(XGB_DAMAGE_PATH)
    with open(XGB_DAMAGE_PATH.replace('.json', '_meta.json'), 'r') as f:
        models['universal_damage_meta'] = json.load(f)
    
    # 2. Setup Embedding Bridge
    print("[*] Connecting to Neural Bridge (Hugging Face Inference API)...")
    if not HF_TOKEN:
        print("[!] Warning: HF_TOKEN is not set. Inference API may rate limit heavily.")
    
    # 3. Initialize Postgres Connection Pool
    if DATABASE_URL:
        print("[*] Establishing cloud pgvector connection pool to Supabase...")
        models['db_pool'] = pool.SimpleConnectionPool(1, 10, dsn=DATABASE_URL)
    else:
        print("[*] Establishing local pgvector connection pool on port 5433...")
        models['db_pool'] = pool.SimpleConnectionPool(1, 10, **DB_CONFIG)
    
    print("[+] Orchestrator successfully primed and listening on port 8000.\n")
    
    yield
    
    # Shutdown gracefully
    print("\n[*] Shutting down Orchestrator...")
    if 'db_pool' in models and models['db_pool']:
        models['db_pool'].closeall()

app = FastAPI(title="Calamity AI: Neuro-Symbolic Orchestrator", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/health")
def health_check():
    return {"status": "alive", "service": "calamity-orchestrator"}

# Pydantic Payload
class SimulationRequest(BaseModel):
    query_text: str
    country: str
    disaster_type: str
    month: int
    event_year: int
    severity: float

class ChatRequest(BaseModel):
    messages: list
    stream: bool = True

class AskAIRequest(BaseModel):
    query_text: str
    historical_context: list
    simulation_parameters: dict
    math_predictions: dict
    stream: bool = True

COUNTRY_ALIASES = {
    "Turkey": "Türkiye",
    "Russia": "Russian Federation",
    "US": "United States of America",
    "USA": "United States of America",
    "Vietnam": "Viet Nam"
}

@app.post("/api/v1/simulate_calamity")
async def simulate_calamity(payload: SimulationRequest):
    payload.country = COUNTRY_ALIASES.get(payload.country, payload.country)
    try:
        # ---------------------------------------------------------
        # 1. The Math Engine Execution (Predictive)
        # ---------------------------------------------------------
        # Format exact columns trained by XGBoost
        input_data = pd.DataFrame({
            'Country': [payload.country],
            'Disaster Type': [payload.disaster_type],
            'Start Month': [payload.month],
            'Start Year': [payload.event_year],
            'Severity': [payload.severity]
        })
        
        # Cast specific columns to native categories exactly as done in training
        input_data['Country'] = input_data['Country'].astype('category')
        input_data['Disaster Type'] = input_data['Disaster Type'].astype('category')
        
        # Dynamic Multi-Physics Routing
        import re
        import json
        slug = str(payload.disaster_type).lower()
        slug = re.sub(r'[^a-z0-9]+', '_', slug).strip('_')
        
        cache_key_aff = f"{slug}_affected"
        cache_key_dam = f"{slug}_damage"
        
        aff_model_path = os.path.join(MODEL_DIR, f"{cache_key_aff}.json")
        dam_model_path = os.path.join(MODEL_DIR, f"{cache_key_dam}.json")
        
        if os.path.exists(aff_model_path) and os.path.exists(dam_model_path):
            # Lazy load domain-specific models if not in cache
            if cache_key_aff not in models:
                models[cache_key_aff] = xgb.XGBRegressor()
                models[cache_key_aff].load_model(aff_model_path)
                with open(aff_model_path.replace('.json', '_meta.json'), 'r') as f:
                    models[f"{cache_key_aff}_meta"] = json.load(f)
            if cache_key_dam not in models:
                models[cache_key_dam] = xgb.XGBRegressor()
                models[cache_key_dam].load_model(dam_model_path)
                with open(dam_model_path.replace('.json', '_meta.json'), 'r') as f:
                    models[f"{cache_key_dam}_meta"] = json.load(f)
                
            model_affected = models[cache_key_aff]
            model_damage = models[cache_key_dam]
            meta_affected = models[f"{cache_key_aff}_meta"]
            meta_damage = models[f"{cache_key_dam}_meta"]
            
            # Domain-specific inference
            pred_log_affected = model_affected.predict(input_data)[0]
            pred_log_damage = model_damage.predict(input_data)[0]
        else:
            # Fallback to Universal v2 Model for rare physics
            pred_log_affected = models['universal_affected'].predict(input_data)[0]
            pred_log_damage = models['universal_damage'].predict(input_data)[0]
            meta_affected = models['universal_affected_meta']
            meta_damage = models['universal_damage_meta']
        
        # Inverse log1p transform (expm1) back to real-world numbers
        est_affected = float(np.expm1(pred_log_affected))
        est_damage = float(np.expm1(pred_log_damage))
        
        # ---------------------------------------------------------
        # 2. The RAG Engine Execution (Historical Context)
        # ---------------------------------------------------------
        # Generate Vector Embedding via Hugging Face API
        instruction = "Represent this sentence for searching relevant passages: "
        master_semantic_query = f"{payload.disaster_type} in {payload.country} (Year: {payload.event_year}). Additional Context: {payload.query_text}"
        full_query = instruction + master_semantic_query
        
        hf_api_url = "https://router.huggingface.co/hf-inference/models/BAAI/bge-large-en-v1.5"
        headers = {"Authorization": f"Bearer {HF_TOKEN}"} if HF_TOKEN else {}
        resp = requests.post(hf_api_url, headers=headers, json={"inputs": full_query, "options": {"wait_for_model": True}})
        
        if resp.status_code != 200:
            raise HTTPException(status_code=500, detail=f"Hugging Face API Error: {resp.text}")
            
        embed_result = resp.json()
        # Ensure we have a flat list of floats
        if isinstance(embed_result, list) and len(embed_result) > 0 and isinstance(embed_result[0], list):
            embed_result = embed_result[0] # handle batch outer list
            
        # Normalize embeddings (equivalent to normalize_embeddings=True)
        vec = np.array(embed_result, dtype=float)
        norm = np.linalg.norm(vec)
        if norm > 0:
            vec = vec / norm
        query_embedding = vec.tolist()

        # Map EM-DAT taxonomy to ReliefWeb taxonomy for RAG matching
        rw_types = [payload.disaster_type]
        dt_lower = payload.disaster_type.lower()
        if dt_lower == "extreme temperature":
            rw_types = ["Heat Wave", "Cold Wave", "Extreme temperature"]
        elif dt_lower == "storm":
            rw_types = ["Storm", "Storm Surge", "Tropical Cyclone", "Extratropical Cyclone", "Severe Local Storm"]
        elif dt_lower == "mass movement (wet)":
            rw_types = ["Mud Slide", "Land Slide", "Mass movement (wet)"]
        elif dt_lower == "volcanic activity":
            rw_types = ["Volcano", "Volcanic activity"]
        elif dt_lower == "wildfire":
            rw_types = ["Wild Fire", "Fire", "Wildfire"]
            
        db_pool = models['db_pool']
        conn = db_pool.getconn()
        
        try:
            cur = conn.cursor()
            
            # Pass 1: Strict match (Year, Country, Disaster Type)
            sql_query_pass1 = """
                SELECT date, country, disaster_type, narrative_text, event_year, lat, lng,
                       1 - (embedding <=> %s::vector) AS cosine_similarity
                FROM disaster_narratives
                WHERE event_year = %s AND disaster_type = ANY(%s) AND country ILIKE %s
                ORDER BY embedding <=> %s::vector
                LIMIT 3;
            """
            cur.execute(sql_query_pass1, (query_embedding, payload.event_year, rw_types, payload.country, query_embedding))
            results = cur.fetchall()
            
            # Pass 2: Relax Year completely, strictly enforce Country and Disaster Type
            if len(results) < 3:
                sql_query_pass2 = """
                    SELECT date, country, disaster_type, narrative_text, event_year, lat, lng,
                           1 - (embedding <=> %s::vector) AS cosine_similarity
                    FROM disaster_narratives
                    WHERE disaster_type = ANY(%s) AND country ILIKE %s
                    ORDER BY embedding <=> %s::vector
                    LIMIT 3;
                """
                cur.execute(sql_query_pass2, (query_embedding, rw_types, payload.country, query_embedding))
                results = cur.fetchall()
                
            # Pass 3: Recommendation Engine (If Pass 2 yields 0 results)
            suggested_alternatives = None
            if len(results) == 0:
                # Option A: Same Country, Alternate Hazards
                cur.execute("SELECT DISTINCT disaster_type FROM disaster_narratives WHERE country ILIKE %s AND disaster_type IS NOT NULL LIMIT 5", (payload.country,))
                same_country_disasters = [row[0] for row in cur.fetchall()]
                
                # Option B: Same Country, Closest Chronological Matches
                cur.execute("SELECT event_year FROM disaster_narratives WHERE country ILIKE %s AND event_year IS NOT NULL GROUP BY event_year ORDER BY ABS(event_year - %s) ASC LIMIT 5", (payload.country, payload.event_year))
                closest_historical_years = [row[0] for row in cur.fetchall()]
                
                suggested_alternatives = {
                    "same_country_disasters": same_country_disasters,
                    "closest_historical_years": closest_historical_years
                }
                
            cur.close()
        finally:
            db_pool.putconn(conn)
            
        # Format Context
        historical_context = []
        total_cosine_sim = 0.0
        for row in results:
            sim_score = float(row[7])
            total_cosine_sim += sim_score
            text_preview = row[3][:300] + "..." if len(row[3]) > 300 else row[3]
            historical_context.append({
                "date": str(row[0]),
                "country": str(row[1]) if row[1] is not None else "Unknown",
                "disaster_type": str(row[2]) if row[2] is not None else "Unknown",
                "text_preview": text_preview,
                "event_year": row[4],
                "lat": row[5],
                "lng": row[6],
                "similarity_score": sim_score
            })
            
        avg_cosine_sim = (total_cosine_sim / len(results)) if len(results) > 0 else 0.0
            
        # ---------------------------------------------------------
        # 3. The Fusion Payload
        # ---------------------------------------------------------
        return {
            "status": "success",
            "predictions": {
                "estimated_affected_population": round(est_affected, 0),
                "estimated_damage_usd_thousands": round(est_damage, 2)
            },
            "historical_context": historical_context,
            "suggested_alternatives": suggested_alternatives,
            "telemetry": {
                "math_engine": {
                    "affected_population": {
                        "val_rmse": meta_affected.get("rmse"),
                        "val_mae": meta_affected.get("mae"),
                        "feature_importances": meta_affected.get("feature_importance_gain", {})
                    },
                    "economic_damage": {
                        "val_rmse": meta_damage.get("rmse"),
                        "val_mae": meta_damage.get("mae"),
                        "feature_importances": meta_damage.get("feature_importance_gain", {})
                    }
                },
                "rag_engine": {
                    "average_cosine_similarity": avg_cosine_sim
                }
            }
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ---------------------------------------------------------
# LLM Integration (OpenAI Compatible via Serverless GPU)
# ---------------------------------------------------------
client = openai.AsyncOpenAI(
    base_url=CLOUD_LLM_ENDPOINT,
    api_key="dummy" # Cloud endpoint doesn't require a key
)

@app.post("/api/v1/chat")
async def chat_endpoint(payload: ChatRequest):
    try:
        response = await client.chat.completions.create(
            model="calamity-ai",
            messages=payload.messages,
            stream=payload.stream
        )
        if payload.stream:
            async def generate():
                async for chunk in response:
                    if chunk.choices and chunk.choices[0].delta.content:
                        yield f"data: {json.dumps({'text': chunk.choices[0].delta.content})}\n\n"
                yield "data: [DONE]\n\n"
            return StreamingResponse(generate(), media_type="text/event-stream")
        else:
            return {"response": response.choices[0].message.content}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/v1/ask_ai")
async def ask_ai_endpoint(payload: AskAIRequest):
    try:
        system_prompt = "You are Calamity AI, a disaster impact analysis assistant trained on historical disaster data from USGS, NASA EONET, EM-DAT, and HDX/ReliefWeb. Write cold, objective, highly analytical, and strictly factual impact assessments."
        
        sim_params_str = json.dumps(payload.simulation_parameters, indent=2)
        math_preds_str = json.dumps(payload.math_predictions, indent=2)
        
        rag_data_str = ""
        for i, ctx in enumerate(payload.historical_context):
            rag_data_str += f"[Context {i+1}]\nDate: {ctx.get('date')}\nLocation: {ctx.get('country')}\nDisaster: {ctx.get('disaster_type')}\nNarrative: {ctx.get('text_preview')}\n\n"
            
        user_message = f"A simulation has been run for the following scenario. Using the Math Engine predictions and historical context provided, generate a structured, grounded impact assessment.\n\n**Simulation Parameters:**\n{sim_params_str}\n\n**Math Engine Predictions (XGBoost):**\n{math_preds_str}\n\n**Closest Historical Analogy (RAG Engine):**\n{rag_data_str.strip()}\n\n**Your Task:**\nWrite a 3-4 sentence impact assessment..."
        
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message}
        ]
        
        response = await client.chat.completions.create(
            model="calamity-ai",
            messages=messages,
            stream=payload.stream
        )
        if payload.stream:
            async def generate():
                async for chunk in response:
                    if chunk.choices and chunk.choices[0].delta.content:
                        yield f"data: {json.dumps({'text': chunk.choices[0].delta.content})}\n\n"
                yield "data: [DONE]\n\n"
            return StreamingResponse(generate(), media_type="text/event-stream")
        else:
            return {"response": response.choices[0].message.content}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="info")
