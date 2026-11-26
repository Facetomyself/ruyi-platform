"""Join the private beta's eight checked downloads to the actual native builds."""
from datetime import datetime
from pathlib import Path
import hashlib
import json
import unittest

PROOF = (Path(__file__).resolve().parents[1] / 'artifacts' / 'receipts' /
         'trace-linux-gap-closure-v1' / 'patched-websocket')
TAG = 'native-events-v0.2.0-beta.1'
TAG_REF = 'e407308c5ea67ddb3a57d0999db66e66d6e68691'
RUNTIME = 'f177682d8dc4e028ad450a00f2d78acc4063e321'
PATCH = '3cecbf0b086ff1b630f79ce493d2c4f64782bdf96feb05a9d0a9db57fff3e45b'
URL = 'https://github.com/Facetomyself/ruyitrace/releases'
SKILL = 'ruyitrace-skill-v0.2.0.zip'


def load(name):
    return json.loads((PROOF / name).read_bytes())


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def instant(text):
    return datetime.fromisoformat(text.replace('Z', '+00:00'))


class NativeBeta(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.p = load('beta-published.json')
        cls.m = load('native-events-beta.json')
        cls.z = load('two-architecture-review.json')

    def test_release_is_private_prerelease_separate_from_stable_site(self):
        p, m, z = self.p, self.m, self.z
        self.assertEqual(p['release_id'], 459605674)
        self.assertEqual((p['tag'], p['tag_commit'], p['runtime_source'], p['native_patch_sha256']),
                         (TAG, TAG_REF, RUNTIME, PATCH))
        self.assertEqual((m['tag'], m['tag_commit'], m['runtime_source'], m['gecko_patch_sha256']),
                         (TAG, TAG_REF, RUNTIME, PATCH))
        self.assertEqual(p['release_url'], URL + '/tag/' + TAG)
        self.assertTrue(p['passed'] and p['private'] and p['prerelease'])
        self.assertFalse(p['make_latest'])
        self.assertEqual(p['latest_before_and_after'], {'id':458886757, 'tag':'arm64-site-ops-v1'})
        self.assertEqual(z['cases'], 44)
        self.assertEqual((m['ordinary_cli2_and_site'], m['physical_display'], m['system_ime']),
                         ('unchanged', 'outside_beta_scope', 'outside_beta_scope'))

    def test_asset_custody_and_supplements_are_architecture_specific(self):
        assets = self.p['assets']
        expected = {'native-events-beta.json', 'BETA-ZH.md', 'SHA256SUMS', SKILL}
        self.assertEqual(set(self.m['architectures']), {'arm64', 'amd64'})
        for arch, lane in self.m['architectures'].items():
            verdict = self.z['architectures']['linux/' + arch]
            self.assertEqual(lane['image_id'], verdict['browser_image_id'])
            self.assertEqual(lane['firefox_build_id'], verdict['build_id'])
            self.assertEqual(lane['firefox_libxul_elf_build_id'], verdict['gnu_elf_build_id'])
            self.assertEqual(lane['native_cases'], {'wasm':6, 'jscall':5, 'http':6, 'websocket':5})
            self.assertEqual(lane['native_cases_passed'], 22)
            for field, key, suffix in [('authenticated_evidence_sha256', 'full_byte_review_sha256', '-full-byte-review.json'),
                                       ('authenticated_core_evidence_sha256', 'review_sha256', '-review.json')]:
                self.assertEqual(lane[field], verdict[key])
                self.assertEqual(lane[field], sha((PROOF / (arch + suffix)).read_bytes()))
            for kind, digest in [('docker', verdict['operator_archive_sha256']),
                                 ('kernel', verdict['native_firefox_sha256'])]:
                asset = lane['artifacts'][kind]
                proof = assets[asset['name']]
                self.assertEqual((asset['sha256'], asset['bytes']), (digest, proof['bytes']))
                self.assertEqual(proof['sha256'], digest)
                expected.add(asset['name'])
            s = self.m['supplemental'][arch]
            self.assertEqual(s['operator_http_alternate']['http_statuses'], [302, 418])
            self.assertEqual(s['operator_http_direct']['http_statuses'], [418])
            self.assertFalse(s['operator_wrong_document']['complete'])
            self.assertEqual(s['websocket_oversize']['limit_drops'], 1)
            self.assertFalse(s['websocket_oversize']['complete'])
            self.assertEqual(s['websocket_selected_route']['peer_payload_lengths'], [5, 9])
            self.assertEqual(s['operator_jscall_alternate']['matched_rows'], 2)
        self.assertEqual(set(assets), expected)
        self.assertEqual(self.m['portable_skill']['member_files'], 30)
        self.assertEqual((assets[SKILL]['bytes'], assets[SKILL]['sha256']),
                         (97591, '5fd47b719240490db04e9a339e8ba45d5fcfbfb83e492aa49b4d69a9a0bd78e5'))

    def test_distribution_identifiers_timestamps_and_small_asset_bytes(self):
        p = self.p
        assets = p['assets']
        self.assertEqual(len({a['id'] for a in assets.values()}), 8)
        for n in ('native-events-beta.json', 'BETA-ZH.md', 'SHA256SUMS'):
            raw = (PROOF / n).read_bytes()
            self.assertEqual((assets[n]['bytes'], assets[n]['sha256']), (len(raw), sha(raw)))
        sums = ''.join(assets[n]['sha256'] + '  ' + n + '\n' for n in sorted(set(assets) - {'SHA256SUMS'}))
        self.assertEqual(sums.encode(), (PROOF / 'SHA256SUMS').read_bytes())
        for name, a in assets.items():
            self.assertEqual(a['github_digest'], 'sha256:' + a['sha256'])
            self.assertEqual(a['canonical_url'], URL + '/download/' + TAG + '/' + name)
            self.assertFalse(a['authorization_forwarded_to_cdn'])
            self.assertGreaterEqual(instant(a['readback_utc']), instant(p['published_at']))
            self.assertEqual(a['hosts'][0], 'api.github.com')


if __name__ == '__main__':
    unittest.main()
