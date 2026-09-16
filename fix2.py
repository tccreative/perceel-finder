p='perceel/geocode.py'; s=open(p).read()
old = '''def geocode(http: Http, item: dict) -> None:
    if item.get("lat") and item.get("lon"):
        return
    for level, q in enumerate(queries(item)):
        hit = _lookup(http, q)
        if hit:'''
new = '''def _plausible(item: dict, hit: dict) -> bool:
    """Reject a match in the wrong district.

    Street names repeat across Suriname: a "Kleineweg" in Wanica happily
    matches one in Brokopondo, which drops the pin 80 km into the interior.
    If we know the district the advert names, the match has to agree.
    """
    district = (item.get("district") or "").strip().lower()
    if not district:
        return True
    return district in (hit.get("display_name") or "").lower()


def geocode(http: Http, item: dict) -> None:
    if item.get("lat") and item.get("lon"):
        return
    for level, q in enumerate(queries(item)):
        hit = _lookup(http, q)
        if hit and not _plausible(item, hit):
            continue
        if hit:'''
assert old in s
s = s.replace(old, new, 1)
open(p,'w').write(s)

p='web/index.html'; s=open(p).read()
old='  #side{position:absolute;inset:0;z-index:900;background:var(--panel)}'
new='  #side{position:absolute;inset:0;z-index:1200;background:var(--panel)}\n  body:not(.mapview) .leaflet-control-container{display:none}'
assert old in s
s=s.replace(old,new,1)
s=s.replace('#toggle{position:absolute;z-index:1000;','#toggle{position:absolute;z-index:1300;')
open(p,'w').write(s)
print('ok')
