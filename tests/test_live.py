import json

from d3soccer.pipelines import live
from d3soccer.scrapers import ncaa_national as nn


def test_live_writes_scores_and_started_games_box_scores(tmp_path, monkeypatch):
    monkeypatch.setattr(live, "WEB_DIR", tmp_path)

    def game(gid, state):
        side = {"names": {"short": "T" + gid}, "score": "1"}
        return {"game": {"gameID": gid, "gameState": state, "home": side, "away": side}}

    monkeypatch.setattr(
        nn, "fetch_scoreboard", lambda: {"games": [game("1", "live"), game("2", "pre")]}
    )
    monkeypatch.setattr(nn, "fetch_boxscore", lambda gid: {"contestId": gid})
    out = live.run()
    assert out["boxscores"] == ["1"]
    assert json.loads((tmp_path / "boxscores" / "1.json").read_text()) == {"contestId": "1"}
    saved = json.loads((tmp_path / "live.json").read_text())
    assert [r["id"] for r in saved["scoreboard"]] == ["1", "2"] and saved["fetchedAt"]
