import pytest

from d3soccer import cli


def test_scrape_all_runs_national_before_conferences(monkeypatch):
    from d3soccer.pipelines import conferences, national

    calls = []
    monkeypatch.setattr(national, "run", lambda: calls.append("national"))
    monkeypatch.setattr(conferences, "run", lambda only: calls.append(("conferences", only)))
    cli.main(["scrape", "all"])
    cli.main(["scrape", "conferences", "SCIAC", "UAA"])
    assert calls == ["national", ("conferences", None), ("conferences", ["SCIAC", "UAA"])]


def test_parser_rejects_unknown_job():
    with pytest.raises(SystemExit):
        cli.build_parser().parse_args(["scrape", "nope"])
