import json

import pytest

from d3soccer.models import Player, StandingRow, Team
from d3soccer.pipelines import conferences, national

TEAM_A = Team(name="A", conference="TEST", site_domain="a.edu")
TEAM_B = Team(name="B", conference="TEST", site_domain="b.edu")


@pytest.fixture
def fake_sites(monkeypatch):
    """One test conference; team B's site is down and its roster page is empty."""
    monkeypatch.setattr(
        conferences,
        "registry",
        lambda: {
            "TEST": {
                "teams": [TEAM_A, TEAM_B],
                "fetch_standings": lambda: [StandingRow("TEST", "A", "1-0-0", "5-0-0")],
            },
            "OTHER": {"teams": [], "fetch_standings": lambda: []},
        },
    )

    def roster(domain, name, slug):
        return [] if name == "B" else [Player(name, "1", "New Player", "F", "Fr.")]

    def down(domain, name, *args):
        if name == "B":
            raise ConnectionError("403")
        return []

    monkeypatch.setattr(conferences, "fetch_roster", roster)
    monkeypatch.setattr(conferences, "fetch_schedule", down)
    monkeypatch.setattr(conferences, "fetch_stats", down)


def test_conferences_carries_forward_failed_and_empty_fetches(snapshot_dir, fake_sites):
    previous = {
        "conferences": {
            "TEST": {
                "standings": [],
                "teams": {"B": {"roster": ["old roster"], "schedule": ["old schedule"]}},
            },
            "OTHER": {"standings": ["kept as is"], "teams": {}},
        }
    }
    old = snapshot_dir / "conferences3_snapshot_2026-10-06.json"
    old.write_text(json.dumps(previous))

    snap = conferences.run(["TEST"])

    a, b = snap["conferences"]["TEST"]["teams"]["A"], snap["conferences"]["TEST"]["teams"]["B"]
    assert a["roster"][0]["name"] == "New Player" and "roster" not in a["stale"]
    assert b["roster"] == ["old roster"] and b["schedule"] == ["old schedule"]
    assert b["stale"] == ["roster", "schedule", "stats"]
    assert snap["conferences"]["TEST"]["standings"][0]["team"] == "A"
    assert snap["conferences"]["OTHER"]["standings"] == ["kept as is"]  # not pulled this run
    assert any("B schedule: ConnectionError" in f for f in snap["failures"])
    assert not old.exists()  # superseded by the new conferences snapshot


def test_conferences_rejects_unknown_key(snapshot_dir, fake_sites):
    with pytest.raises(SystemExit, match="NOPE"):
        conferences.run(["NOPE"])


def test_national_keeps_previous_npi_when_feed_fails(snapshot_dir, monkeypatch):
    prev = {"npi_rankings": {"data": [{"Rank": "1", "School": "Tufts"}]}, "leaders": {}}
    (snapshot_dir / "leaders_snapshot_2026-10-06.json").write_text(json.dumps(prev))

    nn = national.ncaa_national
    monkeypatch.setattr(nn, "STAT_CATEGORIES", {"save_pct": 421})
    monkeypatch.setattr(nn, "TEAM_STAT_CATEGORIES", {})
    monkeypatch.setattr(nn, "fetch_individual_stat_leaders", lambda i: {"data": [{"Rank": "1"}]})
    monkeypatch.setattr(nn, "fetch_npi_rankings", lambda: {"data": []})
    monkeypatch.setattr(nn, "fetch_scoreboard", lambda: {"games": []})
    monkeypatch.setattr(nn, "fetch_united_soccer_coaches_poll", lambda: [{"rank": 1}])

    out = national.run()

    assert out["npi_rankings"] == prev["npi_rankings"]
    assert out["scoreboard"] == {"games": []}  # no games today is real data, not a failure
    assert out["failures"] == ["NPI rankings: empty result"]
    assert [p.name for p in snapshot_dir.iterdir()] == [
        f"national_snapshot_{out['generated']}.json"
    ]


def test_merge_finals_keeps_old_finals_and_drops_stale_ones():
    from d3soccer.pipelines.national import merge_finals

    def game(gid, state, epoch, home_wins=True):
        side = lambda name, won: {"names": {"short": name}, "score": "1", "winner": won}  # noqa: E731
        return {
            "game": {
                "gameID": gid,
                "gameState": state,
                "startTimeEpoch": str(epoch),
                "home": side("Tufts", home_wins),
                "away": side("Amherst", not home_wins),
            }
        }

    now = 100 * 86400
    previous = {"old": {"id": "old", "epoch": 1}, "kept": {"id": "kept", "epoch": now - 86400}}
    board = {"games": [game("1", "final", now, home_wins=False), game("2", "live", now)]}
    out = merge_finals(previous, board, now)
    assert set(out) == {"kept", "1"}  # stale "old" dropped, live game "2" not a final
    assert out["1"]["win"] == "away" and out["1"]["hs"] == out["1"]["as"] == "1"


def test_pull_boxscores_refetches_live_and_keeps_finals(monkeypatch):
    from d3soccer.pipelines import national
    from d3soccer.scrapers import ncaa_national as nn

    calls = []
    monkeypatch.setattr(nn, "fetch_boxscore", lambda gid: calls.append(gid) or {"id": gid})
    now = 50 * 86400
    rows = [
        {"id": "1", "status": "final", "epoch": now},  # already stored as final: skip
        {"id": "2", "status": "live", "epoch": now},
        {"id": "3", "status": "pre", "epoch": now},  # not started: skip
        {"id": "4", "status": "final", "epoch": now},  # stored while live: fetch again
    ]
    previous = {
        "1": {"final": True, "epoch": now, "data": {"id": "1"}},
        "4": {"final": False, "epoch": now, "data": {}},
        "old": {"final": True, "epoch": 1, "data": {}},
    }
    failures = []
    out = national.pull_boxscores(previous, rows, now, failures)
    assert calls == ["2", "4"] and failures == []
    assert set(out) == {"1", "2", "4"} and out["4"]["final"] and not out["2"]["final"]
