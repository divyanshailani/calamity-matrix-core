import os
from dotenv import load_dotenv

load_dotenv()

def _require(key):
    val = os.getenv(key)
    if not val:
        raise ValueError(
            f"Missing required environment variable: {key}\n"
            f"Copy .env.example to .env and fill in your values."
        )
    return val

DB_CONFIG = {
    "host":     os.getenv("POSTGRES_HOST", "localhost"),
    "port":     os.getenv("POSTGRES_PORT", "5433"),
    "user":     os.getenv("POSTGRES_USER", "admin"),
    "password": os.getenv("POSTGRES_PASSWORD", ""),
    "dbname":   os.getenv("POSTGRES_DB", "calamity_rag"),
}

DATABASE_URL = os.getenv("DATABASE_URL")
HF_TOKEN = os.getenv("HF_TOKEN")
EMBEDDING_MODEL    = os.getenv("EMBEDDING_MODEL", "BAAI/bge-large-en-v1.5")
RELIEFWEB_APPNAME  = os.getenv("RELIEFWEB_APPNAME", "")
MODAL_TOKEN_ID     = os.getenv("MODAL_TOKEN_ID", "")
MODAL_TOKEN_SECRET = os.getenv("MODAL_TOKEN_SECRET", "")
CLOUD_LLM_ENDPOINT = os.getenv("CLOUD_LLM_ENDPOINT", "")
INGESTION_SECRET_KEY = _require("INGESTION_SECRET_KEY")

BASE_DIR      = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR      = os.path.join(BASE_DIR, "data")
RAW_DIR       = os.path.join(DATA_DIR, "raw")
PROCESSED_DIR = os.path.join(DATA_DIR, "processed")
RAG_DIR       = os.path.join(PROCESSED_DIR, "rag_texts")
MODELS_DIR    = os.path.join(BASE_DIR, "models")
