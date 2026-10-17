"""Reading, writing and pruning the dated JSON files in data/snapshots/.

File names are `<family>_snapshot_<YYYY-MM-DD>.json`. Families:

  conferences   every conference: standings + each team's roster/schedule/stats
  national      leaders, team leaders, NPI, scoreboard, United Soccer Coaches poll

Older families from the pilot scripts (`sciac`, `conferences2`, `conferences3`,
`leaders`) are still read so existing snapshots keep working, and are pruned once
a newer file supersedes them.
"""

from __future__ import annotations

import json
import os
import re
from datetime import date
from pathlib import Path

from d3soccer.config import SNAPSHOT_DIR

CONFERENCE_FAMILIES = ["sciac", "conferences", "conferences2", "conferences3"]
NATIONAL_FAMILIES = ["leaders", "national"]

_NAME = re.compile(r"^(?P<family>[a-z0-9]+)_snapshot_(?P<date>\d{4}-\d{2}-\d{2})\.json$")


def _files(families: list[str], snapshot_dir: Path | None) -> list[tuple[str, str, Path]]:
    """(date, family, path) for every snapshot in `families`, oldest first."""
    out = []
    for path in (snapshot_dir or SNAPSHOT_DIR).glob("*_snapshot_*.json"):
        m = _NAME.match(path.name)
        if m and m["family"] in families:
            out.append((m["date"], m["family"], path))
    return sorted(out)


def latest_per_family(families: list[str], snapshot_dir: Path | None = None) -> list[Path]:
    """Newest file of each family, ordered oldest to newest so later ones win when merged."""
    newest: dict[str, tuple[str, int, Path]] = {}
    for d, family, path in _files(families, snapshot_dir):
        newest[family] = (d, families.index(family), path)
    # Same-date ties resolve in the order `families` lists them.
    return [path for *_, path in sorted(newest.values())]


def load(path: Path) -> dict:
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def write(family: str, data: dict, snapshot_dir: Path | None = None) -> Path:
    """Write today's snapshot for `family` (compact JSON) and return its path."""
    snapshot_dir = snapshot_dir or SNAPSHOT_DIR
    snapshot_dir.mkdir(parents=True, exist_ok=True)
    path = snapshot_dir / f"{family}_snapshot_{date.today().isoformat()}.json"
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, separators=(",", ":"), ensure_ascii=False)
    print(f"Wrote {path} ({path.stat().st_size:,} bytes)")
    return path


def prune(families: list[str], keep: Path, snapshot_dir: Path | None = None) -> list[Path]:
    """Delete every snapshot in `families` except `keep`. Git history keeps the old ones."""
    removed = []
    for _, _, path in _files(families, snapshot_dir):
        if path != keep:
            path.unlink()
            removed.append(path)
    for path in removed:
        print(f"Pruned {path.name}")
    return removed


def report(title: str, failures: list[str]) -> None:
    """Print failed fetches, and add them to the GitHub Actions run summary when there."""
    print(f"\n{title}: {len(failures)} failed fetches (previous data kept for each).")
    summary = os.environ.get("GITHUB_STEP_SUMMARY")
    if not summary:
        return
    with open(summary, "a", encoding="utf-8") as f:
        f.write(f"### {title}: {len(failures)} failed fetches\n\n")
        if failures:
            f.write(
                "Previous data was kept for each of these.\n\n<details><summary>Show</summary>\n\n"
            )
            f.writelines(f"- {line}\n" for line in failures)
            f.write("\n</details>\n\n")
