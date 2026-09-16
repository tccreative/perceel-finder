"""Nominatim geocoding with an on-disk cache and Suriname-aware query building."""
from __future__ import annotations

import json
import re
import time
from pathlib import Path

from .core import CONFIG, DATA, Http, clean, haversine_km

CACHE_PATH = DATA / "geocache.json"
NOMINATIM = "https://nominatim.openstreetmap.org/search"
DELAY = float(CONFIG.get("nominatim_delay_seconds", 1.1))

# Suriname bounding box (lon_min, lat_max, lon_max, lat_min) for viewbox bias
VIEWBOX = "-58.1,6.4,-53.9,1.8"

_cache: dict | None = None
_last = 0.0


def _load() -> dict:
    global _cache
    if _cache is None:
        if CACHE_PATH.exists():
            _cache = json.loads(CACHE_PATH.read_text(encoding="utf-8"))
        else:
            _cache = {}
    return _cache


def save() -> None:
    if _cache is not None:
        CACHE_PATH.write_text(json.dumps(_cache, ensure_ascii=False, indent=1), encoding="utf-8")


_CLEAN = re.compile(r"\b(te koop|for sale|perceel|percelen|kavel|bouwkavel|plot|"
                    r"nabij|nearby|project|verkaveling)\b", re.I)


def _street(item: dict) -> str | None:
    raw = item.get("street") or item.get("title") or ""
    raw = _CLEAN.sub(" ", clean(raw))
    raw = re.sub(r"[#\d]+\s*$", "", raw)
    raw = re.sub(r"\bpc\.?\s*\d+.*$", "", raw, flags=re.I)
    raw = re.sub(r"\s{2,}", " ", raw).strip(" ,.-")
    return raw or None


def queries(item: dict) -> list[str]:
    st = _street(item)
    resort = clean(item.get("resort") or "")
    district = clean(item.get("district") or "")
    out = []
    if st and resort and district:
        out.append(f"{st}, {resort}, {district}, Suriname")
    if st and district:
        out.append(f"{st}, {district}, Suriname")
    if st:
        out.append(f"{st}, Suriname")
    if resort and district:
        out.append(f"{resort}, {district}, Suriname")
    elif resort:
        out.append(f"{resort}, Suriname")
    if district:
        out.append(f"{district}, Suriname")
    seen, uniq = set(), []
    for q in out:
        if q.lower() not in seen:
            seen.add(q.lower())
            uniq.append(q)
    return uniq


def _lookup(http: Http, query: str):
    global _last
    cache = _load()
    if query in cache:
        return cache[query]
    gap = time.time() - _last
    if gap < DELAY:
        time.sleep(DELAY - gap)
    _last = time.time()
    res = http.json(NOMINATIM, params={
        "q": query, "format": "jsonv2", "limit": 1, "countrycodes": "sr",
        "viewbox": VIEWBOX, "bounded": 1,
    })
    val = None
    if res:
        r = res[0]
        val = {"lat": float(r["lat"]), "lon": float(r["lon"]),
               "display_name": r.get("display_name"), "type": r.get("addresstype")}
    cache[query] = val
    return val


def _plausible(item: dict, hit: dict) -> bool:
    """Reject a match in the wrong district.

    Street names repeat across Suriname: a "Kleineweg" in Wanica happily
    matches one in Brokopondo, which drops the pin 80 km into the interior.
    If we know the district the advert names, the match has to agree.
    """
    district = (item.get("district") or "").strip().lower()
    if not district:
        return True
    return district in (hit.get("display_name") or "").lower()


def geocode(http: Http, item: dict) -> None:
    if item.get("lat") and item.get("lon"):
        return
    for level, q in enumerate(queries(item)):
        hit = _lookup(http, q)
        if hit and not _plausible(item, hit):
            continue
        if hit:
            item["lat"], item["lon"] = hit["lat"], hit["lon"]
            item["geocode_quality"] = ("street" if level == 0 or "road" in (hit.get("type") or "")
                                       else "area" if level < 3 else "district")
            item["geocode_match"] = hit.get("display_name")
            return
    item["geocode_quality"] = "none"


def annotate_distance(item: dict) -> None:
    home = CONFIG["home"]
    centre = CONFIG["city_centre"]
    item["km_from_home"] = haversine_km(home["lat"], home["lon"], item.get("lat"), item.get("lon"))
    item["km_from_centre"] = haversine_km(centre["lat"], centre["lon"], item.get("lat"), item.get("lon"))
    home_to_centre = haversine_km(home["lat"], home["lon"], centre["lat"], centre["lon"])
    item["home_km_from_centre"] = home_to_centre
    if item["km_from_centre"] is None:
        item["closer_to_city"] = None
    else:
        item["closer_to_city"] = item["km_from_centre"] <= home_to_centre + float(
            CONFIG.get("max_extra_km_from_centre", 5.0))


def jitter_if_approx(item: dict) -> None:
    """Spread out plots that only resolved to a resort/district centroid.

    Without this, 130 listings sit on one pin and the map is unreadable. The
    offset is deterministic (same listing -> same spot) and clearly flagged in
    the UI as an approximate location.
    """
    q = item.get("geocode_quality")
    if q in (None, "street") or item.get("lat") is None:
        return
    import hashlib
    from math import cos, pi
    seed = hashlib.sha1((item.get("source_id") or item.get("url") or "").encode()).digest()
    radius_m = 900 if q == "area" else 2200
    ang = (seed[0] / 255.0) * 2 * pi
    dist = (0.35 + 0.65 * (seed[1] / 255.0)) * radius_m
    dlat = (dist * cos(ang)) / 111320.0
    dlon = (dist * (1 - cos(ang) ** 2) ** 0.5 * (1 if seed[2] % 2 else -1)) / (
        111320.0 * max(0.2, cos(item["lat"] * pi / 180)))
    item["lat"] = round(item["lat"] + dlat, 6)
    item["lon"] = round(item["lon"] + dlon, 6)
    item["position_is_approximate"] = True
