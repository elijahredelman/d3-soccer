# D3 Soccer App — data pipeline (SCIAC pilot)

This is the first real (non-sample) data pipeline for the app, scoped to one
conference — SCIAC — to prove out the scraping approach before building it
for all ~400+ D3 men's soccer teams.

## What this proves

All 10 SCIAC schools' athletics sites, plus the conference site itself, run
on the same "SIDEARM Sites" platform template. Confirmed by live fetches
against 5 of the 10 schools (Occidental, Chapman, Redlands, Pomona-Pitzer,
Claremont-Mudd-Scripps) on 2026-09-18:

- Every team site exposes the same URL shape:
  `https://<school-domain>/sports/mens-soccer/roster`
  `https://<school-domain>/sports/mens-soccer/schedule/<year>`
  `https://<school-domain>/sports/mens-soccer/stats`
- The conference site (thesciac.org) exposes current-season standings at a
  stable URL that doesn't need a per-season ID:
  `https://thesciac.org/standings.aspx?path=msoc`
  The same `standings.aspx?path=msoc` pattern showed up in search results
  for several *other* D3 conferences (ACC, SLIAC, SSAC, SAC, CACC, GSAC),
  which suggests this generalizes well beyond SCIAC — worth testing next.
- National stat leaders and live scores come from ncaa.com's own JSON feed
  (via the free third-party wrapper `ncaa-api.henrygd.me` documented at
  github.com/henrygd/ncaa-api) — this part already works across all of D3,
  not just SCIAC.

## What's still open

- NPI rankings haven't published yet this season (confirmed empty as of
  2026-09-18). United Soccer Coaches D3 Top 25 is live now and is being used
  as the stand-in in the app until NPI publishes.
- "Where to watch" has no scrapable source anywhere — stays manual/directory
  data, not pulled by these scrapers.
- The exact HTML/JSON structure of each Sidearm page (table markup, CSS
  classes, or whether data ships as embedded JSON) was read here through a
  research/rendering tool, not a raw HTTP client — so the extraction
  functions below encode the *fields and URLs* confirmed live, but the CSS
  selectors are first-pass and need to be checked against real page source
  once this runs somewhere with open outbound network access. This sandbox's
  shell can't reach these domains directly (only the research tools can), so
  the scrapers here are untested end-to-end — treat `sidearm.py`'s selectors
  as a starting point to adjust against real HTML, not as verified code.

## Layout

Paths are relative to the repo root.

- `src/d3soccer/models.py` — shared data shapes (Team, Player, Game, StandingRow)
- `src/d3soccer/scrapers/sidearm.py` — generic scraper for any Sidearm-template team site
  (roster / schedule / stats), reusable across schools and conferences
- `src/d3soccer/scrapers/sciac.py` — SCIAC team registry (the 10 domains) + conference
  standings scraper
- `src/d3soccer/scrapers/conferences.py` — team registries and standings for the other
  conferences
- `src/d3soccer/scrapers/ncaa_national.py` — national stat leaders, live scores, and the
  United Soccer Coaches D3 poll
- `src/d3soccer/pipelines/conferences.py` — pulls every conference (or the ones
  named) into one `conferences_snapshot_<date>.json`; failed or empty fetches keep
  the team's previous data and are listed under `stale` / `failures`
- `src/d3soccer/pipelines/national.py` — leaders, team leaders, NPI, scoreboard and
  the coaches' poll into `national_snapshot_<date>.json`, same carry-forward rule
- `src/d3soccer/pipelines/app_data.py` — turns the newest snapshots into
  `web/app_data.js`
- `data/snapshots/` — only the newest file per family is kept; older ones are in git
  history. The `sciac`, `conferences2/3` and `leaders` files from the pilot scripts
  are still read, and get pruned the first time the new jobs run.

## Running it for real

1. Run on any host with normal outbound internet (a small VPS, a CI runner, etc.).
2. `uv sync`
3. Fetch one live page (`curl https://oxyathletics.com/sports/mens-soccer/roster`)
   and compare its actual HTML to the selectors in `sidearm.py`; adjust.
4. `uv run d3soccer scrape conferences SCIAC` to pull one conference, or
   `scrape national` / `scrape conferences` / `scrape all`. In production the
   Refresh data workflow runs these on a schedule (see the README).
5. `uv run d3soccer build` to regenerate `web/app_data.js`, then
   `uv run d3soccer serve` to view the site.
6. Add conferences one at a time by adding entries to the `CONFERENCES` registry in
   `conferences.py`.
