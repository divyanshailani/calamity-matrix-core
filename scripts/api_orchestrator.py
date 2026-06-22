import os
import uvicorn
import numpy as np
import pandas as pd
import xgboost as xgb
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sentence_transformers import SentenceTransformer
from psycopg2 import pool
from contextlib import asynccontextmanager

import sys

# Config
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.abspath(os.path.join(SCRIPT_DIR, '..')))
from src.config import DB_CONFIG
MODEL_DIR = os.path.join(SCRIPT_DIR, "..", "models")
XGB_AFFECTED_PATH = os.path.join(MODEL_DIR, "xgb_log_affected.json")
XGB_DAMAGE_PATH = os.path.join(MODEL_DIR, "xgb_log_damage.json")



# Global state container
models = {}

@asynccontextmanager
async def lifespan(app: FastAPI):
    print("\n[*] Initializing Calamity AI Neuro-Symbolic Orchestrator...")
    
    # 1. Load XGBoost Models
    print("[*] Loading XGBoost Predictors...")
    models['xgb_affected'] = xgb.XGBRegressor()
    models['xgb_affected'].load_model(XGB_AFFECTED_PATH)
    
    models['xgb_damage'] = xgb.XGBRegressor()
    models['xgb_damage'].load_model(XGB_DAMAGE_PATH)
    
    # 2. Load Embedding Model
    print("[*] Booting Embedding Engine (BAAI/bge-large-en-v1.5)...")
    models['embedder'] = SentenceTransformer('BAAI/bge-large-en-v1.5')
    
    # 3. Initialize Postgres Connection Pool
    print("[*] Establishing pgvector connection pool on port 5433...")
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
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Pydantic Payload
class SimulationRequest(BaseModel):
    query_text: str
    country: str
    disaster_type: str
    month: int
    event_year: int
    severity: float

@app.post("/api/v1/simulate_calamity")
async def simulate_calamity(payload: SimulationRequest):
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
        
        # Inference
        pred_log_affected = models['xgb_affected'].predict(input_data)[0]
        pred_log_damage = models['xgb_damage'].predict(input_data)[0]
        
        # Inverse log1p transform (expm1) back to real-world numbers
        est_affected = float(np.expm1(pred_log_affected))
        est_damage = float(np.expm1(pred_log_damage))
        
        # ---------------------------------------------------------
        # 2. The RAG Engine Execution (Historical Context)
        # ---------------------------------------------------------
        # Generate Vector Embedding for Semantic Search
        instruction = "Represent this sentence for searching relevant passages: "
        master_semantic_query = f"{payload.disaster_type} in {payload.country} (Year: {payload.event_year}). Additional Context: {payload.query_text}"
        full_query = instruction + master_semantic_query
        query_embedding = models['embedder'].encode(full_query, normalize_embeddings=True).tolist()

        
        db_pool = models['db_pool']
        conn = db_pool.getconn()
        
        try:
            cur = conn.cursor()
            # Hybrid Query: Filter by country & disaster type, then search semantically
            sql_query = """
                SELECT date, country, disaster_type, narrative_text, event_year,
                       1 - (embedding <=> %s::vector) AS cosine_similarity
                FROM disaster_narratives
                ORDER BY embedding <=> %s::vector
                LIMIT 3;
            """
            
            cur.execute(sql_query, (query_embedding, query_embedding))
            results = cur.fetchall()
            cur.close()
        finally:
            db_pool.putconn(conn)
            
        # Format Context
        historical_context = []
        for row in results:
            text_preview = row[3][:300] + "..." if len(row[3]) > 300 else row[3]
            historical_context.append({
                "date": str(row[0]),
                "country": str(row[1]) if row[1] is not None else "Unknown",
                "disaster_type": str(row[2]) if row[2] is not None else "Unknown",
                "narrative_preview": text_preview,
                "event_year": row[4],
                "similarity_score": float(row[5])
            })
            
        # ---------------------------------------------------------
        # 3. The Fusion Payload
        # ---------------------------------------------------------
        return {
            "status": "success",
            "predictions": {
                "estimated_affected_population": round(est_affected, 0),
                "estimated_damage_usd_thousands": round(est_damage, 2)
            },
            "historical_context": historical_context
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="info")
