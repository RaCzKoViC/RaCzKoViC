import copy
import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))

import portfolio
from generate_stats import update_readme


def repo(name, **extra):
    meta = {'name': name, 'html_url': f'https://github.com/RaCzKoViC/{name}', 'private': False,
            'fork': False, 'archived': False, 'description': f'{name} project', 'homepage': None,
            'topics': [], 'language': 'Python', 'stars': 0, 'pages_url': None, 'ci': 'Passed',
            'release': 'No release', 'release_url': None, 'release_date': None,
            'changed': '2026-10-04T10:00:00Z', 'sha': 'a' * 40}
    meta.update(extra)
    return meta


CONFIG = {'heading': 'Featured portfolio', 'topics_limit': 2, 'featured': [
    {'repo': 'Game', 'title': 'The Game', 'kind': 'sandbox game', 'summary': 'Hand-written *summary*.',
     'body': '**Play:** [latest]({{latest_release}}) · [site]({{website}}) · {{release_tag}}'},
    {'repo': 'Secret', 'kind': 'not public yet', 'summary': 'Must not leak.'}],
    'more': {'enabled': True, 'heading': 'More public projects', 'exclude': ['RaCzKoViC']}}


def repos():
    return {'Game': repo('Game', description='Dig deep', homepage='https://example.org/game/',
                         topics=['a', 'b', 'c'], release='v1.2.0', stars=3,
                         release_url='https://github.com/RaCzKoViC/Game/releases/tag/v1.2.0',
                         release_date='2026-10-01T12:00:00Z'),
            'Secret': repo('Secret', private=True),
            'Tool': repo('Tool', description='Tool — handy [tool] | fast', pages_url='https://raczkovic.github.io/Tool/'),
            'Old': repo('Old', archived=True),
            'RaCzKoViC': repo('RaCzKoViC')}


class PortfolioConfigTests(unittest.TestCase):
    def test_repository_config_is_valid_and_keeps_featured_order(self):
        config = portfolio.load_config(ROOT / 'portfolio.yml')
        self.assertEqual([e['repo'] for e in config['featured']], ['RacOS', 'The-MinerGuy', 'Odysseus-Lab'])
        self.assertIn('RaCzKoViC', config['more']['exclude'])

    def test_invalid_config_is_rejected(self):
        for bad in [{}, {'featured': [{'kind': 'x'}]},
                    {'featured': [{'repo': 'A'}, {'repo': 'A'}]},
                    {'featured': [{'repo': 'A', 'typo': 1}]},
                    {'featured': [{'repo': 'A', 'body': '{{nope}}'}]}]:
            with self.assertRaises(ValueError, msg=bad):
                portfolio.validate_config(bad)

    def test_readme_has_one_generated_block_under_the_existing_anchor(self):
        readme = (ROOT / 'README.md').read_text(encoding='utf-8')
        self.assertEqual(readme.count(portfolio.START), 1)
        self.assertEqual(readme.count(portfolio.END), 1)
        block = readme[readme.index(portfolio.START):readme.index(portfolio.END)]
        self.assertIn('## Featured portfolio', block)
        self.assertIn('(#featured-portfolio)', readme)


class PortfolioRenderTests(unittest.TestCase):
    def test_render_is_deterministic_and_keeps_manual_text(self):
        first = portfolio.render(CONFIG, repos())
        self.assertEqual(first, portfolio.render(copy.deepcopy(CONFIG), repos()))
        self.assertIn('### [The Game](https://github.com/RaCzKoViC/Game) · sandbox game', first)
        self.assertIn('Hand-written *summary*.', first)
        self.assertTrue(first.startswith(portfolio.START) and first.endswith(portfolio.END))

    def test_live_metadata_is_shown(self):
        out = portfolio.render(CONFIG, repos())
        self.assertIn('_Dig deep_', out)
        self.assertIn('Release [v1.2.0](https://github.com/RaCzKoViC/Game/releases/tag/v1.2.0) (2026-10-01)', out)
        self.assertIn('CI: [Passed](https://github.com/RaCzKoViC/Game/actions)', out)
        self.assertIn('★ 3', out)
        self.assertIn('[Website](https://example.org/game/)', out)
        self.assertIn('Last change [2026-10-04](https://github.com/RaCzKoViC/Game/commit/' + 'a' * 40 + ')', out)
        self.assertIn('**Topics:** `a` `b` +1 more', out)
        self.assertIn('[latest](https://github.com/RaCzKoViC/Game/releases/latest) · [site](https://example.org/game/) · v1.2.0', out)

    def test_metadata_changes_change_the_block(self):
        before = portfolio.render(CONFIG, repos())
        for field, value in [('description', 'New tagline'), ('homepage', 'https://new.example/'),
                             ('topics', ['z']), ('stars', 9), ('ci', 'Failed'), ('release', 'v2.0.0'),
                             ('changed', '2026-10-05T00:00:00Z')]:
            data = repos()
            data['Game'][field] = value
            self.assertNotEqual(before, portfolio.render(CONFIG, data), field)

    def test_private_archived_and_excluded_repositories_are_hidden(self):
        out = portfolio.render(CONFIG, repos())
        self.assertNotIn('Secret', out)
        self.assertNotIn('Must not leak', out)
        self.assertNotIn('[Old]', out)
        self.assertNotIn('[RaCzKoViC]', out)

    def test_newly_published_repository_appears_automatically(self):
        data = repos()
        self.assertNotIn('[Secret]', portfolio.render(CONFIG, data))
        data['Secret']['private'] = False
        out = portfolio.render(CONFIG, data)
        self.assertIn('### [Secret](https://github.com/RaCzKoViC/Secret) · not public yet', out)
        data['Brand-New'] = repo('Brand-New', description='Fresh')
        out = portfolio.render(CONFIG, data)
        self.assertIn('- **[Brand-New](https://github.com/RaCzKoViC/Brand-New)** — Fresh', out)
        self.assertLess(out.index('[Brand-New]'), out.index('[Tool]'))

    def test_more_list_escapes_text_and_drops_repeated_name(self):
        out = portfolio.render(CONFIG, repos())
        self.assertIn('**[Tool](https://github.com/RaCzKoViC/Tool)** — handy \\[tool\\] \\| fast', out)
        self.assertIn('[Website](https://raczkovic.github.io/Tool/)', out)

    def test_placeholders_fall_back_without_release_or_website(self):
        data = repos()
        data['Game'].update(homepage='https://github.com/RaCzKoViC/Game#readme', release_url=None,
                            release='No release', pages_url=None)
        out = portfolio.render(CONFIG, data)
        self.assertIn('[latest](https://github.com/RaCzKoViC/Game/releases) · [site](https://github.com/RaCzKoViC/Game) · no release yet', out)
        self.assertIn('No release yet', out)
        self.assertNotIn('[Website]', out.split('### More')[0])

    def test_replace_block_requires_exactly_one_block(self):
        with self.assertRaises(ValueError):
            portfolio.replace_block('no markers', 'x')
        doubled = (portfolio.START + portfolio.END) * 2
        with self.assertRaises(ValueError):
            portfolio.replace_block(doubled, 'x')


class ReadmeUpdateTests(unittest.TestCase):
    VALUES = dict(lines=10, documentation=2, configuration=1, repos=3, stars=3, followers=1, forks=0, projects=[])
    PORTRAIT = ('x' * 48 + '\n') * 36

    def readme(self, updated='2026-10-04 05:00'):
        skeleton = ('intro\n<!-- PROFILE:START -->\n<!-- PROFILE:END -->\n\n' + portfolio.START + '\n'
                    + portfolio.END + '\n\n<!-- TELEMETRY:START -->\n<!-- TELEMETRY:END -->\n')
        return update_readme(skeleton, self.VALUES, repos(), CONFIG, updated, self.PORTRAIT)

    def test_unchanged_data_leaves_readme_byte_identical(self):
        first = self.readme()
        again = update_readme(first, json.loads(json.dumps(self.VALUES)), repos(), CONFIG,
                              '2030-01-01 00:00', self.PORTRAIT)
        self.assertEqual(first, again)
        self.assertNotIn('2030-01-01', again)

    def test_portfolio_only_change_keeps_terminal_timestamp(self):
        first = self.readme()
        data = repos()
        data['Game']['description'] = 'Changed tagline'
        second = update_readme(first, self.VALUES, data, CONFIG, '2030-01-01 00:00', self.PORTRAIT)
        self.assertIn('_Changed tagline_', second)
        self.assertNotIn('2030-01-01', second)
        head = lambda s: s[:s.index(portfolio.START)]
        self.assertEqual(head(first), head(second))


if __name__ == '__main__':
    unittest.main()


class ProfileSelfSnapshotTests(unittest.TestCase):
    def test_profile_repository_snapshot_ignores_its_own_head(self):
        from unittest.mock import patch
        import project_telemetry

        def api(path):
            if '/commits/' in path:
                return {'sha': 'b' * 40, 'commit': {'committer': {'date': '2026-10-04T19:41:04Z'}}}
            raise AssertionError('no run or release lookups for the profile itself: ' + path)

        repo = {'name': 'RaCzKoViC', 'full_name': 'RaCzKoViC/RaCzKoViC', 'default_branch': 'main'}
        with patch('project_telemetry.archive_files', return_value={'README.md': 'x\n', 'a.py': 'y\n'}):
            snap = project_telemetry.snapshot(repo, api)
        self.assertEqual((snap['sha'], snap['changed'], snap['ci']), (None, None, None))
        self.assertEqual(snap['source'], 1)
        self.assertEqual(snap['documentation'], 0)
