import sys, requests
from bs4 import BeautifulSoup
UA={"User-Agent":"perceel-finder/1.0 (personal use)","Accept-Language":"nl,en;q=0.8"}
url,sel,n=sys.argv[1],sys.argv[2],int(sys.argv[3]) if len(sys.argv)>3 else 1
r=requests.get(url,headers=UA,timeout=30); r.raise_for_status()
s=BeautifulSoup(r.text,"lxml")
els=s.select(sel)
print("MATCHES",len(els))
for e in els[:n]:
    print("="*70); print(e.prettify()[:4000])
