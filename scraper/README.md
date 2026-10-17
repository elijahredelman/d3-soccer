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

- `models.py` — shared data shapes (Team, Player, Game, StandingRow)
- `scrapers/sidearm.py` — generic scraper for any Sidearm-template team site
  (roster / schedule / stats), reusable across schools and, eventually,
  across conferences
- `scrapers/sciac.py` — SCIAC team registry (the 10 domains) + conference
  standings scraper
- `scrapers/ncaa_national.py` — national stat leaders, live scores, and the
  United Soccer Coaches D3 poll (all already confirmed working)
- `run_sciac_pilot.py` — orchestrates a full pull for SCIAC and writes JSON
  to `data/`
- `data/sciac_snapshot_2026-09-18.json` — a real snapshot, hand-verified
  against live pages during this session (standings for all 10 teams, full
  Occidental roster/schedule/stats, partial rosters for Chapman and
  Pomona-Pitzer)

## Running it for real

1. Deploy this to any host with normal outbound internet (a small VPS,
   Vercel/Render/Fly, etc.) — not this sandbox.
2. `pip install -r requirements.txt`
3. Fetch one live page (`curl https://oxyathletics.com/sports/mens-soccer/roster`)
   and compare its actual HTML to the selectors in `sidearm.py`; adjust.
4. `python run_sciac_pilot.py` to pull everything and write `data/*.json`.
5. Once this is solid for SCIAC, add conferences one at a time by adding
   entries to a `CONFERENCES` registry modeled on `sciac.py`.
