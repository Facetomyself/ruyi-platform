"""Contract regressions. Synthetic receipts exist only inside TemporaryDirectory."""
from contextlib import redirect_stdout
import gzip
import io
import json
from pathlib import Path
import runpy
import shutil
import subprocess
import sys
import tarfile
import tempfile
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT/'scripts/verify-trace-arm64.py'
V = runpy.run_path(str(SCRIPT))
SOURCE = ROOT.parent/'trace-arm64-lease-v1'
SOURCE = SOURCE if SOURCE.is_dir() else ROOT/'submodules/ruyitrace'
END = '2026-11-26T01:00:00+00:00'
EXTERNAL = '2026-11-26T02:00:00+00:00'
CLEANED = '2026-11-26T03:00:00+00:00'
ID = lambda n: 'sha256:'+f'{n:064x}'
H = lambda n: f'{n:064x}'


def wire(obj):
    return (json.dumps(obj,sort_keys=True)+'\n').encode()


def invoke(*args):
    p = subprocess.run([sys.executable,'-B',str(SCRIPT),*(str(x) for x in args)], capture_output=True, text=True)
    return p.returncode, json.loads(p.stdout)


class Preflight(unittest.TestCase):
    def test_real_preflight_is_explicitly_not_product(self):
        rc, x = invoke('--preflight')
        self.assertEqual(rc, 0, x)
        self.assertEqual(x, dict(passed=True,mode='preflight',scope='preflight-and-public-health-only',product_release=False,desktop_tested=False))

    def test_rehashing_substituted_preflight_cannot_move_historical_anchor(self):
        with tempfile.TemporaryDirectory() as d:
            tmp = Path(d)/'receipts'; shutil.copytree(V['RECEIPTS'],tmp,ignore=shutil.ignore_patterns('release'))
            stage = tmp/'preflight/stage.json'; doc = json.loads(stage.read_bytes()); raw = tmp/'preflight/host185.json'
            raw.write_bytes(raw.read_bytes()+b' ')
            self.assertEqual(invoke('--receipts',tmp,'--preflight')[1]['reason'],'historical-raw-sha256')
            doc['raw_sha256'][raw.name] = V['sha'](raw.read_bytes()); stage.write_bytes(wire(doc))
            self.assertEqual(invoke('--receipts',tmp,'--preflight')[1]['reason'],'historical-index-sha256')

    def test_genuine_preflight_cannot_satisfy_default_release(self):
        with tempfile.TemporaryDirectory() as d:
            tmp = Path(d)/'receipts'; shutil.copytree(V['RECEIPTS'],tmp,ignore=shutil.ignore_patterns('release'))
            rc, result = invoke('--receipts',tmp)
            self.assertEqual(rc,1)
            self.assertEqual(result['reason'],'missing-or-invalid:kernel-release-summary.json')
            release = tmp/'release'; release.mkdir()
            for name in V['RAW']:
                (release/name).write_bytes(b'{"passed":true}\n')
            self.assertFalse(invoke('--receipts',tmp,'--trace-source',SOURCE)[1]['passed'])

    def test_receipt_path_contract_matches_required_raw_names(self):
        contract = json.loads((V['RECEIPTS']/'receipt-paths.json').read_bytes())
        self.assertEqual(set(contract['raw']),set(V['RAW']))

    def test_duplicate_members_and_numeric_booleans_rejected(self):
        with self.assertRaisesRegex(V['Failure'],'duplicate-json-member'):
            V['parse'](b'{"passed":false,"passed":true}')
        self.assertFalse(V['fields']({'passed':1,'exit':False}, passed=True, exit=0))


def docker_fixture(target, roles):
    archive = io.BytesIO(); manifests = []; layers = {}; config_ids = {}; names = []; diffs = []
    with tarfile.open(fileobj=archive,mode='w') as t:
        def add(name, raw):
            entry = tarfile.TarInfo(name); entry.size = len(raw); t.addfile(entry,io.BytesIO(raw))
        for i,role in enumerate(roles):
            raw = f'synthetic layer {i}'.encode(); h = V['sha'](raw)
            diffs.append('sha256:'+h); names.append('blobs/sha256/'+h); add(names[-1],raw)
            cfg = wire(dict(os='linux',architecture='arm64',rootfs=dict(type='layers',diff_ids=diffs)))
            h = V['sha'](cfg); cfg_name = 'blobs/sha256/'+h; add(cfg_name,cfg)
            config_ids[role] = 'sha256:'+h; layers[config_ids[role]] = list(diffs)
            manifests.append(dict(Config=cfg_name,Layers=list(names),RepoTags=None))
        add('manifest.json',wire(manifests))
    target.write_bytes(gzip.compress(archive.getvalue(),mtime=0))
    return config_ids,dict(archive=V['ARCHIVE'],platform=V['PLATFORM'],bytes=target.stat().st_size,
                sha256=V['sha'](target.read_bytes()),gzip_crc_verified=True,config_ids=sorted(config_ids.values()),layers=layers)


def raw_fixture(root, target):
    plat, arch, build, attempt = (V[x] for x in ('PLATFORM','ARCH','BUILD','ATTEMPT'))
    base, producer, gecko, runtime, site = (V[x] for x in ('BASE','PRODUCER','GECKO','RUNTIME','SITE'))
    ids, archive = docker_fixture(target,V['TAGS']); cli, ui, edge = ids.values()
    layers = archive['layers']; repo = {}; ar = {k:archive[k] for k in ('bytes','sha256')}
    def put(key, obj):
        repo[key+'.json'] = obj
        return V['sha'](wire(obj))
    cfg = dict(arch=arch,pin=gecko,generated_source_stamp=gecko,generated_build_id=build,sandbox=True,wasm_sandbox=True,
               rust_target='aarch64-unknown-linux-gnu',rust_library_lto=True,rust_opt_level=1,upstream_audit_sources='match',core_backend=True)
    rust = dict(rust_edge_profile='arm64-gkrust-thin-v1',rust_edge_receipt_sha256=H(5))
    package = dict(kind='audited-candidate',arch=arch,build_id=build,archive_sha256=H(1),libxul_sha256=H(2))
    state = dict(profile='arm64-window-script-error-audited-v1',trace_input_sha256=V['TRACE_INPUT'],gecko_diff_sha256=V['DIFF'],
                 attempt=attempt,source_stamp=gecko,build_id=build,rust_sha256=H(3),elf_build_id='a'*40,build_libxul_sha256=H(4))
    put('kernel-configured',dict(cfg,archive_audit='pending',browser_capture='pending'))
    put('kernel-archive-audit',dict(cfg,**rust,sha256=H(3),archive_audit='passed',exit_code=0,archive_stability='sha256-before-after-v1',
                                  archive='/work/build/obj-wasi159/aarch64-unknown-linux-gnu/release/libgkrust.a'))
    rt_hash = put('kernel-runtime-identity',dict(**rust,schema=1,arch=arch,attempt=attempt,audit_exit=0,kind=package['kind'],
                  rust_sha256=H(3),archive_sha256=H(1),elf_build_id='a'*40,window_script_error_build=state,
                  installed=dict(build_id=build,version='159.0',source_stamp=gecko,files={'libxul.so':{'sha256':H(2)}})))
    counts = {'off':0,'opt-out':0,'wrong-origin':0,'gate-closed':0,'on':1}; trace = dict(session_ids=[1,2],closed_markers_found=0,click_ids=[3,4])
    isolation = dict(machine=arch,uid=1000,interfaces=['lo'],seccomp=2,no_new_privs=1,capabilities=0)
    qa = dict(passed=True,runtime=package,isolation=isolation)
    common_page = dict(page_ack=True,png=True,browser_exit=0,require_window_context=True,require_dom_shape=True,require_clicks=True,
                       pid_domain='browser-parent',require_storage_summary=True,content_at_ack=[{}],marker='a'*32)
    off = dict(common_page,case='off',core_files=[],verified_storage_file=None)
    on = dict(common_page,case='on',core_files=['core'],verified_event_files=['click'],verified_storage_file='storage')
    base_hash = put('kernel-baseline',dict(qa,mode='candidate',require_window_context=True,parent_window_transport=True,extended_producers=True,
                                        gate_trace=trace,event_files_by_case={'off':[],'on':['core']},storage_summary_file='storage'))
    err_hash = put('kernel-exception',dict(qa,scope='window-script-error-summary',window_script_error_build=state,exception_rows_by_case=counts))
    put('kernel-page',dict(passed=True,mode='audited-package',runtime_identity=package,cases=[off,on]))
    put('kernel-gate-page',dict(passed=True,mode='audited-package-gate',runtime_identity=package,pid_domain='browser-parent',trace=trace,
        png=True,load_barrier_seen=True,failed_step=None,browser_exit=0,nonce='a'*32,observed_writer_pid=1,
        steps=[dict(step=x) for x in ('start1','stop1','start2','stop2','done')]))
    put('kernel-package-result',dict(passed=True,phase='package_verified',archive_sha256=H(1)))
    put('kernel-script-error-build',state)
    summary_hash = put('kernel-release-summary',dict(schema=1,passed=True,trace_revision=base,builder=V['BUILDER'],attempt=attempt,runtime_image=runtime,
                       package=package,gecko_revision=gecko,gecko_diff_sha256=V['DIFF'],elf_build_id='a'*40,libgkrust_sha256=H(3),
                       upstream_audit_exit=0,gate=trace,exception_rows_by_case=counts,archive_bytes=100,peak=dict(oom=0,oom_kill=0,memory=100)))
    ca = '64e7c24b0536b525fb19b145768bd5e6e12ced0df3db837c34553ea789acd143'
    sl = '4d2f54e4be8a33c22ac80acfa78f6dcd740a5a82c594c99f866aa7e79cd7d5fc'
    lock_meta = dict(schema=2,platform=plat,source_revision=producer,firefox_build_id=build,gecko_attempt=attempt,
                     runtime_base=runtime,gecko_archive_sha256=H(1)); lock_sums = {}
    doctor_case = dict(page_ack=True,screenshot_verified=True,native_trace_verified=True,additional_firefox_filter_verified=True,
                       cli_exit=0,browser_exit=dict(code=0,signal=None))
    doctor_hash = put('cli-doctor',dict(passed=True,exit=0,phase='complete',runtime=dict(isolation,euid=1000,gid=1000),network=dict(interfaces=['lo']),
        fixtures=dict(baseline=dict(doctor_case,core_files=['core'],click_files=['click'],storage_file='storage'),exception=dict(doctor_case,exception_rows=1))))
    ident = dict(build_id=build,pid=2,start_ticks='10',owner_pid=1,owner_start_ticks='9',run_id='unit',headed_kiosk=True,
                 private_rfb_0600=True,embedded_init=True,main_processes=1)
    private_hash = put('private-native',dict(schema=1,passed=True,image_id=ui,platform=plat,no_container_published_ports=True,framebuffer=[1280,720],
        arm_empty_tcp=dict(isolation,listeners=[],viewer_ui_http=200,no_published_ports=True,gid=1000,readonly=True,
                           capabilities=dict.fromkeys(('CapInh','CapPrm','CapEff','CapBnd'),0)),
        identity_first_connected=ident,identity_before_disconnect=ident,identity_after_reconnect=ident,
        reconnect=dict(canvas_input_ready=True),page_final=dict(acks=[dict(clicks=3,drops=1,submits=1,sliderOK=True,textOK=True,titleOK=True)]),
        native_after_stop=dict(run_id='unit',trace=dict(fixture_native_clicks=1,native_stop_observed=True,closed_title_markers=0))))
    old = put('private-first-failure',dict(schema=1,passed=False,image_id=ui,platform=plat,
              failure_phase='confirm capture off and reconnect',
              failure='QA peer finish: timed out waiting for matching rendered Firefox fixture pixels',
              identity_after_reconnect=dict(ident,run_id='original'),reconnect=dict(acks=[dict(clicks=2)])))
    checkpoint = put('private-qa-checkpoint',dict(image_id=ui,sha256=private_hash)); evidence = site+'/evidence/release-v1/'
    put('private-readiness-recovery',dict(schema=1,host=V['HOST'],producer=producer,qa_revision=V['QA_REVISION'],qa_tar_sha256=V['QA_TAR'],
        expected_image=ui,old_sha256=old,old_peer_sha256=V['QA_OLD_PEER'],new_peer_sha256=V['QA_BLOBS']['peer.py'],
        old_source=site+'/source/product-'+producer,new_qa_source='/var/lib/ruyitrace-arm64-site/'+V['QA_REVISION'],
        moved_from=[evidence+'private-native-report.json',evidence+'private-native-output'],preserved_in=evidence+'private-qa-failed-'+old[:16],
        checked_utc='2026-11-26T00:58:00+00:00',completion_utc='2026-11-26T00:59:00+00:00',passed=True,original_failed_receipt_preserved=True,
        production_image_changed=False,corrected_fixture_executed=True,canvas_input_ready=True,private_qa_sha256=private_hash,checkpoint_sha256=checkpoint))
    cm = put('cli-product-manifest',dict(schema=1,scope='cli2-release',platform=plat,cli_revision=base,runtime=package,runtime_base=runtime,
                   runtime_receipt_sha256=rt_hash,source_lock_sha256=sl,parent=ID(8),node_version='22.14.0',ca_bundle_sha256=ca,ca_root_count=120,
                   baseline_sha256=base_hash,exception_sha256=err_hash,files={'one':{}}))
    for role,scope,img,parent,manifest,extra in (('cli','cli2-release',cli,ID(8),cm,dict(doctor_sha256=doctor_hash)),
           ('interactive','private-release',ui,cli,H(9),dict(acceptance_sha256=private_hash,layer_manifest_sha256=H(9)))):
        rb = dict(passed=True,platform=plat,scope=scope,tag=V['TAGS'][role],image_id=img,parent=parent,local_parent_id=parent,
                  manifest_sha256=manifest,rootfs_layers=layers[img],files=1)
        if role=='cli':
            rb.update(runtime=package,runtime_base=runtime,cli_revision=base,runtime_receipt_sha256=rt_hash,source_lock_sha256=sl,
                      node={'version':'v22.14.0','arch':'arm64'},system_trust=dict(path='/usr/lib/ssl/cert.pem',root_count=120,sha256=ca,
                      isrg_roots=dict(enumerate(sorted(V['ROOTS'])))))
        read = put(role+'-readback',rb)
        lock_sums[role] = dict(path=f'{site}/evidence/release-v1/release-locks/{role}/release-lock.json',
             sha256=put(role+'-lock',dict(lock_meta,**extra,name=V['TAGS'][role],image_id=img,parent_image=parent,manifest_sha256=manifest,readback_sha256=read)))
    exts = sorted(V['producer_functions'](SOURCE,V['ADAPTER'],'product/arm64/offline/verify_empty.py')['EXTENSIONS'])
    read = put('edge-readback',dict(passed=True,platform=plat,uid=1000,parent_image_id=ui,manifest_sha256=H(10),native_extensions=exts))
    entry = dict(interactive_image=ui,interactive_parent=cli,edge_image=edge,interactive_manifest_sha256=H(9),edge_manifest_sha256=H(10))
    registry = put('release-images',dict(schema=1,images={plat:entry})); put('production-verified-release',dict(entry,platform=plat))
    put('archive-verified',archive)
    put('archive-export',dict(ar,platform=plat,archive=V['ARCHIVE'],edge_image=edge,interactive_image=ui,interactive_parent=cli))
    post = put('post-kernel-summary',dict(V['RUNNER'],passed=True,kernel_summary_sha256=summary_hash,kernel_archive_sha256=H(1),images=ids,
         release_locks=lock_sums,edge=dict(tag=V['TAGS']['edge'],registry=site+'/edge/release-v1/readback/release-images.json',
         registry_sha256=registry,native_readback_sha256=read,manifest_sha256=H(10)),archive=dict(archive,path=site+'/edge/release-v1/'+V['ARCHIVE'])))
    put('post-kernel-result',dict(V['RUNNER'],passed=True,phase='complete',invocation='20261126T010000Z-abcdef123456',started=END,ended=END,
         summary=site+'/evidence/post-kernel-v1/summary.json',summary_sha256=post))
    put('empty-engine',dict(schema=1,platform=plat,passed=True,scope='native ARM64 isolated empty Docker engine archive acceptance',archive=ar,
         imported_config_ids=ids,initial_images=0,remaining_private_containers=0,rootfs_layer_counts={k:len(layers[v]) for k,v in ids.items()},
         rootfs_prefix_chain_verified=True,private_namespaces=dict.fromkeys(('pid','mnt','net','ipc'),True),host_daemon_identity_unchanged=True,
         private_engine_stopped=True,cli_doctor=dict(passed=True,sandbox_filter_verified=True,exception_rows=1,baseline_dom_click_storage=True),
         edge_readback=dict(passed=True,native_extensions=8),docker_server_version='29.1.3',
         interactive=dict(passed=True,viewer_uds_http=200,owner_exit=0,profile_and_socket_removed=True)))
    for case, reason in zip(V['CASES'],('expired','revoked','service_stopped')):
        put('loopback-'+case,dict(schema=1,passed=True,platform=plat,scenario=case,phase='reconcile',public_listener=False,
             scope='native loopback TLS fixture, two network-none Firefox sessions, no public demo',reason=reason,
             harness_sha256=V['IMMUTABLE_BLOBS']['product/interactive/qa/public_native.py'],edge_image_id=edge,interactive_image_id=ui,
             default_policy_seconds=1200,test_ttl_seconds=90 if case=='expire' else 140,loopback_bind_verified=True,
             active_session_revoked=True,runtime_directory_removed=True,tls_listener_removed=True,owned_containers_remaining=0,
             owner_exit=0,cli_orderly_stop=True,firewall='never-managed',checked_at=int(V['utc_seconds'](END))+60,
             unauthenticated_grant_status=403,unauthenticated_asset_status=403,second_redemption_status=403,
             first_view=dict(stage='connected',tls_hostname_verified=True,fragment_cleared=True,http_only_cookie_hidden_from_js=True,
                             framebuffer=[1280,720],no_manual_code=True),reconnect=dict(stage='reconnected',reused_cookie=True,reused_invitation=False),
             disconnect=dict(stage='disconnected',active_ws_closed=True),**({'simulated_worker_loss':True} if case=='worker-loss' else {})))
    leaf = H(11); transport = 'dsh-direct-stock'
    public = [dict(stage='tls',tls='TLSv1.3',transport=transport,public_ready=200,unauthorized_grant=403,public_dns_verified=True,
                   tls_bypass=False,leaf_sha256=leaf,root_sha256=[]),dict(stage='connected',framebuffer=[1280,720],nonblank=True,secure_context=True,
                   fragment_cleared=True,manual_access_code=False,js_visible_cookie=False),
              dict(stage='reconnected',fresh_url=True,existing_cookie=True,invitation_reuse_status=403),dict(stage='disconnected',public_ws_closed=True)]
    put('external-desktop',dict(schema=1,passed=True,origin=V['ORIGIN'],ipv4=V['IP'],target=V['HOST'],target_arch=arch,target_cli_image=cli,
         target_interactive_image=ui,target_edge_image=edge,fixture_sha256=V['FIXTURE'],public_port_443_closed=True,remaining_lease_containers=0,
         remaining_client_containers=0,owner_exit=0,transport=transport,client='oracle-dsh',client_arch=arch,stock_firefox_archive_sha256=V['STOCK'],
         scope='real public DNS/TLS/WSS/Firefox with native Oracle DSH stock Firefox direct egress',
         checked_utc=EXTERNAL,results=public,native_cli_tls=dict(stage='native-cli-public-tls',passed=True,platform=plat,image_id=cli,
             scope='target-vNIC; not independent public DNS reachability',leaf_sha256=leaf,ready_status=200,tls='TLSv1.3',
             python_wrong_authority_verify_code=64,firefox_strict_https=True,firefox_wrong_authority='insecure certificate')))
    put('post-cleanup',dict(V['IDENTITY'],schema='ruyitrace-arm64-post-cleanup.v1',os_arch=arch,checked_utc=CLEANED,archive_sha256=archive['sha256'],
         public_origin=V['ORIGIN'],public_ipv4=V['IP'],target_vnic=V['VNIC'],public_port=443,public_leaf_sha256=leaf,qa_ca_sha256=H(12),
         public_chain_and_hostname_verified_with_system_ca=True,qa_private_key_removed=True,listeners_80_443=[],loaded_qa_units=[],remaining_lease_containers=0,
         remaining_qa_client_containers=0,remaining_qa_units=0,remaining_lease_runtime_directories=0,caddy='inactive',certbot_timer='active',
         ssh='active',docker='active',iptables_sha256=dict(before=H(13),after=H(13)),oci_admission_sha256=dict(before=H(14),after=H(14))))
    for name,doc in repo.items():
        (root/name).write_bytes(wire(doc))
    return repo


class Release(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        try:
            V['reviewed_source'](SOURCE)
        except V['Failure'] as e:
            raise unittest.SkipTest(str(e)) from e

    def setUp(self):
        d = tempfile.TemporaryDirectory(); self.addCleanup(d.cleanup)
        self.root = Path(d.name); self.raw = self.root/'release'; self.raw.mkdir()
        self.archive = self.root/'synthetic-fixture.tar.gz'
        self.docs = raw_fixture(self.raw,self.archive)

    def run_verifier(self,*args):
        # Only these two historical anchors are replaced for temporary synthetic bytes.
        ids = self.docs['post-kernel-summary.json']['images']
        anchors = dict(QA_IMAGES=(ids['cli'],ids['interactive']),
                       QA_FIRST=V['sha'](wire(self.docs['private-first-failure.json'])))
        out = io.StringIO()
        with mock.patch.dict(V['main'].__globals__,anchors), redirect_stdout(out):
            rc = V['main'](['--receipts',str(self.root),'--trace-source',str(SOURCE),*(str(x) for x in args)])
        return rc,json.loads(out.getvalue())

    def mutate(self, name, doc):
        (self.raw/(name+'.json')).write_bytes(wire(doc))

    def test_index_is_mandatory_and_archive_gzip_bytes_are_checked(self):
        self.assertEqual(self.run_verifier()[1]['reason'],'release-confirmation-missing-or-invalid')
        rc, index = self.run_verifier('--release','--prepare-index','--archive',self.archive)
        self.assertEqual(rc,0,index)
        self.assertEqual(set(index['raw_sha256']),set(V['RAW']))
        self.mutate('confirmation',index)
        self.assertFalse(self.run_verifier()[1]['archive_bytes_checked'])
        self.assertTrue(self.run_verifier('--archive',self.archive)[1]['archive_bytes_checked'])
        content = bytearray(self.archive.read_bytes()); content[4] ^= 1; self.archive.write_bytes(content)
        self.assertEqual(self.run_verifier('--archive',self.archive)[1]['reason'],'archive-digest-or-config-layer-mismatch')

    def test_reviewed_stream_verifies_config_and_layer_content(self):
        scanner = V['producer_functions'](SOURCE,V['PRODUCER'],'product/arm64/release_after_kernel.py')['archive_readback']
        proof = self.docs['archive-verified.json']; expected = dict(proof['layers'])
        edge = max(expected,key=lambda k: len(expected[k])); expected[edge] = [*expected[edge][:-1],ID(99)]
        with self.assertRaisesRegex(ValueError,'layer bytes or graph'):
            scanner(self.archive,expected)
        expected[ID(99)] = expected.pop(edge)
        with self.assertRaisesRegex(ValueError,'unknown, repeated or foreign'):
            scanner(self.archive,expected)

    def test_wrong_arch_image_substitution_empty_engine_and_missing_desktop(self):
        for name, key, value, why in (
            ('cli-lock','platform','linux/amd64','cli-release-lock-and-native-readback'),
            ('kernel-archive-audit','archive_audit','pending','original-arm64-rust-audit'),
            ('empty-engine','initial_images',1,'independent-empty-engine'),
            ('external-desktop','target_edge_image',ID(88),'independent-public-firefox-wss-and-cleanup'),
            ('external-desktop','results',[],'network-receipt-shape'),
            ('post-cleanup','qa_ca_sha256',H(11),'site-isolation-and-final-cleanup')):
            with self.subTest(name=name,key=key):
                doc = self.docs[name+'.json']; self.mutate(name,dict(doc,**{key:value}))
                rc, result = self.run_verifier('--prepare-index')
                self.assertEqual((rc,result['reason']),(1,why))
                self.mutate(name,doc)

    def test_site_cleanup_requires_explicitly_empty_loaded_qa_units(self):
        name = 'post-cleanup'; original = self.docs[name+'.json']
        for units in (None, ['ruyitrace-demo-qa-example.slice']):
            with self.subTest(units=units):
                changed = dict(original)
                if units is None:
                    del changed['loaded_qa_units']
                else:
                    changed['loaded_qa_units'] = units
                self.mutate(name,changed)
                rc, result = self.run_verifier('--prepare-index')
                self.assertEqual((rc,result['reason']),(1,'site-isolation-and-final-cleanup'))

    def test_private_recovery_rejects_bad_revision_report_sha_and_timing(self):
        name = 'private-readiness-recovery'; original = self.docs[name+'.json']
        for key,value in (('qa_revision',V['ADAPTER']),('qa_tar_sha256',H(89)),('new_peer_sha256',H(90)),
                          ('private_qa_sha256',H(91)),('checkpoint_sha256',H(92)),('production_image_changed',True),
                          ('completion_utc',EXTERNAL)):
            with self.subTest(key=key):
                self.mutate(name,dict(original,**{key:value}))
                rc, result = self.run_verifier('--prepare-index')
                self.assertEqual((rc,result['reason']),(1,'private-readiness-recovery-binding'))
        self.mutate(name,original)
        old = self.raw/'private-first-failure.json'; old.write_bytes(old.read_bytes()+b' ')
        self.assertEqual(self.run_verifier('--prepare-index')[1]['reason'],'preserved-private-readiness-failure')

    def test_private_recovery_requires_corrected_run_flag_even_with_bound_hashes(self):
        docs = dict(self.docs); ids = docs['post-kernel-summary.json']['images']
        name = 'private-native.json'; docs[name] = dict(docs[name],reconnect={'canvas_input_ready':False})
        report_sha = V['sha'](wire(docs[name])); checkpoint = dict(image_id=ids['interactive'],sha256=report_sha)
        docs['private-qa-checkpoint.json'] = checkpoint
        proof_name = 'private-readiness-recovery.json'
        docs[proof_name] = dict(docs[proof_name],private_qa_sha256=report_sha,checkpoint_sha256=V['sha'](wire(checkpoint)))
        hashes = {k:V['sha'](wire(v)) for k,v in docs.items()}
        with mock.patch.dict(V['main'].__globals__,QA_IMAGES=(ids['cli'],ids['interactive']),QA_FIRST=hashes['private-first-failure.json']):
            with self.assertRaisesRegex(V['Failure'],'private-readiness-new-native-run'):
                V['private_readiness'](lambda k:docs[k+'.json'],hashes,SOURCE,ids)

    def test_raw_byte_substitutions_fail_even_with_reissued_index(self):
        a = self.raw/'kernel-baseline.json'; old = a.read_bytes(); a.write_bytes(old+b' ')
        self.assertEqual(self.run_verifier('--prepare-index')[1]['reason'],'sealed-cli-manifest-and-raw-qa-sha256')
        a.write_bytes(old)
        rc,index = self.run_verifier('--prepare-index'); self.assertEqual(rc,0,index)
        self.mutate('confirmation',index)
        p = self.raw/'external-desktop.json'; p.write_bytes(p.read_bytes()+b' ')
        self.assertEqual(self.run_verifier()[1]['reason'],'release-confirmation-identity-or-raw-sha256')


if __name__ == '__main__':
    unittest.main()
