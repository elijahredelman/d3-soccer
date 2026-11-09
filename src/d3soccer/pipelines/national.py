"""
Pulls national data and writes `national_snapshot_<date>.json`:

  - individual leaders: save %, goals/gm, assists/gm, points/gm
  - team leaders: team goals/gm, total goals, total assists, team assists/gm
  - NPI rankings
  - today's scoreboard
  - United Soccer Coaches D3 Top 25
  - boxscores: for each game on the scoreboard that has started, its NCAA box
    score; a final's is fetched once and kept as long as the finals below
  - finals: every final seen on a scoreboard in the last FINALS_DAYS days, carried
    forward between runs (the scoreboard itself only has today), so the tournament
    bracket can fill in results

    uv run d3soccer scrape national

This is fast (about a dozen requests), so it runs every couple of hours to
keep scores current. Anything that fails keeps its previous value.
"""

from __future__ import annotations

from datetime import UTC, date, datetime

from d3soccer.pipelines import snapshots
from d3soccer.scrapers import ncaa_national

TITLE = "National"
FINALS_DAYS = 45
MAX_BOXSCORES = 60  # per run; tournament days have at most 32 games


def pull_boxscores(previous: dict | None, rows: list[dict], now: float, failures: list) -> dict:
    """
    Box scores keyed by game id: {id: {final, epoch, data}}. Live games are re-fetched
    every run; finals only until one is stored with the final state.
    """
    out = dict(previous or {})
    todo = [
        r
        for r in rows
        if r["id"] and r["status"] != "pre" and not (out.get(r["id"]) or {}).get("final")
    ]
    errors = []
    for r in todo[:MAX_BOXSCORES]:
        try:
            data = ncaa_national.fetch_boxscore(r["id"])
        except Exception as e:  # one bad game shouldn't stop the rest
            errors.append(f"{r['id']} ({type(e).__name__})")
            continue
        out[r["id"]] = {"final": r["status"] == "final", "epoch": r["epoch"], "data": data}
    if errors:
        failures.append(f"box scores: {len(errors)} failed: " + ", ".join(errors[:5]))
    cutoff = now - FINALS_DAYS * 86400
    return {k: v for k, v in out.items() if v.get("epoch", 0) >= cutoff}


def merge_finals(previous: dict | None, scoreboard: dict | None, now: float) -> dict:
    """Finals keyed by NCAA game id: the previous ones plus today's, minus old ones."""
    from d3soccer.pipelines.app_data import compact_scoreboard

    finals = dict(previous or {})
    for row in compact_scoreboard(scoreboard):
        if row["status"] == "final" and row["id"]:
            finals[row["id"]] = row
    cutoff = now - FINALS_DAYS * 86400
    return {k: v for k, v in finals.items() if v.get("epoch", 0) >= cutoff}


def previous_state() -> dict:
    """Merged national data from the newest snapshots, including the legacy SCIAC file."""
    state: dict = {"leaders": {}, "team_leaders": {}}
    for path in snapshots.latest_per_family(["sciac"]):
        legacy = snapshots.load(path).get("national", {})
        state["scoreboard"] = legacy.get("scoreboard")
        state["usc_poll"] = legacy.get("usc_poll")
    for path in snapshots.latest_per_family(snapshots.NATIONAL_FAMILIES):
        for key, value in snapshots.load(path).items():
            if isinstance(value, dict) and key in (
                "leaders",
                "team_leaders",
                "finals",
                "boxscores",
            ):
                state.setdefault(key, {})
                state[key].update(value)
            elif value:
                state[key] = value
    return state


def _has_rows(value) -> bool:
    if isinstance(value, dict):
        return bool(value.get("data") or value.get("games"))
    return bool(value)


def run() -> dict:
    prev = previous_state()
    failures: list[str] = []
    out = {
        "generated": date.today().isoformat(),
        "fetched_at": datetime.now(UTC).isoformat(timespec="seconds"),
        "leaders": {},
        "team_leaders": {},
        "failures": failures,
    }

    def pull(label, fetch, previous):
        print(f"Fetching {label}...")
        try:
            value = fetch()
            if _has_rows(value):
                return value
            reason = "empty result"
        except Exception as e:
            reason = f"{type(e).__name__}: {e}"
        failures.append(f"{label}: {reason}")
        print(f"  {label} failed ({reason}); keeping previous data")
        return previous

    for label, stat_id in ncaa_national.STAT_CATEGORIES.items():
        out["leaders"][label] = pull(
            f"individual {label}",
            lambda stat_id=stat_id: ncaa_national.fetch_individual_stat_leaders(stat_id),
            prev["leaders"].get(label),
        )
    for label, stat_id in ncaa_national.TEAM_STAT_CATEGORIES.items():
        out["team_leaders"][label] = pull(
            f"team {label}",
            lambda stat_id=stat_id: ncaa_national.fetch_team_stat_leaders(stat_id),
            prev["team_leaders"].get(label),
        )
    out["npi_rankings"] = pull(
        "NPI rankings", ncaa_national.fetch_npi_rankings, prev.get("npi_rankings")
    )
    # Today's games only: an empty scoreboard just means no games today, so don't carry
    # yesterday's forward.
    try:
        print("Fetching scoreboard...")
        out["scoreboard"] = ncaa_national.fetch_scoreboard()
    except Exception as e:
        failures.append(f"scoreboard: {type(e).__name__}: {e}")
        print(f"  scoreboard failed ({e}); keeping previous data")
        out["scoreboard"] = prev.get("scoreboard")
    now = datetime.now(UTC).timestamp()
    out["finals"] = merge_finals(prev.get("finals"), out["scoreboard"], now)
    from d3soccer.pipelines.app_data import compact_scoreboard

    print("Fetching box scores...")
    out["boxscores"] = pull_boxscores(
        prev.get("boxscores"), compact_scoreboard(out["scoreboard"]), now, failures
    )
    print(f"  {len(out['boxscores'])} box scores stored")
    out["usc_poll"] = pull(
        "United Soccer Coaches poll",
        ncaa_national.fetch_united_soccer_coaches_poll,
        prev.get("usc_poll"),
    )

    path = snapshots.write("national", out)
    snapshots.prune(snapshots.NATIONAL_FAMILIES, keep=path)
    snapshots.report(TITLE, failures)
    return out
