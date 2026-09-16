import json
from collections import Counter
d=json.load(open('data/listings.json'))
tg=[x for x in d['listings'] if x.get('in_target_area')]
print('target',len(tg),'geo',sum(1 for x in tg if x.get('lat')),'price',sum(1 for x in tg if x.get('price_eur')),'size',sum(1 for x in tg if x.get('size_m2')),'posted',sum(1 for x in tg if x.get('posted')),'thumb',sum(1 for x in tg if x.get('thumbs')))
print('src',Counter(x['source'] for x in tg).most_common())
bad=[x for x in tg if x.get('lat') and not (5.6 <= x['lat'] <= 6.1 and -55.7 <= x['lon'] <= -54.9)]
print('outside Pbo/Wanica box:',len(bad))
for x in bad[:6]:
    print(f"  {x['lat']:8.3f} {x['lon']:9.3f}  {x['source']:8} {x.get('district')} | {(x.get('street') or '')[:35]}")
p=[x for x in tg if x.get('posted')]
p.sort(key=lambda x:x['posted'],reverse=True)
print('--- newest posted ---')
for x in p[:8]:
    print(f"  {x['posted']}  {str(x.get('price_eur')):>8}  {str(x.get('size_m2')):>8} m2  {(x.get('street') or '')[:30]:30} {x['source']}")
