p='web/index.html'; s=open(p).read()
old = """    const approx = d.geocode_quality && d.geocode_quality !== "street";
    const mk = L.circleMarker([d.lat, d.lon], {"""
new = """    const approx = d.geocode_quality && d.geocode_quality !== "street";
    const r = d.is_new ? 8.5 : 7;
    // A black casing under the white ring: two outlines keep the dot readable
    // on pale streets and on dark green alike.
    dotLayer.addLayer(L.circleMarker([d.lat, d.lon], {
      renderer: canvasRenderer, radius: r + 1.5, weight: 1.4,
      color: "#000", opacity: approx ? .45 : .8, fill: false, interactive: false,
    }));
    const mk = L.circleMarker([d.lat, d.lon], {"""
assert old in s; s=s.replace(old,new,1)
s=s.replace("""      radius: d.is_new ? 8.5 : 7,
      weight: d.is_new ? 3 : 2.2,""","""      radius: r,
      weight: d.is_new ? 3 : 2.2,""",1)
s=s.replace(""".legend i{width:12px;height:12px;border-radius:50%;border:2px solid #fff;display:inline-block;flex:none}""",
""".legend i{width:12px;height:12px;border-radius:50%;border:2px solid #fff;display:inline-block;flex:none;box-shadow:0 0 0 1px #000}""")
open(p,'w').write(s)
print("fix7 applied")
