import json

from d3soccer.pipelines import probe
from d3soccer.scrapers import ncaa_national


class FakeResponse:
    def __init__(self, body, content_type="text/html", status=200, url=None):
        self.text = body
        self.content = body.encode()
        self.status_code = status
        self.headers = {"content-type": content_type}
        self.url = url

    def json(self):
        return json.loads(self.text)

    def raise_for_status(self):
        if self.status_code >= 400:
            raise ncaa_national.requests.HTTPError(str(self.status_code))


def test_describe_html_reports_parser_selectors_and_tables(monkeypatch):
    html = """<html><head><title>Roster</title></head><body class="sidearm">
      <ul><li class="sidearm-roster-player">A</li><li class="sidearm-roster-player">B</li></ul>
      <table class="standings"><tr><th>Team</th><th>Conf</th></tr><tr><td>X</td></tr></table>
      <a href="/rankings/soccer-men/d3/npi">NPI</a></body></html>"""
    url = "https://x.edu/sports/mens-soccer/roster"
    monkeypatch.setattr(probe.requests, "get", lambda *a, **k: FakeResponse(html, url=url))
    out = "\n".join(probe.describe(url, links="rankings/"))
    assert "li.sidearm-roster-player=2" in out
    assert "platform hints: ['sidearm']" in out
    assert "<table class='standings' id=None> 2 rows; header: Team | Conf" in out
    assert "/rankings/soccer-men/d3/npi" in out


def test_describe_json_reports_shape(monkeypatch):
    body = json.dumps({"title": "NPI", "updated": "Oct 12", "data": [{"Rank": "1"}]})
    monkeypatch.setattr(
        probe.requests, "get", lambda *a, **k: FakeResponse(body, "application/json", url="u")
    )
    out = "\n".join(probe.describe("u"))
    assert "data rows: 1" in out and "'Oct 12'" in out


def test_failed_urls_skips_403_and_maps_names(snapshot_dir):
    snap = {
        "failures": [
            "Caltech roster: empty result",
            "Caltech schedule: empty result",
            "Bates stats: HTTPError: 403 Client Error: Forbidden",
            "SCIAC standings: empty result",
        ]
    }
    (snapshot_dir / "conferences_snapshot_2026-10-17.json").write_text(json.dumps(snap))
    urls = probe.failed_urls()
    assert urls[0] == "https://gocaltech.com/sports/mens-soccer/roster"
    assert urls[1].startswith("https://gocaltech.com/sports/mens-soccer/schedule/")
    assert urls[2] == "https://thesciac.org/standings.aspx?path=msoc"
    assert len(urls) == 3


def test_npi_falls_through_to_first_slug_with_rows(monkeypatch):
    empty, missing, good = ncaa_national.NPI_SLUGS[:3]

    def get(url, **kwargs):
        slug = url.rsplit("/", 1)[1]
        if slug == empty:
            return FakeResponse(json.dumps({"title": "old", "data": []}), "application/json")
        if slug == missing:
            return FakeResponse("", status=404)
        rows = [{"RANK": "1", "SCHOOL": slug}]
        return FakeResponse(json.dumps({"title": "NPI", "data": rows}), "application/json")

    monkeypatch.setattr(ncaa_national.requests, "get", get)
    payload = ncaa_national.fetch_npi_rankings()
    assert payload["source_slug"] == good and payload["data"][0]["SCHOOL"] == good


def test_npi_tries_regional_rankings_first():
    # ncaa.com/rankings/soccer-men/d3 redirects there and it carries the NPI column.
    assert ncaa_national.NPI_SLUGS[0] == "regional-rankings"


def test_describe_dumps_selector_and_tiny_body(monkeypatch):
    html = "<html><body><table><tbody><tr><td>X</td></tr></tbody></table></body></html>"
    monkeypatch.setattr(probe.requests, "get", lambda *a, **k: FakeResponse(html, url="u"))
    out = "\n".join(probe.describe("u", dump=["tbody tr", "li.nope"]))
    assert "dump 'tbody tr': '<tr><td>X</td></tr>'" in out
    assert "dump 'li.nope': no match" in out
    assert "body: '<html>" in out
