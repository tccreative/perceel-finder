# perceel-finder

Finds land (percelen) for sale in Suriname — focused on **Paramaribo** and **Wanica**,
ranked by how close each plot is to Paramaribo centrum compared to where you live now
(Project Schuilplaats, Shantaweg, Kwatta). Everything lands on one OpenStreetMap map.

## What it does

1. **Scrapes** the Surinamese estate-agent sites (one polite request at a time, honest user-agent).
2. **Removes duplicates** — inside a site and across sites. The same plot advertised by
   two agents becomes one pin with both links.
3. **Geocodes** each address with OpenStreetMap Nominatim (cached, so re-runs are fast)
   and computes distance to the city and to home.
4. **Publishes** `web/index.html` — a Leaflet map with filters, photos, sizes, prices
   and clickable phone / WhatsApp links.

## Sources

| key | site | notes |
|---|---|---|
| `remy` | remyvastgoed.com | biggest supply, ~680 plots |
| `surgoed` | surgoed.com | ~100 plots, one page |
| `remax` | remax.sr | ~100 plots |
| `oso` | osonangadjari.com | ~140 plots, detail pages read for size + photos |
| `terzol` | terzol.com | ~20 plots |
| `karima` | karimainvest.com | generic scraper |
| `survast`, `shopsmart`, `marktplaats_sr` | | generic scraper, small/flaky |
| `facebook` | Marketplace | see below |

### Facebook

Facebook blocks automated scraping and bans accounts that try it, so there is **no
Facebook scraper in this repo**. Instead, Marketplace is read in a real browser and the
results are written to `data/facebook.json`, which `update.py` folds into the same
pipeline — deduplicated against the agent sites like any other source.

`data/facebook.json` format:

```json
[{"url":"https://www.facebook.com/marketplace/item/123/","title":"...","street":"Kalloestraat",
  "resort":"Kwatta","district":"Wanica","price":29500,"currency":"EUR","size_m2":600,
  "phones":["+5978523435"],"title_type":"Eigendom","description":"..."}]
```

## Running it

```bash
python3 -m venv .venv && ./.venv/bin/pip install -r requirements.txt
./.venv/bin/python update.py            # full run (scrape + dedupe + geocode)
./.venv/bin/python update.py --fast     # skip per-listing detail pages
./.venv/bin/python update.py --only remy,surgoed
./.venv/bin/python update.py --images   # also save compressed WebP thumbnails (640px, q70)
./.venv/bin/python update.py --no-geocode
```

Then open `web/index.html`, or serve the `web/` folder.

A run is **incremental**: `data/listings.json` keeps `first_seen` / `last_seen` per plot,
flags what is new since the previous run, records price drops, and archives plots that
disappeared from the sites.

## Publishing (GitHub Pages)

The site is served from the `docs/` folder of this repo:
**https://tccreative.github.io/perceel-finder/**

```bash
./publish.sh                 # scrape + rebuild docs/ + commit + push
./publish.sh --skip-scrape   # rebuild docs/ from existing data and push
```

`publish.sh` runs on the Contabo VPS at `/opt/perceel-finder`, pushing over SSH
with a repo-scoped deploy key (`~/.ssh/perceel_finder_deploy`). Listing photos
are downloaded once and re-encoded as 480px WebP at quality 62 — roughly 7 KB
each — so the map loads fast and does not hotlink the agents' image servers.

To refresh on a schedule:

```cron
0 6 * * 1,4  /opt/perceel-finder/publish.sh >> /var/log/perceel-finder.log 2>&1
```

## Configuration

`config.json`:

```json
{ "home": {...}, "city_centre": {...},
  "wanted_districts": ["Paramaribo", "Wanica"],
  "excluded_places": ["Lelydorp"],
  "max_extra_km_from_centre": 5.0 }
```

`max_extra_km_from_centre` is the "a few km further is fine" rule: a plot is flagged
`closer_to_city` when it is no more than this many km further from the centre than home is.

## Adding a source

Drop a module in `perceel/sources/` exposing `KEY`, `NAME` and
`scrape(http, deep=False) -> list[dict]` (use `core.new_listing(**fields)`), then add it
to `MODULES` in `perceel/sources/__init__.py`. For a simple site, add an entry to
`SITES` in `perceel/sources/generic.py` instead — the heuristic scraper finds repeated
blocks that contain a link plus a price or an m² figure.

## Layout

```
update.py               entry point
config.json             home location, districts, exclusions
perceel/core.py         HTTP client, rate limiting, price/size/phone parsing
perceel/dedup.py        fingerprinting and merging
perceel/geocode.py      Nominatim + cache + distances
perceel/images.py       compressed WebP thumbnails
perceel/store.py        incremental listings.json
perceel/sources/        one module per site
web/index.html          Leaflet / OpenStreetMap viewer
data/listings.json      the data
data/geocache.json      geocoding cache (keep it, it saves a lot of requests)
```

## Manners

One request at a time per host with a delay, an honest user-agent, and Nominatim is
called at its documented 1 request/second. Don't lower the delays.
