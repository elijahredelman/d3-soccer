from datetime import date

from d3soccer.models import Game, Gender


def make_game(home_goals, away_goals):
    return Game(2025, Gender.MEN, date(2025, 9, 1), "Amherst", "Williams", home_goals, away_goals)


def test_winner():
    assert make_game(2, 1).winner == "Amherst"
    assert make_game(0, 3).winner == "Williams"


def test_draw_and_unplayed_have_no_winner():
    assert make_game(1, 1).winner is None
    assert make_game(None, None).winner is None
    assert not make_game(None, None).played
