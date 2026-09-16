"""Heuristic scraper for the smaller Surinamese sites.

Finds repeated blocks that contain a link plus something that looks like a
price and/or a plot size. Works well enough on the long tail of agent sites
without hand-written selectors for each one.
"""
from __future__ import annotations

import re
from collections import Counter

from ..core import (Http, absolute, clean, guess_district, new_listing,
                    parse_phones, parse_price, parse_size_m2)

SIZE_HINT = re.compile(r"\d[\d.,]*\s*(m\s*[²2]|m2|ha\b)", re.I)
PRICE_HINT = re.compile(r"(€|\$|srd|usd|eur)\s*\d|(\d[\d.,]{3,})\s*(euro|usd|srd)", re.I)
LAND_HINT = re.compile(r"perceel|percelen|kavel|bouwgrond|grond|plot|land", re.I)


def _cards(soup):
    """Group elements by their class signature; keep the biggest plausible set."""
    buckets: dict[str, list] = {}
    for el in soup.find_all(["article", "div", "li", "a"]):
        cls = " ".join(sorted(el.get("class") or []))
        if not cls:
            continue
        txt = clean(el.get_text(" "))
        if len(txt) < 15 or len(txt) > 1200:
            continue
        if not el.find("a", href=True):
            continue
        if not (SIZE_HINT.search(txt) or PRICE_HINT.search(txt)):
            continue
        buckets.setdefault(cls, []).append(el)
    if not buckets:
        return []
    best = None
    for cls, els in buckets.items():
        if len(els) < 2:
            continue
        # prefer many, small, sibling-ish blocks
        avg = sum(len(clean(e.get_text(" "))) for e in els) / len(els)
        score = len(els) * (1.0 if avg < 400 else 0.4)
        if best is None or score > best[0]:
            best = (score, els)
    if best is None:
        return []
    els = best[1]
    # drop elements that merely contain other chosen elements
    chosen = set(id(e) for e in els)
    return [e for e in els if not any(id(d) in chosen for d in e.find_all(True))]


def scrape_site(http: Http, key: str, name: str, base: str, start_urls: list[str],
                page_pattern: str | None = None, max_pages: int = 12,
                deep: bool = False):
    out, seen = [], set()
    urls = list(start_urls)
    if page_pattern:
        urls += [page_pattern.format(page=p) for p in range(2, max_pages + 1)]
    empty_streak = 0
    for url in urls:
        soup = http.soup(url)
        if soup is None:
            empty_streak += 1
            if empty_streak >= 2:
                break
            continue
        page_phones = parse_phones(clean(soup.get_text(" ")))[:2]
        cards = _cards(soup)
        fresh = 0
        for c in cards:
            a = c if (c.name == "a" and c.get("href")) else c.find("a", href=True)
            href = absolute(base, a.get("href")) if a else None
            if not href or href in seen:
                continue
            text = clean(c.get_text(" "))
            if not (SIZE_HINT.search(text) or LAND_HINT.search(text)):
                continue
            seen.add(href)
            fresh += 1
            h = c.find(["h1", "h2", "h3", "h4", "h5"])
            title = clean(h.get_text()) if h else clean(a.get_text()) or text[:70]
            img_el = c.find("img")
            img = None
            if img_el:
                img = (img_el.get("data-lazy-src") or img_el.get("data-src")
                       or img_el.get("data-original") or img_el.get("src"))
                if img and img.startswith("data:"):
                    img = None
                if img:
                    img = absolute(base, img)
            amount, cur, per_m2 = parse_price(text)
            out.append(new_listing(
                source=key, source_id=f"{key}:{href.rstrip('/').split('/')[-1][:80]}",
                url=href, title=title[:120], street=title[:120],
                district=guess_district(text), raw_location=text[:160],
                price=amount, currency=cur, price_per_m2=per_m2 or None,
                size_m2=parse_size_m2(text), images=[img] if img else [],
                phones=page_phones, agent=name, description=text[:600],
            ))
        if fresh == 0 and page_pattern and url != start_urls[0]:
            empty_streak += 1
            if empty_streak >= 2:
                break
        else:
            empty_streak = 0
    return out


SITES = [
    dict(key="survast", name="Survast", base="https://survast.sr",
         start_urls=["https://survast.sr/percelen-te-koop-wanica-en-omgeving/",
                     "https://survast.sr/percelen-te-koop-paramaribo-en-omgeving/",
                     "https://survast.sr/percelen/"],
         page_pattern=None),
    dict(key="shopsmart", name="ShopSmart Vastgoed", base="https://shopsmartvastgoed.com",
         start_urls=["https://shopsmartvastgoed.com/property-type/perceel/",
                     "https://shopsmartvastgoed.com/properties/"],
         page_pattern="https://shopsmartvastgoed.com/property-type/perceel/page/{page}/",
         max_pages=8),
    dict(key="karima", name="Karima Invest N.V.", base="https://karimainvest.com",
         start_urls=["https://karimainvest.com/percelen/", "https://karimainvest.com/"],
         page_pattern="https://karimainvest.com/percelen/page/{page}/", max_pages=8),
    dict(key="marktplaats_sr", name="Marktplaats.sr", base="https://www.marktplaats.sr",
         start_urls=["https://www.marktplaats.sr/l/onroerend-goed-percelen/"],
         page_pattern="https://www.marktplaats.sr/l/onroerend-goed-percelen/p/{page}/",
         max_pages=10),
    dict(key="osonangadjari_w", name="Oso Nanga Djari (Wanica)", base="https://osonangadjari.com",
         start_urls=["https://osonangadjari.com/location/wanica/de-nieuwe-grond/"],
         page_pattern=None),
]
