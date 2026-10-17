from dataclasses import asdict

from d3soccer.models import Game, Player


def test_player_optional_stats_default_to_none():
    p = Player(team="Occidental", number="00", name="Casey Scott", position="GK", class_year="Sr.")
    assert p.number == "00"
    assert p.goals is None and p.saves is None


def test_game_serializes_to_snapshot_shape():
    g = Game(team="Occidental", date="2026-09-01", opponent="Caltech", location="home")
    assert asdict(g) == {
        "team": "Occidental",
        "date": "2026-09-01",
        "opponent": "Caltech",
        "location": "home",
        "conference_game": False,
        "result": None,
        "watch_provider": None,
        "venue": None,
        "time": None,
    }
