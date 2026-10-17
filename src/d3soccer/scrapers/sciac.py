"""
SCIAC-specific registry and conference-level scraping.

Team domains confirmed live on 2026-09-18 (5 fetched directly, 5 identified
via search + cross-referenced against the SCIAC standings page team list).
"""

from __future__ import annotations

import re

import requests
from bs4 import BeautifulSoup

from d3soccer.models import StandingRow, Team

CONFERENCE_NAME = "SCIAC"

TEAMS: list[Team] = [
    Team(name="Occidental", conference=CONFERENCE_NAME, site_domain="oxyathletics.com"),
    Team(name="Chapman", conference=CONFERENCE_NAME, site_domain="athletics.chapman.edu"),
    Team(name="Redlands", conference=CONFERENCE_NAME, site_domain="goredlands.com"),
    Team(name="Pomona-Pitzer", conference=CONFERENCE_NAME, site_domain="sagehens.com"),
    Team(name="Claremont-Mudd-Scripps", conference=CONFERENCE_NAME, site_domain="cmsathletics.org"),
    Team(name="Whittier", conference=CONFERENCE_NAME, site_domain="wcpoets.com"),
    Team(name="La Verne", conference=CONFERENCE_NAME, site_domain="leopardathletics.com"),
    Team(name="California Lutheran", conference=CONFERENCE_NAME, site_domain="clusports.com"),
    Team(name="Caltech", conference=CONFERENCE_NAME, site_domain="gocaltech.com"),
    Team(name="Azusa Pacific", conference=CONFERENCE_NAME, site_domain="athletics.apu.edu"),
]

STANDINGS_URL = "https://thesciac.org/standings.aspx?path=msoc"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; D3SoccerAppBot/0.1; contact: elijahredelman@gmail.com)"
}


def _first_matching(row_map: dict, *candidates: str) -> str | None:
    """Case-insensitive lookup trying several possible header spellings."""
    lower_map = {k.lower(): v for k, v in row_map.items()}
    for c in candidates:
        if c.lower() in lower_map:
            return lower_map[c.lower()]
    return None


def fetch_standings() -> list[StandingRow]:
    """
    Pulls the *current season* standings -- this URL doesn't need a
    per-season numeric ID (unlike the historical `standings.aspx?standings=NNN`
    links), which is what makes it safe to hit on a schedule without
    updating a season ID every year.

    Confirmed live on 2026-09-18 against a real fetch (not a research tool):
    the page is a real static <table class="sidearm-table sidearm-standings-
    table">, rendered responsively with duplicate hidden/visible columns
    (one set marked hide-on-large for mobile, one hide-on-medium-down for
    desktop) -- this parser reads only the desktop-visible set to avoid
    double-counting.

    BUG FOUND 2026-10-06: this originally hardcoded the header text as
    "CONF. W-L" / "W-L" / "CONF. PCT" (matching the site's 2026-09-18
    layout), but thesciac.org has since added columns (Conf. GP, CPts,
    Conf. PF-PA, GP, PF-PA, L10, Streak) and renamed the ones we use to
    plain "Conf" / "Overall" / "CPct." -- this silently returned blank
    records for every team instead of erroring, which is exactly the
    kind of thing a column-name match should never let through quietly.
    Fixed by reusing the same case-insensitive multi-spelling
    _first_matching() approach as conferences.py's generic parser,
    instead of two near-duplicate hardcoded parsers drifting apart.
    Re-verified live 2026-10-06 against real data (Redlands 3-0-2 conf /
    6-1-4 overall, matches the raw HTML exactly).

    Also strips trailing parenthetical annotations from team names (e.g.
    "Azusa Pacific(First Year of NCAA Reclassification)" -> "Azusa
    Pacific") -- the site appends season-context notes directly into the
    School cell's text with no separator.
    """
    resp = requests.get(STANDINGS_URL, headers=HEADERS, timeout=15)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "lxml")

    table = soup.select_one("table.sidearm-standings-table")
    if not table:
        return []

    thead = table.find("thead")
    raw_headers = [
        th.get_text(strip=True)
        for th in thead.select("th.hide-on-medium-down, th:not(.hide-on-large)")
    ]
    headers: list[str] = []
    for h in raw_headers:
        if not headers or headers[-1] != h:
            headers.append(h)

    rows: list[StandingRow] = []
    for tr in table.select("tbody tr"):
        cells = tr.select("td.hide-on-medium-down")
        vals = [c.get_text(strip=True) for c in cells]
        if len(vals) < 2:
            continue
        row_map = dict(zip(headers, vals))
        team_name = _first_matching(row_map, "School", "Team")
        if not team_name:
            continue
        team_name = re.sub(r"\s*\([^)]*\)\s*$", "", team_name).strip()
        rows.append(
            StandingRow(
                conference=CONFERENCE_NAME,
                team=team_name,
                conf_record=_first_matching(row_map, "CONF. W-L", "Conf", "Conference") or "",
                overall_record=_first_matching(row_map, "W-L", "Overall") or "",
                conf_points=_first_matching(row_map, "CONF. PCT", "CPct.", "Pct."),
            )
        )
    return rows
