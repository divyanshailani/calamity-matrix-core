# Calamity Matrix Core - Project Memory & Rules

## Project Overview
Calamity Matrix Core is a global natural disaster intelligence system (2000-2025) utilizing a "First-Principles" engineering approach. It simulates and analyzes physical disaster events, predicts human impact, and grounds predictions in actual historical narratives.
Current Phase: V2 Active Development (LLM Synthesis layer integrated via Serverless Cloud GPU with SSE streaming).

## Tech Stack
- **Frontend (Vercel):** Next.js (calamity-ui), MapLibre GL, CartoDB Positron maps
- **Backend (DigitalOcean):** FastAPI (api_orchestrator.py), Nginx Reverse Proxy
- **Database (Supabase):** PostgreSQL + pgvector
- **ML (Predictive):** XGBoost (isolated multi-physics models), Optuna
- **ML (Embeddings):** BAAI/bge-large-en-v1.5
- **ML (Generative):** Qwen-3 8B LoRA. Fine-tuned on an enterprise Hosted Workbench (L40S GPU, 32GB RAM, 8-Core CPU). Inference deployed on a Serverless Cloud Platform (A10G GPU, 24GB VRAM) running vLLM.

## Core Architectures
- **Math Engine v3 (Multi-Physics):** Isolated XGBoost regression models for different disaster types. Inputs are fused structured matrices. Output requires an inverse `log1p` transform (`expm1`).
- **Narrative Engine (Semantic RAG):** 2,281 SITREPs from HDX/ReliefWeb. 1024-d embeddings using pgvector cosine distance (`<=>`), with multi-pass strict/fallback SQL filtering in `api_orchestrator.py`.
- **LLM Synthesis Layer:** Qwen-3 8B model with a "Simulation Architect" persona (via `scripts/inject_identity.py`).

## Critical Issues & Action Items (Issue #1: LLM Merge)
[RESOLVED] The Qwen-3 8B model integration into `api_orchestrator.py` was previously halted due to catastrophic failures:
1. **VRAM Exhaustion (Container Sprawl):** Resolved by deploying a serverless A10G (24GB VRAM) cloud endpoint running vLLM with a 60-second idle container timeout.
2. **JSON Parsing Crashes:** Resolved by bypassing JSON entirely. The FastAPI `/api/v1/ask_ai` endpoint now uses Server-Sent Events (`StreamingResponse`) to stream raw text directly to the frontend.
3. **Hallucinated Prompts:** Resolved by enforcing the exact `calamity_training_data.jsonl` string structure in the orchestrator payload.

### Core Goal for Agents (Current Focus)
**[RESOLVED] Phase 21: UI/UX Frontend SSE Integration**
The backend API orchestrator successfully streams Server-Sent Events (SSE) from the Serverless LLM, and the Next.js frontend (`calamity-ui`) has been fully updated.
- `ColdStartTerminal.tsx` was refactored to consume the streaming `/api/v1/ask_ai` endpoint via `fetch()` and `ReadableStream`.
- Incoming text tokens are parsed into human-readable text instead of rendering raw JSON.
- CSS guardrails (`overflow-y-auto`, `break-words`, `whitespace-pre-wrap`) were implemented to prevent overflow and preserve the dashboard layout.
- The LLM inference was isolated behind an explicit manual trigger ("GENERATE AI SYNTHESIS" button) to prevent unnecessary GPU cold boots on every simulation run.
- Nginx `proxy_read_timeout` was increased to 300s to allow for Modal A10G cold boots without throwing `504 Gateway Timeout` (which appeared as `Failed to fetch` in the browser).
