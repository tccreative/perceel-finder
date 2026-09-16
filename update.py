#!/usr/bin/env python3
"""Collect percelen for sale in Suriname, deduplicate, geocode, publish.

    python3 update.py                 # full run
    python3 update.py --fast          # skip per-listing detail pages
    python3 update.py --only remy,oso # one or more sources
    python3 update.py --images        # also save compressed WebP thumbnails
    python3 update.py --no-geocode    # reuse cached coordinates only
"""
from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

from perceel import dates, dedup, geocode, store, verified
from perceel.core import CONFIG, DATA, Http, clean
from perceel.sources import facebook, run_all

ROOT = Path(__file__).resolve().parent
WEB_DATA = ROOT / "web" / "data" / "listings.json"


def in_target_area(item: dict) -> bool:
    wanted = [w.lower() for w in CONFIG["wanted_districts"]]
    excluded = [e.lower() for e in CONFIG["excluded_places"]]
    blob = " ".join(clean(item.get(f) or "") for f in
                    ("district", "resort", "raw_location", "title", "street",
                     "geocode_match")).lower()
    if any(x in blob for x in excluded):
        return False
    district = (item.get("district") or "").lower()
    if district:
        return district in wanted
    return any(w in blob for w in wanted)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", default="")
    ap.add_argument("--fast", action="store_true")
    ap.add_argument("--images", action="store_true")
    ap.add_argument("--no-geocode", action="store_true")
    args = ap.parse_args()
    only = [s.strip() for s in args.only.split(",") if s.strip()] or None

    t0 = time.time()
    http = Http()

    print("1/5  scraping sources")
    items = run_all(http, only=only, deep=not args.fast)
    fb = facebook.scrape()
    if fb:
        print(f"  -> Facebook (captured in browser): {len(fb)} listings")
        items.extend(fb)
    print(f"     raw total: {len(items)}")

    stamped = dates.enrich(http, items)
    print(f"     publish dates found for {stamped} listings")

    print("2/5  removing duplicates")
    unique, dropped = dedup.deduplicate(items)
    print(f"     {len(unique)} unique ({dropped} duplicates merged)")

    print("3/5  geocoding")
    if not args.no_geocode:
        for n, it in enumerate(unique, 1):
            geocode.geocode(http, it)
            if n % 25 == 0:
                print(f"     {n}/{len(unique)}")
                geocode.save()
        geocode.save()
    located = sum(1 for i in unique if i.get("lat"))
    areas = sum(1 for i in unique if i.get("lat") is None and i.get("area_lat") is not None)
    checked = sum(1 for i in unique if i.get("geocode_checked"))
    print(f"     {located}/{len(unique)} on a street, {areas} only a buurt, "
          f"{len(unique) - located - areas} unplaced ({checked} hand-checked)")

    # second dedup pass now that coordinates exist
    unique, extra = dedup.deduplicate(unique)
    if extra:
        print(f"     {extra} more duplicates found after geocoding")

    for it in unique:
        # A plot under EUR 1.000 is a parsing artefact (a "from" figure, a
        # per-m2 rate, a phone number), not a price. Drop it rather than let
        # it poison the cheapest-first sort.
        from perceel.core import price_in_eur
        if it.get("price") and (price_in_eur(it["price"], it.get("currency")) or 0) < 1000:
            it["price_suspect"] = it["price"]
            it["price"] = None
            it["currency"] = None
        geocode.annotate_distance(it)
        it["in_target_area"] = in_target_area(it)

    if args.images:
        print("4/5  saving compressed thumbnails")
        from perceel.images import fetch_thumbs
        n = fetch_thumbs(http, [i for i in unique if i.get("in_target_area")],
                         ROOT / "web" / "thumbs")
        print(f"     {n} new thumbnails")
    else:
        print("4/5  thumbnails skipped (use --images)")

    todo = verified.write_queue(unique)
    print(f"     {todo} addresses waiting to be checked by hand "
          f"(data/needs_check.json)")

    print("5/5  writing data")
    unique.sort(key=lambda i: (not i.get("in_target_area"),
                               i.get("km_from_centre") if i.get("km_from_centre") is not None else 999))
    data = store.merge_run(store.load(), unique)
    data["home"] = CONFIG["home"]
    data["city_centre"] = CONFIG["city_centre"]
    data["sources"] = sorted({i["source"] for i in unique})
    data["counts"]["in_target_area"] = sum(1 for i in unique if i.get("in_target_area"))
    data["counts"]["duplicates_removed"] = dropped + extra
    store.save(data, extra_paths=[WEB_DATA])

    c = data["counts"]
    print(f"\nDone in {time.time()-t0:.0f}s")
    print(f"  {c['active']} plots | {c['in_target_area']} in Paramaribo/Wanica "
          f"| {c['new_this_run']} new | {c['duplicates_removed']} duplicates removed "
          f"| {c['gone_since_last_run']} gone")
    print(f"  data: {store.STORE}")
    print(f"  map:  {ROOT / 'web' / 'index.html'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
