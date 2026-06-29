# Calamity Matrix Core - Project Memory & Rules

## Project Overview
Calamity Matrix Core is a global natural disaster intelligence system (2000-2025) utilizing a "First-Principles" engineering approach. It simulates and analyzes physical disaster events, predicts human impact, and grounds predictions in actual historical narratives.
Current Phase: V2 Active Development (LLM Synthesis layer integrated via Serverless Cloud GPU with SSE streaming).

## Tech Stack
- **Frontend (Vercel):** Next.js (calamity-ui), MapLibre GL, CartoDB Positron maps
- **Backend (DigitalOcean):** FastAPI (api_orchestrator.py), Nginx Reverse Proxy
- **Database (Azure VM - Bare Metal):** PostgreSQL 18 + pgvector (compiled from `master` branch)
- **ML (Predictive):** XGBoost (isolated multi-physics models), Optuna
- **ML (Embeddings):** BAAI/bge-large-en-v1.5
- **ML (Generative):** Qwen-3 8B LoRA. Fine-tuned on an enterprise Hosted Workbench (L40S GPU, 32GB RAM, 8-Core CPU). Inference deployed on a Serverless Cloud Platform (Modal A10G GPU, 24GB VRAM) running vLLM.

## Core Architectures
- **Math Engine v3 (Multi-Physics):** Isolated XGBoost regression models for different disaster types. Inputs are fused structured matrices. Output requires an inverse `log1p` transform (`expm1`).
- **Narrative Engine (Semantic RAG):** 2,281 SITREPs from HDX/ReliefWeb. 1024-d embeddings using pgvector cosine distance (`<=>`), with multi-pass strict/fallback SQL filtering in `api_orchestrator.py`.
- **LLM Synthesis Layer:** Qwen-3 8B model with a "Simulation Architect" persona (via `scripts/inject_identity.py` and System Prompt hardcoding).

## Action Items & Incident Log

### [RESOLVED] Issue #1: LLM Merge & VRAM Exhaustion
The Qwen-3 8B model integration into `api_orchestrator.py` was previously halted due to catastrophic failures:
1. **VRAM Exhaustion (Container Sprawl):** Resolved by deploying a serverless A10G (24GB VRAM) cloud endpoint running vLLM with a 60-second idle container timeout.
2. **JSON Parsing Crashes:** Resolved by bypassing JSON entirely. The FastAPI `/api/v1/ask_ai` endpoint now uses Server-Sent Events (`StreamingResponse`) to stream raw text directly to the frontend.
3. **Hallucinated Prompts:** Resolved by enforcing the exact `calamity_training_data.jsonl` string structure in the orchestrator payload.

### [RESOLVED] Phase 21: UI/UX Portfolio Overhaul (Part 1)
- **Full Column 3D Flip:** Replaced the global `ColdStartTerminal` chatbox with a full-column CSS 3D flip architecture on the right-hand side.
- **RAG Front Face:** The front face (`HistoricalContext`) displays the RAG results. Each card has an "Ask AI" button that flips the entire column.
- **AI Chat Back Face:** The back face (`CalamityAiChat`) features a minimalist, classic dark-mode chat interface (similar to ChatGPT) with a 5-minute sleep counter that tracks the idle status of the Serverless A10G GPU.

### [RESOLVED] Issue #2: AI Synthesis Ignoring Custom Chat Queries (And Subsequent Removal)
- **The Bug:** The model ignored custom user queries ("who are you?") sent from the new chat UI, outputting the standard disaster synthesis script instead.
- **The Fix:** We originally created a separate, dedicated `/api/v1/chat` endpoint to bypass the rigid RAG payload. However, to permanently eradicate prompt injection and pre-trained identity bleed, we **completely removed the conversational input box and the global "Ask AI" button** from the UI. The architecture is now strictly locked to Contextual RAG Synthesis.

### [RESOLVED] Issue #3: Cascading Network Timeouts, Cold Start Latency & Modal 300s Limit
- **The Bug:** The initial chat request failed repeatedly with `[Error: Failed to fetch]` on the frontend and `HTTP 500` on the backend. This was caused by the Modal Serverless A10G taking ~260 seconds to download 15GB of model weights, hitting Modal's default 300s `startup_timeout`. Later, even with caching, Modal's hard 300-second *function* timeout was brutally killing the container during model initialization exactly at the 5-minute mark, doubling the response time. Furthermore, vLLM's auto-prefetching was disabled because Modal's 9P filesystem isn't recognized as a standard network drive, slowing volume loading to 4.20s/iteration.
- **The Fix:**
  1. **Nginx & Modal Timeouts:** Increased `proxy_read_timeout` in DigitalOcean Nginx from 300s to 900s, and Modal `startup_timeout` to 900s. We also added `timeout=900` to the top-level `@app.function` to prevent Modal from interrupting the initialization.
  2. **HuggingFace Persistent Caching & High-Performance Xet:** Modified `modal_inference.py` to point `HF_HOME` directly to the `calamity-model-cache` persistent Volume, completely bypassing the 15GB model download on subsequent cold starts. We also enabled `HF_XET_HIGH_PERFORMANCE: "1"` for maximum network speed.
  3. **vLLM Safetensors Prefetch Hack:** We injected `--safetensors-load-strategy prefetch` into the vLLM arguments to force aggressive streaming from the Modal Volume, dropping the init engine phase down to ~130 seconds.
  4. **UI Polish:** Added an animated pulsing text warning in `CalamityAiChat` ("Waking up Serverless A10G GPU...") that appears while waiting for the streaming response, keeping users informed during cold starts.

### [RESOLVED] Issue #4: Identity Hallucination (Pre-trained Weight Bleed)
- **The Bug:** When asked "who created you?", the fine-tuned LoRA model hallucinated ("Mathew J. Turek Lab"). The `calamity_training_data.jsonl` identity injection script only contained specific phrasing ("Who built you?"). Because the user's query didn't match perfectly, the LoRA weights were bypassed, and the Qwen-3 base model's pre-trained weights bled through.
- **The Fix:** Shifted identity anchoring from pure LoRA reliance to System Prompt hardcoding. We modified `api_orchestrator.py` on the DigitalOcean server to append explicit identity parameters to the system prompt (`"You were engineered by Divyansh Ailani... running on a Modal Serverless GPU."`). This guarantees 100% adherence to the persona regardless of query phrasing.

### [RESOLVED] Phase 22: Calamity Matrix V3 Data Layer Upgrade
- **Azure VM Migration:** Abandoned Supabase due to scale/cost constraints. Automated a bare-metal provisioning on an Azure VM (Ubuntu, 2vCPU, 1GB RAM) with a 4GB Swap Shield, Thermodynamics Tuning (`shared_buffers=256MB`), and a custom `pgvector` compilation to resolve the `vacuum_delay_point` signature issue in PostgreSQL 18.
- **RAG Date Quarantine:** Injected a strict `AND event_year >= 2000` SQL clause into the `api_orchestrator.py` to prevent pre-2000 historical bleed from the LLM.
- **Hybrid Search Time-Decay:** Bypassed complex database RPCs by writing the Time-Decay Math directly into the orchestrator's SQL. Tuned the decay constant down to 0.005 to prevent aggressive rank degradation for older events: `ORDER BY (1 - (embedding <=> %s::vector)) - (0.005 * ABS(event_year - TargetYear)) DESC`. This enforces that recent, highly relevant events rank at the top without destroying perfect historical analogies.
- **Autonomous Crawler:** Built `live_ingestion.py` and a weekly GitHub Actions workflow (`live_ingestion.yml`) to automatically query the ReliefWeb API for 7-day old events, generate `BAAI/bge-large-en-v1.5` embeddings, and inject them into the Azure database without human intervention.
- **Serverless GitHub Actions Proxy:** To prevent exposing the raw Azure database credentials in GitHub and heavy ML compute overhead, we engineered a DigitalOcean FastAPI proxy endpoint (`POST /api/v1/trigger_ingestion`) secured via a custom `X-Ingestion-Secret` header. GitHub Actions simply sends a `curl` request every Sunday at midnight, offloading the compute entirely to the Droplet via Starlette's `BackgroundTasks`.

### [RESOLVED] Issue #5: Deployment Pipeline Cascading Failures
- **The Bug:** After merging the Tri-API autonomous crawler, the deployment pipeline crashed due to three cascading issues: (1) The Dockerfile omitted copying the new script directory resulting in `ModuleNotFoundError`. (2) The URL-encoded password string failed to parse correctly in `libpq`. A special character (`@`) caused `psycopg2` to misinterpret the host as an Abstract Unix Domain Socket, instantly crashing with `Connection refused`. (3) After fixing the parsing, the container hung on the TCP connection pool creation, leading to an Nginx `502 Bad Gateway`.
- **The Fix:** (1) Rewrote the Dockerfile `COPY` directives to encompass the entire `scripts/` directory. (2) Strictly URL-encoded the Azure database password (`%40`, `%23`, `%21`) in the `.env` file to prevent `libpq` parsing overrides. (3) Diagnosed the TCP hang using `nc` and explicitly authorized port `5432` through the Azure Network Security Group (NSG) dashboard, establishing a seamless and secure data bridge.

### [RESOLVED] Issue #6: PyTorch JIT Compilation Latency on Serverless Cold Starts
- **The Bug:** Even with the `HF_HOME` model weight caching enabled, the initial cold start generation still took ~4 minutes. This was traced to vLLM's `torch.compile` (PyTorch Inductor/Dynamo) running a Just-In-Time (JIT) CUDA graph optimization. Because Modal containers are ephemeral, the ~65s compiled bytecode cache was destroyed upon every sleep cycle, forcing a recompilation on every cold start.
- **The Fix (First-Principles Approach):** Rejected the naive solution of disabling CUDA graphs (`--enforce-eager`), which would have artificially bottlenecked inference generation speed (from ~22 tokens/sec down to ~10 tokens/sec). Instead, we injected `XDG_CACHE_HOME: "/models/.cache"` directly into the `modal.Image` environment definition, rerouting the `torch.compile` cache writes to the persistent SSD Volume. This preserves maximum tokens/sec throughput while completely eliminating the 65-second JIT tax on all subsequent cold starts.
