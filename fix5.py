p='web/index.html'; s=open(p).read()

s=s.replace('let DATA = [], VIEW = [],','let BASELINE_RUN = false;\nlet DATA = [], VIEW = [],')

s=s.replace('''  const c = raw.counts||{};''','''  // A first run (or a reset store) marks every plot "new", which is noise
  // rather than news. Only trust the flag once there is a baseline to compare to.
  const c0 = raw.counts || {};
  BASELINE_RUN = !c0.active || (c0.new_this_run || 0) >= c0.active * 0.9;
  if (BASELINE_RUN) DATA.forEach(d => { d.is_new = false; });

  const c = raw.counts||{};''')

s=s.replace('''    `<span><b>${c.new_this_run||0}</b> nieuw</span>`,''','''    BASELINE_RUN ? "" : `<span><b>${c.new_this_run||0}</b> nieuw</span>`,''')

# hide the "Nieuw" filter chip when there is nothing new to filter on
s=s.replace('''  ["q","district","source","sort","maxPrice","minSize","maxKm"].forEach(id =>''','''  if (BASELINE_RUN) $("#cNew").style.display = "none";

  ["q","district","source","sort","maxPrice","minSize","maxKm"].forEach(id =>''')
open(p,'w').write(s)
print('fix5 applied')
