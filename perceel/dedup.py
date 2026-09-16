"""Duplicate detection within and across sources."""
from __future__ import annotations

import re

from .core import clean, slugify

_NOISE = re.compile(
    r"\b(te koop|for sale|perceel|percelen|kavel|bouwkavel|plot|land|grond|"
    r"in suriname|suriname|nr|no|nummer|#)\b", re.I)

_STREET_SUFFIX = re.compile(r"(weg|straat|laan|pad|dreef|street|road|lane)\b", re.I)


def street_key(item: dict) -> str:
    raw = " ".join(filter(None, [item.get("street") or item.get("title") or "",
                                 item.get("resort") or ""]))
    raw = _NOISE.sub(" ", clean(raw))
    raw = re.sub(r"\b(pc|p\.?c\.?|perc)\.?\s*\d+[a-z]?\b", " ", raw, flags=re.I)
    return slugify(raw)[:60]


def size_bucket(item: dict):
    s = item.get("size_m2")
    if not s:
        return None
    return int(round(s / 5.0))  # 5 m2 tolerance


def price_bucket(item: dict):
    from .core import price_in_eur
    p = price_in_eur(item.get("price"), item.get("currency"))
    if not p:
        return None
    return int(round(p / 500.0))  # 500 EUR tolerance


def fingerprints(item: dict) -> list[str]:
    """Keys that, if shared, mean two records are the same plot."""
    out = []
    sk, sz, pr = street_key(item), size_bucket(item), price_bucket(item)
    if sk and sz is not None and pr is not None:
        out.append(f"a|{sk}|{sz}|{pr}")
    if sk and sz is not None:
        out.append(f"b|{sk}|{sz}")
    if item.get("lat") and item.get("lon") and sz is not None:
        out.append(f"c|{round(item['lat'],4)}|{round(item['lon'],4)}|{sz}")
    if sk and pr is not None:
        out.append(f"d|{sk}|{pr}")
    return out


def merge(primary: dict, other: dict) -> dict:
    """Fold `other` into `primary`, keeping the richest values."""
    also = primary.setdefault("also_listed_by", [])
    entry = {"source": other.get("source"), "url": other.get("url"),
             "agent": other.get("agent"), "price": other.get("price"),
             "currency": other.get("currency")}
    if other.get("url") and all(e.get("url") != other.get("url") for e in also):
        also.append(entry)
    for field in ("size_m2", "price", "currency", "district", "resort", "street",
                  "title_type", "description", "lat", "lon", "geocode_quality"):
        if not primary.get(field) and other.get(field):
            primary[field] = other[field]
    imgs = list(primary.get("images") or [])
    for i in other.get("images") or []:
        if i not in imgs:
            imgs.append(i)
    primary["images"] = imgs[:10]
    phones = list(primary.get("phones") or [])
    for p in other.get("phones") or []:
        if p not in phones:
            phones.append(p)
    primary["phones"] = phones[:6]
    return primary


def _quality(item: dict) -> int:
    score = 0
    score += 3 if item.get("size_m2") else 0
    score += 3 if item.get("price") else 0
    score += 2 if item.get("images") else 0
    score += 2 if item.get("description") else 0
    score += 1 if item.get("district") else 0
    score += 1 if item.get("phones") else 0
    return score


def deduplicate(items: list[dict]):
    """Return (unique_items, dropped_count)."""
    by_source_id: dict[str, dict] = {}
    for it in items:
        sid = it.get("source_id")
        if sid and sid in by_source_id:
            merge(by_source_id[sid], it)
        elif sid:
            by_source_id[sid] = it
    pool = sorted(by_source_id.values(), key=_quality, reverse=True)

    index: dict[str, dict] = {}
    unique: list[dict] = []
    dropped = 0
    for it in pool:
        fps = fingerprints(it)
        hit = None
        for fp in fps:
            if fp in index:
                hit = index[fp]
                break
        if hit is not None and hit.get("source") != it.get("source"):
            merge(hit, it)
            dropped += 1
            continue
        if hit is not None and hit.get("url") == it.get("url"):
            dropped += 1
            continue
        if hit is not None and fps and fps[0] in index:
            merge(hit, it)
            dropped += 1
            continue
        unique.append(it)
        for fp in fps:
            index.setdefault(fp, it)
    return unique, dropped
