"""Offline join of the seven streamed GH assets, deployment pins and reviewed source."""
import hashlib
import json
from pathlib import Path
import subprocess
import unittest

ROOT=Path(__file__).resolve().parents[1]; P=ROOT/'artifacts/receipts/trace-arm64-site-operations'; SRC=ROOT/'submodules/ruyitrace'; TAG='arm64-site-ops-v1'; REF='e35e7278a49d4e67c9ad9e480308bf5e11273493'; URL='https://github.com/Facetomyself/ruyitrace/releases'; SITE='product/arm64/site/'

def sha(b):return hashlib.sha256(b).hexdigest()
def at(path):return subprocess.check_output(['git','-C',str(SRC),'show',REF+':'+path])

class SiteReleaseDelivery(unittest.TestCase):
    def test_published_bytes_against_native_sources_and_deployment(self):
        p=json.loads((P/'github-release.json').read_bytes());self.assertTrue(p['passed'] and p['private']);self.assertEqual((p['source'],p['tag'],p['html_url'],p['release_id']),(REF,TAG,URL+'/tag/'+TAG,458886757));self.assertEqual(p['published_at'],'2026-11-26T02:51:28Z');self.assertEqual(p['source'],json.loads((P/'index.json').read_bytes())['source_commit']);self.assertEqual(subprocess.check_output(['git','-C',str(SRC),'rev-parse',TAG+'^{commit}'],text=True).strip(),REF)
        catbytes=at(SITE+'releases/catalog.json');catalog=json.loads(catbytes);assets=p['assets'];items={i['name']:i for i in assets};self.assertEqual(len(items),len(assets));self.assertEqual(len(items),7)
        for v in assets:
            self.assertIs(v['streamed_download_verified'],True);self.assertEqual(v['github_digest'],'sha256:'+v['sha256']);self.assertEqual(v['download_url'],URL+'/download/'+TAG+'/'+v['name'])
        def check_item(n,sz,h):self.assertEqual((items[n]['bytes'],items[n]['sha256']),(sz,h))
        check_item('ruyitrace-site-catalog.json',len(catbytes),sha(catbytes));guide=at(SITE+'README.md');check_item('ARM64-SITE.md',len(guide),sha(guide))
        ids=[]
        for i in (1,2):
            name='r5-arm64-site'+str(i);docs=json.loads((P/'raw'/('site'+str(i))/'slot-review.json').read_bytes());s=catalog['site_packages'][name];self.assertEqual(s['release_sha256'],docs['manifest_sha256']);self.assertEqual(s['slot_tar_sha256'],docs['tar_sha256']);check_item(s['slot_file'],s['slot_bytes'],s['slot_tar_sha256']);ids.append(s['slot_file']);self.assertEqual(s['slot_url'],items[s['slot_file']]['download_url'])
        b=catalog['site_packages']['r5-arm64-site2']['product_archive'];check_item(b['name'],b['bytes'],b['sha256']);core=catalog['bootstrap_archive'];check_item(core['name'],core['bytes'],core['sha256']);self.assertEqual(core['sha256'],json.loads((P/'raw/core-guarded-installed.json').read_bytes())['bundle_sha256']);names=[b['name'],*ids,core['name'],'ruyitrace-site-catalog.json','ARM64-SITE.md'];raw=''.join(items[n]['sha256']+'  '+n+'\n' for n in names).encode();check_item('SHA256SUMS',len(raw),sha(raw))

if __name__=='__main__':unittest.main()
