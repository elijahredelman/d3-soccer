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

from d3soccer import teamnames
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
    Returns (teams, standings_by_conf, sites, conf_teams) merged from the newest
    conference snapshots, newer files overriding older ones. conf_teams maps each
    conference to its registry team names.
    """
    teams, standings_by_conf, sites, conf_teams = {}, {}, {}, {}
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
            conf_teams[conf_name] = list(cdata.get("teams", {}))
    return teams, standings_by_conf, sites, conf_teams


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


RESULT = re.compile(r"^([WLT]),")


def schedule_records(team: str, games: list[dict], conf_teams: list[str]) -> tuple[str, str]:
    """(overall, conference) W-L-T from a team's scraped schedule results."""
    overall, conf = [0, 0, 0], [0, 0, 0]
    others = [t for t in conf_teams if t != team]
    for g in games:
        m = RESULT.match(g.get("result") or "")
        if not m:
            continue
        i = "WLT".index(m.group(1))
        overall[i] += 1
        if teamnames.match_one(g.get("opponent", ""), others):
            conf[i] += 1

    def fmt(r):
        return "-".join(map(str, r if r[2] else r[:2])) if any(r) else ""

    return fmt(overall), fmt(conf)


def compact_standings(rows, teams=None):
    """
    Standings rows for the site, named with our registry names so the team page
    finds that team's roster/schedule/stats. `teams` (registry name -> scraped
    team data) also fills in what the conference page lacked: registry teams
    missing from the standings, and conference records the parser couldn't read,
    both computed from scraped schedule results.
    """
    teams = teams or {}
    registry = list(teams)
    rows = [r for r in rows if r.get("team")]
    names = teamnames.match_all([r["team"] for r in rows], registry)

    out = []
    for r in rows:
        name = names.get(r["team"], teamnames.clean(r["team"]))
        conf_rec, conf_pct = r.get("conf_record") or "", r.get("conf_points")
        overall_rec = r.get("overall_record") or ""
        if name in teams and not (conf_rec and overall_rec):
            overall, conf = schedule_records(name, teams[name].get("schedule", []), registry)
            overall_rec = overall_rec or overall
            if not conf_rec:
                # A pct without a conference record is the overall pct, mis-read.
                conf_rec, conf_pct = conf, None
        out.append(
            {"name": name, "confRec": conf_rec, "overallRec": overall_rec, "confPct": conf_pct}
        )

    missing = [t for t in registry if t not in names.values()]
    extra = []
    for name in missing:
        overall, conf = schedule_records(name, teams[name].get("schedule", []), registry)
        extra.append({"name": name, "confRec": conf, "overallRec": overall, "confPct": None})
    extra.sort(key=lambda r: (-_pct(r["confRec"]), -_pct(r["overallRec"]), r["name"]))
    return out + extra


def _pct(rec: str) -> float:
    parts = [int(x) for x in rec.split("-")] if rec else []
    if len(parts) < 2:
        return -1.0
    wins, losses, ties = parts[0], parts[1], parts[2] if len(parts) > 2 else 0
    games = wins + losses + ties
    return (wins + ties / 2) / games if games else -1.0


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
    teams, standings_by_conf, sites, conf_teams = load_all()
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

    standings = {
        conf: compact_standings(rows, {t: teams[t] for t in conf_teams.get(conf, [])})
        for conf, rows in standings_by_conf.items()
    }

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
