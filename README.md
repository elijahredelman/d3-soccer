# d3-soccer

**Pitch Sheet** is a site for NCAA Division III men's soccer: rosters, schedules, team
stats, standings for all 41 conferences, and national stat leaders. This repo holds the
data pipeline that scrapes it and the static site that shows it.

Live at **https://elijahredelman.github.io/d3-soccer/**.

## Layout

```
src/d3soccer/
  models.py        Team / Player / Game / StandingRow
  scrapers/        Sidearm team sites, conference standings, NCAA national feeds
  pipelines/       conferences.py and national.py (scrape -> snapshot),
                   app_data.py (snapshots -> web/app_data.js), snapshots.py (file helpers)
  config.py        repo paths
  cli.py           the `d3soccer` command
data/snapshots/    newest JSON snapshot per family (older ones live in git history)
web/index.html     the site; app_data.js next to it is generated, not committed
docs/pipeline.md   scraping approach, what's verified, what's still open
tests/
```

Data flows one way: **scrapers → `data/snapshots/` → `d3soccer build` → `web/app_data.js` → `web/index.html`**.

## How the site stays up to date

Two GitHub Actions workflows in `.github/workflows/`:

- **Refresh data** (`refresh.yml`) scrapes national data (scores, leaders, NPI,
  coaches' poll) every 2 hours and everything, including all 41 conferences'
  standings, rosters, schedules and stats, daily at 2:41am Pacific. It commits the
  new snapshots to `main`, then redeploys the site. Run it by hand from the
  **Actions** tab → **Refresh data** → **Run workflow**. Each run's page lists any
  fetches that failed; those teams keep their previous data instead of going blank.
- **Probe sites** (`probe.yml`, run by hand) fetches the pages a refresh failed on and
  logs their markup (platform, tables, which parser selectors match), for fixing
  scrapers against the real HTML. Same as `d3soccer probe --failed` locally.
- **Deploy site** (`pages.yml`) builds `app_data.js` and publishes `web/` to GitHub
  Pages on every push to `main`.

## Usage

Requires Python 3.11+ and [uv](https://docs.astral.sh/uv/).

```sh
uv sync
uv run d3soccer scrape national               # scores, leaders, NPI, poll (needs open internet)
uv run d3soccer scrape conferences            # all conferences; or e.g. `conferences SCIAC UAA`
uv run d3soccer scrape all
uv run d3soccer build                         # regenerate web/app_data.js from data/snapshots
uv run d3soccer serve                         # http://127.0.0.1:8000
uv run d3soccer probe --failed                # describe pages the last refresh failed on
uv run d3soccer probe --standings all         # run the standings parser on every conference, print rows
uv run pytest
uv run ruff check . && uv run ruff format .
```

See [docs/pipeline.md](docs/pipeline.md) for how the scrapers work and their known gaps.
