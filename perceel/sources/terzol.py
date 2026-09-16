"""Terzol Vastgoed NV - Toolset Views grid of plots."""
import re
from ..core import Http, absolute, clean, guess_district, new_listing, parse_price, parse_size_m2

NAME = "Terzol Vastgoed NV"
KEY = "terzol"
BASE = "https://terzol.com"
START = f"{BASE}/vastgoed/en/real-estate-in-suriname/offer/buy/plots/"
MAX_PAGES = 15


def scrape(http: Http, deep: bool = False):
    out, seen = [], set()
    for page in range(1, MAX_PAGES + 1):
        url = START if page == 1 else f"{START}page/{page}/"
        soup = http.soup(url)
        if soup is None:
            break
        cards = soup.select(".wpv-block-loop-item")
        if not cards:
            break
        fresh = 0
        for c in cards:
            a = c.select_one("a[href]")
            href = absolute(BASE, a["href"]) if a else None
            if not href or href in seen:
                continue
            seen.add(href)
            fresh += 1
            loc_el = c.select_one("p.tb-heading")
            loc = clean(loc_el.get_text()) if loc_el else ""
            price_el = c.select_one(".specs-views-prijs")
            amount, cur, per_m2 = parse_price(clean(price_el.get_text()) if price_el else "")
            size = None
            for li in c.select(".specs-views li"):
                t = clean(li.get_text(" "))
                if re.search(r"plot size|perceel", t, re.I) or "m²" in t:
                    size = parse_size_m2(t)
                    if size:
                        break
            img = None
            for d in c.select("[style*='url(']"):
                st = d.get("style", "")
                if "url(" in st:
                    img = st.split("url(", 1)[1].split(")", 1)[0].strip("'\" ")
                    break
            parts = [clean(p) for p in loc.split(",") if clean(p)]
            street = parts[0] if parts else href.rstrip("/").split("/")[-1].replace("-", " ").title()
            resort = parts[1] if len(parts) > 2 else None
            out.append(new_listing(
                source=KEY, source_id=f"{KEY}:{href.rstrip('/').split('/')[-1]}", url=href,
                title=loc or street, street=street, resort=resort,
                district=guess_district(loc), raw_location=loc,
                price=amount, currency=cur, price_per_m2=per_m2 or None, size_m2=size,
                images=[img] if img else [], agent=NAME,
            ))
        if fresh == 0:
            break
    return out
