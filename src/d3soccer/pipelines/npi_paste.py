"""
Reads the hand-pasted NPI table in data/npi.txt.

The NCAA publishes D3 NPI on stats.ncaa.org behind a bot check that blocks
automated fetches, so the table is copied from the browser once a week and
pasted into that file. Copying an HTML table gives one row per line with
tab-separated cells; runs of 2+ spaces are accepted too. Lines starting with
`#` are comments, and one of the form `# as of <date>` sets the date shown on
the site.
"""

from __future__ import annotations

import re
from pathlib import Path

from d3soccer.config import NPI_PASTE

MAX_ROWS = 100


def _cells(line: str) -> list[str]:
    parts = line.split("\t") if "\t" in line else re.split(r"\s{2,}", line)
    return [p.strip() for p in parts]


def parse(text: str) -> dict | None:
    """{title, updated, source, data: [row]} in the NCAA-feed shape, or None if no table."""
    updated, headers, data = "", None, []
    for raw in text.splitlines():
        line = raw.strip()
        if not line:
            continue
        if line.startswith("#"):
            m = re.match(r"#\s*as of[:\s]+(.+)", line, re.I)
            if m:
                updated = m.group(1).strip()
            continue
        cells = _cells(raw.strip("\n"))
        if headers is None:
            if any(re.search(r"team|school|name", c, re.I) for c in cells):
                headers = cells
            continue
        if len(cells) >= 2 and any(cells):
            data.append(dict(zip(headers, cells)))
    if not headers or not data:
        return None
    if not any(re.search(r"rank|^rk\.?$", h, re.I) for h in headers):
        data = [{"Rank": str(i), **r} for i, r in enumerate(data, 1)]
    return {
        "title": "NCAA DIII Men's Soccer NPI",
        "updated": updated,
        "source": "stats.ncaa.org (pasted)",
        "data": data[:MAX_ROWS],
    }


def load(path: Path = NPI_PASTE) -> dict | None:
    return parse(path.read_text(encoding="utf-8")) if path.exists() else None
