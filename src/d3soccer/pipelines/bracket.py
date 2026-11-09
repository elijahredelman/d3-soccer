"""
Reads the hand-maintained NCAA tournament bracket in data/bracket.txt.

The NCAA posts the DIII men's soccer bracket as a PDF/graphic, not a feed, so
the matchups are typed in once at selection and results filled in as games
finish. Format (see the file's header for a worked example):

    # announced: Monday, Nov. 9        date shown before the bracket is out
    # as of: Nov. 15                    "updated" date shown with the bracket
    # info: Final Dec. 5 in Columbus    a line shown under the bracket title
    ## First round                      a round
    ### Williamstown, Mass.             optional group (pod / host site) in a round
    Williams (11-2-3) | Amherst | 2-1 | Sat. 1 p.m.     (a record after a name is optional)
    Tufts | Bowdoin | 1-1 (4-3 PK) |
    Hamilton | Bye

Each game is `team | team | score | note`, score and note optional. A score is
from the first team's point of view; ties name the penalty-kick result in
parentheses, also first team first.
"""

from __future__ import annotations

import re
from pathlib import Path

from d3soccer.config import BRACKET_FILE

_SCORE = re.compile(
    r"^(\d+)\s*-\s*(\d+)(?:\s*\((\d+)\s*-\s*(\d+)\s*(?:PK|pk|PKs|pks)?\))?\s*(\w+)?$"
)
_META = re.compile(r"#\s*(announced|as of|info)\s*:?\s*(.*)", re.I)
# A team's record after its name, as the NCAA bracket prints it: "Williams (11-2-3)".
_RECORD = re.compile(r"^(.*?)\s*\((\d+-\d+(?:-\d+)?)\)$")


def _team(cell: str) -> tuple[str, str]:
    m = _RECORD.match(cell)
    return (m.group(1), m.group(2)) if m else (cell, "")


def _game(line: str, group: str) -> dict:
    parts = [p.strip() for p in line.split("|")]
    a, a_rec = _team(parts[0])
    b, b_rec = _team(parts[1] if len(parts) > 1 else "")
    score = parts[2] if len(parts) > 2 else ""
    note = " | ".join(p for p in parts[3:] if p)
    game = {"a": a, "b": b}
    if a_rec:
        game["a_rec"] = a_rec
    if b_rec:
        game["b_rec"] = b_rec
    if b.lower() == "bye":
        game["b"], game["bye"], game["winner"] = "", True, "a"
    m = _SCORE.match(score)
    if m:
        sa, sb, pa, pb, suffix = m.groups()
        game["score"] = f"{sa}-{sb}"
        if pa:
            game["pk"] = f"{pa}-{pb}"
        if suffix:  # "2-1 OT", "1-0 2OT"
            game["score"] += f" {suffix}"
        x, y = (int(pa), int(pb)) if pa and sa == sb else (int(sa), int(sb))
        if x != y:
            game["winner"] = "a" if x > y else "b"
    elif score:
        note = " | ".join(p for p in (score, note) if p)
    if note:
        game["note"] = note
    if group:
        game["group"] = group
    return game


def parse(text: str) -> dict:
    """{announced, updated, rounds: [{name, games: [...]}]}; rounds empty until filled in."""
    out: dict = {"announced": "", "updated": "", "info": "", "rounds": []}
    group = ""
    for raw in text.splitlines():
        line = raw.strip()
        if not line:
            continue
        if line.startswith("###"):
            group = line.lstrip("#").strip()
        elif line.startswith("##"):
            out["rounds"].append({"name": line.lstrip("#").strip(), "games": []})
            group = ""
        elif line.startswith("#"):
            m = _META.match(line)
            if m:
                key = {"announced": "announced", "as of": "updated", "info": "info"}
                out[key[m.group(1).lower()]] = m.group(2).strip()
        elif out["rounds"]:
            out["rounds"][-1]["games"].append(_game(line, group))
    out["rounds"] = [r for r in out["rounds"] if r["games"]]
    return out


def load(path: Path = BRACKET_FILE) -> dict | None:
    return parse(path.read_text(encoding="utf-8")) if path.exists() else None
