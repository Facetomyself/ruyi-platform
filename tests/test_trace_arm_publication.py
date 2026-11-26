"""Join the artifact bytes actually read from GitHub to the gitlink and ARM proof set."""
import hashlib, io, json, re, subprocess, unittest, zipfile
from pathlib import Path, PurePosixPath

ROOT=Path(__file__).resolve().parents[1];PROOF=ROOT/'artifacts/receipts/trace-arm64-native-lease';TRACE=ROOT/'submodules/ruyitrace';TAG='arm64-r5-cli2-lease-v1';REF='f1253a6ddf03dffa178d349231facc61866e686b';URL='https://github.com/Facetomyself/ruyitrace/releases';PREFIX='.agents/skills/ruyitrace-skill';
def sha(b):return hashlib.sha256(b).hexdigest()
def at(path):return subprocess.check_output(['git','-C',str(TRACE),'show',REF+':'+path])

def source_skill():
    out=io.BytesIO();files={}
    for line in subprocess.check_output(['git','-C',str(TRACE),'ls-tree','-rz',REF,'--',PREFIX]).split(b'\0'):
        if not line:continue
        head,path=line.decode().split('\t');mode,kind,oid=head.split();name=PurePosixPath(path).relative_to(PREFIX).as_posix()
        if kind!='blob' or mode not in ('100644','100755'):raise ValueError('unexpected skill file')
        files[name]=(mode,subprocess.check_output(['git','-C',str(TRACE),'cat-file','blob',oid]))
    with zipfile.ZipFile(out,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=9) as z:
        for name,(mode,data) in sorted(files.items()):
            i=zipfile.ZipInfo('ruyitrace-skill/'+name,(2000,1,1,0,0,0));i.create_system=3;i.external_attr=(0o100000|int(mode[-3:],8))<<16;i.compress_type=zipfile.ZIP_DEFLATED;z.writestr(i,data)
    return out.getvalue()


class GitHubDelivery(unittest.TestCase):
    def test_published_assets_relate_to_signed_off_product_not_only_api_success(self):
        p=json.loads((PROOF/'github-release.json').read_bytes());self.assertIs(p['passed'],True);self.assertIs(p['private'],True);self.assertEqual((p['tag'],p['source'],p['html_url']),(TAG,REF,URL+'/tag/'+TAG));self.assertTrue(p['published_at']);subprocess.run(['git','-C',str(TRACE),'merge-base','--is-ancestor',REF,'HEAD'],check=True)
        assets={a['name']:a for a in p['assets']};self.assertEqual(len(assets),len(p['assets']));self.assertEqual(len(assets),6)
        for n,v in assets.items():
            self.assertEqual(v['download_url'],URL+'/download/'+TAG+'/'+n);self.assertIs(v['streamed_download_verified'],True);self.assertEqual(v['github_digest'],'sha256:'+v['sha256']);self.assertRegex(v['sha256'],r'^[a-f0-9]{64}$')
        doc=at('product/arm64/release.json');reg=at('product/arm64/edge/release-images.json');self.assertEqual(reg,(PROOF/'release/release-images.json').read_bytes());x=json.loads(doc);co=(PROOF/'release/confirmation.json').read_bytes();self.assertEqual(x['platform_confirmation_sha256'],sha(co));self.assertEqual(x['release']['url'],p['html_url']);self.assertEqual(at(PREFIX+'/references/release-arm64.json'),(PROOF/'release/cli-lock.json').read_bytes())
        for n,b in [('ruyitrace-arm64-release.json',doc),('release-images.json',reg),('ruyitrace-skill-arm64-cli2-v1.zip',source_skill())]:self.assertEqual((assets[n]['sha256'],assets[n]['bytes']),(sha(b),len(b)))
        arch=json.loads((PROOF/'release/archive-verified.json').read_bytes());kernel=json.loads((PROOF/'release/kernel-release-summary.json').read_bytes());self.assertEqual((assets[arch['archive']]['sha256'],assets[arch['archive']]['bytes']),(arch['sha256'],arch['bytes']));kname=x['kernel']['archive'];self.assertEqual((assets[kname]['sha256'],assets[kname]['bytes']),(kernel['package']['archive_sha256'],kernel['archive_bytes']))
        checks=''.join(assets[n]['sha256']+'  '+n+'\n' for n in [arch['archive'],kname,'ruyitrace-skill-arm64-cli2-v1.zip','release-images.json','ruyitrace-arm64-release.json']).encode('ascii');self.assertEqual((assets['SHA256SUMS']['sha256'],assets['SHA256SUMS']['bytes']),(sha(checks),len(checks)))

if __name__=='__main__':unittest.main()
