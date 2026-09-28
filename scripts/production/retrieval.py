"""Shared retrieval layer for the Calamity orchestrator and the eval harness.

Single source of truth: api_orchestrator.py and scripts/eval/run_retrieval_eval.py
both import their retrieval logic from here, so the evaluation harness cannot
drift from what production actually runs.

Env knobs (read directly so the eval tools work without a full Heroku env):
  EMBEDDING_COLUMN  'embedding' (default) | 'embedding_v2' | 'embedding_fireworks'
  USE_HYBRID_RAG    1/true/yes  -> hybrid three-list RRF pipeline
  EMBEDDING_PRIMARY_PROVIDER  'fireworks' (default when keyed) | 'huggingface'
  FIREWORKS_API_KEY, FIREWORKS_EMBEDDING_MODEL, FIREWORKS_EMBEDDING_DIMENSIONS
  USE_RERANKER, FIREWORKS_RERANKER_MODEL, RERANK_CANDIDATES, RERANK_DOC_CHARS
  HF_TOKEN, MIN_EVENT_YEAR, DECAY_*  (mirror src/config.py defaults)

Provider isolation rule: Qwen3 and BGE are different vector spaces. A query
vector may only be compared against the column produced by the SAME provider
(see PROVIDERS below). Never write one provider's vector into another's column.
"""
import math
import os
import re
import time

import pycountry
import requests

import psycopg2

HF_EMBED_URL = "https://router.huggingface.co/hf-inference/models/BAAI/bge-large-en-v1.5"
INSTRUCTION_PREFIX = "Represent this sentence for searching relevant passages: "

FIREWORKS_BASE_URL = os.getenv("FIREWORKS_BASE_URL", "https://api.fireworks.ai/inference/v1")
FIREWORKS_API_KEY = os.getenv("FIREWORKS_API_KEY", "")
FIREWORKS_EMBEDDING_MODEL = os.getenv(
    "FIREWORKS_EMBEDDING_MODEL", "accounts/fireworks/models/qwen3-embedding-8b")
FIREWORKS_EMBEDDING_DIMENSIONS = int(os.getenv("FIREWORKS_EMBEDDING_DIMENSIONS", "1024"))
FIREWORKS_RERANKER_MODEL = os.getenv(
    "FIREWORKS_RERANKER_MODEL", "accounts/fireworks/models/qwen3-reranker-8b")

MIN_EVENT_YEAR = int(os.getenv("MIN_EVENT_YEAR", "2000"))
EMBEDDING_COLUMN = os.getenv("EMBEDDING_COLUMN", "embedding")
USE_HYBRID_RAG = os.getenv("USE_HYBRID_RAG", "").lower() in ("1", "true", "yes")
HF_TOKEN = os.getenv("HF_TOKEN", "")

# Reranking is opt-in: Qwen3 Reranker 8B bills per candidate token, so it must
# never be switched on implicitly by a provider change.
USE_RERANKER = os.getenv("USE_RERANKER", "").lower() in ("1", "true", "yes")
RERANK_CANDIDATES = int(os.getenv("RERANK_CANDIDATES", "20"))
RERANK_DOC_CHARS = int(os.getenv("RERANK_DOC_CHARS", "1200"))

# Mirrors src/config.py TIME_DECAY_PENALTY defaults.
DECAY_DEFAULTS = {
    "earthquake": float(os.getenv("DECAY_EARTHQUAKE", "0.002")),
    "flood": float(os.getenv("DECAY_FLOOD", "0.008")),
    "default": float(os.getenv("DECAY_DEFAULT", "0.005")),
}

# Only these column names may be interpolated into SQL.
_VALID_EMBED_COLUMNS = ("embedding", "embedding_v2", "embedding_fireworks")

# Provider -> vector space mapping. Qwen3 and BGE vectors are NOT comparable, so
# each provider owns its own column and a query vector is only ever compared
# against the column of the provider that produced it.
PROVIDERS = {
    "fireworks": {"column": "embedding_fireworks", "model": FIREWORKS_EMBEDDING_MODEL},
    "huggingface": {"column": os.getenv("HF_EMBEDDING_COLUMN", "embedding_v2"),
                    "model": "BAAI/bge-large-en-v1.5"},
}

# Order in which providers are attempted. Fireworks is primary when keyed
# because the HF free tier is the dependency this migration removes; HF stays
# configured as a secondary so an expired Fireworks balance still degrades to
# semantic retrieval rather than straight to lexical.
def _default_provider_order():
    configured = os.getenv("EMBEDDING_PROVIDER_ORDER", "").strip()
    if configured:
        return [p.strip() for p in configured.split(",") if p.strip() in PROVIDERS]
    primary = os.getenv("EMBEDDING_PRIMARY_PROVIDER", "").strip().lower()
    if primary not in PROVIDERS:
        primary = "fireworks" if FIREWORKS_API_KEY else "huggingface"
    order = [primary] + [p for p in ("fireworks", "huggingface") if p != primary]
    return order


PROVIDER_ORDER = _default_provider_order()

_COLUMNS = "date, country, disaster_type, narrative_text, event_year, lat, lng"


def _embed_col(column=None):
    col = column or EMBEDDING_COLUMN
    if col not in _VALID_EMBED_COLUMNS:
        raise ValueError(f"unsafe EMBEDDING_COLUMN: {col!r}")
    return col


# ---------------------------------------------------------------------------
# Country / taxonomy normalisation (moved verbatim from api_orchestrator.py so
# the eval harness uses the exact same mapping the API uses)
# ---------------------------------------------------------------------------

COUNTRY_ALIASES = {
    # user input / legacy spelling -> dominant production DB spelling
    # (verified against the 2026-09-28 country snapshot)
    'Turkey': 'Türkiye',
    'Russia': 'Russian Federation',
    'US': 'United States',
    'USA': 'United States',
    'United States of America': 'United States',
    'Vietnam': 'Viet Nam',
    'Vet Nam': 'Viet Nam',
    'Britain': 'United Kingdom',
    'UK': 'United Kingdom',
    'Great Britain': 'United Kingdom',
    'Tanzania': 'United Republic of Tanzania',
    'Bolivia': 'Bolivia (Plurinational State of)',
    'Venezuela': 'Venezuela (Bolivarian Republic of)',
    'Iran': 'Iran (Islamic Republic of)',
    'North Korea': "Democratic People's Republic of Korea",
    'South Korea': 'Republic of Korea',
    'Syria': 'Syrian Arab Republic',
    'Burma': 'Myanmar',
    'Czech Republic': 'Czechia',
    'DR Congo': 'Democratic Republic of the Congo',
    'Zaire': 'Democratic Republic of the Congo',
    'Ivory Coast': "Côte d'Ivoire",
    'Timor Leste': 'Timor-Leste',
}
# Canonical spellings actually present in the production DB
# (snapshot 2026-09-28: 239 distinct values from
# disaster_narratives.country). Guards the pycountry fuzzy
# fallback: a fuzzy answer is only accepted if it exists in the
# DB, otherwise the user input passes through unchanged.
_DB_COUNTRY_SNAPSHOT = frozenset({
    'Philippines', 'Indonesia', 'United States', 'Australia',
    'China', 'Angola', 'Unknown', 'Bangladesh',
    'Sri Lanka', 'Afghanistan', 'India', 'Viet Nam',
    'Pakistan', 'Madagascar', 'Papua New Guinea', 'Democratic Republic of the Congo',
    'Vanuatu', 'Brasil', 'République démocratique du Congo', 'Tajikistan',
    'Zambia', 'Somalia', 'Myanmar', 'Algeria',
    'Colombia', 'Peru', 'Nigeria', 'Thailand',
    'Haiti', 'Nepal', 'Ethiopia', 'Fiji',
    'Sudan', 'Kenya', 'Solomon Islands', 'Bolivia (Plurinational State of)',
    'Guatemala', 'Uganda', 'Niger', 'Yemen',
    'Iran (Islamic Republic of)', 'Mexico', 'South Sudan', 'Ecuador',
    'United Republic of Tanzania', 'Namibia', 'Cameroon', 'Central African Republic',
    'Россия', 'Russian Federation', 'Tonga', 'Botswana',
    'Japan', 'Burundi', 'Mongolia', 'Mozambique',
    'Chile', 'Kyrgyzstan', 'Argentina', "Democratic People's Republic of Korea",
    'Malaysia', 'South Africa', 'Benin', 'Syrian Arab Republic',
    'Alaska', 'Guinea', 'Dominican Republic', 'New Caledonia',
    'Georgia', 'Brazil', 'Ghana', 'Zimbabwe',
    'Malawi', 'Moçambique', "Lao People's Democratic Republic (the)", 'Chad',
    'Honduras', 'Paraguay', 'El Salvador', 'Iraq',
    'Congo', 'Costa Rica', 'Panama', 'Mali',
    'Canada', 'Republic of Korea', 'South Sandwich Islands region', 'Senegal',
    'Rwanda', 'Cuba', 'Serbia', 'Kazakhstan',
    'Cambodia', 'Tanzania', 'Türkiye', "Côte d'Ivoire",
    'Burkina Faso', 'Қазақстан', 'Nicaragua', 'Mauritania',
    'Belize', 'Sierra Leone', 'Ukraine', 'Timor-Leste',
    'China - Taiwan Province', 'Liberia', 'Morocco', 'ⵍⵣⵣⴰⵢⴻⵔ الجزائر',
    'the Republic of North Macedonia', 'Venezuela (Bolivarian Republic of)', 'Kermadec Islands region', 'occupied Palestinian territory',
    'Gabon', 'Lebanon', 'Albania', 'Egypt',
    'Bosnia and Herzegovina', 'New Zealand', 'Marshall Islands', 'Armenia',
    'Timor Leste', 'Tunisia', 'Cabo Verde', 'United States of America',
    'Micronesia (Federated States of)', 'Saint Vincent and the Grenadines', 'Cook Islands', 'southern East Pacific Rise',
    'Japan region', 'Belarus', 'Lesotho', 'Gambia',
    'Hungary', 'Guinea-Bissau', 'Samoa', 'Uruguay',
    'southern Mid-Atlantic Ridge', 'Micronesia', 'Libya', 'Saint Lucia',
    'Mauritius', 'south of Tonga', 'Kiribati', 'Dominica',
    'Togo', 'Equatorial Guinea', 'Guyana', 'Eswatini',
    'South Atlantic Ocean', 'Sao Tome and Principe', 'American Samoa', 'Guam',
    'Uzbekistan', 'Bolivia', 'south of the Kermadec Islands', 'Bulgaria',
    'north of Ascension Island', 'Spain', 'Pacific-Antarctic Ridge', 'Reykjanes Ridge',
    'Venezuela', 'Moldova', 'northern Mid-Atlantic Ridge', 'España',
    'southeast of the Loyalty Islands', 'Bahamas', 'Северна Македонија', 'Djibouti',
    'Comoros', 'Scotia Sea', 'Bhutan', 'Trinidad and Tobago',
    'off the coast of Central America', 'Czechia', 'Suriname', 'Maldives',
    'Northern Mariana Islands', 'Seychelles', 'Romania', 'Slovenia',
    'Mariana Islands region', 'Turkmenistan', 'Saudi Arabia', 'southeast Indian Ridge',
    'Barbados', 'سوريا', 'east central Pacific Ocean', 'Grenada',
    'Fiji region', 'Israel', 'Antigua and Barbuda', 'Iceland',
    'British Virgin Islands', 'Jordan', 'Tuvalu', 'Montenegro',
    'Balleny Islands region', 'България', 'Wallis and Futuna', 'Papua Niugini',
    'south of the Fiji Islands', 'República Dominicana', 'French Polynesia (France)', 'Taiwan',
    'central Mid-Atlantic Ridge', 'western Xizang', 'Italy', 'မြန်မာ',
    'south of Africa', 'Southwest Indian Ridge', 'México', 'Palau',
    'Galapagos Triple Junction region', 'Vanuatu region', 'northern East Pacific Rise', 'Anguilla',
    'World', 'Cyprus', 'Kuril Islands', 'Iran',
    'Dominican Rep.', 'New Zealand region', 'Madeira (Portugal)', 'Nauru',
    '中国', 'Owen Fracture Zone region', 'Hawaii', 'CA',
    'Azerbaijan', 'west of Macquarie Island', 'southeast of Easter Island', 'off the coast of Oregon',
    'Austria', 'France', 'Germany', 'Ireland', 'Lithuania', 'Poland', 'Portugal',
})

_PC_BY_NAME = {c.name.casefold(): c.name for c in pycountry.countries}
_ALIASES_CF = {k.casefold(): v for k, v in COUNTRY_ALIASES.items()}


def resolve_country(name: str, lower: bool = False):
    """Normalize a user-supplied country name to the DB spelling.

    alias map -> pycountry exact -> guarded pycountry fuzzy ->
    unchanged. The fuzzy guard only accepts an answer that exists
    in the DB snapshot, so unknown input degrades to passthrough
    instead of a pycountry canonical name with zero DB rows.
    """
    if not isinstance(name, str) or not name.strip():
        return name
    hit = COUNTRY_ALIASES.get(name) or _ALIASES_CF.get(name.casefold(), name)
    exact = _PC_BY_NAME.get(hit.casefold())
    if exact in _DB_COUNTRY_SNAPSHOT:
        resolved = exact
    else:
        try:
            top = pycountry.countries.search_fuzzy(hit)[0]
        except Exception:  # LookupError on bad input; never crash the API
            top = None
        if top is not None and top.name in _DB_COUNTRY_SNAPSHOT:
            resolved = top.name
        else:
            resolved = hit
    return resolved.lower() if lower else resolved


RW_TYPE_MAP = {
    "earthquake": ["Earthquake", "Tsunami"],
    "flood": ["Flood", "Flash Flood", "Floods"],
    "extreme temperature": ["Heat Wave", "Cold Wave", "Extreme temperature"],
    "storm": ["Storm", "Storm Surge", "Tropical Cyclone", "Extratropical Cyclone",
             "Severe Local Storm", "Severe Storms", "Hurricane"],
    "mass movement (wet)": ["Mud Slide", "Land Slide", "Mass movement (wet)"],
    "mass movement (dry)": ["Land Slide", "Mass movement (dry)"],
    "volcanic activity": ["Volcano", "Volcanic activity"],
    "wildfire": ["Wild Fire", "Fire", "Wildfire", "Wildfires"],
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

VECTOR_DIM = 1024

# Safe, non-secret failure reasons surfaced in telemetry and logs. The watchdog
# and any future alerting key off these strings, so keep them stable.
EMBED_MISSING_TOKEN = "missing_token"
EMBED_HTTP = "http_error"
EMBED_TIMEOUT = "timeout"
EMBED_NETWORK = "network_error"
EMBED_MALFORMED = "malformed_response"
EMBED_ZERO_VECTOR = "zero_vector"
EMBED_WRONG_DIMENSION = "wrong_dimension"
EMBED_NONFINITE = "nonfinite_vector"
EMBED_BATCH_MISMATCH = "batch_cardinality_mismatch"

# Only these statuses are worth a retry. 408/429 are throttling/timeouts that
# clear on their own; 502/503/504 are provider/gateway blips. Everything else
# (401/402/403 auth/billing, 400/404/405 contract errors) is permanent and must
# fail fast rather than burn quota or stall the request.
_HTTP_RETRYABLE = {408, 429, 502, 503, 504}


def _validate_vector(vec):
    """Return (normalized_vector, None) or (None, reason) for a raw embedding.

    Enforces the vector(1024) contract: exactly VECTOR_DIM finite values with a
    non-zero norm. A zero or wrong-dimension vector silently poisons pgvector
    similarity, so it is rejected here instead of being written or queried.
    """
    if not isinstance(vec, (list, tuple)) or len(vec) != VECTOR_DIM:
        return None, EMBED_WRONG_DIMENSION
    try:
        floats = [float(x) for x in vec]
    except (TypeError, ValueError):
        return None, EMBED_NONFINITE
    if not all(math.isfinite(x) for x in floats):
        return None, EMBED_NONFINITE
    norm = math.sqrt(sum(x * x for x in floats))
    if not math.isfinite(norm) or norm <= 0.0:
        return None, EMBED_ZERO_VECTOR
    return [x / norm for x in floats], None


def _hf_embed(texts, timeout=24, retries=2):
    """Return (vectors_or_None, failure_info_or_None) for text(s).

    `timeout` is a TOTAL wall-clock budget shared across every attempt (not a
    per-attempt timeout), so a cold provider can never consume ~2x the
    orchestrator's 24s ceiling. Permanent 4xx responses are not retried.
    """
    if not HF_TOKEN:
        return None, {"reason": EMBED_MISSING_TOKEN, "http_status": None, "attempts": 0, "elapsed_ms": 0.0}

    is_batch = isinstance(texts, list)
    body = {"inputs": texts if is_batch else [texts],
            "options": {"wait_for_model": True}}
    headers = {"Authorization": f"Bearer {HF_TOKEN}"}

    deadline = time.monotonic() + timeout
    started = time.monotonic()
    attempts = 0
    last_err = None
    last_status = None

    while attempts < retries:
        remaining = deadline - time.monotonic()
        if remaining <= 0.05:
            last_err = EMBED_TIMEOUT
            break
        attempts += 1
        try:
            resp = requests.post(HF_EMBED_URL, headers=headers, json=body, timeout=remaining)
            if resp.status_code != 200:
                last_status = resp.status_code
                last_err = EMBED_HTTP
                if resp.status_code not in _HTTP_RETRYABLE:
                    break
                continue
            try:
                data = resp.json()
            except ValueError:
                last_status = resp.status_code
                last_err = EMBED_MALFORMED
                break
            if not isinstance(data, list) or not data:
                last_err = EMBED_MALFORMED
                continue
            out = []
            bad_reason = None
            for item in (data if is_batch else [data]):
                if isinstance(item, list) and item and isinstance(item[0], (int, float)):
                    vec = item
                elif isinstance(item, list) and item and isinstance(item[0], list):
                    vec = item[0]  # batch outer list
                else:
                    continue
                normalized, reason = _validate_vector(vec)
                if reason:
                    bad_reason = reason
                    break
                out.append(normalized)
            if bad_reason:
                last_err = bad_reason
                break
            if not out:
                last_err = EMBED_ZERO_VECTOR
                continue
            if is_batch and len(out) != len(texts):
                last_err = EMBED_BATCH_MISMATCH
                break
            return (out if is_batch else out[0]), None
        except requests.Timeout:
            last_err = EMBED_TIMEOUT
        except requests.RequestException:
            last_err = EMBED_NETWORK

    info = {
        "reason": last_err or EMBED_NETWORK,
        "http_status": last_status,
        "attempts": attempts,
        "elapsed_ms": round((time.monotonic() - started) * 1000, 1),
    }
    print(f"[retrieval] embedding bridge unavailable ({info}); lexical fallback")
    return None, info


def embed_query(text, timeout=24):
    """Single-text embedding with the BGE instruction prefix, or None on failure.

    Kept for the legacy BGE callers (eval harness / reembed script) that assume
    the Hugging Face vector space explicitly.
    """
    vectors, _ = _hf_embed(INSTRUCTION_PREFIX + text, timeout=timeout)
    return vectors


def embed_many(texts, timeout=60):
    """Batch embedding; each text gets the BGE instruction prefix, or None on failure."""
    vectors, _ = _hf_embed([INSTRUCTION_PREFIX + t for t in texts], timeout=timeout)
    return vectors


# ---------------------------------------------------------------------------
# Fireworks AI (Qwen3 Embedding 8B) — OpenAI-compatible /embeddings
# ---------------------------------------------------------------------------

# Verified against the live API 2026-08-20: response is
# {"data":[{"index":i,"embedding":[...]}], "usage":{"prompt_tokens":n}, ...}
# with UNNORMALIZED vectors (observed norm ~68.9), so normalisation happens here.
FW_QUERY_INSTRUCTION = (
    "Instruct: Given a disaster scenario, retrieve historical disaster "
    "narratives describing comparable events and their humanitarian impact\nQuery: "
)


def _fireworks_embed(texts, timeout=24, retries=2, is_query=True):
    """Return (vectors_or_None, failure_info_or_None) from Fireworks Qwen3.

    Same contract as _hf_embed: one shared wall-clock deadline across attempts,
    transient statuses only are retried, and every vector must satisfy the
    vector(1024) contract before it can reach pgvector.
    """
    if not FIREWORKS_API_KEY:
        return None, {"reason": EMBED_MISSING_TOKEN, "http_status": None, "attempts": 0,
                      "elapsed_ms": 0.0, "provider": "fireworks"}

    is_batch = isinstance(texts, list)
    items = list(texts) if is_batch else [texts]
    if is_query:
        items = [FW_QUERY_INSTRUCTION + t for t in items]
    body = {
        "model": FIREWORKS_EMBEDDING_MODEL,
        "input": items,
        "dimensions": FIREWORKS_EMBEDDING_DIMENSIONS,
    }
    headers = {"Authorization": f"Bearer {FIREWORKS_API_KEY}",
               "Content-Type": "application/json"}

    deadline = time.monotonic() + timeout
    started = time.monotonic()
    attempts = 0
    last_err = None
    last_status = None
    prompt_tokens = None

    while attempts < retries:
        remaining = deadline - time.monotonic()
        if remaining <= 0.05:
            last_err = EMBED_TIMEOUT
            break
        attempts += 1
        try:
            resp = requests.post(f"{FIREWORKS_BASE_URL}/embeddings", headers=headers,
                                 json=body, timeout=remaining)
            if resp.status_code != 200:
                last_status = resp.status_code
                last_err = EMBED_HTTP
                if resp.status_code not in _HTTP_RETRYABLE:
                    break
                continue
            try:
                payload = resp.json()
            except ValueError:
                last_status = resp.status_code
                last_err = EMBED_MALFORMED
                break
            data = payload.get("data") if isinstance(payload, dict) else None
            if not isinstance(data, list) or not data:
                last_err = EMBED_MALFORMED
                break
            prompt_tokens = (payload.get("usage") or {}).get("prompt_tokens")

            # Fireworks documents an `index` per item; do not trust arrival order.
            slots = [None] * len(items)
            bad_reason = None
            for item in data:
                if not isinstance(item, dict):
                    bad_reason = EMBED_MALFORMED
                    break
                idx = item.get("index")
                if not isinstance(idx, int) or not 0 <= idx < len(items) or slots[idx] is not None:
                    bad_reason = EMBED_BATCH_MISMATCH
                    break
                normalized, reason = _validate_vector(item.get("embedding"))
                if reason:
                    bad_reason = reason
                    break
                slots[idx] = normalized
            if bad_reason:
                last_err = bad_reason
                break
            if any(v is None for v in slots):
                last_err = EMBED_BATCH_MISMATCH
                break
            # Success still carries usage so the backfill can bill from the
            # provider's own token count instead of estimating from characters.
            ok = {"reason": None, "http_status": 200, "attempts": attempts,
                  "elapsed_ms": round((time.monotonic() - started) * 1000, 1),
                  "provider": "fireworks", "prompt_tokens": prompt_tokens}
            return (slots if is_batch else slots[0]), ok
        except requests.Timeout:
            last_err = EMBED_TIMEOUT
        except requests.RequestException:
            last_err = EMBED_NETWORK

    info = {
        "reason": last_err or EMBED_NETWORK,
        "http_status": last_status,
        "attempts": attempts,
        "elapsed_ms": round((time.monotonic() - started) * 1000, 1),
        "provider": "fireworks",
        "prompt_tokens": prompt_tokens,
    }
    print(f"[retrieval] fireworks embedding unavailable ({info})")
    return None, info


# ---------------------------------------------------------------------------
# Provider-neutral entry point
# ---------------------------------------------------------------------------

def embed_query_meta(text, timeout=24, provider_order=None):
    """Embed one query, walking PROVIDER_ORDER until a provider succeeds.

    Returns (vector, meta) where meta always names the provider and the vector
    column that vector may legally be compared against. On total failure the
    vector is None and meta carries every provider's sanitized failure reason so
    the caller can degrade to lexical retrieval and still say why.
    """
    order = provider_order or PROVIDER_ORDER
    deadline = time.monotonic() + timeout
    failures = []

    for provider in order:
        remaining = deadline - time.monotonic()
        if remaining <= 0.2:
            failures.append({"provider": provider, "reason": EMBED_TIMEOUT,
                             "http_status": None, "attempts": 0})
            break
        if provider == "fireworks":
            vec, info = _fireworks_embed(text, timeout=remaining)
        elif provider == "huggingface":
            vec, info = _hf_embed(INSTRUCTION_PREFIX + text, timeout=remaining)
            if info is not None:
                info = dict(info, provider="huggingface")
        else:
            continue
        if vec is not None:
            return vec, {
                "provider": provider,
                "model": PROVIDERS[provider]["model"],
                "column": PROVIDERS[provider]["column"],
                "dimensions": len(vec),
                "prompt_tokens": (info or {}).get("prompt_tokens"),
                "failures": failures,
            }
        failures.append(info)

    return None, {"provider": None, "model": None, "column": None,
                  "dimensions": None, "failures": failures}


def embed_documents_fireworks(texts, timeout=60, retries=3):
    """Batch document embedding for the Fireworks backfill / ingestion path.

    Documents are embedded WITHOUT the query instruction — Qwen3 is
    instruction-aware, and the corpus side must stay in the plain-document form
    the query instruction was designed to retrieve.
    """
    return _fireworks_embed(texts, timeout=timeout, retries=retries, is_query=False)


# ---------------------------------------------------------------------------
# Optional second-stage reranking (Fireworks Qwen3 Reranker 8B)
# ---------------------------------------------------------------------------

# Verified against the live API 2026-08-20: POST /rerank returns
# {"data":[{"index":i,"relevance_score":f}], "usage":{"prompt_tokens":n}}.
def rerank(query, documents, top_n=None, timeout=12, retries=2):
    """Return (ordering, meta): `ordering` is a list of original indices sorted
    by descending relevance, or None when reranking is unavailable.

    Callers MUST treat None as "keep the existing RRF order" — a reranker outage
    is never allowed to drop or reorder results arbitrarily.
    """
    if not FIREWORKS_API_KEY:
        return None, {"reason": EMBED_MISSING_TOKEN, "http_status": None, "attempts": 0}
    if not documents:
        return [], {"reason": None, "http_status": None, "attempts": 0, "prompt_tokens": 0}

    docs = [(d or "")[:RERANK_DOC_CHARS] for d in documents]
    body = {
        "model": FIREWORKS_RERANKER_MODEL,
        "query": query,
        "documents": docs,
        "top_n": top_n or len(docs),
        "return_documents": False,
    }
    headers = {"Authorization": f"Bearer {FIREWORKS_API_KEY}",
               "Content-Type": "application/json"}

    deadline = time.monotonic() + timeout
    started = time.monotonic()
    attempts = 0
    last_err = None
    last_status = None

    while attempts < retries:
        remaining = deadline - time.monotonic()
        if remaining <= 0.05:
            last_err = EMBED_TIMEOUT
            break
        attempts += 1
        try:
            resp = requests.post(f"{FIREWORKS_BASE_URL}/rerank", headers=headers,
                                 json=body, timeout=remaining)
            if resp.status_code != 200:
                last_status = resp.status_code
                last_err = EMBED_HTTP
                if resp.status_code not in _HTTP_RETRYABLE:
                    break
                continue
            try:
                payload = resp.json()
            except ValueError:
                last_status = resp.status_code
                last_err = EMBED_MALFORMED
                break
            data = payload.get("data") if isinstance(payload, dict) else None
            if not isinstance(data, list) or not data:
                last_err = EMBED_MALFORMED
                break
            scored = []
            for item in data:
                idx = item.get("index") if isinstance(item, dict) else None
                score = item.get("relevance_score") if isinstance(item, dict) else None
                if not isinstance(idx, int) or not 0 <= idx < len(docs):
                    last_err = EMBED_BATCH_MISMATCH
                    scored = []
                    break
                if not isinstance(score, (int, float)) or not math.isfinite(score):
                    last_err = EMBED_NONFINITE
                    scored = []
                    break
                scored.append((idx, float(score)))
            if not scored:
                break
            scored.sort(key=lambda p: p[1], reverse=True)
            return [i for i, _ in scored], {
                "reason": None,
                "http_status": 200,
                "attempts": attempts,
                "elapsed_ms": round((time.monotonic() - started) * 1000, 1),
                "prompt_tokens": (payload.get("usage") or {}).get("prompt_tokens"),
                "candidates": len(docs),
            }
        except requests.Timeout:
            last_err = EMBED_TIMEOUT
        except requests.RequestException:
            last_err = EMBED_NETWORK

    info = {
        "reason": last_err or EMBED_NETWORK,
        "http_status": last_status,
        "attempts": attempts,
        "elapsed_ms": round((time.monotonic() - started) * 1000, 1),
        "candidates": len(docs),
    }
    print(f"[retrieval] reranker unavailable ({info}); keeping RRF order")
    return None, info


# ---------------------------------------------------------------------------
# Sparse-arm query construction (Phase 4 query rewriting)
# ---------------------------------------------------------------------------

TAXONOMY_SYNONYMS = {
    "flood": ["flood", "flooding", "inundation", "deluge", "overflow"],
    "earthquake": ["earthquake", "seismic", "tremor", "aftershock", "quake", "tsunami"],
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

# Noise floor (measured on prod 2026-09-28, 3226 rows):
#  - 345 USGS auto-ingest stubs ("A Magnitude X earthquake occurred in
#    N km of ...") — ZERO of them carry impact info; they land in top-k
#    and displace real SITREPs (seen in the 2026-09-28 canary).
#  - 596 EONET title-stubs ("A <Cat> event titled '...' was recorded on
#    <date>.") — 73-115 chars, 1/596 carries impact info; the 100-char
#    floor alone leaves 51 of them alive.
#  - 879 rows < 100 chars, incl. country-name-only entries ("Philippines"
#    x14); shortest genuine narrative in the corpus is ~130 chars.
# Single source of truth: eval/build_eval_dataset.py imports this and
# refuses to build ground truth from rows retrieval will never return.
NOISE_FLOOR_SQL = (
    "LENGTH(narrative_text) >= 100 "
    "AND NOT (narrative_text LIKE 'A Magnitude %' "
    "AND narrative_text LIKE '%earthquake occurred in%') "
    "AND NOT (narrative_text LIKE 'A % event titled % was recorded on %')"
)


def _tier_where(tier: str, rw_types, country, event_year, region_list):
    # %% escape: this SQL is always passed to psycopg2 WITH parameters.
    base = f"event_year >= {MIN_EVENT_YEAR} AND {NOISE_FLOOR_SQL.replace('%', '%%')}"
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
                    suggested_alternatives=None, embed_column=None):
    """The pre-upgrade pipeline, ported verbatim from api_orchestrator.py:193-260
    _rag_search(). Multi-pass pgvector cosine + time-decay, lexical fallback.
    Returns (results, suggested_alternatives, meta). Results keep the exact
    historical row shape (8 columns, score at index 7); ids travel in meta.
    """
    col = _embed_col(embed_column)
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
                    region_list=(), recency_weight=0.5, top_k=5, embed_column=None,
                    semantic_query=None, decay_factor=0.0):
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
    col = _embed_col(embed_column)
    valid_ts = _has_terms(tsquery_text)
    cur = conn.cursor()
    try:
        if query_embedding is None and not valid_ts:
            return retrieve_legacy(conn, None, rw_types, country, event_year, 0.0,
                                   embed_column=embed_column)

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

        def run_arms(where_sql, where_params, candidate_limit, limit=None):
            if limit is None:
                limit = top_k
            # Only define (and therefore only bind placeholders for) the arms
            # that are actually usable — an unreferenced CTE still counts its %s
            # against the bind array at parse time, so dead arms would
            # desynchronise binds.
            arm_defs, union_parts, bind = {}, [], []
            if query_embedding is not None:
                # decay_w is the time-decay multiplier for this arm's RRF score:
                # GREATEST(0.0, 1.0 - decay*|year diff|). With decay_factor=0 it
                # is the constant 1.0, so the default path ranks exactly as
                # before (frozen eval comparability).
                arm_defs["dense"] = f"""
                    (SELECT id, ROW_NUMBER() OVER (ORDER BY {col} <=> %s::vector) AS rank,
                            GREATEST(0.0, 1.0 - %s * ABS(event_year - %s)) AS decay_w
                     FROM disaster_narratives WHERE {where_sql} LIMIT {candidate_limit})"""
                union_parts.append("dense")
                bind += [query_embedding, decay_factor, event_year] + list(where_params)
            if valid_ts:
                arm_defs["sparse"] = f"""
                    (SELECT id, ROW_NUMBER() OVER (ORDER BY ts_rank(fts_vector, {TSQUERY_SQL}, 1|2) DESC) AS rank
                     FROM disaster_narratives WHERE fts_vector @@ {TSQUERY_SQL} AND {where_sql} LIMIT {candidate_limit})"""
                union_parts.append("sparse")
                bind += [tsquery_text, tsquery_text] + list(where_params)
            arm_defs["recency"] = f"""
                (SELECT id, ROW_NUMBER() OVER (ORDER BY ABS(event_year - %s)) AS rank
                 FROM disaster_narratives WHERE {where_sql} LIMIT {candidate_limit})"""
            union_parts.append("recency")
            bind += [event_year] + list(where_params)

            rank_expr = {
                "dense": "1.0/(60+rank) * decay_w",
                "sparse": "1.0/(60+rank)",
                "recency": f"{recency_weight}*(1.0/(60+rank))",
            }
            union_sql = " UNION ALL ".join(
                f"SELECT id, {rank_expr[a]}" + (" * decay_w" if a == "dense" else "") + " AS w FROM " + a
                for a in union_parts
            )

            if len(union_parts) == 1:
                # Only recency (both bridges down): the structured fallback.
                sql = f"""
                    SELECT {_COLUMNS}, 0.0 AS rrf, id, unique_id
                    FROM disaster_narratives WHERE {where_sql}
                    ORDER BY ABS(event_year - %s)
                    LIMIT {limit};
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
                    LIMIT {limit};
                """
                cur.execute(sql, bind)
            return cur.fetchall()

        # 2. Pad: more-specific tiers first, dedupe by id. The candidate budget
        # widens when the reranker is on: it reorders the whole pool, so more
        # candidates can only help.
        candidate_budget = RERANK_CANDIDATES if (USE_RERANKER and (semantic_query or tsquery_text)) else top_k
        merged, seen, used_tiers, total_pool = [], set(), [], 0
        for tier, n, where_sql, where_params in tier_counts[start:]:
            used_tiers.append(tier)
            total_pool += n
            for row in run_arms(where_sql, where_params, candidate_limit=30, limit=candidate_budget):
                if row[8] not in seen:
                    seen.add(row[8])
                    merged.append(row)
            if len(merged) >= candidate_budget:
                break

        candidates = merged[:candidate_budget]

        # Optional second-stage cross-encoder rerank over the merged RRF pool.
        # Reorders by true query/document relevance; any failure (no key,
        # network, timeout, malformed response) keeps the RRF order intact.
        reranked = False
        rerank_meta = None
        rerank_query = semantic_query or tsquery_text
        if USE_RERANKER and rerank_query and len(candidates) > 1:
            docs = [c[3] for c in candidates]  # narrative_text
            order, rmeta = rerank(rerank_query, docs, top_n=len(candidates), timeout=10, retries=2)
            rerank_meta = rmeta
            if order is not None and len(order) == len(candidates):
                candidates = [candidates[i] for i in order]
                reranked = True

        rows = candidates[:top_k]

        # Replace the RRF fused score (max ~0.041, meaningless to users) with
        # each row's true cosine similarity to the query embedding. RRF still
        # decides ordering above; this only fixes what the UI displays
        # (average_cosine_similarity + per-row similarity_score). The eval
        # harness only reads meta["result_unique_ids"], so it is unaffected.
        # When the dense bridge is down (query_embedding is None) there is no
        # cosine value to compute, and rows keep the RRF score in r[7].
        if query_embedding is not None and rows:
            ids = [r[8] for r in rows]
            cur.execute(
                f"SELECT id, 1 - ({col} <=> %s::vector) AS cosine_sim "
                f"FROM disaster_narratives WHERE id = ANY(%s)",
                (query_embedding, ids),
            )
            cos_by_id = {r[0]: r[1] for r in cur.fetchall()}
            results = [tuple(list(r[:7]) + [cos_by_id.get(r[8], 0.0)]) for r in rows]
        else:
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
            "ranked": "rerank" if reranked else "rrf",
            "reranked": reranked,
            "rerank_candidates": len(candidates) if reranked else None,
            "rerank_prompt_tokens": (rerank_meta or {}).get("prompt_tokens"),
        }
        return results, suggested_alternatives, meta
    finally:
        cur.close()


def dispatch(conn, query_embedding, tsquery_text, rw_types, country, event_year,
             region_list=(), recency_weight=0.5, top_k=5,
             decay_factor=None, embed_column=None, semantic_query=None):
    """USE_HYBRID_RAG-aware entry point used by both the API and eval runner.

    `embed_column` pins the vector space to the provider that produced
    `query_embedding`; omitting it falls back to the EMBEDDING_COLUMN default.
    """
    if decay_factor is None:
        decay_factor = 0.0
    if USE_HYBRID_RAG:
        return retrieve_hybrid(
            conn, query_embedding, tsquery_text, rw_types, country, event_year,
            region_list=region_list, recency_weight=recency_weight, top_k=top_k,
            embed_column=embed_column, semantic_query=semantic_query,
            decay_factor=decay_factor,
        )
    return retrieve_legacy(conn, query_embedding, rw_types, country, event_year, decay_factor,
                           embed_column=embed_column)


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
