import sys, re, requests
from bs4 import BeautifulSoup
UA={"User-Agent":"perceel-finder/1.0 (personal use)","Accept-Language":"nl,en;q=0.8"}
url=sys.argv[1]
r=requests.get(url,headers=UA,timeout=30)
print("STATUS",r.status_code,len(r.text))
s=BeautifulSoup(r.text,"lxml")
for t in s(["script","style","noscript"]): t.decompose()
# print candidate listing containers
cands={}
for el in s.find_all(True):
    cls=" ".join(el.get("class") or [])
    if not cls: continue
    if re.search(r"(propert|listing|object|kavel|perceel|card|item|result|aanbod)",cls,re.I):
        cands[cls]=cands.get(cls,0)+1
for k,v in sorted(cands.items(),key=lambda x:-x[1])[:25]:
    print(f"{v:4d}  {k}")
print("---- sample anchors ----")
seen=set()
for a in s.find_all("a",href=True)[:400]:
    h=a["href"]
    if re.search(r"(propert|perceel|kavel|listing|object|/\d{4,})",h) and h not in seen:
        seen.add(h); print(h[:120],"|",(a.get_text(" ",strip=True) or "")[:70])
    if len(seen)>25: break
