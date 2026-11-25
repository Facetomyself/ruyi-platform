"""A retired public tutorial is not a TLS/lease product acceptance receipt."""
import hashlib
import json
from pathlib import Path
import re
import subprocess
import unittest

ROOT=Path(__file__).resolve().parents[1];E=ROOT/'artifacts/receipts/trace-public-lease-v1';T=ROOT/'submodules/ruyitrace';SOURCE='c3723ca5f71e860ed19d1fa1a4305da930dc7428';BASE='sha256:9d3201e2689a974f431f090c31e08a3d2c2794da03e483cd31eada8badf0918a';IMG='sha256:28eac74b5455256d4e20b41b7feb18c8371e9f940fee11c05d144ff771b57a22';A='44c1f62192a851c8e183da31a3b12beff6769ff72495b7a0144016f3f2a731dc';
def digest(x):return hashlib.sha256(x).hexdigest()
def src(p):return subprocess.check_output(['git','-C',str(T),'show',SOURCE+':product/interactive/'+p])
def raw(n):return json.loads((E/n).read_bytes())


class LeaseProof(unittest.TestCase):
    def test_source_inputs_and_host_are_pinned(self):
        x=raw('release.json');self.assertEqual(x['schema'],'ruyitrace-public-lease.v1');self.assertEqual(x['source'],{'tag':'product/public-edge-tls-lease-v1-amd64','commit':SOURCE});subprocess.run(['git','-C',str(T),'merge-base','--is-ancestor',SOURCE,'HEAD'],check=True)
        self.assertEqual((x['image_id'],x['parent_image_id'],x['archive']['sha256'],x['archive']['bytes']),(IMG,BASE,A,351919702))
        keys=set(x['source_sha256']);self.assertTrue({'public-gateway.py','demo_lease.py','edge-build/wheels-lock.json','qa/public_native.py','qa/public_browser.py','systemd/install','systemd/demo@.service'}<=keys)
        for p,h in x['source_sha256'].items():
            self.assertRegex(p,r'^[A-Za-z0-9_./@-]+$');self.assertFalse(Path(p).is_absolute() or '..' in Path(p).parts);self.assertEqual(digest(src(p)),h)
        expected={'edge-export.json','edge-readback.json','prepare-final.json','final-revoke.json','final-expire.json','final-worker-loss.json','systemd-failure-recovery.json','final-host.json'};self.assertEqual(set(x['raw_sha256']),expected)
        for n,h in x['raw_sha256'].items():self.assertTrue((E/n).is_file() and not (E/n).is_symlink());self.assertEqual(digest((E/n).read_bytes()),h)
        ex=raw('edge-export.json');rb=raw('edge-readback.json');p=raw('prepare-final.json');self.assertTrue(ex['passed'] and rb['passed']);self.assertEqual((ex['image_id'],ex['archive_sha256'],ex['archive_bytes'],ex['tag']),(IMG,A,351919702,'ruyitrace/public-edge:tls-lease-v1-amd64'));self.assertEqual(rb['parent_image_id'],BASE);self.assertEqual(rb['uid'],1000);self.assertEqual(rb['manifest_sha256'],p['manifest_sha256']);self.assertEqual(p['wheel_lock_sha256'],x['source_sha256']['edge-build/wheels-lock.json']);self.assertEqual(rb['aiohttp'],json.loads(src('edge-build/wheels-lock.json'))['inputs']['aiohttp']['version'])
    def test_native_cases_prove_real_session_and_cleanup(self):
        for case,why in [('revoke','revoked'),('expire','expired'),('worker-loss','service_stopped')]:
            with self.subTest(case=case):
                x=raw('final-'+case+'.json');self.assertIs(x['passed'],True);self.assertEqual(x['scenario'],case);self.assertEqual(x['reason'],why); self.assertEqual((x['edge_image_id'],x['interactive_image_id'],x['harness_sha256']),(IMG,BASE,digest(src('qa/public_native.py'))));self.assertIs(x['public_listener'],False);self.assertIs(x['loopback_bind_verified'],True);self.assertEqual(x['first_view']['framebuffer'],[1280,720]); self.assertTrue(all(x['first_view'][k] is True for k in ('tls_hostname_verified','fragment_cleared','http_only_cookie_hidden_from_js','no_manual_code')));self.assertTrue(x['reconnect']['reused_cookie'] and not x['reconnect']['reused_invitation']);self.assertEqual([x[k] for k in ('second_redemption_status','unauthenticated_asset_status','unauthenticated_grant_status')],[403]*3);self.assertTrue(x['disconnect']['active_ws_closed'] and x['runtime_directory_removed'] and x['tls_listener_removed'] and x['cli_orderly_stop']);self.assertEqual((x['owner_exit'],x['owned_containers_remaining']),(0,0))
                if case=='expire':self.assertEqual(x['test_ttl_seconds'],90)
                if case=='worker-loss':self.assertIs(x['simulated_worker_loss'],True)
        x=raw('systemd-failure-recovery.json');self.assertTrue(x['passed'] and x['failed_startup_cleaned'] and x['unrecorded_created_container_reconciled']);self.assertFalse(x['actual_host_reboot'] or x['invitation_emitted']);f=raw('final-host.json');self.assertEqual(f['offline_edge_image'],IMG);self.assertEqual(f['interactive_image'],BASE);self.assertTrue(f['passed']);self.assertFalse(f['port_30007_listening'] or f['port_30009_listening'] or f['qa_listener_present'] or f['production_lease_installed']);self.assertTrue(all(f[k]==0 for k in ('qa_unit_files','qa_workdirs','qa_containers','public_demo_rules','edge_containers_running')))

if __name__=='__main__':unittest.main()
