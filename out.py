import json
d=json.load(open('data/listings.json'))
L=[x for x in d['listings'] if x.get('lat') is not None]
print('geocoded',len(L))
bad=[x for x in L if not (1.5 <= x['lat'] <= 6.5 and -58.5 <= x['lon'] <= -53.5)]
print('outside Suriname bbox:',len(bad))
for x in bad[:12]:
    print(f"  {x['lat']:>10.4f} {x['lon']:>11.4f}  {x['source']:8} q={x.get('geocode_quality')} {(x.get('street') or '')[:40]} | {(x.get('geocode_match') or '')[:60]}")
lats=[x['lat'] for x in L]; lons=[x['lon'] for x in L]
print('lat',min(lats),max(lats),'lon',min(lons),max(lons))
