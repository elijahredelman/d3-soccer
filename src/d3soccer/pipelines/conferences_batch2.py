"""
Batch 2: pulls a full snapshot for 7 more D3 men's soccer conferences --
Liberty League, Centennial, Empire 8, OAC, NCAC, NJAC, NEWMAC. Same shape
as pipelines/conferences_batch1.py (batch 1: NESCAC/UAA/MIAC/WIAC/Northwest).

Run this from a real host with normal outbound network access:

    uv sync
    uv run d3soccer scrape batch2

Schools already flagged as likely to fail on this first run (known URL-
pattern deviations or fetch-blocking found during research -- see
scrapers/conferences.py quirk notes above each conference's TEAMS list):
  - Dickinson (Centennial): uses the short "msoc" sport-slug
  - Russell Sage (Empire 8): old URL scheme + blocks automated fetches
  - Muskingum, Ohio Northern (OAC): block automated fetches
  - Wittenberg (NCAC): blocks automated fetches
  - William Paterson (NJAC): blocked by robots.txt

That's the same signal as always: fetch that school's real page, look at
the markup, and adjust sidearm.py or add a per-school override.
"""

from __future__ import annotations

import dataclasses
import json
from datetime import date

from d3soccer.config import SNAPSHOT_DIR
from d3soccer.scrapers import conferences
from d3soccer.scrapers.sidearm import fetch_roster, fetch_schedule, fetch_stats

CONFERENCE_KEYS = [
    "Liberty League",
    "Centennial",
    "Empire 8",
    "OAC",
    "NCAC",
    "NJAC",
    "NEWMAC",
]


def run():
    snapshot = {
        "generated": date.today().isoformat(),
        "conferences": {},
    }

    for conf_key in CONFERENCE_KEYS:
        print(f"=== {conf_key} ===")
        conf_data = {"standings": [], "teams": {}}

        print(f"Fetching {conf_key} standings...")
        try:
            rows = conferences.fetch_standings(conf_key)
            conf_data["standings"] = [dataclasses.asdict(r) for r in rows]
        except Exception as e:
            print(f"  {conf_key} standings failed: {e}")

        for team in conferences.CONFERENCES[conf_key]["teams"]:
            print(f"Fetching {team.name}...")
            team_data = {"domain": team.site_domain, "roster": [], "schedule": [], "stats": []}
            try:
                team_data["roster"] = [dataclasses.asdict(p) for p in fetch_roster(team.site_domain, team.name, team.sport_slug)]
            except Exception as e:
                print(f"  {team.name} roster failed: {e}")
            try:
                team_data["schedule"] = [dataclasses.asdict(g) for g in fetch_schedule(team.site_domain, team.name, 2026, team.sport_slug)]
            except Exception as e:
                print(f"  {team.name} schedule failed: {e}")
            try:
                team_data["stats"] = [dataclasses.asdict(p) for p in fetch_stats(team.site_domain, team.name, team.sport_slug)]
            except Exception as e:
                print(f"  {team.name} stats failed: {e}")
            conf_data["teams"][team.name] = team_data

        snapshot["conferences"][conf_key] = conf_data

    out_path = SNAPSHOT_DIR / f"conferences2_snapshot_{snapshot['generated']}.json"
    with open(out_path, "w") as f:
        json.dump(snapshot, f, indent=2)
    print(f"Wrote {out_path}")


if __name__ == "__main__":
    run()
