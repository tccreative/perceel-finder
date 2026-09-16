"""RE/MAX Suriname - https://www.remax.sr/nl/percelen/percelen.html"""
from ..core import Http, absolute, clean, guess_district, new_listing, parse_price, parse_size_m2

NAME = "RE/MAX Suriname"
KEY = "remax"
BASE = "https://www.remax.sr"
START = f"{BASE}/nl/percelen/percelen.html"
MAX_PAGES = 20


def scrape(http: Http, deep: bool = False):
    out, seen = [], set()
    for page in range(1, MAX_PAGES + 1):
        url = START if page == 1 else f"{START}?lang=nl&category=percelen&page=percelen&paginate={page}"
        soup = http.soup(url)
        if soup is None:
            break
        cards = soup.select("div.listing")
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
            sid = href.rstrip("/").split("/")[-2] if "/lo" in href else href.rstrip("/").split("/")[-1]
            title = clean(c.select_one(".overview_title").get_text()) if c.select_one(".overview_title") else None
            area = clean(c.select_one(".overview_area").get_text()) if c.select_one(".overview_area") else ""
            price_txt = clean(c.select_one(".price").get_text()) if c.select_one(".price") else ""
            size_txt = clean(c.select_one("strong").get_text()) if c.select_one("strong") else ""
            img = None
            ratio = c.select_one(".ratioimage")
            if ratio and ratio.get("style"):
                st = ratio["style"]
                if "url(" in st:
                    img = st.split("url(", 1)[1].split(")", 1)[0].strip("'\" ")
                    if img.startswith("//"):
                        img = "https:" + img
            amount, cur, per_m2 = parse_price(price_txt)
            out.append(new_listing(
                source=KEY, source_id=f"{KEY}:{sid}", url=href, title=title, street=title,
                resort=area or None, district=guess_district(area, title or ""),
                raw_location=area, price=amount, currency=cur, price_per_m2=per_m2 or None,
                size_m2=parse_size_m2(size_txt), images=[img] if img else [], agent=NAME,
            ))
        if fresh == 0:
            break
    return out
