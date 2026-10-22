from bs4 import BeautifulSoup

from d3soccer.scrapers import sidearm


def soup(html):
    return BeautifulSoup(html, "lxml")


def test_roster_table_layout():
    page = soup(
        """<table><thead><tr><th>#</th><th>Name</th><th>Pos.</th><th>Cl.</th><th>Ht.</th>
        <th>Hometown / High School</th></tr></thead><tbody>
        <tr><td>7</td><th>Alex Kim</th><td>MF</td><td>Jr.</td><td>5'10"</td><td>Berea, Ohio / Midpark</td></tr>
        </tbody></table>"""
    )
    [p] = sidearm._parse_roster_table(page, "Baldwin Wallace")
    assert p.high_school == "Midpark"
    assert (p.number, p.name, p.position, p.class_year, p.height, p.hometown) == (
        "7",
        "Alex Kim",
        "MF",
        "Jr.",
        "5'10\"",
        "Berea, Ohio",
    )


def test_schedule_table_layout():
    page = soup(
        """<table><thead><tr><th>Date</th><th>Time</th><th>At</th><th>Opponent</th>
        <th>Location</th><th>Result</th></tr></thead><tbody>
        <tr><td>Sep 1 (Tue)</td><td>7 PM</td><td>at</td><td>Sewanee *</td><td>Sewanee, Tenn.</td>
        <td>W, 2-1</td></tr>
        <tr><td>Sep 5 (Sat)</td><td>1 PM</td><td>vs</td><td>Centre</td><td>Memphis, Tenn.</td>
        <td></td></tr></tbody></table>"""
    )
    first, second = sidearm._parse_schedule_table(page, "Rhodes")
    assert (first.opponent, first.location, first.conference_game, first.result) == (
        "Sewanee",
        "away",
        True,
        "W, 2-1",
    )
    assert (second.location, second.result, second.time) == ("home", None, "1 PM")


def test_card_layout_still_preferred():
    assert sidearm._parse_schedule_table(soup("<ul></ul>"), "X") == []
