"""Offline checks for the independently released RuyiDOM product and its operator handoff."""
import hashlib
import json
from pathlib import Path
import subprocess
import unittest

import yaml

ROOT = Path(__file__).resolve().parents[1]


class RuyiDOMHandoff(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.book = yaml.safe_load((ROOT / 'STATUS.yaml').read_text(encoding='utf-8'))
        cls.entry = cls.book['related_projects']['ruyidom']
        cls.body = (ROOT / cls.entry['evidence']).read_bytes()
        cls.receipt = json.loads(cls.body)

    def test_release_and_operator_sources_are_separate(self):
        e = self.entry
        self.assertEqual(e['relationship'], 'independent_release')
        self.assertIsNone(e['platform_gitlink'])
        self.assertNotIn('ruyidom', self.book['submodules'])
        self.assertEqual(subprocess.check_output(['git', 'ls-files', '--stage', '--', 'submodules/ruyidom'], cwd=ROOT), b'')
        repo, ref, operator = e['repository'], e['release_commit'], e['arm64_deployment']['operator_commit']
        self.assertRegex(ref, r'^[a-f0-9]{40}$')
        self.assertRegex(operator, r'^[a-f0-9]{40}$')
        pins = (ROOT / 'PINS.md').read_text(encoding='utf-8')
        handoff = (ROOT / 'docs/14-source-handoff.md').read_text(encoding='utf-8')
        self.assertIn(f'{repo}/tree/{ref}', pins)
        self.assertIn(f'{repo}/releases/tag/{e["release_tag"]}', handoff)
        self.assertIn(f'sha={ref}', handoff)
        self.assertIn(f'{repo}/blob/{operator}/deploy/arm64/README.md', handoff)

    def test_current_state_matches_frozen_qualification(self):
        e, r = self.entry, self.receipt
        self.assertEqual(hashlib.sha256(self.body).hexdigest(), e['evidence_sha256'])
        self.assertEqual(r['schema'], 'ruyidom-arm64-source-release-v1')
        arm = e['arm64_deployment']
        self.assertEqual((arm['host'], arm['image_id'], arm['renderer']),
                         (r['nativeGeckoSourceHost'], r['ociImageId'], r['maintainedProfile']))
        self.assertEqual(r['trustedScriptHost'], '136.0')
        self.assertEqual(set(r['mach']), {'configure', 'build', 'package'})
        self.assertTrue(all(x['exit'] == 0 for x in r['mach'].values()))
        self.assertEqual(r['qa'].get('browser-nav'), 0)
        self.assertEqual(r['browserFull']['fail'] + r['browserFull']['unsupported'], [])
        self.assertIn('redirect-csp', r['browserFull']['pass'])
        self.assertIs(r['delivery']['reloadImageIdMatches'], True)
        self.assertNotIn('native_arm64_docker_release_validation', e['pending'])
        self.assertTrue((ROOT / e['historical_v0_1_handoff']).is_file())


if __name__ == '__main__':
    unittest.main()
