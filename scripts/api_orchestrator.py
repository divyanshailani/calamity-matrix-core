import os
import uvicorn
import numpy as np
import pandas as pd
import xgboost as xgb
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from sentence_transformers import SentenceTransformer
from psycopg2 import pool
from contextlib import asynccontextmanager

# Config
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
MODEL_DIR = os.path.join(SCRIPT_DIR, "..", "models")
XGB_AFFECTED_PATH = os.path.join(MODEL_DIR, "xgb_log_affected.json")
XGB_DAMAGE_PATH = os.path.join(MODEL_DIR, "xgb_log_damage.json")

DB_PARAMS = {
    "host": "localhost",
    "port": "5433",
    "user": "admin",
    "password": "root",
    "dbname": "calamity_rag"
}

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
    models['db_pool'] = pool.SimpleConnectionPool(1, 10, **DB_PARAMS)
    
    print("[+] Orchestrator successfully primed and listening on port 8000.\n")
    
    yield
    
    # Shutdown gracefully
    print("\n[*] Shutting down Orchestrator...")
    if 'db_pool' in models and models['db_pool']:
        models['db_pool'].closeall()

app = FastAPI(title="Calamity AI: Neuro-Symbolic Orchestrator", lifespan=lifespan)

# Pydantic Payload
class SimulationRequest(BaseModel):
    query_text: str
    country: str
    disaster_type: str
    month: int
    event_year: int

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
            'Start Year': [payload.event_year]
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
        full_query = instruction + payload.query_text
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
                WHERE country ILIKE %s AND disaster_type ILIKE %s
                ORDER BY embedding <=> %s::vector
                LIMIT 3;
            """
            c_filter = f"%{payload.country}%"
            d_filter = f"%{payload.disaster_type}%"
            
            cur.execute(sql_query, (query_embedding, c_filter, d_filter, query_embedding))
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
                "country": row[1],
                "disaster_type": row[2],
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
