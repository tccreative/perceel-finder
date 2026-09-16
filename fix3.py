p='perceel/core.py'; s=open(p).read()
s=s.replace('import json\nimport os\nimport re','import html\nimport json\nimport os\nimport re')
s=s.replace('''    text = unicodedata.normalize("NFKC", str(text))
    text = re.sub(r"<[^>]+>", " ", text)''','''    text = unicodedata.normalize("NFKC", str(text))
    text = re.sub(r"<[^>]+>", " ", text)
    text = html.unescape(text)''')

add = '''

_PRICE_NEAR = re.compile(
    r"(?:(€|eur|usd|srd|us\\$|sr\\$|\\$)\\s*([\\d][\\d.,\\s]{2,})"
    r"|([\\d][\\d.,\\s]{2,})\\s*(€|eur|usd|srd|euro|dollar))", re.I)
_PRICE_LABEL = re.compile(
    r"(?:vraag|koop|verkoop)?prijs\\w*\\s*[:\\-]?\\s*([^\\n;|]{0,45})", re.I)


def find_price(text: str | None):
    """Pull the asking price out of a free-text advert.

    `parse_price` takes the first number it sees, which in a long advert is
    usually the plot size or a house number. Here we look for a figure that
    actually sits next to a currency symbol or a "vraagprijs" label, and
    ignore anything under 1.000 - no plot in Suriname costs 18 euro.
    """
    t = clean(text)
    if not t:
        return None, None, False
    m = _PRICE_LABEL.search(t)
    if m:
        amount, cur, per_m2 = parse_price(m.group(1))
        if amount and amount >= 1000:
            return amount, cur, per_m2
    best = None
    for m in _PRICE_NEAR.finditer(t):
        amount, cur, per_m2 = parse_price(m.group(0))
        if amount and amount >= 1000 and (best is None or amount > best[0]):
            best = (amount, cur, per_m2)
    return best or (None, None, False)
'''
assert 'def new_listing' in s
s = s.replace('\n\ndef new_listing', add + '\n\ndef new_listing', 1)
open(p,'w').write(s)

p='perceel/sources/vgas.py'; s=open(p).read()
s=s.replace('from ..core import (Http, clean, guess_district, new_listing, parse_phones,\n                    parse_price, parse_size_m2)',
            'from ..core import (Http, clean, find_price, guess_district, new_listing,\n                    parse_phones, parse_size_m2)')
s=s.replace('amount, cur, per_m2 = parse_price(body)','amount, cur, per_m2 = find_price(body)')
open(p,'w').write(s)

p='perceel/sources/generic.py'; s=open(p).read()
s=s.replace('from ..core import (Http, absolute, clean, guess_district, new_listing,\n                    parse_phones, parse_price, parse_size_m2)',
            'from ..core import (Http, absolute, clean, find_price, guess_district,\n                    new_listing, parse_phones, parse_size_m2)')
s=s.replace('amount, cur, per_m2 = parse_price(text)','amount, cur, per_m2 = find_price(text)')
open(p,'w').write(s)

p='perceel/sources/surigrond.py'; s=open(p).read()
s=s.replace('parse_phones, parse_price, parse_size_m2','parse_phones, find_price, parse_size_m2')
s=s.replace('amount, cur, per_m2 = parse_price(text)','amount, cur, per_m2 = find_price(text)')
open(p,'w').write(s)
print('fix3 applied')
