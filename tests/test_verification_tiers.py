"""Offline regressions for the catalog and RuyiJS evidence-tier boundaries."""
import hashlib
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

import yaml

ROOT = Path(__file__).resolve().parents[1]
EVIDENCE_ROOT = 'RUYI_PLATFORM_EVIDENCE_ROOT'
RECEIPT = 'artifacts/receipts/ruyijs-fixture/validation.json'
COPY = b'{"record":"tracked receipt"}\n'
EXTERNAL = b'{"record":"external only"}\n'
WHEEL = b'fixture wheel bytes'


def sha(data):
    return hashlib.sha256(data).hexdigest()


class VerificationTiers(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.outer = Path(tmp.name)
        self.root = self.outer / 'ruyi-platform'
        self.root.mkdir()
        self.env = dict(os.environ, GIT_CONFIG_NOSYSTEM='1', GIT_CONFIG_GLOBAL=os.devnull,
                        GIT_ALLOW_PROTOCOL='', GIT_AUTHOR_NAME='Fixture', GIT_AUTHOR_EMAIL='fixture@example.invalid',
                        GIT_COMMITTER_NAME='Fixture', GIT_COMMITTER_EMAIL='fixture@example.invalid')
        self.env.pop(EVIDENCE_ROOT, None)
        self.git('init', '-q')
        (self.root / 'scripts').mkdir()
        for script in ('verify-pins.sh', 'verify-catalog.py', 'verify-ledger.py'):
            shutil.copyfile(ROOT / 'scripts' / script, self.root / 'scripts' / script)
        sources = {'ruyi-mcp': ('ruyi-mcp', 'public', '1' * 40),
                   'ruyihttp': ('ruyihttp', 'public', '2' * 40),
                   'ruyijs': ('ruyijs-inner', 'private', '3' * 40),
                   'ruyitrace': ('ruyitrace', 'private', '4' * 40)}
        self.status = dict(generated_at='fixture', baseline={'firefox_commit': '5' * 40}, projects={},
                           artifacts={}, blockers=[], submodules={})
        sections = []
        for name, (source, visibility, oid) in sources.items():
            path = f'submodules/{name}'
            slug = f'Facetomyself/{source}'
            url = f'https://github.com/{slug}' + ('.git' if name == 'ruyi-mcp' else '')
            self.status['projects'][name] = {'submodule': path, ('repo_inner' if name == 'ruyijs' else 'repo'): slug}
            self.status['submodules'][name] = dict(url=url, visibility=visibility, state='added', commit=oid)
            sections += [f'[submodule "{path}"]', f'\tpath = {path}', f'\turl = {url}']
            if name == 'ruyi-mcp':
                sections.append('\tbranch = linux')
                self.status['submodules'][name]['branch'] = 'linux'
            self.git('update-index', '--add', '--cacheinfo', f'160000,{oid},{path}')
        self.status['projects']['ruyijs']['verified'] = {
            'private_linux_x86_donor_source': {'guarded_build': {
                'with_copy': dict(evidence='deliverables/history/validation.json', evidence_sha256=sha(COPY),
                                  repository_receipt=RECEIPT, artifact_sha256=sha(WHEEL))}},
            'private_linux_aarch64_stages': {
                'external_only': dict(evidence='deliverables/arm/validation.json', evidence_sha256=sha(EXTERNAL))},
        }
        self.config = self.root / '.gitmodules'
        self.config.write_text('\n'.join(sections) + '\n')
        self.write_status()
        self.write_pins()
        self.receipt = self.root / RECEIPT
        self.receipt.parent.mkdir(parents=True)
        self.receipt.write_bytes(COPY)
        self.git('add', '--', '.gitmodules', 'PINS.md', 'STATUS.yaml', RECEIPT)

    def git(self, *args, cwd=None, stdin=None):
        return subprocess.run(['git', *args], cwd=cwd or self.root, env=self.env, check=True,
                              input=stdin, capture_output=True, text=True).stdout.strip()

    def run_command(self, *args, cwd=None, evidence_root=None):
        env = self.env.copy()
        if evidence_root is not None:
            env[EVIDENCE_ROOT] = str(evidence_root)
        return subprocess.run(args, cwd=cwd or self.root, env=env, capture_output=True, text=True, timeout=30)

    def pins(self, *args, **kwargs):
        return self.run_command('bash', 'scripts/verify-pins.sh', *args, **kwargs)

    def ledger(self, *args, **kwargs):
        return self.run_command('python3', '-B', 'scripts/verify-ledger.py', *args, **kwargs)

    def expect(self, result, status, *messages):
        output = result.stdout + result.stderr
        self.assertEqual(result.returncode, status, output)
        for message in messages:
            self.assertIn(message, output)
        return output

    def write_status(self):
        (self.root / 'STATUS.yaml').write_text(yaml.safe_dump(self.status, sort_keys=False))

    def write_pins(self):
        oid = self.status['submodules']['ruyi-mcp']['commit']
        (self.root / 'PINS.md').write_text('| ruyi-mcp | [Facetomyself/ruyi-mcp]'
                                         f'(https://github.com/Facetomyself/ruyi-mcp) | `linux` | `{oid}` |\n')

    def checkout(self, name):
        path = self.root / 'submodules' / name
        path.mkdir(parents=True)
        self.git('init', '-q', cwd=path)
        tree = self.git('mktree', stdin='', cwd=path)
        # Fabricate a fixture ref without cloning or invoking commit/push in the platform.
        oid = self.git('commit-tree', tree, '-m', f'fixture: {name}', cwd=path)
        self.git('update-ref', 'HEAD', oid, cwd=path)
        return oid

    def archive(self):
        for path, data in [('history/validation.json', COPY), ('arm/validation.json', EXTERNAL),
                           ('history/fixture.whl', WHEEL)]:
            file = self.outer / 'deliverables' / path
            file.parent.mkdir(parents=True, exist_ok=True)
            file.write_bytes(data)

    def test_catalog_without_checkouts_receipts_or_evidence(self):
        self.assertFalse((self.root / 'submodules').exists())
        self.receipt.unlink()
        result = self.pins('--catalog', evidence_root='ignored-relative-path')
        output = self.expect(result, 0, '4 gitlinks', 'recorded visibility: public', 'recorded visibility: private',
                             'source, receipts, and tests not checked')
        self.assertNotIn('JS ledger', output)

    def test_catalog_rejects_wrong_gitlink_sha_mode_and_set(self):
        path = 'submodules/ruyijs'
        oid = self.status['submodules']['ruyijs']['commit']
        blob = self.git('hash-object', '-w', '--stdin', stdin='not a submodule')
        for mode, candidate, message in [('160000', 'a' * 40, 'gitlink mode, stage or SHA'),
                                         ('100644', blob, 'parent gitlinks vs STATUS.yaml')]:
            with self.subTest(mode=mode):
                self.git('update-index', '--cacheinfo', f'{mode},{candidate},{path}')
                self.expect(self.pins('--catalog'), 1, path, message)
        self.git('update-index', '--cacheinfo', f'160000,{oid},{path}')
        self.git('update-index', '--add', '--cacheinfo', f'160000,{oid},extra-gitlink')
        self.expect(self.pins('--catalog'), 1, "unexpected=['extra-gitlink']")
        self.git('update-index', '--force-remove', '--', 'extra-gitlink', path)
        self.expect(self.pins('--catalog'), 1, f"missing=['{path}']")

    def test_catalog_rejects_each_registration_drift(self):
        config = self.config.read_text()
        for before, after, message in [('\tpath = submodules/ruyijs', '\tpath = submodules/wrong', 'path differs'),
                                       ('https://github.com/Facetomyself/ruyijs-inner',
                                        'https://github.com/Facetomyself/other', 'source URL differs'),
                                       ('[submodule "submodules/ruyijs"]', '[submodule "submodules/extra"]',
                                        '.gitmodules sections vs STATUS.yaml')]:
            with self.subTest(message=message):
                self.config.write_text(config.replace(before, after))
                self.expect(self.pins('--catalog'), 1, message)
        self.config.write_text(config)
        project = self.status['projects']['ruyijs']
        path = project.pop('submodule')
        self.write_status()
        self.expect(self.pins('--catalog'), 1, 'project submodule registrations', 'ruyijs')
        project['submodule'] = path
        project['repo_inner'] = 'Facetomyself/wrong'
        self.write_status()
        self.expect(self.pins('--catalog'), 1, 'source URL differs', 'ruyijs')
        project['repo_inner'] = 'Facetomyself/ruyijs-inner'
        self.status['submodules']['ruyijs'].pop('visibility')
        self.write_status()
        self.expect(self.pins('--catalog'), 1, 'missing or invalid visibility', 'ruyijs')

    def test_catalog_rejects_mcp_pin_url_sha_and_missing_row(self):
        pins = self.root / 'PINS.md'
        good = pins.read_text()
        for bad in (good.replace('/ruyi-mcp)', '/wrong)'), good.replace('1' * 40, 'a' * 40), '', good * 2):
            with self.subTest(row=bad):
                pins.write_text(bad)
                self.expect(self.pins('--catalog'), 1, 'PINS.md:')

    def test_repo_rejects_missing_or_mismatched_checkout(self):
        path = self.root / 'submodules' / 'ruyijs'
        path.mkdir(parents=True)
        output = self.expect(self.pins('--repo'), 1, 'submodules/ruyijs: submodule checkout missing')
        self.assertNotIn('JS ledger', output)
        self.git('init', '-q', cwd=path)
        tree = self.git('mktree', stdin='', cwd=path)
        oid = self.git('commit-tree', tree, '-m', 'different source', cwd=path)
        self.git('update-ref', 'HEAD', oid, cwd=path)
        self.expect(self.pins('--repo'), 1, f'checkout SHA {oid} differs from pinned SHA')

    def test_repo_receipt_damage_and_block_shape_are_rejected(self):
        opts = {'evidence_root': 'ignored-relative-path'}
        result = self.ledger('--repo', **opts)
        self.expect(result, 0, 'repository receipt SHA-256 verified: 1', 'external originals not checked (2',
                    '1 entries without a repository copy', 'secondary hash provenance not checked (1)')
        self.receipt.write_bytes(COPY + b'changed')
        self.expect(self.ledger('--repo', **opts), 1, 'repository receipt SHA-256 differs')
        self.receipt.write_bytes(COPY)
        scopes = self.status['projects']['ruyijs']['verified']
        record = scopes['private_linux_x86_donor_source']['guarded_build']['with_copy']
        record['artifact_sha256'] = 'a' * 63
        self.write_status()
        self.expect(self.ledger('--repo', **opts), 1, 'artifact_sha256 is not a SHA-256 digest')
        record['artifact_sha256'] = sha(WHEEL)
        record['repository_receipt'] = '../external.json'
        self.write_status()
        self.expect(self.ledger('--repo', **opts), 1, 'repository_receipt must be a relative file path')
        record['repository_receipt'] = RECEIPT
        scopes['private_linux_x86_donor_source']['guarded_build']['damaged_record'] = False
        self.write_status()
        self.expect(self.ledger('--repo', **opts), 1, 'damaged_record: block: expected a non-empty mapping')

    def test_full_fails_without_external_evidence(self):
        for name, item in self.status['submodules'].items():
            oid = self.checkout(name)
            item['commit'] = oid
            self.git('update-index', '--cacheinfo', f'160000,{oid},submodules/{name}')
        self.write_status()
        self.write_pins()
        # Use the actual shell entry point: all checkouts are present, but no
        # parent receipts may stand in for the explicitly selected originals.
        missing = self.outer / 'missing archive'
        output = self.expect(self.pins('--full', '--evidence-root', str(missing)), 1,
                             'external evidence root missing or not a directory', str(missing),
                             'full 验收有失败项')
        self.assertNotIn('repo 验收通过', output)
        self.expect(self.ledger('--full'), 1, 'external evidence missing at', 'secondary hashes traced: 0')

    def test_full_default_layouts_and_explicit_precedence(self):
        self.archive()
        self.expect(self.ledger(), 0, 'secondary hashes traced: 1', 'byte-identical to originals')
        acceptance = self.outer / 'acceptance' / 'platform-maint'
        shutil.copytree(self.root, acceptance)
        self.expect(self.ledger('--full', cwd=acceptance), 0, f'JS external evidence root: {self.outer}')
        missing = self.outer / 'wrong'
        self.expect(self.ledger('--full', evidence_root=missing), 1, str(missing))
        self.expect(self.ledger('--full', '--evidence-root', str(self.outer), evidence_root=missing),
                    0, 'byte-identical to originals')

    def test_help_and_invalid_arguments(self):
        self.expect(self.pins('--help'), 0, '--catalog', '--repo', '--full', '--evidence-root', EVIDENCE_ROOT)
        for args in [('--whatever',), ('--catalog', '--repo'), ('--full', '--evidence-root'),
                     ('--full', '--evidence-root', 'relative'), ('--repo', '--evidence-root', '/absolute')]:
            with self.subTest(args=args):
                self.expect(self.pins(*args), 2, '参数错误')


if __name__ == '__main__':
    unittest.main()
