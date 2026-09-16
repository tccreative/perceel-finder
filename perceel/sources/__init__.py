"""Registry of all scrapers."""
from . import generic, oso, remax, remy, surgoed, surigrond, terzol

MODULES = [remy, surgoed, remax, oso, terzol, surigrond]


def run_all(http, only=None, deep=True, log=print):
    results = []
    for mod in MODULES:
        if only and mod.KEY not in only:
            continue
        log(f"  -> {mod.NAME} ...")
        try:
            items = mod.scrape(http, deep=deep)
        except Exception as exc:  # noqa: BLE001
            log(f"     !! {mod.NAME} failed: {exc}")
            items = []
        log(f"     {len(items)} listings")
        results.extend(items)
    for site in generic.SITES:
        if only and site["key"] not in only:
            continue
        log(f"  -> {site['name']} (generic) ...")
        try:
            items = generic.scrape_site(http, **site)
        except Exception as exc:  # noqa: BLE001
            log(f"     !! {site['name']} failed: {exc}")
            items = []
        log(f"     {len(items)} listings")
        results.extend(items)
    return results
