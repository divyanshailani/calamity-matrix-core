# Calamity Matrix Core — ML Pipeline

> Global natural disaster intelligence system. Multi-source structured data pipeline, XGBoost impact regression, semantic RAG over 2,281 historical disaster narratives via pgvector, and Qwen3-8B domain fine-tuning on Modal L40S.

**Stack:** Python · PostgreSQL + pgvector · XGBoost · sentence-transformers (BGE-Large) · Qwen3-8B · LoRA · Modal

---

## What It Does

Two parallel intelligence layers over 25 years of global natural disaster data (2000–2025):

**Math Engine** — XGBoost/LightGBM regression trained on fused structured matrices (USGS seismic, NASA EONET fires/floods/storms, EM-DAT casualties/impacts, Smithsonian volcanism). Outputs base-rate hazard probability and historical impact estimates (casualties, affected population) for a given disaster type and region.

**Narrative Engine** — 2,281 situation reports from HDX/ReliefWeb embedded via `BAAI/bge-large-en-v1.5` into a pgvector database. Semantic search retrieves analogous historical events by meaning, not keyword matching, enabling grounded narrative synthesis when combined with the fine-tuned LLM.

**Fine-tuned LLM** — Qwen3-8B fine-tuned via LoRA on Modal's L40S GPU using domain-specific disaster QA pairs. Synthesizes Math Engine output + RAG-retrieved narratives into structured situation assessments.

---

## Data Sources

| Source | Domain | Records | Notes |
|--------|--------|---------|-------|
| USGS Earthquake Catalog | Seismic | M5.0+ global, 2000–2025 | Monthly chunked fetch, 300 CSV files |
| NASA EONET | Fires / Floods / Storms | 2000–2025 | Spatial event polygons |
| EM-DAT (CRED) | Impacts & Casualties | 2000–2025 | Deaths, affected pop, economic loss |
| Smithsonian GVP | Volcanism | 2000–2025 | Eruption history, VEI index |
| HDX / ReliefWeb | Narrative RAG corpus | 2,281 documents | Situation reports, SITREP narratives |

All data is 2000–2025 only. No live forecasting in v1 — historical risk and impact analysis only.

---

## Architecture

```
Data Sources
  USGS ──────────────────────────────────────────────┐
  NASA EONET ─────────────────────────────────────── ├──► Structured Matrices (CSV)
  EM-DAT ─────────────────────────────────────────── ┤       ↓
  Smithsonian GVP ────────────────────────────────── ┘   XGBoost Math Engine
                                                          (hazard prob + impact regression)
  HDX / ReliefWeb ──► BGE-Large Embeddings ──► pgvector    ↓
                       (1024D vectors)           RAG Engine ──► Qwen3-8B (LoRA) ──► Response
```

---

## Project Structure

```
.
├── scripts/
│   ├── fetch_usgs_earthquakes.py      # USGS seismic, monthly chunked, exponential backoff
│   ├── fetch_nasa_eonet.py            # NASA EONET fires/floods/storms
│   ├── fetch_smithsonian_gvp.py       # Smithsonian volcanism catalog
│   ├── fetch_hdx_text_corpus.py       # HDX narrative corpus download
│   ├── fetch_reliefweb_reports.py     # ReliefWeb API reports (appname required)
│   ├── process_emdat_data.py          # EM-DAT cleaning + normalization
│   ├── process_seismic_data.py        # USGS CSV fusion + feature engineering
│   ├── process_nasa_data.py           # NASA spatial data processing
│   ├── build_domain_matrices.py       # Fuse all sources into unified matrices
│   ├── fuse_rag_corpus.py             # Merge HDX + ReliefWeb into master RAG CSV
│   ├── build_vector_db.py             # Embed corpus → pgvector ingestion (BGE-Large)
│   ├── fix_temporal_keys.py           # Patch event_year via EM-DAT fuzzy join + regex
│   ├── test_semantic_search.py        # RAG retrieval validation
│   └── verify_data_integrity.py       # Data quality checks across all sources
├── src/
│   └── config.py                      # DB config + paths loaded from .env
├── models/                            # Trained model artifacts (gitignored)
├── data/
│   ├── raw/                           # Source data downloads (gitignored)
│   └── processed/                     # Fused matrices + RAG corpus (gitignored)
├── notebooks/
│   └── 01_Calamity_EDA.ipynb          # Exploratory analysis
├── docker-compose.yml                 # pgvector container (reads .env)
├── .env.example                       # Environment variable template
├── requirements.txt
└── ISSUES.md                          # Engineering log
```

---

## Running Locally

**Prerequisites:** Docker, Python 3.11+, 8GB+ RAM for embedding model

```bash
# 1. Clone and install
git clone https://github.com/divyanshailani/calamity-matrix-core
cd calamity-matrix-core
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt

# 2. Set up environment
cp .env.example .env
# Fill in POSTGRES_PASSWORD at minimum

# 3. Start pgvector container
docker-compose up -d

# 4. Fetch data (takes time — USGS alone is 300 monthly chunks)
python3 scripts/fetch_usgs_earthquakes.py
python3 scripts/fetch_nasa_eonet.py
python3 scripts/process_emdat_data.py
python3 scripts/build_domain_matrices.py

# 5. Build RAG corpus and vector DB
python3 scripts/fuse_rag_corpus.py
python3 scripts/build_vector_db.py
python3 scripts/fix_temporal_keys.py

# 6. Verify
python3 scripts/test_semantic_search.py
python3 scripts/verify_data_integrity.py
```

---

## RAG Semantic Search

The vector database contains 2,281 disaster situation report narratives embedded as 1024-dimensional vectors using `BAAI/bge-large-en-v1.5`.

Retrieval uses pgvector's `<=>` cosine distance operator with hybrid filtering on `event_year` and `disaster_type` for temporally-grounded results.

**Verified retrieval example:**

Query: *"structural damage and casualties from a high-magnitude earthquake in Southeast Asia during the 2000s"*

Results (cosine similarity):
- 0.7143 — Naggroe Aceh Darussalam, Indonesia (M7.2, April 2010)
- 0.7045 — Irian Jaya, Indonesia (floods/earthquake, 2024 document referencing 1994 event)
- 0.6989 — Kao-hsiung, Taiwan (M7.1, December 2006)

Retrieval correctly resolved geographic and semantic context without keyword matching.

---

## Upcoming: Math Engine + Fine-tuning (v2)

- **Phase 12:** XGBoost + Optuna on fused structural matrices (hazard probability, impact regression)
- **Phase 13:** Qwen3-8B QLoRA fine-tuning on Modal L40S — domain-specific disaster QA dataset
- **Phase 14:** Synthesizer bridge — Math Engine output + RAG retrieval → LLM grounded response
- **Phase 15:** FastAPI serving layer + frontend

See [`ISSUES.md`](./ISSUES.md) for the full engineering log.
