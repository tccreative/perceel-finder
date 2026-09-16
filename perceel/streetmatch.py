"""Reading a street name out of an advert headline.

Kept apart from the plain register lookup in `streets` because this is where
the judgement lives: which words form the name, which near-miss spellings are
the same street, and which are a different street that merely rhymes.
"""
from __future__ import annotations

import difflib
import re

from .streets import _pick, key, load


_SUFFIX_RE = re.compile(
    r"(straat|weg|laan|pad|dreef|gracht|plein|steeg|kanaal|polder|serie|kade|"
    r"singel|boulevard)$", re.I)
_SKIP = {"te", "koop", "aangeboden", "eigendom", "eigendoms", "eigendomskavel",
         "eigendomsperceel", "eigendomspercelen", "bouwperceel", "bouwkavel",
         "perceel", "percelen", "kavel", "kavels", "grondhuur", "verkoop",
         "ruim", "ruime", "mooi", "mooie", "aan", "de", "het", "een", "via",
         "nabij", "omgeving", "gelegen", "hoek", "hk", "zijstraat", "bloot"}


def candidates(text: str):
    """Every plausible street name in a headline, most specific first.

    "Baas Adriaanstraat" should be looked up whole before falling back to
    "Adriaanstraat", or the register happily offers Adrianusstraat instead.
    """
    words = re.findall(r"[A-Za-z0-9][\w'.-]*", text or "")
    out = []
    for i, w in enumerate(words):
        if not _SUFFIX_RE.search(w) or len(w) < 6:
            continue
        for j in range(max(0, i - 3), i + 1):
            if any(words[x].lower() in _SKIP for x in range(j, i)):
                continue
            phrase = " ".join(words[j:i + 1])
            # A house number may follow the street: "Leiding 7B", "Kwattaweg 100"
            tail = words[i + 1] if i + 1 < len(words) else ""
            out.append(phrase)
            if re.fullmatch(r"\d+[a-zA-Z]?", tail or ""):
                out.append(phrase + " " + tail)
    # Also plain "Leiding 7B" style names, which carry no street suffix at all.
    for i, w in enumerate(words[:-1]):
        if len(w) > 3 and re.fullmatch(r"\d+[a-zA-Z]?", words[i + 1]):
            out.append(w + " " + words[i + 1])
    seen, uniq = set(), []
    for c in sorted(out, key=len, reverse=True):
        if c.lower() not in seen:
            seen.add(c.lower())
            uniq.append(c)
    return uniq


def _digits(v: str) -> str:
    return "".join(re.findall(r"\d+", v or ""))


def _stem(v: str) -> str:
    """The name without its street suffix - where the real difference lives.

    The suffix has to come off before folding, not after: folding collapses
    "straat" to "strat", which _SUFFIX_RE no longer recognises, and leaving it
    on makes Adriaanstraat and Adrianusstraat look like near-twins.
    """
    return key(_SUFFIX_RE.sub("", v or "")) or key(v)


def find(street: str, district: str | None = None, resort: str | None = None,
         cutoff: float = 0.88, exact_only: bool = False):
    """Look one name up, tolerating the way adverts spell things.

    Returns (row, how) where how is "exact" or "fuzzy", or None. Three things
    have to hold before a near-match is accepted, because each of them was a
    real wrong pin: the corrected name starts with the same letter, any house
    or road number is identical (Leiding 7B is not Leiding 17), and the part
    before the street suffix matches on its own - otherwise the shared
    "-straat" alone makes Adriaanstraat look like Adrianusstraat.
    """
    idx = load()
    if not idx["keys"] or not street:
        return None
    k = key(street)
    if not k:
        return None
    if k in idx["by_key"]:
        row = _pick(idx["by_key"][k], district, resort)
        return (row, "exact") if row else None
    if exact_only:
        return None

    pool = idx["keys"]
    if district:
        pool = [kk for kk in idx["keys"]
                if any((r.get("district") or "").lower() == district.lower()
                       for r in idx["by_key"][kk])] or idx["keys"]
    # Adverts misspell the middle of a name, not the start.
    pool = [kk for kk in pool if kk[:1] == k[:1]]
    want_digits = _digits(street)
    stem, matcher = _stem(street), difflib.SequenceMatcher()
    matcher.set_seq2(stem)
    for cand in difflib.get_close_matches(k, pool, n=5, cutoff=cutoff):
        rows = idx["by_key"][cand]
        if _digits(rows[0]["name"]) != want_digits:
            continue
        matcher.set_seq1(_stem(rows[0]["name"]))
        if matcher.ratio() < 0.87:
            continue
        row = _pick(rows, district, resort)
        if row:
            return row, "fuzzy"
    return None


def find_in_text(text: str, district: str | None = None, resort: str | None = None):
    """Find the street a headline is talking about.

    Tries the fullest reading of the name first and only then shorter ones, so
    "Baas Adriaanstraat" is looked up whole before "Adriaanstraat" is tried.
    """
    cands = candidates(text or "")
    if not cands:
        return None
    for c in cands:                       # exact beats fuzzy, always
        hit = find(c, district, resort, exact_only=True)
        if hit:
            return hit + (c,)
    for c in cands:
        hit = find(c, district, resort)
        if hit:
            return hit + (c,)
    return None


