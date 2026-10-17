import importlib

import pytest

from d3soccer import cli


@pytest.mark.parametrize("module", cli.SCRAPE_JOBS.values())
def test_every_scrape_job_has_a_run_function(module):
    assert callable(importlib.import_module(f"d3soccer.pipelines.{module}").run)


def test_parser_rejects_unknown_job():
    with pytest.raises(SystemExit):
        cli.build_parser().parse_args(["scrape", "nope"])
