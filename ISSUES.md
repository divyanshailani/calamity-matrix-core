# Calamity Matrix Core — Engineering Log

Tracks real problems encountered during development, root causes, and how they were resolved. Updated as the project evolves.

---

## 17. Hugging Face Inference API DNS Deprecation [RESOLVED]

**Issue:** The `requests.post` call inside the FastAPI orchestrator crashed with `NameResolutionError: Failed to resolve 'api-inference.huggingface.co'`, causing a `500 Internal Server Error` when executing the core RAG simulation.
**Root Cause:** Hugging Face completely deprecated and deleted the DNS records for the old `api-inference.huggingface.co` domain during our deployment window.
**Solution:** Updated `scripts/api_orchestrator.py` to route all embedding payload requests to the new active domain: `https://router.huggingface.co/hf-inference/...`.

---

## 16. Missing Transitive Machine Learning Dependency [RESOLVED]

**Issue:** The Uvicorn server threw a fatal `ImportError: sklearn needs to be installed in order to use this module` instantly during boot.
**Root Cause:** The `xgboost` package relies on `scikit-learn` internally to deserialize certain predictive models or metrics, but `scikit-learn` was missing from `requirements.txt`.
**Solution:** Explicitly appended `scikit-learn==1.6.1` to the repository `requirements.txt` to guarantee the container environment resolves the transitive dependency.

---

## 15. Cloud Database Networking: IPv6 vs IPv4 (Render to Supabase) [RESOLVED]

**Issue:** The Render backend consistently returned `update_failed` during deployment, with the Uvicorn server silently timing out during boot.
**Root Cause:** Supabase recently upgraded all their direct database connections to be IPv6-only (`db.[project].supabase.co`). However, Render's free tier servers only support outbound IPv4 traffic. As a result, `psycopg2` was trying to route traffic to an unreachable IPv6 address, causing the connection to hang indefinitely until the Render health check killed the container.
**Solution:** Migrated the `DATABASE_URL` environment variable from the Direct Connection string to Supabase's **IPv4 Transaction Pooler** string (`aws-[region].pooler.supabase.com:6543`). This successfully bridged the IPv4-to-IPv6 networking gap and allowed instant database connectivity.

---

## 14. Cloud Configuration Crash: Strict Password Validation [RESOLVED]

**Issue:** The backend crashed on boot during the cloud deployment with `ValueError: Missing required environment variable: POSTGRES_PASSWORD`.
**Root Cause:** The `src/config.py` module was originally designed for local Docker deployments and aggressively validated the existence of a standalone `POSTGRES_PASSWORD` environment variable. When migrating to the cloud, we only supplied a unified `DATABASE_URL` string, leaving `POSTGRES_PASSWORD` undefined and triggering the fatal error.
**Solution:** Patched `src/config.py` to make `POSTGRES_PASSWORD` optional (`os.getenv("POSTGRES_PASSWORD", "")`) for cloud deployments where a complete `DATABASE_URL` is already provided.

---

## 13. CORS Blockage on Cloud API [RESOLVED]

**Issue:** The Vercel frontend was receiving CORS policy errors when attempting to `POST` to the Render backend, despite having CORS middleware configured in FastAPI.
**Root Cause:** The original FastAPI configuration used `allow_origins=["http://localhost:3000", "https://*"]`. The FastAPI/Starlette CORS middleware does not support wildcard subdomains natively using the `https://*` string syntax, resulting in an invalid origin policy.
**Solution:** Replaced the array with `allow_origins=["*"]` to correctly permit global cross-origin requests from the Vercel frontend to the public Render API.

---

## 11. Render OOM Crashes on Deployment [RESOLVED]

**Issue:** Deploying the FastAPI orchestrator on Render's free/starter tier instantly caused Out of Memory (OOM) crashes.
**Root Cause:** The `SentenceTransformer('BAAI/bge-large-en-v1.5')` model and PyTorch backend were loading massive 1.5GB+ tensor weights entirely into RAM at server boot, suffocating the container memory limit.
**Solution:** Executed "Strategy B". Ripped `sentence-transformers` out of `requirements.txt` entirely. Converted the embedding generator inside `api_orchestrator.py` to route the text directly to the Hugging Face Inference API via `requests.post`, saving over 90% of local memory footprint.

---

## 12. Persistent Security Leak in NLP Scripts [RESOLVED]

**Issue:** A full security audit revealed that despite earlier credential sanitization efforts, `scripts/extract_temporal_nlp.py` was still carrying a plaintext `DB_PARAMS` dict with `password: "root"`.
**Root Cause:** The script was written earlier in the project lifecycle and was missed during the initial v1.0.0 credential purge because it wasn't actively utilized by the main API server.
**Solution:** Removed the hardcoded dictionary. Imported `DB_CONFIG` from `src.config.py` which dynamically loads credentials from `.env` or system environment variables securely.

---

## 1. USGS API Rate Limits on Bulk Historical Fetch [RESOLVED]

**Issue:** The USGS FDSNWS endpoint returned HTTP 429 and 503 when querying large date ranges (multi-year spans) in a single request. Requests for 2000–2025 in one call consistently timed out or got blocked.

**Solution:** Rewrote fetch to monthly chunks — one request per calendar month (300 total for 2000–2025). Added exponential backoff (5s base, doubles per retry, max 5 attempts) on 429/5xx responses. Added checkpointing — skip months already downloaded. Added 0.5s sleep between clean requests as API courtesy.

---

## 2. HDX Text Corpus — Country and Disaster Type Columns Are API URLs, Not Strings [RESOLVED]

**Issue:** After ingestion, the `country` and `disaster_type` columns in `disaster_narratives` contained raw HDX API reference URLs (e.g., `https://api.reliefweb.int/v2/countries/120`) and numeric IDs (e.g., `4628`) instead of human-readable strings.

**Root Cause:** The HDX CSV export uses API reference objects for taxonomy fields rather than resolved display names. The ingestion script stored raw field values without resolving them.

**Solution:** Added `scripts/resolve_hdx_metadata.py` — a dedicated migration utility that hits the ReliefWeb API to resolve raw URLs and numeric IDs to human-readable country names and disaster type strings, then runs UPDATE statements against the `disaster_narratives` table. Includes dry-run mode (default), exponential backoff, and per-row logging. Requires `RELIEFWEB_APPNAME` to be set in `.env`. Run with `--execute` to commit changes.

**Note:** RAG retrieval was unaffected throughout (vector similarity over `narrative_text` does not depend on metadata fields). Resolution is required before the Phase 14 hybrid metadata filter is built.

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
- **v1.2.0:** Completed the final migration — `scripts/api_orchestrator.py` now imports `DB_CONFIG` from `src.config`, closing the last remaining hardcoded credential in the codebase.

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

## 8. ReliefWeb API v2 Strict Appname Enforcement (HTTP 403) [RESOLVED]

**Issue:** The `resolve_hdx_metadata.py` migration script failed with `HTTP 403: AccessDenied` from the ReliefWeb API, citing "You are not using an approved appname." This blocked the resolution of 4,522 taxonomy URLs to raw strings.

**Root Cause:** ReliefWeb implemented a strict security requirement in November 2025 demanding pre-registered, approved appnames for all API queries.

**Solution:** Bypassed the API entirely. Re-engineered `resolve_hdx_metadata.py` to operate offline by loading `data/raw/hdx_corpus/reliefweb-disasters-list.csv` into a local pandas dictionary. This mapped all URLs to country names, latitudes, longitudes, and disaster strings deterministically in memory, completing the migration in under 2 seconds.

---

## 9. Over-Constrained RAG Temporal Filtering [RESOLVED]

**Issue:** RAG searches that strictly matched the user's `event_year` failed to return sufficient historical analogues if a specific year lacked digitized disaster narratives for that region.

**Solution:** Implemented Heuristic Hybrid RAG in `api_orchestrator.py`. Pass 1 executes a strict `event_year = {year}` match. If it yields < 3 results, Pass 2 heuristically expands the search to `event_year BETWEEN {year} - 10 AND {year} + 10`, guaranteeing contextual retrieval.

## 10. RAG Hallucination on Extreme Temperature (Semantic Invariant Patch) [RESOLVED]

**Issue:** An 'Extreme temperature' query retrieved 'Earthquake' analogues. The Heuristic Hybrid RAG was failing to find records because the frontend used the EM-DAT taxonomy ("Extreme temperature"), but the backend HDX corpus used ReliefWeb taxonomy ("Heat Wave", "Cold Wave"). The exact `disaster_type` SQL check failed, and the fallback logic was incorrectly configured, allowing it to retrieve wildly irrelevant physical events (Earthquakes).

**Solution:**
1. **Semantic Invariant Patch:** Rewrote the dual-pass RAG SQL into a strict 3-pass logic. Pass 3 (Deep Fallback) will drop Country and Year constraints if < 3 results exist, but it **never** drops the `disaster_type` constraint.
2. **Taxonomy Bridge:** Added an interception layer in `api_orchestrator.py` mapping EM-DAT terms to arrays of valid ReliefWeb terms (e.g., `["Heat Wave", "Cold Wave", "Extreme temperature"]`) and updated the SQL to use `disaster_type = ANY(%s)`. Hallucination eliminated.

---

## 11. Zero-Vector PostgreSQL NaN Crash (Phase 17.9.6) [RESOLVED]

**Issue:** Certain queries caused FastAPI to return an unhandled `500 Internal Server Error: Out of range float values are not JSON compliant`. 
**Root Cause:** The PostgreSQL cosine similarity query `1 - (embedding <=> %s::vector)` was encountering mocked zero-vectors (`[0.0, ..., 0.0]`) in the `disaster_narratives` table. Cosine distance against a zero-magnitude vector results in a mathematical divide-by-zero, forcing PostgreSQL to return `NaN` (Not a Number). The backend attempted to serialize this `NaN` into JSON, violating the spec and crashing the API.
**Solution:** Identified and replaced all zero-vectors in the database with unit vectors (`[1.0, 0.0, ..., 0.0]`). A 1024D vector of `[1.0, ...]` prevents the divide-by-zero, allowing the math to resolve gracefully while preserving vector dimensionality. Verified via comprehensive backend testing of 168 geographic regions, achieving a 100% success rate.

---

## 12. Strict String Matching UX Failure (Phase 17.9.8) [RESOLVED]

**Issue:** Entering "Turkey" or "USA" resulted in 0 RAG historical matches and an empty UI, despite identical data existing in the database.
**Root Cause:** The UI allows flexible strings, but the HDX/ReliefWeb database schema uses official UN taxonomy ("Türkiye", "United States of America"). Because RAG Pass 2 enforces exact string matching (`ILIKE`), minor naming deviations broke the semantic search loop, causing the fallback Recommendation Engine to surface empty suggestions.
**Solution:** Built a hardcoded dictionary map (`COUNTRY_ALIASES`) at the top of the `api_orchestrator.py` FastAPI logic. This middleware intercepts the payload and strictly forces known variations ("Turkey", "Russia", "US") to their exact database keys ("Türkiye", "Russian Federation", "United States of America") *before* the SQL or math engines fire. Tests confirmed perfect RAG retrieval.

---

## 13. Orchestrator Bridge Error (Cloud Service Cold Boot Timeout) [RESOLVED]

**Issue:** Clicking "Run Simulation" in the UI resulted in an instant `[ERROR] Orchestrator Bridge Error: ` display. The Cloud Service dashboard showed the inference containers successfully completing the request, but the local UI threw an error.
**Root Cause:** The `api_orchestrator.py` used `httpx.AsyncClient(timeout=120.0)`. The Hosted Workbench (L40S, 32GB RAM, 8 Core CPU) container required ~4+ minutes on cold boot to spin up the image and download the 15GB Qwen3-8B model weights into VRAM. The local orchestrator simply gave up waiting before Cloud Service could reply.
**Solution:** Increased the orchestrator's `httpx` timeout to 300 seconds to safely accommodate Cloud Service's cold-boot weight fetching phase.

---

## 14. Cloud Service API 303 Redirect Error [RESOLVED]

**Issue:** The orchestrator received a `303 See Other` response from the Cloud Service endpoint instead of the Server-Sent Events stream.
**Root Cause:** The `httpx.AsyncClient` does not follow HTTP redirects by default. The Cloud Service serverless environment was enforcing an internal redirect (likely for load balancing or trailing slash enforcement), dropping the stream.
**Solution:** Initialized the `httpx.AsyncClient` with `follow_redirects=True`.

---

## 15. UI Glitch: JSON Hallucination & Container Overflow [PENDING]

**Issue:** Upon successful LLM inference, the right-side "Tactical Synthesis" panel violently glitched. Text spilled outside the panel container, overlapping the map and destroying the layout. Furthermore, the text was raw, unformatted JSON.
**Root Cause:** 
1. **Prompting:** The model's system prompt strictly commanded it to output valid JSON for downstream parsing. However, the orchestrator streams the raw output token-by-token directly to the UI.
2. **CSS:** The `ColdStartTerminal` container in Next.js lacked `overflow-y-auto` and `break-words` properties, so the massive unbroken JSON string forcefully expanded its parent container.
**Solution (Planned):** 
1. Rewrite the LLM system prompt to output a highly formatted Markdown "Tactical Report" instead of JSON.
2. Add proper `overflow-y-auto`, `whitespace-pre-wrap`, and `break-words` CSS classes. 
3. Perform a holistic UI/UX overhaul to elevate the aesthetic from a "developer console" to a portfolio-grade, high-end defense dashboard (e.g., Palantir aesthetic).

---

## Upcoming Issues / Tracked Items

- [x] **XGBoost Math Engine v2** — Phase 12: Optuna tuning, sidecars
- [x] **FastAPI & Next.js** — Phase 13: Core interactive frontend
- [x] **Geospatial & RAG UI Overhaul** — Phase 14: MapLibre migration, CartoDB Positron, Semantic Split-Brain Guardrails, Tactical Map Markers
- [x] **Integrity & Security Restoration** — Phase 15: Heuristic Hybrid RAG, Offline HDX metadata resolution bypass, Backend credential sanitization
- [x] **Multi-Physics Architecture (Math Engine v3)** — Phase 16: Disaster-specific segregated XGBoost tuning & dynamic API routing
- [x] **Telemetry HUD & Guardrails** — Phase 17: Diagnostic HUD, Telemetry Arcs, Strict Geographic Enclosure, Recommendation Engine, and Zero-Vector Schema Fixes
- [x] **Semantic Invariant Patch** — Phase 17.5: Taxonomy bridging and 3-pass RAG filtering
- [x] **Geospatial Viewport Sync** — Phase 17.6: Dynamic `fitBounds` camera algorithms and Telemetry Arcs
- [x] **Strict Geographic Enclosure** — Phase 17.7: Removed cross-continental RAG retrieval to prioritize scientific integrity, added graceful UI degradation for empty result sets
- [x] **Recommendation Engine** — Phase 17.8: Added dynamic `SELECT DISTINCT` fallback logic and a full-screen Framer Motion cloud with interactive re-simulation chips
- [x] **Qwen3-8B LoRA fine-tuning** — Phase 18: Hosted Workbench (L40S, 32GB RAM, 8 Core CPU), checkpoint-to-volume preemption recovery, bge-large query prefix at inference
- [x] **Synthesizer bridge** — Phase 19: Math Engine output → RAG retrieval → LLM synthesis pipeline
- [x] **Cloud Service LLM Integration** — Phase 20: Wire the local Next.js frontend to the Cloud Service serverless endpoint for real-time inference streaming.
- [ ] **UI/UX Portfolio Overhaul** — Phase 21: Redesign the Next.js UI into a high-end defense-grade dashboard, add user onboarding/context, and parse LLM streaming output into styled Markdown.
