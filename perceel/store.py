"""Persist listings, tracking when each plot was first and last seen."""
from __future__ import annotations

import json
from datetime import date
from pathlib import Path

from .core import DATA, price_in_eur

STORE = DATA / "listings.json"


def load() -> dict:
    if STORE.exists():
        return json.loads(STORE.read_text(encoding="utf-8"))
    return {"generated": None, "listings": []}


def _key(item: dict) -> str:
    return item.get("source_id") or item.get("url") or item.get("title") or ""


def merge_run(previous: dict, fresh: list[dict]) -> dict:
    today = date.today().isoformat()
    old = {_key(i): i for i in previous.get("listings", [])}
    out = []
    for it in fresh:
        k = _key(it)
        prev = old.get(k)
        it["first_seen"] = (prev or {}).get("first_seen", today)
        it["last_seen"] = today
        it["is_new"] = prev is None
        if prev and prev.get("price") and it.get("price") and prev["price"] != it["price"]:
            it["previous_price"] = prev["price"]
        it["price_eur"] = price_in_eur(it.get("price"), it.get("currency"))
        if it.get("price_eur") and it.get("size_m2"):
            it["eur_per_m2"] = round(it["price_eur"] / it["size_m2"], 1)
        out.append(it)
    seen_keys = {_key(i) for i in out}
    gone = [i for i in previous.get("listings", []) if _key(i) not in seen_keys]
    for g in gone:
        g["still_listed"] = False
    return {
        "generated": today,
        "counts": {"active": len(out), "new_this_run": sum(1 for i in out if i.get("is_new")),
                   "gone_since_last_run": len(gone)},
        "listings": out,
        "archived": gone[:400],
    }


def save(data: dict, extra_paths: list[Path] | None = None) -> None:
    payload = json.dumps(data, ensure_ascii=False, separators=(",", ":"))
    STORE.write_text(payload, encoding="utf-8")
    for p in extra_paths or []:
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(payload, encoding="utf-8")
