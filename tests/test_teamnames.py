from d3soccer import teamnames


def test_clean_strips_rank_and_clinch_markers():
    assert teamnames.clean("#13Macalester College") == "Macalester College"
    assert [
        teamnames.clean(n) for n in ["Luther*", "MSOE-x", "WartburgQ", "Western Connecticut1"]
    ] == [
        "Luther",
        "MSOE",
        "Wartburg",
        "Western Connecticut",
    ]
    assert teamnames.clean("NYU") == "NYU"


def test_match_all_maps_short_names_to_registry():
    registry = [
        "Washington & Jefferson College",
        "Saint Francis University (PA)",
        "Wisconsin-Stout",
        "North Carolina Wesleyan University",
        "Randolph-Macon College",
    ]
    names = [
        "W&J",
        "Saint Francis*",
        "UW-Stout Polytechnic",
        "N.C. Wesleyan",
        "Randolph",
        "Randolph-Macon",
    ]
    assert teamnames.match_all(names, registry) == {
        "W&J": "Washington & Jefferson College",
        "Saint Francis*": "Saint Francis University (PA)",
        "UW-Stout Polytechnic": "Wisconsin-Stout",
        "N.C. Wesleyan": "North Carolina Wesleyan University",
        # Randolph is a different school; the exact match claims Randolph-Macon first.
        "Randolph-Macon": "Randolph-Macon College",
    }


def test_match_one_rejects_ambiguous_names():
    registry = ["Wisconsin-Stout", "Wisconsin-Whitewater"]
    assert teamnames.match_one("UW-Whitewater", registry) == "Wisconsin-Whitewater"
    assert teamnames.match_one("Wisconsin", registry) is None
    assert teamnames.match_one("Wisconsin Lutheran", registry) is None
