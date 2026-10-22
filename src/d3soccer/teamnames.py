"""
Matching the short names conference sites use ("UW-Platteville", "W&J",
"North Central*") to the full names in our team registry
("Wisconsin-Platteville", "Washington & Jefferson College", "North Central
College"), so a standings row or a schedule opponent can be tied back to the
team whose roster/schedule/stats we scraped.

Matching is always within one conference's registry, which keeps short names
like "Eastern" or "Trinity" unambiguous.
"""

from __future__ import annotations

import re

# Words that carry no identity: "Hope" == "Hope College".
STOPWORDS = {"college", "university", "of", "the", "at", "in", "institute", "and"}

# Per-token expansions applied to both sides before comparing.
TOKEN_MAP = {
    "uw": ["wisconsin"],
    "st": ["saint"],
    "univ": ["university"],
    "col": ["college"],
    "tech": ["technology"],
    "conn": ["connecticut"],
    "nc": ["north", "carolina"],
    "md": ["maryland"],
    "mn": ["minnesota"],
    "il": ["illinois"],
    "ma": ["massachusetts"],
    "pa": ["pennsylvania"],
    "wi": ["wisconsin"],
    "vtsu": ["vermont", "state"],
    "fdu": ["fairleigh", "dickinson"],
}

# Abbreviations no token rule can recover, keyed by normalized short name.
ALIASES = {
    "w j": "washington jefferson",
    "ccny": "city new york",
    "msoe": "milwaukee school engineering",
    "emu": "eastern mennonite",
    "new york": "nyu",
    "batten": "virginia wesleyan",
    "penn": "pennsylvania technology",
}

# Clinch/seed markers conference sites tack onto names: "Luther*", "MSOE-x",
# "WartburgQ", "Western Connecticut1". Also a leading poll rank: "#13Macalester".
_MARKERS = re.compile(r"(\*+|-[a-z]|(?<=[a-z])[A-Z]|\d+)$")
_RANK = re.compile(r"^(#|No\.\s*)\d+\s*")


def clean(name: str) -> str:
    """Display form: rank prefix and clinch markers removed."""
    name = _RANK.sub("", (name or "").strip())
    return _MARKERS.sub("", name).strip()


def tokens(name: str) -> frozenset[str]:
    text = clean(name).lower().replace("&", " ").replace("'", "").replace(".", "")
    words = re.findall(r"[a-z0-9]+", text)
    key = " ".join(w for w in words if w not in STOPWORDS)
    if key in ALIASES:
        words = ALIASES[key].split()
    out: set[str] = set()
    for w in words:
        out.update(TOKEN_MAP.get(w, [w]))
    return frozenset(out - STOPWORDS)


def match_all(names: list[str], registry: list[str]) -> dict[str, str]:
    """
    Map each of `names` to at most one registry name, each registry name used
    once. Exact token matches are claimed first so that, e.g., "Randolph-Macon"
    takes its row before "Randolph" (a different school) can grab it by subset.
    """
    reg_tokens = {r: tokens(r) for r in registry}
    out: dict[str, str] = {}
    claimed: set[str] = set()

    for n in names:
        t = tokens(n)
        hit = next((r for r, rt in reg_tokens.items() if rt == t and r not in claimed), None)
        if hit:
            out[n] = hit
            claimed.add(hit)

    for n in names:
        if n in out:
            continue
        t = tokens(n)
        if not t:
            continue
        hits = [r for r, rt in reg_tokens.items() if r not in claimed and (t <= rt or rt <= t)]
        if len(hits) == 1:
            out[n] = hits[0]
            claimed.add(hits[0])
    return out


def match_one(name: str, registry: list[str]) -> str | None:
    """Best registry match for a single name (e.g. a schedule opponent), or None."""
    t = tokens(name)
    if not t:
        return None
    exact = [r for r in registry if tokens(r) == t]
    if exact:
        return exact[0]
    hits = [r for r in registry if t <= tokens(r) or tokens(r) <= t]
    return hits[0] if len(hits) == 1 else None
