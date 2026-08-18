#!/usr/bin/env python3
"""Build eval/retrieval_eval.json from the live corpus.

Category design (see implementation_plan.md Phase 0):
- 10 "beyond char 500": relevant text lives past the [:500] embedding window,
      proving whether the coverage fix in Phase 1 changed anything.
- 8 exact-token: distinctive place/event names that FTS should catch.
- 6 small-pool: countries with <=5 in-scope rows, exercising the relaxation path.
- 6 taxonomy-mismatch: colloquial phrasing vs the stored disaster_type.

Ground truth keys are unique_id (has a UNIQUE constraint), never integer id —
ids are not stable across a restore from the off-box archives.

Read-only: connects to the DB and SELECTs only. Deterministic via a fixed seed.

Usage: DATABASE_URL=<dsn> python3 scripts/eval/build_eval_dataset.py
"""
import json
import os
import random
import re
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))
import psycopg2


def get_dsn():
    return os.environ.get("DATABASE_URL") or open(
        os.path.expanduser("~/.calamity_rollback/DATABASE_URL.new.rotated")
    ).read().strip()


# Colloquial phrasing that does not match the stored disaster_type, for the
# taxonomy-mismatch category. Key = stored type, value = user-style query.
MISMATCH_PAIRS = [
    ("Tropical Cyclone", "typhoon winds hitting the coast"),
    ("Wild Fire", "bushfire smoke and evacuations"),
    ("Wildfires", "wildfire smoke blanketing the city"),
    ("Flash Flood", "sudden flash flooding of the valley"),
    ("Heat Wave", "record heatwave temperatures"),
    ("Land Slide", "mudslide burying houses"),
    ("Storm Surge", "coastal storm surge flooding"),
    ("Mud Slide", "mudslide after heavy rain"),
]

# Famous-event keyword fingerprints. A row is a candidate only if it is in
# scope (event_year >= 2000), contains the keyword, and its country is one of
# the event's canonical countries — plain substring search alone matches
# incidental text (e.g. "Kashmir" inside a Bangladesh cold-wave narrative).
EXACT_FINGERPRINTS = [
    # (label, keyword, canonical countries, target year, allowed disaster_types or None)
    ("hurricane katrina new orleans", "Katrina", ("USA", "United States of America"), 2005, None),
    ("sichuan earthquake 2008", "Sichuan", ("China",), 2008, ("Earthquake",)),
    ("cyclone idai mozambique", "Idai", ("Mozambique",), 2019, ("Tropical Cyclone",)),
    ("cyclone in bangladesh 2007", None, ("Bangladesh",), 2007, ("Tropical Cyclone",)),
    # No in-scope Pakistan/India EARTHQUAKE row near 2005 mentions Kashmir; the
    # closest real ground truth is the 2010 Pakistan flood narrative that does.
    ("kashmir floods 2010", "Kashmir", ("Pakistan", "India"), 2010, ("Flood",)),
    ("christchurch earthquake 2011", "Christchurch", ("New Zealand",), 2011, None),
    # Tohoku never appears verbatim in the corpus; use the Japan row nearest 2011.
    ("japan earthquake tsunami 2011", None, ("Japan", "Japan region"), 2011, None),
    ("bangladesh cyclone bhola 2009", "Bhola", ("Bangladesh",), 1970, ("Tropical Cyclone",)),
]

STOP = set(
    "a an the and or but of in on at to for with from by as is are was were be been has had have "
    "its it's their they this that these those not no so such also over under during after before "
    "according more most than about between into out up down near plus".split()
)


def cleaned_phrase(text: str, rng: random.Random) -> str:
    """A 4-7 word phrase from the middle of a narrative, minus URLs/refs."""
    text = re.sub(r"\(\[[^\]]*\]\([^)]*\)\)", " ", text)  # markdown-ish citations
    text = re.sub(r"https?://\S+", " ", text)
    text = re.sub(r"[^A-Za-z ,'\-]", " ", text)
    sents = re.split(r"(?<=[.!?])\s+", text)
    sents = [s.strip() for s in sents if s.strip()]
    for s in sents:
        words = [w for w in re.split(r"[^A-Za-z\-']+", s) if w]
        for start in range(0, max(1, len(words) - 6), 2):
            phrase = words[start : start + rng.randint(4, 7)]
            if len(phrase) >= 4 and not any(w.lower() in STOP for w in phrase[:2]):
                return " ".join(phrase)
    return None


def main():
    rng = random.Random(20260818)
    conn = psycopg2.connect(get_dsn())
    cur = conn.cursor()
    cur.execute(
        """
        SELECT id, unique_id, country, disaster_type, event_year,
               length(narrative_text), narrative_text
        FROM disaster_narratives
        WHERE narrative_text IS NOT NULL AND event_year >= 2000
        """
    )
    rows = [
        {
            "id": r[0], "unique_id": r[1], "country": r[2], "disaster_type": r[3],
            "event_year": r[4], "len": r[5], "text": r[6],
        }
        for r in cur.fetchall()
    ]
    cur.close()
    conn.close()
    print(f"corpus rows (in scope): {len(rows)}")

    by_uid = {r["unique_id"]: r for r in rows}
    queries = []

    # 1. beyond char 500 -----------------------------------------------------
    long_rows = [r for r in rows if r["len"] > 2500]
    print(f"  long rows (>2500 chars): {len(long_rows)}")
    for r in rng.sample(long_rows, min(10, len(long_rows))):
        phrase = cleaned_phrase(r["text"][600:1400], rng)
        if not phrase:
            continue
        queries.append({
            "id": f"q_beyond500_{len(queries)+1}",
            "query_text": phrase,
            "disaster_type": r["disaster_type"],
            "country": r["country"],
            "event_year": r["event_year"],
            "relevant_unique_ids": [r["unique_id"]],
            "note": "answer text lies beyond the [:500] embedding window",
        })

    # 2. exact-token fingerprints --------------------------------------------
    used_uids = set()
    for label, keyword, countries, target_year, types in EXACT_FINGERPRINTS:
        hits = [
            r for r in rows
            if r["country"] in countries
            and (types is None or r["disaster_type"] in types)
            and (keyword is None or keyword.lower() in r["text"].lower())
            and r["unique_id"] not in used_uids
        ]
        if not hits:
            print(f"  !! no rows for {label}")
            continue
        # Among candidates, choose the one nearest the event year.
        r = min(hits, key=lambda x: abs(x["event_year"] - target_year))
        used_uids.add(r["unique_id"])
        queries.append({
            "id": f"q_exact_{len(queries)+1}",
            "query_text": label,
            "disaster_type": r["disaster_type"],
            "country": r["country"],
            "event_year": r["event_year"],
            "relevant_unique_ids": [r["unique_id"]],
            "note": f"exact-token fingerprint: {label}",
        })

    # 3. small-pool countries ------------------------------------------------
    from collections import Counter
    country_counts = Counter(r["country"] for r in rows)
    small = [c for c, n in country_counts.items() if 2 <= n <= 5]
    for c in rng.sample(small, min(6, len(small))):
        members = [r for r in rows if r["country"] == c]
        type_ = Counter(m["disaster_type"] for m in members).most_common(1)[0][0]
        queries.append({
            "id": f"q_smallpool_{len(queries)+1}",
            "query_text": f"{type_} in {c}",
            "disaster_type": type_,
            "country": c,
            "event_year": max(m["event_year"] for m in members),
            "relevant_unique_ids": [m["unique_id"] for m in members if m["disaster_type"] == type_],
            "note": f"small pool: {c} has {len(members)} in-scope rows",
        })

    # 4. taxonomy mismatch ----------------------------------------------------
    for stored, phrase in MISMATCH_PAIRS:
        hits = [r for r in rows if r["disaster_type"].lower() == stored.lower() and r["unique_id"] not in used_uids]
        if not hits:
            print(f"  !! no rows for mismatch pair {stored}")
            continue
        r = rng.choice(hits)
        used_uids.add(r["unique_id"])
        queries.append({
            "id": f"q_mismatch_{len(queries)+1}",
            "query_text": phrase,
            "disaster_type": r["disaster_type"],
            "country": r["country"],
            "event_year": r["event_year"],
            "relevant_unique_ids": [r["unique_id"]],
            "note": f"stored type is '{stored}', query uses colloquial wording",
        })

    # sanity: all unique_ids must actually exist -----------------------------
    missing = [qid for q in queries for uid in q["relevant_unique_ids"] if uid not in by_uid]
    if missing:
        raise SystemExit(f"eval dataset references missing unique_ids: {missing[:5]}")

    out = os.path.join(os.path.dirname(__file__), "..", "..", "eval", "retrieval_eval.json")
    os.makedirs(os.path.dirname(out), exist_ok=True)
    with open(out, "w") as f:
        json.dump(queries, f, indent=2)
    print(f"wrote {out}: {len(queries)} queries")


if __name__ == "__main__":
    main()
