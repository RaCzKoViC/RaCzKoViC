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
from urllib.error import HTTPError
from project_telemetry import collect_projects, markdown
import portfolio

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


def pages_url(repo):
    if not repo.get('has_pages'):
        return None
    try:
        return api(f"/repos/{repo['full_name']}/pages").get('html_url')
    except HTTPError as error:
        if error.code != 404:
            raise
        return None


def repository_metadata(repos, projects):
    """Public facts used by the Featured portfolio, keyed by repository name."""
    snapshots = {p['name']: p for p in projects}
    result = {}
    for repo in repos:
        snap = snapshots.get(repo['name'], {})
        result[repo['name']] = {
            'name': repo['name'], 'html_url': repo['html_url'],
            'private': repo.get('private', False), 'fork': repo.get('fork', False),
            'archived': repo.get('archived', False),
            'description': repo.get('description'), 'homepage': repo.get('homepage'),
            'topics': sorted(repo.get('topics') or []), 'language': repo.get('language'),
            'stars': repo.get('stargazers_count', 0), 'pages_url': pages_url(repo),
            **{k: snap.get(k) for k in ('ci', 'release', 'release_url', 'release_date', 'changed', 'sha')}}
    return result


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
    originals = [r for r in repos if not r.get('fork') and not r.get('private')]
    projects = collect_projects(originals, api)
    values = {'lines': sum(p['source'] for p in projects),
              'documentation': sum(p['documentation'] for p in projects),
              'configuration': sum(p['configuration'] for p in projects),
              'projects': projects, 'repos': user['public_repos'], 'followers': user['followers'],
              'stars': sum(r['stargazers_count'] for r in originals),
              'forks': sum(r['forks_count'] for r in originals)}
    return values, repository_metadata(originals, projects)


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
    row()
    section('- GitHub Stats')
    field('Lines of Code on GitHub',
          f"{values['lines']:,} source lines")
    field('Documentation', f"{values['documentation']:,}")
    field('Configuration', f"{values['configuration']:,}")
    field('Public repos', f"{values['repos']:,}")
    field('Stars received', f"{values['stars']:,}")
    field('Followers', f"{values['followers']:,}")
    field('Forks received', f"{values['forks']:,}")
    row('  Stars / forks: public, non-fork repositories.',
        '  <b>Stars / forks:</b> public, non-fork repositories.')
    field('Updated', updated + ' UTC')
    row()
    left = portrait.splitlines()
    if len(left) != len(rows):
        raise ValueError(f'Expected {len(rows)} portrait lines, got {len(left)}')
    if any(len(line) > LEFT_WIDTH for line in left):
        raise ValueError('Portrait exceeds its column width')
    lines = [escape(line.ljust(LEFT_WIDTH)) + '  ' + right for line, right in zip(left, rows)]
    return (START + '\n<details open>\n<summary>ASCII terminal · collapse to read the portfolio</summary>\n\n<pre>\n' + '\n'.join(lines) + '\n</pre>\n'
            + '<!-- PROFILE:DATA ' + json.dumps(values, sort_keys=True) + ' -->\n</details>\n' + END)


def main():
    username = os.environ.get('GITHUB_USERNAME', 'RaCzKoViC')
    if username != 'RaCzKoViC':
        raise ValueError('This profile belongs to RaCzKoViC')
    event_path = os.environ.get('GITHUB_EVENT_PATH')
    if os.environ.get('GITHUB_EVENT_NAME') == 'repository_dispatch' and event_path:
        payload = json.loads(Path(event_path).read_text()).get('client_payload', {})
        repository = payload.get('repository')
        run_id = payload.get('run_id')
        owned = isinstance(repository, str) and re.fullmatch(r'RaCzKoViC/[A-Za-z0-9._-]+', repository)
        if owned and isinstance(run_id, int) and run_id > 0:
            # A reusable CI notification is sent just before its caller completes.
            # Wait only for that event's run. Any owned repository may notify, so a
            # newly published project needs no allow-list change here.
            for attempt in range(60):
                try:
                    status = api(f'/repos/{repository}/actions/runs/{run_id}')['status']
                except HTTPError as error:
                    if error.code != 404:
                        raise
                    break  # not readable with this token (e.g. private): refresh anyway
                if status == 'completed':
                    break
                time.sleep(2)
            else:
                raise RuntimeError('The notifying CI run did not finish within two minutes')
    values, repos = collect(username)
    config = portfolio.load_config(ROOT / 'portfolio.yml')
    path = ROOT / 'README.md'
    existing = path.read_text(encoding='utf-8')
    updated = datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M')
    result = update_readme(existing, values, repos, config, updated,
                           (ROOT / 'assets/portrait.txt').read_text(encoding='utf-8'))
    if result == existing:
        print('No statistics or portfolio data changed; README remains unchanged.')
        return
    temporary = path.with_suffix('.md.tmp')
    temporary.write_text(result, encoding='utf-8')
    temporary.replace(path)
    print(values)


def update_readme(existing, values, repos, config, updated, portrait):
    """Return the README with all generated blocks refreshed.

    The terminal block (which carries the "Updated" timestamp) is re-rendered
    only when its statistics changed; the portfolio and telemetry blocks are
    pure functions of their data, so identical data yields identical text.
    """
    result = existing
    previous = re.search(r'<!-- PROFILE:DATA (.*?) -->', existing)
    if not (previous and json.loads(previous.group(1)) == values):
        block = render(values, updated, portrait)
        pattern = re.compile(re.escape(START) + r'.*?' + re.escape(END), re.S)
        if len(pattern.findall(result)) != 1:
            raise ValueError('Expected exactly one generated profile block')
        result = pattern.sub(lambda _: block, result)
    result = portfolio.replace_block(result, portfolio.render(config, repos))
    telemetry_pattern = re.compile(r'<!-- TELEMETRY:START -->.*?<!-- TELEMETRY:END -->', re.S)
    if len(telemetry_pattern.findall(result)) != 1:
        raise ValueError('Expected exactly one telemetry block')
    telemetry = '<!-- TELEMETRY:START -->\n' + markdown(values['projects']) + '\n<!-- TELEMETRY:END -->'
    return telemetry_pattern.sub(lambda _: telemetry, result)

if __name__ == '__main__':
    main()
