#!/usr/bin/env python3
"""One-shot DDL reweight for the fts_vector generated column.

Switches the sparse-arm FTS weights from narrative=A, country/type=B
to narrative=A, country/type=C (rag_quality_report.md §10.2). With
ts_rank(..., 1|2) the country/type containment terms are nearly
constant across a candidate pool, so C degrades gracefully.

Dry-run by default (prints current expression + planned).
Apply with --apply; restore the old weights with --rollback.
DSN: DATABASE_URL env or ~/.calamity_rollback/DATABASE_URL.new.rotated.
"""
import argparse
import os
import sys
import time

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(SCRIPT_DIR))
import psycopg2  # noqa: E402

OLD_EXPR = """(setweight(to_tsvector('english', COALESCE(narrative_text, '')), 'A')
 || setweight(to_tsvector('english', COALESCE(country, '')), 'B')
 || setweight(to_tsvector('english', COALESCE(disaster_type, '')), 'B'))"""
NEW_EXPR = """(setweight(to_tsvector('english', COALESCE(narrative_text, '')), 'A')
 || setweight(to_tsvector('english', COALESCE(country, '')), 'C')
 || setweight(to_tsvector('english', COALESCE(disaster_type, '')), 'C'))"""


def get_dsn():
    dsn = os.environ.get("DATABASE_URL")
    if dsn:
        return dsn
    p = os.path.expanduser("~/.calamity_rollback/DATABASE_URL.new.rotated")
    return open(p).read().strip()


def get_expr(cur):
    cur.execute("""SELECT pg_get_expr(d.adbin, d.adrelid)
                   FROM pg_attrdef d JOIN pg_attribute a
                     ON a.attrelid = d.adrelid AND a.attnum = d.adnum
                   WHERE a.attrelid = 'disaster_narratives'::regclass
                     AND a.attname = 'fts_vector'""")
    row = cur.fetchone()
    return row[0] if row else None


def weights_of(expr):
    """Extract the three setweight letters in expression order."""
    return [s for s in "ABC" if f"'{s}'" in expr] if expr else []


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true",
                    help="switch to narrative=A, country/type=C")
    ap.add_argument("--rollback", action="store_true",
                    help="restore narrative=A, country/type=B")
    args = ap.parse_args()
    assert not (args.apply and args.rollback), "--apply and --rollback are exclusive"

    conn = psycopg2.connect(get_dsn(), connect_timeout=10)
    conn.autocommit = False
    cur = conn.cursor()
    current = get_expr(cur)
    print(f"current: weights={weights_of(current)}")
    print(f"        {current}")

    if not args.apply and not args.rollback:
        print(f"\nplanned: weights={weights_of(NEW_EXPR)}")
        print(f"        {NEW_EXPR}")
        print("dry run — pass --apply (or --rollback) to execute.")
        conn.rollback()
        return

    target = NEW_EXPR if args.apply else OLD_EXPR
    cur.execute("SELECT count(*) FROM disaster_narratives")
    n = cur.fetchone()[0]
    t0 = time.time()
    cur.execute("ALTER TABLE disaster_narratives DROP COLUMN fts_vector")
    cur.execute("ALTER TABLE disaster_narratives ADD COLUMN fts_vector tsvector "
                f"GENERATED ALWAYS AS ({target}) STORED")
    cur.execute("CREATE INDEX idx_dn_fts ON disaster_narratives USING gin (fts_vector)")
    cur.execute("ANALYZE disaster_narratives")
    conn.commit()
    dur = time.time() - t0

    cur.execute("SELECT count(*), count(fts_vector) FROM disaster_narratives")
    total, populated = cur.fetchone()
    cur.execute("SELECT indexdef FROM pg_indexes WHERE tablename='disaster_narratives' "
                "AND indexname='idx_dn_fts'")
    idx = cur.fetchone()[0]
    after = get_expr(cur)
    print(f"done in {dur:.1f}s: {n} rows, fts populated {populated}/{total}")
    print(f"new:     weights={weights_of(after)}")
    print(f"index:   {idx}")
    assert populated == total == n, "fts_vector not fully populated after reweight"
    conn.close()


if __name__ == "__main__":
    main()
