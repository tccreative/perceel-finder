"""Shared helpers: HTTP session, rate limiting, text/price/size parsing."""
from __future__ import annotations

import json
import os
import re
import time
import unicodedata
from pathlib import Path
from urllib.parse import urljoin, urlparse

import requests

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
DATA.mkdir(exist_ok=True)

with open(ROOT / "config.json", encoding="utf-8") as fh:
    CONFIG = json.load(fh)

UA = CONFIG.get("user_agent", "perceel-finder/1.0")
DELAY = float(CONFIG.get("request_delay_seconds", 1.2))

_last_hit: dict[str, float] = {}


class Http:
    """Polite HTTP client: one session, per-host delay, retries."""

    def __init__(self, delay: float = DELAY, ua: str = UA):
        self.delay = delay
        self.s = requests.Session()
        self.s.headers.update({
            "User-Agent": ua,
            "Accept": "text/html,application/xhtml+xml,application/json;q=0.9,*/*;q=0.8",
            "Accept-Language": "nl,en-US;q=0.8,en;q=0.6",
        })

    def _wait(self, url: str) -> None:
        host = urlparse(url).netloc
        prev = _last_hit.get(host, 0.0)
        gap = time.time() - prev
        if gap < self.delay:
            time.sleep(self.delay - gap)
        _last_hit[host] = time.time()

    def get(self, url: str, *, tries: int = 3, timeout: int = 40, **kw):
        last = None
        for attempt in range(tries):
            self._wait(url)
            try:
                r = self.s.get(url, timeout=timeout, **kw)
                if r.status_code == 200:
                    return r
                if r.status_code in (404, 410):
                    return None
                last = f"HTTP {r.status_code}"
            except requests.RequestException as exc:  # noqa: PERF203
                last = str(exc)
            time.sleep(2 * (attempt + 1))
        print(f"    ! give up on {url} ({last})")
        return None

    def json(self, url: str, **kw):
        r = self.get(url, **kw)
        if r is None:
            return None
        try:
            return r.json()
        except ValueError:
            return None

    def soup(self, url: str, **kw):
        from bs4 import BeautifulSoup
        r = self.get(url, **kw)
        if r is None:
            return None
        return BeautifulSoup(r.text, "lxml")


# ---------------------------------------------------------------- text utils

def clean(text: str | None) -> str:
    if not text:
        return ""
    text = unicodedata.normalize("NFKC", str(text))
    text = re.sub(r"<[^>]+>", " ", text)
    text = text.replace("\xa0", " ")
    return re.sub(r"\s+", " ", text).strip()


def slugify(text: str) -> str:
    text = unicodedata.normalize("NFKD", clean(text).lower())
    text = "".join(c for c in text if not unicodedata.combining(c))
    return re.sub(r"[^a-z0-9]+", "-", text).strip("-")


_CUR = {"eur": "EUR", "€": "EUR", "usd": "USD", "$": "USD", "us$": "USD",
        "srd": "SRD", "sr$": "SRD", "srd.": "SRD"}

# Rough reference rates, only used to make prices comparable on the map.
RATES_TO_EUR = {"EUR": 1.0, "USD": 0.92, "SRD": 0.023}


def parse_price(text: str | None):
    """-> (amount, currency, per_m2_flag) or (None, None, False)."""
    t = clean(text).lower()
    if not t or any(w in t for w in ("op aanvraag", "on request", "n.o.t.k", "prijs op")):
        return None, None, False
    cur = None
    for token, code in _CUR.items():
        if token in t:
            cur = code
            break
    per_m2 = bool(re.search(r"p(er)?\s*/?\s*m.?2|p/m", t))
    # numbers like 1.234.567,89 or 1,234,567.89 or 21500
    m = re.search(r"(\d[\d.,\s]{2,})", t)
    if not m:
        return None, cur, per_m2
    raw = m.group(1).replace(" ", "")
    if "," in raw and "." in raw:
        if raw.rfind(",") > raw.rfind("."):
            raw = raw.replace(".", "").replace(",", ".")
        else:
            raw = raw.replace(",", "")
    elif "," in raw:
        raw = raw.replace(",", ".") if len(raw.split(",")[-1]) == 2 else raw.replace(",", "")
    else:
        parts = raw.split(".")
        if len(parts) > 1 and all(len(p) == 3 for p in parts[1:]):
            raw = raw.replace(".", "")
    try:
        val = float(raw)
    except ValueError:
        return None, cur, per_m2
    if val <= 0:
        return None, cur, per_m2
    return val, cur or "EUR", per_m2


def price_in_eur(amount, currency):
    if amount is None:
        return None
    return round(amount * RATES_TO_EUR.get(currency or "EUR", 1.0), 2)


_SIZE_RE = re.compile(
    r"(\d[\d.,]*)\s*(m\s*[²2]|m2|vierkante meter|sq\s?m|ha\b|hectare|acre)", re.I)


def parse_size_m2(text: str | None):
    t = clean(text)
    if not t:
        return None
    m = _SIZE_RE.search(t)
    if not m:
        return None
    raw, unit = m.group(1), m.group(2).lower()
    raw = raw.replace(" ", "")
    if "," in raw and "." in raw:
        raw = raw.replace(".", "").replace(",", ".") if raw.rfind(",") > raw.rfind(".") else raw.replace(",", "")
    elif "," in raw:
        raw = raw.replace(",", ".") if len(raw.split(",")[-1]) <= 2 else raw.replace(",", "")
    else:
        parts = raw.split(".")
        if len(parts) > 1 and all(len(p) == 3 for p in parts[1:]):
            raw = raw.replace(".", "")
    try:
        val = float(raw)
    except ValueError:
        return None
    if unit.startswith("ha"):
        val *= 10000
    elif unit.startswith("acre"):
        val *= 4046.86
    return round(val, 1) if val > 0 else None


PHONE_RE = re.compile(r"(?:\+?597[\s\-.]?|\+?31[\s\-.]?)?(?:\(?0?\d{2,3}\)?[\s\-.]?)?\d{3}[\s\-.]?\d{3,4}")


def parse_phones(text: str | None) -> list[str]:
    t = clean(text)
    out = []
    for m in re.finditer(r"(\+?\d[\d\s\-().]{5,18}\d)", t):
        raw = re.sub(r"[^\d+]", "", m.group(1))
        digits = re.sub(r"\D", "", raw)
        if len(digits) < 6 or len(digits) > 15:
            continue
        if digits.startswith("597") and len(digits) >= 9:
            raw = "+" + digits
        elif len(digits) in (6, 7) :
            raw = "+597" + digits
        elif digits.startswith("31") and len(digits) >= 10:
            raw = "+" + digits
        if raw not in out:
            out.append(raw)
    return out[:4]


DISTRICTS = ["Paramaribo", "Wanica", "Commewijne", "Para", "Saramacca", "Nickerie",
             "Coronie", "Marowijne", "Brokopondo", "Sipaliwini"]


def guess_district(*chunks: str) -> str | None:
    blob = " ".join(clean(c) for c in chunks if c)
    for d in DISTRICTS:
        if re.search(rf"\b{d}\b", blob, re.I):
            return d
    return None


def absolute(base: str, href: str | None) -> str | None:
    if not href:
        return None
    return urljoin(base, href.strip())


def haversine_km(lat1, lon1, lat2, lon2):
    from math import asin, cos, radians, sin, sqrt
    if None in (lat1, lon1, lat2, lon2):
        return None
    dlat = radians(lat2 - lat1)
    dlon = radians(lon2 - lon1)
    a = sin(dlat / 2) ** 2 + cos(radians(lat1)) * cos(radians(lat2)) * sin(dlon / 2) ** 2
    return round(2 * 6371.0088 * asin(sqrt(a)), 3)


_BAD_PREFIX = re.compile(r"^https?:(?=https?://)", re.I)


def clean_image_urls(urls) -> list:
    """Drop junk and repair the double-scheme URLs some sites hand out."""
    out = []
    for u in urls or []:
        if not u or not isinstance(u, str):
            continue
        u = _BAD_PREFIX.sub("", u.strip())
        if u.startswith("//"):
            u = "https:" + u
        if not u.startswith("http"):
            continue
        if u not in out:
            out.append(u)
    return out[:10]


def new_listing(**kw) -> dict:
    base = {
        "source": None, "source_id": None, "url": None, "title": None,
        "street": None, "resort": None, "district": None, "address": None,
        "price": None, "currency": None, "price_eur": None, "price_per_m2": None,
        "size_m2": None, "title_type": None, "description": None,
        "images": [], "phones": [], "agent": None, "lat": None, "lon": None,
        "geocode_quality": None, "raw_location": None,
    }
    base.update(kw)
    base["images"] = clean_image_urls(base.get("images"))
    return base
