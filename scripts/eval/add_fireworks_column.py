"""Phase C — add the Fireworks (Qwen3) vector column and its HNSW index.

Qwen3 and BGE are different vector spaces, so Fireworks vectors get their own
column instead of overwriting `embedding` / `embedding_v2`. This script is
idempotent and additive: it never drops, rewrites, or reads existing vectors.

Usage:
    python3 scripts/eval/add_fireworks_column.py --dry-run
    python3 scripts/eval/add_fireworks_column.py --apply
    python3 scripts/eval/add_fireworks_column.py --apply --index   # after backfill
"""
import argparse
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

import psycopg2  # noqa: E402

COLUMN = "embedding_fireworks"
INDEX = "idx_dn_embedding_fireworks_hnsw"
DIM = int(os.getenv("FIREWORKS_EMBEDDING_DIMENSIONS", "1024"))

ADD_COLUMN_SQL = f"ALTER TABLE disaster_narratives ADD COLUMN IF NOT EXISTS {COLUMN} vector({DIM});"

# Built only after the backfill so HNSW is constructed once over real data
# instead of being incrementally maintained through 2,600 individual inserts.
CREATE_INDEX_SQL = (
    f"CREATE INDEX IF NOT EXISTS {INDEX} ON disaster_narratives "
    f"USING hnsw ({COLUMN} vector_cosine_ops) WITH (m = 16, ef_construction = 64);"
)

ROLLBACK_SQL = f"""-- Rollback (destructive to Fireworks vectors only):
DROP INDEX IF EXISTS {INDEX};
ALTER TABLE disaster_narratives DROP COLUMN IF EXISTS {COLUMN};"""


def dsn():
    url = os.getenv("DATABASE_URL")
    if not url:
        sys.exit("DATABASE_URL is required (never hardcode the DSN).")
    return url


def redact(url):
    import re
    return re.sub(r"://[^@]*@", "://***:***@", url)


def inspect(cur):
    cur.execute(
        "SELECT column_name, udt_name FROM information_schema.columns "
        "WHERE table_name = 'disaster_narratives' AND column_name LIKE 'embedding%' "
        "ORDER BY column_name"
    )
    cols = cur.fetchall()
    cur.execute("SELECT count(*) FROM disaster_narratives")
    total = cur.fetchone()[0]
    cur.execute("SELECT indexname FROM pg_indexes WHERE tablename = 'disaster_narratives' ORDER BY indexname")
    idx = [r[0] for r in cur.fetchall()]
    return cols, total, idx


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true", help="execute the DDL (default is inspect only)")
    ap.add_argument("--index", action="store_true", help="also build the HNSW index (run after backfill)")
    ap.add_argument("--dry-run", action="store_true", help="inspect and print planned DDL")
    args = ap.parse_args()

    url = dsn()
    print(f"[*] target: {redact(url)}")
    conn = psycopg2.connect(url)
    conn.autocommit = True
    cur = conn.cursor()
    try:
        cols, total, idx = inspect(cur)
        print(f"[*] rows: {total}")
        print(f"[*] embedding columns: {cols}")
        print(f"[*] has {COLUMN}: {any(c[0] == COLUMN for c in cols)}")
        print(f"[*] has {INDEX}: {INDEX in idx}")

        if not args.apply:
            print("\n[dry-run] planned DDL:")
            print(" ", ADD_COLUMN_SQL)
            if args.index:
                print(" ", CREATE_INDEX_SQL)
            print("\n" + ROLLBACK_SQL)
            return

        print(f"\n[+] {ADD_COLUMN_SQL}")
        cur.execute(ADD_COLUMN_SQL)
        if args.index:
            cur.execute(f"SELECT count({COLUMN}) FROM disaster_narratives")
            filled = cur.fetchone()[0]
            if filled == 0:
                print("[!] refusing to build HNSW over an empty column; run the backfill first.")
            else:
                print(f"[+] building HNSW over {filled} vectors (this can take a minute)...")
                cur.execute(CREATE_INDEX_SQL)

        cols, total, idx = inspect(cur)
        cur.execute(f"SELECT count(*) - count({COLUMN}) FROM disaster_narratives")
        print(f"[=] embedding columns now: {cols}")
        print(f"[=] {COLUMN} nulls: {cur.fetchone()[0]} / {total}")
        print(f"[=] {INDEX} present: {INDEX in idx}")
    finally:
        cur.close()
        conn.close()


if __name__ == "__main__":
    main()
