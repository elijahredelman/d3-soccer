"""Core data models."""

from dataclasses import dataclass
from datetime import date
from enum import StrEnum


class Gender(StrEnum):
    MEN = "men"
    WOMEN = "women"


@dataclass(frozen=True)
class Team:
    name: str
    conference: str | None = None
    region: str | None = None


@dataclass(frozen=True)
class Game:
    season: int
    gender: Gender
    date: date
    home: str
    away: str
    home_goals: int | None = None
    away_goals: int | None = None
    neutral_site: bool = False

    @property
    def played(self) -> bool:
        return self.home_goals is not None and self.away_goals is not None

    @property
    def winner(self) -> str | None:
        """Winning team name, or None for a draw or unplayed game."""
        if not self.played or self.home_goals == self.away_goals:
            return None
        return self.home if self.home_goals > self.away_goals else self.away
