"""SuriGrond - single long page with all plots."""
import re
from ..core import Http, absolute, clean, guess_district, new_listing, parse_phones, parse_price, parse_size_m2

NAME = "SuriGrond"
KEY = "surigrond"
BASE = "https://surigrond.com"
START = BASE + "/"


def scrape(http: Http, deep: bool = False):
    soup = http.soup(START)
    if soup is None:
        return []
    page_phones = parse_phones(clean(soup.get_text(" ")))
    out, seen = [], set()
    cards = soup.select("article, .elementor-post, .property, .grid-item, .wp-block-column")
    for c in cards:
        a = c.select_one("a[href]")
        href = absolute(BASE, a["href"]) if a else None
        text = clean(c.get_text(" "))
        if not href or href in seen or len(text) < 25:
            continue
        if not re.search(r"m\s*[²2]|perceel|kavel|grond", text, re.I):
            continue
        seen.add(href)
        img_el = c.select_one("img")
        img = (img_el.get("data-lazy-src") or img_el.get("data-src") or img_el.get("src")) if img_el else None
        if img and img.startswith("data:"):
            img = None
        h = c.select_one("h1, h2, h3, h4")
        title = clean(h.get_text()) if h else text[:70]
        amount, cur, per_m2 = parse_price(text)
        out.append(new_listing(
            source=KEY, source_id=f"{KEY}:{href.rstrip('/').split('/')[-1]}", url=href,
            title=title, street=title, district=guess_district(text), raw_location=text[:160],
            price=amount, currency=cur, price_per_m2=per_m2 or None, size_m2=parse_size_m2(text),
            images=[img] if img else [], phones=page_phones, agent=NAME,
            description=text[:600],
        ))
    return out
