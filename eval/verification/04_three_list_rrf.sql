\timing on
BEGIN;
ALTER TABLE disaster_narratives
ADD COLUMN fts_vector tsvector GENERATED ALWAYS AS (
    setweight(to_tsvector('english', coalesce(narrative_text,'')),'A') ||
    setweight(to_tsvector('english', coalesce(country,'')),'B') ||
    setweight(to_tsvector('english', coalesce(disaster_type,'')),'B')) STORED;
CREATE INDEX idx_fts ON disaster_narratives USING GIN (fts_vector);
CREATE INDEX idx_hnsw ON disaster_narratives USING hnsw (embedding vector_cosine_ops) WITH (m=16, ef_construction=64);
ANALYZE disaster_narratives;
CREATE TEMP TABLE probe AS SELECT embedding AS q FROM disaster_narratives WHERE event_year=2011 AND embedding IS NOT NULL LIMIT 1;

\echo '### THREE-LIST RRF (dense + sparse + recency), relaxed pool: type only'
EXPLAIN (ANALYZE, COSTS OFF, TIMING OFF, SUMMARY ON)
WITH params AS (
  SELECT (SELECT q FROM probe) AS qvec,
         replace(plainto_tsquery('english','coastal tsunami inundation damage')::text,'&','|')::tsquery AS qts,
         2011 AS target_year
),
dense AS (
  SELECT dn.id, ROW_NUMBER() OVER (ORDER BY dn.embedding <=> p.qvec) AS rank
  FROM disaster_narratives dn, params p
  WHERE dn.disaster_type = ANY(ARRAY['Earthquake']) AND dn.event_year >= 2000
  LIMIT 30
),
sparse AS (
  SELECT dn.id, ROW_NUMBER() OVER (ORDER BY ts_rank_cd(dn.fts_vector, p.qts, 32) DESC) AS rank
  FROM disaster_narratives dn, params p
  WHERE dn.fts_vector @@ p.qts AND dn.disaster_type = ANY(ARRAY['Earthquake']) AND dn.event_year >= 2000
  LIMIT 30
),
recency AS (
  SELECT dn.id, ROW_NUMBER() OVER (ORDER BY ABS(dn.event_year - p.target_year)) AS rank
  FROM disaster_narratives dn, params p
  WHERE dn.disaster_type = ANY(ARRAY['Earthquake']) AND dn.event_year >= 2000
  LIMIT 30
)
SELECT dn.id, dn.country, dn.event_year,
       round(SUM(w)::numeric, 6) AS rrf
FROM (
  SELECT id, 1.0/(60+rank)        AS w FROM dense
  UNION ALL
  SELECT id, 1.0/(60+rank)        AS w FROM sparse
  UNION ALL
  SELECT id, 0.5*(1.0/(60+rank))  AS w FROM recency
) f JOIN disaster_narratives dn ON dn.id = f.id
GROUP BY dn.id, dn.country, dn.event_year
ORDER BY rrf DESC LIMIT 5;

\echo '### same query, actual rows'
WITH params AS (
  SELECT (SELECT q FROM probe) AS qvec,
         replace(plainto_tsquery('english','coastal tsunami inundation damage')::text,'&','|')::tsquery AS qts,
         2011 AS target_year),
dense AS (SELECT dn.id, ROW_NUMBER() OVER (ORDER BY dn.embedding <=> p.qvec) AS rank
  FROM disaster_narratives dn, params p WHERE dn.disaster_type=ANY(ARRAY['Earthquake']) AND dn.event_year>=2000 LIMIT 30),
sparse AS (SELECT dn.id, ROW_NUMBER() OVER (ORDER BY ts_rank_cd(dn.fts_vector,p.qts,32) DESC) AS rank
  FROM disaster_narratives dn, params p WHERE dn.fts_vector @@ p.qts AND dn.disaster_type=ANY(ARRAY['Earthquake']) AND dn.event_year>=2000 LIMIT 30),
recency AS (SELECT dn.id, ROW_NUMBER() OVER (ORDER BY ABS(dn.event_year-p.target_year)) AS rank
  FROM disaster_narratives dn, params p WHERE dn.disaster_type=ANY(ARRAY['Earthquake']) AND dn.event_year>=2000 LIMIT 30)
SELECT dn.id, dn.country, dn.event_year, round(SUM(w)::numeric,6) AS rrf,
       count(*) AS lists_hit
FROM (SELECT id,1.0/(60+rank) w FROM dense UNION ALL SELECT id,1.0/(60+rank) w FROM sparse
      UNION ALL SELECT id,0.5*(1.0/(60+rank)) w FROM recency) f
JOIN disaster_narratives dn ON dn.id=f.id
GROUP BY dn.id, dn.country, dn.event_year ORDER BY rrf DESC LIMIT 8;
ROLLBACK;
