p='web/index.html'; s=open(p).read()
s=s.replace('.pop a{color:var(--accent)}','.pop a{color:var(--accent)}\n.pop a.ad{color:var(--accent-ink)}')
old = """    const b = map.getBounds();
    const env = [b.getWest(), b.getSouth(), b.getEast(), b.getNorth()].join(",");
    const layers = [...new Set(VIEW.map(d => GLIS_LAYERS[d.district]).filter(v => v != null))];
    for (const layer of (layers.length ? layers : [6, 9])){
      const url = `${GLIS}/${layer}/query?geometry=${env}&geometryType=esriGeometryEnvelope`
        + `&inSR=4326&outSR=4326&spatialRel=esriSpatialRelIntersects`
        + `&outFields=PerceelID,PerceelNR,PerceelOpp,EenheidOpp,Ressort,Distrikt,Uitmetings`
        + `&returnGeometry=true&resultRecordCount=600&f=geojson`;
      const res = await fetch(url).then(r => r.ok ? r.json() : null).catch(() => null);
      for (const f of (res && res.features) || []){"""
new = """    const b = map.getBounds();
    const env = [b.getWest(), b.getSouth(), b.getEast(), b.getNorth()].join(",");
    // Only ask the district layers that actually cover what is on screen -
    // querying all ten takes seconds and returns nothing for nine of them.
    const here = new Set();
    for (const d of VIEW) if (d.lat != null && b.contains([d.lat, d.lon])) here.add(GLIS_LAYERS[d.district]);
    const layers = [...here].filter(v => v != null);
    const results = await Promise.all((layers.length ? layers : [6, 9]).map(layer =>
      fetch(`${GLIS}/${layer}/query?geometry=${env}&geometryType=esriGeometryEnvelope`
        + `&inSR=4326&outSR=4326&spatialRel=esriSpatialRelIntersects`
        + `&outFields=PerceelID,PerceelNR,PerceelOpp,EenheidOpp,Ressort,Distrikt,Uitmetings`
        + `&returnGeometry=true&resultRecordCount=800&f=geojson`)
        .then(r => r.ok ? r.json() : null).catch(() => null)));
    for (const res of results){
      for (const f of (res && res.features) || []){"""
assert old in s; s=s.replace(old,new,1)
s=s.replace('L.geoJSON(f, {style:{color:"#38bdf8", weight:1.2, fillOpacity:.06, fillColor:"#38bdf8"}})',
            'L.geoJSON(f, {style:{color:"#0284c7", weight:1.6, opacity:.95, fillOpacity:.10, fillColor:"#38bdf8"}})',1)
s=s.replace("""    if (b.id === "cGlis"){ glisLayer.clearLayers(); glisSeen.clear(); loadGlis(); return; }""",
"""    if (b.id === "cGlis"){ glisLayer.clearLayers(); glisSeen.clear(); loadGlis(); return; }""")
s=s.replace("""  if (map.getZoom() < 15){
    glisLayer.clearLayers(); glisSeen.clear();
    return;
  }""","""  const chip = $("#cGlis");
  if (map.getZoom() < 15){
    glisLayer.clearLayers(); glisSeen.clear();
    chip.textContent = "Kadaster \\u2014 zoom verder in";
    return;
  }
  chip.textContent = "Kadaster tonen";""")
open(p,'w').write(s)
print("ok")
