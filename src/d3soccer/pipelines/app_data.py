"""
Reads every real data snapshot we've pulled so far (SCIAC, batch 1/2/3
conferences, national leaders) and emits a single compact JS file
(app_data.js) with lookup objects for the Pitch Sheet prototype:

  REAL_ROSTERS     team name -> {players, total, partial}
  REAL_SCHEDULES   team name -> [games]
  REAL_STATS       team name -> {scorers, keepers}
  REAL_STANDINGS    conference name -> [ {name, confRec, overallRec, confPct} ]
  REAL_SITES        team name -> athletics site domain
  REAL_CONFERENCES  [conference names present, in a sensible display order]
  REAL_LEADERS      individual national leader category -> raw NCAA-API payload
  REAL_TEAM_LEADERS team-level national leader category -> raw NCAA-API payload

Run this after any pilot script finishes to regenerate app_data.js with
whatever's newest. It always prefers the most recent dated snapshot file
for the same conference set if more than one exists.
"""

import glob
import json
import os
import re

from d3soccer.config import APP_DATA_JS, SNAPSHOT_DIR

DISPLAY_ORDER = [
    "SCIAC",
    "NESCAC",
    "UAA",
    "MIAC",
    "WIAC",
    "Northwest Conference",
    "Liberty League",
    "Centennial",
    "Empire 8",
    "OAC",
    "NCAC",
    "NJAC",
    "NEWMAC",
    "LEC",
    "NAC",
    "MASCAC",
    "Skyline",
    "SUNYAC",
    "GNAC",
    "CUNYAC",
    "UNITED_EAST",
    "ATLANTIC_EAST",
    "MAC_COMMONWEALTH",
    "MAC_FREEDOM",
    "LANDMARK",
    "AMCC",
    "PAC",
    "ODAC",
    "SAA",
    "SCAC",
    "USA_SOUTH",
    "ASC",
    "C2C",
    "HCAC",
    "MIAA",
    "NACC",
    "CCIW",
    "MWC",
    "ARC",
    "SLIAC",
    "UMAC",
]


def _latest(pattern):
    """Return the path with the latest YYYY-MM-DD date in its filename, or None."""
    matches = glob.glob(pattern)
    if not matches:
        return None

    def date_key(path):
        m = re.search(r"(\d{4}-\d{2}-\d{2})", path)
        return m.group(1) if m else ""

    return sorted(matches, key=date_key)[-1]


def load_all():
    """
    Returns (teams, standings_by_conf, sites).
    teams: team name -> {roster, schedule, stats}
    standings_by_conf: conference name -> list of StandingRow dicts
    sites: team name -> site domain
    """
    teams = {}
    standings_by_conf = {}
    sites = {}

    sciac_path = _latest(str(SNAPSHOT_DIR / "sciac_snapshot_*.json"))
    if sciac_path:
        print(f"Loading {sciac_path}")
        sciac = json.load(open(sciac_path))
        for name, t in sciac.get("teams", {}).items():
            teams[name] = t
            sites[name] = t.get("domain")
        standings_by_conf["SCIAC"] = sciac.get("standings", [])

    # batch 1 is a dated "conferences_snapshot", batches 2/3 are
    # "conferences2_snapshot" / "conferences3_snapshot" -- glob each
    # family separately so a newer batch-1 re-run doesn't get shadowed by
    # batch 2/3 files matching the same loose pattern.
    for family in (
        "conferences_snapshot_*.json",
        "conferences2_snapshot_*.json",
        "conferences3_snapshot_*.json",
    ):
        path = _latest(str(SNAPSHOT_DIR / family))
        if not path:
            continue
        print(f"Loading {path}")
        conf = json.load(open(path))
        for conf_name, cdata in conf.get("conferences", {}).items():
            for name, t in cdata.get("teams", {}).items():
                teams[name] = t
                sites[name] = t.get("domain")
            standings_by_conf[conf_name] = cdata.get("standings", [])

    return teams, standings_by_conf, sites


def load_leaders():
    path = _latest(str(SNAPSHOT_DIR / "leaders_snapshot_*.json"))
    if not path:
        return {}, {}
    print(f"Loading {path}")
    d = json.load(open(path))
    return d.get("leaders", {}), d.get("team_leaders", {})


def compact_roster(players):
    out = []
    for p in players:
        row = {"num": p["number"], "name": p["name"], "pos": p["position"], "cl": p["class_year"]}
        if p.get("hometown"):
            row["hometown"] = p["hometown"]
        out.append(row)
    return out


def compact_schedule(games):
    out = []
    for g in games:
        row = {"d": g["date"], "opp": g["opponent"], "where": g["location"]}
        if g.get("conference_game"):
            row["note"] = "Conf"
        if g.get("result"):
            row["result"] = g["result"]
        if g.get("venue"):
            row["venue"] = g["venue"]
        if g.get("time"):
            row["time"] = g["time"]
        out.append(row)
    return out


def compact_stats(players):
    scorers, keepers = [], []
    for p in players:
        if p.get("position") == "GK" or p.get("saves") is not None:
            keepers.append(
                {
                    "name": p["name"],
                    "gp": p.get("games_played"),
                    "min": p.get("minutes"),
                    "ga": p.get("goals_against"),
                    "sv": p.get("saves"),
                    "pct": p.get("save_pct"),
                }
            )
        elif p.get("goals") is not None or p.get("points") is not None:
            scorers.append(
                {
                    "name": p["name"],
                    "gp": p.get("games_played"),
                    "g": p.get("goals"),
                    "a": p.get("assists"),
                    "pts": p.get("points"),
                }
            )
    scorers.sort(key=lambda r: r["pts"] or 0, reverse=True)
    return {"scorers": scorers[:12], "keepers": keepers[:4]}


def compact_standings(rows):
    out = []
    for r in rows:
        if not r.get("team"):
            continue
        out.append(
            {
                "name": r["team"],
                "confRec": r.get("conf_record") or "",
                "overallRec": r.get("overall_record") or "",
                "confPct": r.get("conf_points"),
            }
        )
    return out


def run():
    teams, standings_by_conf, sites = load_all()
    leaders, team_leaders = load_leaders()

    rosters, schedules, stats = {}, {}, {}
    for name, t in teams.items():
        if t.get("roster"):
            rosters[name] = {
                "players": compact_roster(t["roster"]),
                "total": len(t["roster"]),
                "partial": False,
            }
        if t.get("schedule"):
            schedules[name] = compact_schedule(t["schedule"])
        if t.get("stats"):
            s = compact_stats(t["stats"])
            if s["scorers"] or s["keepers"]:
                stats[name] = s

    standings = {conf: compact_standings(rows) for conf, rows in standings_by_conf.items()}

    # Order conferences by DISPLAY_ORDER, then anything unexpected at the end.
    present = set(standings.keys())
    ordered_confs = [c for c in DISPLAY_ORDER if c in present]
    ordered_confs += sorted(present - set(ordered_confs))

    with open(APP_DATA_JS, "w") as f:
        f.write(
            "// Auto-generated from real scraped data -- see src/d3soccer/pipelines/app_data.py (`d3soccer build`)\n"
        )
        f.write("const REAL_ROSTERS = " + json.dumps(rosters, separators=(",", ":")) + ";\n")
        f.write("const REAL_SCHEDULES = " + json.dumps(schedules, separators=(",", ":")) + ";\n")
        f.write("const REAL_STATS = " + json.dumps(stats, separators=(",", ":")) + ";\n")
        f.write("const REAL_STANDINGS = " + json.dumps(standings, separators=(",", ":")) + ";\n")
        f.write("const REAL_SITES = " + json.dumps(sites, separators=(",", ":")) + ";\n")
        f.write(
            "const REAL_CONFERENCES = " + json.dumps(ordered_confs, separators=(",", ":")) + ";\n"
        )
        f.write("const REAL_LEADERS = " + json.dumps(leaders, separators=(",", ":")) + ";\n")
        f.write(
            "const REAL_TEAM_LEADERS = " + json.dumps(team_leaders, separators=(",", ":")) + ";\n"
        )

    print(f"{len(rosters)} rosters, {len(schedules)} schedules, {len(stats)} team-stat sets")
    print(
        f"{len(standings)} conferences with standings, {sum(len(v) for v in standings.values())} standings rows total"
    )
    print("file size:", os.path.getsize(APP_DATA_JS), "bytes")


if __name__ == "__main__":
    run()
