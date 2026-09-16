import re
p='web/index.html'; s=open(p).read()

# ---- 1. remove the distance slider -------------------------------------
old_html = """      <div class="field">
        <div class="lbl">Afstand tot het centrum van Paramaribo <span class="val" id="kmVal"></span></div>
        <div class="range" id="kmRange" style="height:26px">
          <div class="track"></div><div class="fill"></div>
          <input type="range" id="kmMin" min="0" max="100" value="0" aria-label="Minimale afstand" style="display:none">
          <input type="range" id="kmMax" min="0" max="100" value="100" aria-label="Maximale afstand">
        </div>
      </div>

"""
assert old_html in s, "html"; s = s.replace(old_html, "", 1)

old_js = """  const [, kHi]    = readRange($("#kmMin"), $("#kmMax"), KMS,
        v => Math.round(v) + " km", $("#kmVal"), "#kmRange .fill",
        {linear:true, max: Math.ceil(Math.max(...KMS, 10))});
"""
assert old_js in s, "readRange"; s = s.replace(old_js, "", 1)
s = s.replace("""    if (kHi != null && (d.km_from_centre == null || d.km_from_centre > kHi)) return false;\n""", "", 1)
s = s.replace("""let PRICES = [], SIZES = [], KMS = [];""", """let PRICES = [], SIZES = [];""")
s = s.replace("""  KMS    = DATA.map(d => d.km_from_centre).filter(v => v != null).sort((a,b) => a-b);\n""", "", 1)
s = s.replace("""    $("#kmMax").value = 100;\n""", "", 1)
s = s.replace('''["q","sort","priceMin","priceMax","sizeMin","sizeMax","kmMax"]''',
              '''["q","sort","priceMin","priceMax","sizeMin","sizeMax"]''')

# ---- 2. parcels below the dots, and no longer click targets -------------
s = s.replace("""  canvasRenderer = L.canvas({padding:.5});
  glisLayer = L.layerGroup().addTo(map);""",
"""  map.createPane("glisPane");
  map.getPane("glisPane").style.zIndex = 350;      // under the dots (overlayPane = 400)
  canvasRenderer = L.canvas({padding:.5});
  glisRenderer = L.canvas({padding:.5, pane:"glisPane"});
  glisLayer = L.layerGroup().addTo(map);""")
s = s.replace("""let map, dotLayer, canvasRenderer, glisLayer, byId""",
              """let map, dotLayer, canvasRenderer, glisRenderer, glisLayer, byId""")

pat = re.compile(r"        L\.geoJSON\(f, \{style:.*?\.addTo\(glisLayer\);", re.S)
assert pat.search(s), "draw block"
s = pat.sub("""        L.geoJSON(f, {renderer: glisRenderer, pane: "glisPane", interactive: false,
          style:{color:"#0284c7", weight:1.6, opacity:.95, fillOpacity:.10, fillColor:"#38bdf8"}})
          .addTo(glisLayer);""", s, count=1)

# the parcel popup now comes from clicking the map
helper = '''function parcelPopup(p){
  const dash = "\\u2014";
  return `<div class="pop"><h3>Kadaster (GLIS)</h3>
    <div class="line">Perceel-ID <b>${p.PerceelID || dash}</b></div>
    <div class="line">Perceelnummer ${p.PerceelNR || dash}</div>
    <div class="line">Geregistreerde grootte: <b>${p.PerceelOpp ? Math.round(p.PerceelOpp).toLocaleString("nl-NL") + " " + (p.EenheidOpp || "m2") : dash}</b></div>
    <div class="line">${[p.Ressort, p.Distrikt].filter(Boolean).join(", ")}</div>
    ${p.Uitmetings && p.Uitmetings.trim() ? `<div class="line">Uitmeting: ${p.Uitmetings}</div>` : ""}
    <div class="glis-note">Offici\\u00eble registratie van MI-GLIS. Niet elk perceel staat er al in.</div></div>`;
}

/* With the cadastre on, a click on the map asks GLIS what is registered there.
   The parcels are not click targets themselves, so the plot dots stay clickable. */
async function parcelAt(latlng){
  if ($("#cGlis").ariaPressed !== "true" || map.getZoom() < 15) return;
  const {lat, lng} = latlng;
  const near = new Set();
  for (const d of VIEW) if (d.lat != null && Math.abs(d.lat-lat) < .2 && Math.abs(d.lon-lng) < .2)
    near.add(GLIS_LAYERS[d.district]);
  const layers = [...near].filter(v => v != null);
  const hits = await Promise.all((layers.length ? layers : [6, 9]).map(layer =>
    fetch(`${GLIS}/${layer}/query?geometry=${lng},${lat}&geometryType=esriGeometryPoint`
      + `&inSR=4326&spatialRel=esriSpatialRelIntersects&returnGeometry=false`
      + `&outFields=PerceelID,PerceelNR,PerceelOpp,EenheidOpp,Ressort,Distrikt,Uitmetings`
      + `&resultRecordCount=1&f=json`)
      .then(r => r.ok ? r.json() : null).catch(() => null)));
  for (const h of hits){
    const f = ((h && h.features) || [])[0];
    if (f){ L.popup({maxWidth:300}).setLatLng(latlng).setContent(parcelPopup(f.attributes)).openOn(map); return; }
  }
}

/* ---------------- boot ---------------- */'''
assert "/* ---------------- boot ---------------- */" in s, "boot marker"
s = s.replace("/* ---------------- boot ---------------- */", helper, 1)
s = s.replace("""  map.on("moveend zoomend", loadGlis);""",
              """  map.on("moveend zoomend", loadGlis);
  map.on("click", e => parcelAt(e.latlng));""")
open(p,'w').write(s)
print("fix8 applied")
