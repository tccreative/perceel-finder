import re
p='web/index.html'; s=open(p).read()
old="  if (pts.length) map.fitBounds(L.latLngBounds(pts).pad(.12), {maxZoom:14, animate:false});\n}"
new=("  fitToView(pts);\n}\n\nlet didFirstFit = false;\nfunction fitToView(pts){\n"
"  if (!pts.length) return;\n"
"  // Leaflet caches the container size at init; if the layout wasn't settled\n"
"  // yet that size is 0 and fitBounds silently lands on the whole world.\n"
"  requestAnimationFrame(() => {\n"
"    map.invalidateSize({animate:false});\n"
"    map.fitBounds(L.latLngBounds(pts).pad(.12), {maxZoom: didFirstFit ? 15 : 13, animate:false});\n"
"    didFirstFit = true;\n  });\n}")
assert old in s; s=s.replace(old,new)
old2="  applyFilters();\n}\nboot()"
new2=('  window.addEventListener("resize", () => map.invalidateSize({animate:false}));\n'
'  applyFilters();\n  setTimeout(() => { map.invalidateSize({animate:false}); applyFilters(); }, 350);\n}\nboot()')
assert old2 in s; s=s.replace(old2,new2)
open(p,'w').write(s)

p='perceel/core.py'; s=open(p).read()
add=('_BAD_PREFIX = re.compile(r"^https?:(?=https?://)", re.I)\n\n\n'
'def clean_image_urls(urls) -> list:\n'
'    """Drop junk and repair the double-scheme URLs some sites hand out."""\n'
'    out = []\n'
'    for u in urls or []:\n'
'        if not u or not isinstance(u, str):\n            continue\n'
'        u = _BAD_PREFIX.sub("", u.strip())\n'
'        if u.startswith("//"):\n            u = "https:" + u\n'
'        if not u.startswith("http"):\n            continue\n'
'        if u not in out:\n            out.append(u)\n'
'    return out[:10]\n\n\n'
'def new_listing(**kw) -> dict:')
assert 'def new_listing(**kw) -> dict:' in s
s=s.replace('def new_listing(**kw) -> dict:', add, 1)
s=s.replace('    base.update(kw)\n    return base',
            '    base.update(kw)\n    base["images"] = clean_image_urls(base.get("images"))\n    return base')
open(p,'w').write(s)
print('patched vps')
