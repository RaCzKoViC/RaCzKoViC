#!/usr/bin/env python3
"""Render the profile as real, selectable ASCII and live public statistics."""
import json
import os
import re
import urllib.request
import time
import subprocess
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from html import escape
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LEFT_WIDTH = 44
RIGHT_WIDTH = 64
START = '<!-- PROFILE:START -->'
END = '<!-- PROFILE:END -->'


def api(path):
    headers = {'Accept': 'application/vnd.github+json', 'User-Agent': 'profile-telemetry'}
    token = os.environ.get('GITHUB_TOKEN')
    if token:
        headers['Authorization'] = 'Bearer ' + token
    request = urllib.request.Request('https://api.github.com' + path, headers=headers)
    with urllib.request.urlopen(request, timeout=30) as response:
        if response.status == 202:
            raise StatisticsPending(path)
        return json.load(response)


class StatisticsPending(RuntimeError):
    pass


def count_numstat(history):
    added = deleted = 0
    for line in history.splitlines():
        columns = line.split('\t', 2)
        if len(columns) == 3 and columns[0].isdigit() and columns[1].isdigit():
            added += int(columns[0])
            deleted += int(columns[1])
    return added, deleted


def code_frequency(repo):
    """GitHub counts tracked text changes; this is not a source-only parser."""
    if repo['full_name'] == 'RaCzKoViC/RaCzKoViC' and (ROOT / '.git').exists():
        history = subprocess.run(
            ['git', '-C', str(ROOT), 'log', '--no-merges', '--invert-grep',
             '--grep=^chore(profile): refresh public statistics$',
             '--format=', '--numstat', 'HEAD'],
            check=True, capture_output=True, text=True).stdout
        return count_numstat(history)
    path = '/repos/' + repo['full_name'] + '/stats/code_frequency'
    for attempt in range(10):
        try:
            weeks = api(path)
            if not isinstance(weeks, list):
                raise ValueError('Unexpected code-frequency response')
            if any(len(week) != 3 for week in weeks):
                raise ValueError('Invalid code-frequency row')
            added = sum(week[1] for week in weeks)
            deleted = -sum(week[2] for week in weeks)
            if weeks and added == 0 and deleted == 0:
                raise ValueError('GitHub returned empty line counts for a nonempty repository')
            return added, deleted
        except StatisticsPending:
            if attempt == 9:
                raise
            time.sleep(10)


def collect(username):
    user = api(f'/users/{username}')
    repos = []
    page = 1
    while True:
        batch = api(f'/users/{username}/repos?type=owner&per_page=100&page={page}')
        repos.extend(batch)
        if len(batch) < 100:
            break
        page += 1
    originals = [r for r in repos if not r.get('fork')]
    with ThreadPoolExecutor(max_workers=4) as pool:
        counts = list(pool.map(code_frequency, originals))
    added = sum(pair[0] for pair in counts)
    deleted = sum(pair[1] for pair in counts)
    return {'lines': added - deleted, 'added': added, 'deleted': deleted,
            'repos': user['public_repos'], 'followers': user['followers'],
            'stars': sum(r['stargazers_count'] for r in originals),
            'forks': sum(r['forks_count'] for r in originals)}


def render(values, updated, portrait):
    rows = []

    def row(raw='', html=None):
        if len(raw) > RIGHT_WIDTH:
            raise ValueError(f'Profile row too wide: {raw}')
        rows.append(escape(raw) if html is None else html)

    def section(title):
        raw = title + ' ' + '-' * (RIGHT_WIDTH - len(title) - 1)
        row(raw, '<b>' + escape(raw) + '</b>')

    def field(key, value, url=None):
        dots = '.' * (RIGHT_WIDTH - len(key) - len(value) - 5)
        if not dots:
            raise ValueError(f'Profile field too wide: {key}')
        raw = f'  {key}: {dots} {value}'
        html = f'  <b>{escape(key)}:</b> {dots} '
        html += (f'<a href="{escape(url, quote=True)}">{escape(value)}</a>'
                 if url else escape(value))
        row(raw, html)

    section('RaCzKoViC@github')
    field('OS', 'Windows 11 / Ubuntu / iOS')
    field('Focus', 'Systems / AI agents / Games')
    field('Editor', 'VS Code / Terminal')
    field('Workflow', 'AI-assisted development')
    row()
    field('Languages', 'Rust / Python / TypeScript / C#')
    field('Web', 'JavaScript / HTML / CSS')
    field('AI tools', 'Claude Code / Codex / Kimi')
    field('Local AI', 'Local LLMs / vLLM')
    row()
    field('Infra', 'Docker / PostgreSQL / Qdrant')
    field('Messaging', 'Redis / NATS / MCP')
    row()
    section('- Projects')
    for name, label in [('RacOS', 'Rust operating system'),
                        ('Odysseus-Lab', 'AI / development laboratory'),
                        ('AgentBox', 'Agent tools / environments'),
                        ('CodeMap', 'Code exploration tools'),
                        ('The-MinerGuy', 'Mining / crafting / exploration')]:
        # Each project name is a real link inside the text terminal.
        dots = '.' * (RIGHT_WIDTH - len(name) - len(label) - 5)
        row(f'  {name}: {dots} {label}',
            f'  <a href="https://github.com/RaCzKoViC/{name}">{name}</a>: {dots} {label}')
    row()
    section('- Contact')
    field('GitHub', '@RaCzKoViC', 'https://github.com/RaCzKoViC')
    field('Repositories', 'Browse projects', 'https://github.com/RaCzKoViC?tab=repositories')
    field('Email.Personal', 'raczimaczi@icloud.com', 'mailto:raczimaczi@icloud.com')
    row()
    section('- GitHub Stats')
    field('Lines of Code on GitHub',
          f"{values['lines']:,} ({values['added']:,}++, {values['deleted']:,}--)")
    field('Public repos', f"{values['repos']:,}")
    field('Stars received', f"{values['stars']:,}")
    field('Followers', f"{values['followers']:,}")
    field('Forks received', f"{values['forks']:,}")
    row('  Stars / forks: public, non-fork repositories.',
        '  <b>Stars / forks:</b> public, non-fork repositories.')
    field('Updated', updated + ' UTC')
    row('  Refresh: on profile push / check every 5 minutes.')
    row('  Lines: additions minus deletions; tracked text.')
    left = portrait.splitlines()
    if len(left) != len(rows):
        raise ValueError(f'Expected {len(rows)} portrait lines, got {len(left)}')
    if any(len(line) > LEFT_WIDTH for line in left):
        raise ValueError('Portrait exceeds its column width')
    lines = [escape(line.ljust(LEFT_WIDTH)) + '   ' + right for line, right in zip(left, rows)]
    return (START + '\n<pre>\n' + '\n'.join(lines) + '\n</pre>\n'
            + '<!-- PROFILE:DATA ' + json.dumps(values, sort_keys=True) + ' -->\n' + END)


def main():
    username = os.environ.get('GITHUB_USERNAME', 'RaCzKoViC')
    if username != 'RaCzKoViC':
        raise ValueError('This profile belongs to RaCzKoViC')
    values = collect(username)
    path = ROOT / 'README.md'
    existing = path.read_text()
    previous = re.search(r'<!-- PROFILE:DATA (.*?) -->', existing)
    if previous and json.loads(previous.group(1)) == values:
        print('No statistics changed; README remains unchanged.')
        return
    updated = datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M')
    block = render(values, updated, (ROOT / 'assets/portrait.txt').read_text())
    pattern = re.compile(re.escape(START) + r'.*?' + re.escape(END), re.S)
    if len(pattern.findall(existing)) != 1:
        raise ValueError('Expected exactly one generated profile block')
    result = pattern.sub(lambda _: block, existing)
    temporary = path.with_suffix('.md.tmp')
    temporary.write_text(result, encoding='utf-8')
    temporary.replace(path)
    print(values)


if __name__ == '__main__':
    main()
