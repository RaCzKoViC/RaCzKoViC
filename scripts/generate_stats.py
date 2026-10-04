#!/usr/bin/env python3
"""Generate a self-contained SVG using public GitHub statistics."""
import json
import os
import re
import urllib.request
from datetime import datetime, timezone
from html import escape
from pathlib import Path
from xml.etree import ElementTree

ROOT = Path(__file__).resolve().parents[1]


def api(path):
    headers = {"Accept": "application/vnd.github+json", "User-Agent": "profile-telemetry"}
    token = os.environ.get("GITHUB_TOKEN")
    if token:
        headers["Authorization"] = "Bearer " + token
    request = urllib.request.Request("https://api.github.com" + path, headers=headers)
    with urllib.request.urlopen(request, timeout=30) as response:
        return json.load(response)


def collect(username):
    profile = api(f"/users/{username}")
    repositories = []
    page = 1
    while True:
        batch = api(f"/users/{username}/repos?type=owner&per_page=100&page={page}")
        repositories.extend(batch)
        if len(batch) < 100:
            break
        page += 1
    originals = [repo for repo in repositories if not repo.get("fork")]
    return [
        ("Public repos", profile["public_repos"]),
        ("Followers", profile["followers"]),
        ("Stars received", sum(repo["stargazers_count"] for repo in originals)),
        ("Forks received", sum(repo["forks_count"] for repo in originals)),
    ]


def render(values, updated):
    rows = "\n".join(
        f'<text x="24" y="{102 + index * 44}" fill="#c9d1d9">{escape(label)}</text>'
        f'<text x="456" y="{102 + index * 44}" text-anchor="end" fill="#79c0ff">{value:,}</text>'
        for index, (label, value) in enumerate(values)
    )
    return f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 480 318" width="480" height="318" role="img" aria-labelledby="title desc">
<title id="title">Public GitHub activity</title>
<desc id="desc">{escape('; '.join(f'{label}: {value}' for label, value in values))}. Updated {escape(updated)}.</desc>
<rect x="1" y="1" width="478" height="316" rx="18" fill="#0d1117" stroke="#30363d" stroke-width="2"/>
<g font-family="monospace" font-size="24">
<text x="24" y="48" font-weight="bold" fill="#f2a65a">PUBLIC GITHUB</text>
{rows}
<text x="24" y="286" font-size="20" fill="#b1bac4">{escape(updated)} UTC</text>
</g>
</svg>
'''


def main():
    username = os.environ.get("GITHUB_USERNAME", "RaCzKoViC")
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9-]{0,38}", username):
        raise ValueError("Invalid GitHub username")
    values = collect(username)
    updated = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M")
    svg = render(values, updated)
    ElementTree.fromstring(svg)
    target = ROOT / "assets/github-stats.svg"
    temporary = target.with_suffix(".svg.tmp")
    temporary.write_text(svg, encoding="utf-8")
    temporary.replace(target)
    print(dict(values))


if __name__ == "__main__":
    main()
