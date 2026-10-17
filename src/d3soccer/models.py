"""
Shared data shapes for the D3 soccer pipeline.

Kept as plain dataclasses (not a DB model yet) so the scrapers can be
tested and iterated on before a real database schema is locked in. When
that schema is chosen (Postgres is the obvious default), these map almost
directly onto tables: Team, Player, Game, StandingRow -> teams, players,
games, standings.
"""

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class Team:
    name: str                  # e.g. "Occidental"
    conference: str            # e.g. "SCIAC"
    site_domain: str           # e.g. "oxyathletics.com"
    sport_slug: str = "mens-soccer"
    watch_provider: Optional[str] = None   # filled in manually / crowdsourced


@dataclass
class Player:
    team: str
    number: str                # string: some jerseys are "00"
    name: str
    position: str               # GK / D / M / F
    class_year: str             # Fr. / So. / Jr. / Sr.
    height: Optional[str] = None
    hometown: Optional[str] = None
    high_school: Optional[str] = None
    # season stats, filled from the stats page when available
    games_played: Optional[int] = None
    goals: Optional[int] = None
    assists: Optional[int] = None
    points: Optional[int] = None
    shots: Optional[int] = None
    # goalkeeper-only fields
    minutes: Optional[int] = None
    goals_against: Optional[int] = None
    saves: Optional[int] = None
    save_pct: Optional[float] = None


@dataclass
class Game:
    team: str
    date: str                   # ISO date where possible
    opponent: str
    location: str               # "home" / "away" / "neutral"
    conference_game: bool = False
    result: Optional[str] = None      # "W 2-0", "L 0-1", "T 2-2", or None if upcoming
    watch_provider: Optional[str] = None
    venue: Optional[str] = None       # "W.C. Patterson Field" / "Los Angeles, CA" etc.
    time: Optional[str] = None        # kickoff time as shown on the site, e.g. "4:00 PM PDT"


@dataclass
class StandingRow:
    conference: str
    team: str
    conf_record: str
    overall_record: str
    conf_points: Optional[str] = None
    rank: Optional[int] = None
