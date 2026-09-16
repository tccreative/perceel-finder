import json, re
from collections import Counter
from perceel.core import Http, clean
h = Http(delay=0.35)
STR = "https://services2.arcgis.com/CK9GXvmosMB7QXv8/arcgis/rest/services/Strpln/FeatureServer/0"

meta = h.json(f"{STR}?f=json") or {}
print("layer:", meta.get("name"), "| geom:", meta.get("geometryType"))
print("fields:", [f["name"] for f in meta.get("fields", [])][:20])
cnt = h.json(f"{STR}/query", params={"where":"1=1","returnCountOnly":"true","f":"json"})
print("street features:", (cnt or {}).get("count"))

def find(street, district=None):
    st = street.replace("'", "''")
    where = f"UPPER(STREETNAME) LIKE UPPER('%{st}%')"
    r = h.json(f"{STR}/query", params={
        "where": where, "outFields": "*", "returnGeometry": "true",
        "outSR": "4326", "f": "geojson", "resultRecordCount": 5})
    return (r or {}).get("features") or []

d = json.load(open("data/listings.json"))
tried = ok = 0
for it in d["listings"]:
    if it.get("geocode_quality") == "street": continue
    st = clean(it.get("street") or "")
    st = re.sub(r"[#\d].*$", "", st).strip(" ,.-")
    st = re.sub(r"\b(pc|perceel|kavel|hoek|te koop|zijstr\.?|verkoop)\b", "", st, flags=re.I).strip(" ,.-")
    if len(st) < 5: continue
    tried += 1
    if tried > 22: break
    f = find(st)
    if f:
        ok += 1
        props = f[0]["properties"]
        c = f[0]["geometry"]["coordinates"]
        while isinstance(c[0], list): c = c[0]
        print(f"  OK  {st[:30]:30} -> {str(props.get('STREETNAME'))[:26]:26} {c[1]:.5f},{c[0]:.5f}")
    else:
        print(f"  --  {st[:30]:30} -> not in the street plan")
print(f"Stratenplan match: {ok}/{min(tried,22)}")
