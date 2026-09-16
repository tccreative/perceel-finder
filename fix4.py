p='perceel/core.py'; s=open(p).read()
old='''    m = _PRICE_LABEL.search(t)
    if m:
        amount, cur, per_m2 = parse_price(m.group(1))
        if amount and amount >= 1000:
            return amount, cur, per_m2
    best = None
    for m in _PRICE_NEAR.finditer(t):
        amount, cur, per_m2 = parse_price(m.group(0))
        if amount and amount >= 1000 and (best is None or amount > best[0]):
            best = (amount, cur, per_m2)
    return best or (None, None, False)'''
new='''    m = _PRICE_LABEL.search(t)
    if m:
        amount, cur, per_m2 = parse_price(m.group(1))
        if _sane_price(amount, m.group(1)):
            return amount, cur, per_m2
    best = None
    for m in _PRICE_NEAR.finditer(t):
        amount, cur, per_m2 = parse_price(m.group(0))
        if _sane_price(amount, m.group(0)) and (best is None or amount > best[0]):
            best = (amount, cur, per_m2)
    return best or (None, None, False)


def _sane_price(amount, blob: str) -> bool:
    """Guard against phone numbers and plot IDs masquerading as prices.

    Surinamese phone numbers are seven digits written without separators
    ("8550564"), which reads as a perfectly good price if you squint. A real
    asking price either carries a thousands separator or stays under a million.
    """
    if not amount or amount < 1000 or amount > 3_000_000:
        return False
    if amount >= 1_000_000 and not any(c in blob for c in ".,"):
        return False
    return True'''
assert old in s
open(p,'w').write(s.replace(old,new,1))
print('fix4 applied')
