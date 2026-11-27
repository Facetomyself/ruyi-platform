"""Offline checks for the public v0.9.4 delivery, not a new download or CI run."""
import hashlib
import json
import unittest
from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[1]
RECEIPTS = ROOT / 'artifacts/receipts/ruyihttp-0.9.4'


class PublicRelease(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.raw = (RECEIPTS / 'publication.json').read_bytes()
        cls.pub = json.loads(cls.raw)
        cls.ci = json.loads((RECEIPTS / 'qualification.json').read_bytes())
        cls.register = yaml.safe_load((ROOT / 'STATUS.yaml').read_bytes())['projects']['ruyihttp']['connect_udp_and_glibc231']

    def test_release_bound_to_qualified_revision(self):
        p, q, row = self.pub, self.ci, self.register
        self.assertEqual(p['repo'], 'Facetomyself/ruyihttp')
        self.assertEqual(p['tag'], 'v' + q['version'])
        self.assertIs(p['prerelease'], False)
        self.assertEqual(p['commit'], q['commit'])
        self.assertEqual(p['commit'], row['commit'])
        self.assertEqual(p['wheel_run'], q['run_id'])
        self.assertEqual(row['public_release'], p['url'])
        self.assertEqual(ROOT / row['publication'], RECEIPTS / 'publication.json')
        self.assertEqual(hashlib.sha256(self.raw).hexdigest(), row['publication_sha256'])

    def test_public_assets_match_ci_without_equating_different_zip_files(self):
        p, q = self.pub, self.ci
        assets = {a['name']: a for a in p['assets']}
        self.assertEqual(len(assets), len(p['assets']))
        wheels = {s['wheel']: (s['size'], s['sha256']) for s in q['slots']}
        self.assertEqual(len(wheels), 5)
        bundle = 'ruyihttp-0.9.4-release-bundle.zip'
        self.assertEqual(set(assets), set(wheels) | {'SHA256SUMS', 'qualification.json', bundle})
        for name, (size, digest) in wheels.items():
            with self.subTest(asset=name):
                self.assertEqual((assets[name]['bytes'], assets[name]['sha256']), (size, digest))
        for name, item in assets.items():
            self.assertEqual(item['url'], 'https://github.com/Facetomyself/ruyihttp/releases/download/v0.9.4/' + name)
            self.assertEqual(item['http_status'], 200)
        self.assertEqual(assets['qualification.json']['sha256'], q['complete_qualification_sha256'])
        self.assertEqual(assets[bundle]['sha256'], p['public_archive_sha256'])
        self.assertEqual(p['qualification_archive_sha256'], q['bundle_sha256'])
        self.assertNotEqual(p['public_archive_sha256'], q['bundle_sha256'])


if __name__ == '__main__':
    unittest.main()
