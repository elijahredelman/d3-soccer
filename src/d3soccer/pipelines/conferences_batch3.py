"""
Batch 3: pulls a full snapshot for the remaining 26 D3 men's soccer
conferences, rounding out coverage to essentially all of D3 (40
conferences / ~344 teams total across all three pilot scripts + SCIAC).

Run this from a real host with normal outbound network access:

    uv sync
    uv run d3soccer scrape batch3

This is the biggest and messiest batch -- several conference home pages
themselves (not just individual schools) are known to block automated
fetches with a 403, which will make fetch_standings() fail for that
conference even though the team list is solid:
    MASCAC, SUNYAC, GNAC, AMCC, SCAC, C2C
Individual schools already flagged as likely to fail or need special
handling (see scrapers/conferences.py quirk notes for details):
    Penn State Brandywine/Harrisburg (msoc slug), Penn State Altoona (msoc),
    Pitt-Bradford (msoc), Transylvania (msoc), Blackburn/Eureka (msoc),
    Juniata, Moravian, Anderson, Bluffton, Schreiner, Centenary (LA),
    various Penn State branch campuses
A few conferences are intentionally incomplete pending manual domain
lookups (schools omitted rather than guessed) -- see the comment above
each TEAMS list in conferences.py: GNAC (5 schools missing), PAC (5),
ODAC (4), SCAC (7), NACC (11). Fill those in once confirmed and this
script will pick them up automatically (no code changes needed here).

That's the same signal as always: fetch the real page, look at the
markup, and adjust sidearm.py or add a per-school sport_slug override.
"""

from __future__ import annotations

import dataclasses
import json
from datetime import date

from d3soccer.config import SNAPSHOT_DIR
from d3soccer.scrapers import conferences
from d3soccer.scrapers.sidearm import fetch_roster, fetch_schedule, fetch_stats

CONFERENCE_KEYS = [
    "LEC", "NAC", "MASCAC", "Skyline", "SUNYAC", "GNAC",
    "CUNYAC", "UNITED_EAST", "ATLANTIC_EAST", "MAC_COMMONWEALTH", "MAC_FREEDOM", "LANDMARK",
    "AMCC", "PAC", "ODAC", "SAA", "SCAC",
    "USA_SOUTH", "ASC", "C2C", "HCAC", "MIAA", "NACC",
    "CCIW", "MWC", "ARC", "SLIAC", "UMAC",
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

    out_path = SNAPSHOT_DIR / f"conferences3_snapshot_{snapshot['generated']}.json"
    with open(out_path, "w") as f:
        json.dump(snapshot, f, indent=2)
    print(f"Wrote {out_path}")


if __name__ == "__main__":
    run()
