"""SQLite persistence for scraped data."""

import sqlite3
from collections.abc import Iterable
from pathlib import Path

from d3soccer import config
from d3soccer.models import Game

SCHEMA = """
CREATE TABLE IF NOT EXISTS games (
    season       INTEGER NOT NULL,
    gender       TEXT    NOT NULL,
    date         TEXT    NOT NULL,
    home         TEXT    NOT NULL,
    away         TEXT    NOT NULL,
    home_goals   INTEGER,
    away_goals   INTEGER,
    neutral_site INTEGER NOT NULL DEFAULT 0,
    PRIMARY KEY (gender, date, home, away)
);
"""


def connect(path: Path = config.DB_PATH) -> sqlite3.Connection:
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path)
    conn.executescript(SCHEMA)
    return conn


def save_games(conn: sqlite3.Connection, games: Iterable[Game]) -> int:
    rows = [
        (
            g.season,
            g.gender.value,
            g.date.isoformat(),
            g.home,
            g.away,
            g.home_goals,
            g.away_goals,
            int(g.neutral_site),
        )
        for g in games
    ]
    with conn:
        conn.executemany("INSERT OR REPLACE INTO games VALUES (?, ?, ?, ?, ?, ?, ?, ?)", rows)
    return len(rows)
