"""Surgoed Makelaardij - all percelen on one page (99+ listing-cards)."""
from ..core import Http, absolute, clean, guess_district, new_listing, parse_price, parse_size_m2

NAME = "Surgoed Makelaardij NV"
KEY = "surgoed"
BASE = "https://www.surgoed.com"
START = f"{BASE}/vastgoedaanbod/kopen/percelen-te-koop-in-suriname/"


def scrape(http: Http, deep: bool = False):
    soup = http.soup(START)
    if soup is None:
        return []
    out = []
    for c in soup.select("a.listing-card, .listing-card"):
        href = absolute(BASE, c.get("href") or (c.select_one("a[href]") or {}).get("href"))
        if not href:
            continue
        sid = href.rstrip("/").split("/")[-1]
        title = clean(c.select_one(".addr").get_text()) if c.select_one(".addr") else None
        loc = clean(c.select_one(".loc").get_text()) if c.select_one(".loc") else ""
        price_txt = clean(c.select_one(".price").get_text()) if c.select_one(".price") else ""
        cur = "EUR"
        if c.select_one(".price .cur"):
            cls = " ".join(c.select_one(".price .cur").get("class") or [])
            if "usd" in cls:
                cur = "USD"
            elif "srd" in cls:
                cur = "SRD"
        specs = clean(c.select_one(".specs").get_text(" ")) if c.select_one(".specs") else ""
        img_el = c.select_one("img")
        img = None
        if img_el:
            img = img_el.get("data-lazy-src") or img_el.get("data-src") or img_el.get("src")
            if img and img.startswith("data:"):
                ns = c.select_one("noscript img")
                img = ns.get("src") if ns else None
        amount, parsed_cur, per_m2 = parse_price(price_txt)
        ttype = None
        for t in ("Grondhuur", "Eigendom", "Erfpacht", "Huurgrond", "Plantagegrond"):
            if t.lower() in specs.lower():
                ttype = t
        resort, district = None, None
        if "," in loc:
            parts = [clean(p) for p in loc.split(",")]
            resort, district = parts[0], parts[-1]
        else:
            district = guess_district(loc)
        out.append(new_listing(
            source=KEY, source_id=f"{KEY}:{sid}", url=href, title=title, street=title,
            resort=resort, district=district or guess_district(loc), raw_location=loc,
            price=amount, currency=parsed_cur or cur, price_per_m2=per_m2 or None,
            size_m2=parse_size_m2(specs.replace("m 2", "m2").replace("m2", " m2")),
            title_type=ttype, images=[img] if img else [], agent=NAME,
        ))
    return out
