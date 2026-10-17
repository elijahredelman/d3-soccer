"""
Pulls a full snapshot for SCIAC: standings, every team's roster/schedule/
stats, national stat leaders, live scores, and the USC D3 poll. Writes
everything to data/sciac_snapshot_<date>.json.

Run this from a real host with normal outbound network access:

    pip install -r requirements.txt
    python run_sciac_pilot.py

This will fail as written the first time against any given school's site,
because the Sidearm HTML parsers in scrapers/sidearm.py are first-pass and
unverified (see README.md). Treat a failure on `fetch_roster` /
`fetch_schedule` / `fetch_stats` as a sign to open that URL, look at the
real HTML, and adjust the relevant `_parse_*_html` function or point it at
the JSON path instead.
"""

from __future__ import annotations

import dataclasses
import json
from datetime import date

from scrapers import sciac, ncaa_national
from scrapers.sidearm import fetch_roster, fetch_schedule, fetch_stats


def run():
    snapshot = {
        "generated": date.today().isoformat(),
        "conference": sciac.CONFERENCE_NAME,
        "standings": [],
        "teams": {},
        "national": {},
    }

    print("Fetching SCIAC standings...")
    try:
        standings = sciac.fetch_standings()
        snapshot["standings"] = [dataclasses.asdict(r) for r in standings]
    except Exception as e:
        print(f"  standings failed: {e}")

    for team in sciac.TEAMS:
        print(f"Fetching {team.name}...")
        team_data = {"domain": team.site_domain, "roster": [], "schedule": [], "stats": []}
        try:
            team_data["roster"] = [dataclasses.asdict(p) for p in fetch_roster(team.site_domain, team.name)]
        except Exception as e:
            print(f"  {team.name} roster failed: {e}")
        try:
            team_data["schedule"] = [dataclasses.asdict(g) for g in fetch_schedule(team.site_domain, team.name, 2026)]
        except Exception as e:
            print(f"  {team.name} schedule failed: {e}")
        try:
            team_data["stats"] = [dataclasses.asdict(p) for p in fetch_stats(team.site_domain, team.name)]
        except Exception as e:
            print(f"  {team.name} stats failed: {e}")
        snapshot["teams"][team.name] = team_data

    print("Fetching national data...")
    try:
        snapshot["national"]["scoreboard"] = ncaa_national.fetch_scoreboard()
    except Exception as e:
        print(f"  scoreboard failed: {e}")
    try:
        snapshot["national"]["save_pct_leaders"] = ncaa_national.fetch_individual_stat_leaders(421)
    except Exception as e:
        print(f"  stat leaders failed: {e}")
    try:
        snapshot["national"]["usc_poll"] = ncaa_national.fetch_united_soccer_coaches_poll()
    except Exception as e:
        print(f"  USC poll failed: {e}")

    out_path = f"data/sciac_snapshot_{snapshot['generated']}.json"
    with open(out_path, "w") as f:
        json.dump(snapshot, f, indent=2)
    print(f"Wrote {out_path}")


if __name__ == "__main__":
    run()
