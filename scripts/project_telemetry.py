"""Snapshot classified, nonblank physical lines at each default-branch SHA."""
import tarfile
import urllib.request
from pathlib import PurePosixPath
from concurrent.futures import ThreadPoolExecutor
from urllib.error import HTTPError

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
    req = urllib.request.Request('https://api.github.com'+base+'/tarball/'+sha, headers={'User-Agent':'profile-telemetry'})
    with urllib.request.urlopen(req, timeout=120) as response:
        with tarfile.open(fileobj=response, mode='r|gz') as archive:
            for member in archive:
                if not member.isfile() or member.size > 10_000_000: continue
                path = '/'.join(PurePosixPath(member.name).parts[1:])
                kind = category(path)
                # Generated README excluded to avoid a self-referential counter.
                if not kind or (repo['name'] == 'RaCzKoViC' and path == 'README.md'): continue
                data = archive.extractfile(member).read()
                if b'\0' in data: continue
                try: text = data.decode('utf-8-sig')
                except UnicodeDecodeError: continue
                totals[kind] += sum(bool(line.strip()) for line in text.splitlines())
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
                release_url=release['html_url'] if release else None, **totals)

def collect_projects(repos, api):
    with ThreadPoolExecutor(max_workers=3) as pool:
        return sorted(pool.map(lambda r:snapshot(r,api),repos), key=lambda r:r['name'].lower())

def markdown(projects):
    def safe(s): return str(s).replace('|','\\|').replace('\n',' ').replace('`','')
    rows=['\n### Project status\n', '| Project | CI · default branch | Latest release | Last change · UTC |', '|---|---|---|---|']
    for p in projects:
        if p['name']=='RaCzKoViC': continue
        url='https://github.com/RaCzKoViC/'+p['name']
        release='['+safe(p['release'])+']('+p['release_url']+')' if p['release_url'] else 'No release'
        rows.append(f"| [{safe(p['name'])}]({url}) | [{p['ci']}]({url}/actions) | {release} | [{p['changed'][:16].replace('T',' ')}]({url}/commit/{p['sha']}) |")
    rows += ['\nCI refers to the exact default-branch commit; notification workflows are excluded. No release means no published stable GitHub release.\n', '### Lines by project\n', '| Project | Source | Documentation | Configuration |','|---|---:|---:|---:|']
    for p in projects: rows.append(f"| {safe(p['name'])} | {p['source']:,} | {p['documentation']:,} | {p['configuration']:,} |")
    rows.append('\nNonblank physical lines, including comments, at the listed commits. Generated/build/dependency directories and the generated profile README are excluded; binaries and unclassified files are not counted. [Counting rules](SETUP.md#counting-rules).\n')
    return '\n'.join(rows)
