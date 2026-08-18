\timing on
BEGIN;
ALTER TABLE disaster_narratives
ADD COLUMN fts_vector tsvector GENERATED ALWAYS AS (
    setweight(to_tsvector('english', coalesce(narrative_text, '')), 'A') ||
    setweight(to_tsvector('english', coalesce(country, '')), 'B') ||
    setweight(to_tsvector('english', coalesce(disaster_type, '')), 'B')
) STORED;
CREATE INDEX idx_hnsw ON disaster_narratives
USING hnsw (embedding vector_cosine_ops) WITH (m = 16, ef_construction = 64);
ANALYZE disaster_narratives;
CREATE TEMP TABLE probe AS
SELECT embedding AS q FROM disaster_narratives WHERE event_year=2011 AND embedding IS NOT NULL LIMIT 1;

\echo '### F. ground truth: how many rows actually match the Japan/Earthquake filter?'
SELECT count(*) AS true_matching_rows FROM disaster_narratives
WHERE disaster_type = ANY(ARRAY['Earthquake']) AND country ILIKE 'Japan' AND event_year >= 2000;

\echo '### G. filtered HNSW: how many does it return for LIMIT 20? (under-return check)'
SELECT count(*) AS hnsw_returned FROM (
  SELECT id FROM disaster_narratives
  WHERE disaster_type = ANY(ARRAY['Earthquake']) AND country ILIKE 'Japan' AND event_year >= 2000
  ORDER BY embedding <=> (SELECT q FROM probe) LIMIT 20) s;

\echo '### H. same filter but forcing seqscan (exact, no ANN) for comparison'
SET LOCAL enable_indexscan = off;
SELECT count(*) AS exact_returned FROM (
  SELECT id FROM disaster_narratives
  WHERE disaster_type = ANY(ARRAY['Earthquake']) AND country ILIKE 'Japan' AND event_year >= 2000
  ORDER BY embedding <=> (SELECT q FROM probe) LIMIT 20) s;
SET LOCAL enable_indexscan = on;

\echo '### I. a broader, less selective filter (Flood, any country) under HNSW'
SELECT (SELECT count(*) FROM disaster_narratives WHERE disaster_type='Flood' AND event_year>=2000) AS true_rows,
       (SELECT count(*) FROM (SELECT id FROM disaster_narratives WHERE disaster_type='Flood' AND event_year>=2000
          ORDER BY embedding <=> (SELECT q FROM probe) LIMIT 20) s) AS hnsw_returned;

\echo '### J. country cardinality — is ILIKE country a selective filter in general?'
SELECT round(avg(c),1) AS avg_rows_per_country, min(c) AS min_c, max(c) AS max_c, count(*) AS n_countries
FROM (SELECT country, count(*) c FROM disaster_narratives WHERE event_year>=2000 GROUP BY country) t;

\echo '### K. does ILIKE with no wildcard prevent btree/index use on country?'
EXPLAIN (COSTS OFF) SELECT id FROM disaster_narratives WHERE country ILIKE 'Japan';

ROLLBACK;
