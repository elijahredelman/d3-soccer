# d3-soccer

**Pitch Sheet** is a site for NCAA Division III men's soccer: rosters, schedules, team
stats, standings for all 41 conferences, and national stat leaders. This repo holds the
data pipeline that scrapes it and the static site that shows it.

## Layout

```
src/d3soccer/
  models.py        Team / Player / Game / StandingRow
  scrapers/        Sidearm team sites, conference standings, NCAA national feeds
  pipelines/       pull jobs (write data/snapshots/*.json) and the app_data.js builder
  config.py        repo paths
  cli.py           the `d3soccer` command
data/snapshots/    dated JSON snapshots of real scraped data (committed)
web/               the static site: index.html + generated app_data.js
docs/pipeline.md   scraping approach, what's verified, what's still open
tests/
```

Data flows one way: **scrapers → `data/snapshots/` → `d3soccer build` → `web/app_data.js` → `web/index.html`**.
`web/` is self-contained, so any static host (GitHub Pages, Netlify, Cloudflare Pages) can serve it as is.

## Usage

Requires Python 3.11+ and [uv](https://docs.astral.sh/uv/).

```sh
uv sync
uv run d3soccer scrape sciac      # or batch1 | batch2 | batch3 | leaders | all (needs open internet)
uv run d3soccer build             # regenerate web/app_data.js from the latest snapshots
uv run d3soccer serve             # http://127.0.0.1:8000
uv run pytest
uv run ruff check . && uv run ruff format .
```

See [docs/pipeline.md](docs/pipeline.md) for how the scrapers work and their known gaps.
