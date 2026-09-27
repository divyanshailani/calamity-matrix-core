#!/usr/bin/env python3
"""One-shot data fixes for disaster_narratives.

Two jobs:
1. Normalize country variants to canonical form (retrieval.resolve_country),
   so the alias map stops carrying row-level dirt.
2. Backfill lat/lng + country for rows whose country is 'Unknown' but whose
   narrative carries coordinates — via Nominatim reverse geocoding, 1 req/s,
   with a JSON cache so it is resumable and idempotent.

Dry-run by default. Apply with --apply.
"""
import argparse
import json
import os
import re
import sys
import time
from pathlib import Path

SCRIPT_DIR = Path(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, str(SCRIPT_DIR.parent.parent))
import requests  # noqa: E402
import psycopg2  # noqa: E402
import scripts.production.retrieval as retrieval  # noqa: E402


def get_dsn():
    """Same pattern as scripts/eval/run_retrieval_eval.py — avoids src.config,
    which hard-requires INGESTION_SECRET_KEY."""
    import os as _os
    dsn = _os.environ.get("DATABASE_URL")
    if dsn:
        return dsn
    p = _os.path.expanduser("~/.calamity_rollback/DATABASE_URL.new.rotated")
    return open(p).read().strip()

CACHE = SCRIPT_DIR.parent / "eval" / ".nominatim_reverse_cache.json"
UA = "CalamityMatrixDataFix/1.0 (one-off row backfill; divyansh@calamityai.tech)"
def get_conn():
    return psycopg2.connect(get_dsn())


def fix_countries(cur, apply: bool):
    cur.execute(
        """SELECT DISTINCT country FROM disaster_narratives
           WHERE country IS NOT NULL AND lower(country) <> 'unknown'"""
    )
    rows = [r[0] for r in cur.fetchall()]
    pairs = []
    for c in rows:
        canonical = retrieval.resolve_country(c)
        if canonical != c:
            pairs.append((canonical, c))
    print("Country normalization:")
    for canonical, c in pairs:
        print(f"  {c!r} -> {canonical!r}")
    for canonical, c in pairs:
        if apply:
            cur.execute("UPDATE disaster_narratives SET country = %s WHERE country = %s",
                        (canonical, c))
            print(f"  updated {cur.rowcount} row(s)")


def load_cache() -> dict:
    if CACHE.exists():
        return json.loads(CACHE.read_text())
    return {}


def save_cache(cache: dict):
    CACHE.write_text(json.dumps(cache, indent=1))


def coord_key(lat, lng) -> str:
    return f"{lat:.4f},{lng:.4f}"


def nominatim_reverse(lat, lng, cache: dict) -> tuple:
    """Return (country, None-or-error) using the cache."""
    key = coord_key(lat, lng)
    if key in cache:
        c = cache[key]
        return (c or "Unknown"), None
    try:
        r = requests.get(
            "https://nominatim.openstreetmap.org/reverse",
            params={"lat": lat, "lon": lng, "format": "jsonv2", "zoom": 10},
            headers={"User-Agent": UA}, timeout=15)
        r.raise_for_status()
        data = r.json()
        # zoom=10: prefer country, fall back to state/region
        c = data.get("address", {}).get("country") \
            or data.get("address", {}).get("state") \
            or "Unknown"
    except Exception as e:
        return None, str(e)
    time.sleep(1.05)  # Nominatim policy: <= 1 req/s
    return c, None


def backfill_unknown(cur, apply: bool, limit: int = None):
    cur.execute("""
        SELECT id, country, lat, lng FROM disaster_narratives
        WHERE lower(country) = 'unknown' AND lat IS NOT NULL AND lng IS NOT NULL
        ORDER BY id""")
    rows = cur.fetchall()
    if limit:
        rows = rows[:limit]
    print(f"Backfill targets (unknown country, has coords): {len(rows)}")
    cache = load_cache()
    changed = 0
    for i, (row_id, _country, lat, lng) in enumerate(rows, 1):
        if (lat == 0 and lng == 0):
            continue
        c, err = nominatim_reverse(lat, lng, cache)
        if err:
            print(f"  [{i}/{len(rows)}] id={row_id} ({lat},{lng}): FAILED {err}")
            continue
        cache[coord_key(lat, lng)] = c
        if c != "Unknown":
            changed += 1
            if apply:
                cur.execute("UPDATE disaster_narratives SET country = %s WHERE id = %s",
                            (c, row_id))
        if i % 25 == 0:
            save_cache(cache)
            print(f"  [{i}/{len(rows)}] progress...")
    save_cache(cache)
    print(f"  resolved to a real country: {changed}/{len(rows)}"
          + (" (APPLIED)" if apply else " (dry run — rerun with --apply)"))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true", help="commit changes")
    ap.add_argument("--skip-backfill", action="store_true")
    ap.add_argument("--limit", type=int, default=None)
    args = ap.parse_args()

    conn = get_conn()
    cur = conn.cursor()
    fix_countries(cur, args.apply)
    if not args.skip_backfill:
        backfill_unknown(cur, args.apply, args.limit)
    if args.apply:
        conn.commit()
    else:
        conn.rollback()
    conn.close()
    print("done.")


if __name__ == "__main__":
    main()
