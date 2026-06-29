import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from src.config import DB_CONFIG

import os
import pandas as pd
import psycopg2
from psycopg2.extras import execute_values
from sentence_transformers import SentenceTransformer

# Config
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
MASTER_CORPUS = os.path.join(SCRIPT_DIR, "..", "data", "processed", "rag_texts", "master_rag_corpus.csv")

DB_PARAMS = DB_CONFIG

def build_db():
    print("==================================================")
    print("  CALAMITY AI: Vector DB Ingestion Node (BGE-Large)")
    print("==================================================")
    
    # 1. DB Connection
    try:
        print(f"[*] Connecting to pgvector container at {DB_PARAMS['host']}:{DB_PARAMS['port']}...")
        conn = psycopg2.connect(**DB_PARAMS)
        cur = conn.cursor()
    except Exception as e:
        print(f"[-] Database connection failed: {e}")
        print("[-] Ensure your docker-compose.yml port mapping is exactly '5433:5432' and the container is running.")
        return

    # Enable pgvector
    cur.execute("CREATE EXTENSION IF NOT EXISTS vector;")
    
    # 2. Schema Definition
    print("[*] Rebuilding 'disaster_narratives' table (1024D Vectors)...")
    cur.execute("DROP TABLE IF EXISTS disaster_narratives;")
    cur.execute("""
        CREATE TABLE disaster_narratives (
            id SERIAL PRIMARY KEY,
            date VARCHAR(255),
            country VARCHAR(255),
            disaster_type VARCHAR(255),
            narrative_text TEXT,
            event_year INT,
            lat FLOAT,
            lng FLOAT,
            embedding VECTOR(1024)
        );
    """)
    conn.commit()

    # 3. Load Data
    if not os.path.exists(MASTER_CORPUS):
        print(f"[-] Master Corpus not found at {MASTER_CORPUS}")
        return
        
    print("[*] Loading Master RAG Corpus...")
    df = pd.read_csv(MASTER_CORPUS)
    df = df.fillna('') # Handle any stray nulls
    
    # 4. Boot Embedding Model
    # BAAI/bge-large-en-v1.5 is a top-tier open-source embedding model generating 1024D vectors
    print("[*] Booting Embedding Model (BAAI/bge-large-en-v1.5) [1024 Dimensions]...")
    model = SentenceTransformer('BAAI/bge-large-en-v1.5')
    
    # 5. Batch Embedding and Ingestion
    print("[*] Generating embeddings and injecting to pgvector...")
    batch_size = 64
    total_records = len(df)
    
    for start_idx in range(0, total_records, batch_size):
        end_idx = min(start_idx + batch_size, total_records)
        batch_df = df.iloc[start_idx:end_idx]
        
        texts = batch_df['narrative_text'].tolist()
        
        # Generate embeddings (normalize to allow cosine similarity via dot product)
        embeddings = model.encode(texts, normalize_embeddings=True)
        
        # Prepare records for execute_values
        records = []
        for i, row in enumerate(batch_df.itertuples()):
            date_str = str(row.date)
            try:
                event_year = int(date_str[:4])
            except ValueError:
                event_year = None
                
            records.append((
                date_str,
                str(row.country),
                str(row.disaster_type),
                str(row.narrative_text),
                event_year,
                embeddings[i].tolist()
            ))
            
        # Batch insert
        insert_query = """
            INSERT INTO disaster_narratives (date, country, disaster_type, narrative_text, event_year, embedding)
            VALUES %s
        """
        execute_values(cur, insert_query, records)
        conn.commit()
        
        print(f"  [+] Injected batch: {end_idx}/{total_records} records...")

    cur.close()
    conn.close()
    
    print("==================================================")
    print("  INGESTION COMPLETE                              ")
    print("  Vector Math Engine is Primed.                   ")
    print("==================================================")

if __name__ == "__main__":
    build_db()
