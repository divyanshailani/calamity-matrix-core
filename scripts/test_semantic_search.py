import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from src.config import DB_CONFIG

import os
import psycopg2
from sentence_transformers import SentenceTransformer

# Config
DB_PARAMS = DB_CONFIG

def search_disaster(query_text, top_k=3):
    print("==================================================")
    print("  CALAMITY AI: RAG Semantic Search Node           ")
    print("==================================================")
    
    print("[*] Booting Embedding Model (BAAI/bge-large-en-v1.5)...")
    model = SentenceTransformer('BAAI/bge-large-en-v1.5')
    
    # BGE requires the instruction prefix for queries (but not for documents)
    instruction = "Represent this sentence for searching relevant passages: "
    full_query = instruction + query_text
    
    print(f"[*] Generating embedding for query: '{query_text}'")
    query_embedding = model.encode(full_query, normalize_embeddings=True).tolist()
    
    # 1. DB Connection
    try:
        conn = psycopg2.connect(**DB_PARAMS)
        cur = conn.cursor()
    except Exception as e:
        print(f"[-] Database connection failed: {e}")
        return

    # 2. The Search Function
    print("[*] Executing pgvector cosine similarity search (<=>)...")
    
    # In pgvector, <=> computes the cosine distance. Cosine Similarity is (1 - distance).
    query_sql = """
        SELECT date, country, disaster_type, narrative_text, 
               1 - (embedding <=> %s::vector) AS cosine_similarity
        FROM disaster_narratives
        ORDER BY embedding <=> %s::vector
        LIMIT %s;
    """
    
    # Pass the embedding array twice (once for the SELECT projection, once for the ORDER BY)
    cur.execute(query_sql, (query_embedding, query_embedding, top_k))
    results = cur.fetchall()
    
    # 3. Output Formatting
    print("\n==================================================")
    print("  SEMANTIC SEARCH RESULTS")
    print("==================================================\n")
    
    for i, row in enumerate(results, 1):
        date, country, disaster_type, text, similarity = row
        preview = text[:200].replace('\n', ' ') + ('...' if len(text) > 200 else '')
        
        print(f"[{i}] SIMILARITY SCORE: {similarity:.4f}")
        print(f"    Date    : {date}")
        print(f"    Country : {country}")
        print(f"    Type    : {disaster_type}")
        print(f"    Preview : {preview}\n")
        
    cur.close()
    conn.close()

if __name__ == "__main__":
    # 4. The Test Query
    test_query = "Looking for reports detailing structural damage and casualties from a high-magnitude earthquake in Southeast Asia during the 2000s."
    search_disaster(test_query, top_k=3)
