from datetime import date

from d3soccer.analysis import standings
from d3soccer.models import Game, Gender


def game(home, away, hg, ag):
    return Game(2025, Gender.WOMEN, date(2025, 9, 1), home, away, hg, ag)


def test_standings_points_and_order():
    table = standings([game("A", "B", 2, 0), game("B", "C", 1, 1), game("C", "A", None, None)])
    assert list(table["team"]) == ["A", "C", "B"]  # C ahead of B on goal difference
    a = table.iloc[0]
    assert (a.gp, a.w, a.pts, a.gd) == (1, 1, 3, 2)
    assert table.set_index("team").loc["B", "pts"] == 1


def test_standings_empty():
    assert standings([]).empty
