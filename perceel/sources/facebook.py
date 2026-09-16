"""Facebook listings.

Facebook blocks automated scraping, so plots found on Marketplace or in the
Surinamese property groups are captured with a browser and dropped into
data/facebook.json. This module folds that file into the same pipeline, so
Facebook plots are deduplicated against the agent websites like any other
source.

data/facebook.json format (a list):
[
  {
    "url": "https://www.facebook.com/marketplace/item/123...",
    "title": "Perceel Kwatta",
    "street": "Kwattaweg",
    "resort": "Kwatta",
    "district": "Wanica",
    "price": 28000, "currency": "EUR",
    "size_m2": 450,
    "phones": ["+5978123456"],
    "seller": "Naam",
    "images": ["https://..."],
    "description": "...",
    "posted": "2026-09-10"
  }
]
"""
from __future__ import annotations

import json

from ..core import DATA, new_listing, parse_phones, parse_price, parse_size_m2

NAME = "Facebook"
KEY = "facebook"
FILE = DATA / "facebook.json"


def scrape(http=None, deep: bool = False):
    if not FILE.exists():
        return []
    raw = json.loads(FILE.read_text(encoding="utf-8"))
    out = []
    for r in raw:
        url = r.get("url") or ""
        sid = url.rstrip("/").split("/")[-1] or (r.get("title") or "")[:40]
        price, cur = r.get("price"), r.get("currency")
        if price is None and r.get("price_text"):
            price, cur, _ = parse_price(r["price_text"])
        size = r.get("size_m2")
        if size is None and r.get("size_text"):
            size = parse_size_m2(r["size_text"])
        phones = r.get("phones") or parse_phones(r.get("description") or "")
        out.append(new_listing(
            source=KEY, source_id=f"{KEY}:{sid}", url=url or None,
            title=r.get("title"), street=r.get("street") or r.get("title"),
            resort=r.get("resort"), district=r.get("district"),
            raw_location=r.get("location") or r.get("resort"),
            price=price, currency=cur or "SRD" if price else None,
            size_m2=size, images=r.get("images") or [], phones=phones,
            agent=r.get("seller") or "Facebook seller",
            description=r.get("description"),
            lat=r.get("lat"), lon=r.get("lon"),
        ))
    return out
