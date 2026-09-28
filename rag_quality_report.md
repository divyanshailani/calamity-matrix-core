# RAG Quality Report — Calamity Matrix Core

**Date:** 2026-09-27
**Method:** live probes against the production database (Azure VM, `disaster_narratives`, 3,226 rows as of 2026-09-27), the frozen 32-query retrieval eval (`eval/queries/eval_queries.jsonl`), and a production telemetry canary through the live Heroku API.
**Question answered:** "RAG is basic, lacks BM25, no ranking, and it's all been tested" — where the claim holds, where it doesn't, and what to fix.

---

## 1. Verdict in one paragraph

Production RAG is **not** a bare FTS fallback. It is a three-arm hybrid pipeline — pgvector HNSW dense (Fireworks Qwen3 8B, `embedding_fireworks` column) + PostgreSQL full-text sparse arm + recency arm — fused with Reciprocal Rank Fusion, with progressive filter relaxation (strictest non-empty tier first). What it is **not**: BM25. The sparse arm is `ts_rank_cd` over an OR-joined `plainto_tsquery` — a cover-data containment score with no term frequency and no inverse document frequency, so it contributes positional rank to the RRF, not a text-relevance score. A Qwen3 8B reranker is implemented and **evaluated** but is **off in production**: `USE_RERANKER` is not set on the app (`USE_HYBRID_RAG=1` and `EMBEDDING_COLUMN=embedding_v2` are — §2), and the deployed code's hybrid path is the pre-rerank version (v63, 2026-08-21 deploy). Frozen 32-query eval: hybrid+rerank MRR 0.930 vs hybrid 0.885, cost ≈$0.0003/request.

## 2. What production actually runs (verified, not assumed)

Canary `POST /api/v1/simulate_calamity` against `calamity-matrix-api-21d813c1e629.herokuapp.com` (2004 Indonesia tsunami payload) returned telemetry:

```
retrieval_method:        hybrid_rrf
embedding_source:        fireworks
embedding_column:        embedding_fireworks
filter_tier_reached:     no_year
candidate_pool_size:     91
embedding_ms:            283
db_ms:                   1940
average_cosine_similarity: 0.51
```

`heroku config` (verified 2026-09-27, CLI re-authenticated; app `calamity-matrix-api`): `USE_HYBRID_RAG=1` set, `EMBEDDING_COLUMN=embedding_v2` set, `FIREWORKS_API_KEY` + `HF_TOKEN` present, **`USE_RERANKER` absent** → code default OFF. `EMBEDDING_COLUMN=embedding_v2` is inert on the embedding path: the deployed orchestrator derives the column from the provider that produced the query embedding (`embed_meta.column`), and `PROVIDER_ORDER` resolves to Fireworks-primary because `FIREWORKS_API_KEY` is set and `EMBEDDING_PROVIDER_ORDER` is unset — hence the canary's `embedding_column: embedding_fireworks`. The config var only matters when no embedding is produced (lexical fallback). The DB behind the app (`52.140.120.90:5432/postgres`) is the same instance the probes and data fixes used, confirmed by host/port/db match. The rerank telemetry fields and `semantic_query` plumbing above remain uncommitted local work; enabling prod reranking is §10 #1.

Live code path (`scripts/production/retrieval.py`, 939 lines):

- `retrieve_hybrid()` — counts all filter tiers (`strict` country+type+year → `no_year` → `type_only` → `country_only` → `no_type` → `no_country` → `region` …), uses the **strictest non-empty tier** as the base pool, pads from broader tiers only if fewer than `top_k` rows.
- Three arms per tier, fused with RRF `k=60`:
  - **dense:** `ROW_NUMBER() OVER (ORDER BY embedding_fireworks <=> %s)` HNSW cosine
  - **sparse:** `ROW_NUMBER() OVER (ORDER BY ts_rank_cd(fts_vector, tsquery, 32) DESC)`
  - **recency:** `ROW_NUMBER() OVER (ORDER BY ABS(event_year - target_year))`, RRF weight 0.5
- Arms degrade gracefully: no embedding → sparse+recency; no tsquery → dense+recency; neither → legacy structured fallback.

## 3. The "BM25" claim: false, with receipts

The sparse arm is the closest thing to lexical ranking in the system. Measured against the live schema:

```sql
fts_vector tsvector GENERATED ALWAYS AS (
    setweight(to_tsvector('english', narrative_text), 'A')
    || setweight(to_tsvector('english', country), 'B')
    || setweight(to_tsvector('english', disaster_type), 'B')
);
CREATE INDEX idx_dn_fts ON disaster_narratives USING gin (fts_vector);
```

Query side (`retrieval.py:588, 749`):

```sql
tsquery = replace(plainto_tsquery('english', %s)::text, '&', '|')::tsquery
rank    = ts_rank_cd(fts_vector, tsquery, 32)
```

| BM25 property | What this does |
|---|---|
| Inverse document frequency (rare terms weigh more) | **Absent.** `tsvector` stores no document frequencies; there is no IDF computation anywhere. "tsunami" and "the" are equally weighted. |
| Term frequency (more occurrences → stronger signal) | **Absent.** `ts_rank_cd` uses *cover data*: each distinct matching word is counted **once** regardless of how many times it appears. |
| Length normalization | Partial: normalization flag 32 divides by (matching-terms + 1), and country/disaster_type get setweight B (default weight 1.0) vs narrative A (0.4) — so a country-name hit outscores a text hit. |
| Query handling | `plainto_tsquery` with `&`→`|` rewrite: OR-joined, no AND. Measured 42× recall difference AND→OR in earlier tuning; OR buys recall, spends discrimination. No prefix matching, no synonyms at the FTS layer. |

Net effect, measured on the live 3,226-row corpus:

- **OR-dilution:** `plainto_tsquery` OR-joined, "2004 tsunami killed" matches **548/3,226 rows (17%)**; "flood flood flood river" matches **1,446 rows (45%)** — the sparse arm's candidate pool is most of the table, and its `ROW_NUMBER` ranks carry little signal after RRF.
- **No IDF, in numbers:** `flood` appears in 43% of the corpus, `earthquake` in 19%, `river` in 17% — yet `ts_rank_cd` gives each matched term the same weight. `mangrove` appears in 2 rows; a "mangrove" query is indistinguishable from a "flood" query in scoring power.
- **Ranking swaps vs even vanilla Postgres ranking:** `ts_rank_cd(…, 32)` vs plain `ts_rank(…, 1|2)` (TF + length normalization) disagree on **10/10 top-10 positions** for three of four test queries. The current cover-data choice is not even a defensible variant — it is simply the one that was there.

Net effect: the sparse arm answers "how much of this query is contained in this row" and feeds that as a **positional rank** into the RRF — it does not answer "how relevant is this text" with any probabilistic scoring. It is a containment filter with a coarse rank, not BM25 and not TF-IDF.

**What upgrading to real BM25 would mean in Postgres:** pgvector can't. Options are (a) hand-rolled IDF — maintain a `term_stats(term, df)` table refreshed by the weekly ingestion job, join at query time, rank with `ts_rank × log(1 + N/df)`; (b) move the lexical arm out to a real inverted index (`pg_search`/Tantivy, Meilisearch, Typesense) which ships true BM25; (c) stop — the dense arm + Qwen3 reranker already carry quality (§4), so the lexical arm may only need its OR-dilution and setweight defects fixed, not a BM25 rebuild. §10 ranks these by cost.

## 4. The reranker: implemented, evaluated, off in prod

`retrieval.py` carries a full Qwen3 8B rerank path (`/rerank`, 5 docs, relevance score), default **off** in code (`USE_RERANKER` env flag; `.env.example` ships it on for local use). Eval, frozen 32 queries, Fireworks Qwen3 embeddings, hybrid RRF base:

| config | MRR | recall@5 | recall@13 | p50 | p95 | rerank tokens |
|---|---|---|---|---|---|---|
| legacy multi-pass | 0.781 | 0.854 | 0.901 | 180 ms | 127 ms | — |
| hybrid RRF (rerank off) | 0.885 | 0.958 | 0.958 | 717 ms | 988 ms | 0 |
| hybrid RRF + rerank | **0.930** | 0.948 | 0.958 | 2524 ms | 4322 ms | 204,867 (whole run) |

Per-query diff rerank on vs off: **4 improved** (`beyond500_1`, `beyond500_8`, `exact_11`, `exact_13` — all from ≤0.5 to 1.0), **1 regressed** (`q_mismatch_28`: near-exact-match query "sudden flash flooding of the valley"; the gold doc was rank 1 off-rerank, dropped to #4 by the reranker → MRR 1.0 → 0.25). Net MRR **+0.045**, recall@5 −0.010 (within noise; same set, different order).

Cost at Fireworks' $0.20/M reranker tokens (plan §1.3 screenshot): 204,867 tokens for the entire 32-query eval run ≈ **$0.041 total**; a typical production request (5 docs × ~300 tokens) ≈ 1,700 tokens ≈ **$0.0003/request**. Negligible against a $0 budget only because traffic is low; it scales linearly.

Latency is the real price: p50 0.7 s → 2.5 s. The endpoint budget is 24 s (under Heroku's 30 s H12 ceiling) with embedding ~0.3 s, so there is headroom, but p95 4.3 s rerank + cold embedding could stack uncomfortably.

## 5. Recency decay: the `DECAY_*` env vars are decorative in the active path

`src/config.py` defines `TIME_DECAY_PENALTY` (`DECAY_EARTHQUAKE=0.002`, `DECAY_FLOOD=0.008`, `DECAY_DEFAULT=0.005`), but `grep` shows they are consumed **only by the legacy multi-pass path** (`build_scalar_query`). The hybrid path's recency arm is `ORDER BY ABS(event_year - target)` → a **positional** RRF arm (weight 0.5), not the multiplicative year penalty the env vars suggest.

Probe (hybrid, rerank on, live DB): China-flood query at `recency_weight=0.5` vs `0.0` returned **byte-identical top-5** — with a 0.93-MRR reranker deciding final order, the recency arm's RRF contribution is not moving top-k at all. The decay knobs and the RRF weight are currently dead levers on the dominant path.

## 6. Country resolution: exact-match dict, no fuzziness

`resolve_country()` in `retrieval.py` is a **5-entry alias map** (keys: `Turkey`, `Russia`, `US`, `USA`, `Vietnam` → canonical names) plus `REGION_COUNTRIES` tier membership. `grep -r pycountry` across `scripts/`: **zero hits** — the fuzzy-resolution fallback claimed in AGENTS.md Phase 24 (Issue 13) is not in the code.

Probe: `country="Vet Nam"` → alias map miss → falls through to the region tier (pool 498), top-5 are all Indonesian/other-Southeast-Asia rows; **zero Vietnam rows in top-5**. The UI country dropdown (fixed list) makes typos unlikely through the normal flow, but the field is API-exposed and the alias set is 5 of ~195 countries.

## 7. Data defects found and fixed this session

`scripts/production/fix_country_rows.py` (new, dry-run by default, Nominatim cache in `eval/.nominatim_reverse_cache.json`):

1. **Country normalization** (applied): `"USA"` → `"United States of America"` (4 rows), `"Vietnam"` → `"Viet Nam"`, `Türkiye`/`Russian Federation` normalization, so the alias map stops carrying row-level dirt.
2. **Unknown-country backfill** (applied, `--apply`): 546 rows with `country='Unknown'` but valid lat/lng → Nominatim reverse-geocode at 1 req/s (policy), zoom=10, cached and resumable. Result: **522/551 rows resolved and APPLIED** (519 of 548 unique coordinates returned a country; the remaining 29 rows sit in sea/unresolvable coordinates Nominatim can't map at zoom 10).
3. **Unfixable tail:** 45 rows with **null coordinates** and 29 with sea/unresolvable coordinates → **74 `Unknown` rows remain** out of 3,226 (2.3%). The 45 need a source with location (manual or ReliefWeb re-fetch); the 29 are a coordinate-accuracy problem, not a data-missing problem.

Post-fix probe verification: see §9.

## 8. Handcrafted probes (pre-fix baseline, rerank on, Fireworks)

| probe | result |
|---|---|
| exact control: "2004 tsunami that killed over 200000 people", Indonesia | 2004 tsunami **rank 1**, cos 0.663 ✓ |
| synonym: "tsunami" query vs earthquake-tagged gold doc | rank 1, cos 0.721 ✓ |
| typo: `country="Vet Nam"` | **fail** — region-tier fallback, no Vietnam in top-5 (§6) |
| low lexical overlap: "Which villages in the Sunda Strait were submerged by a 17-meter wave?" | 2004 tsunami rank 1 ✓ (dense arm carries it) |
| decay 0.5 vs 0.0 | identical top-5 (§5) |

The dense arm is doing the heavy lifting; the sparse arm adds mostly the country/type containment the tier filter already enforces.

## 9. Post-fix probe verification

Re-ran the §8 probe suite after applying both fixes (rerank on, Fireworks):

| probe | pre-fix | post-fix |
|---|---|---|
| exact control | 2004 tsunami rank 1, cos 0.663 | unchanged ✓ |
| synonym "tsunami" | rank 1, cos 0.721 | unchanged ✓ |
| typo `country="Vet Nam"` | no Vietnam in top-5 | **unchanged** — alias map still 5 entries, no fuzziness (§6, fix #4) |
| low lexical overlap | 2004 tsunami rank 1 | unchanged ✓ |
| decay 0.5 vs 0.0 | identical top-5 | still identical (§5 — dead lever, not a data problem) |

The data fixes remove a **retrieval-input defect** (country containment tier + FTS B-terms now see real country names on 522 rows instead of `Unknown`) but do not change ranking *behavior*, which is why the probes are stable rather than improved: the dominant arm is dense (Qwen3 embeddings over `narrative_text`), which never read the `country` column. The fix pays off on country-filtered queries and on the sparse arm's B-weighted containment, where `Unknown` previously contributed zero signal.

## 10. Recommendations, ranked by cost

1. **Deploy the local rerank wiring + set `USE_RERANKER=1`.** Zero new infra, +0.045 MRR, ~$0.0003/req, +1.8 s p50 latency (headroom exists under the 24 s budget). The known regression (near-exact-match demotion, `q_mismatch_28`) is one of 32 eval queries; acceptable, monitor.
2. **Cheap FTS upgrade in place** (one code line + one DDL, no new infra): switch the sparse arm from `ts_rank_cd … ,32)` to `ts_rank(fts_vector, tsquery, 1|2)` (adds TF + document-length normalization), and re-weight the generated column to narrative=A/B, country/type=C. The reweight requires `ALTER TABLE disaster_narratives DROP COLUMN fts_vector` and re-adding the generated column with the new setweights — a full table rewrite, but ~30 s on 3,226 rows. Expected: better sparse-arm signal feeding RRF; measure with the frozen eval before/after.
3. **Hand-rolled IDF** if #2 isn't enough: `term_stats(term, df)` table refreshed by the weekly ingestion job; sparse score `ts_rank × log(1 + N/df)`. ~50 lines, one nightly/weekly job, still in-database.
4. **Country fuzziness:** add `pycountry.countries.search_fuzzy` fallback in `resolve_country` (the Phase 24 claim, actually implement it). 1 dependency, 10 lines.
5. **Recency:** either wire `DECAY_*` into the hybrid path as a real score multiplier or delete the env vars; today they are documentation of intent, not behavior.
6. **Null-coord rows** (~45): re-fetch location from ReliefWeb/EM-DAT source of record; Nominatim can't help.

## 11. Applied 2026-09-28: recommendation #2 (code line + DDL)

Both halves of #2 are now in place; frozen-eval A/B is byte-identical, so the
change is neutral on the 32-query set and kept as the report's recommended
end state (narrative=A, country/type=C).

**Code** (working tree, committed as part of the splice-repair commit):
sparse arm is now `ts_rank(fts_vector, tsquery, 1|2)` — TF + document-length
normalization instead of `ts_rank_cd … ,32)`.

**DDL** (applied to prod 2026-09-28 via
`scripts/production/reweight_fts_vector.py --apply`, 4.7 s, GIN index
rebuilt, `ANALYZE` after):

```sql
ALTER TABLE disaster_narratives DROP COLUMN fts_vector;
ALTER TABLE disaster_narratives ADD COLUMN fts_vector tsvector
  GENERATED ALWAYS AS (
    setweight(to_tsvector('english', COALESCE(narrative_text, '')), 'A')
    || setweight(to_tsvector('english', COALESCE(country, '')), 'C')
    || setweight(to_tsvector('english', COALESCE(disaster_type, '')), 'C')) STORED;
CREATE INDEX idx_dn_fts ON disaster_narratives USING gin (fts_vector);
```

Pre-apply state was narrative=A, country/type=B (verified with `pg_get_expr`
before the change). 3,226/3,226 rows repopulated. `--rollback` restores the
old weights if a wider eval ever shows a regression.

**Frozen eval (32 queries, Fireworks column, rerank unkeyed = pure RRF):**

| run | weights | mrr | recall@5 | ndcg@5 | p50/p95 |
|---|---|---|---|---|---|
| 1790577725 (pre) | A/B/B | 0.875 | 0.927 | 0.886 | 541/708 ms |
| 1790577781 (post) | A/C/C | 0.875 | 0.927 | 0.886 | 561/720 ms |

0/32 per-query differences; no regressions vs `eval/baseline.json`. Matches
the 1790543574/851 post-repair numbers exactly, confirming the DDL variable
was the only thing between pre and post.
