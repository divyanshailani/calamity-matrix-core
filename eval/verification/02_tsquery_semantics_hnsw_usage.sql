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
CREATE INDEX idx_fts ON disaster_narratives USING GIN (fts_vector);
ANALYZE disaster_narratives;

CREATE TEMP TABLE probe AS
SELECT embedding AS q FROM disaster_narratives WHERE event_year = 2011 AND embedding IS NOT NULL LIMIT 1;

\echo '### A. tsquery operator semantics: AND or OR?'
SELECT plainto_tsquery('english','earthquake tsunami damage') AS plainto,
       websearch_to_tsquery('english','earthquake tsunami damage') AS websearch;

\echo '### B. recall consequence of AND semantics (rows matching, in scope)'
SELECT
  count(*) FILTER (WHERE fts_vector @@ plainto_tsquery('english','earthquake tsunami damage')) AS and_semantics,
  count(*) FILTER (WHERE fts_vector @@ to_tsquery('english','earthquake | tsunami | damage')) AS or_semantics
FROM disaster_narratives WHERE event_year >= 2000;

\echo '### C. does ROW_NUMBER() OVER (ORDER BY <=>) still use the HNSW index?'
EXPLAIN (ANALYZE, COSTS OFF, TIMING OFF, SUMMARY OFF)
WITH dense AS (
    SELECT id, ROW_NUMBER() OVER (ORDER BY embedding <=> (SELECT q FROM probe)) AS rank
    FROM disaster_narratives WHERE event_year >= 2000
    LIMIT 20
) SELECT * FROM dense;

\echo '### D. plain ORDER BY ... LIMIT (no window) for comparison'
EXPLAIN (ANALYZE, COSTS OFF, TIMING OFF, SUMMARY OFF)
SELECT id FROM disaster_narratives WHERE event_year >= 2000
ORDER BY embedding <=> (SELECT q FROM probe) LIMIT 20;

\echo '### E. does the metadata filter push into HNSW, or over-filter after it?'
EXPLAIN (ANALYZE, COSTS OFF, TIMING OFF, SUMMARY OFF)
SELECT id FROM disaster_narratives
WHERE disaster_type = ANY(ARRAY['Earthquake']) AND country ILIKE 'Japan' AND event_year >= 2000
ORDER BY embedding <=> (SELECT q FROM probe) LIMIT 20;

ROLLBACK;
