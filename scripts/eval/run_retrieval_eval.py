#!/usr/bin/env python3
"""Retrieval evaluation runner (implementation_plan.md Phase 0+).

Imports the SAME retrieval functions the API uses (scripts/production/retrieval.py)
so the harness cannot drift from production behaviour.

Usage:
  DATABASE_URL=<dsn> HF_TOKEN=<token> python3 scripts/eval/run_retrieval_eval.py \
      --mode legacy|hybrid|both --baseline          # --baseline freezes the file
  ... --guard                                       # fail if vs baseline.json drops >5%
  ... --recency-weight 0.5 --column embedding|embedding_v2

Outputs a markdown-compatible summary to stdout; writes full JSON to
eval/results/<timestamp>.json.
"""
import argparse
import json
import os
import statistics
import sys
import time

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))
import psycopg2

import scripts.production.retrieval as R

BASELINE = os.path.join(os.path.dirname(__file__), "..", "..", "eval", "baseline.json")
RESULTS_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "eval", "results")
CACHE_FILE = os.path.join(os.path.dirname(__file__), "..", "..", "eval", ".embedding_cache.json")


def get_dsn():
    return os.environ.get("DATABASE_URL") or open(
        os.path.expanduser("~/.calamity_rollback/DATABASE_URL.new.rotated")
    ).read().strip()


def load_queries(path):
    with open(path) as f:
        return json.load(f)


def embed_with_cache(queries):
    """Pre-embed every query's semantic text in ONE batched router call, cached."""
    cache = {}
    if os.path.exists(CACHE_FILE):
        with open(CACHE_FILE) as f:
            cache = json.load(f)
    missing = [q for q in queries if q["id"] not in cache]
    if missing:
        texts = [R.build_semantic_query(q["disaster_type"], q["country"], q["event_year"], q["query_text"])
                 for q in missing]
        vecs = R.embed_many(texts)
        if not vecs or len(vecs) != len(missing):
            print("!! batched embedding failed; falling back per-query", file=sys.stderr)
            vecs = []
            for t in texts:
                v = R.embed_query(t)
                vecs.append(v)
        for q, v in zip(missing, vecs):
            if v is not None:
                cache[q["id"]] = v
        with open(CACHE_FILE, "w") as f:
            json.dump(cache, f)
    return [cache.get(q["id"]) for q in queries]


def dcg_at_k(rel, k):
    tot = 0.0
    for i in range(min(k, len(rel))):
        if rel[i]:
            tot += 1.0 / (i + 2)  # log2 rank+1
    return tot


def evaluate_queries(queries, embeddings, mode, recency_weight):
    conn = psycopg2.connect(get_dsn())
    per_query = []
    try:
        for q, query_embedding in zip(queries, embeddings):
            rw_types = R.build_rw_types(q["disaster_type"])
            country = R.resolve_country(q["country"])
            event_year = q["event_year"]
            relevant = set(q["relevant_unique_ids"])
            fts_text = R.build_fts_text(q["disaster_type"], country, q["query_text"])

            t0 = time.monotonic()
            if mode == "hybrid":
                results, _, meta = R.retrieve_hybrid(
                    conn, query_embedding, fts_text, rw_types, country, event_year,
                    region_list=R.region_members(country),
                    recency_weight=recency_weight, top_k=5,
                )
                db_ms = (time.monotonic() - t0) * 1000
            else:
                results, _, meta = R.retrieve_legacy(
                    conn, query_embedding, rw_types, country, event_year,
                    R.decay_factor_for(q["disaster_type"]),
                )
                db_ms = (time.monotonic() - t0) * 1000

            got = meta["result_unique_ids"]
            rel = [uid in relevant for uid in got[:5]]

            per_query.append({
                "id": q["id"],
                "category": q["id"].split("_")[1],
                "query_text": q["query_text"],
                "relevant": sorted(relevant),
                "retrieved": got[:5],
                "recall@5": len([u for u in got[:5] if u in relevant]) / max(1, len(relevant)),
                "recall@3": len([u for u in got[:3] if u in relevant]) / max(1, len(relevant)),
                "mrr": next((1.0 / (i + 1) for i, u in enumerate(got) if u in relevant), 0.0),
                "ndcg@5": dcg_at_k(rel, 5) / dcg_at_k([True] * len(relevant), 5) if relevant else 0.0,
                "db_ms": round(db_ms, 1),
                "meta": {k: v for k, v in meta.items() if k != "result_ids"},
            })
    finally:
        conn.close()

    n = len(per_query)
    def mean(key):
        return statistics.mean(p[key] for p in per_query)
    lat = sorted(p["db_ms"] for p in per_query)
    agg = {
        "mode": mode,
        "n": n,
        "recall@5": mean("recall@5"),
        "recall@3": mean("recall@3"),
        "mrr": mean("mrr"),
        "ndcg@5": mean("ndcg@5"),
        "latency_ms_p50": lat[len(lat) // 2],
        "latency_ms_p95": lat[int(len(lat) * 0.95)],
    }
    return agg, per_query


CATEGORIES = ["beyond500", "exact", "smallpool", "mismatch"]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--mode", choices=["legacy", "hybrid", "both"], required=True)
    ap.add_argument("--baseline", action="store_true")
    ap.add_argument("--guard", action="store_true")
    ap.add_argument("--recency-weight", type=float, default=0.5)
    ap.add_argument("--dataset", default="eval/retrieval_eval.json")
    ap.add_argument("--column", default=None)
    args = ap.parse_args()

    if args.column:
        os.environ["EMBEDDING_COLUMN"] = args.column
        # retrieval.py freezes EMBEDDING_COLUMN at import time; the env change
        # above alone would leave _embed_col() pointing at the old column.
        R.EMBEDDING_COLUMN = args.column

    queries = load_queries(args.dataset)
    embeddings = embed_with_cache(queries)
    print(f"evaluating {len(queries)} queries, mode={args.mode}, "
          f"column={R.EMBEDDING_COLUMN}, recency_weight={args.recency_weight}\n")

    modes = ["legacy", "hybrid"] if args.mode == "both" else [args.mode]
    results = {}
    for mode in modes:
        agg, per_query = evaluate_queries(queries, embeddings, mode, args.recency_weight)
        results[mode] = {"aggregate": agg, "per_query": per_query}
        print(f"--- {mode.upper()} ---")
        for m in ("recall@5", "recall@3", "mrr", "ndcg@5"):
            print(f"  {m:<9} {agg[m]:.3f}")
        print(f"  latency  {agg['latency_ms_p50']:.1f}ms p50 / {agg['latency_ms_p95']:.1f}ms p95")
        for cat in CATEGORIES:
            rows = [p for p in per_query if p["category"] == cat]
            if rows:
                print(f"  {cat:<10} recall@5={statistics.mean(p['recall@5'] for p in rows):.3f} "
                      f"mrr={statistics.mean(p['mrr'] for p in rows):.3f}")

    if args.baseline:
        if "legacy" not in results:
            sys.exit("--baseline requires the legacy mode to be run")
        os.makedirs(os.path.dirname(BASELINE), exist_ok=True)
        with open(BASELINE, "w") as f:
            json.dump(results["legacy"]["aggregate"], f, indent=2, sort_keys=True)
        print(f"\nbaseline frozen -> {BASELINE}")

    if args.guard:
        with open(BASELINE) as f:
            base = json.load(f)
        for mode, r in results.items():
            for m in ("recall@5", "recall@3", "mrr", "ndcg@5"):
                if r["aggregate"][m] < base[m] * 0.95:
                    sys.exit(f"GUARD FAILED: {mode}.{m} {r['aggregate'][m]:.3f} < 95% of "
                             f"baseline {base[m]:.3f}")
        print("guard: all metrics within 5% of baseline")

    os.makedirs(RESULTS_DIR, exist_ok=True)
    path = os.path.join(RESULTS_DIR, f"{int(time.time())}_{args.mode}.json")
    with open(path, "w") as f:
        json.dump(results, f, indent=2)
    print(f"\nfull results -> {path}")


if __name__ == "__main__":
    main()
