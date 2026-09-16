# perceel-finder

Finds land (percelen) for sale in Suriname — focused on **Paramaribo** and **Wanica**,
ranked by how close each plot is to Paramaribo centrum compared to where you live now
(Project Schuilplaats, Shantaweg, Kwatta). Everything lands on one OpenStreetMap map.

## What it does

1. **Scrapes** the Surinamese estate-agent sites (one polite request at a time, honest user-agent).
2. **Removes duplicates** — inside a site and across sites. The same plot advertised by
   two agents becomes one pin with both links.
3. **Places** each plot as honestly as it can (see below) and computes distance to the
   city and to home.
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

## The map

`web/index.html` is a single self-contained page (Leaflet + OpenStreetMap, no build step).

- Every plot in the dataset is shown; nothing is filtered away by default.
- Dot colour is the asking price, so the map reads as a price heat map. Each dot
  carries a white ring inside a black casing so it stays legible on pale streets
  and dark green alike. Faded dots are plots whose advert gave no exact address.
- Filters: free text, district multi-select (each pick becomes a tag you can
  remove), dual-handle sliders for price, plot size and distance to Paramaribo
  centrum, plus toggles for photos, exact locations and the cadastral overlay.
  The sliders map their 0-100 travel onto the actual spread of the data, so the
  handles always cover something instead of bunching up at the left.
- Each plot shows where it came from. A plot advertised by two agents is one pin
  with a link to each of them.

## Cadastral overlay (MI-GLIS)

The "Kadaster tonen" toggle draws the official parcel boundaries from MI-GLIS
Percelen Online, straight from their public ArcGIS feature service:

```
https://services2.arcgis.com/CK9GXvmosMB7QXv8/arcgis/rest/services/Percelen_Online/FeatureServer/<layer>
```

Layer per district: 0 Brokopondo, 1 Commewijne, 2 Coronie, 3 Marowijne,
4 Nickerie, 5 Para, 6 Paramaribo, 7 Saramacca, 8 Sipaliwini, 9 Wanica. The
service answers `f=geojson` in WGS84, so Leaflet can draw it directly — no key,
no proxy. Clicking a parcel shows its Perceel-ID, parcel number, registered area,
ressort and the surveyor's measurement reference.

The overlay loads from zoom 15 and only queries the district layers that cover
what is on screen. It is deliberately kept *next to* the listings rather than
merged into them: a listing's pin comes from geocoding a street name, so it
cannot be claimed to be a particular registered parcel. Look at the two together
and judge for yourself. MI-GLIS also notes that not every parcel is in the
geometric file yet.

## Where the dots come from

Most adverts give a street, not a coordinate, so every position has to be worked
out. The rule is that we never invent one. A dot on the map means an actual
street was matched; anything vaguer is drawn as a shaded circle over the
neighbourhood, and anything vaguer still stays in the list with no position at
all.

The cascade, in order:

0. **`data/verified.json`** — an address a human actually looked up on a map.
   Always wins, never re-checked. See *The check procedure* below.
1. **Stratenplan (MI-GLIS)** — the official Surinamese street plan, 8.247 named
   streets with their ressort, served from the same ArcGIS host as the cadastre.
   It is authoritative for Suriname and knows local roads OpenStreetMap has
   never heard of. The pin is put at the middle of the street's polyline, so it
   sits on the road rather than at one end.
2. **Nominatim (OpenStreetMap)** — the fallback, and only trusted when it
   returns something OSM itself classifies as a road *and* the district in the
   result matches the district in the advert. A hit on a shop, a school or a
   road in the wrong district is thrown away.
3. **Ressortgrenzen (MI-GLIS)** — if only the neighbourhood is known, the
   resort's real polygon centroid and a radius derived from its area are stored
   as `area_lat` / `area_lon` / `area_radius_m`. The map draws a dashed circle
   with the plots inside it, not a pin.
4. **Nothing** — the listing keeps its place in the list and says so.

### The check procedure

Automatic geocoding is a first pass, not the answer. Every run therefore writes
`data/needs_check.json`: every address that did not end up on a street with a
confirmed position, best candidates first (in Paramaribo or Wanica, priced, no
guess at all). Each entry carries the advert URL and a ready-made Google Maps
search link.

Working the queue:

```bash
./.venv/bin/python verify.py list 25 > batch.json   # next 25 to look at
# open each maps_url, cross-check against the advert's own photos and text,
# then fill in lat/lon/label/confidence in batch.json
./.venv/bin/python verify.py add < batch.json       # write them in
./.venv/bin/python update.py                        # re-run; they are now placed
```

`confidence` is one of:

| value | meaning | on the map |
|---|---|---|
| `exact` | the plot itself was identified — corner, house number, landmark | dot |
| `street` | the street was identified; the plot is somewhere along it | dot |
| `area` | only the neighbourhood could be confirmed | circle of `radius_m` |
| `none` | looked at properly and genuinely not findable | list only |

Three things make this cheap to keep up:

* Keys are derived from the **address**, not the advert id. The same street
  re-advertised next month by a different agent inherits the check and never
  re-enters the queue.
* `none` is a real answer. An address that was checked and could not be found
  is recorded as such and never queued again.
* The queue therefore only ever contains **addresses nobody has looked at yet**,
  so each update is smaller than the last.

Google Maps is used as a *reference to read*, by hand — its geocoding API
results may not be stored or displayed on OpenStreetMap tiles, but nothing stops
a person looking at the map and writing down where a street is.

Each listing carries `geocode_quality` (`street`, `area` or `none`),
`geocode_source` and `geocode_match`, so the map can be honest about what it
knows and the "Exacte locatie" filter can hide the rest. An earlier version
scattered street-less plots randomly around a district centroid; that
manufactured precision that did not exist and has been removed.

This is what Funda, Rightmove and Zillow do with plots whose address is not
public: a circle, not a pin. Google's geocoder is better in Suriname, but its
terms do not allow the results to be displayed on OpenStreetMap tiles, and it is
paid per request.

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
verify.py               work through the hand-check queue
config.json             home location, districts, exclusions
perceel/core.py         HTTP client, rate limiting, price/size/phone parsing
perceel/dedup.py        fingerprinting and merging
perceel/geocode.py      Stratenplan / Nominatim / ressort + cache + distances
perceel/images.py       compressed WebP thumbnails
perceel/verified.py     hand-checked coordinates + the check queue
perceel/store.py        incremental listings.json
perceel/sources/        one module per site
web/index.html          Leaflet / OpenStreetMap viewer
data/listings.json      the data
data/geocache.json      geocoding cache (keep it, it saves a lot of requests)
data/verified.json      hand-checked addresses - the most valuable file here
data/needs_check.json   what still needs a human look (rebuilt every run)
```

## Manners

One request at a time per host with a delay, an honest user-agent, and Nominatim is
called at its documented 1 request/second. Don't lower the delays.
