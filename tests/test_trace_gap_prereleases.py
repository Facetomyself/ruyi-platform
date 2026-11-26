"""Private prerelease byte custody is separate from runtime/seat qualification."""
import datetime as dt
import hashlib
import json
from pathlib import Path
import unittest
ROOT=Path(__file__).resolve().parents[1]/'artifacts/receipts/trace-linux-gap-closure-v1'; BASE='https://github.com/Facetomyself/ruyitrace/releases'

def load(p):return json.loads(p.read_bytes())
class Prereleases(unittest.TestCase):
    def test_observation_candidate_downloads(self):
        p=load(ROOT/'candidate-002-publication.json');self.assertTrue(p['private'] and p['prerelease'] and p['passed']);self.assertFalse(p['approved_for_default_site']);self.assertEqual(p['source'],'b90f5f0a7fe28b244da927de4a3b68efe7176c08');self.assertEqual(p['url'],BASE+'/tag/'+p['tag']);self.assertEqual(p['tag'],'native-events-v0.1.0-alpha.1');self.assertEqual(len(p['assets']),5)
        files={x['name']:x for x in p['assets']};self.assertEqual(len(files),5)
        for n,x in files.items():
            self.assertTrue(x['streamed_after_publication']);self.assertEqual(x['url'],BASE+'/download/'+p['tag']+'/'+n);self.assertEqual(x['github_digest'],'sha256:'+x['sha256']);self.assertGreater(x['bytes'],0)
        self.assertEqual(files['ruyitrace-native-amd64-14f2ce66295f7b04.docker.tar.gz']['sha256'],'79c2005f2d020e68f614624c3e0e7765715bc1cca14e9f1571450dacb3dfbcca');self.assertEqual(files['ruyitrace-native-arm64-1ae4616eeabc8d3b.docker.tar.gz']['sha256'],'fa0cdf41ac245318fb51d1a62b6771b644ad0cb6220036a66ccbe3740793ba13')
    def test_clean_desktop_downloads_and_prior_default(self):
        d=ROOT/'electron-owner';p=load(d/'published.json');self.assertTrue(p['passed'] and p['private'] and p['prerelease']);self.assertFalse(p['latest']);self.assertEqual(p['release_id'],459305751);self.assertEqual(p['tag_ref_sha'],p['tag_commit_sha']);self.assertEqual(p['tag_commit_sha'],'2d58cbdf43129a16afa315c70e0c93eb793758f3');self.assertEqual(p['actual_shipped_source_sha'],'724ef8e147dc1c688601346cb4d25cb3f26a8942');self.assertEqual(p['app_receipt_sha256'],hashlib.sha256((d/'custody/build-receipt.json').read_bytes()).hexdigest());self.assertEqual(p['release_url'],BASE+'/tag/'+p['tag']);self.assertEqual(p['tag'],'linux-electron-owner-v0.1.0-alpha.1');self.assertEqual(len(p['assets']),6)
        for n,v in p['assets'].items():
            self.assertEqual(v['github_digest'],'sha256:'+v['sha256']);self.assertEqual(v['browser_download_url'],BASE+'/download/'+p['tag']+'/'+n);self.assertFalse(v['credential_forwarded_to_redirect']);self.assertGreaterEqual(dt.datetime.fromisoformat(v['https_readback_utc'].replace('Z','+00:00')),dt.datetime.fromisoformat(p['published_at'].replace('Z','+00:00')))
        for arch in ('amd64','arm64'):
            fname='ruyitrace-linux-'+arch+'-electron-owner-724ef8e.tar.gz';v=p['assets'][fname];b=load(d/'custody'/(arch+'-archive-proof.json'));self.assertIn(v['sha256'],json.dumps(b));self.assertIn(str(v['bytes']),json.dumps(b));self.assertEqual(p['bundle_receipt_sha256'][arch],hashlib.sha256((d/'custody'/(arch+'-bundle-receipt.json')).read_bytes()).hexdigest())
        self.assertEqual(p['assets']['owner-inputs-v1.zip']['sha256'],'bb87c20d4397391b1dbe1a1a4ef616eae5003ebdbb64f4faa61fe85a583f382d');self.assertEqual(p['assets']['seat-operator-kit-v1.tar.gz']['sha256'],'bd6ddaa4c2c0fcb0e80361db196aeb5a46588df1c4e0981b18132fbb603f0d8c')
if __name__=='__main__':unittest.main()
