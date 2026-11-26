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

    def test_second_arm_restore_has_separate_pinned_evidence(self):
        e, original = self.entry, self.receipt
        followup = e['arm64_second_host_restore']
        self.assertEqual(hashlib.sha256(self.body).hexdigest(),
                         'bea6ca613783071c68005dfa86b7faef738187fe3460dc2f25ec24e15864caee')
        self.assertNotEqual(followup['evidence'], e['evidence'])
        body = (ROOT / followup['evidence']).read_bytes()
        self.assertEqual(hashlib.sha256(body).hexdigest(), followup['evidence_sha256'])
        restored = json.loads(body)
        self.assertEqual(restored['schema'], 'ruyidom-v030-second-arm-cold-navigation-v1')
        self.assertEqual(followup['scope'], 'empty_store_import_and_real_navigation')
        self.assertEqual((followup['host'], restored['receiver'], restored['receiverMachine'], restored['architecture']),
                         ('oracle-dsh', 'oracle-dsh', 'aarch64', 'linux/arm64'))
        self.assertEqual(restored['buildHost'], original['nativeGeckoSourceHost'])
        self.assertNotEqual(restored['receiver'], restored['buildHost'])
        name = next(name for name in original['delivery']['artifacts'] if name.endswith('.docker.tar.gz'))
        archive = original['delivery']['artifacts'][name]
        self.assertEqual(restored['localArchive'], {'bytes': archive['bytes'], 'measured_sha256': archive['sha256']})
        self.assertEqual((restored['configSHA256'], restored['tagInArchive'], restored['renderer']),
                         (original['ociImageId'], original['retainedImageTag'], original['maintainedProfile']))
        self.assertEqual(restored['manifestSHA256'],
                         'sha256:1c35c2a41300a62b03c2c8a8d0ccd26a18f97edfebaf9dfcf26e5636ae89f377')
        self.assertEqual(restored['emptyBeforeLoad'], dict.fromkeys((
            'containerdImages', 'containers', 'contentRecords', 'dockerImages', 'overlaySnapshots', 'physicalBlobs'), 0))
        self.assertEqual(restored['storeAfterLoad']['verifiedRootFSLayers'], 7)
        self.assertIs(restored['offlineEngine'], True)
        self.assertEqual(restored['nativeSerializationCasesPassed'], 10)
        self.assertIs(restored['coldRestoreAndRealNavigationPassed'], True)
        for key in ('noRemainingJobContainers', 'primaryDockerAndServicesUnchanged', 'privateStoreRemoved'):
            self.assertIs(restored[key], True)
        self.assertEqual([test['budgetMs'] for test in restored['navigation']], [15000, 75000])
        for test in restored['navigation']:
            self.assertEqual(test['requests'], ['GET /start', 'GET /page', 'GET /external.js'])
            self.assertEqual((test['finalPath'], test['blockedInlineScripts']), ('/page', 2))
            self.assertIs(test['freshExternalValueAndNonceMatched'], True)
            self.assertIs(test['cleanTeardown'], True)

        commands = restored['eightOriginalCommands']
        self.assertEqual(set(commands['results']), set(original['qa']))
        self.assertEqual({k: v for k, v in commands['results'].items() if v}, {'browser-nav': 137})
        self.assertEqual((commands['passed'], commands['total']), (7, 8))
        self.assertIs(commands['fullMatrixPassed'], False)
        self.assertIsNone(commands['groupCountOnReceiver'])
        self.assertIsNone(commands['coldStartCountOnReceiver'])
        self.assertEqual(set(e['pending']), {'bare_jammy_arm64_abi', 'amd64_full_source_build'})
        self.assertEqual(restored['imageUserspace'], 'Ubuntu 24.04')

        source = followup['product_commit']
        self.assertRegex(source, r'^[a-f0-9]{40}$')
        self.assertNotEqual(source, e['release_commit'])
        prefix = f'{e["repository"]}/blob/{source}'
        pins = (ROOT / 'PINS.md').read_text(encoding='utf-8')
        handoff = (ROOT / 'docs/14-source-handoff.md').read_text(encoding='utf-8')
        self.assertIn(f'{prefix}/docs/releases/arm64-v0.3-cold-restore.json', pins)
        self.assertIn(f'{prefix}/docs/ARM64-SOURCE-RELEASE.md', handoff)
        self.assertIn(f'../{followup["evidence"]}', handoff)


if __name__ == '__main__':
    unittest.main()
