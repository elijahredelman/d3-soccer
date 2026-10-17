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


def test_compact_scoreboard_orders_live_upcoming_final():
    def game(state, home, epoch, **extra):
        side = {"names": {"short": home}, "score": "1", "conferences": [{"conferenceSeo": "sciac"}]}
        return {
            "game": {
                "gameState": state,
                "home": side,
                "away": {**side, "names": {"short": "Opp"}},
                "startTimeEpoch": str(epoch),
                **extra,
            }
        }

    payload = {
        "games": [
            game("final", "F", 1),
            game("pre", "P2", 30, startTime="7:00 PM ET"),
            game("pre", "P1", 20, startTime="4:00 PM ET"),
            game("live", "L", 10, currentPeriod="2nd", contestClock="61:00"),
        ]
    }
    rows = app_data.compact_scoreboard(payload)
    assert [r["home"] for r in rows] == ["L", "P1", "P2", "F"]
    assert rows[0]["clock"] == "2nd 61:00" and rows[0]["conf"] == "SCIAC"
    assert rows[1]["time"] == "4:00 PM ET" and "hs" not in rows[1]
    assert app_data.compact_scoreboard(None) == []


def test_compact_usc_poll_drops_previous_rank_stored_as_record():
    rows = [
        {"rank": 1, "team": "St. Olaf", "record": "1"},
        {"rank": 2, "team": "Tufts", "record": "8-1-2"},
    ]
    assert [r["rec"] for r in app_data.compact_usc_poll(rows)] == ["", "8-1-2"]
