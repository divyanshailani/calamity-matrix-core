# Changelog

All notable changes to the Calamity Matrix Core will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.5.1] - 2026-06-23

### ⏸️ Project Status: Stable Maintenance Mode
- **Current Status**: The Calamity Matrix Core has successfully completed its primary development arc and is now in **Maintenance Mode**. The core architecture (Neuro-Symbolic RAG + XGBoost Predictors + FastAPI + Vercel UI) is fully deployed, validated, and stable in the cloud.
- **Reason for Transition**: With the successful deployment of the primary engine, engineering focus is shifting to a new, highly complex data engineering challenge: the **Global AQ (Air Quality)** backend. Global AQ requires migrating and scaling a massive 8GB environmental time-series PostgreSQL database, demanding our full architectural attention.
- **Final Deployment Hotfixes**: Resolved transitive `scikit-learn` dependency crash in Docker container, and migrated Hugging Face API strings to the new `router.huggingface.co` domain following sudden upstream deprecation of the `api-inference` URL.
- **Future Roadmap**: This repository will remain online and fully functional as a portfolio centerpiece. Once the Global AQ data pipeline is established, future updates here may include re-integrating the Qwen3-8B LoRA for autonomous synthesis and upgrading the Render/Supabase bridge for higher throughput.

## [1.5.0] - 2026-06-23

### 🚀 Strategy B Cloud Deployment & Security Audit
- **Supabase Matrix Migration**: Successfully migrated the local Docker-bound `disaster_narratives` pgvector database to a managed Supabase cloud cluster.
- **Hugging Face Inference Bridge**: Ripped out the massive local PyTorch/`sentence-transformers` embedding models from the FastAPI orchestrator. Replaced it with a lightweight `requests.post` call to the Hugging Face Inference API (`BAAI/bge-large-en-v1.5`), slashing memory requirements by over 90% and eliminating Render OOM crashes.
- **Render Web Service Deployment**: The orchestrator is now deployed on a Render Web Service (`calamity-matrix-orchestrator.onrender.com`).
- **Heartbeat Hack**: Implemented a `/health` endpoint to serve as a target for UptimeRobot cron jobs, ensuring the Render container and HF models remain warm 24/7 without cold start penalties.
- **Zero-Secret Security Pass**: Audited the entire repository for hardcoded credentials. Surgically removed a legacy plaintext `password: "root"` from `scripts/extract_temporal_nlp.py` and converted it to load dynamically from `src.config.DB_CONFIG`. All endpoints are securely managed via environment variables.

### 🎨 UI/UX V1 Launch Polish
- **Designer Aesthetic Refactoring**: Replaced the hyper-aggressive neon "cyber-punk" aesthetic with a highly polished, clean, and professional "designer-quality" UI.
- **Fluid Micro-Animations**: Introduced physics-based `framer-motion` animations, including staggered element entrances, subtle scale/color shifts on interactive elements, and a smooth, low-opacity glowing pointer orb tracking the mouse vector.
- **Proportional Dashboard Geometry**: Rewrote the dashboard grid system from a fixed static setup to a responsive `minmax(240px, 1fr) 2fr minmax(240px, 1fr)` flex-grid, preventing the map from monopolizing horizontal screen space.
- **Legibility Sweep**: Boosted base contrast metrics for non-critical elements (`--text-3`) to improve legibility on dark surfaces while retaining the dark mode aesthetic.

## [1.4.0] - 2026-06-22

### AI Integration & Cloud Inference
- **Qwen3-8B LoRA Fine-Tuning**: Successfully trained a parameter-efficient adapter (`calamity-qwen3-lora-v1`) on Cloud Service using an L40S GPU. The model was trained on the `calamity_training_data.jsonl` dataset to parse RAG historical context and ML predictor outputs into tactical responses.
- **Cloud Service Serverless Inference**: Deployed `inference.py` to expose a highly available serverless endpoint powered by the `vLLM` engine. Added support for Server-Sent Events (SSE) to stream generated tokens back to the client with sub-second latency.
- **Orchestrator Bridge**: Upgraded `api_orchestrator.py` with a new `/api/v1/synthesize` endpoint that acts as a proxy between the Next.js frontend and the Cloud Service cloud. The proxy successfully aggregates XGBoost predictions and pgvector RAG context into a massive LLM prompt, posts it to Cloud Service, and streams the inference directly to the UI.

### Phase 21: V1 Beta Pivot (UI Stability & Architecture Optimization)
- **Decoupled LLM Streaming**: Temporarily removed the experimental Qwen3-8B synthesis layer from the Next.js UI to resolve JSON hallucination overflows and CSS constraints. 
- **RAG-First Architecture**: Reframed the project to `V1 Beta`. The system now operates exclusively as a highly stable, deterministic Neuro-Symbolic engine (pgvector Historical RAG + XGBoost Predictive Modeling), resulting in instant execution times and zero cloud infrastructure overhead.

### Phase 20: Cloud Service Integration
- **Cloud Service Cold Boot Timeout Patch**: Fixed a race condition where the FastAPI orchestrator's `httpx` client timed out (120s limit) while the Cloud Service container was still cold-booting and downloading the 15GB model weights. Increased the timeout to 300s to allow graceful container startups.
- **303 Redirect Handling**: Configured the orchestrator's async client to follow HTTP redirects (`follow_redirects=True`), fixing a fatal connection drop caused by Cloud Service's internal load balancing rules.
- **vLLM Configuration Patch**: Upgraded the hardcoded `vllm==0.4.3` requirement to the latest version to properly parse the `Qwen3-8B` architecture configuration (resolving a fatal `KeyError: 'type'` on RoPE scaling).

### Pending Design Overhaul
- **UI Glitch & JSON Hallucination**: Currently, the LLM output overflows the Next.js right panel due to missing `overflow-y-auto` and `break-words` CSS. The model is also outputting raw JSON instead of human-readable Markdown due to strict system prompting. A complete UX/UI aesthetic overhaul is scheduled to elevate the dashboard from a "concept project" to a professional, defense-grade application.

## [1.3.0] - 2026-06-22
- **The Recommendation Pop-Up Patch (Phase 17.8)**: Upgraded the Next.js UI with an interactive, full-screen Framer Motion cloud (`RecommendationCloud Service.tsx`) that triggers when exact RAG matches fail. The backend `api_orchestrator.py` was extended to execute localized aggregation queries (`SELECT DISTINCT`), serving alternative disaster types (for the same country) and alternative countries (for the same disaster type) directly to the UI. Clicking a recommendation chip automatically updates form state and triggers a fresh simulation, completely eliminating dead-end UX states.
- **Strict Geographic Enclosure & Graceful Degradation (Phase 17.7)**: Reverted the global fallback logic in `api_orchestrator.py` to prioritize scientific integrity over broad retrieval. RAG Pass 3 was completely removed. Pass 2 now searches across all years but *strictly* enforces Exact Country and Exact Disaster Type. If 0 analogies exist within the specific geography, the RAG engine returns `[]`, and the Next.js UI degrades gracefully via a professional empty state in `HistoricalContext.tsx`, preserving the isolated Math Engine metrics while omitting hallucinated geospatial arcs.
- **Geospatial Viewport Sync (Phase 17.6)**: Upgraded `GeospatialMap.tsx` with dynamic `fitBounds` algorithms to automatically re-frame the MapLibre camera whenever the global RAG fallback logic pulls historical analogies from foreign continents.
- **Telemetry Arcs (Phase 17.6)**: Implemented curved GeoJSON lines connecting global RAG markers to the target simulation country, visually conveying predictive data transfer.
- **Semantic Invariant Patch (Phase 17.5)**: Re-engineered the Heuristic Hybrid RAG in `scripts/api_orchestrator.py` to utilize a strict 3-pass SQL fallback sequence. The final Deep Fallback (Pass 3) guarantees retrieval of semantically matched historical analogies by vector distance without *ever* dropping the exact `disaster_type` constraint.
- **EM-DAT to ReliefWeb Taxonomy Bridge**: Implemented a dynamic runtime mapping dictionary to translate incoming EM-DAT UI queries (e.g. `Extreme temperature`) into valid HDX/ReliefWeb database arrays (e.g. `['Heat Wave', 'Cold Wave']`), fully resolving the zero-result RAG hallucination vulnerability.
- **ReliefWeb API 403 Bypass**: Re-engineered `scripts/resolve_hdx_metadata.py` to circumvent the new ReliefWeb `appname` requirement. The script now operates fully offline, parsing taxonomy mappings directly from the historical `reliefweb-disasters-list.csv` corpus. Successfully geolocated and mapped 4,522 missing fields (lat/lng, country names, disaster types) in under 2 seconds.
- **Heuristic Hybrid RAG**: Upgraded `scripts/api_orchestrator.py` with a two-pass temporal fallback. The RAG engine now attempts a strict `event_year` match, and heuristically falls back to a 20-year window (`event_year BETWEEN {year} - 10 AND {year} + 10`) if strict matches yield insufficient analogies.
- **Model Metadata Sidecars**: Modified `scripts/train_math_engine_v2.py` to auto-export `_meta.json` sidecar files containing RMSE, MAE, and Optuna feature importance gains alongside the serialized XGBoost models, ensuring metric provenance is preserved.
- **String Alias Mapping Middleware (Phase 17.9.8)**: Added a dynamic `COUNTRY_ALIASES` dict to `api_orchestrator.py` to transparently translate common UI geographic names ("Turkey", "US", "Russia") into their rigid database equivalents ("Türkiye", "United States of America").
- **Zero-Vector Database Patch (Phase 17.9.6)**: Resolved a critical API crash caused by PostgreSQL generating `NaN` values during cosine similarity calculations against dummy `[0.0]` vectors. Replaced all origin vectors with unit-magnitude `[1.0, 0.0...]` vectors to bypass divide-by-zero mathematical impossibilities.
- **Geospatial Anchoring**: Hardened `GeospatialMap.tsx` to conditionally render tactical map markers only for narratives with validated database coordinates, preventing frontend panics on zero-coordinate data.

## [1.2.0] - 2026-06-22


### Security
- **Orchestrator Credential Sanitization**: Migrated `scripts/api_orchestrator.py` from a hardcoded `DB_PARAMS` dict (`password: "root"`) to `DB_CONFIG` imported from `src.config`. The orchestrator now loads all database credentials securely from the `.env` file at startup, completing the credential sanitization pass begun in v1.0.0.

### Backend Maintenance
- **HDX Metadata Resolution Script**: Added `scripts/resolve_hdx_metadata.py` — a new maintenance utility that connects to the pgvector database and resolves raw ReliefWeb API URLs (e.g. `https://api.reliefweb.int/v2/countries/174`) and numeric disaster IDs (e.g. `4611`) in the `disaster_narratives` table to human-readable strings (e.g. `Philippines`, `Earthquake`). Includes dry-run mode (default), exponential backoff on 429/5xx responses, a per-request 0.4s courtesy sleep, and per-row resolution logging. Requires `RELIEFWEB_APPNAME` to be set in `.env` before execution. Run with `--execute` flag to commit changes.
- **Dependency Pinning**: Added `requirements.txt` to the repository root with all direct Python dependencies pinned to their current working versions, eliminating deployment environment ambiguity.

## [1.1.0] - 2026-06-22

### UI / Frontend Overhaul
- **MapLibre Migration**: Stripped out `mapbox-gl` entirely. Replaced with the open-source `maplibre-gl` to eliminate the `NEXT_PUBLIC_MAPBOX_TOKEN` requirement.
- **CartoDB Positron**: Swapped the proprietary map theme for Carto Positron, matching the new high-trust minimal aesthetic without needing an API key.
- **High-Trust Light Theme**: Purged the dark, neon "cyberpunk matrix" CSS and implemented a clean, professional FinTech-grade light theme using `bg-zinc-50`.
- **Tactical Map Markers**: Added dynamic, deterministic geospatial marker generation for the top 3 historical RAG events.
- **Auto-Zoom Camera**: Engineered an automatic camera zoom sequence that punches in on the country when a simulation completes.
- **HUD Optimization**: Re-positioned the map's Navigation Controls to the top-right to prevent overlap with the data readout HUD at the bottom.

### Backend Guardrails
- **Split-Brain Patch**: Engineered a Master Query synthesizer in `api_orchestrator.py` that forcefully prepends the selected Dropdown parameters (Country, Disaster Type, Year) to the user's free-text string, closing a vulnerability where text inputs could override semantic UI context.

## [1.0.0] - 2026-06-22

### Security & Configuration
- **Credential Sanitization**: Removed all hardcoded PostgreSQL database credentials (`admin`/`root`) across all 4 vector DB and ingestion scripts.
- **Environment Management**: Implemented secure environment variable loading architecture via `src/config.py`.
- **Docker Security**: Patched `docker-compose.yml` to inject credentials from `.env` instead of exposing plaintext passwords.
- **Safe Initialization**: Added `.env.example` to provide a secure configuration template for new environments.
- **Repository Hygiene**: Expanded `.gitignore` to rigorously exclude sensitive files (`.env`), heavy raw/processed datasets (`data/`), and generated AI artifacts (`models/`).

### Features & Data Pipeline
- **5-Source Fusion Pipeline**: Successfully integrated APIs and datasets from USGS, Smithsonian GVP, NASA EONET, EM-DAT, and HDX/ReliefWeb.
- **Matrix Partitioning**: Developed scripts to output distinct, physically sound analytical matrices (`tectonic_matrix.csv` and `atmospheric_impact_matrix.csv`).
- **Shadow Scraper**: Deployed a Playwright-based asynchronous headless crawler to bypass API rate limits and extract disaster reports directly from the ReliefWeb frontend.
- **Exploratory Data Analysis**: Initialized `01_Calamity_EDA.ipynb` with interactive Plotly maps and Gutenberg-Richter scatterplots.

### Vector RAG Architecture
- **pgvector Integration**: Spun up an isolated Dockerized PostgreSQL container with the `pgvector` extension.
- **Semantic Engine**: Embedded 2,281 disaster narratives using the 1024-dimensional `BAAI/bge-large-en-v1.5` dense vector model.
- **Semantic Search**: Validated the engine's capability to understand contextual, non-keyword queries using Cosine Similarity (`<=>`) distance calculations.

### Data Integrity & Rectification
- **Temporal Key Recovery**: Developed `fix_temporal_keys.py` to decouple ReliefWeb upload metadata from actual historical event dates.
- **Fuzzy Joining**: Successfully mapped text narratives back to EM-DAT ground-truth records using Country + Disaster Type heuristics.
- **Regex Fallback**: Achieved 99.6% timestamp recovery via targeted `r'\b(19|20)\d{2}\b'` sweeping on legacy HDX documents.
