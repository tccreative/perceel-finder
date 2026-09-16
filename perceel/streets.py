"""A local copy of the official Surinamese street plan.

Querying the ArcGIS service one street at a time can only ever find an exact
spelling, and adverts are full of near-misses: Drambrandesgracht for
Drambrandersgracht, Garniezoenspad for Garnizoenspad, Commissaris Whythingweg
for Commissaris Weytinghweg. With the whole index on disk we can match those
the way a person would - by recognising the name - instead of throwing the
listing away.

Downloaded once, then reused. Re-run `python3 -m perceel.streets` to refresh.
"""
from __future__ import annotations

import difflib
import json
import re
import unicodedata

from .core import DATA, Http

ARC = "https://services2.arcgis.com/CK9GXvmosMB7QXv8/arcgis/rest/services"
STRPLN = f"{ARC}/Strpln/FeatureServer/0"
RESSORTEN = f"{ARC}/140409Ressorten/FeatureServer/0"
STREETS = DATA / "streets.json"
PAGE = 1000

_index: dict | None = None


def _midpoint(geom: dict):
    flat = []

    def walk(c):
        if c and isinstance(c[0], (int, float)):
            flat.append(c)
        else:
            for part in c:
                walk(part)

    walk((geom or {}).get("coordinates") or [])
    if not flat:
        return None
    lon, lat = flat[len(flat) // 2][:2]
    return round(lat, 6), round(lon, 6)


def key(name: str) -> str:
    """Fold a street name down to what makes it recognisable.

    Accents, punctuation, spacing and the usual Dutch doubled letters all vary
    between an advert and the register; none of them change which street is
    meant.
    """
    s = unicodedata.normalize("NFKD", (name or "").lower())
    s = "".join(c for c in s if not unicodedata.combining(c))
    s = re.sub(r"[^a-z0-9]+", "", s)
    s = re.sub(r"(.)\1+", r"\1", s)          # straat/straaat, penninck/penninck
    s = s.replace("ij", "y").replace("ck", "k").replace("th", "t")
    s = s.replace("ph", "f").replace("z", "s").replace("ie", "i")
    return s


def download(http: Http) -> dict:
    """Pull the whole street plan and the resort -> district table."""
    streets, offset = [], 0
    while True:
        res = http.json(f"{STRPLN}/query", params={
            "where": "1=1", "outFields": "STREETNAME,RESSORTNAM",
            "returnGeometry": "true", "outSR": "4326", "f": "geojson",
            "resultRecordCount": PAGE, "resultOffset": offset})
        feats = (res or {}).get("features") or []
        for f in feats:
            mid = _midpoint(f.get("geometry") or {})
            if not mid:
                continue
            p = f.get("properties") or {}
            name = (p.get("STREETNAME") or "").strip()
            if not name:
                continue
            streets.append({"name": name, "ressort": (p.get("RESSORTNAM") or "").strip(),
                            "lat": mid[0], "lon": mid[1]})
        if len(feats) < PAGE:
            break
        offset += PAGE
        if offset > 40000:
            break

    res = http.json(f"{RESSORTEN}/query", params={
        "where": "1=1", "outFields": "RES_NM,DISTR_NM", "returnGeometry": "false",
        "f": "json", "resultRecordCount": 200})
    ressorts = {}
    for f in (res or {}).get("features") or []:
        a = f.get("attributes") or {}
        if a.get("RES_NM"):
            ressorts[a["RES_NM"].strip().lower()] = (a.get("DISTR_NM") or "").strip()

    data = {"streets": streets, "ressort_district": ressorts}
    STREETS.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    return data


def load() -> dict:
    """The index, keyed by folded name, with a district on every entry."""
    global _index
    if _index is None:
        if not STREETS.exists():
            _index = {"by_key": {}, "keys": [], "ressort_district": {}}
            return _index
        raw = json.loads(STREETS.read_text(encoding="utf-8"))
        r2d = raw.get("ressort_district", {})
        by_key: dict[str, list] = {}
        for s in raw.get("streets", []):
            s["district"] = r2d.get((s.get("ressort") or "").lower(), "")
            by_key.setdefault(key(s["name"]), []).append(s)
        _index = {"by_key": by_key, "keys": list(by_key), "ressort_district": r2d}
    return _index


def _pick(rows: list[dict], district: str | None, resort: str | None):
    """Same name in several resorts: prefer the one the advert names."""
    if resort:
        for r in rows:
            if resort.lower() in (r.get("ressort") or "").lower():
                return r
    if district:
        in_d = [r for r in rows if (r.get("district") or "").lower() == district.lower()]
        if in_d:
            return in_d[0]
        if any(r.get("district") for r in rows):
            return None          # it exists, but not where the advert says
    return rows[0] if rows else None


def find(street: str, district: str | None = None, resort: str | None = None,
         cutoff: float = 0.88):
    """Look a street up, tolerating the way adverts spell things.

    Returns (row, how) where how is "exact" or "fuzzy", or None. A fuzzy match
    inside the wrong district is rejected rather than returned - a close
    spelling in another part of the country is not the same street.
    """
    idx = load()
    if not idx["keys"] or not street:
        return None
    k = key(street)
    if not k:
        return None
    if k in idx["by_key"]:
        row = _pick(idx["by_key"][k], district, resort)
        return (row, "exact") if row else None

    pool = idx["keys"]
    if district:
        pool = [kk for kk in idx["keys"]
                if any((r.get("district") or "").lower() == district.lower()
                       for r in idx["by_key"][kk])] or idx["keys"]
    # Adverts misspell the middle of a name, not the start. Without this,
    # "Balitoestraat" happily becomes "Alitostraat" - a different street.
    pool = [kk for kk in pool if kk[:1] == k[:1]]
    near = difflib.get_close_matches(k, pool, n=1, cutoff=cutoff)
    if not near:
        return None
    row = _pick(idx["by_key"][near[0]], district, resort)
    return (row, "fuzzy") if row else None


if __name__ == "__main__":
    d = download(Http())
    print(f"{len(d['streets'])} streets, {len(d['ressort_district'])} resorts "
          f"-> {STREETS}")
