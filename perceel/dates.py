"""When was this advert put up?

Most of the Surinamese agent sites run WordPress, and WordPress hands out the
publish date of every post through its REST API. Pulling 100 records per
request gives us a URL -> date map for a whole site in a few calls, which beats
opening every listing page.
"""
from __future__ import annotations

from .core import Http, clean

# site key -> (wp root, rest_base of the plot post type)
WP_SOURCES = {
    "surgoed": ("https://www.surgoed.com", "perceel"),
    "terzol": ("https://terzol.com/vastgoed", "perceel"),
    "oso": ("https://osonangadjari.com", "property"),
    "karima": ("https://karimainvest.com", "property"),
    "survast": ("https://survast.sr", "property"),
}
MAX_PAGES = 12


def _normalise(url: str) -> str:
    u = clean(url).lower().split("?")[0].rstrip("/")
    return u.replace("https://", "").replace("http://", "").replace("www.", "")


def fetch_dates(http: Http, base: str, rest_base: str, log=print) -> dict:
    """-> {normalised link: 'YYYY-MM-DD'}"""
    out = {}
    for page in range(1, MAX_PAGES + 1):
        url = (f"{base}/wp-json/wp/v2/{rest_base}"
               f"?per_page=100&page={page}&_fields=link,date,modified&orderby=date&order=desc")
        rows = http.json(url)
        if not isinstance(rows, list) or not rows:
            break
        for r in rows:
            link, date = r.get("link"), r.get("date")
            if link and date:
                out[_normalise(link)] = date[:10]
        if len(rows) < 100:
            break
    log(f"     {len(out)} dates from {base}")
    return out


def enrich(http: Http, items: list, log=print) -> int:
    """Stamp `posted` on every listing we can find a publish date for."""
    needed = {i["source"] for i in items if i.get("source") in WP_SOURCES}
    found = 0
    for key in sorted(needed):
        base, rest_base = WP_SOURCES[key]
        try:
            table = fetch_dates(http, base, rest_base, log=log)
        except Exception as exc:  # noqa: BLE001
            log(f"     !! dates for {key} failed: {exc}")
            continue
        for it in items:
            if it.get("source") != key or it.get("posted"):
                continue
            d = table.get(_normalise(it.get("url") or ""))
            if d:
                it["posted"] = d
                found += 1
    return found
