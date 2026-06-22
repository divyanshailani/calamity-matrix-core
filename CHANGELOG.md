# Changelog

All notable changes to the Calamity Matrix Core will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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
