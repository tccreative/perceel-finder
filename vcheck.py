import json
d=json.load(open('data/listings.json'))
v=[x for x in d['listings'] if x['source']=='vgas']
print('vgas',len(v),'with posted',sum(1 for x in v if x.get('posted')),'with size',sum(1 for x in v if x.get('size_m2')),'with price',sum(1 for x in v if x.get('price')),'with img',sum(1 for x in v if x.get('images')))
for x in v[:6]:
    print(f"  {x.get('posted')} {str(x.get('price')):>8} {str(x.get('size_m2')):>8} m2  {x.get('district')} | {(x.get('title') or '')[:50]}")
