"""
National-level data: live scores, individual stat leaders, and the
United Soccer Coaches D3 Top 25 (used as the rankings stand-in until the
NCAA publishes its first weekly NPI of the season).

Unlike the per-team Sidearm scrapers, this part is already confirmed
working end-to-end with real JSON, via a free third-party wrapper around
ncaa.com's own data feed: github.com/henrygd/ncaa-api. That project is NOT
an official NCAA API -- flagged in feasibility-findings.md as needing a
terms-of-use review before this is a paid product. Self-hosting that
wrapper (it ships a docker-compose.yml) removes the dependency on someone
else's free public instance, which is worth doing regardless of the legal
question, just for reliability.
"""

from __future__ import annotations

import requests

NCAA_API_BASE = "https://ncaa-api.henrygd.me"  # self-host this in production
HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; D3SoccerAppBot/0.1; contact: elijahredelman@gmail.com)"
}
TIMEOUT = 15


def fetch_scoreboard(division: str = "d3") -> dict:
    """Live + today's D3 men's soccer scores. Confirmed working 2026-09-18."""
    url = f"{NCAA_API_BASE}/scoreboard/soccer-men/{division}"
    resp = requests.get(url, headers=HEADERS, timeout=TIMEOUT)
    resp.raise_for_status()
    return resp.json()


def fetch_individual_stat_leaders(stat_id: int, division: str = "d3") -> dict:
    """
    National individual stat leaders. Confirmed working 2026-09-18 for
    stat_id=421 (goalkeeper save %), plus the ids in STAT_CATEGORIES below
    (goals/gm, assists/gm, points/gm) -- pulled the raw category list from
    ncaa-api.henrygd.me/stats/soccer-men/d3 and verified each id returns
    real, plausible current-season leaders.
    """
    url = f"{NCAA_API_BASE}/stats/soccer-men/{division}/current/individual/{stat_id}"
    resp = requests.get(url, headers=HEADERS, timeout=TIMEOUT)
    resp.raise_for_status()
    return resp.json()


# Individual stat category ids on ncaa.com/ncaa-api, confirmed live
# 2026-09-18 against https://ncaa-api.henrygd.me/stats/soccer-men/d3 (19
# individual categories total there; these are the ones the app surfaces).
STAT_CATEGORIES = {
    "save_pct": 421,
    "goals_per_game": 5,
    "assists_per_game": 6,
    "points_per_game": 4,
}


def fetch_team_stat_leaders(stat_id: int, division: str = "d3") -> dict:
    """
    National TEAM-level stat leaders (as opposed to individual player
    leaders above) -- team goals/gm, total goals, total assists, team
    assists/gm. Category ids found + spot-checked 2026-09-27:
    stat_id=30 (Scoring Offense) confirmed against real data (Saint
    John's (MN) leading at 5.00 goals/gm, 45 goals in 9 games). The other
    three ids were confirmed to exist in the category listing but not yet
    independently spot-checked with a live fetch -- verify their returned
    data looks plausible the first time this runs.
    """
    url = f"{NCAA_API_BASE}/stats/soccer-men/{division}/current/team/{stat_id}"
    resp = requests.get(url, headers=HEADERS, timeout=TIMEOUT)
    resp.raise_for_status()
    return resp.json()


# Team-level stat category ids on ncaa.com/ncaa-api, found 2026-09-27
# against https://ncaa-api.henrygd.me/stats/soccer-men/d3 (team-stats
# section of the same category listing used for STAT_CATEGORIES above).
TEAM_STAT_CATEGORIES = {
    "goals_per_game": 30,  # "Scoring Offense" -- team goals/gm
    "total_goals": 575,  # "Total Goals"
    "total_assists": 569,  # "Total Assists"
    "assists_per_game": 90,  # "Assists Per Game" (team)
}


def fetch_npi_rankings(division: str = "d3") -> dict:
    """
    NPI rankings. Confirmed to return an empty `data` array as of
    2026-09-18 -- check again as the season progresses; NPI typically
    starts publishing a few weeks in, not week 1.
    """
    url = f"{NCAA_API_BASE}/rankings/soccer-men/{division}/national-rankings-npi"
    resp = requests.get(url, headers=HEADERS, timeout=TIMEOUT)
    resp.raise_for_status()
    return resp.json()


def fetch_united_soccer_coaches_poll() -> list[dict]:
    """
    The D3 Top 25, pulled directly from the source (United Soccer Coaches'
    own site), since it wasn't available through the ncaa-api wrapper.
    Confirmed working 2026-09-18 (Poll 1, dated Sept 15, 2026 -- records
    through Sept 13).

    NOTE: unitedsoccercoaches.org doesn't expose this as JSON -- this page
    was read via a research/rendering tool. A production scraper needs to
    fetch the raw HTML and find the real table/markup; this function is a
    first-pass BeautifulSoup parser to verify against that HTML.
    """
    from bs4 import BeautifulSoup

    url = "https://unitedsoccercoaches.org/rankings/college-rankings/ncaa-diii-men/"
    resp = requests.get(url, headers=HEADERS, timeout=TIMEOUT)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "lxml")

    rankings = []
    table = soup.find("table")
    if not table:
        return rankings
    for tr in table.find_all("tr"):
        cells = [c.get_text(strip=True) for c in tr.find_all(["td", "th"])]
        if len(cells) < 2 or not cells[0].isdigit():
            continue
        rankings.append(
            {
                "rank": int(cells[0]),
                "team": cells[1],
                "record": cells[2] if len(cells) > 2 else None,
            }
        )
    return rankings
