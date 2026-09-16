"""VastgoedAanbod Suriname - a central listing platform, read through its
WordPress REST API. The API gives us the publish date and the full advert text,
which is where the size, the asking price and the phone number live.
"""
from __future__ import annotations

import re

from ..core import (Http, clean, find_price, guess_district, new_listing,
                    parse_phones, parse_size_m2)

NAME = "VastgoedAanbod Suriname"
KEY = "vgas"
BASE = "https://vastgoedaanbodsuriname.com"
API = f"{BASE}/wp-json/wp/v2"

_LAND = re.compile(r"perceel|kavel|bouwrijp|grond", re.I)
_SIZE_LABEL = re.compile(
    r"(perceel\s*(?:grootte|oppervlakte)|kavelgrootte|oppervlakte\s*perceel|"
    r"terreingrootte|perceelgrootte)\s*[:\-]?\s*([^\n.;]{0,40})", re.I)


def _terms(http: Http, taxonomy: str) -> dict:
    out = {}
    for page in (1, 2):
        rows = http.json(f"{API}/{taxonomy}?per_page=100&page={page}&_fields=id,name,slug")
        if not isinstance(rows, list) or not rows:
            break
        for r in rows:
            out[r["id"]] = r["name"]
        if len(rows) < 100:
            break
    return out


def scrape(http: Http, deep: bool = False):
    types = http.json(f"{API}/property-type?per_page=50&_fields=id,name,slug")
    if not isinstance(types, list):
        return []
    land_ids = [str(t["id"]) for t in types if _LAND.search(t.get("name", ""))]
    if not land_ids:
        return []
    locations = _terms(http, "location")
    hoods = _terms(http, "neighborhoods")
    purposes = _terms(http, "purpose")

    out = []
    for page in range(1, 8):
        rows = http.json(
            f"{API}/properties?property-type={','.join(land_ids)}"
            f"&per_page=50&page={page}&_embed=wp:featuredmedia")
        if not isinstance(rows, list) or not rows:
            break
        for r in rows:
            title = clean((r.get("title") or {}).get("rendered"))
            body = clean((r.get("content") or {}).get("rendered"))
            amount, cur, per_m2 = find_price(body)

            size = None
            m = _SIZE_LABEL.search(body)
            if m:
                size = parse_size_m2(m.group(2))
            if size is None:
                size = parse_size_m2(body)

            district = None
            for tid in r.get("location") or []:
                district = guess_district(locations.get(tid, "")) or locations.get(tid)
                if district:
                    break
            resort = next((hoods.get(t) for t in (r.get("neighborhoods") or []) if hoods.get(t)), None)
            title_type = next((purposes.get(t) for t in (r.get("purpose") or []) if purposes.get(t)), None)

            img = None
            media = ((r.get("_embedded") or {}).get("wp:featuredmedia") or [{}])[0]
            if isinstance(media, dict):
                img = media.get("source_url")

            out.append(new_listing(
                source=KEY, source_id=f"{KEY}:{r.get('id')}", url=r.get("link"),
                title=title, street=title, resort=resort,
                district=district or guess_district(body, title),
                raw_location=" ".join(filter(None, [resort, district])) or None,
                price=amount, currency=cur, price_per_m2=per_m2 or None, size_m2=size,
                title_type=title_type, images=[img] if img else [],
                phones=parse_phones(body), agent=NAME,
                description=body[:900] or None,
                posted=(r.get("date") or "")[:10] or None,
            ))
        if len(rows) < 50:
            break
    return out
