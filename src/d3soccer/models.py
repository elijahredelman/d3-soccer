"""
Shared data shapes for the D3 soccer pipeline.

Kept as plain dataclasses (not a DB model yet) so the scrapers can be
tested and iterated on before a real database schema is locked in. When
that schema is chosen (Postgres is the obvious default), these map almost
directly onto tables: Team, Player, Game, StandingRow -> teams, players,
games, standings.
"""

from dataclasses import dataclass


@dataclass
class Team:
    name: str  # e.g. "Occidental"
    conference: str  # e.g. "SCIAC"
    site_domain: str  # e.g. "oxyathletics.com"
    sport_slug: str = "mens-soccer"
    watch_provider: str | None = None  # filled in manually / crowdsourced


@dataclass
class Player:
    team: str
    number: str  # string: some jerseys are "00"
    name: str
    position: str  # GK / D / M / F
    class_year: str  # Fr. / So. / Jr. / Sr.
    height: str | None = None
    hometown: str | None = None
    high_school: str | None = None
    # season stats, filled from the stats page when available
    games_played: int | None = None
    goals: int | None = None
    assists: int | None = None
    points: int | None = None
    shots: int | None = None
    # goalkeeper-only fields
    minutes: int | None = None
    goals_against: int | None = None
    saves: int | None = None
    save_pct: float | None = None


@dataclass
class Game:
    team: str
    date: str  # ISO date where possible
    opponent: str
    location: str  # "home" / "away" / "neutral"
    conference_game: bool = False
    result: str | None = None  # "W 2-0", "L 0-1", "T 2-2", or None if upcoming
    watch_provider: str | None = None
    venue: str | None = None  # "W.C. Patterson Field" / "Los Angeles, CA" etc.
    time: str | None = None  # kickoff time as shown on the site, e.g. "4:00 PM PDT"


@dataclass
class StandingRow:
    conference: str
    team: str
    conf_record: str
    overall_record: str
    conf_points: str | None = None
    rank: int | None = None
