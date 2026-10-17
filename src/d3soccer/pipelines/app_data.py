"""
Turns the newest snapshots into web/app_data.js, a set of lookup objects the
site reads directly:

  REAL_ROSTERS      team name -> {players, total, partial}
  REAL_SCHEDULES    team name -> [games]
  REAL_STATS        team name -> {scorers, keepers}
  REAL_STANDINGS    conference name -> [ {name, confRec, overallRec, confPct} ]
  REAL_SITES        team name -> athletics site domain
  REAL_CONFERENCES  [conference names present, in a sensible display order]
  REAL_LEADERS      individual national leader category -> raw NCAA-API payload
  REAL_TEAM_LEADERS team-level national leader category -> raw NCAA-API payload
  REAL_NPI          raw NCAA-API NPI payload ({updated, data: [...]}) or null
  REAL_SCOREBOARD   [ {status, home, away, hs, as, conf, time, clock} ] for today
  REAL_USC_POLL     [ {rank, team, rec} ] United Soccer Coaches Top 25
  REAL_META         {conferencesDate, nationalFetchedAt, nationalDate, built}

    uv run d3soccer build
"""

import json
import re
from datetime import UTC, datetime

from d3soccer.config import APP_DATA_JS
from d3soccer.pipelines import snapshots

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


def load_all():
    """
    Returns (teams, standings_by_conf, sites) merged from the newest conference
    snapshots, newer files overriding older ones.
    """
    teams, standings_by_conf, sites = {}, {}, {}
    for path in snapshots.latest_per_family(snapshots.CONFERENCE_FAMILIES):
        print(f"Loading {path}")
        snap = snapshots.load(path)
        if "conference" in snap:  # legacy single-conference SCIAC file
            confs = {snap["conference"]: snap}
        else:
            confs = snap.get("conferences", {})
        for conf_name, cdata in confs.items():
            for name, t in cdata.get("teams", {}).items():
                teams[name] = t
                sites[name] = t.get("domain")
            standings_by_conf[conf_name] = cdata.get("standings", [])
    return teams, standings_by_conf, sites


def load_national():
    """Merged national data: leaders, team_leaders, npi_rankings, scoreboard, usc_poll."""
    from d3soccer.pipelines.national import previous_state

    return previous_state()


def conferences_date():
    paths = snapshots.latest_per_family(snapshots.CONFERENCE_FAMILIES)
    return re.search(r"\d{4}-\d{2}-\d{2}", paths[-1].name).group(0) if paths else None


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


def compact_scoreboard(payload):
    """Today's games from the NCAA scoreboard feed: live first, then upcoming, then final."""
    games = []
    for item in (payload or {}).get("games", []):
        g = item.get("game", {})
        home, away = g.get("home", {}), g.get("away", {})
        confs = (home.get("conferences") or [{}])[0]
        status = g.get("gameState") or "pre"
        row = {
            "status": status,
            "home": home.get("names", {}).get("short", ""),
            "away": away.get("names", {}).get("short", ""),
            "epoch": int(g.get("startTimeEpoch") or 0),
            "date": g.get("startDate", ""),  # MM/DD/YYYY
        }
        if status != "pre":
            row["hs"], row["as"] = home.get("score", ""), away.get("score", "")
        else:
            row["time"] = g.get("startTime") or "TBA"
        if status == "live":
            row["clock"] = " ".join(x for x in (g.get("currentPeriod"), g.get("contestClock")) if x)
        if confs.get("conferenceSeo"):
            row["conf"] = confs["conferenceSeo"].replace("-", " ").upper()
        games.append(row)
    order = {"live": 0, "pre": 1, "final": 2}
    games.sort(key=lambda r: (order.get(r["status"], 1), r["epoch"]))
    return games


RECORD = re.compile(r"^\d+-\d+(-\d+)?$")


def compact_usc_poll(rows):
    out = []
    for r in rows or []:
        # Older snapshots stored the previous rank under "record"; keep only real W-L(-T).
        rec = r.get("record") or ""
        out.append({"rank": r["rank"], "team": r["team"], "rec": rec if RECORD.match(rec) else ""})
    return out


def _js(name, value):
    return f"const {name} = " + json.dumps(value, separators=(",", ":"), ensure_ascii=False) + ";\n"


def run():
    teams, standings_by_conf, sites = load_all()
    national = load_national()

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

    npi = national.get("npi_rankings")
    meta = {
        "conferencesDate": conferences_date(),
        "nationalFetchedAt": national.get("fetched_at"),
        "nationalDate": national.get("generated"),
        "built": datetime.now(UTC).isoformat(timespec="seconds"),
    }

    APP_DATA_JS.parent.mkdir(parents=True, exist_ok=True)
    with open(APP_DATA_JS, "w", encoding="utf-8") as f:
        f.write("// Auto-generated by `d3soccer build` from data/snapshots -- do not edit.\n")
        f.write(_js("REAL_ROSTERS", rosters))
        f.write(_js("REAL_SCHEDULES", schedules))
        f.write(_js("REAL_STATS", stats))
        f.write(_js("REAL_STANDINGS", standings))
        f.write(_js("REAL_SITES", sites))
        f.write(_js("REAL_CONFERENCES", ordered_confs))
        f.write(_js("REAL_LEADERS", national.get("leaders", {})))
        f.write(_js("REAL_TEAM_LEADERS", national.get("team_leaders", {})))
        f.write(_js("REAL_NPI", npi if npi and npi.get("data") else None))
        f.write(_js("REAL_SCOREBOARD", compact_scoreboard(national.get("scoreboard"))))
        f.write(_js("REAL_USC_POLL", compact_usc_poll(national.get("usc_poll"))))
        f.write(_js("REAL_META", meta))

    print(f"{len(rosters)} rosters, {len(schedules)} schedules, {len(stats)} team-stat sets")
    print(
        f"{len(standings)} conferences with standings, "
        f"{sum(len(v) for v in standings.values())} standings rows total"
    )
    print(f"Wrote {APP_DATA_JS} ({APP_DATA_JS.stat().st_size:,} bytes)")
