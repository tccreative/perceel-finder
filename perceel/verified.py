"""Hand-checked coordinates - the top of the location cascade.

Everything else in this project guesses. This file does not: an entry here was
looked at on Google Maps (or another map with better Surinamese coverage),
matched against the advert's own photos and description, and only then written
down. Once an address is in here it is never looked up again, by any run.

Keys are derived from the advert's address, not from the listing id, so the same
street coming back next month under a new advert id inherits the check for free
and never re-enters the queue.
"""
from __future__ import annotations

import json
from datetime import date

from .core import DATA, clean

STORE = DATA / "verified.json"
QUEUE = DATA / "needs_check.json"

# Confidence levels, best first.
#   exact  - the plot itself was identified (corner, house number, landmark)
#   street - the street was identified; the plot is somewhere along it
#   area   - only the neighbourhood could be confirmed; drawn as a circle
#   none   - looked at and genuinely not findable; never queued again
LEVELS = ("exact", "street", "area", "none")

_cache: dict | None = None


def _norm(v) -> str:
    return clean(v or "").lower().strip(" ,.;:-")


def key_for(item: dict) -> str:
    """A stable id for an address, independent of which advert carried it."""
    from .geocode import normalise_street
    street = _norm(normalise_street(item.get("street") or item.get("title")))
    return "|".join([street, _norm(item.get("resort")), _norm(item.get("district"))])


def load() -> dict:
    global _cache
    if _cache is None:
        if STORE.exists():
            _cache = json.loads(STORE.read_text(encoding="utf-8"))
        else:
            _cache = {"schema": 1, "entries": {}}
        _cache.setdefault("entries", {})
    return _cache


def save() -> None:
    if _cache is not None:
        STORE.write_text(json.dumps(_cache, ensure_ascii=False, indent=1), encoding="utf-8")


def apply(item: dict) -> bool:
    """Put a hand-checked position on a listing. True if one was found."""
    e = load()["entries"].get(key_for(item))
    if not e:
        return False
    conf = e.get("confidence", "street")
    src = e.get("method") or "handmatig gecontroleerd"
    if conf in ("exact", "street") and e.get("lat") is not None:
        item.update(lat=e["lat"], lon=e["lon"], geocode_quality="street",
                    geocode_source=src, geocode_match=e.get("label") or "",
                    geocode_checked=e.get("checked"), geocode_confidence=conf)
    elif conf == "area" and e.get("lat") is not None:
        item.update(area_lat=e["lat"], area_lon=e["lon"],
                    area_radius_m=int(e.get("radius_m") or 1200),
                    area_name=e.get("label") or "", geocode_quality="area",
                    geocode_source=src, geocode_match=e.get("label") or "",
                    geocode_checked=e.get("checked"), geocode_confidence=conf)
    else:
        item.update(geocode_quality="none", geocode_source=src,
                    geocode_checked=e.get("checked"), geocode_confidence="none")
    return True


def record(key: str, lat, lon, label: str, confidence: str = "street",
           radius_m: int = 0, method: str = "Google Maps (handmatig)",
           note: str = "") -> None:
    assert confidence in LEVELS, confidence
    load()["entries"][key] = {
        "lat": lat, "lon": lon, "label": label, "confidence": confidence,
        "radius_m": radius_m, "method": method, "note": note,
        "checked": date.today().isoformat(),
    }


def merge(rows: list[dict]) -> int:
    """Take a batch of checks and write them in. Returns how many were new."""
    entries = load()["entries"]
    added = 0
    for r in rows:
        k = r.get("key")
        if not k or k in entries:
            continue
        record(k, r.get("lat"), r.get("lon"), r.get("label") or "",
               r.get("confidence") or "street", int(r.get("radius_m") or 0),
               r.get("method") or "Google Maps (handmatig)", r.get("note") or "")
        added += 1
    save()
    return added


# A word that looks like a Surinamese street in an advert headline. If the
# advert never names one, no amount of looking at a map will place the plot,
# so those go to the bottom of the queue and usually end as "none".
_STREETY = ("straat", "weg", "laan", "pad", "dreef", "kanaal", "project",
            "plein", "steeg", "gracht", "polder", "serie", "km ", "kmr")


def looks_like_street(v: str | None) -> bool:
    t = (v or "").lower()
    return any(w in t for w in _STREETY)


def tier_of(it: dict) -> int:
    """1 = a human look will most likely fix it, 4 = only worth a spot check."""
    q = it.get("geocode_quality")
    named = looks_like_street(it.get("street") or it.get("title"))
    if q == "none":
        return 1
    if it.get("geocode_fuzzy"):
        return 2          # placed by recognising a misspelt name: confirm it
    if q == "area" and named:
        return 2          # the advert names a street we could not match
    if q == "area":
        return 3          # the advert names no street at all
    return 4              # placed automatically; confirm it


def build_queue(items: list[dict]) -> list[dict]:
    """Everything still worth looking at by hand, best candidates first.

    An address that is already checked never comes back, even when a new advert
    for it appears, and even when the check concluded 'not findable'.
    """
    entries = load()["entries"]
    seen, out = set(), []
    for it in items:
        if it.get("geocode_quality") == "street" and it.get("geocode_confidence"):
            continue                                   # already hand-checked
        k = key_for(it)
        if k in entries or k in seen or not k.strip("|"):
            continue
        seen.add(k)
        out.append({
            "key": k,
            "tier": tier_of(it),
            "street": it.get("street") or it.get("title") or "",
            "resort": it.get("resort") or "",
            "district": it.get("district") or "",
            "size_m2": it.get("size_m2"),
            "price": it.get("price"),
            "url": it.get("url"),
            "agent": it.get("agent") or it.get("source"),
            "guess_quality": it.get("geocode_quality"),
            "guess_lat": it.get("lat") if it.get("lat") is not None else it.get("area_lat"),
            "guess_lon": it.get("lon") if it.get("lon") is not None else it.get("area_lon"),
            "guess_match": it.get("geocode_match"),
            "maps_url": "https://www.google.com/maps/search/?api=1&query=" +
                        "+".join(filter(None, [
                            (it.get("street") or it.get("title") or "").replace(" ", "+"),
                            (it.get("resort") or "").replace(" ", "+"),
                            (it.get("district") or "").replace(" ", "+"), "Suriname"])),
        })
    # Fixable first, then the plots we can actually buy: in the search area,
    # priced, and the ones with nothing at all on the map.
    out.sort(key=lambda r: (
        r["tier"],
        0 if r["district"] in ("Paramaribo", "Wanica") else 1,
        0 if r["price"] else 1,
    ))
    return out


def write_queue(items: list[dict]) -> int:
    q = build_queue(items)
    tiers = {t: sum(1 for r in q if r["tier"] == t) for t in (1, 2, 3, 4)}
    QUEUE.write_text(json.dumps({"generated": date.today().isoformat(),
                                 "todo": len(q), "tiers": tiers, "items": q},
                                ensure_ascii=False, indent=1), encoding="utf-8")
    return len(q)
