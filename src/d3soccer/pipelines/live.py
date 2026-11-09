"""
Today's scores and box scores, written straight into the site for a deploy:

  web/live.json            {fetchedAt, scoreboard: [compact rows], boxscores: [game ids]}
  web/boxscores/<id>.json  each started game's NCAA box score

    uv run d3soccer live

The NCAA feed doesn't allow browsers on other sites to read it (no CORS header), so
the page can't poll it directly. Instead every deploy runs this after `build`, the
Live scores workflow redeploys every 10 minutes during tournament games, and an open
page re-reads live.json every minute. Nothing here is committed: the national scrape
keeps the history (finals, box scores) in the snapshots.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime

from d3soccer.config import WEB_DIR
from d3soccer.pipelines.app_data import compact_scoreboard
from d3soccer.scrapers import ncaa_national


def run() -> dict:
    rows = compact_scoreboard(ncaa_national.fetch_scoreboard())
    box_dir = WEB_DIR / "boxscores"
    box_dir.mkdir(parents=True, exist_ok=True)
    boxscores = []
    for r in rows:
        if r["status"] == "pre" or not r["id"].isdigit():
            continue
        try:
            data = ncaa_national.fetch_boxscore(r["id"])
        except Exception as e:  # keep going: one game's box score isn't worth the deploy
            print(f"  box score {r['id']} failed: {type(e).__name__}: {e}")
            continue
        (box_dir / f"{r['id']}.json").write_text(
            json.dumps(data, separators=(",", ":"), ensure_ascii=False), encoding="utf-8"
        )
        boxscores.append(r["id"])
    out = {
        "fetchedAt": datetime.now(UTC).isoformat(timespec="seconds"),
        "scoreboard": rows,
        "boxscores": boxscores,
    }
    (WEB_DIR / "live.json").write_text(json.dumps(out, separators=(",", ":")), encoding="utf-8")
    print(f"live.json: {len(rows)} games, {len(boxscores)} box scores")
    return out
