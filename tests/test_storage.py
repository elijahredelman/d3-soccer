from datetime import date

from d3soccer import storage
from d3soccer.models import Game, Gender


def test_save_games_upserts(tmp_path):
    conn = storage.connect(tmp_path / "test.db")
    g = Game(2025, Gender.MEN, date(2025, 9, 1), "A", "B", 1, 0)
    storage.save_games(conn, [g, g])
    assert conn.execute("SELECT COUNT(*) FROM games").fetchone()[0] == 1
