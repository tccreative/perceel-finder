import json
from perceel.core import Http
h = Http(delay=0.4)
BASE = "https://services2.arcgis.com/CK9GXvmosMB7QXv8/arcgis/rest/services/Percelen_Online/FeatureServer"

# which layer is which district?
meta = h.json(f"{BASE}?f=json")
for lyr in (meta or {}).get("layers", []):
    print(lyr["id"], lyr["name"])

print("--- point query: Hofstraat, Paramaribo centrum ---")
for lat, lon, label in [(5.8266, -55.1668, "Hofstraat area"),
                        (5.8611709, -55.2971196, "Shantaweg Kwatta"),
                        (5.8495, -55.2847, "Garnizoenspad")]:
    for layer in (6, 9):
        r = h.json(f"{BASE}/{layer}/query", params={
            "geometry": f"{lon},{lat}", "geometryType": "esriGeometryPoint",
            "inSR": "4326", "spatialRel": "esriSpatialRelIntersects",
            "outFields": "PerceelID,PerceelNR,PerceelOpp,EenheidOpp,Straat1,Straat2,Ressort,Distrikt,Uitmetings,PerceelOms",
            "returnGeometry": "false", "f": "json", "resultRecordCount": 2})
        feats = (r or {}).get("features") or []
        if feats:
            print(f"  [{label}] layer {layer}: {json.dumps(feats[0]['attributes'], ensure_ascii=False)[:260]}")
