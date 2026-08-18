\set ON_ERROR_STOP off
\timing on

-- Everything happens inside a transaction we roll back, so production schema
-- is never actually modified. Non-concurrent CREATE INDEX is transactional in PG.
BEGIN;

-- TEST 1: does the GENERATED ALWAYS tsvector column from the plan actually
-- pass PG's immutability check? to_tsvector(regconfig, text) is IMMUTABLE but
-- to_tsvector(text) is only STABLE, so this is the make-or-break detail.
ALTER TABLE disaster_narratives
ADD COLUMN fts_vector tsvector GENERATED ALWAYS AS (
    setweight(to_tsvector('english', coalesce(narrative_text, '')), 'A') ||
    setweight(to_tsvector('english', coalesce(country, '')), 'B') ||
    setweight(to_tsvector('english', coalesce(disaster_type, '')), 'B')
) STORED;

\echo '=== TEST 1 result above: generated tsvector column ==='

CREATE INDEX idx_fts ON disaster_narratives USING GIN (fts_vector);
\echo '=== TEST 2: GIN index built ==='

CREATE INDEX idx_hnsw ON disaster_narratives
USING hnsw (embedding vector_cosine_ops) WITH (m = 16, ef_construction = 64);
\echo '=== TEST 3: HNSW index built ==='

-- TEST 4: the exact RRF query from the plan, with a real embedding pulled from
-- an existing row standing in for a query vector.
CREATE TEMP TABLE probe AS
SELECT embedding AS q FROM disaster_narratives WHERE event_year = 2011 AND embedding IS NOT NULL LIMIT 1;

\echo '=== TEST 4: plan RRF query verbatim ==='
WITH dense AS (
    SELECT id, ROW_NUMBER() OVER (ORDER BY embedding <=> (SELECT q FROM probe)) AS rank
    FROM disaster_narratives
    WHERE disaster_type = ANY(ARRAY['Earthquake']) AND country ILIKE 'Japan' AND event_year >= 2000
    LIMIT 20
),
sparse AS (
    SELECT id, ROW_NUMBER() OVER (ORDER BY ts_rank_cd(fts_vector, plainto_tsquery('english','earthquake tsunami'), 32) DESC) AS rank
    FROM disaster_narratives
    WHERE fts_vector @@ plainto_tsquery('english','earthquake tsunami')
      AND disaster_type = ANY(ARRAY['Earthquake']) AND country ILIKE 'Japan' AND event_year >= 2000
    LIMIT 20
),
rrf AS (
    SELECT id, COALESCE(SUM(1.0 / (60 + rank)), 0) AS rrf_score
    FROM (SELECT id, rank FROM dense UNION ALL SELECT id, rank FROM sparse) combined
    GROUP BY id
)
SELECT dn.id, dn.event_year, round(rrf.rrf_score, 6) AS rrf,
       round((rrf.rrf_score * (1.0 - 0.002 * ABS(dn.event_year - 2011)))::numeric, 6) AS final
FROM rrf JOIN disaster_narratives dn ON dn.id = rrf.id
ORDER BY final DESC LIMIT 5;

-- TEST 5: is the LIMIT-inside-CTE actually taking the TOP 20 by rank, or an
-- arbitrary 20? Compare the max rank that survives the CTE against 20.
\echo '=== TEST 5: does LIMIT 20 inside the CTE keep ranks 1..20? ==='
WITH dense AS (
    SELECT id, ROW_NUMBER() OVER (ORDER BY embedding <=> (SELECT q FROM probe)) AS rank
    FROM disaster_narratives
    WHERE event_year >= 2000
    LIMIT 20
)
SELECT min(rank) AS min_rank, max(rank) AS max_rank, count(*) AS n FROM dense;

-- TEST 6: RRF dynamic range vs the decay multiplier's dynamic range.
\echo '=== TEST 6: RRF range vs decay range (does decay swamp RRF?) ==='
SELECT round(1.0/(60+1), 6)  AS rrf_rank1,
       round(1.0/(60+20), 6) AS rrf_rank20,
       round((1.0/(60+1))/(1.0/(60+20)), 4) AS rrf_ratio_max,
       round((1.0 - 0.008*26)::numeric, 4) AS decay_worst_flood_2000_2026,
       round((1.0/(1.0 - 0.008*26))::numeric, 4) AS decay_ratio;

\echo '=== TEST 7: how many rows survive the MIN_EVENT_YEAR=2000 quarantine ==='
SELECT count(*) FILTER (WHERE event_year >= 2000) AS in_scope,
       count(*) FILTER (WHERE event_year < 2000)  AS quarantined,
       max(event_year) - 2000 AS max_year_delta_in_scope
FROM disaster_narratives;

ROLLBACK;
\echo '=== ROLLED BACK: production schema untouched ==='
