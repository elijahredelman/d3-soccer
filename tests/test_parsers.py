"""Parser regressions, using markup captured by the Probe sites workflow on 2026-10-22."""

from bs4 import BeautifulSoup

from d3soccer.scrapers.conferences import _parse_sidearm_standings_table
from d3soccer.scrapers.sidearm import _parse_roster_html


def standings_html(headers, cells):
    """A sidearm standings table: (class, text) pairs for the header and one row."""
    th = "".join(f'<th class="{c} text-uppercase">{t}</th>' for c, t in headers)
    td = "".join(f'<td class="{c}">{t}</td>' for c, t in cells)
    return (
        '<table class="sidearm-table sidearm-standings-table">'
        f'<thead class="sidearm-primary"><tr>{th}</tr></thead><tbody><tr>{td}</tr></tbody></table>'
    )


L, M = "hide-on-large", "hide-on-medium-down"


def test_nac_institution_and_c_rec_columns():
    html = standings_html(
        [
            (L, "School"),
            (M, "Institution"),
            (L, "Overall"),
            (M, "C-PTS"),
            (L, "Conf"),
            (M, "C-GP"),
            (M, "C-REC"),
            (M, "C-W%"),
            (M, "O-GP"),
            (M, "O-REC"),
            (M, "O-W%"),
        ],
        [
            (L, "<a>Thomas</a>"),
            (
                M,
                '<div class="sidearm-standings-school-logo-container"><img alt="Thomas"/>'
                "<a>Thomas</a></div>",
            ),
            (L, "9-3"),
            (M, "15"),
            (L, "5-0"),
            (M, "5"),
            (M, "5-0"),
            (M, "1.000"),
            (M, "12"),
            (M, "9-3"),
            (M, ".750"),
        ],
    )
    [row] = _parse_sidearm_standings_table(html, "NAC")
    assert (row.team, row.conf_record, row.overall_record, row.conf_points) == (
        "Thomas",
        "5-0",
        "9-3",
        "1.000",
    )


def test_atlantic_east_schools_and_repeated_win_pct():
    html = standings_html(
        [
            (L, "Schools"),
            (M, "Schools"),
            (L, "Atlantic East"),
            (M, "AEC  Record"),
            (L, "Overall"),
            (M, "Win %"),
            (M, "Overall Record"),
            (M, "Win %"),
            (M, "Win Streak"),
            (M, "Points"),
        ],
        [
            (L, "<a>Marymount (VA)</a>"),
            (M, "<a>Marymount (VA)</a>"),
            (L, "5-0"),
            (M, "5-0"),
            (L, "9-6-1"),
            (M, "1.000"),
            (M, "9-6-1"),
            (M, ".594"),
            (M, "W5"),
            (M, "15"),
        ],
    )
    [row] = _parse_sidearm_standings_table(html, "ATLANTIC_EAST")
    # The first "Win %" is the conference one; the overall one must not overwrite it.
    assert (row.team, row.conf_record, row.overall_record, row.conf_points) == (
        "Marymount (VA)",
        "5-0",
        "9-6-1",
        "1.000",
    )


def test_sliac_long_team_header_falls_back_to_first_column():
    html = standings_html(
        [
            (L, "School"),
            (M, "School Name With Logo (link to Schedule)"),
            (L, "Conf"),
            (M, "Conf"),
            (L, "Overall"),
            (M, "CPct."),
            (M, "CPts"),
            (M, "Overall"),
            (M, "Pct."),
            (M, "Streak"),
            (M, "L10"),
        ],
        [
            (L, "<a>Webster</a>"),
            (M, '<img alt="Webster"/><a>Webster</a>'),
            (L, "6-0"),
            (M, "6-0"),
            (L, "6-2-4"),
            (M, "1.000"),
            (M, "18"),
            (M, "6-2-4"),
            (M, ".667"),
            (M, "W3"),
            (M, "6-2-2"),
        ],
    )
    [row] = _parse_sidearm_standings_table(html, "SLIAC")
    assert (row.team, row.conf_record, row.overall_record, row.conf_points) == (
        "Webster",
        "6-0",
        "6-2-4",
        "1.000",
    )


def test_existing_sciac_style_headers_unchanged():
    html = standings_html(
        [(M, "School"), (M, "CONF. W-L"), (M, "CONF. PCT"), (M, "W-L"), (M, "Pct.")],
        [(M, "Redlands"), (M, "3-0-2"), (M, ".800"), (M, "6-1-4"), (M, ".727")],
    )
    [row] = _parse_sidearm_standings_table(html, "SCIAC")
    assert (row.team, row.conf_record, row.overall_record, row.conf_points) == (
        "Redlands",
        "3-0-2",
        "6-1-4",
        ".800",
    )


def test_roster_without_jersey_numbers_baldwin_wallace():
    html = """<li class="sidearm-roster-player">
      <div class="sidearm-roster-player-position"><span class="text-bold"> GK </span>
        <span class="sidearm-roster-player-height">5'10"</span></div>
      <div class="sidearm-roster-player-name"><p></p><h3><a>Zach Abend</a></h3></div>
      <div class="sidearm-roster-player-other hide-on-large">
        <span class="sidearm-roster-player-academic-year hide-on-large">Sr.</span>
        <span class="sidearm-roster-player-hometown">Decatur, Ga.</span>
        <span class="sidearm-roster-player-highschool">Woodward Academy</span></div>
    </li>"""
    [p] = _parse_roster_html(BeautifulSoup(html, "lxml"), "Baldwin Wallace")
    assert (p.name, p.number, p.position, p.class_year, p.hometown) == (
        "Zach Abend",
        "",
        "GK",
        "Sr.",
        "Decatur, Ga.",
    )
