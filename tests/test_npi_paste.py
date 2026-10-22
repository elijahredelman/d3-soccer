from d3soccer.pipelines import npi_paste


def test_parse_tab_separated_paste():
    text = (
        "# as of Oct 19, 2026\n"
        "Rank\tTeam\tRecord\tNPI\n"
        "1\tSt. Olaf\t13-0-2\t63.05\n"
        "2\tTufts\t11-1-2\t61.20\n"
    )
    out = npi_paste.parse(text)
    assert out["updated"] == "Oct 19, 2026"
    assert out["data"] == [
        {"Rank": "1", "Team": "St. Olaf", "Record": "13-0-2", "NPI": "63.05"},
        {"Rank": "2", "Team": "Tufts", "Record": "11-1-2", "NPI": "61.20"},
    ]


def test_parse_space_separated_paste_adds_rank_and_caps_rows():
    rows = "\n".join(f"Team {i}  10-2  {60 - i / 10:.2f}" for i in range(150))
    out = npi_paste.parse("Team  Record  NPI\n" + rows)
    assert len(out["data"]) == npi_paste.MAX_ROWS
    assert out["data"][0] == {"Rank": "1", "Team": "Team 0", "Record": "10-2", "NPI": "60.00"}


def test_template_without_a_table_falls_back_to_feed():
    assert npi_paste.parse("# instructions\n# as of\n") is None
    assert npi_paste.load() is None  # the committed data/npi.txt is just the template
