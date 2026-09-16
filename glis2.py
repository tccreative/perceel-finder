import json, re
from perceel.core import Http
h = Http(delay=0.4)
BASE = "https://services2.arcgis.com/CK9GXvmosMB7QXv8/arcgis/rest/services/Percelen_Online/FeatureServer"

print("--- bbox query (small area in Paramaribo Noord), geometry in 4326 ---")
r = h.json(f"{BASE}/6/query", params={
    "geometry": "-55.180,5.835,-55.170,5.845", "geometryType": "esriGeometryEnvelope",
    "inSR": "4326", "outSR": "4326", "spatialRel": "esriSpatialRelIntersects",
    "outFields": "PerceelID,PerceelNR,PerceelOpp,Ressort", "returnGeometry": "true",
    "f": "geojson", "resultRecordCount": 3})
if r:
    print("  type:", r.get("type"), "features:", len(r.get("features") or []))
    f0 = (r.get("features") or [{}])[0]
    print("  props:", json.dumps(f0.get("properties"), ensure_ascii=False)[:180])
    g = f0.get("geometry") or {}
    print("  geom:", g.get("type"), str(g.get("coordinates"))[:120])
else:
    print("  no geojson support")

print("--- attribute query by PerceelID ---")
r = h.json(f"{BASE}/6/query", params={
    "where": "PerceelID='CP-2965-4367'", "outFields": "*",
    "returnGeometry": "false", "f": "json"})
print("  hits:", len((r or {}).get("features") or []))

print("--- how many of our listings quote a PerceelID? ---")
d = json.load(open("data/listings.json"))
pat = re.compile(r"\b([A-Z]{1,3}-\d{3,5}-\d{3,5})\b")
hits = 0
for it in d["listings"]:
    blob = " ".join(filter(None, [it.get("description"), it.get("title"), it.get("raw_location")]))
    m = pat.search(blob or "")
    if m:
        hits += 1
        if hits <= 5:
            print("   ", m.group(1), "|", (it.get("street") or "")[:40], "|", it["source"])
print("  total listings quoting a PerceelID:", hits, "of", len(d["listings"]))
