"""
Pulls a full snapshot for the "most competitive/watched" batch of D3 men's
soccer conferences: NESCAC, UAA, MIAC, WIAC, Northwest Conference. Same
shape and same run instructions as pipelines/sciac.py -- this is the
second pass, expanding the same proven Sidearm-based pattern to new
conferences instead of writing new scraper code per conference.

Run this from a real host with normal outbound network access:

    uv sync
    uv run d3soccer scrape batch1

A handful of schools are known in advance to deviate from the standard
Sidearm URL pattern (see scrapers/conferences.py quirk notes: Carnegie
Mellon, Concordia-Moorhead, Whitman, Willamette) -- expect those four to
fail on this first run. That's the same signal as always: fetch that
school's real page, look at the markup, and adjust.
"""

from __future__ import annotations

import dataclasses
import json
from datetime import date

from d3soccer.config import SNAPSHOT_DIR
from d3soccer.scrapers import conferences, ncaa_national
from d3soccer.scrapers.sidearm import fetch_roster, fetch_schedule, fetch_stats

CONFERENCE_KEYS = ["NESCAC", "UAA", "MIAC", "WIAC", "Northwest Conference"]


def run():
    snapshot = {
        "generated": date.today().isoformat(),
        "conferences": {},
        "national": {},
    }

    for conf_key in CONFERENCE_KEYS:
        print(f"=== {conf_key} ===")
        conf_data = {"standings": [], "teams": {}}

        print(f"Fetching {conf_key} standings...")
        try:
            if conf_key == "NESCAC":
                rows = conferences.fetch_nescac_standings()
            else:
                rows = conferences.fetch_standings(conf_key)
            conf_data["standings"] = [dataclasses.asdict(r) for r in rows]
        except Exception as e:
            print(f"  {conf_key} standings failed: {e}")

        for team in conferences.CONFERENCES[conf_key]["teams"]:
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
            conf_data["teams"][team.name] = team_data

        snapshot["conferences"][conf_key] = conf_data

    print("Fetching national data (scoreboard only -- leaders/USC poll already covered by the SCIAC pilot)...")
    try:
        snapshot["national"]["scoreboard"] = ncaa_national.fetch_scoreboard()
    except Exception as e:
        print(f"  scoreboard failed: {e}")

    out_path = SNAPSHOT_DIR / f"conferences_snapshot_{snapshot['generated']}.json"
    with open(out_path, "w") as f:
        json.dump(snapshot, f, indent=2)
    print(f"Wrote {out_path}")


if __name__ == "__main__":
    run()
