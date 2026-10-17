"""
Pulls national data and writes `national_snapshot_<date>.json`:

  - individual leaders: save %, goals/gm, assists/gm, points/gm
  - team leaders: team goals/gm, total goals, total assists, team assists/gm
  - NPI rankings
  - today's scoreboard
  - United Soccer Coaches D3 Top 25

    uv run d3soccer scrape national

This is fast (about a dozen requests), so it runs every couple of hours to
keep scores current. Anything that fails keeps its previous value.
"""

from __future__ import annotations

from datetime import UTC, date, datetime

from d3soccer.pipelines import snapshots
from d3soccer.scrapers import ncaa_national

TITLE = "National"


def previous_state() -> dict:
    """Merged national data from the newest snapshots, including the legacy SCIAC file."""
    state: dict = {"leaders": {}, "team_leaders": {}}
    for path in snapshots.latest_per_family(["sciac"]):
        legacy = snapshots.load(path).get("national", {})
        state["scoreboard"] = legacy.get("scoreboard")
        state["usc_poll"] = legacy.get("usc_poll")
    for path in snapshots.latest_per_family(snapshots.NATIONAL_FAMILIES):
        for key, value in snapshots.load(path).items():
            if isinstance(value, dict) and key in ("leaders", "team_leaders"):
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
    out["usc_poll"] = pull(
        "United Soccer Coaches poll",
        ncaa_national.fetch_united_soccer_coaches_poll,
        prev.get("usc_poll"),
    )

    path = snapshots.write("national", out)
    snapshots.prune(snapshots.NATIONAL_FAMILIES, keep=path)
    snapshots.report(TITLE, failures)
    return out
