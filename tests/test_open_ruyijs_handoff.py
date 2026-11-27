"""Verify the public fork's pinned source, without initializing or running Firefox."""
import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[1]


class OpenRuyiJSHandoff(unittest.TestCase):
    def test_integrated_upstream_and_firefox_gitlink(self):
        status = yaml.safe_load((ROOT / 'STATUS.yaml').read_bytes())
        project = status['projects']['ff-ruyijs']
        registration = status['submodules']['ff-ruyijs']
        path = ROOT / project['submodule']
        pin = registration['commit']
        self.assertEqual(project['relationship'], 'maintained_open_source_fork')
        self.assertEqual(set(project['downstream_scope']), {'performance', 'macos_compatibility', 'linux_compatibility'})
        self.assertIs(project['private_product_source'], False)
        self.assertEqual(subprocess.check_output(['git', '-C', path, 'rev-parse', 'HEAD'], text=True).strip(), pin)
        subprocess.run(['git', '-C', path, 'merge-base', '--is-ancestor', project['upstream_integrated'], pin], check=True)
        tree = subprocess.check_output(['git', '-C', path, 'ls-tree', pin, '--', 'firefox'], text=True)
        self.assertEqual(tree.strip(), f"160000 commit {project['firefox_gitlink']}\tfirefox")
        url = subprocess.check_output(['git', '-C', path, 'config', '--blob', f'{pin}:.gitmodules',
                                       '--get', 'submodule.firefox.url'], text=True)
        self.assertEqual(url.strip(), 'https://github.com/mozilla-firefox/firefox.git')

    def test_sync_public_needs_neither_private_access_nor_nested_firefox(self):
        # Only local fixture repositories are reachable. The nested URL is deliberately absent.
        with tempfile.TemporaryDirectory() as tmp:
            work = Path(tmp)
            env = dict(os.environ, HOME=tmp, GIT_CONFIG_GLOBAL=str(work / 'gitconfig'), GIT_CONFIG_NOSYSTEM='1',
                       GIT_ALLOW_PROTOCOL='file', GIT_TERMINAL_PROMPT='0', GIT_AUTHOR_NAME='Fixture',
                       GIT_AUTHOR_EMAIL='fixture@example.invalid', GIT_COMMITTER_NAME='Fixture',
                       GIT_COMMITTER_EMAIL='fixture@example.invalid')
            # Platform gates can disable transports in their own environment; use isolated fixture Git settings.
            def run(cwd, *cmd):
                return subprocess.run(cmd, cwd=cwd, env=env, capture_output=True, text=True,
                                      timeout=20, check=True).stdout.strip()
            (work / 'gitconfig').write_text('[submodule]\n\trecurse = true\n', encoding='utf-8')
            child, parent = work / 'public-child', work / 'platform'
            for repo in (child, parent):
                repo.mkdir()
                run(repo, 'git', 'init', '-q')
            def register(repo, path, url, sha):
                for field, val in [('path', path), ('url', url)]:
                    run(repo, 'git', 'config', '-f', '.gitmodules', f'submodule.{path}.{field}', val)
                run(repo, 'git', 'update-index', '--add', '--cacheinfo', f'160000,{sha},{path}')
            register(child, 'firefox', (work/'absent-firefox').as_uri(), '1' * 40)
            run(child, 'git', 'add', '.gitmodules')
            run(child, 'git', 'commit', '-qm', 'nested source declaration')
            revision = run(child, 'git', 'rev-parse', 'HEAD')
            public = ('ff-ruyijs', 'ruyihttp', 'ruyi-mcp')
            private = ('ruyijs', 'ruyitrace', 'ruyidom')
            for name in (*public, *private):
                url = (child if name in public else work/'absent-private').as_uri()
                register(parent, f'submodules/{name}', url, revision)
            (parent/'scripts').mkdir()
            shutil.copyfile(ROOT/'scripts/sync-submodules.sh', parent/'scripts/sync-submodules.sh')
            run(parent, 'git', 'add', '.gitmodules', 'scripts/sync-submodules.sh')
            run(parent, 'git', 'commit', '-qm', 'fixture catalog')
            run(parent, 'bash', 'scripts/sync-submodules.sh', '--public')
            for name in public:
                checkout = parent/'submodules'/name
                self.assertEqual(run(checkout, 'git', 'rev-parse', 'HEAD'), revision)
                self.assertFalse((checkout/'firefox/.git').exists())
            for name in private:
                self.assertFalse((parent/'submodules'/name/'.git').exists())


if __name__ == '__main__':
    unittest.main()
