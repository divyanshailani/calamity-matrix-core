"""Shared retrieval layer for the Calamity orchestrator and the eval harness.

Single source of truth: api_orchestrator.py and scripts/eval/run_retrieval_eval.py
both import their retrieval logic from here, so the evaluation harness cannot
drift from what production actually runs.

Env knobs (read directly so the eval tools work without a full Heroku env):
  EMBEDDING_COLUMN  'embedding' (default, current behaviour) | 'embedding_v2'
  USE_HYBRID_RAG    1/true/yes  -> hybrid three-list RRF pipeline
  HF_TOKEN, MIN_EVENT_YEAR, DECAY_*  (mirror src/config.py defaults)
"""
import os
import re

import requests

import psycopg2

HF_EMBED_URL = "https://router.huggingface.co/hf-inference/models/BAAI/bge-large-en-v1.5"
INSTRUCTION_PREFIX = "Represent this sentence for searching relevant passages: "

MIN_EVENT_YEAR = int(os.getenv("MIN_EVENT_YEAR", "2000"))
EMBEDDING_COLUMN = os.getenv("EMBEDDING_COLUMN", "embedding")
USE_HYBRID_RAG = os.getenv("USE_HYBRID_RAG", "").lower() in ("1", "true", "yes")
HF_TOKEN = os.getenv("HF_TOKEN", "")

# Mirrors src/config.py TIME_DECAY_PENALTY defaults.
DECAY_DEFAULTS = {
    "earthquake": float(os.getenv("DECAY_EARTHQUAKE", "0.002")),
    "flood": float(os.getenv("DECAY_FLOOD", "0.008")),
    "default": float(os.getenv("DECAY_DEFAULT", "0.005")),
}

# Only these column names may be interpolated into SQL.
_VALID_EMBED_COLUMNS = ("embedding", "embedding_v2")

_COLUMNS = "date, country, disaster_type, narrative_text, event_year, lat, lng"


def _embed_col():
    if EMBEDDING_COLUMN not in _VALID_EMBED_COLUMNS:
        raise ValueError(f"unsafe EMBEDDING_COLUMN: {EMBEDDING_COLUMN!r}")
    return EMBEDDING_COLUMN


# ---------------------------------------------------------------------------
# Country / taxonomy normalisation (moved verbatim from api_orchestrator.py so
# the eval harness uses the exact same mapping the API uses)
# ---------------------------------------------------------------------------

COUNTRY_ALIASES = {
    "Turkey": "Türkiye",
    "Russia": "Russian Federation",
    "US": "United States of America",
    "USA": "United States of America",
    "Vietnam": "Viet Nam",
}


def resolve_country(name: str, lower: bool = False):
    resolved = COUNTRY_ALIASES.get(name, name)
    return resolved.lower() if lower else resolved


RW_TYPE_MAP = {
    "earthquake": ["Earthquake"],
    "flood": ["Flood", "Flash Flood"],
    "extreme temperature": ["Heat Wave", "Cold Wave", "Extreme temperature"],
    "storm": ["Storm", "Storm Surge", "Tropical Cyclone", "Extratropical Cyclone", "Severe Local Storm"],
    "mass movement (wet)": ["Mud Slide", "Land Slide", "Mass movement (wet)"],
    "mass movement (dry)": ["Land Slide", "Mass movement (dry)"],
    "volcanic activity": ["Volcano", "Volcanic activity"],
    "wildfire": ["Wild Fire", "Fire", "Wildfire"],
    "drought": ["Drought"],
}


def build_rw_types(disaster_type: str):
    """EM-DAT taxonomy -> ReliefWeb taxonomy (moved from api_orchestrator.py:341-362)."""
    return RW_TYPE_MAP.get(disaster_type.lower(), [disaster_type])


def decay_factor_for(disaster_type: str) -> float:
    dt_lower = disaster_type.lower()
    return DECAY_DEFAULTS.get(dt_lower, DECAY_DEFAULTS["default"])


def build_semantic_query(disaster_type: str, country: str, event_year: int, query_text: str) -> str:
    """Exact replica of the orchestrator's master_semantic_query construction."""
    return f"{disaster_type} in {country} (Year: {event_year}). Additional Context: {query_text}"


# ---------------------------------------------------------------------------
# Embeddings (Hugging Face router, BAAI/bge-large-en-v1.5)
# ---------------------------------------------------------------------------

def _hf_embed(texts, timeout=24, retries=2):
    """Return normalized 1024-dim vectors for a list of texts, or None on failure."""
    if not HF_TOKEN:
        return None
    body = {"inputs": texts if isinstance(texts, list) else [texts],
            "options": {"wait_for_model": True}}
    headers = {"Authorization": f"Bearer {HF_TOKEN}"}
    last_err = None
    for attempt in range(retries):
        try:
            resp = requests.post(HF_EMBED_URL, headers=headers, json=body, timeout=timeout)
            if resp.status_code != 200:
                last_err = f"HTTP {resp.status_code}"
                continue
            data = resp.json()
            if not isinstance(data, list) or not data:
                last_err = "malformed response"
                continue
            out = []
            for item in (data if isinstance(texts, list) else [data]):
                if isinstance(item, list) and item and isinstance(item[0], (int, float)):
                    vec = item
                elif isinstance(item, list) and item and isinstance(item[0], list):
                    vec = item[0]  # batch outer list
                else:
                    continue
                norm = sum(x * x for x in vec) ** 0.5
                if norm > 0:
                    out.append([x / norm for x in vec])
            if out:
                return out if isinstance(texts, list) else out[0]
            last_err = "zero vectors produced"
        except requests.RequestException as e:
            last_err = f"{type(e).__name__}: {e}"
    print(f"[retrieval] embedding bridge unavailable ({last_err}); lexical fallback")
    return None


def embed_query(text, timeout=24):
    """Single-text embedding with the BGE instruction prefix."""
    return _hf_embed(INSTRUCTION_PREFIX + text, timeout=timeout)


def embed_many(texts, timeout=60):
    """Batch embedding; each text gets the BGE instruction prefix."""
    return _hf_embed([INSTRUCTION_PREFIX + t for t in texts], timeout=timeout)


# ---------------------------------------------------------------------------
# Sparse-arm query construction (Phase 4 query rewriting)
# ---------------------------------------------------------------------------

TAXONOMY_SYNONYMS = {
    "flood": ["flood", "flooding", "inundation", "deluge", "overflow"],
    "earthquake": ["earthquake", "seismic", "tremor", "aftershock", "quake"],
    "storm": ["storm", "cyclone", "typhoon", "hurricane", "surge"],
    "wildfire": ["wildfire", "bushfire", "forest fire", "blaze"],
    "drought": ["drought", "water scarcity", "crop failure"],
    "volcanic activity": ["volcano", "volcanic", "eruption", "ashfall", "lava"],
}

# same window generator
def build_fts_text(disaster_type: str, country: str, query_text: str) -> str:
    """User query -> text handed to plainto_tsquery for the sparse arm.

    Taxonomies are expanded with synonyms (the caller's replace('&','|') ORs
    them all, so extra terms only ever add recall, never require it). Years are
    deliberately NOT added: event_year is already a structured filter, and a
    bare '2011' in an OR-query surfaces unrelated documents.
    """
    terms = list(TAXONOMY_SYNONYMS.get(disaster_type.lower(), [disaster_type]))
    terms.append(country)
    if query_text and query_text.strip():
        terms.append(query_text)
    return " ".join(t for t in terms if t and t.strip())


TSQUERY_SQL = "replace(plainto_tsquery('english', %s)::text, '&', '|')::tsquery"
"""OR-joined tsquery: plainto_tsquery sanitises the input, the replace widens it
from AND to OR semantics (measured 42x recall difference), and the result is
empty (matches nothing) for stopword-only or empty input."""


def _has_terms(tsquery_text: str) -> bool:
    return bool(tsquery_text and tsquery_text.strip())


# ---------------------------------------------------------------------------
# Filter-tier relaxation (Phase 2). Returns (where_sql, params, label).
# ---------------------------------------------------------------------------

def _tier_where(tier: str, rw_types, country, event_year, region_list):
    base = f"event_year >= {MIN_EVENT_YEAR}"
    if tier == "strict":
        return (f"{base} AND disaster_type = ANY(%s) AND lower(country) = lower(%s) AND event_year = %s",
                [rw_types, country, event_year])
    if tier == "no_year":
        return (f"{base} AND disaster_type = ANY(%s) AND lower(country) = lower(%s)", [rw_types, country])
    if tier == "country":
        return (f"{base} AND lower(country) = lower(%s)", [country])
    if tier == "type":
        return (f"{base} AND disaster_type = ANY(%s)", [rw_types])
    if tier == "region":
        mapped = [c for c in region_list if c]
        if not mapped:
            return (f"{base} AND disaster_type = ANY(%s)", [rw_types])
        return (f"{base} AND disaster_type = ANY(%s) AND lower(country) = ANY(%s)",
                [rw_types, mapped])
    raise ValueError(tier)


# Widen along the country axis before the type axis: dropping the country loses
# the user's geography, dropping the type keeps at least the right place.
TIER_ORDER = ["strict", "no_year", "country", "region", "type"]


# ---------------------------------------------------------------------------
# Retrieval implementations
# ---------------------------------------------------------------------------

def retrieve_legacy(conn, query_embedding, rw_types, country, event_year, decay_factor,
                    suggested_alternatives=None):
    """The pre-upgrade pipeline, ported verbatim from api_orchestrator.py:193-260
    _rag_search(). Multi-pass pgvector cosine + time-decay, lexical fallback.
    Returns (results, suggested_alternatives, meta). Results keep the exact
    historical row shape (8 columns, score at index 7); ids travel in meta.
    """
    col = _embed_col()
    cur = conn.cursor()
    try:
        if query_embedding is None:
            sql = f"""
                SELECT {_COLUMNS}, 0.0 AS hybrid_similarity, id, unique_id
                FROM disaster_narratives
                WHERE disaster_type = ANY(%s) AND country ILIKE %s AND event_year >= %s
                ORDER BY ABS(event_year - %s) ASC, date DESC
                LIMIT 3;
            """
            cur.execute(sql, (rw_types, country, MIN_EVENT_YEAR, event_year))
            rows = cur.fetchall()
            results = [r[:8] for r in rows]
            meta = {"result_ids": [r[8] for r in rows],
                    "result_unique_ids": [r[9] for r in rows]}
            return results, None, meta

        sql_pass1 = f"""
            SELECT {_COLUMNS},
                   (1 - ({col} <=> %s::vector)) - (%s * ABS(event_year - %s)) AS hybrid_similarity,
                   id, unique_id
            FROM disaster_narratives
            WHERE event_year = %s AND disaster_type = ANY(%s) AND country ILIKE %s AND event_year >= %s
            ORDER BY hybrid_similarity DESC
            LIMIT 3;
        """
        cur.execute(sql_pass1, (query_embedding, decay_factor, event_year, event_year, rw_types, country, MIN_EVENT_YEAR))
        rows = cur.fetchall()
        results = [r[:8] for r in rows]

        if len(results) < 3:
            sql_pass2 = f"""
                SELECT {_COLUMNS},
                       (1 - ({col} <=> %s::vector)) - (%s * ABS(event_year - %s)) AS hybrid_similarity,
                       id, unique_id
                FROM disaster_narratives
                WHERE disaster_type = ANY(%s) AND country ILIKE %s AND event_year >= %s
                ORDER BY hybrid_similarity DESC
                LIMIT 3;
            """
            cur.execute(sql_pass2, (query_embedding, decay_factor, event_year, rw_types, country, MIN_EVENT_YEAR))
            rows = cur.fetchall()
            results = [r[:8] for r in rows]

        if len(results) == 0:
            cur.execute("SELECT DISTINCT disaster_type FROM disaster_narratives WHERE country ILIKE %s AND disaster_type IS NOT NULL LIMIT 5", (country,))
            same_country_disasters = [row[0] for row in cur.fetchall()]
            cur.execute("SELECT event_year FROM disaster_narratives WHERE country ILIKE %s AND event_year IS NOT NULL GROUP BY event_year ORDER BY ABS(event_year - %s) ASC LIMIT 5", (country, event_year))
            closest_historical_years = [row[0] for row in cur.fetchall()]
            suggested_alternatives = {
                "same_country_disasters": same_country_disasters,
                "closest_historical_years": closest_historical_years,
            }
        meta = {"result_ids": [r[8] for r in rows],
                "result_unique_ids": [r[9] for r in rows]}
        return results, suggested_alternatives, meta
    finally:
        cur.close()


def retrieve_hybrid(conn, query_embedding, tsquery_text, rw_types, country, event_year,
                    region_list=(), recency_weight=0.5, top_k=5):
    """Phase 2+3 pipeline: progressive filter relaxation with tier padding,
    then dense + sparse + recency fused with Reciprocal Rank Fusion.

    Tier rule (measured against the eval set): the base pool is the STRICTEST
    non-empty tier — a 2-row truthful pool beats a 290-row wrong pool — and if
    it holds fewer than top_k rows it is padded from the next broader tiers,
    never abandoned. Falls back gracefully:
    - no embedding  -> sparse + recency still run
    - no tsquery    -> dense + recency
    - neither       -> the legacy structured fallback
    Returns (results, suggested_alternatives, meta) with the same row shape.
    """
    col = _embed_col()
    valid_ts = _has_terms(tsquery_text)
    cur = conn.cursor()
    try:
        if query_embedding is None and not valid_ts:
            return retrieve_legacy(conn, None, rw_types, country, event_year, 0.0)

        # 1. Count every tier; base = strictest tier with any rows; pad upward.
        tier_counts = []
        for tier in TIER_ORDER:
            where_sql, where_params = _tier_where(tier, rw_types, country, event_year, region_list)
            cur.execute(f"SELECT count(*) FROM disaster_narratives WHERE {where_sql}", where_params)
            n = cur.fetchone()[0]
            tier_counts.append((tier, n, where_sql, where_params))
        start = next((i for i, (_, n, _, _) in enumerate(tier_counts) if n >= 1), None)
        if start is None:
            start = len(tier_counts) - 1

        def run_arms(where_sql, where_params, candidate_limit):
            # Only define (and therefore only bind placeholders for) the arms
            # that are actually usable — an unreferenced CTE still counts its %s
            # against the bind array at parse time, so dead arms would
            # desynchronise binds.
            arm_defs, union_parts, bind = {}, [], []
            if query_embedding is not None:
                arm_defs["dense"] = f"""
                    (SELECT id, ROW_NUMBER() OVER (ORDER BY {col} <=> %s::vector) AS rank
                     FROM disaster_narratives WHERE {where_sql} LIMIT {candidate_limit})"""
                union_parts.append("dense")
                bind += [query_embedding] + list(where_params)
            if valid_ts:
                arm_defs["sparse"] = f"""
                    (SELECT id, ROW_NUMBER() OVER (ORDER BY ts_rank_cd(fts_vector, {TSQUERY_SQL}, 32) DESC) AS rank
                     FROM disaster_narratives WHERE fts_vector @@ {TSQUERY_SQL} AND {where_sql} LIMIT {candidate_limit})"""
                union_parts.append("sparse")
                bind += [tsquery_text, tsquery_text] + list(where_params)
            arm_defs["recency"] = f"""
                (SELECT id, ROW_NUMBER() OVER (ORDER BY ABS(event_year - %s)) AS rank
                 FROM disaster_narratives WHERE {where_sql} LIMIT {candidate_limit})"""
            union_parts.append("recency")
            bind += [event_year] + list(where_params)

            rank_expr = {
                "dense": "1.0/(60+rank)",
                "sparse": "1.0/(60+rank)",
                "recency": f"{recency_weight}*(1.0/(60+rank))",
            }
            union_sql = " UNION ALL ".join(
                f"SELECT id, {rank_expr[a]} AS w FROM {a}" for a in union_parts
            )

            if len(union_parts) == 1:
                # Only recency (both bridges down): the structured fallback.
                sql = f"""
                    SELECT {_COLUMNS}, 0.0 AS rrf, id, unique_id
                    FROM disaster_narratives WHERE {where_sql}
                    ORDER BY ABS(event_year - %s)
                    LIMIT {top_k};
                """
                cur.execute(sql, list(where_params) + [event_year])
            else:
                with_clause = ",\n".join(f"{name} AS {arm_defs[name]}" for name in union_parts)
                sql = f"""
                    WITH {with_clause}
                    SELECT dn.{_COLUMNS.replace(', ', ', dn.')}, SUM(w) AS rrf, dn.id, dn.unique_id
                    FROM ({union_sql}) f
                    JOIN disaster_narratives dn ON dn.id = f.id
                    GROUP BY dn.id, dn.{_COLUMNS.replace(', ', ', dn.')}, dn.unique_id
                    ORDER BY rrf DESC
                    LIMIT {top_k};
                """
                cur.execute(sql, bind)
            return cur.fetchall()

        # 2. Pad: more-specific tiers first, dedupe by id, stop at top_k.
        merged, seen, used_tiers, total_pool = [], set(), [], 0
        for tier, n, where_sql, where_params in tier_counts[start:]:
            used_tiers.append(tier)
            total_pool += n
            for row in run_arms(where_sql, where_params, candidate_limit=30):
                if row[8] not in seen:
                    seen.add(row[8])
                    merged.append(row)
            if len(merged) >= top_k:
                break

        rows = merged[:top_k]
        results = [r[:8] for r in rows]

        suggested_alternatives = None
        if len(results) == 0:
            cur.execute("SELECT DISTINCT disaster_type FROM disaster_narratives WHERE country ILIKE %s AND disaster_type IS NOT NULL LIMIT 5", (country,))
            same_country_disasters = [row[0] for row in cur.fetchall()]
            cur.execute("SELECT event_year FROM disaster_narratives WHERE country ILIKE %s AND event_year IS NOT NULL GROUP BY event_year ORDER BY ABS(event_year - %s) ASC LIMIT 5", (country, event_year))
            closest_historical_years = [row[0] for row in cur.fetchall()]
            suggested_alternatives = {
                "same_country_disasters": same_country_disasters,
                "closest_historical_years": closest_historical_years,
            }

        meta = {
            "result_ids": [r[8] for r in rows],
            "result_unique_ids": [r[9] for r in rows],
            "filter_tiers": used_tiers,
            "filter_tier": used_tiers[0] if used_tiers else None,
            "candidate_pool_size": total_pool,
            "sparse_arm_used": valid_ts,
            "dense_arm_used": query_embedding is not None,
            "recency_weight": recency_weight,
            "padded": len(used_tiers) > 1,
        }
        return results, suggested_alternatives, meta
    finally:
        cur.close()


def dispatch(conn, query_embedding, tsquery_text, rw_types, country, event_year,
             region_list=(), recency_weight=0.5, top_k=5,
             decay_factor=None):
    """USE_HYBRID_RAG-aware entry point used by both the API and eval runner."""
    if USE_HYBRID_RAG:
        return retrieve_hybrid(
            conn, query_embedding, tsquery_text, rw_types, country, event_year,
            region_list=region_list, recency_weight=recency_weight, top_k=top_k,
        )
    return retrieve_legacy(conn, query_embedding, rw_types, country, event_year, decay_factor)


# ---------------------------------------------------------------------------
# Coarse region map for the fallback tier (Phase 2c). Normalised keys only;
# unmapped countries skip the region tier and fall through to type-only.
# ---------------------------------------------------------------------------

REGION_COUNTRIES = {
    "South Asia": ["India", "Pakistan", "Bangladesh", "Nepal", "Sri Lanka", "Bhutan", "Maldives", "Afghanistan"],
    "East Asia": ["China", "Japan", "Japan region", "Republic of Korea", "Mongolia", "China - Taiwan Province"],
    "Southeast Asia": ["Philippines", "Indonesia", "Thailand", "Myanmar", "Viet Nam", "Malaysia",
                       "Cambodia", "Lao People's Democratic Republic (the)", "Timor-Leste"],
    "Central Asia": ["Tajikistan", "Kazakhstan", "Kyrgyzstan", "Uzbekistan", "Turkmenistan"],
    "Middle East & North Africa": ["Iran (Islamic Republic of)", "Iraq", "Syrian Arab Republic", "Lebanon",
                                   "Israel", "Jordan", "Yemen", "occupied Palestinian territory",
                                   "Saudi Arabia", "Egypt", "Algeria", "Morocco", "Tunisia", "Libya", "Sudan"],
    "Sub-Saharan Africa": [
        "Democratic Republic of the Congo", "Somalia", "Nigeria", "Ethiopia", "Kenya", "Uganda", "Niger",
        "Madagascar", "United Republic of Tanzania", "South Sudan", "Cameroon", "Central African Republic",
        "Burundi", "Mozambique", "Benin", "Ghana", "Malawi", "Guinea", "Chad", "Zimbabwe", "Angola",
        "Zambia", "Congo", "Senegal", "Mali", "Rwanda", "Burkina Faso", "Côte d'Ivoire", "Mauritania",
        "Sierra Leone", "Gabon", "Liberia", "Namibia", "Botswana", "Cabo Verde", "Lesotho", "Gambia",
        "Guinea-Bissau", "Equatorial Guinea", "Togo", "Eswatini", "Sao Tome and Principe", "Seychelles",
        "Comoros", "Djibouti", "Mauritius"],
    "Europe": ["Türkiye", "Albania", "Bosnia and Herzegovina", "Serbia", "Ukraine", "Georgia", "Russian Federation",
               "the Republic of North Macedonia", "Hungary", "Bulgaria", "Romania", "Czechia", "Slovenia",
               "Montenegro", "Moldova", "Belarus", "Italy", "Spain", "Iceland", "Cyprus", "Greece", "France"],
    "Central America & Caribbean": ["Haiti", "Guatemala", "Dominican Republic", "Honduras", "Cuba", "El Salvador",
                                    "Nicaragua", "Costa Rica", "Panama", "Belize", "Jamaica", "Saint Vincent and the Grenadines",
                                    "Barbados", "Dominica", "Grenada", "Antigua and Barbuda", "Trinidad and Tobago",
                                    "Bahamas", "British Virgin Islands", "Anguilla", "Saint Lucia"],
    "South America": ["Colombia", "Peru", "Bolivia (Plurinational State of)", "Ecuador", "Brazil", "Venezuela (Bolivarian Republic of)",
                      "Chile", "Argentina", "Paraguay", "Uruguay", "Guyana", "Suriname"],
    "Oceania & Pacific": ["Vanuatu", "Papua New Guinea", "Fiji", "Solomon Islands", "Tonga", "Samoa",
                          "Marshall Islands", "Micronesia (Federated States of)", "Micronesia", "Cook Islands",
                          "Palau", "Nauru", "Tuvalu", "Kiribati", "American Samoa", "French Polynesia (France)",
                          "New Zealand", "Australia", "Hawaii", "Kermadec Islands region", "south of Tonga",
                          "south of the Kermadec Islands", "west of Macquarie Island", "north of Ascension Island",
                          "Balleny Islands region", "southeast of Easter Island", "Pacific-Antarctic Ridge",
                          "South Sandwich Islands region", "east central Pacific Ocean", "Galapagos Triple Junction region",
                          "northern Mid-Atlantic Ridge", "Japan region", "New Zealand region", "Alaska", "USA"],
}


def region_members(country):
    """Lowercased country list for the region of `country` (empty if unmapped)."""
    for members in REGION_COUNTRIES.values():
        if any(m.lower() == country.lower() for m in members):
            return [m.lower() for m in members]
    return []
