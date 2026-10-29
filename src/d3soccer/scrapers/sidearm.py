"""
Generic scraper for a "SIDEARM Sites" team athletics page.

Confirmed live on 2026-09-18 against oxyathletics.com (Occidental) — roster,
schedule, and stats pages all fetched and their real HTML inspected (via a
live browser, checking actual DOM/network, not guessed). Selectors below
are tested against real markup and verified to produce correct data
(cross-checked against Elijah Edelman's own roster entry and stat line).

URL pattern confirmed across 5 SCIAC schools (Occidental, Chapman,
Redlands, Pomona-Pitzer, Claremont-Mudd-Scripps):

    /sports/<slug>/roster
    /sports/<slug>/schedule/<year>
    /sports/<slug>/stats

Two different rendering styles were found within the same site:
- The roster page renders player cards directly in server HTML
  (<li class="sidearm-roster-player">...) — no JS needed.
- The schedule page renders games as <li class="sidearm-schedule-game">.
- The stats page ships as static <table class="sidearm-table
  highlight-column-hover ...">. A jQuery DataTables plugin adds a
  "dataTable" class client-side after load -- matching on that class
  against a plain requests.get() finds nothing (learned the hard way).
  fetch_stats() identifies the right tables by header row content
  (must contain "PLAYER") instead.

Not yet verified: whether every SCIAC/D3 school uses this exact template
version. Occidental, and the general "sidearm-roster-player" / "sidearm-
schedule-game" / "dataTable" class families, are widely used across
Sidearm sites, but a school on an older or customized template could
differ. If a given team returns zero results, that's the signal to fetch
that one page and check its markup the same way this file was built.
"""

from __future__ import annotations

import re

from bs4 import BeautifulSoup

from d3soccer.models import Game, Player
from d3soccer.scrapers import http


def _get(url: str) -> BeautifulSoup:
    return BeautifulSoup(http.get(url).text, "lxml")


def _nothing_found(soup: BeautifulSoup, url: str) -> ValueError:
    """An error saying what the page looked like, for pages that parse to nothing."""
    html = str(soup)
    title = soup.title.get_text(" ", strip=True) if soup.title else ""
    markers = [
        m
        for m in ("sidearm", "prestosports", "s-person-card", "s-game-card", "__NUXT__", "<table")
        if m in html
    ]
    return ValueError(f"nothing parsed from {url}: title {title!r}, markers {markers}")


def _clean(text: str) -> str:
    return re.sub(r"\s+", " ", text or "").strip()


# ---------------------------------------------------------------------
# Roster
# ---------------------------------------------------------------------


def fetch_roster(site_domain: str, team_name: str, sport_slug: str = "mens-soccer") -> list[Player]:
    url = f"https://{site_domain}/sports/{sport_slug}/roster"
    soup = _get(url)
    players = _parse_roster_html(soup, team_name) or _parse_roster_table(soup, team_name)
    if not players:
        raise _nothing_found(soup, url)
    return players


def _parse_roster_html(soup: BeautifulSoup, team_name: str) -> list[Player]:
    players: list[Player] = []
    for li in soup.select("li.sidearm-roster-player"):

        def txt(sel: str) -> str:
            el = li.select_one(sel)  # noqa: B023 -- called within this iteration only
            return _clean(el.get_text(strip=True)) if el else ""

        pos_el = li.select_one(".sidearm-roster-player-position")
        position = ""
        if pos_el:
            first_span = pos_el.select_one("span")
            position = _clean(first_span.get_text(strip=True)) if first_span else ""

        name = txt(".sidearm-roster-player-name h3")
        # Some sites (e.g. Baldwin Wallace) don't list jersey numbers at all, so only
        # the name is required. Staff are in a separate table, not these cards.
        number = txt(".sidearm-roster-player-jersey-number")
        if not name:
            continue  # malformed entry

        players.append(
            Player(
                team=team_name,
                number=number,
                name=name,
                position=position,
                class_year=txt(".sidearm-roster-player-academic-year"),
                height=txt(".sidearm-roster-player-height") or None,
                hometown=txt(".sidearm-roster-player-hometown") or None,
                high_school=txt(".sidearm-roster-player-highschool") or None,
            )
        )
    return players


# ---------------------------------------------------------------------
# Schedule
# ---------------------------------------------------------------------


def fetch_schedule(
    site_domain: str, team_name: str, year: int, sport_slug: str = "mens-soccer"
) -> list[Game]:
    url = f"https://{site_domain}/sports/{sport_slug}/schedule/{year}"
    soup = _get(url)
    games = _parse_schedule_html(soup, team_name) or _parse_schedule_table(soup, team_name)
    if not games:
        # Some schedule templates (e.g. Rhodes') render games with JavaScript, but the
        # page links a plain-text version of the same schedule.
        m = re.search(r"/services/schedule_txt\.ashx\?schedule=\d+", str(soup))
        if m:
            games = _parse_schedule_text(
                http.get(f"https://{site_domain}{m.group(0)}").text, team_name
            )
    if not games:
        raise _nothing_found(soup, url)
    return games


def _parse_schedule_text(text: str, team_name: str) -> list[Game]:
    """
    Sidearm's schedule_txt.ashx: a fixed-width table under a header line
    "Date  Time  At  Opponent  Location  Tournament  Result". Columns are cut at
    the header words' positions.
    """
    lines = [ln.rstrip() for ln in re.split(r"\r?\n\r?", text)]
    header = next(
        (i for i, ln in enumerate(lines) if ln.startswith("Date") and "Opponent" in ln), None
    )
    if header is None:
        return []
    names = ["Date", "Time", "At", "Opponent", "Location", "Tournament", "Result"]
    starts = [(n, lines[header].find(n)) for n in names if lines[header].find(n) >= 0]
    games = []
    for line in lines[header + 1 :]:
        if not line.strip():
            continue
        cols = {
            name: line[start : (starts[i + 1][1] if i + 1 < len(starts) else None)].strip()
            for i, (name, start) in enumerate(starts)
        }
        opponent = cols.get("Opponent", "")
        if not opponent or " vs. " in opponent:  # games between two other teams it hosts
            continue
        at = cols.get("At", "").lower()
        result = cols.get("Result", "")
        m = re.match(r"([WLT])\s+(\d+-\d+.*)", result)
        games.append(
            Game(
                team=team_name,
                date=cols.get("Date", ""),
                opponent=opponent,
                location=at if at in ("home", "away") else "unknown",
                conference_game=False,
                result=f"{m.group(1)},{m.group(2)}" if m else (result or None),
                venue=cols.get("Location") or None,
                time=cols.get("Time") or None,
            )
        )
    return games


def _parse_schedule_html(soup: BeautifulSoup, team_name: str) -> list[Game]:
    games: list[Game] = []
    for li in soup.select("li.sidearm-schedule-game"):
        opp_el = li.select_one(".sidearm-schedule-game-opponent-name")
        date_el = li.select_one(".sidearm-schedule-game-opponent-date span")
        result_el = li.select_one(".sidearm-schedule-game-result")
        venue_el = (
            li.select_one(".sidearm-schedule-game-location")
            or li.select_one(".sidearm-schedule-game-location a")
            or li.select_one("[class*='schedule-game-location']")
        )
        # Upcoming games show a separate time element; final games often
        # fold the time into the result text instead, so this is only
        # populated pre-kickoff -- not yet verified against every school's
        # markup (only Occidental's page has been inspected raw so far).
        time_el = li.select_one(".sidearm-schedule-game-time") or li.select_one(
            "[class*='schedule-game-time']"
        )

        opponent = _clean(opp_el.get_text(strip=True)) if opp_el else ""
        date = _clean(date_el.get_text(strip=True)) if date_el else ""
        result = _clean(result_el.get_text(strip=True)) if result_el else ""
        venue = _clean(venue_el.get_text(strip=True)) if venue_el else None
        time = _clean(time_el.get_text(strip=True)) if time_el else None

        if not opponent:
            continue

        classes = li.get("class", [])
        location = (
            "home"
            if "sidearm-schedule-home-game" in classes
            else ("away" if "sidearm-schedule-away-game" in classes else "unknown")
        )
        conference_game = bool(li.select_one(".sidearm-schedule-game-opponent-promotion"))

        games.append(
            Game(
                team=team_name,
                date=date,
                opponent=opponent,
                location=location,
                conference_game=conference_game,
                result=result or None,
                venue=venue or None,
                time=time or None,
            )
        )
    return games


# ---------------------------------------------------------------------
# Table layouts
# ---------------------------------------------------------------------
# Some Sidearm sites are set to show the roster or schedule as a plain table
# instead of cards (seen on Baldwin Wallace's roster and Rhodes' schedule). Header
# text varies a little, so columns are found by pattern.


def _table_rows(soup: BeautifulSoup, required: list[str]) -> list[dict[str, str]]:
    """Rows (header -> cell text) of the first table whose headers match every pattern."""
    for table in soup.find_all("table"):
        headers = [_clean(th.get_text(" ", strip=True)) for th in table.select("thead th")]
        if not all(any(re.search(p, h, re.I) for h in headers) for p in required):
            continue
        rows = []
        for tr in table.select("tbody tr"):
            cells = [_clean(c.get_text(" ", strip=True)) for c in tr.find_all(["td", "th"])]
            if len(cells) >= 2:
                rows.append(dict(zip(headers, cells)))
        return rows
    return []


def _col(row: dict[str, str], *patterns: str) -> str:
    for p in patterns:
        for h, v in row.items():
            if re.search(p, h, re.I):
                return v
    return ""


def _parse_roster_table(soup: BeautifulSoup, team_name: str) -> list[Player]:
    players = []
    for row in _table_rows(soup, [r"name", r"^(#|no\.?|num)"]):
        name, number = _col(row, r"name"), _col(row, r"^(#|no\.?|num)")
        if not name:
            continue
        hometown, high_school = _col(row, r"hometown"), _col(row, r"high school|previous")
        if hometown == high_school and " / " in hometown:  # one "Hometown / High School" column
            hometown, high_school = hometown.split(" / ", 1)
        players.append(
            Player(
                team=team_name,
                number=number,
                name=name,
                position=_col(row, r"^pos"),
                class_year=_col(row, r"^(cl|yr|year|class|academic)"),
                height=_col(row, r"^(ht|height)") or None,
                hometown=hometown or None,
                high_school=high_school or None,
            )
        )
    return players


def _parse_schedule_table(soup: BeautifulSoup, team_name: str) -> list[Game]:
    games = []
    for row in _table_rows(soup, [r"^date", r"opponent"]):
        opponent = _col(row, r"opponent")
        if not opponent:
            continue
        at = _col(row, r"^(at|h/a|home)")
        where = _col(row, r"^location")
        location = (
            "away"
            if at.lower() in ("at", "away", "a") or opponent.lower().startswith("at ")
            else "home"
            if at.lower() in ("vs", "vs.", "home", "h")
            else "unknown"
        )
        games.append(
            Game(
                team=team_name,
                date=_col(row, r"^date"),
                opponent=re.sub(r"^(at|vs\.?)\s+", "", opponent, flags=re.I).rstrip(" *"),
                location=location,
                conference_game="*" in opponent,
                result=_col(row, r"^result") or None,
                venue=where or None,
                time=_col(row, r"^time") or None,
            )
        )
    return games


# ---------------------------------------------------------------------
# Stats
# ---------------------------------------------------------------------


def fetch_stats(site_domain: str, team_name: str, sport_slug: str = "mens-soccer") -> list[Player]:
    """
    Returns Player records with season-stat fields populated. A Sidearm
    stats page has several tables (field-player cumulative stats,
    goalkeeper cumulative stats, and per-game logs for both) — this
    function identifies the two CUMULATIVE tables by their header row
    rather than a fixed index, since table order isn't guaranteed across
    schools.
    """
    url = f"https://{site_domain}/sports/{sport_slug}/stats"
    soup = _get(url)
    players = _parse_stats_html(soup, team_name)
    if not players:
        raise _nothing_found(soup, url)
    return players


def _table_headers(table) -> list[str]:
    return [_clean(th.get_text(strip=True)).upper() for th in table.select("thead th")]


def _parse_stats_html(soup: BeautifulSoup, team_name: str) -> list[Player]:
    players: list[Player] = []
    seen_names: set[str] = set()

    for table in soup.select("table.sidearm-table.highlight-column-hover"):
        headers = _table_headers(table)
        if "PLAYER" not in headers:
            continue  # skip per-game log tables (headers start with "DATE")

        is_keeper_table = "SV%" in headers or "GAA" in headers
        rows = table.select("tbody tr")
        for row in rows:
            cells = row.select("td")
            if len(cells) < 2:
                continue
            row_map = dict(zip(headers, [c.get_text(strip=True) for c in cells]))

            raw_name = row_map.get("PLAYER", "")
            # Sidearm concatenates the name twice around the jersey number
            # with no separator in the raw HTML text, e.g.
            # "Edelman, Elijah10Edelman, Elijah" -- everything before the
            # first digit is the clean "Last, First" form.
            m = re.match(r"^([^\d]+)", raw_name)
            name = _clean(m.group(1)) if m else _clean(raw_name)
            if not name or name in seen_names:
                continue
            seen_names.add(name)

            if is_keeper_table:
                players.append(
                    Player(
                        team=team_name,
                        number="",
                        name=name,
                        position="GK",
                        class_year="",
                        games_played=_to_int(row_map.get("GP")),
                        minutes=_to_int(row_map.get("MIN")),
                        goals_against=_to_int(row_map.get("GA")),
                        saves=_to_int(row_map.get("SV")),
                        save_pct=_to_float(row_map.get("SV%")),
                    )
                )
            else:
                players.append(
                    Player(
                        team=team_name,
                        number="",
                        name=name,
                        position="",
                        class_year="",
                        games_played=_to_int(row_map.get("GP")),
                        goals=_to_int(row_map.get("G")),
                        assists=_to_int(row_map.get("A")),
                        points=_to_int(row_map.get("PTS")),
                        shots=_to_int(row_map.get("SH")),
                        minutes=_to_int(row_map.get("MIN")),
                    )
                )
    return players


def _to_int(v: str | None) -> int | None:
    if not v:
        return None
    try:
        return int(re.sub(r"[^\d-]", "", v))
    except ValueError:
        return None


def _to_float(v: str | None) -> float | None:
    if not v:
        return None
    try:
        return float(re.sub(r"[^\d.]", "", v))
    except ValueError:
        return None
