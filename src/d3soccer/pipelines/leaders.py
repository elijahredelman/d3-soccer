"""
Quick add-on to pull national leader boards -- doesn't touch rosters/
schedules/standings, so it's fast. Run this instead of the full pilot
scripts when you just want fresh national leader boards.

Pulls:
  - individual leaders: save %, goals/gm, assists/gm, points/gm
  - team leaders: team goals/gm, total goals, total assists, team assists/gm
  - NPI rankings (once the NCAA starts publishing them for the season)

    uv run d3soccer scrape leaders
"""
from __future__ import annotations
import json
from datetime import date
from d3soccer.config import SNAPSHOT_DIR
from d3soccer.scrapers import ncaa_national

def run():
    out = {"generated": date.today().isoformat(), "leaders": {}, "team_leaders": {}, "npi_rankings": None}

    for label, stat_id in ncaa_national.STAT_CATEGORIES.items():
        print(f"Fetching individual {label} (stat_id={stat_id})...")
        try:
            out["leaders"][label] = ncaa_national.fetch_individual_stat_leaders(stat_id)
        except Exception as e:
            print(f"  {label} failed: {e}")

    for label, stat_id in ncaa_national.TEAM_STAT_CATEGORIES.items():
        print(f"Fetching team {label} (stat_id={stat_id})...")
        try:
            out["team_leaders"][label] = ncaa_national.fetch_team_stat_leaders(stat_id)
        except Exception as e:
            print(f"  team {label} failed: {e}")

    print("Fetching NPI rankings...")
    try:
        npi = ncaa_national.fetch_npi_rankings()
        out["npi_rankings"] = npi
        n_rows = len(npi.get("data", [])) if isinstance(npi, dict) else 0
        print(f"  got {n_rows} NPI rows")
        if n_rows == 0:
            print("  NPI still empty -- hasn't started publishing yet this season, that's expected, not a bug")
    except Exception as e:
        print(f"  NPI rankings failed: {e}")

    out_path = SNAPSHOT_DIR / f"leaders_snapshot_{out['generated']}.json"
    with open(out_path, "w") as f:
        json.dump(out, f, indent=2)
    print(f"Wrote {out_path}")

if __name__ == "__main__":
    run()
