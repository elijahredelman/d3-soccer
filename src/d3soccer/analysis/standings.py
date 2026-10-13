"""Win/loss/draw records from a set of games."""

from collections.abc import Iterable

import pandas as pd

from d3soccer.models import Game

COLUMNS = ["team", "gp", "w", "l", "d", "gf", "ga", "gd", "pts"]


def standings(games: Iterable[Game]) -> pd.DataFrame:
    """Table of records, sorted by points then goal difference (3 for a win, 1 for a draw)."""
    rows = []
    for g in games:
        if not g.played:
            continue
        for team, gf, ga in (
            (g.home, g.home_goals, g.away_goals),
            (g.away, g.away_goals, g.home_goals),
        ):
            rows.append(
                {"team": team, "w": gf > ga, "l": gf < ga, "d": gf == ga, "gf": gf, "ga": ga}
            )

    if not rows:
        return pd.DataFrame(columns=COLUMNS)

    df = (
        pd.DataFrame(rows)
        .groupby("team")
        .agg(
            gp=("w", "size"),
            w=("w", "sum"),
            l=("l", "sum"),
            d=("d", "sum"),
            gf=("gf", "sum"),
            ga=("ga", "sum"),
        )
    )
    df["gd"] = df["gf"] - df["ga"]
    df["pts"] = 3 * df["w"] + df["d"]
    df = df.reset_index().sort_values(["pts", "gd", "gf"], ascending=False, ignore_index=True)
    return df[COLUMNS]
