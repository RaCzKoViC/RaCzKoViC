"""Snapshot classified, nonblank physical lines at each default-branch SHA."""
import tarfile
import urllib.request
from pathlib import PurePosixPath
from concurrent.futures import ThreadPoolExecutor
from urllib.error import HTTPError
from provenance import archive_files, provenance, dependency

SOURCE = set('rs py js mjs cjs ts tsx jsx c h cpp hpp cc cs java go rb php swift kt kts sh bash ps1 bat cmd asm s lua sql vue svelte css scss sass less html htm'.split())
DOCS = set('md mdx rst txt adoc tex'.split())
CONFIG = set('json jsonc yaml yml toml ini cfg conf xml csproj fsproj sln props targets lock env editorconfig gitignore gitattributes dockerignore'.split())
EXCLUDED = set('node_modules vendor target dist build bin obj .git .venv venv __pycache__ coverage'.split())

def category(path):
    p = PurePosixPath(path)
    if any(part in EXCLUDED for part in p.parts): return None
    name = p.name.lower(); ext = p.suffix.lower().lstrip('.')
    if name in {'license','licence','copying','notice'} or ext in DOCS: return 'documentation'
    if name in {'dockerfile','makefile','justfile','cmakelists.txt'} or name.startswith('.env') or ext in CONFIG or name.lstrip('.') in CONFIG: return 'configuration'
    if ext in SOURCE: return 'source'
    return None

def ci_state(runs):
    if not runs: return 'No CI for this commit'
    if any(r['status'] != 'completed' for r in runs): return 'Running'
    conclusions = [r.get('conclusion') for r in runs]
    if any(c in {'failure','timed_out','action_required','startup_failure'} for c in conclusions): return 'Failed'
    if any(c == 'cancelled' for c in conclusions): return 'Cancelled'
    if all(c in {'success','neutral','skipped'} for c in conclusions) and 'success' in conclusions: return 'Passed'
    return 'Skipped / neutral'

def snapshot(repo, api):
    base = '/repos/' + repo['full_name']
    commit = api(base + '/commits/' + repo['default_branch'])
    sha = commit['sha']; totals = dict(source=0, documentation=0, configuration=0)
    files = archive_files(repo['full_name'], sha)
    origins = provenance(repo, files, category, SOURCE)
    for path, text in files.items():
        kind = category(path)
        if not kind or dependency(repo['name'], path) or (repo['name'] == 'RaCzKoViC' and path == 'README.md'): continue
        totals[kind] += sum(bool(line.strip()) for line in text.splitlines())
    assert totals['source'] == origins['project_source'] + origins['upstream_source']
    runs = []
    page = 1
    while True:
        batch = api(base+'/actions/runs?head_sha='+sha+'&per_page=100&page='+str(page))['workflow_runs']
        runs.extend(batch)
        if len(batch) < 100: break
        page += 1
    latest = {}
    for run in runs:
        if run['head_branch'] != repo['default_branch'] or run['name'] == 'Notify profile': continue
        latest.setdefault(run['workflow_id'], run)
    try: release = api(base+'/releases/latest')
    except HTTPError as e:
        if e.code != 404: raise
        release = None
    return dict(name=repo['name'], sha=sha, changed=commit['commit']['committer']['date'],
                ci=ci_state(list(latest.values())), release=release['tag_name'] if release else 'No release',
                release_url=release['html_url'] if release else None,
                release_date=release['published_at'] if release else None, **totals, **origins)

def collect_projects(repos, api):
    with ThreadPoolExecutor(max_workers=3) as pool:
        return sorted(pool.map(lambda r:snapshot(r,api),repos), key=lambda r:r['name'].lower())

def markdown(projects):
    def safe(s): return str(s).replace('|','\\|').replace('\n',' ').replace('`','')
    rows=['\n## Project telemetry\n', 'Source counts describe repository contents, not personal authorship. Third-party code is separated below.\n']
    for p in projects:
        url='https://github.com/RaCzKoViC/'+p['name']
        rows.append('### ['+safe(p['name'])+']('+url+')\n')
        if p['name'] != 'RaCzKoViC':
            release='['+safe(p['release'])+']('+p['release_url']+')' if p['release_url'] else 'No stable release'
            rows.append(f"**CI:** [{p['ci']}]({url}/actions) · **Release:** {release}  ")
            rows.append(f"**Last change:** [{p['changed'][:16].replace('T',' ')} UTC]({url}/commit/{p['sha']})\n")
        rows.append(f"- Project source: **{p['source']:,}** nonblank lines")
        rows.append(f"- Documentation: **{p['documentation']:,}** · Configuration: **{p['configuration']:,}**")
        rows.append(f"- Bundled / adapted third-party source: **{p['dependency_source']:,}**")
        if p['baseline']:
            base=p['baseline']['commit']
            rows.append(f"- Retained upstream source: **{p['upstream_source']:,}**")
            rows.append(f"- Added / replaced source since import: **{p['project_source']:,}**")
            rows.append(f"\nCompared per file with [imported baseline `{base[:7]}`]({url}/blob/{p['sha']}/UPSTREAM_BASE). This measures surviving changes from the Lab distribution, including formatting and any later upstream imports; it does not prove who authored each line.\n")
        else:
            rows.append('\nNo imported upstream baseline is configured. Project source is not a verified personal-authorship count.\n')
    rows.append('\nCI uses the exact default-branch commit. Counts include comments and exclude blank lines, build output, binaries and the generated profile README. Remote packages, Docker images and CDN libraries are not downloaded or counted. [Method and exclusions](SETUP.md#counting-rules).\n')
    return '\n'.join(rows)
