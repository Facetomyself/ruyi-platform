"""Site-verifier regression tests; synthetic receipts live only in temp dirs."""
from datetime import datetime, timezone
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

REPO = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location('trace_site', REPO / 'scripts/verify-trace-site.py')
V = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(V)
HEX = 'a' * 64
NOW = 1795662000


def wire(doc):
    return (json.dumps(doc, sort_keys=True, separators=(',', ':')) + '\n').encode()


def utc(n):
    return datetime.fromtimestamp(NOW + n, timezone.utc).isoformat()


def fixture():
    docs, refs, releases = {}, [], []
    def put(stem, schema=None, **values):
        docs[stem + '.json'] = dict(values, **({'schema': schema} if schema else {}))
    keys = ('host.py', 'health.py', 'cli-lock.json', 'interactive-lock.json', 'archive-proof.json', 'release-images.json')
    quiet = dict(state='idle', live_leases=0, ready_leases=0, listener_443=False, docker_published_443=False,
                 tls=dict(material_verified=True, leaf_sha256=HEX, ready_lease_handshake=False))
    for i in (1, 2):
        vs, ids = f'r5-arm64-site{i}', dict(V.ORIGINALS, edge=V.EDGES[i - 1])
        archive = dict(zip(('name', 'bytes', 'sha256'), V.ARCHIVES[i - 1]))
        meta = dict(platform=V.PLATFORM, version=vs, host_source=V.HOST_SOURCE, product_source=(V.BASE, V.EDGE_SOURCE)[i - 1],
                    readiness_contract=i, image_ids=ids, archive=archive)
        put(f'site{i}/release', 'ruyitrace-host-release.v1', files=dict.fromkeys(keys, HEX), **meta)
        pin = V.sha(wire(docs[f'site{i}/release.json'])); releases.append(dict(meta, release_sha256=pin))
        ref = dict(version=vs, sha256=pin, inventory_sha256=str(i) * 64); refs.append(ref)
        put(f'site{i}/slot-review', version=vs, host_source=V.HOST_SOURCE, product_source=meta['product_source'],
            manifest_sha256=pin, product_archive_sha256=archive['sha256'], slot_archive=f'ruyitrace-site-slot-{vs}.tar.gz',
            tar_sha256=HEX, tar_bytes=90000, files=len(keys) + 1)
        common = dict(version=vs, ok=True, bundle_sha256=HEX, release_sha256=pin, image_ids=ids, archive_sha256=archive['sha256'],
                      archive_bytes=archive['bytes'], archive_gzip_and_layers_verified=True, activated=False, public_listener_started=False)
        put(f'enroll-site{i}', 'ruyitrace-site-enroll.v1', **common, docker_load_executed=True, slot_new=True,
            archive_new=i == 2, already_present=dict(cli=True, interactive=True, edge=i == 1), utc=utc(10 * i))
        put(f'idempotent-{vs}', 'ruyitrace-site-enroll.v1', **common, docker_load_executed=False, slot_new=False,
            archive_new=False, already_present=dict(cli=True, interactive=True, edge=True), utc=utc(30 + i))
        hashes = dict(V.READBACKS, edge=V.READBACKS['edge'][i - 1])
        doctor = dict(exit=0, page_ack=True, native_trace_verified=True, firefox_filter_verified=True, isolated_content_processes=1)
        when = utc(45 if i == 1 else 95)
        verified = dict(release=releases[-1], verified_utc=when, payload_files=len(keys), inventory_sha256=ref['inventory_sha256'],
                        archive=dict(archive, path=f'/var/lib/ruyitrace-arm64-site/artifacts/{archive["sha256"]}/{archive["name"]}'),
                        installed_manifests={r: dict(files=9, manifest_sha256=h) for r, h in hashes.items()},
                        registry={r + '_manifest_sha256': hashes[r] for r in ('edge', 'interactive')},
                        fixtures=dict(baseline=dict(doctor, storage_fixture_rows_verified=16, core_files=1, click_files=1),
                                      exception=dict(doctor, exception_rows=1)))
        checks = dict(installed_image_ids=ids, checked_payload_files=len(keys), inventory_sha256=ref['inventory_sha256'], site=quiet,
                      timers={u: dict(active=True, enabled=True) for u in ('certbot.timer', 'ruyitrace-demo-sweep.timer')})
        put(f'site{i}-last-verified', 'ruyitrace-host-verified.v1', **verified)
        put(f'site{i}-verify', 'ruyitrace-host-health.v1', command='verify', passed=True, checked_utc=when, checks=checks, **verified)
        put(f'desktop-site{i}', 'ruyitrace-site-live-desktop.v1', passed=True, stage='complete', observer='oracle-dsh',
            observer_arch=V.ARCH, browser='Mozilla Firefox 159.0', rootless_read_only_sandbox=True, stock_firefox_archive_sha256=V.STOCK,
            stock_dependencies_sha256=V.DEPS, fixture_sha256=V.FIXTURE, target=V.HOST, target_arch=V.ARCH, stable_user='ubuntu',
            stable_command=V.STABLE, slot=vs, release_sha256=pin, inventory_sha256=ref['inventory_sha256'], manager_sha256=V.MANAGER,
            broker_registry_sha256=str(i) * 64, image_ids=ids, ready_contract=i, ttl_seconds=180, public_origin=V.ORIGIN,
            public_ipv4=V.IPV4, browser_direct_public=True, framebuffer=[1280, 720], nonblank=True, reconnect=True,
            spent_invite_status=403, unauthorized_grant_status=403, session_linkage_verified=True, active_pointer_and_registry_unchanged=True,
            viewer_connection_survived=True, viewer_disconnected_after_revoke=True, owner_exit=0, remaining_lease_containers=0,
            public_port_443_closed=True, private_handoff_cleanup_verified=True, checked_utc=utc(50 if i == 1 else 65),
            last_public_ready=dict(status=200, body_ready=True, header_version=None if i == 1 else '2', public_dns_verified=True,
                                   system_ca_and_hostname_verified=True, leaf_sha256=HEX, tls='TLSv1.3'),
            upgrade_plan=dict(tested=False) if i == 1 else dict(tested=True, target_version=refs[0]['version'], target_sha256=refs[0]['sha256'],
                                                                  exit=2, error='broker_busy', mutation_path_executed=False))
    a, b = refs
    put('two-approved-versions', 'ruyitrace-site-versions.v1', ok=True, platform=V.PLATFORM, active=None, previous=None,
        versions=[dict(ref, archive=r['archive'], image_ids=r['image_ids']) for ref, r in zip(refs, releases)])
    for i, (name, action, old, j) in enumerate(zip(V.ACTIONS, ('adopt', 'activate', 'rollback', 'activate'), (None, a, b, a), (0, 1, 0, 1))):
        new, tid = refs[j], str(i + 1) * 32
        common = dict(action=action, old=old, new=new, id=tid)
        put(name, 'ruyitrace-site-action.v1', ok=True, action=action, active=new, previous=old, transaction_id=tid, changed=True)
        put(name + '-history', 'ruyitrace-site-history.v1', started=NOW + 40 + i * 15, **common)
        put(name + '-receipt', 'ruyitrace-site-receipt.v1', **common, current='releases/' + new['version'],
            image_ids=releases[j]['image_ids'], endpoint_policy_sha256=HEX, active=dict(schema='ruyitrace-site-active.v1', active=new,
            previous=old, config_sha256=HEX, registry_sha256=str(j + 1) * 64))
    install = dict(ok=True, source=V.HOST_SOURCE, modified_existing_broker=False, opened_listener=False, bundle_sha256=HEX,
                   installed={'manager.py': V.MANAGER, 'install.py': HEX, 'archive_readback.py': V.ARCHIVE_READER})
    put('bootstrap-installed', **install, new_core=True); put('bootstrap-idempotent', **install, new_core=False)
    link = dict(ok=True, user=1001, command=V.STABLE, version=a['version'], target='/opt/ruyitrace/releases/r5-arm64-site1/host.py')
    put('user-link-install', **link, changed=True, installed_links=['/home/ubuntu/.local/share/ruyitrace/releases',
        '/home/ubuntu/.local/share/ruyitrace/current', V.STABLE]); put('user-link-idempotent', **link, changed=False, installed_links=[])
    put('noop-plan', 'ruyitrace-site-action.v1', ok=True, action='activate', changed=False, eligible=True, transaction_id=None, active=b, previous=a)
    put('noop-plan-invocation', 'ruyitrace-site-invocation.v1', exit=0, argv=[V.STABLE, 'upgrade', b['version'], '--sha256', b['sha256'], '--plan'],
        stdout_sha256=V.sha(wire(docs['noop-plan.json'])), checked_utc=utc(99))
    put('default-ttl', 'ruyitrace-site-default-ttl.v1', stable_command=V.STABLE, stable_argv=['desktop', '--write-invite', '[private]'],
        slot=b['version'], release_sha256=b['sha256'], exit=0, ttl_seconds=1200, created_at=NOW + 96, ready_at=NOW + 97,
        expires_at=NOW + 1296, closed_at=NOW + 98, owner_exit=0, session_linkage_verified=True, public_port_443_closed=True,
        private_handoff_cleanup_verified=True, existing_cert_and_timers_preserved=True)
    put('site2-final-status', 'ruyitrace-host-health.v1', command='status', release=releases[1], manager_pending=False, site=quiet,
        previous=dict(version=a['version'], release_sha256=a['sha256']), last_verified=dict(state='historical', verified_utc=utc(95), release_sha256=b['sha256']))
    images = ['ruyidom:sample sha256:' + HEX, 'ruyijs:sample sha256:' + HEX]
    for after, n in ((False, 0), (True, 105)):
        put('surface-after' if after else 'surface-baseline', host=V.HOST, arch=V.ARCH, active_trace_leases=0, time=utc(n), docker_engine='native',
            docker_sock_dev_inode=[1, 2], sshd_config_hashes={'sshd_config': HEX}, ruyidom_wrapper_target='/rootless/host.py',
            ruyidom_files={'host.py': HEX}, ruyijs_wheels={'r432.whl': HEX}, non_trace_images=images,
            non_trace_images_sha256=V.sha(wire(images).rstrip(b'\n')), listener_addresses=['tcp 0.0.0.0:22'],
            units=dict.fromkeys(('ssh.service', 'ssh.socket', 'docker.service'), ['ActiveState=active']),
            user_commands=['ruyidom', 'ruyitrace'] if after else ['ruyidom'], initial_ledger_count=int(after),
            cpus=4, neighbor_project_dirs=['ruyidom-artifacts', 'ruyijs-artifacts'], operator_user='ubuntu',
            non_trace_containers=[], non_trace_containers_sha256=V.sha(b'[]'))
        put('site-after' if after else 'site-before', 1,
            cloud=dict(public_ip=V.IPV4, private_ip='10.0.0.139', tcp_80_and_443_admission=True, oci_ingress_sha256=HEX),
            host=dict(utc=utc(n), hostname=V.HOST, arch=V.ARCH, system_ca_verified=True, projected_key_permissions='root:0400', public_leaf_sha256=HEX,
                      existing_host_allow80_and_443=True, production_broker_installed=True, qa_loaded_units=[], qa_unit_files=0, qa_private_dirs=0,
                      production_runtime_sessions=0, port80_listening=False, port443_listening=False, raw5900_listening=False, host_ip_443_dnat=0,
                      host_iptables_input_sha256=HEX, scoped_containers=dict.fromkeys(('io.ruyitrace.demo.scope', 'io.ruyitrace.demo.qa-client',
                      'io.ruyitrace.qa.native-public', 'io.ruyitrace.qa.public-client'), 0)))
    guarded = dict(V.GUARD_FILES, **{'manager.py': V.MANAGER, 'archive_readback.py': V.ARCHIVE_READER})
    for verb, changed in (('installed', True), ('idempotent', False)):
        put('core-guarded-' + verb, source=V.GUARD_SOURCE, bundle_sha256=V.GUARD_TAR, installed=guarded,
            core_upgraded=changed, new_core=False, ok=True, scope='root site enrollment tools only',
            invite_runtime='/run/ruyitrace-site-invites', state_dir='/var/lib/ruyitrace-site-manager',
            modified_existing_broker=False, opened_listener=False)
    for i, r in enumerate(releases, 1):
        ids = r['image_ids']
        docs[f'guarded-reload-site{i}.json'] = dict(docs[f'idempotent-{r["version"]}.json'], utc=utc(110+i), docker_load_executed=True,
            archive_naming=dict(schema=1, approved=True, config_ids=sorted(ids.values()), docker_manifest_entries=3,
                oci_index_entries=1, oci_index_config_ids=[ids['cli']], repository_tags=0, repositories='absent'))
    for stem, n in (('guarded-before', 110), ('guarded-after', 115)):
        docs[stem + '.json'] = dict(docs['surface-after.json'], time=utc(n))
    put('stable-native-capture', 'ruyitrace-site-capture-acceptance.v1', passed=True, platform=V.PLATFORM, checked_utc=utc(107),
        command='ruyitrace capture demo --case network', variants=['fetch', 'xhr', 'skip-request'], page_readback=[42, 42, None],
        server_requests=[1, 1, 0], interfaces=['lo'], distinct_process_profile_origin=True, host_port_published=False, raw_sha256=V.CAPTURE_RAW)
    put('guarded-final-check', 'ruyitrace-host-health.v1', command='check', passed=True, release=releases[1], checked_utc=utc(114),
        checks=docs['site2-verify.json']['checks'], last_verified=docs['site2-final-status.json']['last_verified'])
    return docs, tuple(ref['sha256'] for ref in refs)


class SiteProof(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix='.trace-site-tests-', dir=REPO)
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.docs, pins = fixture()
        patches = patch.object(V, 'MANIFESTS', pins)
        patches.start(); self.addCleanup(patches.stop)

    def seal(self, emergency=False):
        hashes = {}
        for name, doc in self.docs.items():
            p = self.root / 'raw' / name; p.parent.mkdir(parents=True, exist_ok=True)
            p.write_bytes(wire(doc)); hashes[name] = V.sha(p.read_bytes())
        (self.root / 'index.json').write_bytes(wire(dict(schema='ruyitrace-site-operations-index.v1', source_commit='f' * 40,
             source_tag=V.TAG, emergency=emergency, raw_sha256=hashes)))

    def test_complete_and_emergency_required(self):
        self.seal(); self.assertEqual(V.verify(self.root)['source_tag'], V.TAG)
        with self.assertRaisesRegex(V.Failure, 'emergency receipt required'):
            V.verify(self.root, require_emergency=True)

    def test_emergency_distinct_real_transaction_and_restore(self):
        recover = dict(self.docs['rollback-site1.json'], action='recover', transaction_id='5' * 32)
        restore = dict(self.docs['upgrade-site2.json'], transaction_id='6' * 32)
        a, b = recover['active'], restore['active']
        base = dict(schema='ruyitrace-site-status.v1', ok=True, platform=V.PLATFORM)
        self.docs.update({
            'emergency-pending.json': dict(base, previous=a, active=b, current_target='releases/' + b['version'],
                pending=dict(id='5' * 32, phase='config_fenced', action='activate', old=b, new=a)),
            'emergency-kill.json': dict(schema='ruyitrace-site-emergency-kill.v1', target=V.HOST, manager_sha256=V.MANAGER,
                transaction_id='5' * 32, signal='SIGKILL', wait_returncode=-9, real_manager_process=True,
                noninjected=True, fence_confirmed=True, pid=345, killed_at=utc(67)),
            'emergency-recover.json': recover,
            'emergency-history.json': dict(self.docs['rollback-site1-history.json'], action='activate', id='5' * 32, started=NOW + 66),
            'emergency-receipt.json': dict(self.docs['rollback-site1-receipt.json'], action='activate', id='5' * 32),
            'emergency-post-status.json': dict(base, previous=b, active=a, current_target='releases/' + a['version'], pending=None),
            'restore-site2-after-emergency.json': restore,
            'restore-site2-after-emergency-history.json': dict(self.docs['upgrade-site2-history.json'], id='6' * 32, started=NOW + 68),
            'restore-site2-after-emergency-receipt.json': dict(self.docs['upgrade-site2-receipt.json'], id='6' * 32),
        })
        self.seal(emergency=True); self.assertTrue(V.verify(self.root, require_emergency=True)['emergency'])
        self.docs['emergency-kill.json']['noninjected'] = False
        self.seal(emergency=True)
        with self.assertRaisesRegex(V.Failure, 'native manager SIGKILL'):
            V.verify(self.root, require_emergency=True)

    def test_concurrent_drift_requires_exact_independent_provenance(self):
        before, after = (self.docs[k] for k in ('surface-baseline.json', 'surface-after.json'))
        def update(row, images):
            row['non_trace_images'] = sorted(images)
            row['non_trace_images_sha256'] = V.sha(wire(row['non_trace_images']).rstrip(b'\n'))
        update(before, [f'ruyidom:sample sha256:{HEX}', f'ruyijs:arm64-r432-host1 {V.JS_IMAGE}'])
        update(after, before['non_trace_images'] + [f'{V.JS_ALIAS} {V.JS_IMAGE}'])
        after['user_commands'] = sorted(after['user_commands'] + V.JS_COMMANDS)
        def d(name):
            return self.docs[name + '.json']
        with self.assertRaisesRegex(V.Failure, 'independent attribution required'):
            V.surface_delta(d, {}, {})
        hashes = dict.fromkeys(V.CONCURRENT, HEX)
        with self.assertRaisesRegex(V.Failure, 'independently reviewed RuyiJS provenance bytes'):
            V.surface_delta(d, hashes, {})
        update(after, [f'ruyidom:sample sha256:{HEX}', f'ruyijs:arm64-r432-host1 sha256:{HEX}', f'{V.JS_ALIAS} {V.JS_IMAGE}'])
        with self.assertRaisesRegex(V.Failure, 'exceeds exact concurrent'):
            V.surface_delta(d, hashes, {})

    def test_final_source_gitlink_mismatch(self):
        (self.root / '.git').mkdir()
        with patch.object(V, 'REPO', self.root), patch.object(V, 'git', return_value=b'160000 stale entry'):
            with self.assertRaisesRegex(V.Failure, 'final source/gitlink mismatch'):
                V.verify_git(dict(source_commit='f' * 40, source_tag=V.TAG), None)

    def test_maintained_gitlink_cannot_substitute_different_arm_product(self):
        (self.root / '.git').mkdir()
        commit, checkout = 'a' * 40, 'b' * 40
        def lookup(_repo, *args):
            if args[0] == 'ls-files':
                return f'160000 {checkout} 0\t{V.LINK}'.encode()
            if args[0] == 'merge-base':
                self.assertEqual(args, ('merge-base', '--is-ancestor', commit, checkout)); return b''
            if args[-1] == 'HEAD': return checkout.encode()
            if args[-1].endswith('^{commit}'): return commit.encode()
            if args[-1].endswith(':product/arm64'): return args[-1].split(':')[0].encode()
            self.fail(f'unexpected command {args}')
        with patch.object(V, 'REPO', self.root), patch.object(V, 'git', side_effect=lookup):
            with self.assertRaisesRegex(V.Failure, 'ARM product subtree differs'):
                V.verify_git(dict(source_commit=commit, source_tag=V.TAG), self.root, True)

    def test_unsealed_bytes_and_unindexed_attempt(self):
        self.seal()
        raw = self.root / 'raw/desktop-site1.json'; raw.write_bytes(raw.read_bytes() + b' ')
        with self.assertRaisesRegex(V.Failure, 'byte hash'):
            V.verify(self.root)
        self.seal(); (raw.parent / 'previous-attempt.json').write_bytes(b'{}')
        with self.assertRaisesRegex(V.Failure, 'fixed raw directory'):
            V.verify(self.root)

    def test_rehash_does_not_launder_semantic_failures(self):
        cases = [('enroll-site2', 'docker_load_executed', False, 'Docker load'),
                 ('upgrade-site2-final', 'transaction_id', '2' * 32, 'history'),
                 ('upgrade-site2-receipt', 'image_ids', dict(V.ORIGINALS, edge=V.EDGES[0]), 'receipt'),
                 ('noop-plan-invocation', 'argv', ['upgrade', 'different-slot'], 'command evidence'),
                 ('noop-plan-invocation', 'checked_utc', utc(69), 'final selected B'),
                 ('site2-last-verified', 'registry', {}, 'persisted verification'),
                 ('desktop-site2', 'nonblank', False, 'independent native'),
                 ('desktop-site2', 'last_public_ready', {'status': 200, 'header_version': '2'}, 'public ready'),
                 ('desktop-site2', 'upgrade_plan', {'tested': False}, 'real B upgrade-busy'),
                 ('desktop-site1', 'checked_utc', utc(5), 'witness windows'),
                 ('default-ttl', 'ttl_seconds', 180, 'default TTL'),
                 ('core-guarded-idempotent', 'core_upgraded', True, 'root core exchange'),
                 ('guarded-reload-site1', 'docker_load_executed', False, 'real guarded reload'),
                 ('guarded-reload-site2', 'archive_naming', dict(fixture()[0]['guarded-reload-site2.json']['archive_naming'],
                      repository_tags=1), 'ID-only Docker and OCI'),
                 ('stable-native-capture', 'server_requests', [1, 1, 1], 'stable isolated native capture'),
                 ('surface-after', 'listener_addresses', ['tcp 0.0.0.0:22', 'tcp 0.0.0.0:443'], 'surface changed'),
                 ('site-after', 'host', dict(fixture()[0]['site-after.json']['host'], host_iptables_input_sha256='b'*64), 'firewall changed')]
        for stem, key, value, error in cases:
            with self.subTest(stem=stem, key=key):
                self.docs = fixture()[0]; self.docs[stem + '.json'][key] = value
                self.seal()
                with self.assertRaisesRegex(V.Failure, error):
                    V.verify(self.root)

    def test_duplicate_keys_private_values_and_partial_index(self):
        self.seal(); p = self.root / 'index.json'; p.write_bytes(b'{"schema":1,"schema":2}')
        with self.assertRaisesRegex(V.Failure, 'duplicate JSON'):
            V.verify(self.root)
        self.docs['desktop-site1.json']['invite_url'] = 'redacted-looking-but-private'
        self.seal()
        with self.assertRaisesRegex(V.Failure, 'private JSON'):
            V.verify(self.root)
        p.write_bytes(wire(dict(schema='ruyitrace-site-operations-index.v1', source_tag=V.TAG, source_commit='f'*40,
                                emergency=False, raw_sha256={})))
        with self.assertRaisesRegex(V.Failure, 'fixed receipt index'):
            V.verify(self.root)


if __name__ == '__main__':
    unittest.main()
