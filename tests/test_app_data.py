from d3soccer.pipelines import app_data


def test_compact_stats_splits_keepers_and_sorts_scorers():
    players = [
        {"name": "A", "position": "F", "games_played": 5, "goals": 1, "assists": 0, "points": 2},
        {"name": "B", "position": "M", "games_played": 5, "goals": 3, "assists": 1, "points": 7},
        {"name": "K", "position": "GK", "games_played": 5, "minutes": 450, "saves": 20},
        {"name": "Bench", "position": "D"},
    ]
    out = app_data.compact_stats(players)
    assert [s["name"] for s in out["scorers"]] == ["B", "A"]
    assert [k["name"] for k in out["keepers"]] == ["K"]


def test_compact_schedule_drops_empty_fields():
    games = [{"date": "Sep 1", "opponent": "Caltech", "location": "home", "conference_game": True}]
    assert app_data.compact_schedule(games) == [
        {"d": "Sep 1", "opp": "Caltech", "where": "home", "note": "Conf"}
    ]


def test_compact_standings_skips_blank_rows():
    rows = [{"team": "Redlands", "conf_record": "3-0-2", "overall_record": "6-1-4"}, {"team": ""}]
    assert app_data.compact_standings(rows) == [
        {"name": "Redlands", "confRec": "3-0-2", "overallRec": "6-1-4", "confPct": None}
    ]


def test_committed_snapshots_cover_every_conference():
    teams, standings, sites = app_data.load_all()
    assert set(app_data.DISPLAY_ORDER) <= set(standings)
    assert "Occidental" in teams and sites["Occidental"] == "oxyathletics.com"
