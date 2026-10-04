"""Render the Featured portfolio from portfolio.yml and live repository metadata.

Rendering is a pure function of its inputs (no clock, no randomness), so an
unchanged configuration and unchanged GitHub data produce a byte-identical block
and the workflow does not commit.
"""
import re
from pathlib import Path

OWNER = 'RaCzKoViC'
START = '<!-- PORTFOLIO:START -->'
END = '<!-- PORTFOLIO:END -->'
PLACEHOLDER = re.compile(r'\{\{\s*(\w+)\s*\}\}')
PLACEHOLDERS = {'repo_url', 'website', 'latest_release', 'release_tag'}
ENTRY_KEYS = {'repo', 'title', 'kind', 'summary', 'tagline', 'body'}


def load_config(path):
    import yaml  # imported lazily so telemetry-only tests do not need PyYAML
    config = yaml.safe_load(Path(path).read_text(encoding='utf-8'))
    validate_config(config)
    return config


def validate_config(config):
    if not isinstance(config, dict) or not isinstance(config.get('featured'), list):
        raise ValueError('portfolio.yml needs a "featured" list')
    seen = set()
    for entry in config['featured']:
        if not isinstance(entry, dict) or not isinstance(entry.get('repo'), str):
            raise ValueError(f'Featured entry needs a repository name: {entry!r}')
        unknown = set(entry) - ENTRY_KEYS
        if unknown:
            raise ValueError(f"Unknown keys for {entry['repo']}: {sorted(unknown)}")
        if entry['repo'] in seen:
            raise ValueError(f"Duplicate featured repository: {entry['repo']}")
        seen.add(entry['repo'])
        for name in PLACEHOLDER.findall(entry.get('body') or ''):
            if name not in PLACEHOLDERS:
                raise ValueError(f"Unknown placeholder {{{{{name}}}}} in {entry['repo']}")
    more = config.get('more', {})
    if not isinstance(more, dict) or not isinstance(more.get('exclude', []), list):
        raise ValueError('"more" must be a mapping with an "exclude" list')


def text(value):
    """Make a one-line plain string safe inside Markdown prose."""
    value = ' '.join(str(value or '').split())
    value = value.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
    return re.sub(r'([\\`*_\[\]|])', r'\\\1', value)


def website(meta):
    homepage = (meta.get('homepage') or '').strip()
    if homepage.startswith(('https://', 'http://')) and not homepage.startswith('https://github.com/'):
        return homepage
    return meta.get('pages_url') or None


def visible(meta):
    return bool(meta) and not meta.get('private') and not meta.get('fork') and not meta.get('archived')


def status_line(meta):
    url = meta['html_url']
    parts = []
    if meta.get('language'):
        parts.append(text(meta['language']))
    if meta.get('release_url'):
        released = f" ({meta['release_date'][:10]})" if meta.get('release_date') else ''
        parts.append(f"Release [{text(meta['release'])}]({meta['release_url']}){released}")
    else:
        parts.append('No release yet')
    if meta.get('ci'):
        parts.append(f"CI: [{text(meta['ci'])}]({url}/actions)")
    if meta.get('stars'):
        parts.append(f"★ {meta['stars']:,}")
    site = website(meta)
    if site:
        parts.append(f'[Website]({site})')
    if meta.get('changed') and meta.get('sha'):
        parts.append(f"Last change [{meta['changed'][:10]}]({url}/commit/{meta['sha']})")
    return ' · '.join(parts)


def topics_line(meta, limit):
    topics = list(meta.get('topics') or [])
    if not topics:
        return None
    shown = ' '.join(f'`{t}`' for t in topics[:limit])
    rest = len(topics) - limit
    return '**Topics:** ' + shown + (f' +{rest} more' if rest > 0 else '')


def fill(body, meta):
    url = meta['html_url']
    values = {'repo_url': url,
              'website': website(meta) or url,
              'latest_release': meta.get('release_url') and f'{url}/releases/latest' or f'{url}/releases',
              'release_tag': meta.get('release') if meta.get('release_url') else 'no release yet'}
    return PLACEHOLDER.sub(lambda m: values[m.group(1)], body)


def featured_section(entry, meta, limit):
    title = entry.get('title') or entry['repo']
    heading = f"### [{text(title)}]({meta['html_url']})"
    if entry.get('kind'):
        heading += ' · ' + text(entry['kind'])
    parts = [heading]
    description = ' '.join((meta.get('description') or '').split())
    summary = ' '.join((entry.get('summary') or '').split()) or description
    show_tagline = entry.get('tagline', True) and description and description not in {
        meta['name'], title, summary}
    if show_tagline:
        parts.append('_' + text(description) + '_')
    if summary:
        parts.append(summary if entry.get('summary') else text(summary))
    parts.append('**Status:** ' + status_line(meta))
    topics = topics_line(meta, limit)
    if topics:
        parts.append(topics)
    body = (entry.get('body') or '').strip()
    if body:
        parts.append(fill(body, meta))
    return '\n\n'.join(parts)


def strip_name(name, description):
    """Drop a leading "Name — " that repeats the linked repository name."""
    description = ' '.join((description or '').split())
    match = re.match(re.escape(name) + r'\s*[—–:-]\s*(.+)', description)
    if match:
        return match.group(1)
    return '' if description == name else description


def more_line(meta):
    line = f"- **[{text(meta['name'])}]({meta['html_url']})**"
    description = strip_name(meta['name'], meta.get('description'))
    if description:
        line += ' — ' + text(description)
    return line + '  \n  ' + status_line(meta)


def render(config, repos):
    """config: parsed portfolio.yml; repos: {name: metadata} for owned repositories."""
    validate_config(config)
    limit = int(config.get('topics_limit', 6))
    sections = [f"## {config.get('heading', 'Featured portfolio')}"]
    featured = set()
    for entry in config['featured']:
        featured.add(entry['repo'])
        meta = repos.get(entry['repo'])
        if visible(meta):
            sections.append(featured_section(entry, meta, limit))
    more = config.get('more', {})
    if more.get('enabled', True):
        skip = featured | set(more.get('exclude', []))
        others = sorted((m for n, m in repos.items() if n not in skip and visible(m)),
                        key=lambda m: m['name'].lower())
        if others:
            sections.append(f"### {more.get('heading', 'More public projects')}\n\n"
                            + '\n'.join(more_line(m) for m in others))
    return START + '\n' + '\n\n'.join(sections) + '\n' + END


def replace_block(readme, block):
    pattern = re.compile(re.escape(START) + r'.*?' + re.escape(END), re.S)
    if len(pattern.findall(readme)) != 1:
        raise ValueError('Expected exactly one generated portfolio block')
    return pattern.sub(lambda _: block, readme)
