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
        cls.entry = cls.book['projects']['ruyidom']
        cls.original = cls.entry['historical_v0_3_0_arm64_release']
        cls.original_body = (ROOT / cls.original['evidence']).read_bytes()
        cls.original_receipt = json.loads(cls.original_body)
        cls.current_body = (ROOT / cls.entry['evidence']).read_bytes()
        cls.current_receipt = json.loads(cls.current_body)

    def test_release_and_operator_sources_are_separate(self):
        e = self.entry
        self.assertEqual(e['relationship'], 'platform_component_independent_release')
        self.assertNotIn('ruyidom', self.book.get('related_projects', {}))
        reg = self.book['submodules']['ruyidom']
        path = e['submodule']
        self.assertEqual((path, reg['url'], reg['visibility'], reg['branch']),
                         ('submodules/ruyidom', e['repository'] + '.git', 'private', 'main'))
        row = subprocess.check_output(['git', 'ls-files', '--stage', '--', path], cwd=ROOT, text=True).strip()
        self.assertEqual(row, f"160000 {reg['commit']} 0\t{path}")
        repo, ref, operator = e['repository'], e['release_commit'], e['arm64_deployment']['operator_commit']
        self.assertRegex(ref, r'^[a-f0-9]{40}$')
        self.assertRegex(operator, r'^[a-f0-9]{40}$')
        pins = (ROOT / 'PINS.md').read_text(encoding='utf-8')
        handoff = (ROOT / 'docs/14-source-handoff.md').read_text(encoding='utf-8')
        self.assertIn(f'{repo}/tree/{ref}', pins)
        self.assertIn(f'{repo}/releases/tag/{e["release_tag"]}', handoff)
        self.assertIn(f'sha={ref}', handoff)
        self.assertIn(f'{repo}/blob/{operator}/deploy/arm64/README.md', handoff)

    def test_tag_commit_source_and_platform_receipts_match_offline(self):
        e = self.entry
        repo = ROOT / e['submodule']
        tag = e['release_tag']
        pin = self.book['submodules']['ruyidom']['commit']
        def git(*args):
            return subprocess.check_output(['git', '--no-optional-locks', '-C', str(repo), *args])
        self.assertEqual(git('rev-parse', '--show-toplevel').decode().strip(), str(repo))
        self.assertEqual(git('rev-parse', 'HEAD^{commit}').decode().strip(), pin)
        self.assertEqual(git('rev-parse', f'{tag}^{{tag}}').decode().strip(), e['release_tag_object'])
        self.assertEqual(git('rev-parse', f'{tag}^{{commit}}').decode().strip(), e['release_commit'])
        self.assertNotEqual(pin, e['release_tag_object'])
        git('merge-base', '--is-ancestor', e['release_commit'], pin)
        # Read frozen blobs from the release, not from a later worktree or a live host.
        copies = {
            'source-portability-v0.3.1.json': self.current_body,
            'arm64-source-v0.3.json': self.original_body,
            'arm64-v0.3-cold-restore.json': (ROOT / e['arm64_second_host_restore']['evidence']).read_bytes(),
        }
        for name, expected in copies.items():
            with self.subTest(name=name):
                self.assertEqual(git('show', f"{e['release_commit']}:docs/releases/{name}"), expected)

    def test_v030_release_and_arm64_use_match_frozen_qualification(self):
        e, h, r = self.entry, self.original, self.original_receipt
        self.assertEqual((h['tag'], h['commit']), ('v0.3.0', '790cc23e6c049bbcb2d186656fa5545d1ef7bac6'))
        self.assertEqual(hashlib.sha256(self.original_body).hexdigest(), h['evidence_sha256'])
        self.assertEqual(h['evidence_sha256'], 'bea6ca613783071c68005dfa86b7faef738187fe3460dc2f25ec24e15864caee')
        self.assertEqual(r['schema'], 'ruyidom-arm64-source-release-v1')
        arm = e['arm64_deployment']
        self.assertEqual((arm['host'], arm['image_id'], arm['renderer']),
                         (r['nativeGeckoSourceHost'], r['ociImageId'], r['maintainedProfile']))
        self.assertEqual((arm['local_tag'], arm['mode'], arm['default_network']),
                         ('ruyidom:arm64-use', 'on_demand', 'none'))
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
        e, original = self.entry, self.original_receipt
        followup = e['arm64_second_host_restore']
        self.assertNotEqual(followup['evidence'], self.original['evidence'])
        body = (ROOT / followup['evidence']).read_bytes()
        self.assertEqual(hashlib.sha256(body).hexdigest(), followup['evidence_sha256'])
        self.assertEqual(followup['evidence_sha256'], 'b97fb7d6232844a3c82c953cd24b24a04c463f06efdbda4d1f06164b5f477a2a')
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
        self.assertEqual(restored['imageUserspace'], 'Ubuntu 24.04')

        source = followup['product_commit']
        self.assertRegex(source, r'^[a-f0-9]{40}$')
        self.assertNotEqual(source, self.original['commit'])
        prefix = f'{e["repository"]}/blob/{source}'
        pins = (ROOT / 'PINS.md').read_text(encoding='utf-8')
        handoff = (ROOT / 'docs/14-source-handoff.md').read_text(encoding='utf-8')
        self.assertIn(f'{prefix}/docs/releases/arm64-v0.3-cold-restore.json', pins)
        self.assertIn(f'{prefix}/docs/ARM64-SOURCE-RELEASE.md', handoff)
        self.assertIn(f'../{followup["evidence"]}', handoff)

    def test_current_portability_evidence_is_distinct_from_v030(self):
        e, r = self.entry, self.current_receipt
        self.assertEqual(hashlib.sha256(self.current_body).hexdigest(), e['evidence_sha256'])
        self.assertEqual(r['schema'], 'ruyidom-source-portability-v0.3.1')
        self.assertEqual((e['release_tag'], r['release']), ('v0.3.1', 'v0.3.1'))
        self.assertEqual(e['release_tag_object'], '436429465dd740ee67471198d34fc97c6c81b8b0')
        self.assertNotEqual(e['release_commit'], self.original['commit'])
        self.assertEqual(r['trustedScriptHost'], self.original_receipt['trustedScriptHost'])
        self.assertEqual(e['pending'], [])
        old = r['historical']
        self.assertEqual((old['originalRelease'], old['sourceCommit'], old['oldReleaseReceiptSHA256']),
                         (self.original['tag'], self.original['commit'], self.original['evidence_sha256']))
        noble = old['originalNobleOnBareJammy']
        self.assertEqual(noble['buildID'], self.original_receipt['buildID'])
        self.assertIs(noble['passedFileCheck'], True)
        self.assertIs(noble['actualBrowserStart'], False)
        self.assertEqual(noble['firstRequestCount'], 0)
        cold = old['arm64ColdRestore']
        self.assertEqual(cold['sha256'], e['arm64_second_host_restore']['evidence_sha256'])
        self.assertEqual((cold['optionalOriginalCommandsPassed'], cold['optionalOriginalCommandsTotal']), (7, 8))
        self.assertIsNone(cold['fullOtherHostGroupCount'])
        self.assertIsNone(cold['fullOtherHostColdStarts'])

        handoff = (ROOT / 'docs/14-source-handoff.md').read_text(encoding='utf-8')
        pins = (ROOT / 'PINS.md').read_text(encoding='utf-8')
        self.assertIn(f'{e["repository"]}/blob/{e["release_commit"]}/docs/PORTABILITY.md', handoff)
        self.assertIn(f'{e["repository"]}/tree/{self.original["commit"]}', pins)
        self.assertIn(f'../{e["evidence"]}', handoff)
        self.assertIn(e['evidence'], pins)

    def test_new_amd64_and_bare_jammy_pass_their_own_gates(self):
        r = self.current_receipt
        amd, jammy = r['nativeAmd64'], r['jammyArm64']
        self.assertEqual(r['mozillaSource']['sourceStamp'], self.original_receipt['sourceStamp'])
        self.assertEqual((amd['buildID'], jammy['buildID']), ('20261126091201', '20261126091202'))
        self.assertEqual((amd['libxul']['machine'], jammy['libxul']['machine']), ('x86_64', 'aarch64'))
        self.assertEqual((amd['libxul']['size'], jammy['libxul']['size']), (183082880, 181036304))
        for candidate, gate, command_key, count in (
            (amd, amd['qa'], 'commands', 8), (jammy, jammy['bareGate'], 'commandExitCodes', 10),
        ):
            with self.subTest(engine=candidate['engine']):
                self.assertEqual(set(candidate['mach']), {'configure', 'build', 'package'})
                self.assertTrue(all(phase['exit'] == 0 for phase in candidate['mach'].values()))
                self.assertIs(gate['passed'], True)
                self.assertEqual(list(gate[command_key].values()), [0] * count)
                self.assertEqual(len(gate['browserGroups']['pass']), 12)
                self.assertEqual(gate['browserGroups']['fail'] + gate['browserGroups']['unsupported'], [])
                self.assertEqual((gate['coldStarts'], gate['coldHTTPRequests']), (10, 10))

        self.assertEqual(amd['image']['platform'], 'linux/amd64')
        self.assertIs(amd['registryPush'], False)
        self.assertEqual((amd['readback']['nativeSmoke'], amd['readback']['browserRedirectCSP']),
                         ('RuyiDOM:offline', 'pass'))
        self.assertIs(amd['readback']['sameHost'], True)
        self.assertIs(amd['readback']['cleanStore'], False)
        self.assertIs(jammy['containerUsedForRuntime'], False)
        self.assertEqual((jammy['system'], jammy['glibc']), ('Ubuntu 22.04.5 LTS', 'glibc 2.35'))
        abi = jammy['abi']
        self.assertEqual((abi['checkedELFs'], abi['incompatibleELFs']), (30, 0))
        self.assertEqual(set(abi['systemLoaderAndLibraries']), {'ld-linux-aarch64.so.1', 'libc.so.6', 'libstdc++.so.6'})
        for key in ('matchedByDeviceAndInode', 'observedCandidateLibxulMatchesPackage',
                    'freshExternalValueVerified', 'inlineScriptBlocked', 'cleanTeardown'):
            self.assertIs(abi[key], True)

        handoff = (ROOT / 'docs/14-source-handoff.md').read_text(encoding='utf-8')
        for artifact in (amd['package'], amd['image']['archive'], jammy['package']):
            self.assertIn(artifact['sha256'], handoff)
            self.assertIn(f'{artifact["size"]:,}', handoff)
        self.assertIn(amd['image']['imageID'], handoff)


if __name__ == '__main__':
    unittest.main()
