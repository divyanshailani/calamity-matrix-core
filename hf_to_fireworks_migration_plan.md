# Hugging Face → Fireworks AI Embedding/Reranker Migration Plan

**Date:** 2026-08-20  
**Status:** PHASES A–F EXECUTED 2026-08-20 (see §11). Local code, tests, active-database schema, and the full 2,615-row Fireworks backfill are done; Phase G (production canary) and Phase H (reranker) are still pending, and nothing is committed or deployed.  
**Scope:** Move semantic query/document embeddings to Fireworks Qwen3 Embedding 8B, preserve Hugging Face as an emergency/secondary provider, and evaluate Qwen3 Reranker 8B as an optional second-stage reranker.

> The provider name is **Fireworks AI**. The existing Hugging Face bridge is not removed. It remains available as a separately configured fallback until its account/quota is restored or intentionally retired.

---

## 0. Executive decision

Fireworks is a viable primary provider for this project, but it is not a drop-in URL replacement.

1. Fireworks Qwen3 Embedding 8B returns OpenAI-compatible `data[]` objects, while the current Hugging Face parser expects a bare list.
2. Qwen3 and `BAAI/bge-large-en-v1.5` produce different vector spaces. Even if both are requested at 1,024 dimensions, their vectors are **not interchangeable**.
3. Existing production columns (`embedding` / `embedding_v2`) contain BGE-space vectors. A Fireworks query must search a Fireworks-space corpus column, and an HF fallback query must search a BGE-space corpus column.
4. The safe architecture is therefore:

```text
Fireworks Qwen3 Embedding 8B  ──> embedding_fireworks (vector(1024))
                                  └─ primary semantic retrieval

HF BGE Embedding              ──> embedding_v2 / embedding (vector(1024))
                                  └─ secondary semantic fallback

Neither vector space is ever mixed with the other.
Both can fall back to lexical/recency retrieval.
```

5. Qwen3 Reranker 8B is an optional later phase. It should not be enabled on every request until its real response contract, latency, and token burn are measured. Reranker failure must preserve the RRF result order.

**Recommendation:** make Fireworks the primary *embedding* provider after a dual-column backfill and frozen-evaluation gate. Keep HF configured as a provider-specific fallback, not as a dependency for the normal path. Keep reranking disabled by default until a cost-controlled canary proves it is worth the remaining credits.

---

## 1. Current state and migration constraints

### 1.1 Current production path

- Query-time semantic embedding: `scripts/production/retrieval.py` → Hugging Face `BAAI/bge-large-en-v1.5`.
- Live ingestion has a separate HF implementation in `scripts/production/live_ingestion.py`.
- Offline corpus build uses local `SentenceTransformer("BAAI/bge-large-en-v1.5")` in `scripts/pipeline/build_vector_db.py`.
- Resumable BGE backfill uses `scripts/eval/reembed_embedding_v2.py`.
- Production vectors are `vector(1024)` and normalized before cosine search.
- Hybrid retrieval uses dense pgvector + sparse PostgreSQL FTS + recency RRF.
- There is currently no reranker implementation.
- The current HF bridge has been hardened locally but has not been deployed because the provider is returning HTTP 402.

### 1.2 Standing safety constraints

- Do not roll back to the retired acc1 database.
- Investigate and use only the active production database when a database operation is eventually approved.
- Do not touch `globalaqi-archive`; another agent is actively using that project.
- Never commit or upload `.agents/`, `AGENTS.md`, Modal deployment files, or secrets.
- Rotate credentials exposed by the earlier failed redaction before any deployment.
- This document is a design and cost plan, not authorization to spend Fireworks credits or mutate production.

### 1.3 What the screenshot prices imply

The supplied Fireworks screenshot shows:

| Model | Displayed serverless price | Intended use |
|---|---:|---|
| Qwen3 Embedding 8B | $0.10 / 1M tokens | Query and document embeddings |
| Qwen3 Reranker 8B | $0.20 / 1M tokens | Candidate reranking |

These are token prices, not a promise that a fixed number of requests is free. Actual spend depends on input token count, retries, candidate count, truncation, billing rules, and any price changes. The dashboard must be treated as the source of truth before the canary.

---

## 2. Fireworks API contract to verify before coding

The following is the working contract from the Fireworks documentation and model pages. Phase A must verify it against a real, low-volume request before production code is written around it.

### 2.1 Embeddings

- Base URL: `https://api.fireworks.ai/inference/v1`
- Endpoint: `POST /embeddings`
- Model: `fireworks/qwen3-embedding-8b`
- Authentication: `Authorization: Bearer $FIREWORKS_API_KEY`
- Example request:

```json
{
  "model": "fireworks/qwen3-embedding-8b",
  "input": ["text one", "text two"],
  "dimensions": 1024
}
```

- Expected response shape:

```json
{
  "data": [
    {"index": 0, "embedding": [0.01, -0.02]}
  ]
}
```

- Fireworks documents configurable dimensions from 32 through 4,096. Request **`dimensions: 1024`** initially to preserve the existing pgvector schema and avoid an unnecessary index migration.
- Qwen3 embeddings are not assumed to be normalized. The client must normalize them and run the same finite/non-zero/1024-dimension validation already added for the HF path.
- Sort by `index`; reject missing, duplicate, or out-of-range indices. Never trust response order implicitly.

### 2.2 Reranking

The model page identifies `fireworks/qwen3-reranker-8b` at approximately $0.20 / 1M input tokens. Fireworks documents:

- `POST /rerank` with `model`, `query`, `documents`, `top_n`, and `return_documents`.
- An embeddings/logits route for Qwen3 reranker prompts, which can expose an explicit relevance probability and may be easier to batch deterministically.

The exact `/rerank` response schema must be captured from a real request and frozen in a contract test before integration. Do not ship a parser based only on the request example.

### 2.3 Rate limits and errors

Fireworks serverless limits are account/model dependent and may return 429 or 503 during throttling/capacity pressure. The client should:

- Retry only transient statuses (`408`, `429`, `500`/`502`/`503`/`504` as justified by the verified API contract).
- Use exponential backoff with jitter and a single request wall-clock deadline below the Heroku 30-second router ceiling.
- Never retry permanent 400/401/402/403/404/422 contract, authentication, or billing errors.
- Record sanitized provider, endpoint, status, attempt count, and latency in telemetry.
- Never log API keys, authorization headers, request bodies containing secrets, or full provider error bodies if they can contain credentials.

---

## 3. Architecture after migration

### 3.1 Provider/space mapping

Introduce an explicit provider configuration object rather than a single URL switch:

```text
fireworks_qwen3:
  provider: fireworks
  model: fireworks/qwen3-embedding-8b
  column: embedding_fireworks
  dimensions: 1024

hf_bge:
  provider: huggingface
  model: BAAI/bge-large-en-v1.5
  column: embedding_v2       # existing BGE space
  dimensions: 1024

lexical:
  provider: none
  column: fts_vector + recency
```

The retrieval code must choose the vector column from the provider that produced the query vector. A Fireworks vector may only search `embedding_fireworks`; an HF vector may only search the BGE column.

### 3.2 Provider priority and fallback

Recommended production order:

1. **Fireworks embedding** → search `embedding_fireworks` with hybrid RRF.
2. If Fireworks fails and HF is available → **HF BGE embedding** → search `embedding_v2` with the BGE-compatible retrieval path.
3. If both semantic providers fail → lexical + recency RRF.
4. If the optional reranker fails → return the pre-reranked RRF candidates and expose a sanitized failure reason.

A provider failure must never silently change the vector column. Telemetry should include:

- `embedding_provider_attempted`
- `embedding_model`
- `embedding_column`
- `embedding_source` (`fireworks`, `hf`, or `lexical_fallback`)
- `embedding_failure_reason`
- `embedding_http_status`
- `embedding_attempts`
- `reranker_provider` / `reranker_source` when enabled
- `reranker_failure_reason`
- `provider_latency_ms`
- `estimated_input_tokens` where available

### 3.3 Ingestion behavior

Stop the current behavior that writes one vector into both `embedding` and `embedding_v2`. That is safe only because both columns historically received the same BGE vector; it would corrupt retrieval if a Fireworks vector were copied into a BGE column.

For each document:

- Compute Fireworks and HF vectors independently when both are configured.
- Write each vector only to its matching column.
- Treat either provider's failure as a partial result, not as permission to copy the other vector.
- Record vector availability/provider/model metadata and counters.
- If only Fireworks succeeds, the document is available to Fireworks retrieval and remains lexical/recency-only for HF fallback until its BGE vector is filled.
- If neither succeeds, retain the document with a null vector and a healthy FTS vector; do not drop the source record.

---

## 4. Cost and credit-duration model

The $5 balance can last a very long time for embeddings alone, but reranking full candidate narratives can spend it quickly. The right unit is **tokens per user request**, not requests per dollar.

### 4.1 Formulas

Let:

- `C = $5` available credit.
- `Pe = $0.10 / 1,000,000` embedding input tokens.
- `Pr = $0.20 / 1,000,000` reranker input tokens.
- `B` = one-time corpus backfill tokens.
- `Q` = query embedding tokens per request.
- `K` = reranked candidate count.
- `D` = average candidate-document tokens sent to the reranker, after truncation.
- `R` = reranker query/instruction overhead tokens per candidate/request.
- `N` = number of application requests.

Approximate spend:

```text
backfill_cost       = B / 1,000,000 * $0.10
embedding_cost      = N * Q / 1,000,000 * $0.10
reranker_cost       = N * (K * D + R) / 1,000,000 * $0.20
remaining_requests  = ($5 - backfill_cost) / cost_per_request
```

This excludes retries, failed requests that are still billable, and any provider-side billing nuance. The dashboard must be checked after a measured canary.

### 4.2 One-time corpus backfill estimate

The active corpus is approximately 2,615 narratives. Assuming one embedding call per document:

| Average document tokens | Backfill tokens | Approximate embedding cost |
|---:|---:|---:|
| 300 | 784,500 | $0.08 |
| 500 | 1,307,500 | $0.13 |
| 1,000 | 2,615,000 | $0.26 |
| 2,000 | 5,230,000 | $0.52 |

Even a 2,000-token average backfill is roughly fifty cents at the displayed embedding price. The backfill is therefore not the main credit risk; repeated reranking is.

### 4.3 Query-only embedding duration

If a normal request embeds only a 100–300-token query and does not rerank:

- Cost is approximately `$0.00001–$0.00003` per request.
- $5 covers roughly **166,000–500,000 query embeddings** before backfill/retry overhead.

This is an order-of-magnitude estimate, not a quota guarantee.

### 4.4 Reranker scenarios

Illustrative costs, excluding small query/instruction overhead:

| Candidate policy | Approx. reranker tokens/request | Approx. cost/request | $5 capacity after a $0.25 backfill |
|---|---:|---:|---:|
| 20 candidates × 300 tokens | 6,000 | $0.0012 | ~3,958 requests |
| 30 candidates × 500 tokens | 15,000 | $0.0030 | ~1,583 requests |
| 50 candidates × 1,000 tokens | 50,000 | $0.0100 | ~475 requests |
| 50 candidates × 2,000 tokens | 100,000 | $0.0200 | ~237 requests |

For a concrete operating rate, using the middle `30 × 500` case:

| Requests/day | Approx. reranker spend/day | Approx. duration of $5 balance |
|---:|---:|---:|
| 10 | $0.03 | ~158 days |
| 20 | $0.06 | ~79 days |
| 50 | $0.15 | ~32 days |
| 100 | $0.30 | ~16 days |

Real duration will be shorter if the corpus text is not truncated, if retries occur, if multiple reranker calls are made per request, or if the dashboard price differs from the screenshot. The first canary must measure actual billed token usage and record it in a cost ledger.

### 4.5 Cost-control recommendation

Do **not** enable reranking globally at first. Start with:

- Reranker disabled by default.
- Explicit feature flag and per-request opt-in for the canary.
- Maximum 20–30 candidates.
- Deterministic document truncation (for example 500–800 tokens, to be validated for recall).
- One reranker call per request.
- A daily token/spend budget and automatic fail-open to RRF when the budget is reached.
- Alerts at 25%, 50%, 75%, and 90% of the $5 balance.

Fireworks embeddings can become the default primary path immediately after quality validation; reranking is an independent product/performance decision.

---

## 5. Phased implementation plan

### Phase A — Account and contract verification (no production mutation)

1. Confirm the Fireworks balance, billing unit, account-level request limit, and whether credits expire.
2. Record the exact model IDs and current prices from the Fireworks dashboard/API.
3. Make one minimal embedding request with a non-sensitive test string and `dimensions: 1024`.
4. Make one minimal reranker request only if needed; capture and redact the full response shape.
5. Measure actual usage headers, response latency, and billed tokens.
6. Add a local-only cost ledger entry; never commit the API key.
7. Confirm whether Fireworks credits are shared across embeddings and reranking.

**Exit gate:** verified endpoint/response contracts, balance, expiry behavior, and token accounting. If the account has no usable credits or the model is unavailable, stop without touching production.

### Phase B — Canonical provider adapter

1. Extend `scripts/production/retrieval.py` into a provider-neutral embedding client.
2. Add allowlisted configuration, with no arbitrary user-supplied URLs:
   - `EMBEDDING_PRIMARY_PROVIDER=fireworks`
   - `FIREWORKS_API_KEY`
   - `FIREWORKS_BASE_URL=https://api.fireworks.ai/inference/v1`
   - `FIREWORKS_EMBEDDING_MODEL=fireworks/qwen3-embedding-8b`
   - `FIREWORKS_EMBEDDING_DIMENSIONS=1024`
   - `HF_TOKEN`
   - `HF_EMBEDDING_MODEL=BAAI/bge-large-en-v1.5`
3. Parse Fireworks `data[]`, sort by `index`, verify cardinality, validate dimensions/finiteness/non-zero norm, and normalize.
4. Apply the existing total-deadline/no-permanent-retry policy to both providers.
5. Make provider failures safe and observable without logging secrets.
6. Freeze a single Qwen3 query/document text construction rule. Do not blindly reuse the BGE-specific instruction prefix without evaluation.
7. Keep `embed_query`/`embed_many` compatibility for existing evaluation scripts, or update all callers together with explicit provider/space returns.

**Exit gate:** unit tests pass for single/batch, out-of-order indexes, malformed responses, 4xx fail-fast, transient retry, timeout, wrong dimension, non-finite values, zero vectors, and normalization.

### Phase C — Dual-column schema and metadata

1. Add a new nullable `embedding_fireworks vector(1024)` column using a versioned migration.
2. Add an HNSW cosine index only after data exists and the migration has been reviewed for lock/latency impact.
3. Do not overwrite `embedding` or `embedding_v2`.
4. Add a small metadata mechanism (column/table or controlled application metadata) recording provider, model, dimension, normalization, text-format version, and backfill timestamp.
5. Verify active production schema, row counts, null counts, index definitions, and rollback SQL before applying anything.
6. Keep all existing BGE retrieval behavior unchanged while the new column is null.

**Exit gate:** schema accepts both spaces, current BGE retrieval remains unchanged, and no vector from one provider can be selected for the other provider's column.

### Phase D — Fireworks corpus backfill

1. Use a resumable, checkpointed backfill derived from `scripts/eval/reembed_embedding_v2.py`.
2. Read the canonical document text and apply the frozen Qwen3 document format.
3. Batch conservatively (start at 16; increase only after observing response size/latency).
4. Enforce request deadline, transient retry/backoff, and exact response cardinality.
5. Write only `embedding_fireworks`; never copy it into BGE columns.
6. Record per-batch token usage, cost estimate, failures, and checkpoint.
7. Pause automatically on unexpected spend, repeated 4xx, or a provider outage.
8. Verify: total rows, non-null count, null count, finite values, norm distribution, dimension, and HNSW index health.

**Exit gate:** all eligible rows have valid Fireworks vectors, the cost ledger matches the Fireworks dashboard within an explainable tolerance, and the backfill is reproducible/resumable.

### Phase E — Retrieval evaluation

Run the existing frozen retrieval evaluation against separate provider/column pairs:

- BGE query → BGE column (current baseline).
- Fireworks query → Fireworks column (candidate).
- Fireworks query → BGE column (must be rejected by code/tests, not used as a result).
- Lexical-only fallback.

Measure at minimum:

- Recall@5 and Recall@10.
- MRR and nDCG where labels exist.
- Small-pool/truthful-filter guard from the existing hybrid evaluation.
- p50/p95 embedding latency and full API latency.
- HTTP error/fallback rates.
- Tokens/request and estimated cost/request.
- Score calibration; do not display RRF scores as cosine similarity.

**Acceptance suggestion:** Fireworks must meet or exceed the frozen BGE baseline within a pre-agreed tolerance, with no regression on the small-pool guard. If quality is lower, retain HF/BGE as semantic primary and use Fireworks only for an experiment.

### Phase F — Ingestion and fallback hardening

1. Replace the duplicated HF code in `live_ingestion.py` with the canonical adapter.
2. Add explicit request timeout, bounded retries, vector validation, and counters.
3. Write provider-specific vectors independently.
4. Stop writing the same vector to `embedding` and `embedding_v2` as a shortcut.
5. Add `embedding_fireworks` availability and failure reason to ingestion logs/telemetry.
6. Decide whether normal ingestion pays for both providers:
   - **Quality-first:** generate both Fireworks and HF vectors when both are healthy.
   - **Cost-first:** generate Fireworks only; generate HF later in a controlled secondary backfill.
7. Ensure lexical FTS is still populated when all embedding providers fail.

### Phase G — Controlled production canary

1. Deploy only after credential rotation and provider-account verification.
2. Start with Fireworks primary behind a feature flag and a small traffic slice.
3. Keep HF fallback mapped to BGE column; keep lexical fallback as the final path.
4. Monitor provider status, latency, fallback source, candidate counts, score distributions, and token spend.
5. Do not enable the reranker in the same first canary; isolate variables.
6. Compare live output against the current baseline queries and the frozen evaluation set.
7. Expand gradually only if error rate, quality, latency, and spend remain inside the gates.
8. If Fireworks fails, disable the flag and continue on HF/BGE or lexical retrieval. Do not roll back the database or point at acc1.

### Phase H — Optional reranker experiment

Only after Fireworks embedding is stable:

1. Retrieve a bounded RRF candidate pool (start with 20).
2. Truncate candidate narratives deterministically and measure the token budget.
3. Implement the verified `/rerank` or logits response parser.
4. Add timeout, retry, budget guard, and fail-open-to-RRF behavior.
5. Compare RRF vs reranked RRF for MRR/nDCG, relevance judgments, latency, and spend.
6. Run an opt-in canary; do not make it global unless the relevance gain justifies the credit burn.

---

## 6. Acceptance matrix

| Area | Required evidence before Fireworks becomes primary |
|---|---|
| API contract | Real embedding response parsed; real status/error behavior documented; reranker response frozen if used |
| Vector safety | Exactly 1,024 finite non-zero normalized values; batch indexes/cardinality verified |
| Space isolation | Fireworks vectors only search `embedding_fireworks`; BGE vectors only search BGE column |
| Backfill | Resumable, checkpointed, complete or intentionally bounded; no existing BGE column overwritten |
| Retrieval quality | Frozen eval meets agreed recall/MRR/nDCG gate and preserves small-pool truthfulness |
| Reliability | Total deadline, transient-only retries, 4xx fail-fast, lexical fallback, no secret leakage |
| Ingestion | Canonical client; separate provider writes; FTS survives embedding outages |
| Cost | Measured tokens/request; daily budget; alerts; automatic reranker budget stop |
| Deployment | Credentials rotated; preview/staging verified; controlled production canary; rollback flag tested |
| Safety | Active DB only; no acc1 rollback; `.agents`/`AGENTS.md`/Modal files excluded from git |

---

## 7. Explicit non-goals

- Do not delete the Hugging Face client or remove `HF_TOKEN` during this migration.
- Do not overwrite BGE vectors with Qwen vectors merely because both use 1,024 dimensions.
- Do not change the pgvector dimension to 4,096 in the first migration. That is a separate quality/storage/index decision.
- Do not add a reranker just because the model is available; it has a separate cost and latency budget.
- Do not use the Fireworks reranker to replace candidate generation; sparse/recency retrieval remains important for recall and outage resilience.
- Do not infer credit duration from request count alone.
- Do not deploy until the HF 402 decision and exposed-credential rotation gates are satisfied.

---

## 8. Risks and mitigations

| Risk | Mitigation |
|---|---|
| Fireworks account credits run out | Daily spend budget, dashboard checks, alerts, provider flag, HF/lexical fallback |
| Qwen quality differs from BGE | Separate backfill + frozen eval before canary |
| Mixed vector spaces | Provider-to-column mapping enforced in code and tests |
| Fireworks response shape changes | Contract tests, strict parser, fail closed to fallback |
| Reranker burns credits too quickly | Disabled by default, candidate/text caps, token ledger, budget circuit breaker |
| Provider throttling/503 | Bounded exponential backoff and total deadline |
| New vector column/index impacts DB | Migration plan, lock/latency review, apply only after active DB inspection |
| HF remains unavailable | Fireworks primary; BGE fallback only when HF is actually healthy; lexical final fallback |
| Ingestion writes partial vectors | Per-provider status and independent writes; never fabricate/copy vectors |
| Credentials leak | Redaction tests, secret-free logs, rotate before deploy, never commit `.env` |

---

## 9. Sources

Verify these URLs at execution time because provider model IDs, prices, response schemas, and account limits can change:

- [Fireworks embeddings and reranking guide](https://docs.fireworks.ai/guides/querying-embeddings-models)
- [Qwen3 Embedding 8B model page](https://fireworks.ai/models/fireworks/qwen3-embedding-8b)
- [Qwen3 Reranker 8B model page](https://fireworks.ai/models/fireworks/qwen3-reranker-8b)
- [Fireworks embeddings/reranking announcement](https://fireworks.ai/blog/embeddings-and-reranking-announcement)
- [Fireworks serverless rate limits](https://docs.fireworks.ai/serverless/rate-limits)
- [Fireworks account quotas and request limits](https://docs.fireworks.ai/guides/quotas_usage/account-quotas)
- [Fireworks inference error codes](https://docs.fireworks.ai/guides/inference-error-codes)
- [Fireworks reliability and retry guidance](https://docs.fireworks.ai/guides/reliability)
- [Qwen3 Embedding upstream model specifications](https://github.com/QwenLM/Qwen3-Embedding)

---

## 10. Current conclusion

The $5 Fireworks balance is likely sufficient for a full 2,615-row embedding backfill and a meaningful embedding canary. It may last from weeks to months for low-volume reranking, but only days to weeks if every request reranks 30–50 long documents. Therefore:

- Migrate **embeddings first**.
- Preserve HF as a separate, provider-matched fallback.
- Keep lexical retrieval permanently available.
- Treat reranking as opt-in until measured.
- Use actual Fireworks token/balance telemetry to replace these estimates before widening traffic.

**No production action is authorized by this plan alone.**

---

## 11. Execution record — 2026-08-20

Phases A–F are done. Nothing is committed and nothing is deployed; the only
remote system changed is the active production **database schema** (additively).

### 11.1 Phase A — verified API contract (supersedes the §2 assumptions)

Measured against the live account, not documentation:

| Check | Result |
| --- | --- |
| `GET /models` | 200; `qwen3-embedding-8b` and `qwen3-reranker-8b` both present |
| `POST /embeddings` with `dimensions: 1024` | 200; `data[].embedding` has 1024 finite floats |
| Returned vector norm | **68.877** — Qwen3 output is *not* unit-normalized, so the client must normalize |
| `usage.prompt_tokens` | present (13 for one short query, 33 for a batch of 3) |
| Batch of 3 | `data[].index` = `[0,1,2]`; slotting by `index` is required, order is not guaranteed by contract |
| Bad key | 401 `UNAUTHORIZED` — permanent, must not be retried |
| Bad model id | 400 — permanent |
| `POST /rerank` | 200; `data[]` of `{"index", "relevance_score"}` plus `usage.prompt_tokens` (171). Relevant doc scored 0.4378, irrelevant 3.04e-06 |

This closes the plan's open item that the `/rerank` response schema was
undocumented. The reranker exists, works, and is priced per prompt token.

### 11.2 Phase C — schema change applied to the active database

Applied to the live DSN at `52.140.120.90:5432` (2,615 rows):

```sql
ALTER TABLE disaster_narratives ADD COLUMN IF NOT EXISTS embedding_fireworks vector(1024);
CREATE INDEX IF NOT EXISTS idx_dn_embedding_fireworks_hnsw ON disaster_narratives
  USING hnsw (embedding_fireworks vector_cosine_ops) WITH (m = 16, ef_construction = 64);
```

`embedding` and `embedding_v2` were not read, rewritten, or reindexed; both
still have 0 NULLs. Rollback is `DROP INDEX ... ; ALTER TABLE ... DROP COLUMN
embedding_fireworks;` and destroys only Fireworks vectors.

### 11.3 Phase D — backfill actuals vs estimate

| Metric | Estimated (§4.2) | Actual |
| --- | --- | --- |
| Rows | 2,615 | 2,615 (0 NULL remaining) |
| Prompt tokens | 800k–5.2M | **842,618** |
| Spend | $0.08–$0.52 | **$0.0843** |
| Wall clock | — | ~8 min at batch 16 |

The actual cost landed at the optimistic end of the estimate, so roughly
**1.7% of a $5 balance** paid for the entire corpus. Ledger:
`eval/fireworks_cost_ledger.jsonl`.

Post-backfill vector validation: 2,615 rows, dimensions exactly 1024 for every
row, and L2 norms in `[0.99999999, 1.00000000]` — client-side normalization is
confirmed working end to end. The highest off-diagonal cosine is 0.798, so the
column is not degenerate (identical vectors would sit at 1.0).

### 11.4 Phase E — retrieval evaluation, 32 frozen queries, hybrid mode

Each provider searched only its own column.

| Metric | BGE / `embedding_v2` | Fireworks Qwen3 / `embedding_fireworks` |
| --- | --- | --- |
| recall@5 | 0.969 | **0.969** |
| recall@3 | 0.969 | **0.969** |
| MRR | 0.906 | 0.885 |
| nDCG@5 | 0.927 | 0.911 |
| latency p50 | 510 ms | 526 ms |
| latency p95 | 693 ms | 860 ms |

Per category, Fireworks matches BGE exactly on `beyond500`, `exact`,
`smallpool`, and `mismatch` recall@5 (1.000/1.000/1.000/0.875). The only
difference is ranking *within* the retrieved set: `beyond500` MRR is 0.883 for
Fireworks against 0.950 for BGE, meaning the correct document is slightly more
often at rank 2 instead of rank 1. Every metric passes the 5%-of-baseline guard
against the frozen legacy baseline (recall@5 0.8125, MRR 0.7448).

Interpretation: Fireworks is a safe primary. It finds the same documents; it
orders them marginally worse. That ordering gap is exactly what the Phase H
reranker would target, and it is small enough that the reranker is not
justified on retrieval quality alone.

The eval runner gained `--provider {huggingface,fireworks}`, which selects the
embedder, the matching column, and a per-provider embedding cache, and it now
refuses to report metrics if any query failed to embed (a partly-lexical run
would silently understate the dense arm).

### 11.5 What is deliberately still pending

- **Phase G — production canary.** Blocked on credential rotation: `HF_TOKEN`,
  `CLOUD_LLM_API_KEY`, `INGESTION_SECRET_KEY`, and the Fireworks key have all
  been exposed in a transcript. Rotate before setting Heroku config vars.
- **Phase H — reranker.** Contract verified, `USE_RERANKER` still defaults off.
- **Commit and deploy.** The working tree holds all of the above uncommitted.
- **Heroku config.** `FIREWORKS_API_KEY` is not set in production, so the
  deployed app would still resolve `huggingface` as its only provider.

