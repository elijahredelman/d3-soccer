"""
Fetches pages and prints what's on them, to fix parsers from a host that can
reach the sites (the Probe sites workflow) instead of guessing at selectors.

    uv run d3soccer probe https://example.edu/sports/mens-soccer/roster
    uv run d3soccer probe --failed      # every non-403 failure in the latest snapshot
    uv run d3soccer probe URL --links rankings/soccer-men   # also list matching hrefs
    uv run d3soccer probe URL --dump "tbody tr"             # print the first match's HTML

For HTML it reports the platform, the counts of the selectors our Sidearm
parsers rely on, every table's classes and header row, and the most common
roster/schedule/standings class names. For JSON it reports the shape.
"""

from __future__ import annotations

import json
import re
from collections import Counter
from datetime import date

from bs4 import BeautifulSoup

from d3soccer.pipelines import snapshots
from d3soccer.scrapers import conferences, http, sciac

# Selectors the current parsers depend on (scrapers/sidearm.py, conferences.py, sciac.py).
PARSER_SELECTORS = [
    "li.sidearm-roster-player",
    "li.sidearm-schedule-game",
    "table.sidearm-table.highlight-column-hover",
    "table.sidearm-standings-table",
    "table.sidearm-standings-table td.hide-on-medium-down",
]
INTERESTING_CLASS = re.compile(r"roster|schedule|standing|stats|player|game", re.I)


def describe(url: str, links: str | None = None, dump: list[str] | None = None) -> list[str]:
    try:
        # Same Chrome-like client the scrapers use, so the probe sees what they see.
        resp = http.get_raw(url, timeout=20)
    except http.RequestException as e:
        return [f"  ERROR {type(e).__name__}: {e}"]
    out = [
        f"  status {resp.status_code}, {len(resp.content):,} bytes, "
        f"{resp.headers.get('content-type', '?')}",
    ]
    if resp.url != url:
        out.append(f"  redirected to {resp.url}")

    if "json" in resp.headers.get("content-type", ""):
        try:
            data = resp.json()
        except ValueError:
            return [*out, "  invalid JSON"]
        if isinstance(data, dict):
            out.append(f"  keys: {list(data)[:15]}")
            for k in ("title", "updated"):
                if k in data:
                    out.append(f"  {k}: {data[k]!r}")
            if isinstance(data.get("data"), list):
                out.append(f"  data rows: {len(data['data'])}")
                out += [f"    {json.dumps(r)[:240]}" for r in data["data"][:2]]
        else:
            out.append(f"  {type(data).__name__} of {len(data)}")
        return out

    if "text/plain" in resp.headers.get("content-type", ""):
        return [*out, f"  text: {resp.text[:3000]!r}"]

    html = resp.text
    if len(html) < 1500:
        out.append(f"  body: {html!r}")
    soup = BeautifulSoup(html, "lxml")
    title = soup.title.get_text(strip=True) if soup.title else ""
    generator = soup.find("meta", attrs={"name": "generator"})
    platform = [
        name
        for name, marker in (("sidearm", "sidearm"), ("prestosports", "prestosports"))
        if marker in html.lower()
    ]
    out.append(f"  title: {title[:120]!r}")
    out.append(
        f"  platform hints: {platform or 'none'}"
        + (f", generator={generator.get('content')!r}" if generator else "")
    )
    out.append(
        "  parser selectors: " + ", ".join(f"{s}={len(soup.select(s))}" for s in PARSER_SELECTORS)
    )

    tables = soup.find_all("table")
    out.append(f"  tables: {len(tables)}")
    for t in tables[:8]:
        first_row = t.find("tr")
        headers = (
            [c.get_text(" ", strip=True) for c in first_row.find_all(["th", "td"])]
            if first_row
            else []
        )
        out.append(
            f"    <table class={' '.join(t.get('class', []))!r} id={t.get('id')!r}> "
            f"{len(t.find_all('tr'))} rows; header: {' | '.join(headers)[:200]}"
        )

    classes = Counter(
        c for el in soup.find_all(class_=True) for c in el["class"] if INTERESTING_CLASS.search(c)
    )
    out.append(f"  common classes: {', '.join(f'{c}x{n}' for c, n in classes.most_common(15))}")

    apis = sorted(set(re.findall(r"""["'](/(?:api|services)/[^"'\s]{3,120})["']""", html)))[:8]
    if apis:
        out.append(f"  api paths in page: {apis}")
    for selector in dump or []:
        el = soup.select_one(selector)
        out.append(f"  dump {selector!r}: " + (repr(str(el)[:2500]) if el else "no match"))
    if links:
        hrefs = sorted({a["href"] for a in soup.find_all("a", href=True) if links in a["href"]})
        out.append(f"  links containing {links!r} ({len(hrefs)}): {hrefs[:25]}")
    return out


def failed_urls() -> list[str]:
    """URLs for every non-403 failure in the newest conferences snapshot."""
    paths = snapshots.latest_per_family(["conferences"])
    if not paths:
        return []
    failures = snapshots.load(paths[-1]).get("failures", [])

    teams = {t.name: t for t in sciac.TEAMS}
    for cfg in conferences.CONFERENCES.values():
        teams.update({t.name: t for t in cfg["teams"]})
    standings = {key: cfg["standings_url"] for key, cfg in conferences.CONFERENCES.items()}
    standings["SCIAC"] = sciac.STANDINGS_URL

    season = date.today().year  # same season the conferences pipeline requests
    urls = []
    for line in failures:
        if " 403 " in line:
            continue  # the site blocks automated requests; probing won't change that
        m = re.match(r"(.+) (roster|schedule|stats|standings): ", line)
        if not m:
            continue
        name, part = m.groups()
        if part == "standings":
            if standings.get(name):
                urls.append(standings[name])
            continue
        team = teams.get(name)
        if team:
            base = f"https://{team.site_domain}/sports/{team.sport_slug}"
            suffix = {
                "roster": "/roster",
                "schedule": f"/schedule/{season}",
                "stats": "/stats",
            }
            urls.append(base + suffix[part])
    return list(dict.fromkeys(urls))


def run(
    urls: list[str], failed: bool = False, links: str | None = None, dump: list[str] | None = None
) -> None:
    targets = list(urls) + (failed_urls() if failed else [])
    if not targets:
        raise SystemExit("Nothing to probe: pass URLs or --failed.")
    for url in targets:
        print(url)
        print("\n".join(describe(url, links, dump)))
        print()
