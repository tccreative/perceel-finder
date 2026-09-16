import json, re
from collections import Counter
from perceel.core import Http, clean
h = Http(delay=0.35)
BASE = "https://services2.arcgis.com/CK9GXvmosMB7QXv8/arcgis/rest/services/Percelen_Online/FeatureServer"
LAYER = {"Paramaribo":6, "Wanica":9, "Para":5, "Commewijne":1, "Saramacca":7}

def esc(v): return v.replace("'", "''")

def street_hit(street, district, resort=None):
    lyr = LAYER.get(district)
    if lyr is None: return None
    where = f"UPPER(Straat1) LIKE UPPER('%{esc(street)}%')"
    if resort:
        where += f" AND UPPER(Ressort) LIKE UPPER('%{esc(resort)}%')"
    r = h.json(f"{BASE}/{lyr}/query", params={
        "where": where, "outFields": "PerceelID,Straat1,Ressort,Distrikt",
        "returnGeometry": "true", "outSR": "4326", "f": "geojson",
        "resultRecordCount": 60})
    feats = (r or {}).get("features") or []
    return feats

d = json.load(open("data/listings.json"))
L = d["listings"]
print("geocode quality across all", len(L), ":", Counter(x.get("geocode_quality") for x in L).most_common())

# how often can GLIS find the street the advert names?
tried = ok = 0
for it in L:
    if it.get("geocode_quality") == "street": continue
    st = clean(it.get("street") or "")
    st = re.sub(r"\b(pc|perceel|kavel|hoek|te koop)\b.*", "", st, flags=re.I).strip(" ,.-")
    if len(st) < 5 or not it.get("district"): continue
    tried += 1
    if tried > 25: break
    feats = street_hit(st, it["district"], it.get("resort"))
    if feats:
        ok += 1
        c = feats[0]["geometry"]["coordinates"]
        while isinstance(c[0], list): c = c[0]
        print(f"  OK  {st[:32]:32} {it['district']:11} -> {len(feats):3} parcels, first at {c[1]:.5f},{c[0]:.5f}")
    else:
        print(f"  --  {st[:32]:32} {it['district']:11} -> no parcel with that street name")
print(f"GLIS street match: {ok}/{tried-1 if tried>25 else tried}")
