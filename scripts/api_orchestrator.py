import os
import sys
import json
import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
import requests
from psycopg2 import pool
from contextlib import asynccontextmanager
from fastapi import BackgroundTasks, Header, Request
import openai
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
import logging
import pycountry
import contextvars
import uuid
import hmac

request_id_ctx = contextvars.ContextVar("request_id", default=None)

class JSONFormatter(logging.Formatter):
    def format(self, record):
        log_record = {
            "time": self.formatTime(record, self.datefmt),
            "level": record.levelname,
            "message": record.getMessage(),
            "name": record.name
        }
        req_id = request_id_ctx.get()
        if req_id:
            log_record["request_id"] = req_id
        return json.dumps(log_record)

logger = logging.getLogger("calamity-orchestrator")
logger.setLevel(logging.INFO)
handler = logging.StreamHandler(sys.stdout)
handler.setFormatter(JSONFormatter())
logger.addHandler(handler)

# Config
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.abspath(os.path.join(SCRIPT_DIR, '..')))
from src.config import DB_CONFIG, DATABASE_URL, HF_TOKEN, CLOUD_LLM_ENDPOINT, INGESTION_SECRET_KEY, CLOUD_LLM_API_KEY, MIN_EVENT_YEAR, TIME_DECAY_PENALTY, CLOUD_LLM_MODEL, MATH_ENGINE_URL
import scripts.live_ingestion as live_ingestion
# Global state container
models = {}

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("\n[*] Initializing Calamity AI Neuro-Symbolic Orchestrator...")
    
    # 2. Setup Embedding Bridge
    logger.info("[*] Connecting to Neural Bridge (Hugging Face Inference API)...")
    if not HF_TOKEN:
        logger.warning(" HF_TOKEN is not set. Inference API may rate limit heavily.")
        
    # Start a background thread to keep ONLY the Hugging Face API warm
    import threading
    import time
    def keep_hf_warm():
        hf_api_url = "https://router.huggingface.co/hf-inference/models/BAAI/bge-large-en-v1.5"
        headers = {"Authorization": f"Bearer {HF_TOKEN}"} if HF_TOKEN else {}
        
        while True:
            try:
                # 1. Ping Hugging Face with wait_for_model to force it into VRAM
                payload = {"inputs": "warmup", "options": {"wait_for_model": True}}
                resp = requests.post(hf_api_url, headers=headers, json=payload, timeout=40)
                if resp.status_code == 200:
                    logger.debug("[~] HF Warmup Ping: Success.")
                else:
                    logger.warning(f"[!] HF Warmup Ping: Status {resp.status_code}")
            except Exception as e:
                logger.warning(f"[!] HF Warmup Ping Exception: {e}")
                
            time.sleep(30)  # Ping every 30 seconds to aggressively prevent sleep

    warmup_thread = threading.Thread(target=keep_hf_warm, daemon=True)
    warmup_thread.start()
    logger.info("[+] Neural Bridge Warm-up Thread (HF) started.")

    
    # 3. Initialize Postgres Connection Pool
    if DATABASE_URL:
        logger.info("[*] Establishing cloud pgvector connection pool to Azure...")
        models['db_pool'] = pool.SimpleConnectionPool(
            1, 10, 
            dsn=DATABASE_URL,
            keepalives=1,
            keepalives_idle=60,
            keepalives_interval=10,
            keepalives_count=5,
            connect_timeout=10,
            options="-c statement_timeout=10000"
        )
    else:
        logger.info("[*] Establishing local pgvector connection pool on port 5433...")
        models['db_pool'] = pool.SimpleConnectionPool(
            1, 10, 
            **DB_CONFIG,
            connect_timeout=10,
            options="-c statement_timeout=10000"
        )
        
    logger.info("[*] Validating Database Connection...")
    conn = models['db_pool'].getconn()
    try:
        cur = conn.cursor()
        cur.execute("SELECT 1;")
        cur.close()
        logger.info("[+] Database connection pool validated successfully.")
    except Exception as e:
        logger.error(f"[-] Database connection failed during startup: {e}")
        raise e
    finally:
        models['db_pool'].putconn(conn)
    
    logger.info("[+] Orchestrator successfully primed and listening on port 8000.\n")
    
    yield
    
    # Shutdown gracefully
    logger.info("\n[*] Shutting down Orchestrator...")
    if 'db_pool' in models and models['db_pool']:
        models['db_pool'].closeall()

limiter = Limiter(key_func=get_remote_address)
app = FastAPI(title="Calamity AI: Neuro-Symbolic Orchestrator", lifespan=lifespan)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://calamityai.tech", "https://www.calamityai.tech", "https://calamity-ui.vercel.app"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/health")
def health_check():
    return {"status": "alive", "service": "calamity-orchestrator"}

# Pydantic Payload
class SimulationRequest(BaseModel):
    query_text: str = Field(..., min_length=1, max_length=4000)
    country: str
    disaster_type: str
    month: int
    event_year: int
    severity: float = Field(..., ge=0.0, lt=1000000.0)

class ChatRequest(BaseModel):
    query_text: str = Field(..., min_length=1, max_length=4000)
    stream: bool = True

class AskAIRequest(BaseModel):
    query_text: str = Field(..., min_length=1, max_length=4000)
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

def resolve_country(name: str):
    if name in COUNTRY_ALIASES:
        return COUNTRY_ALIASES[name]
    try:
        return pycountry.countries.lookup(name).name
    except LookupError:
        try:
            matches = pycountry.countries.search_fuzzy(name)
            if matches:
                return matches[0].name
        except Exception as e:
            logger.warning(f"Fuzzy search failed for country '{name}': {e}")
    return name

@app.post("/api/v1/simulate_calamity")
@limiter.limit("5/minute")
def simulate_calamity(request: Request, payload: SimulationRequest):
    request_id_ctx.set(str(uuid.uuid4()))
    payload.country = resolve_country(payload.country)
    payload.country = payload.country.replace('%', '').replace('_', '')
    try:
        from concurrent.futures import ThreadPoolExecutor

        # ---------------------------------------------------------
        # 1. Prepare Payloads
        # ---------------------------------------------------------
        math_engine_url = MATH_ENGINE_URL
        compute_payload = {
            "country": payload.country,
            "disaster_type": payload.disaster_type,
            "month": payload.month,
            "event_year": payload.event_year,
            "severity": payload.severity
        }
        
        instruction = "Represent this sentence for searching relevant passages: "
        master_semantic_query = f"{payload.disaster_type} in {payload.country} (Year: {payload.event_year}). Additional Context: {payload.query_text}"
        full_query = instruction + master_semantic_query
        
        hf_api_url = "https://router.huggingface.co/hf-inference/models/BAAI/bge-large-en-v1.5"
        headers = {"Authorization": f"Bearer {HF_TOKEN}"} if HF_TOKEN else {}

        # ---------------------------------------------------------
        # 2. Define Network Workers
        # ---------------------------------------------------------
        def fetch_math_engine():
            logger.info("[DEBUG] Hitting Math Engine Microservice...")
            resp = requests.post(math_engine_url, json=compute_payload, timeout=30)
            resp.raise_for_status()
            return resp.json()

        def fetch_hf():
            max_retries = 3
            for attempt in range(max_retries):
                try:
                    logger.info(f"[DEBUG] Hitting HF API... (Attempt {attempt+1}/{max_retries})")
                    resp = requests.post(hf_api_url, headers=headers, json={"inputs": full_query, "options": {"wait_for_model": True}}, timeout=120)
                    
                    if resp.status_code == 200:
                        return resp.json()
                    elif resp.status_code in [500, 502, 503, 504]:
                        logger.warning(f"[!] HF API Error {resp.status_code} on attempt {attempt+1}: {resp.text}")
                        if attempt < max_retries - 1:
                            time.sleep(2 ** attempt)  # Backoff: 1s, 2s
                            continue
                        raise HTTPException(status_code=500, detail=f"Hugging Face API Error: {resp.status_code}")
                    else:
                        logger.warning(f"[!] HF API Client Error {resp.status_code}: {resp.text}")
                        raise HTTPException(status_code=500, detail=f"Hugging Face API Error: {resp.status_code}")
                        
                except requests.exceptions.Timeout:
                    logger.warning(f"[!] HF API Timeout on attempt {attempt+1}.")
                    if attempt < max_retries - 1:
                        continue
                    raise HTTPException(status_code=503, detail="Hugging Face API timed out after 120s. Model may be fully cold.")
                except requests.exceptions.RequestException as e:
                    logger.warning(f"[!] HF API Network Exception on attempt {attempt+1}: {e}")
                    if attempt < max_retries - 1:
                        time.sleep(2 ** attempt)
                        continue
                    raise HTTPException(status_code=500, detail="Hugging Face API Request failed due to network error.")
                except Exception as e:
                    logger.warning(f"[!] HF API Unexpected Exception on attempt {attempt+1}: {e}")
                    raise HTTPException(status_code=500, detail="Hugging Face API Request failed unexpectedly.")

        # ---------------------------------------------------------
        # 3. Execute in Parallel
        # ---------------------------------------------------------
        with ThreadPoolExecutor(max_workers=2) as executor:
            future_math = executor.submit(fetch_math_engine)
            future_hf = executor.submit(fetch_hf)
            
            try:
                math_data = future_math.result()
            except Exception as e:
                logger.error(f"[!] Math Engine Microservice Error: {e}")
                raise HTTPException(status_code=500, detail="Math Engine Microservice Failed.")
            
            embed_result = future_hf.result()
            
        est_affected = math_data["est_affected"]
        est_damage = math_data["est_damage"]
        meta_affected = math_data.get("meta_affected", {})
        meta_damage = math_data.get("meta_damage", {})
        # Ensure we have a flat list of floats
        if isinstance(embed_result, list) and len(embed_result) > 0 and isinstance(embed_result[0], list):
            embed_result = embed_result[0] # handle batch outer list
            
        # Normalize embeddings (equivalent to normalize_embeddings=True)
        norm = sum(x**2 for x in embed_result)**0.5
        if norm > 0:
            query_embedding = [x / norm for x in embed_result]
        else:
            raise HTTPException(status_code=500, detail="Hugging Face API returned an invalid zero-vector.")

        # Map EM-DAT taxonomy to ReliefWeb taxonomy for RAG matching
        rw_types = [payload.disaster_type]
        dt_lower = payload.disaster_type.lower()
        decay_factor = TIME_DECAY_PENALTY.get(dt_lower, TIME_DECAY_PENALTY["default"])
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
            
            # Pass 1: Strict match (Year, Country, Disaster Type) + Quarantine
            sql_query_pass1 = """
                SELECT date, country, disaster_type, narrative_text, event_year, lat, lng,
                       (1 - (embedding <=> %s::vector)) - (%s * ABS(event_year - %s)) AS hybrid_similarity
                FROM disaster_narratives
                WHERE event_year = %s AND disaster_type = ANY(%s) AND country ILIKE %s AND event_year >= %s
                ORDER BY hybrid_similarity DESC
                LIMIT 3;
            """
            cur.execute(sql_query_pass1, (query_embedding, decay_factor, payload.event_year, payload.event_year, rw_types, payload.country, MIN_EVENT_YEAR))
            results = cur.fetchall()
            
            # Pass 2: Relax Year completely, strictly enforce Country and Disaster Type + Time-Decay + Quarantine
            if len(results) < 3:
                sql_query_pass2 = """
                    SELECT date, country, disaster_type, narrative_text, event_year, lat, lng,
                           (1 - (embedding <=> %s::vector)) - (%s * ABS(event_year - %s)) AS hybrid_similarity
                    FROM disaster_narratives
                    WHERE disaster_type = ANY(%s) AND country ILIKE %s AND event_year >= %s
                    ORDER BY hybrid_similarity DESC
                    LIMIT 3;
                """
                cur.execute(sql_query_pass2, (query_embedding, decay_factor, payload.event_year, rw_types, payload.country, MIN_EVENT_YEAR))
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
        
        logger.info(f"\n[RAG] Top 3 Semantic Search Results for {payload.disaster_type} in {payload.country} (Target Year: {payload.event_year})")
        print("-" * 70)
        
        for idx, row in enumerate(results):
            sim_score = float(row[7])
            total_cosine_sim += sim_score
            event_year = row[4]
            
            penalty = decay_factor * abs(event_year - payload.event_year)
            raw_score = sim_score + penalty
            
            logger.info(f"Rank {idx+1}: {row[2]} in {row[1]} ({event_year})")
            logger.info(f"  -> Raw Vector Score: {raw_score:.4f}")
            logger.info(f"  -> Time-Decay Penalty: -{penalty:.4f} ({abs(event_year - payload.event_year)} years diff)")
            logger.info(f"  -> Final Hybrid Score: {sim_score:.4f}")
            print("-" * 70)
            
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
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[!] Unhandled Exception in simulate_calamity: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

# ---------------------------------------------------------
# LLM Integration (OpenAI Compatible via Serverless GPU)
# ---------------------------------------------------------
client = openai.AsyncOpenAI(
    base_url=CLOUD_LLM_ENDPOINT,
    api_key=CLOUD_LLM_API_KEY
)

@app.post("/api/v1/chat")
@limiter.limit("10/minute")
async def chat_endpoint(request: Request, payload: ChatRequest):
    request_id_ctx.set(str(uuid.uuid4()))
    try:
        system_prompt = "You are Calamity AI, a disaster impact analysis assistant trained on historical disaster data from USGS, NASA EONET, EM-DAT, and HDX/ReliefWeb. Write cold, objective, highly analytical, and strictly factual impact assessments. Speak with absolute certainty and full confidence. Never use phrases like 'expected to', 'estimated to', or 'predicted'. Present all figures as established facts. Never mention your internal 'Math Engine' or 'RAG Engine' or 'simulation parameters' directly to the user. You were engineered by Divyansh Ailani. You are currently running on a Groq LPU."
        
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": payload.query_text}
        ]
        
        response = await client.chat.completions.create(
            model=CLOUD_LLM_MODEL,
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

@app.post("/api/v1/ask_ai")
@limiter.limit("10/minute")
async def ask_ai_endpoint(request: Request, payload: AskAIRequest):
    request_id_ctx.set(str(uuid.uuid4()))
    try:
        system_prompt = "You are Calamity AI, a disaster impact analysis assistant trained on historical disaster data from USGS, NASA EONET, EM-DAT, and HDX/ReliefWeb. Write cold, objective, highly analytical, and strictly factual impact assessments. Speak with absolute certainty and full confidence. Never use phrases like 'expected to', 'estimated to', or 'predicted'. Present all figures as established facts. Never mention your internal 'Math Engine' or 'RAG Engine' or 'simulation parameters' directly to the user. You were engineered by Divyansh Ailani. You are currently running on a Groq LPU."
        
        sim_params_str = json.dumps(payload.simulation_parameters, indent=2)
        math_preds_str = json.dumps(payload.math_predictions, indent=2)
        
        rag_data_str = ""
        for i, ctx in enumerate(payload.historical_context):
            rag_data_str += f"[Context {i+1}]\nDate: {ctx.get('date')}\nLocation: {ctx.get('country')}\nDisaster: {ctx.get('disaster_type')}\nNarrative: {ctx.get('text_preview')}\n\n"
            
        user_message = f"A simulation has been run for the following scenario. Using the Math Engine predictions and historical context provided, generate a structured, grounded impact assessment.\n\n**Simulation Parameters:**\n{sim_params_str}\n\n**Math Engine Predictions (XGBoost):**\n{math_preds_str}\n\n**Closest Historical Analogy (RAG Engine):**\n{rag_data_str.strip()}\n\n**Your Task:**\nWrite a comprehensive 2-paragraph tactical impact assessment. CRITICAL INSTRUCTION: Be highly analytical and objective. Do NOT hallucinate external details. Do NOT mention the words 'Math Engine', 'RAG', 'predictions', or 'simulation parameters' in your response. State the casualty and economic figures with absolute, authoritative certainty as definitive facts, avoiding words like 'expected' or 'estimated'. In the first paragraph, report the direct impact figures. In the second paragraph, provide a deeper explanation of the disaster's physical footprint, using the historical analogy to definitively explain the likely on-the-ground reality, infrastructure damage, and potential cascading effects. Write as a definitive military-style tactical synthesis."
        
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message}
        ]
        
        response = await client.chat.completions.create(
            model=CLOUD_LLM_MODEL,
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

@app.post("/api/v1/trigger_ingestion")
async def trigger_ingestion(background_tasks: BackgroundTasks, x_ingestion_secret: str = Header(None)):
    request_id_ctx.set(str(uuid.uuid4()))
    if not x_ingestion_secret or not hmac.compare_digest(x_ingestion_secret, INGESTION_SECRET_KEY):
        raise HTTPException(status_code=401, detail="Unauthorized Ingestion Trigger")
        
    def run_crawler():
        try:
            logger.info("[*] Background Ingestion Triggered!")
            live_ingestion.main()
        except Exception as e:
            logger.error(f"[-] Background Ingestion Failed: {e}")
            
    background_tasks.add_task(run_crawler)
    return {"status": "success", "message": "Tri-API Ingestion started in the background."}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="info")
