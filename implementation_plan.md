# Production RAG Upgrade: Implementation Plan

**Created:** 2026-08-18 · **Status:** EXECUTED — see §11 for measured results
**Every claim below was verified against the live PostgreSQL 18.4 / pgvector 0.8.6 instance and the live Hugging Face router.** Verification commands are inline so you can re-run them.

---

## 0. Executive summary — and a correction to the obvious plan

The intuitive plan (add BM25 → add reranking → done) is **not** the right order for this system. Measurement changed the priorities:

1. **Embeddings only ever saw the first 500 characters of each document.** `scripts/production/live_ingestion.py:119` embeds `narrative_text[:500]`. Measured: **75.4% of rows are truncated, and only 20.1% of the corpus's characters have ever been vectorised.** No amount of fusion or reranking can retrieve text that was never embedded. This is the single largest defect and it is upstream of everything else.
2. **The metadata filters leave almost nothing to rank.** Measured: **11.9 rows per country on average** (191 countries, min 1, max 211). The example `country='Japan' AND disaster_type='Earthquake' AND event_year>=2000` matches **exactly 7 rows**. Retrieving "top 20 candidates", fusing two rankings, then reranking down to 3 is machinery with nothing to chew on. Pool size is the bottleneck, not ranking quality.
3. **Cross-encoder reranking is not available on the current infrastructure.** Verified by direct API probe: `cross-encoder/ms-marco-MiniLM-L-6-v2` → `"Model not supported by provider hf-inference"`; `BAAI/bge-reranker-v2-m3` is `live` but registered as `task: text-classification`, and every text-pair payload shape returns HTTP 400. There is no `/rerank` route. Reranking needs a different provider or it does not happen.

So: **make it measurable, fix coverage, widen the pool, then rank.** Hybrid retrieval lands in Phase 3 rather than Phase 1, and reranking in Phase 5, because both operate on candidates that the first two phases determine.

---

## 1. Verified current state

| Property | Value | How verified |
|---|---|---|
| PostgreSQL | 18.4 (Ubuntu, x86_64) | `SELECT version()` |
| pgvector | 0.8.6 | `pg_extension` |
| Other extensions | `pg_stat_statements`, `pgcrypto`, `uuid-ossp`, `plpgsql` | `pg_extension` |
| Rows | 2,615 | `count(*)` |
| Event years | 1906–2026 | `min/max(event_year)` |
| Rows in scope (`>= MIN_EVENT_YEAR` 2000) | 2,264 (351 quarantined) | filtered count |
| Indexes on `disaster_narratives` | `disaster_narratives_pkey`, `unique_id_constraint` **only** | `pg_indexes` |
| Vector index | **none** — sequential scan | `pg_indexes` + `EXPLAIN` |
| Narrative length | avg 2,138 · p50 1,056 · p95 7,543 · max 47,820 chars | percentiles |
| Rows > 2,048 chars | 742 | count |
| Dyno | Heroku **Basic**, 512 MB, `--workers 4` | `Procfile`, `heroku ps` |

Retrieval today is `_rag_search()` at `scripts/production/api_orchestrator.py:193-260`: three passes of pgvector cosine with a time-decay penalty, `(1 - (embedding <=> q)) - (decay * ABS(event_year - target))`. The column alias `hybrid_similarity` is a misnomer — there is no sparse component. No reranker, no query rewriting, no evaluation.

---

## 2. Phase order

| Phase | Work | Why here |
|---|---|---|
| 0 | Evaluation harness + frozen baseline | Nothing after this is provable without it |
| 1 | Fix embedding coverage (re-embed) | Largest quality defect; upstream of all ranking |
| 2 | Metadata filtering / candidate pool | Pools of 7–12 rows make ranking moot |
| 3 | FTS + hybrid RRF + indexes | The BM25 work, now with something to rank |
| 4 | Query rewriting | Multiplies phase 3 |
| 5 | Reranking | Blocked on a provider decision |
| 6 | Latency instrumentation | Continuous from phase 0 |

---

## Phase 0 — Evaluation harness and a frozen baseline

Build this first and keep it small. Ponytail Mode: ~30 queries beats a perfect 300-query set that never ships.

**Dataset** `eval/retrieval_eval.json` — one record per query:

```json
{
  "id": "eq_japan_2011",
  "query_text": "coastal devastation and tsunami inundation",
  "disaster_type": "Earthquake",
  "country": "Japan",
  "event_year": 2011,
  "relevant_unique_ids": ["...", "..."],
  "note": "Tohoku. Tests whether long narratives are reachable at all."
}
```

Use `unique_id` (stable, has a unique constraint) as the relevance key, **not** `id` — integer ids are not stable across a restore from the off-box archives.

**Compose the 30 from measured weak spots, not intuition:**
- 10 queries whose answer lives **beyond character 500** of its narrative — these must fail at baseline and pass after Phase 1. This is the coverage regression test.
- 8 exact-token queries (place names, magnitudes, years) — these are what FTS should fix in Phase 3.
- 6 queries on countries with ≤ 5 rows, to exercise the small-pool path from Phase 2.
- 6 taxonomy-mismatch queries ("typhoon" when the row says `Tropical Cyclone`) for Phase 4.

**Metrics:** Recall@5, Recall@3, MRR, nDCG@5, plus p50/p95 latency. Report all six every run; optimise none of them in isolation.

**Do not set numeric targets yet.** Targets picked before a baseline exists are fiction. Run the harness against current production, freeze the output as `eval/baseline.json`, and set thresholds from it.

**Runner** `scripts/eval/run_retrieval_eval.py`, importing the same retrieval function the API uses so the harness cannot drift from production behaviour. Read-only; safe against production, but prefer a restored off-box archive.

**Regression guard:** fail if any metric drops >5% versus `baseline.json`.

---

## Phase 1 — Fix embedding coverage (the actual bottleneck)

### The defect

`scripts/production/live_ingestion.py:107-119`:

```python
narrative_text = f"Title: {title}\n\n{body}"
if len(narrative_text) > 4000:
    narrative_text = narrative_text[:4000] + "..."
...
"semantic_query": f"{disaster} in {country} (Year: {event_year}). "
                  f"Additional Context: {narrative_text[:500]}",
```

The row stores up to 4,000 characters but the embedding is built from `[:500]`. Measured consequence:

```sql
SELECT count(*) FILTER (WHERE length(narrative_text) > 500)                      AS truncated,
       round(100.0*sum(least(length(narrative_text),500))/sum(length(narrative_text)),1) AS pct_chars_embedded
FROM disaster_narratives;
--  truncated = 1971 / 2615  (75.4%)
--  pct_chars_embedded = 20.1
```

**79.9% of the corpus text has never been vectorised.** `bge-large-en-v1.5` accepts 512 tokens (~2,048 chars), so even the model's own capacity is being under-used by 4x. Rows up to 47,820 chars exist (predating the 4,000-char cap in the live path).

### Options

| Option | Coverage | Cost | Verdict |
|---|---|---|---|
| A. Raise `[:500]` → `[:2000]` | 20.1% → 53.7% | 2,615 re-embeddings, no schema change | **Do this first** |
| B. Chunk to ~1,800 chars with 200-char overlap, one row per chunk | ~100% | Schema change (`parent_id`, `chunk_index`), ~4,200 embeddings, dedup at query time | Do after A is measured |
| C. Leave it | 20.1% | 0 | Not viable |

Option A is one line and recovers over half the loss; measure it before paying for B. The 53.7% figure is measured, not estimated:

```sql
SELECT round(100.0*sum(least(length(narrative_text),2048))/sum(length(narrative_text)),1)
FROM disaster_narratives;  -- 53.7
```

### Re-embedding run

2,615 calls to the HF router. Measured single-call latency with `wait_for_model=True`: **4.04s** (HTTP 200, verified). Serial worst case ≈ 2.9 hours; the model warms after the first call so expect well under that.

Constraints that must be respected:
- Run it as a **local one-off script**, never in a Heroku request or a `--workers 4` process. The keep-warm thread was removed in `6657bd3` precisely because per-worker background work burned the free quota.
- Batch where the router allows it, checkpoint progress to disk, and make the script resumable by `unique_id` — a mid-run quota exhaustion must not corrupt the table.
- Write to a **new column** `embedding_v2 vector(1024)`, backfill, verify, then swap. Never overwrite `embedding` in place; the rollback path is the old column.
- Take an off-box archive first (`~/.hermes/scripts/calamity_pull_backup.sh`) and confirm it before starting.

### Acceptance

The 10 "answer beyond char 500" eval queries move from failing to passing. If they do not, Option A was insufficient and Option B is justified.

---

## Phase 2 — Metadata filtering and candidate pool size

### The measured problem

```sql
SELECT round(avg(c),1) avg_per_country, min(c), max(c), count(*) n_countries
FROM (SELECT country, count(*) c FROM disaster_narratives
      WHERE event_year>=2000 GROUP BY country) t;
--  11.9 | 1 | 211 | 191

SELECT count(*) FROM disaster_narratives
WHERE disaster_type = ANY(ARRAY['Earthquake']) AND country ILIKE 'Japan' AND event_year >= 2000;
--  7
```

The current filters are a conjunction of `disaster_type = ANY(...)`, `country ILIKE`, and a year constraint. For a typical query that leaves single digits. **A retriever cannot rank its way out of a 7-row candidate pool**, which is why Phase 3 and Phase 5 are worth little until this is addressed.

### 2a. Make strictness a parameter, defaulting to today's behaviour

```python
class SimulationRequest(BaseModel):
    # ... existing fields ...
    filter_strictness: str = Field(default="normal", pattern="^(strict|normal|relaxed)$")
    max_year_delta: int = Field(default=0, ge=0, le=126)   # 0 = no year bound
    min_candidates: int = Field(default=20, ge=3, le=200)
```

Defaults are chosen so an existing client that sends none of these fields keeps the current strict-then-relax behaviour. That equivalence is not free, though — Phase 2b replaces the fixed pass ladder, so the eval harness must confirm the default path still returns what it returned before, rather than assuming it.

### 2b. Progressive relaxation driven by pool size, not by a fixed pass ladder

Replace the hardcoded Pass 1 → Pass 2 → Pass 3 ladder with a loop that widens the filter until the pool reaches `min_candidates`:

1. country + type + exact year
2. country + type (drop year)
3. country only, or type only — whichever retains more rows
4. type + geographic neighbours (needs a region column; see 2c)
5. type only, globally

Stop at the first tier reaching `min_candidates`. Record the tier reached in telemetry so the eval harness can report how often the strict tier is actually sufficient — that number decides whether Phase 5 reranking is worth building at all.

### 2c. Add a `region` column to make tier 4 possible

191 countries with a mean of 11.9 rows is too granular to be the only geographic filter. A coarse region (`South Asia`, `East Asia`, `Sub-Saharan Africa`, …) gives a meaningful fallback that keeps results topically plausible. Deriving it from `country` is a static mapping table, no new data source.

### 2d. Fix `country ILIKE` — it cannot use an index

```
EXPLAIN SELECT id FROM disaster_narratives WHERE country ILIKE 'Japan';
--  Seq Scan on disaster_narratives
--    Filter: ((country)::text ~~* 'Japan'::text)
```

Irrelevant at 2,615 rows, load-bearing at 100k. Country values already pass through `resolve_country()` / `COUNTRY_ALIASES`, so they are controlled input and the `ILIKE` buys nothing. Move to `lower(country) = lower(%s)` plus:

```sql
CREATE INDEX idx_dn_country_lower ON disaster_narratives (lower(country));
CREATE INDEX idx_dn_type_year     ON disaster_narratives (disaster_type, event_year);
```

Keep the existing `payload.country.replace('%','').replace('_','')` sanitisation regardless — it is what stops `ILIKE` wildcard injection today.

---

## Phase 3 — Full-text search, indexes, and RRF fusion

PostgreSQL's built-in FTS ranks with a TF-IDF-derived score, **not** true BM25 (no `k1`/`b` term-saturation or length-normalisation parameters). At 2,615 documents the difference is unlikely to be measurable, and native FTS needs no new extension on the Azure VM. Real BM25 would mean installing ParadeDB `pg_search` — see the decision in §8.

### 3a. Generated `tsvector` column — verified to work

The immutability question decides this: `to_tsvector(regconfig, text)` is `IMMUTABLE` (two-arg, explicit config) while `to_tsvector(text)` is only `STABLE` and cannot appear in a generated column. The two-arg form is used below, and it was executed successfully against production inside a rolled-back transaction:

```sql
ALTER TABLE disaster_narratives
ADD COLUMN fts_vector tsvector GENERATED ALWAYS AS (
    setweight(to_tsvector('english', coalesce(narrative_text, '')), 'A') ||
    setweight(to_tsvector('english', coalesce(country, '')),        'B') ||
    setweight(to_tsvector('english', coalesce(disaster_type, '')),  'B')
) STORED;
--  ALTER TABLE, 2,889 ms (full table rewrite, ACCESS EXCLUSIVE lock)
```

`STORED` self-maintains on insert and update, so `live_ingestion.py` needs no change. The 2.9s rewrite holds an `ACCESS EXCLUSIVE` lock — brief, but run it during a quiet window.

### 3b. Indexes — both verified to build

```sql
CREATE INDEX idx_dn_fts ON disaster_narratives USING GIN (fts_vector);
--  242 ms
CREATE INDEX idx_dn_embedding_hnsw ON disaster_narratives
  USING hnsw (embedding vector_cosine_ops) WITH (m = 16, ef_construction = 64);
--  1,173 ms
```

A caveat worth knowing before promising a speed-up: the planner does **not** always choose HNSW at this size. Two forms of the same dense lookup, measured:

```
ROW_NUMBER() OVER (ORDER BY embedding <=> q) ... LIMIT 20
  -> Index Scan using idx_hnsw     shared hit=354
plain ORDER BY embedding <=> q LIMIT 20
  -> Seq Scan + top-N heapsort     shared hit=7913
```

22x fewer buffers for the windowed form, and the plain form ignored the index entirely because a seq scan over 2,264 rows costed cheaper. **Do not describe HNSW as an unconditional win at this corpus size** — its value is insurance for 10k–100k rows. Re-check `EXPLAIN` after the corpus grows.

### 3c. The `tsquery` operator is the highest-impact detail in this phase

`plainto_tsquery` **AND**-joins every term, and so does `websearch_to_tsquery`:

```
plainto_tsquery('english','earthquake tsunami damage')  -> 'earthquak' & 'tsunami' & 'damag'
```

Measured recall consequence on rows in scope:

```
AND semantics (plainto_tsquery):      28 rows
OR  semantics ('a' | 'b' | 'c'):   1,196 rows
```

**A 42x recall difference.** Requiring every term of a descriptive disaster query is fatal. Build an OR-query while keeping `plainto_tsquery`'s sanitisation by swapping the operator afterwards:

```sql
replace(plainto_tsquery('english', %s)::text, '&', '|')::tsquery
```

Verified injection-safe — the hostile input `x' | y & !z:* ; DROP TABLE t --` reduces to the inert `'x' | 'y' | 'z' | 'drop' | 'tabl'`. Verified edge case: stopword-only and empty input both yield an **empty** tsquery plus a `NOTICE`, and an empty tsquery matches zero rows, so the sparse arm must be skipped when the query is empty rather than silently contributing nothing.

### 3d. Fusion — and why time-decay must not be a multiplier

Reciprocal Rank Fusion sums `1/(k+rank)` across ranked lists, `k=60` (Cormack et al., 2009). It is used precisely because it ignores the incomparable scales of cosine distance and `ts_rank_cd`.

The tempting move is to keep the existing time-decay by multiplying it into the fused score. **Measured, that inverts the intended ranking hierarchy:**

```
RRF score at rank 1  = 1/(60+1)  = 0.016393
RRF score at rank 20 = 1/(60+20) = 0.012500
=> the entire dense/sparse ranking signal spans a ratio of 1.31x

decay multiplier, flood (0.008) across the in-scope year span (26 years)
  = 1 - 0.008*26 = 0.7920
=> the decay term alone spans a ratio of 1.26x
```

The decay factor's dynamic range is as large as the whole fused ranking, so it becomes the de-facto primary sort key with retrieval relevance demoted to a tiebreaker. That is not the current behaviour and not the intent: today decay is subtracted from a cosine whose meaningful range is far wider, so it modulates rather than dominates.

**Fix: make recency a third ranked list and fuse it on RRF's own scale**, with a weight expressing how much recency should matter relative to relevance:

```sql
WITH dense AS (
  SELECT id, ROW_NUMBER() OVER (ORDER BY embedding <=> %s::vector) AS rank
  FROM disaster_narratives
  WHERE <filters> LIMIT 30
),
sparse AS (
  SELECT id, ROW_NUMBER() OVER (ORDER BY ts_rank_cd(fts_vector, %s::tsquery, 32) DESC) AS rank
  FROM disaster_narratives
  WHERE fts_vector @@ %s::tsquery AND <filters> LIMIT 30
),
recency AS (
  SELECT id, ROW_NUMBER() OVER (ORDER BY ABS(event_year - %s)) AS rank
  FROM disaster_narratives
  WHERE <filters> LIMIT 30
)
SELECT dn.*, SUM(w) AS rrf
FROM (
  SELECT id, 1.0/(60+rank)       AS w FROM dense
  UNION ALL
  SELECT id, 1.0/(60+rank)       AS w FROM sparse
  UNION ALL
  SELECT id, 0.5*(1.0/(60+rank)) AS w FROM recency   -- recency at half weight
) f JOIN disaster_narratives dn ON dn.id = f.id
GROUP BY dn.id
ORDER BY rrf DESC LIMIT %s;
```

Verified end to end against production: **4.57 ms execution, 0.69 ms planning**, returning sensibly diverse results (Haiti 2021, Türkiye 2023, Philippines 2026 …) each matched by two of the three lists. The `0.5` recency weight is the one knob to tune against the Phase 0 eval set; `TIME_DECAY_PENALTY` per disaster type maps onto this weight instead of onto a subtraction.

Two implementation details that measurement exposed:

- **`LIMIT n` inside a CTE that computes `ROW_NUMBER() OVER (ORDER BY …)` does return ranks 1..n** — verified `min_rank=1, max_rank=20, n=20`. It works because PostgreSQL must materialise the window in sorted order, so the `LIMIT` truncates the already-ranked stream. It is implicit rather than guaranteed by the standard, so keep the assertion in the eval harness.
- **Do not pass the query vector through a CTE.** Writing `FROM disaster_narratives dn, params p ... ORDER BY dn.embedding <=> p.qvec` made the planner abandon HNSW for a Nested Loop plus Seq Scan plus Sort. Bind the vector directly as `%s::vector` in each arm.

### 3e. Rollout

Keep `_rag_search()` untouched as `_rag_search_legacy()` and select with a `USE_HYBRID_RAG` Heroku config var (default off until the eval set says otherwise). Reverting is a config change, not a deploy.

---

## Phase 4 — Query rewriting

**Do not put an LLM in the retrieval path.** The request budget is 24s against a 30s Heroku router kill (`api_orchestrator.py:300-304`), the embedding call alone was measured at 4.04s warm, and `/api/v1/simulate_calamity` already fans out to the Modal math engine in parallel. An extra LLM round-trip adds a failure mode and latency for a gain that rule-based expansion mostly captures. HyDE is deferred for the same reason.

Rewriting earns its place here because the taxonomy mismatch is real: `api_orchestrator.py:341-362` already hardcodes an EM-DAT → ReliefWeb type mapping (`"storm"` → `Storm, Storm Surge, Tropical Cyclone, Extratropical Cyclone, Severe Local Storm`). That knowledge currently steers only the SQL filter; it should also feed the FTS arm.

```python
TAXONOMY_SYNONYMS = {
    "flood":            ["flood", "flooding", "inundation", "deluge", "overflow"],
    "earthquake":       ["earthquake", "seismic", "tremor", "aftershock", "quake"],
    "storm":            ["storm", "cyclone", "typhoon", "hurricane", "surge"],
    "wildfire":         ["wildfire", "bushfire", "forest fire", "blaze"],
    "drought":          ["drought", "water scarcity", "crop failure"],
    "volcanic activity":["volcano", "volcanic", "eruption", "ashfall", "lava"],
}

def build_fts_text(disaster_type: str, country: str, query_text: str) -> str:
    """Text handed to plainto_tsquery. Synonyms widen the OR-query; the caller
    still swaps & for | so every term is optional."""
    terms = TAXONOMY_SYNONYMS.get(disaster_type.lower(), [disaster_type.lower()])
    return " ".join(terms + [country, query_text or ""])
```

Two things this deliberately does **not** do:

- It does not inject the year as a term. Years appear in narratives inconsistently and `event_year` is already a structured filter; adding `"2011"` to an OR-query mostly surfaces unrelated documents that happen to mention the number.
- It does not expand the semantic query with synonyms. `bge-large-en-v1.5` already places synonyms near each other in embedding space, so synonym stuffing on the dense side adds noise. Synonyms are a **sparse-arm** device only.

The dense arm keeps the existing instruction prefix, which is required by BGE: `"Represent this sentence for searching relevant passages: "` (`api_orchestrator.py:283`).

Measure this phase against the 6 taxonomy-mismatch eval queries specifically.

---

## Phase 5 — Reranking (blocked: no working provider on current infrastructure)

This is the phase most likely to be assumed easy, so here is what direct probing of the live HF router actually returned.

**Control — the embedding model still works:**
```
POST router.huggingface.co/hf-inference/models/BAAI/bge-large-en-v1.5
  -> HTTP 200 in 4.04s
```

**`cross-encoder/ms-marco-MiniLM-L-6-v2`:**
```
-> HTTP 400  {"error":"Model not supported by provider hf-inference"}
```

**`BAAI/bge-reranker-v2-m3`** — the HF API reports it as `status: live` on `hf-inference`, but with `task: "text-classification"`, which is the wrong pipeline for pair scoring:
```
{"inputs":[[query, doc]]}                     -> 400  "invalid inputs ... try {"text","text_pair"}"
{"inputs":{"text":q,"text_pair":d}}           -> 400  "TextClassificationPipeline.__call__()
                                                       missing 1 required positional argument"
{"inputs":{"source_sentence":q,"sentences":[…]}} -> 400
{"inputs":"query [SEP] doc"}                  -> 200  [[{"label":"LABEL_0","score":0.44}]]
POST .../bge-reranker-v2-m3/rerank            -> 404  Not Found
```

Only the concatenated-string form returns 200, and it yields a single-label classification score that does **not** use the model's pair-encoding path — it is not a usable relevance signal. **The batched-pairs reranker code in the first draft of this plan returns HTTP 400 and cannot work.**

Running a cross-encoder locally is also out: the dyno is Heroku **Basic (512 MB)** with `--workers 4`, so any model is loaded four times. `bge-reranker-v2-m3` is ~568M parameters (≈2.2 GB fp32) and cannot load once, let alone four times.

### Options, in order of preference

1. **Defer.** Phase 2's telemetry will report how often the candidate pool even exceeds the 3 results shown. With a mean of 11.9 rows per country, reranking may be reordering 7 candidates to pick 3 — near-zero return for real cost. **Decide this from data after Phase 2, not now.**
2. **A purpose-built rerank API** (Cohere Rerank, Jina Reranker, Voyage). All expose a proper `{query, documents}` contract. This adds a new vendor, a new key, and a new egress dependency in the hot path, so it needs approval.
3. **HF dedicated Inference Endpoint** — correct pipeline, but paid and always-on, which conflicts with the cost posture that drove removing the keep-warm thread.
4. **A small local cross-encoder** (e.g. 22M-param MiniLM, ~90 MB) only if `--workers` drops to 1. That trades throughput for reranking; not obviously worth it.

### If a provider is approved, the constraints are fixed

- **Hard 6s timeout**, and skip reranking entirely when the embedding call already consumed >14s. Never let reranking push the request past 24s.
- Failure must be non-fatal: log, return RRF order, continue. Same posture as the existing lexical fallback.
- **Do not truncate documents to 512 characters.** Measured p95 narrative length is 7,543 chars and 742 rows exceed 2,048; a 512-char window shows the reranker roughly 7% of a p95 document. Send the reranker the same window the embedding model sees (~2,048 chars) so the two stages judge the same text.

---

## Phase 6 — Latency budget and observability

### Measured components

| Stage | Measured | Note |
|---|---|---|
| HF embedding (warm) | 4.04 s | `wait_for_model=true`, HTTP 200 |
| Three-list RRF query | 4.57 ms exec / 0.69 ms plan | 30-candidate arms, production data |
| GIN index build | 242 ms | one-off |
| HNSW index build | 1,173 ms | one-off |
| `tsvector` column add | 2,889 ms | one-off, ACCESS EXCLUSIVE |
| Router kill | 30 s | upstream calls capped at 24 s |

Retrieval is not the latency problem — the embedding call is ~880x the cost of the fused SQL query. Optimisation effort belongs there, and the pool's `statement_timeout=10000` (`api_orchestrator.py:93`) already bounds the DB side with three orders of magnitude of headroom.

### Instrumentation

Record per-stage timings and the *decisions* taken, then return them in the existing `telemetry.rag_engine` block and log them as one structured line:

```python
"rag_engine": {
    "retrieval_method": "hybrid_rrf" | "vector_only" | "lexical_fallback",
    "embedding_ms": ..., "db_ms": ..., "rerank_ms": ...,
    "filter_tier_reached": 1,      # from Phase 2 — how much relaxation was needed
    "candidate_pool_size": 7,      # the number that decides if reranking is worth it
    "sparse_arm_used": True,       # False when the tsquery came out empty
    "rerank_skipped_reason": "no_provider" | "budget" | None,
}
```

`filter_tier_reached` and `candidate_pool_size` are the two fields that matter most: aggregated over real traffic they answer whether Phase 2 relaxation is firing and whether Phase 5 is worth building.

### Watchdog

`~/.hermes/scripts/calamity_watchdog.py` already runs hourly with four checks and alerts to Discord. Its existing end-to-end `/api/v1/simulate_calamity` probe can assert on the new telemetry — for example flag when `retrieval_method` falls back to `lexical_fallback` repeatedly, which currently passes silently. Note that its psql check has a 45s timeout and once fired a false positive from local WiFi degradation, so any new threshold should tolerate a single bad sample.

---

## 7. Risks

| Risk | Severity | Mitigation |
|---|---|---|
| Re-embedding 2,615 rows exhausts the HF free quota mid-run | High | Resumable by `unique_id`, checkpoint to disk, write to `embedding_v2`, keep `embedding` intact |
| `ALTER TABLE ADD COLUMN … GENERATED` takes ACCESS EXCLUSIVE for ~2.9s | Medium | Run in a quiet window; verified duration, not estimated |
| tsquery built with AND semantics | **High** | Measured 42x recall loss (28 vs 1,196 rows); use the `replace(…,'&','|')` form |
| Empty tsquery from stopword-only input | Medium | Verified to yield an empty query matching nothing; skip the sparse arm |
| Decay-as-multiplier silently reorders results | **High** | Measured 1.26x vs 1.31x range collision; use the three-list form |
| Query vector passed via CTE kills HNSW usage | Medium | Verified Seq Scan regression; bind `%s::vector` directly |
| Reranker assumed available | **High** | Falsified by probe; Phase 5 gated on a provider decision |
| tsquery injection | Low | `plainto_tsquery` sanitises; verified hostile input reduced to inert lexemes |
| Eval set unrepresentative | Medium | Seed from real queries; treat the 30 as a living set |

---

## 8. Decisions needed before implementation starts

1. **Phase 1 scope** — Option A (`[:500]` → `[:2000]`, 20.1% → 53.7% coverage, one line) alone, or go straight to chunking for ~100%? Recommendation: A first, measure, then decide on B.
2. **Re-embedding cost** — 2,615 HF calls against the free tier. Approve, or move embedding to a paid/self-hosted path first?
3. **Reranking** — defer pending Phase 2 pool data (recommended), or approve a third-party rerank API now?
4. **True BM25** — native FTS is TF-IDF-based and probably adequate at this corpus size. Installing ParadeDB `pg_search` on the Azure VM would give real BM25 but adds an extension to a box that currently has **no inbound SSH** (port 22 filtered; only 5432 open), so installation would have to go through `az vm run-command`. Worth it, or stay native?
5. **Recency weight** — start at 0.5 and tune on the eval set, or derive per-type weights from the existing `TIME_DECAY_PENALTY` values?

---

## 9. What changed from the first draft of this plan

Verification contradicted four substantive claims I had made:

- The reranker code (batched `[[query, doc]]` pairs to `bge-reranker-v2-m3`) **returns HTTP 400** and cannot work. Phase 5 went from "deploy last" to "blocked on a provider decision".
- The plan said it used OR semantics for recall but the SQL called `plainto_tsquery`, which is AND. Measured 42x recall gap.
- Time-decay as a post-fusion multiplier would have made decay the primary sort key, not a modifier.
- The phase order was wrong. Embedding coverage (79.9% of corpus text never vectorised) and candidate pool size (mean 11.9 rows per country) dominate ranking quality, so BM25 and reranking dropped below them.

## 10. References

- Retrieval: `scripts/production/api_orchestrator.py:193-260`; budget `:300-304`; taxonomy map `:341-362`; pool `:85-94`
- Embedding truncation: `scripts/production/live_ingestion.py:107-119`
- Config: `src/config.py:35-41`
- Verification scripts (committed, reproducible, no credentials — each wraps its work in `BEGIN … ROLLBACK`):
  `eval/verification/01_schema_indexes_rrf.sql`,
  `02_tsquery_semantics_hnsw_usage.sql`,
  `03_filter_selectivity.sql`,
  `04_three_list_rrf.sql`
  Run with `psql "$DSN" -f <file>`; production schema was confirmed unchanged afterwards (10 columns, 2 indexes, 2,615 rows).
- Project context: [[calamity-matrix-core-state]], [[calamity-azure-infra-facts]], [[calamity-hermes-monitoring]]

---

## 11. Execution log (2026-08-18)

All Phases 0–4 and 6 were implemented in `scripts/production/retrieval.py` (the
shared single source of truth imported by both `api_orchestrator.py` and the
eval runner) and measured against the frozen baseline. Phase 5 (reranking)
remains blocked on the provider decision from §5.

| Metric | Baseline (legacy, frozen) | Hybrid RRF + tier padding | Δ |
|---|---|---|---|
| recall@5 | 0.812 | **0.969** | +19.3% |
| recall@3 | 0.812 | **0.969** | +19.3% |
| MRR | 0.745 | **0.891** | +19.6% |
| nDCG@5 | 0.766 | **0.917** | +19.7% |
| latency p50 / p95 | 127.6 / 180.2 ms | 483.7 / 673.8 ms | 3.8x but trivial vs 24s budget |
| beyond500 recall@5 | 0.800 | **1.000** | +25% |
| exact recall@5 | 0.750 | **1.000** | +33% |
| smallpool recall@5 | 1.000 | **1.000** | — |
| mismatch recall@5 | 0.750 | **0.875** | +16.7% |

`eval/results/1787077801_hybrid.json` (full per-query breakdown). The regression
guard passed: no metric below 95% of baseline. **Decision (eval-driven):**
`USE_HYBRID_RAG=true` in production; `EMBEDDING_COLUMN=embedding_v2` once the
backfill + v2 eval confirm the coverage fix.

**Shipped state (deploy v56, `db338da`, 2026-08-18):** `embedding_v2` backfill
completed — all 2,615 rows re-embedded from the full 2,048-char window
(verified `count(*) FILTER (WHERE embedding_v2 IS NULL) = 0`). V2 eval
(`eval/results/1787079934_hybrid.json`): recall@5 0.969, MRR 0.875, nDCG@5
0.906, guard passed — statistically indistinguishable from v1 on this 32-query
set (the sparse FTS arm already captured the beyond-500 recall), so the switch
rests on the mechanical coverage fix, not on the eval delta. Both flags are ON
in production (`USE_HYBRID_RAG=1`, `EMBEDDING_COLUMN=embedding_v2`); rollback
is `heroku config:unset` on either flag. Live probes verified: Tohoku 2011
query → `hybrid_rrf`, strict tier reached, padded, 5 rows, cold-start embedding
14.5s inside the 24s budget, DB 1.9s over WAN.

**Schema changes applied to production** (verified):

```
embedding_v2 vector(1024)          -- backfill target, embedding intact as rollback
fts_vector tsvector GENERATED      -- IMMUTABLE 2-arg to_tsvector('english', narrative_text)
idx_dn_fts GIN (fts_vector)        -- sparse arm
idx_dn_embedding_hnsw HNSW(embedding_v2 vector_cosine_ops)  -- m=16 ef_construction=64
idx_dn_country_lower (lower(country))
idx_dn_type_year (disaster_type, event_year)
```

**First hybrid eval attempt failed the guard** (smallpool collapsed to 0.25:
`min_candidates=20` widened a 2-row Suriname pool into a 290-row wrong pool,
abandoning the truthful local rows). Fixed with tier padding — base pool is the
**strictest non-empty tier**, padded upward only to reach `top_k`, dedup by id.
Re-run: smallpool 1.000, all categories at or above baseline.

**Latency notes:** the DB side went from 128→484 ms p50 because hybrid runs 5
tier counts + up to 3 arms per tier, each with a 30-candidate LIMIT — that is
still ~20x inside the pool's `statement_timeout=10000` and ~50x inside the 24s
upstream budget where the embedding call alone costs ~4s.

---

## 12. Embedding-bridge incident plan — 2026-08-20

**Status:** PLAN ONLY. The investigation was read-only. No HF token change, Heroku config mutation, deployment, database write, recovery action, or rollback was performed.

**Incident:** Hermes job `7bb503232e6c` reported six consecutive production probes with `embedding_source="lexical_fallback"`:

```text
Calamity AI watchdog: problem detected
  - embedding bridge has been down 6 consecutive probes (lexical RAG only; HF quota may be exhausted)
```

**Safety constraint:** Do not roll back to the retired acc1 database. It is a stale copy. All remediation must target the active production path only after provider/account diagnosis.

### 12.1 Executive diagnosis

The active production database is healthy. The embedding provider is rejecting requests.

| Check | Evidence | Conclusion |
|---|---|---|
| Hermes streak | `~/.hermes/state/calamity_embed_source.json` = `{"consecutive_fallback": 6}`; hourly outputs at 19:01, 20:03, 21:08, 22:04 | Six consecutive semantic failures are real |
| Heroku application | `calamity-matrix-api`, current release v60, deployed commit `1448f70`; `/health` returned HTTP 200 | API process is alive |
| Heroku logs | Repeated `[retrieval] embedding bridge unavailable (HTTP 402); lexical fallback` | Provider returned Payment Required |
| Independent HF probe | Direct POST to the configured BGE endpoint returned HTTP 402 | Failure reproduces outside Heroku |
| API behavior | Watchdog's other checks passed; simulations returned non-empty historical context and numeric predictions | Graceful lexical degradation is functioning |
| Active database | Azure Account 2 PostgreSQL 18.4 / pgvector on port 5432; 2,615 rows; `embedding_v2` nulls = 0; `fts_vector` nulls = 0; `vector` extension present | Active DB is not the incident cause |

**Root-cause confidence:**

- **Confirmed:** Hugging Face embedding requests are persistently rejected with HTTP 402 by both production and an independent probe.
- **Not yet distinguished:** exhausted quota versus billing restriction versus account/token entitlement. The current bridge discards provider response bodies and exposes no failure reason in telemetry.
- **Ruled out for this alert:** retired acc1 database, active Azure row loss, missing v2 embeddings, missing FTS column, API process death, and general DNS failure.

### 12.2 Current failure path

```text
Hermes hourly watchdog
  -> POST /api/v1/simulate_calamity
  -> api_orchestrator.fetch_hf()
  -> retrieval.embed_query()
  -> Hugging Face BGE endpoint
  -> HTTP 402
  -> None
  -> hybrid retrieval without dense arm
  -> sparse/recency lexical fallback
  -> HTTP 200 + embedding_source=lexical_fallback
```

Relevant locations:

- `~/.hermes/scripts/calamity_watchdog.py:76-121`: end-to-end probe and fallback streak.
- `scripts/production/retrieval.py:97-132`: provider call, retries, normalization, generic fallback.
- `scripts/production/api_orchestrator.py:223-254`: parallel upstream calls and lexical degradation.
- `scripts/production/api_orchestrator.py:360-371`: current telemetry, which lacks provider status/reason/attempt fields.

### 12.3 Full-scan findings, ranked

#### P0 — provider outage confirmed; recovery decision still required

The HF account/token path is in a payment/quota failure class. Do not repeatedly retry or rotate arbitrary values. First check the HF account billing/quota/token entitlement through the provider dashboard or authorized status API, recording only model, timestamp, status class, and sanitized reason. Then explicitly choose one of:

1. Restore the existing HF entitlement/quota.
2. Approve a replacement embedding provider.
3. Operate lexical-only temporarily with an explicit degraded-service policy.

No database rollback is relevant to these choices.

#### P0 — retry budget contradicts the documented 24-second budget

`_hf_embed(timeout=24, retries=2)` can wait roughly 48 seconds before returning `None`, excluding overhead. Permanent 401/402/403 responses should not be retried. Transient retries must share one wall-clock deadline below Heroku's 30-second router ceiling.

#### P0 — provider failure reason is not observable

`retrieval.py` reduces non-200 responses to `HTTP <status>` and prints an unstructured line. API telemetry only says `semantic` or `lexical_fallback`; it cannot distinguish quota, invalid token, rate limit, timeout, provider outage, malformed payload, zero vector, or wrong dimension. Add safe internal fields such as `embedding_failure_reason`, `embedding_http_status`, `embedding_attempts`, and `embedding_deadline_ms`, never provider bodies or secrets.

#### P1 — vector contract validation is incomplete

The bridge accepts any numeric vector length, does not reject non-finite values, and can return fewer vectors than requested in a batch. Enforce exactly 1,024 finite, non-zero values and batch cardinality before vectors reach pgvector or the database.

#### P1 — health is liveness-only

`/health` returns unconditional alive. Docker/proxy health checks therefore remain green during HF outage, all-lexical retrieval, DB loss after startup, missing schema, or empty active vectors. Add separate bounded readiness/dependency health; keep liveness cheap.

#### P1 — watchdog and app do not prove the same DB identity

Hermes checks `~/.calamity_rollback/DATABASE_URL.new.rotated`, while Heroku uses its own `DATABASE_URL`. Both currently reach the intended active DB, but the check is not proof of app identity. Prefer app readiness or a safe fingerprint of host/database/user/schema, never a password or full DSN.

#### P1 — ingestion has weaker embedding safeguards

`live_ingestion.py:32-61` has no explicit HF timeout, retry policy, vector-shape validation, or failure counters; failed embeddings are skipped and the job can appear successful. New records copy the same vector into both columns, which can hide future v1/v2 input or model drift. Ingestion also lacks bounded timeouts on several source and DB calls.

#### P1 — outage-mode tests are absent

There is no active pytest suite or CI job for missing token, HTTP 402/429/5xx, timeout, malformed/zero/wrong-dimension vectors, fallback telemetry, watchdog streak, API contract, stale DB retry, or end-to-end degraded mode. The retrieval eval tests ranking quality with precomputed embeddings, not provider outages.

#### P2 — observability is not aggregated

Telemetry is returned to clients but not emitted as one structured RAG event or aggregated metric. Add fallback ratio by reason, provider status counts, embedding/total latency, zero-result rate, DB retry count, ingestion failures, and recovery transitions.

#### P2 — documentation and dependency drift

`INFRASTRUCTURE.md` and historical `ISSUES.md`/`CHANGELOG.md` still describe the removed HF keep-warm behavior and older deployment paths. `npm audit --omit=dev` reports four high-severity advisories (`nanoid`, `next`, `postcss`, `sharp`); no automatic fix was applied. These are separate maintenance work, not emergency recovery.

#### P2 — credential hygiene before next deployment

One audit config-print command failed to redact Heroku's padded `config` output. No secret is included in this plan, but the transcript must be treated as locally exposed. Before the next deploy, rotate affected provider/application credentials through the normal secret-management path and use field-aware redaction thereafter. Do not put values in logs, plans, graph memory, or commits.

### 12.4 Implementation phases

#### Phase A — freeze and provider decision

1. Keep `USE_HYBRID_RAG=1` and `EMBEDDING_COLUMN=embedding_v2`; do not alter the DB.
2. Preserve redacted watchdog, Heroku, and HF status evidence outside source-controlled secrets.
3. Classify the HF 402 through the provider account/billing/token status surface.
4. Choose restore, replacement provider, or approved lexical-only operation.
5. Rotate any credentials exposed by failed redaction before a new deployment.

**Exit criteria:** provider decision recorded; no active DB mutation; lexical fallback returns 200 with non-empty context; credential plan approved.

#### Phase B — harden the embedding client

1. Centralize query-time and ingestion embedding calls.
2. Enforce one absolute deadline at or below 24 seconds.
3. Do not retry permanent 4xx classes; retry only selected transient timeout, connection, 429, and 5xx classes with bounded backoff.
4. Return sanitized internal reason, status class, attempts, elapsed time, and model ID.
5. Validate exactly 1,024 finite numeric values, reject zero vectors, normalize once, and require batch cardinality.
6. Keep lexical fallback non-fatal and explicit.
7. Reconcile configured `EMBEDDING_MODEL` with the actual endpoint using an allowlist; avoid arbitrary URL injection.

**Exit criteria:** tests prove deadline, 402 no-retry, transient retry bounds, vector validation, and correct semantic/lexical telemetry.

#### Phase C — readiness, telemetry, watchdog

1. Add `/ready` or equivalent bounded DB-pool/schema dependency check; retain `/health` as liveness.
2. Emit structured RAG fields: request ID, source, failure reason/status, attempts, embedding/db/total latency, result count, active column, flags, and retry indicator.
3. Aggregate provider status, fallback, latency, zero-result, DB retry, and recovery metrics.
4. Extend watchdog state with timestamp, source, reason/status, streak start, and recovery timestamp.
5. Make watchdog consume app readiness plus a safe production identity fingerprint, or use a protected diagnostic endpoint; retain off-box DB/backup checks as separate checks.
6. Keep hysteresis and send an explicit recovery notification.

**Exit criteria:** a simulated provider outage generates bounded lexical response, configured alert, useful reason context, and a visible recovery transition.

#### Phase D — ingestion and data safeguards

1. Add HTTP/connect/database/statement timeouts to ingestion.
2. Reuse the validated canonical embedding client/input.
3. Count fetched, duplicate, embedded, failed, skipped, inserted, and conflict records.
4. Persist or surface failed IDs; do not report full success after embedding failures.
5. Define and document how new rows populate `embedding_v2`; do not blindly mirror columns.
6. Run post-ingestion checks for count, nulls, dimensions, finite values, norms, and indexes.

**Exit criteria:** forced provider failure leaves failed records uninserted, reports partial/failure status, and successful ingestion proves vector invariants.

#### Phase E — tests and eval gates

1. Mock missing token, 401, 402, 403, 429, 5xx, timeout, connection error, malformed JSON, empty/zero/non-finite/wrong-dimension vectors, and short batch response.
2. Assert API HTTP 200 degraded mode, non-empty context, explicit reason, and no false semantic source.
3. Add stale-pool, statement-timeout, missing-schema, and v2-null DB tests.
4. Add watchdog threshold, persistence, single-failure tolerance, and recovery tests.
5. Keep the 32-query hybrid/legacy eval and 95% guard; add absolute/category floors, both columns, dense/sparse/neither arms, tier/padding/no-result cases, and pinned fixtures.
6. Add a read-only production smoke probe asserting semantic and degraded-mode telemetry plus end-to-end latency.

**Exit criteria:** CI covers provider outage modes and retrieval quality; semantic cannot be claimed when the dense bridge failed.

#### Phase F — controlled restoration and canary

1. Deploy only after Phases B–E pass in test/staging.
2. Validate liveness, readiness, semantic simulation, deliberate fallback, latency, DB timing, result count, and structured logs.
3. Restore or replace provider entitlement through approved secret/config management.
4. Canary and monitor fallback ratio, provider status, latency, and DB health.
5. Limit rollback to release/config rollback; never point to acc1 or alter schema for provider recovery.
6. Close only after three consecutive semantic probes, a recovery alert, and a fresh hybrid smoke/eval result.

**Exit criteria:** canary is semantic, 402s are explained/resolved, active DB identity unchanged, and no H12/H10/pool regression exists.

#### Phase G — runbook and maintenance cleanup

1. Link this section from the Hermes monitoring memory/runbook.
2. Reconcile README, infrastructure, changelog, and historical issue language with current Heroku/v57, disabled keep-warm, hybrid/v2 flags, and lexical fallback behavior.
3. Document safe redaction, provider diagnosis, readiness, vector checks, and no-acc1 rollback rules.
4. Track frontend dependency advisories separately with Next.js compatibility/build checks.
5. Track Azure wildcard 5432/22 exposure and old git-history credential purge as separately approved security work.

### 12.5 Acceptance matrix

| Area | Must be true before incident closure |
|---|---|
| Provider | HF quota/token/billing cause classified; semantic request succeeds or approved replacement is active |
| Budget | Embedding attempts respect the 24-second total ceiling; 402 is not repeatedly retried |
| Fallback | Lexical mode returns 200 with non-empty context and explicit degraded telemetry |
| Vector safety | Query/ingestion vectors are exactly 1,024 finite, non-zero, normalized values; batch counts match |
| Database | Active Account 2 DB remains target; row/v2/FTS invariants healthy; no acc1 access |
| Health | Liveness and dependency readiness are separate and accurate |
| Watchdog | Alert has timestamp/reason/status, hysteresis, and recovery notification |
| Tests | Provider outage, fallback, DB retry, watchdog state, and retrieval quality tests pass |
| Security | Credentials exposed by failed redaction are rotated before next deploy; no secrets enter repo/memory/logs |
| Deployment | Canary semantic probes pass; no blind recovery or rollback occurs |

### 12.6 Explicit non-goals

- Do not roll back to acc1.
- Do not alter active PostgreSQL schema or delete/rebuild embeddings for this provider incident.
- Do not repeatedly call HF hoping a 402 clears.
- Do not add a keep-warm daemon; the previous one exhausted provider allowance and was intentionally removed.
- Do not install a new reranker or BM25 extension as emergency response.
- Do not treat HTTP 200 from `/health` as semantic health.
- Do not expose provider bodies, API keys, DSNs, or passwords in diagnostics.

### 12.7 Audit artifacts and reproducibility

Read-only evidence used:

- Hermes watchdog script, state, and job output under `~/.hermes/cron/output/7bb503232e6/`.
- Heroku app/release/log inspection for `calamity-matrix-api`, v60 / commit `1448f70`.
- Independent HF endpoint probe: HTTP 402 classification only; body not persisted in repository or plan.
- Active DB read-only checks: PostgreSQL 18.4, `postgres`, 2,615 rows, `embedding_v2` null count 0, `fts_vector` null count 0, `vector` extension present.
- Static checks: Python `compileall` passed; frontend `npm audit --omit=dev` reported four high-severity advisories (`nanoid`, `next`, `postcss`, `sharp`); no automatic fix applied.
- Repository was clean at audit start except pre-existing untracked local artifacts.

**Plan conclusion:** keep production running in lexical-degraded mode while the HF account/payment cause is resolved. The database is healthy and must remain untouched. First code work should harden status classification and deadlines, then readiness/telemetry/tests, before provider restoration or deployment.

