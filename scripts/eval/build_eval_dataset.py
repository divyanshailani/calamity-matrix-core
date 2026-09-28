#!/usr/bin/env python3
"""Build eval/retrieval_eval_v2.json (81 queries) + eval/corpus_snapshot.json.

Category design (grown from the original 32-query Phase 0 set, 2026-09-28):
- 24 "beyond char 500": relevant text lives past the [:500] embedding window.
      Written to eval/retrieval_eval_v2.json, NOT the original
      eval/retrieval_eval.json: the 32-query set is frozen for cross-session
      comparison, and --guard compares against eval/baseline.json which was
      measured on it. The v2 set gets its own baseline once the Fireworks
      embedding cache covers the new query ids.
- 21 exact-token: distinctive place/event names that FTS should catch
      (22 fingerprints: original 8 + 14 probe-verified to exist post
      noise-floor 2026-09-28). Katrina correctly skips: seed row is a stub.
- 18 small-pool: countries with 2-5 in-scope rows, exercising the relaxation
      path. The original small-pool query q_smallpool_22 taught this lesson:
      its ground truth WAS two USGS stubs the noise floor (correctly) hides —
      so small-pool ground truth now also requires LENGTH >= 200.
- 18 taxonomy-mismatch: colloquial phrasing vs the stored disaster_type.

Corpus snapshot: every relevant row's full narrative_text is copied to
eval/corpus_snapshot.json. The weekly crawler mutates the live DB, and a
"relevant" doc that gets deleted or overwritten silently turns a recall
failure into a phantom regression (see the Katrina flip, HANDOFF 2026-09-28).
With the snapshot, an eval run can distinguish "retrieval missed it" from
"ground truth no longer exists in the DB".

Ground truth keys are unique_id (has a UNIQUE constraint), never integer id —
ids are not stable across a restore from the off-box archives.

Read-only: connects to the DB and SELECTs only. Deterministic via a fixed seed.

Usage: DATABASE_URL=<dsn> python3 scripts/eval/build_eval_dataset.py
       --dataset eval/retrieval_eval_v2.json on run_retrieval_eval.py points
       at this set (needs embedding cache coverage for its query ids first).
"""
import json
import os
import random
import re
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))
import psycopg2
from scripts.production.retrieval import NOISE_FLOOR_SQL


def get_dsn():
    return os.environ.get("DATABASE_URL") or open(
        os.path.expanduser("~/.calamity_rollback/DATABASE_URL.new.rotated")
    ).read().strip()


# Colloquial phrasing that does not match the stored disaster_type, for the
# taxonomy-mismatch category. Key = stored type, value = user-style query.
# First 8 are the Phase 0 pairs; the rest were added 2026-09-28 when the set
# grew to 96 (same rule: phrase must NOT contain the stored type's word).
MISMATCH_PAIRS = [
    ("Tropical Cyclone", "typhoon winds hitting the coast"),
    ("Wild Fire", "bushfire smoke and evacuations"),
    ("Wildfires", "wildfire smoke blanketing the city"),
    ("Flash Flood", "sudden flash flooding of the valley"),
    ("Heat Wave", "record heatwave temperatures"),
    ("Land Slide", "mudslide burying houses"),
    ("Storm Surge", "coastal storm surge flooding"),
    ("Mud Slide", "mudslide after heavy rain"),
    ("Cold Wave", "deep freeze crippling the power grid"),
    ("Drought", "reservoirs drying up and crops failing"),
    ("Epidemic", "outbreak of a deadly disease"),
    ("Volcano", "ash cloud forces airport closures"),
    ("Earthquake", "tremor levels hit the city"),
    ("Flood", "river bursts its banks downtown"),
    ("Tsunami", "harbour waves flood the coastal road"),
    ("Insect Infestation", "desert locust swarms eat the harvest"),
    ("Snow Avalanche", "snowslides cut off mountain villages"),
    ("Severe Local Storm", "tornado touches down in the suburbs"),
]

# Famous-event keyword fingerprints. A row is a candidate only if it is in
# scope (event_year >= 2000), contains the keyword, and its country is one of
# the event's canonical countries — plain substring search alone matches
# incidental text (e.g. "Kashmir" inside a Bangladesh cold-wave narrative).
# First 8 are the Phase 0 originals; the rest were probe-verified against the
# live DB (post noise-floor) on 2026-09-28 — candidates that matched 0 rows
# (Nargis, Sidr, Muzaffarabad, Russia HW, Maui, Canada, Sandy, ...) were
# dropped, so none of these can silently vanish at build time.
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
    ("haiti earthquake 2010", "Haiti", ("Haiti",), 2010, ("Earthquake",)),
    ("nepal earthquake 2015", None, ("Nepal",), 2015, ("Earthquake",)),
    ("chile earthquake 2010", "Chile", ("Chile",), 2010, ("Earthquake",)),
    ("cyclone winston fiji 2016", "Winston", ("Fiji",), 2016, ("Tropical Cyclone",)),
    ("typhoon haiyan philippines 2013", "Haiyan", ("Philippines",), 2013, ("Tropical Cyclone",)),
    ("libya flood derna 2023", "Derna", ("Libya",), 2023, ("Flood",)),
    ("turkey earthquake 2023", "Turkey", ("Turkey", "Türkiye", "Turkiye"), 2023, ("Earthquake",)),
    ("afghanistan earthquake herat 2023", "Herat", ("Afghanistan",), 2023, ("Earthquake",)),
    ("hunga tonga eruption 2022", "Hunga", ("Tonga", "Tonga region"), 2022, ("Volcano",)),
    ("merapi eruption 2010", "Merapi", ("Indonesia",), 2010, ("Volcano",)),
    ("cyclone amphan 2020", "Amphan", ("Bangladesh", "India"), 2020, ("Tropical Cyclone",)),
    ("cyclone kenneth mozambique 2019", "Kenneth", ("Mozambique",), 2019, ("Tropical Cyclone",)),
    ("somalia drought 2011", "Somalia", ("Somalia",), 2011, ("Drought",)),
    ("ebola outbreak west africa 2014", "Ebola", ("Guinea", "Sierra Leone", "Liberia",
                                                  "Democratic Republic of the Congo",
                                                  "Democratic Republic of Congo", "Congo"),
     2014, ("Epidemic",)),
]

STOP = set(
    "a an the and or but of in on at to for with from by as is are was were be been has had have "
    "its it's their they this that these those not no so such also over under during after before "
    "according more most than about between into out up down near plus".split()
)


def cleaned_phrase(text: str, rng: random.Random) -> str:
    """A 4-7 word phrase from the middle of a narrative, minus URLs/refs."""
    chunk = re.split(r"https?://|\[|Reference|Source", text)[0]
    words = re.findall(r"[A-Za-z][A-Za-z'-]{2,}", chunk)
    if len(words) < 12:
        return None
    start = rng.randint(4, len(words) - 8)
    n = rng.randint(4, min(7, len(words) - start))
    phrase = " ".join(words[start:start + n]).strip()
    if len(phrase) < 15 or phrase.lower().split()[0] in STOP:
        return None
    return phrase


def main():
    rng = random.Random(20260928)
    conn = psycopg2.connect(get_dsn())
    cur = conn.cursor()
    # Shared with retrieval._tier_where: ground truth must come from the same
    # rows the production filter can actually return. Without this, 2026-09-28
    # showed small-pool sets enshrining USGS stubs as relevant (q_smallpool_22
    # expected two "A Magnitude ..." rows the noise floor rightly hides).
    # NOTE: this execute passes NO params, so the single '%' in the floor is
    # literal — keep this query param-free.
    cur.execute(
        f"""
        SELECT id, unique_id, country, disaster_type, event_year,
               length(narrative_text), narrative_text
        FROM disaster_narratives
        WHERE narrative_text IS NOT NULL AND event_year >= 2000
          AND {NOISE_FLOOR_SQL}
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
    print(f"corpus rows (in scope, above noise floor): {len(rows)}")

    # 1. beyond char 500 (24) --------------------------------------------------
    long_rows = [r for r in rows if r["len"] > 2500]
    print(f"  long rows (>2500 chars): {len(long_rows)}")

    by_uid = {r["unique_id"]: r for r in rows}
    queries = []
    # Pool past 24 candidates: cleaned_phrase rejects unlucky windows
    # (stop-word start, <12 usable words) — a single 24-row pass silently
    # lost 10 slots on 2026-09-28. Keep drawing until 24 are built.
    built = 0
    for r in rng.sample(long_rows, len(long_rows)):
        if built >= 24:
            break
        phrase = None
        for _ in range(5):
            phrase = cleaned_phrase(r["text"][600:1400], rng)
            if phrase:
                break
        if not phrase:
            continue
        built += 1
        queries.append({
            "id": f"q_beyond500_{len(queries)+1}",
            "query_text": phrase,
            "disaster_type": r["disaster_type"],
            "country": r["country"],
            "event_year": r["event_year"],
            "relevant_unique_ids": [r["unique_id"]],
            "note": "answer text lies beyond the [:500] embedding window",
        })

    # 2. exact-token fingerprints (25 slots = 8 original + 17 verified) -------
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

    # 3. small-pool countries (18) ---------------------------------------------
    # len>=200 on MEMBERS (not just the pool): with ~2300 noise-floor rows
    # spread over ~200 countries, a 2-5 member pool of pure USGS one-liners
    # is unanswerable by design and only measures itself.
    from collections import Counter
    country_counts = Counter(r["country"] for r in rows)
    small = [c for c, n in country_counts.items()
             if 2 <= n <= 5
             and any(m["country"] == c and m["len"] >= 200 for m in rows)]
    for c in rng.sample(small, 18):
        members = [r for r in rows if r["country"] == c]
        types_with_content = Counter(
            m["disaster_type"] for m in members if m["len"] >= 200)
        type_ = types_with_content.most_common(1)[0][0]
        rel = [m["unique_id"] for m in members
               if m["disaster_type"] == type_ and m["len"] >= 200]
        queries.append({
            "id": f"q_smallpool_{len(queries)+1}",
            "query_text": f"{type_} in {c}",
            "disaster_type": type_,
            "country": c,
            "event_year": max(m["event_year"] for m in members),
            "relevant_unique_ids": rel,
            "note": f"small pool: {c} has {len(members)} in-scope rows "
                    f"({len(rel)} with narrative >= 200 chars)",
        })

    # 4. taxonomy mismatch (18) -------------------------------------------------
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

    eval_dir = os.path.join(os.path.dirname(__file__), "..", "..", "eval")
    os.makedirs(eval_dir, exist_ok=True)
    out = os.path.join(eval_dir, "retrieval_eval_v2.json")
    with open(out, "w") as f:
        json.dump(queries, f, indent=2)
    print(f"wrote {out}: {len(queries)} queries")

    # Corpus snapshot: every relevant row's full text. run_retrieval_eval.py
    # can diff this against the live DB to prove a miss is a retrieval miss,
    # not a ground-truth row the crawler deleted underneath the dataset.
    snap = {uid: {"country": by_uid[uid]["country"],
                  "disaster_type": by_uid[uid]["disaster_type"],
                  "event_year": by_uid[uid]["event_year"],
                  "narrative_text": by_uid[uid]["text"]}
            for q in queries for uid in q["relevant_unique_ids"]}
    snap_path = os.path.join(eval_dir, "corpus_snapshot.json")
    with open(snap_path, "w") as f:
        json.dump(snap, f, indent=1)
    print(f"wrote {snap_path}: {len(snap)} ground-truth rows snapshotted")


if __name__ == "__main__":
    main()
