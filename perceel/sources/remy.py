"""Remy Vastgoed - https://www.remyvastgoed.com/percelen (card list, /page/N)."""
from ..core import Http, absolute, clean, guess_district, new_listing, parse_price, parse_size_m2

NAME = "Remy Vastgoed"
KEY = "remy"
BASE = "https://www.remyvastgoed.com"
START = f"{BASE}/percelen"
MAX_PAGES = 40


def scrape(http: Http, deep: bool = False):
    out, page = [], 1
    while page <= MAX_PAGES:
        url = START if page == 1 else f"{START}/page/{page}"
        soup = http.soup(url)
        if soup is None:
            break
        cards = soup.select("div.object")
        if not cards:
            break
        for c in cards:
            a = c.select_one("a[href]")
            href = absolute(BASE, a["href"]) if a else None
            if not href:
                continue
            sid = clean(c.select_one(".objectnummer").get_text()) if c.select_one(".objectnummer") else href.rstrip("/").split("/")[-1]
            sid = sid.lstrip("#")
            title = clean(c.select_one(".title").get_text()) if c.select_one(".title") else None
            loc = clean(c.select_one(".locatie").get_text()) if c.select_one(".locatie") else ""
            price_txt = clean(c.select_one(".prijs").get_text()) if c.select_one(".prijs") else ""
            size_txt = clean(c.select_one(".perceel").get_text()) if c.select_one(".perceel") else ""
            ttype = clean(c.select_one(".titel").get_text()) if c.select_one(".titel") else None
            img = c.select_one("img.object_img")
            amount, cur, per_m2 = parse_price(price_txt)
            district, resort = None, None
            if " - " in loc:
                district, resort = [clean(x) for x in loc.split(" - ", 1)]
            else:
                district = guess_district(loc)
            out.append(new_listing(
                source=KEY, source_id=f"{KEY}:{sid}", url=href, title=title,
                street=title, resort=resort, district=district or guess_district(loc),
                raw_location=loc, price=amount, currency=cur,
                price_per_m2=per_m2 or None, size_m2=parse_size_m2(size_txt),
                title_type=ttype, images=[img["src"]] if img and img.get("src") else [],
                agent=NAME,
            ))
        nxt = soup.select_one(f'a[href*="/percelen/page/{page+1}"]')
        if not nxt:
            break
        page += 1
    return out
