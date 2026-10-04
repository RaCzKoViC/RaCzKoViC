"""Count source provenance relative to an explicitly recorded imported baseline."""
import json
import re
import tarfile
import urllib.request
from difflib import SequenceMatcher
from pathlib import PurePosixPath

DEPENDENCY_DIRS = {'node_modules', 'vendor', 'third_party', 'third-party', 'external', 'site-packages'}
ADAPTED_PREFIXES = ('services/hwfit/', 'services/research/', 'services/search/')
ADAPTED_FILES = {'routes/hwfit_routes.py', 'routes/research_routes.py', 'src/research_handler.py', 'scripts/odysseus-cookbook'}

def dependency(repo, path):
    if any(part in DEPENDENCY_DIRS for part in PurePosixPath(path).parts): return True
    if repo == 'Odysseus-Lab':
        return (path.startswith('static/lib/') or path.startswith(ADAPTED_PREFIXES)
                or path in ADAPTED_FILES or path.startswith('routes/cookbook_')
                or path.startswith('static/js/cookbook'))
    return False

def archive_files(full_name, sha):
    req = urllib.request.Request('https://api.github.com/repos/'+full_name+'/tarball/'+sha,
                                 headers={'User-Agent':'profile-telemetry'})
    files = {}
    with urllib.request.urlopen(req, timeout=120) as response:
        with tarfile.open(fileobj=response, mode='r|gz') as archive:
            for member in archive:
                if not member.isfile() or member.size > 10_000_000: continue
                path = '/'.join(PurePosixPath(member.name).parts[1:])
                data = archive.extractfile(member).read()
                if b'\0' in data: continue
                try: files[path] = data.decode('utf-8-sig')
                except UnicodeDecodeError: continue
    return files

def source_split(current, baseline):
    """Unchanged matched lines versus surviving added/replaced lines, per path."""
    current = [line for line in current.splitlines() if line.strip()]
    baseline = [line for line in baseline.splitlines() if line.strip()]
    if current == baseline: return len(current), 0
    inherited = sum(match.size for match in SequenceMatcher(None, baseline, current, autojunk=False).get_matching_blocks())
    return inherited, len(current) - inherited

def provenance(repo, files, category, source_extensions):
    baseline_info = None
    if repo['name'] == 'Odysseus-Lab':
        baseline_info = json.loads(files['UPSTREAM_BASE'])
        if baseline_info['repository'] != 'https://github.com/odysseus-dev/odysseus':
            raise ValueError('Unexpected upstream repository')
        if not re.fullmatch('[0-9a-f]{40}', baseline_info['commit']):
            raise ValueError('Invalid upstream baseline SHA')
        baseline = archive_files('odysseus-dev/odysseus', baseline_info['commit'])
    else: baseline = {}
    result = dict(project_source=0, upstream_source=0, dependency_source=0, baseline=baseline_info)
    for path, text in files.items():
        # Dependency folders are measured separately, even if category excludes them.
        kind = category(path)
        if dependency(repo['name'], path):
            if PurePosixPath(path).suffix.lower().lstrip('.') in source_extensions:
                result['dependency_source'] += sum(bool(line.strip()) for line in text.splitlines())
            continue
        if kind != 'source': continue
        if baseline_info:
            inherited, local = source_split(text, baseline.get(path, ''))
            result['upstream_source'] += inherited
            result['project_source'] += local
        else:
            result['project_source'] += sum(bool(line.strip()) for line in text.splitlines())
    return result
