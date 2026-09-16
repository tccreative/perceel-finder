"""Oso Nanga Djari - WordPress 'properta' theme, /property-type/percelen/page/N/"""
from ..core import Http, absolute, clean, guess_district, new_listing, parse_price, parse_size_m2

NAME = "Oso Nanga Djari"
KEY = "oso"
BASE = "https://osonangadjari.com"
START = f"{BASE}/property-type/percelen/"
MAX_PAGES = 25


def scrape(http: Http, deep: bool = True):
    out, seen = [], set()
    for page in range(1, MAX_PAGES + 1):
        url = START if page == 1 else f"{START}page/{page}/"
        soup = http.soup(url)
        if soup is None:
            break
        rows = soup.select(".property-row-content, article")
        cards = [r for r in rows if r.select_one(".property-row-title")]
        if not cards:
            break
        fresh = 0
        for c in cards:
            t = c.select_one(".property-row-title a[href]") or c.select_one(".property-row-title")
            href = absolute(BASE, t.get("href")) if t and t.name == "a" else None
            if not href:
                link = c.select_one("a[href*='/properties/']")
                href = absolute(BASE, link["href"]) if link else None
            if not href or href in seen:
                continue
            seen.add(href)
            fresh += 1
            title = clean(t.get_text()) if t else None
            loc = clean(c.select_one(".property-row-location").get_text()) if c.select_one(".property-row-location") else ""
            price_txt = clean(c.select_one(".property-row-meta-item-price").get_text()) if c.select_one(".property-row-meta-item-price") else ""
            img_el = c.select_one("img")
            img = None
            if img_el:
                img = img_el.get("data-src") or img_el.get("src")
            amount, cur, per_m2 = parse_price(price_txt)
            parts = [clean(p) for p in loc.split(",") if clean(p)]
            resort = parts[0] if parts else None
            district = guess_district(loc) or (parts[-1] if len(parts) > 1 else None)
            out.append(new_listing(
                source=KEY, source_id=f"{KEY}:{href.rstrip('/').split('/')[-1]}", url=href,
                title=title, street=title, resort=resort, district=district, raw_location=loc,
                price=amount, currency=cur, price_per_m2=per_m2 or None,
                images=[img] if img else [], agent=NAME,
            ))
        if fresh == 0:
            break
    if deep:
        for item in out:
            _detail(http, item)
    return out


def _detail(http: Http, item: dict) -> None:
    soup = http.soup(item["url"])
    if soup is None:
        return
    body = soup.select_one(".property-content, .entry-content, article") or soup
    text = clean(body.get_text(" "))
    if not item.get("size_m2"):
        for label in ("perceeloppervlakte", "perceel opp", "kaveloppervlakte", "oppervlakte", "plot size", "terrein"):
            idx = text.lower().find(label)
            if idx >= 0:
                item["size_m2"] = parse_size_m2(text[idx:idx + 90])
                if item["size_m2"]:
                    break
        if not item.get("size_m2"):
            item["size_m2"] = parse_size_m2(text)
    item["description"] = text[:900] or None
    imgs = []
    for im in soup.select(".property-gallery img, .gallery img, .entry-content img, figure img"):
        src = im.get("data-src") or im.get("src")
        if src and not src.startswith("data:") and src not in imgs:
            imgs.append(src)
    if imgs:
        item["images"] = imgs[:8]
