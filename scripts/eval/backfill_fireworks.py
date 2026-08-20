#!/usr/bin/env python3
"""Phase D backfill: embed every narrative with Fireworks Qwen3 into
embedding_fireworks. The BGE columns (embedding, embedding_v2) are never read
or written — the two vector spaces stay strictly separate.

Document text matches the ingestion/eval window so query and corpus agree:
    "{disaster} in {country} (Year: {year}). Additional Context: {text[:2000]}"

Documents are embedded WITHOUT the query instruction; only queries carry it.

Safety:
- writes embedding_fireworks only
- resumable: selects rows where embedding_fireworks IS NULL
- checkpointed after every batch
- cost ledger: records prompt_tokens and running spend, aborts at --max-spend
- aborts after repeated provider failures, leaving the table consistent

Usage:
  DATABASE_URL=<dsn> FIREWORKS_API_KEY=<key> \
    python3 scripts/eval/backfill_fireworks.py --limit 32 --max-spend 0.05
  ... then re-run without --limit to complete.
"""
import argparse
import json
import os
import sys
import time

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))
import psycopg2  # noqa: E402
from psycopg2.extras import execute_values  # noqa: E402

import scripts.production.retrieval as R  # noqa: E402

CHECKPOINT = os.path.join(os.path.dirname(__file__), "..", "..", "eval", ".fireworks_backfill.json")
LEDGER = os.path.join(os.path.dirname(__file__), "..", "..", "eval", "fireworks_cost_ledger.jsonl")
BATCH = 16
SLEEP = 0.5
MAX_CONSECUTIVE_FAILURES = 5
PRICE_PER_1M_TOKENS = float(os.getenv("FIREWORKS_EMBED_PRICE_PER_1M", "0.10"))


def get_dsn():
    dsn = os.environ.get("DATABASE_URL")
    if dsn:
        return dsn
    path = os.path.expanduser("~/.calamity_rollback/DATABASE_URL.new.rotated")
    with open(path) as f:
        return f.read().strip()


def emit(msg):
    print(f"{time.strftime('%Y-%m-%d %H:%M:%S UTC', time.gmtime())} {msg}", flush=True)


def load_state():
    if os.path.exists(CHECKPOINT):
        with open(CHECKPOINT) as f:
            return json.load(f)
    return {"done": 0, "prompt_tokens": 0, "spend_usd": 0.0}


def save_state(state):
    with open(CHECKPOINT, "w") as f:
        json.dump(state, f)


def append_ledger(entry):
    with open(LEDGER, "a") as f:
        f.write(json.dumps(entry) + "\n")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=0, help="stop after N rows (0 = all)")
    ap.add_argument("--max-spend", type=float, default=1.00,
                    help="abort once the estimated cumulative spend exceeds this (USD)")
    ap.add_argument("--batch", type=int, default=BATCH)
    args = ap.parse_args()

    if not R.FIREWORKS_API_KEY:
        sys.exit("FIREWORKS_API_KEY is required.")

    conn = psycopg2.connect(get_dsn())
    cur = conn.cursor()

    cur.execute("SELECT count(*) FROM disaster_narratives WHERE embedding_fireworks IS NULL")
    todo = cur.fetchone()[0]
    emit(f"model={R.FIREWORKS_EMBEDDING_MODEL} dims={R.FIREWORKS_EMBEDDING_DIMENSIONS}")
    emit(f"rows needing a Fireworks vector: {todo}")

    state = load_state()
    emit(f"resuming from ledger: done={state['done']} tokens={state['prompt_tokens']} "
         f"spend=${state['spend_usd']:.4f}")

    processed_this_run = 0
    consecutive_failures = 0

    while todo > 0:
        if args.limit and processed_this_run >= args.limit:
            emit(f"reached --limit {args.limit}; stopping cleanly")
            break
        if state["spend_usd"] >= args.max_spend:
            emit(f"reached --max-spend ${args.max_spend}; stopping cleanly")
            break

        cur.execute(
            "SELECT unique_id, country, disaster_type, event_year, narrative_text "
            "FROM disaster_narratives WHERE embedding_fireworks IS NULL "
            "ORDER BY id LIMIT %s",
            (args.batch,),
        )
        batch = cur.fetchall()
        if not batch:
            break

        texts = [R.build_semantic_query(r[2], r[1], r[3], (r[4] or "")[:2000]) for r in batch]
        vecs, info = R.embed_documents_fireworks(texts, timeout=90)

        if not vecs or len(vecs) != len(batch):
            consecutive_failures += 1
            emit(f"fireworks call failed {info} ({consecutive_failures}/{MAX_CONSECUTIVE_FAILURES})")
            if info and info.get("http_status") in (401, 402, 403):
                emit("permanent provider rejection; aborting without further calls")
                sys.exit(2)
            if consecutive_failures >= MAX_CONSECUTIVE_FAILURES:
                emit("giving up: provider unreachable, table left consistent")
                sys.exit(1)
            time.sleep(5 * consecutive_failures)
            continue
        consecutive_failures = 0

        rows = [(r[0], v) for r, v in zip(batch, vecs) if v is not None]
        if rows:
            execute_values(
                cur,
                "UPDATE disaster_narratives SET embedding_fireworks = data.v "
                "FROM (VALUES %s) AS data(uid, v) "
                "WHERE unique_id = data.uid",
                rows,
                template="(%s, %s::vector)",
            )
            conn.commit()

        # The provider only reports usage on success, so bill from the response
        # rather than estimating from character counts.
        tokens = 0
        if info and info.get("prompt_tokens"):
            tokens = int(info["prompt_tokens"])
        state["done"] += len(rows)
        state["prompt_tokens"] += tokens
        state["spend_usd"] = state["prompt_tokens"] / 1_000_000 * PRICE_PER_1M_TOKENS
        save_state(state)
        append_ledger({
            "ts": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "rows": len(rows),
            "prompt_tokens": tokens,
            "cumulative_tokens": state["prompt_tokens"],
            "cumulative_spend_usd": round(state["spend_usd"], 6),
            "model": R.FIREWORKS_EMBEDDING_MODEL,
        })

        processed_this_run += len(rows)
        cur.execute("SELECT count(*) FROM disaster_narratives WHERE embedding_fireworks IS NULL")
        todo = cur.fetchone()[0]
        emit(f"embedded {len(rows)} (run {processed_this_run}, total {state['done']}), "
             f"remaining {todo}, spend ${state['spend_usd']:.4f}")
        time.sleep(SLEEP)

    cur.execute("SELECT count(*), count(embedding_fireworks) FROM disaster_narratives")
    total, filled = cur.fetchone()
    cur.close()
    conn.close()
    emit(f"done: {filled}/{total} rows have a Fireworks vector; "
         f"tokens={state['prompt_tokens']} estimated spend=${state['spend_usd']:.4f}")


if __name__ == "__main__":
    main()
