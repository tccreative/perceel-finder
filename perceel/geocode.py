"""Work out where a plot actually is.

The rule here is that we never invent a position. A dot on the map means the
advert named a street we could find; anything vaguer is recorded as an area and
is not given a point at all.

Order of preference:

0. **Verified** - an address someone actually looked up on a map is stored in
   `data/verified.json` and always wins. Checked once, trusted forever.
1. **Stratenplan** - MI-GLIS publishes the official Surinamese street plan,
   8.247 named streets with their resort. It is authoritative for Suriname and
   knows local roads OpenStreetMap has never heard of.
2. **Nominatim** - OpenStreetMap's geocoder, used as a fallback and only when
   it returns an actual road inside the district the advert names.
3. **Resort** - if only the neighbourhood is known we store the resort's real
   polygon centroid and radius, flagged as an area. The map draws a circle, not
   a pin.
"""
from __future__ import annotations

import json
import re
import time
import unicodedata
from math import pi, sqrt

from . import verified
from .core import CONFIG, DATA, Http, clean, haversine_km

CACHE_PATH = DATA / "geocache.json"
NOMINATIM = "https://nominatim.openstreetmap.org/search"
ARC = "https://services2.arcgis.com/CK9GXvmosMB7QXv8/arcgis/rest/services"
STRPLN = f"{ARC}/Strpln/FeatureServer/0"
RESSORTEN = f"{ARC}/140409Ressorten/FeatureServer/0"
DELAY = float(CONFIG.get("nominatim_delay_seconds", 1.1))
VIEWBOX = "-58.1,6.4,-53.9,1.8"

_cache: dict | None = None
_last_nominatim = 0.0


# ------------------------------------------------------------------ cache
def _load() -> dict:
    global _cache
    if _cache is None:
        _cache = json.loads(CACHE_PATH.read_text(encoding="utf-8")) if CACHE_PATH.exists() else {}
    return _cache


def save() -> None:
    if _cache is not None:
        CACHE_PATH.write_text(json.dumps(_cache, ensure_ascii=False, indent=1), encoding="utf-8")


# ------------------------------------------------------- street name cleanup
_NOISE = re.compile(
    r"\b(te\s+koop|for\s+sale|aangeboden|verkoop|eigendoms?perceel|eigendoms?kavel|"
    r"bouwperceel|bouwkavel|perceel(en)?|kavel(s)?|plot|grondhuur|eigendom|"
    r"investerings?\s*object|project|verkaveling|zijstr(aat)?\.?|hoek(perceel)?|"
    r"nabij|gelegen\s+aan|aan\s+de|ruim(e)?|mooi(e)?|\d+\s*ha)\b", re.I)


def normalise_street(raw: str | None) -> str:
    """Turn an advert headline into something a street index can match."""
    s = clean(raw)
    if not s:
        return ""
    s = unicodedata.normalize("NFKC", s).replace("’", "'").replace("‘", "'")
    s = s.split(",")[0].split("|")[0]          # "Weidestraat, Centrum" -> "Weidestraat"
    s = _NOISE.sub(" ", s)
    s = re.sub(r"[#(].*$", "", s)               # drop "#1203", "(achter ...)"
    s = re.sub(r"\b\d+\s*[a-z]?\b\s*$", "", s)  # trailing house number
    s = re.sub(r"\s{2,}", " ", s)
    return s.strip(" ,.;:-–—")


def _sql(v: str) -> str:
    return v.replace("'", "''")


def _midpoint(geom: dict):
    """Middle of a polyline, so the pin sits on the street rather than its end."""
    coords = geom.get("coordinates") or []
    flat = []
    def walk(c):
        if c and isinstance(c[0], (int, float)):
            flat.append(c)
        else:
            for part in c:
                walk(part)
    walk(coords)
    if not flat:
        return None
    lon, lat = flat[len(flat) // 2][:2]
    return lat, lon


# ------------------------------------------------------------- street plan
def _strpln(http: Http, street: str, ressort: str | None):
    key = f"strpln|{street.lower()}|{(ressort or '').lower()}"
    cache = _load()
    if key in cache:
        return cache[key]
    where = f"UPPER(STREETNAME) LIKE UPPER('%{_sql(street)}%')"
    if ressort:
        where += f" AND UPPER(RESSORTNAM) LIKE UPPER('%{_sql(ressort)}%')"
    res = http.json(f"{STRPLN}/query", params={
        "where": where, "outFields": "STREETNAME,RESSORTNAM", "returnGeometry": "true",
        "outSR": "4326", "f": "geojson", "resultRecordCount": 5})
    out = None
    for f in (res or {}).get("features") or []:
        mid = _midpoint(f.get("geometry") or {})
        if mid:
            p = f.get("properties") or {}
            out = {"lat": mid[0], "lon": mid[1],
                   "match": ", ".join(filter(None, [p.get("STREETNAME"), p.get("RESSORTNAM")]))}
            break
    cache[key] = out
    return out


# ---------------------------------------------------------------- resorts
def _ressort(http: Http, ressort: str | None, district: str | None):
    if not ressort and not district:
        return None
    key = f"res|{(ressort or '').lower()}|{(district or '').lower()}"
    cache = _load()
    if key in cache:
        return cache[key]
    clauses = []
    if ressort:
        clauses.append(f"UPPER(RES_NM) LIKE UPPER('%{_sql(ressort)}%')")
    if district:
        clauses.append(f"UPPER(DISTR_NM) LIKE UPPER('%{_sql(district)}%')")
    res = http.json(f"{RESSORTEN}/query", params={
        "where": " AND ".join(clauses), "outFields": "RES_NM,DISTR_NM,Shape_Area",
        "returnGeometry": "true", "outSR": "4326", "f": "geojson", "resultRecordCount": 1})
    out = None
    for f in (res or {}).get("features") or []:
        pts = []
        def walk(c):
            if c and isinstance(c[0], (int, float)):
                pts.append(c)
            else:
                for part in c:
                    walk(part)
        walk((f.get("geometry") or {}).get("coordinates") or [])
        if not pts:
            continue
        lat = sum(p[1] for p in pts) / len(pts)
        lon = sum(p[0] for p in pts) / len(pts)
        area = (f.get("properties") or {}).get("Shape_Area") or 0
        radius = int(sqrt(abs(area) / pi)) if area else 1500
        p = f.get("properties") or {}
        out = {"lat": round(lat, 6), "lon": round(lon, 6),
               "radius_m": max(400, min(radius, 6000)),
               "name": ", ".join(filter(None, [p.get("RES_NM"), p.get("DISTR_NM")]))}
        break
    cache[key] = out
    return out


# -------------------------------------------------------------- nominatim
def _nominatim(http: Http, query: str):
    global _last_nominatim
    cache = _load()
    if query in cache:
        return cache[query]
    gap = time.time() - _last_nominatim
    if gap < DELAY:
        time.sleep(DELAY - gap)
    _last_nominatim = time.time()
    res = http.json(NOMINATIM, params={
        "q": query, "format": "jsonv2", "limit": 1, "countrycodes": "sr",
        "viewbox": VIEWBOX, "bounded": 1})
    val = None
    if res:
        r = res[0]
        val = {"lat": float(r["lat"]), "lon": float(r["lon"]),
               "display_name": r.get("display_name"), "type": r.get("addresstype")}
    cache[query] = val
    return val


def _road_in_district(hit: dict, district: str | None) -> bool:
    """Only trust Nominatim when it found a road in the right district."""
    if not hit or hit.get("type") not in ("road", "street", "residential"):
        return False
    if district and district.lower() not in (hit.get("display_name") or "").lower():
        return False
    return True


# ------------------------------------------------------------------ public
def geocode(http: Http, item: dict) -> None:
    if item.get("lat") and item.get("lon"):
        return
    # A hand-checked address beats every automatic guess and is never redone.
    if verified.apply(item):
        return
    street = normalise_street(item.get("street") or item.get("title"))
    resort = clean(item.get("resort") or "") or None
    district = clean(item.get("district") or "") or None

    if len(street) >= 4:
        for res in (resort, None):
            hit = _strpln(http, street, res)
            if hit:
                item.update(lat=hit["lat"], lon=hit["lon"],
                            geocode_quality="street", geocode_source="Stratenplan (MI-GLIS)",
                            geocode_match=hit["match"])
                return

        for q in filter(None, [
                f"{street}, {resort}, {district}, Suriname" if resort and district else None,
                f"{street}, {district}, Suriname" if district else None,
                f"{street}, Suriname"]):
            hit = _nominatim(http, q)
            if _road_in_district(hit, district):
                item.update(lat=hit["lat"], lon=hit["lon"],
                            geocode_quality="street", geocode_source="OpenStreetMap",
                            geocode_match=hit.get("display_name"))
                return

    # Nothing precise enough. Record the neighbourhood as an area - the map
    # draws a circle over it, and no dot pretends to know the address.
    area = _ressort(http, resort, district) or _ressort(http, None, district)
    if area:
        item.update(area_lat=area["lat"], area_lon=area["lon"],
                    area_radius_m=area["radius_m"], area_name=area["name"],
                    geocode_quality="area", geocode_source="Ressortgrenzen (MI-GLIS)",
                    geocode_match=area["name"])
    else:
        item["geocode_quality"] = "none"


def annotate_distance(item: dict) -> None:
    centre = CONFIG["city_centre"]
    home = CONFIG.get("home") or {}
    lat = item.get("lat") if item.get("lat") is not None else item.get("area_lat")
    lon = item.get("lon") if item.get("lon") is not None else item.get("area_lon")
    item["km_from_centre"] = haversine_km(centre["lat"], centre["lon"], lat, lon)
    if home.get("lat"):
        item["km_from_home"] = haversine_km(home["lat"], home["lon"], lat, lon)
