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


# National feeds (NCAA NPI, coaches' poll, the bracket) name teams with their own
# abbreviations and are matched against every conference's registry at once, where
# short names like "Trinity" are ambiguous. These go straight to a registry name.
NATIONAL_ALIASES = {
    "cwru": "Case Western Reserve",
    "uchicago": "Chicago",
    "washu": "Washington University in St. Louis",
    "cms": "Claremont-Mudd-Scripps",
    "trinity (tx)": "Trinity University",
    "trinity (conn.)": "Trinity",
    "trinity (ct)": "Trinity",
    "north central (il)": "North Central College",
    "north central (ill.)": "North Central College",
    "plattsburgh st.": "SUNY Plattsburgh",
    "plattsburgh state": "SUNY Plattsburgh",
    "wis.-superior": "University of Wisconsin-Superior",
    "wisconsin-superior": "University of Wisconsin-Superior",
    "wesleyan (ct)": "Wesleyan",
    "westconn": "Western Connecticut",
    "bridgewater (va)": "Bridgewater College",
    "bridgewater st.": "Bridgewater State",
    "stevens": "Stevens Institute of Technology",
    "thomas (me)": "Thomas College",
    "st. thomas (tx)": "University of St. Thomas (Houston)",
    "rochester (ny)": "Rochester",
    "st. joseph's (me)": "Saint Joseph's College of Maine",
}

# A trailing state tag the registry name doesn't carry: "Southwestern (TX)".
_STATE_TAG = re.compile(r"\s*\([A-Za-z. ]{2,6}\)$")

# Abbreviations the NCAA uses inside names: "Montclair St.", "Wis.-Platteville".
_NATIONAL_EXPANSIONS = [
    (re.compile(r"\bSt\.$"), "State"),
    (re.compile(r"\bWis\.-"), "Wisconsin-"),
    (re.compile(r"\bIll\. "), "Illinois "),
    (re.compile(r"\bChris\. "), "Christopher "),
    (re.compile(r"\bWash\. "), "Washington "),
    (re.compile(r"\bSt\.-"), "State "),  # "Penn St.-Behrend"
    (re.compile(r"\bVa\.$"), "Virginia"),  # "Southern Va."
]


def match_national(names: list[str], registry: list[str]) -> dict[str, str]:
    """
    Map national-feed team names to registry names across all conferences. Each
    name is matched on its own (the poll and NPI both name the same teams): an
    alias, else an exact token match, else a unique registry name that contains all
    of its words. Not the reverse: "Roger Williams" is not "Williams".
    """
    reg = set(registry)
    reg_tokens = {r: tokens(r) for r in registry}
    out: dict[str, str] = {}
    for n in dict.fromkeys(names):
        # Raw name first: clean() would strip "WashU" to "Wash" as a clinch marker.
        alias = NATIONAL_ALIASES.get(n.strip().lower()) or NATIONAL_ALIASES.get(clean(n).lower())
        if alias in reg:
            out[n] = alias
            continue
        expanded = clean(n)
        for pattern, repl in _NATIONAL_EXPANSIONS:
            expanded = pattern.sub(repl, expanded)
        for candidate in dict.fromkeys([expanded, _STATE_TAG.sub("", expanded)]):
            t = tokens(candidate)
            if not t:
                continue
            exact = [r for r, rt in reg_tokens.items() if rt == t]
            hits = exact or [r for r, rt in reg_tokens.items() if t <= rt]
            if len(hits) == 1:
                out[n] = hits[0]
                break
    return out
