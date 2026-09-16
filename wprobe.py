import json
from perceel.core import Http
h = Http(delay=0.8)
SITES = {
 "oso": "https://osonangadjari.com",
 "surgoed": "https://www.surgoed.com",
 "terzol": "https://terzol.com/vastgoed",
 "karima": "https://karimainvest.com",
 "survast": "https://survast.sr",
}
for key, base in SITES.items():
    t = h.json(f"{base}/wp-json/wp/v2/types")
    if not t:
        print(key, "no wp-json"); continue
    cands = [n for n in t if n not in ("post","page","attachment","nav_menu_item","wp_block",
        "wp_template","wp_template_part","wp_navigation","wp_global_styles","wp_font_family",
        "wp_font_face","patterns_ai_data","elementor_library","e-landing-page","wp_font_face")]
    print(f"--- {key}: {cands}")
    for n in cands:
        rb = t[n].get("rest_base") or n
        items = h.json(f"{base}/wp-json/wp/v2/{rb}?per_page=2&_fields=link,date,slug")
        if isinstance(items, list) and items:
            print(f"    {n} rest_base={rb} ok  e.g. date={items[0].get('date')} link={(items[0].get('link') or '')[:70]}")
