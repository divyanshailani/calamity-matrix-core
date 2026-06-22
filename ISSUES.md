# Calamity Matrix Core — Engineering Log

Tracks real problems encountered during development, root causes, and how they were resolved. Updated as the project evolves.

---

## 1. USGS API Rate Limits on Bulk Historical Fetch [RESOLVED]

**Issue:** The USGS FDSNWS endpoint returned HTTP 429 and 503 when querying large date ranges (multi-year spans) in a single request. Requests for 2000–2025 in one call consistently timed out or got blocked.

**Solution:** Rewrote fetch to monthly chunks — one request per calendar month (300 total for 2000–2025). Added exponential backoff (5s base, doubles per retry, max 5 attempts) on 429/5xx responses. Added checkpointing — skip months already downloaded. Added 0.5s sleep between clean requests as API courtesy.

---

## 2. HDX Text Corpus — Country and Disaster Type Columns Are API URLs, Not Strings [RESOLVED]

**Issue:** After ingestion, the `country` and `disaster_type` columns in `disaster_narratives` contained raw HDX API reference URLs (e.g., `https://api.reliefweb.int/v2/countries/120`) and numeric IDs (e.g., `4628`) instead of human-readable strings.

**Root Cause:** The HDX CSV export uses API reference objects for taxonomy fields rather than resolved display names. The ingestion script stored raw field values without resolving them.

**Solution:** Noted in `fix_temporal_keys.py` — the EM-DAT fuzzy join skips rows where country field starts with `http`. The RAG engine retrieves by vector similarity over `narrative_text`, not metadata fields, so retrieval quality is unaffected. Metadata resolution (decoding URLs to country names) is tracked as a future cleanup task before the hybrid filter layer is built.

---

## 3. HDX date Column is Digitization Timestamp, Not Event Date [RESOLVED]

**Issue:** The `date` column imported from the HDX CSV reflected when ReliefWeb digitized or indexed the document, not when the disaster event occurred. This caused a 1994 earthquake event to appear in semantic search results despite being filtered to 2000–2025 — the document was digitized in 2024, so it passed the date filter, but its narrative described a 1994 event.

**Root Cause:** ReliefWeb's `date` metadata field is publication/upload date. Historical documents digitized recently inherit current-era timestamps. The RAG engine reads `narrative_text` vectors, not metadata, so it correctly retrieved the document as semantically relevant — the issue was in display and future hybrid filtering, not retrieval logic.

**Solution:** Added `event_year` column to `disaster_narratives` via `scripts/fix_temporal_keys.py`:
- Primary: fuzzy join on `(country, disaster_type)` against EM-DAT master matrix to get ground-truth event year (18 matches)
- Fallback: regex extraction of most-frequent 4-digit year from `narrative_text` (2,255 matches)
- 8 records unresolvable — left as NULL

Coverage: 99.6% of corpus now has a reliable `event_year` for hybrid temporal filtering.

---

## 4. Hardcoded DB Credentials in All Scripts [RESOLVED]

**Issue:** Every script had a hardcoded `DB_PARAMS` dict with `password: "root"`. `docker-compose.yml` had the same plaintext password. Any GitHub push would expose credentials.

**Solution:**
- Added `src/config.py` — loads all config from `.env` via `python-dotenv`. Raises `ValueError` at startup if `POSTGRES_PASSWORD` is missing, fails fast and loudly.
- Updated `docker-compose.yml` to use `${POSTGRES_PASSWORD}` env substitution with `env_file: .env`.
- Added `.env.example` as the committed template.
- Updated `.gitignore` to exclude `.env`, `data/`, `models/`, and all binary model artifacts.

**Note:** Existing scripts still contain the old hardcoded `DB_PARAMS` dicts — these need to be migrated to `from src.config import DB_CONFIG` as each script is touched going forward.

---

## 5. Earthquake Point-Prediction Is Not a Valid ML Target [DESIGN DECISION]

**Issue / Risk:** Initial framing of the math engine included "predicting earthquakes" as a target. Deterministic point prediction of earthquake occurrence (date, location, magnitude) is physically impossible — chaotic stress accumulation in fault systems means no amount of historical data produces a predictive signal for specific events.

**Decision:** The math engine targets are scoped to:
- **Base-rate hazard probability** — Gutenberg-Richter recurrence statistics for a given region and magnitude range (a probabilistic statement, not a point prediction)
- **Historical impact regression** — given a disaster type, region, and severity index, estimate expected casualties/affected population based on historical analogues

This is clearly documented in the README. No model in this project claims to predict *when* an earthquake will occur.

---

## 6. Semantic RAG "Split-Brain" Vulnerability [RESOLVED]

**Issue:** A user could select "Earthquake" in the dropdown but type "Flood" in the query string, causing the RAG retrieval to return flood documents instead of earthquake documents, leading to a split-brain state where the UI claims it's simulating an earthquake but the historical context is about floods.

**Solution:** Intercepted and synthesized a Master Query in `scripts/api_orchestrator.py` that forcefully anchors the embedding vector to the deterministic dropdown parameters: `"{disaster_type} in {country} (Year: {event_year}). Additional Context: {query_text}"`.

---

## 7. Mapbox API Key Dependency on Frontend [RESOLVED]

**Issue:** The geospatial UI relied on `mapbox-gl`, which threw telemetry warnings and blocked map rendering if `NEXT_PUBLIC_MAPBOX_TOKEN` wasn't provided.

**Solution:** Uninstalled `mapbox-gl` and migrated the Next.js frontend to `maplibre-gl` (an open-source fork). Swapped the proprietary map style for CartoDB Positron, which aligns with the new minimal light-theme aesthetic and completely eliminates the API key requirement.

---

## Upcoming Issues / Tracked Items

- [ ] **Country/disaster_type metadata resolution** — decode HDX API URLs to human-readable strings for hybrid filter queries
- [ ] **XGBoost Math Engine** — Phase 12: Optuna tuning per disaster type, separate targets for hazard probability vs impact regression
- [ ] **Qwen3-8B LoRA fine-tuning** — Phase 13: Modal L40S, checkpoint-to-volume preemption recovery, bge-large query prefix at inference
- [ ] **Synthesizer bridge** — Phase 14: Math Engine output → RAG retrieval → LLM synthesis pipeline
- [ ] **requirements.txt** — pin versions once all dependencies are confirmed stable
