"""
Pulls every conference's standings and every team's roster, schedule and
stats from their Sidearm athletics sites, and writes one
`conferences_snapshot_<date>.json` covering all of D3.

    uv run d3soccer scrape conferences            # all conferences
    uv run d3soccer scrape conferences SCIAC UAA  # just these

Sites fail for lots of reasons (403s, robots.txt, non-standard URLs; see the
quirk notes in scrapers/conferences.py). When a fetch fails or comes back
empty, the team's previous data is carried forward and the part is listed
under `stale`, so one bad run never blanks a team on the site.
"""

from __future__ import annotations

import dataclasses
from collections.abc import Callable
from datetime import date

from d3soccer.models import Team
from d3soccer.pipelines import snapshots
from d3soccer.scrapers import conferences, sciac
from d3soccer.scrapers.sidearm import fetch_roster, fetch_schedule, fetch_stats

TITLE = "Conferences"


def registry() -> dict[str, dict]:
    """Conference key -> {"teams": [Team], "fetch_standings": callable}."""
    out = {"SCIAC": {"teams": sciac.TEAMS, "fetch_standings": sciac.fetch_standings}}
    for key, cfg in conferences.CONFERENCES.items():
        fetch = (
            conferences.fetch_nescac_standings
            if key == "NESCAC"
            else (lambda key=key: conferences.fetch_standings(key))
        )
        out[key] = {"teams": cfg["teams"], "fetch_standings": fetch}
    return out


def previous_state() -> dict[str, dict]:
    """Conference key -> {"standings", "teams"} from the newest snapshots on disk."""
    state: dict[str, dict] = {}
    for path in snapshots.latest_per_family(snapshots.CONFERENCE_FAMILIES):
        snap = snapshots.load(path)
        if "conference" in snap:  # legacy single-conference SCIAC file
            confs = {snap["conference"]: snap}
        else:
            confs = snap.get("conferences", {})
        for key, cdata in confs.items():
            state[key] = {"standings": cdata.get("standings", []), "teams": cdata.get("teams", {})}
    return state


def _pull(label: str, fetch: Callable[[], list], previous: list, failures: list[str]):
    """Run `fetch`; on error or an empty result, keep `previous`. Returns (rows, stale)."""
    try:
        rows = [dataclasses.asdict(r) for r in fetch()]
        if rows:
            return rows, False
        reason = "empty result"
    except Exception as e:
        reason = f"{type(e).__name__}: {e}"
    failures.append(f"{label}: {reason}")
    print(f"  {label} failed ({reason}); keeping previous data")
    return previous, True


def pull_team(team: Team, previous: dict, season: int, failures: list[str]) -> dict:
    data = {"domain": team.site_domain, "stale": []}
    fetchers = {
        "roster": lambda: fetch_roster(team.site_domain, team.name, team.sport_slug),
        "schedule": lambda: fetch_schedule(team.site_domain, team.name, season, team.sport_slug),
        "stats": lambda: fetch_stats(team.site_domain, team.name, team.sport_slug),
    }
    for part, fetch in fetchers.items():
        rows, stale = _pull(f"{team.name} {part}", fetch, previous.get(part, []), failures)
        data[part] = rows
        if stale:
            data["stale"].append(part)
    return data


def run(only: list[str] | None = None) -> dict:
    reg = registry()
    keys = only or list(reg)
    unknown = sorted(set(keys) - set(reg))
    if unknown:
        raise SystemExit(f"Unknown conference(s): {', '.join(unknown)}. Known: {', '.join(reg)}")

    prev = previous_state()
    season = date.today().year
    failures: list[str] = []
    snapshot = {"generated": date.today().isoformat(), "conferences": {}, "failures": failures}

    # Conferences not being pulled this run are carried over unchanged.
    for key in reg:
        if key not in keys and key in prev:
            snapshot["conferences"][key] = prev[key]

    for key in keys:
        print(f"=== {key} ===")
        before = prev.get(key, {"standings": [], "teams": {}})
        standings, _ = _pull(
            f"{key} standings", reg[key]["fetch_standings"], before["standings"], failures
        )
        teams = {}
        for team in reg[key]["teams"]:
            print(f"Fetching {team.name}...")
            teams[team.name] = pull_team(team, before["teams"].get(team.name, {}), season, failures)
        snapshot["conferences"][key] = {"standings": standings, "teams": teams}

    path = snapshots.write("conferences", snapshot)
    snapshots.prune(snapshots.CONFERENCE_FAMILIES, keep=path)
    snapshots.report(TITLE, failures)
    return snapshot
