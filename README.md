# d3-soccer

Collect and analyze NCAA Division III soccer data.

## Layout

```
src/d3soccer/
  config.py      paths and scraper settings
  models.py      Team / Game dataclasses
  scrapers/      data-source scrapers (base class handles rate limiting + caching)
  storage.py     SQLite persistence
  analysis/      standings and other analysis
  cli.py         `d3soccer` command-line entry point
data/raw/        cached HTML from scrapers (gitignored)
data/processed/  derived datasets (gitignored)
notebooks/       exploratory analysis
tests/
```

## Setup

Requires Python 3.11+ and [uv](https://docs.astral.sh/uv/).

```sh
uv sync
uv run d3soccer init-db
uv run pytest
uv run ruff check . && uv run ruff format .
```
