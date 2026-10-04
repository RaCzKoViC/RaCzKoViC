#!/usr/bin/env python3
"""Render the profile as real, selectable ASCII and live public statistics."""
import json
import os
import re
import urllib.request
import time
from datetime import datetime, timezone
from html import escape
from pathlib import Path
from project_telemetry import collect_projects, markdown

ROOT = Path(__file__).resolve().parents[1]
LEFT_WIDTH = 48
RIGHT_WIDTH = 60
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
            raise RuntimeError("API response is not ready")
        return json.load(response)


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
    projects = collect_projects(originals, api)
    return {'lines': sum(p['source'] for p in projects),
            'documentation': sum(p['documentation'] for p in projects),
            'configuration': sum(p['configuration'] for p in projects),
            'projects': projects, 'repos': user['public_repos'], 'followers': user['followers'],
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
          f"{values['lines']:,} source lines")
    field('Public repos', f"{values['repos']:,}")
    field('Stars received', f"{values['stars']:,}")
    field('Followers', f"{values['followers']:,}")
    field('Forks received', f"{values['forks']:,}")
    row('  Stars / forks: public, non-fork repositories.',
        '  <b>Stars / forks:</b> public, non-fork repositories.')
    field('Updated', updated + ' UTC')
    field('Documentation', f"{values['documentation']:,}")
    field('Configuration', f"{values['configuration']:,}")
    left = portrait.splitlines()
    if len(left) != len(rows):
        raise ValueError(f'Expected {len(rows)} portrait lines, got {len(left)}')
    if any(len(line) > LEFT_WIDTH for line in left):
        raise ValueError('Portrait exceeds its column width')
    lines = [escape(line.ljust(LEFT_WIDTH)) + '  ' + right for line, right in zip(left, rows)]
    return (START + '\n<pre>\n' + '\n'.join(lines) + '\n</pre>\n'
            + markdown(values['projects']) + '<!-- PROFILE:DATA ' + json.dumps(values, sort_keys=True) + ' -->\n' + END)


def main():
    username = os.environ.get('GITHUB_USERNAME', 'RaCzKoViC')
    if username != 'RaCzKoViC':
        raise ValueError('This profile belongs to RaCzKoViC')
    event_path = os.environ.get('GITHUB_EVENT_PATH')
    if os.environ.get('GITHUB_EVENT_NAME') == 'repository_dispatch' and event_path:
        payload = json.loads(Path(event_path).read_text()).get('client_payload', {})
        repository = payload.get('repository')
        run_id = payload.get('run_id')
        allowed = {'RaCzKoViC/' + name for name in ['RacOS', 'The-MinerGuy', 'Odysseus-Lab', 'AgentBox', 'CodeMap']}
        if repository in allowed and isinstance(run_id, int) and run_id > 0:
            # A reusable CI notification is sent just before its caller completes.
            # Wait only for that event's run, never on a recurring schedule.
            for attempt in range(60):
                if api(f'/repos/{repository}/actions/runs/{run_id}')['status'] == 'completed':
                    break
                time.sleep(2)
            else:
                raise RuntimeError('The notifying CI run did not finish within two minutes')
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
