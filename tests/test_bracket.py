from d3soccer.pipelines import bracket


def test_committed_bracket_parses():
    out = bracket.load()
    assert out["announced"]
    for rnd in out["rounds"]:
        assert all(g["a"] for g in rnd["games"])


def test_records_after_names_and_info_line():
    out = bracket.parse(
        "# info: Final Dec. 5\n## First round\nSt. Joseph's (ME) (9-2-8) | Williams (11-2-3) | |\n"
    )
    assert out["info"] == "Final Dec. 5"
    game = out["rounds"][0]["games"][0]
    assert (game["a"], game["a_rec"]) == ("St. Joseph's (ME)", "9-2-8")
    assert (game["b"], game["b_rec"]) == ("Williams", "11-2-3")


def test_parse_rounds_groups_scores_and_byes():
    text = """
# announced: Monday, Nov. 9
# as of: Nov. 15
## First round
### Williamstown, Mass.
Williams | Bye
Amherst | Vassar | 2-1 OT | Sat., Nov. 14
Tufts | Bowdoin | 1-1 (3-4 PK) |
## Second round
Williams | Amherst | | Sun. 1 p.m.
## Empty round
"""
    out = bracket.parse(text)
    assert out["announced"] == "Monday, Nov. 9"
    assert out["updated"] == "Nov. 15"
    assert [r["name"] for r in out["rounds"]] == ["First round", "Second round"]
    bye, ot, pks = out["rounds"][0]["games"]
    assert bye == {
        "a": "Williams",
        "b": "",
        "bye": True,
        "winner": "a",
        "group": "Williamstown, Mass.",
    }
    assert ot["score"] == "2-1 OT" and ot["winner"] == "a" and ot["note"] == "Sat., Nov. 14"
    assert pks["score"] == "1-1" and pks["pk"] == "3-4" and pks["winner"] == "b"
    upcoming = out["rounds"][1]["games"][0]
    assert "winner" not in upcoming and "score" not in upcoming
    assert upcoming["note"] == "Sun. 1 p.m." and "group" not in upcoming
