#!/usr/bin/env python3
"""Phase 1 backfill: re-embed every narrative with the full [:2000] window into
embedding_v2 (the old column stays intact as the rollback path).

Consistent with the fixed ingestion window (live_ingestion.py):
    "{disaster} in {country} (Year: {year}). Additional Context: {text[:2000]}"

Safety, per implementation_plan.md:
- writes embedding_v2 only, never touches embedding
- batched (16 per HF request) to stay near the single-call quota cost
- resumable: resumes FROM rows where embedding_v2 IS NULL
- checkpointed to eval/.reembed_checkpoint.json after every batch
- aborts cleanly (transactional UPSERT) if the router refuses repeatedly,
  leaving the table consistent

Usage: DATABASE_URL=<dsn> HF_TOKEN=<token> python3 scripts/eval/reembed_embedding_v2.py
"""
import json
import os
import sys
import time

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))
import psycopg2
from psycopg2.extras import execute_values

import scripts.production.retrieval as R

CHECKPOINT = os.path.join(os.path.dirname(__file__), "..", "..", "eval", ".reembed_checkpoint.json")
BATCH = 16
SLEEP = 2.0
MAX_CONSECUTIVE_FAILURES = 5


def get_dsn():
    return os.environ.get("DATABASE_URL") or open(
        os.path.expanduser("~/.calamity_rollback/DATABASE_URL.new.rotated")
    ).read().strip()


def emit(msg):
    line = f"{time.strftime('%Y-%m-%d %H:%M:%S UTC', time.gmtime())} {msg}"
    print(line, flush=True)


def main():
    conn = psycopg2.connect(get_dsn())
    cur = conn.cursor()
    cur.execute("SELECT count(*) FROM disaster_narratives WHERE embedding_v2 IS NULL")
    todo = cur.fetchone()[0]
    emit(f"rows to embed: {todo}")

    cp = {"done": 0}
    if os.path.exists(CHECKPOINT):
        with open(CHECKPOINT) as f:
            cp = json.load(f)

    consecutive_failures = 0
    while todo > 0:
        cur.execute(
            "SELECT unique_id, country, disaster_type, event_year, narrative_text "
            "FROM disaster_narratives WHERE embedding_v2 IS NULL "
            "ORDER BY id LIMIT %s",
            (BATCH,),
        )
        batch = cur.fetchall()
        if not batch:
            break
        texts = [
            R.build_semantic_query(r[2], r[1], r[3], (r[4] or "")[:2000])
            for r in batch
        ]
        vecs = R.embed_many(texts, timeout=90)
        if not vecs or len(vecs) != len(batch):
            consecutive_failures += 1
            emit(f"embedding call failed ({consecutive_failures}/{MAX_CONSECUTIVE_FAILURES}); sleeping")
            if consecutive_failures >= MAX_CONSECUTIVE_FAILURES:
                emit("giving up: router unreachable, table left consistent")
                sys.exit(1)
            time.sleep(10 * consecutive_failures)
            continue
        consecutive_failures = 0

        rows = [(uid, v) for (uid, _, _, _, _), v in zip(batch, vecs) if v is not None]
        if rows:
            execute_values(
                cur,
                "UPDATE disaster_narratives SET embedding_v2 = data.v "
                "FROM (VALUES %s) AS data(uid, v) "
                "WHERE unique_id = data.uid",
                rows,
                template="(%s, %s::vector)",
            )
            conn.commit()
        cp["done"] = cp.get("done", 0) + len(rows)
        with open(CHECKPOINT, "w") as f:
            json.dump(cp, f)
        cur.execute("SELECT count(*) FROM disaster_narratives WHERE embedding_v2 IS NULL")
        todo = cur.fetchone()[0]
        emit(f"embedded {len(rows)} (total {cp['done']}), remaining {todo}")
        time.sleep(SLEEP)

    cur.close()
    conn.close()
    emit(f"done: {cp['done']} rows embedded into embedding_v2")


if __name__ == "__main__":
    main()
