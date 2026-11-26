#!/usr/bin/env python3
"""Read-only verifier for the single reviewed ARM64 lease, not a generic receipt format."""
import argparse
from contextlib import contextmanager
from datetime import datetime
import hashlib
import json
import os
from pathlib import Path
import re
import stat
import subprocess
import tarfile
import zlib

REPO = Path(__file__).resolve().parents[1]
RECEIPTS = REPO/'artifacts/receipts/trace-arm64-native-lease'
SITE = '/home/ubuntu/ruyitrace-arm64-lease-v1'
HOST, ARCH, PLATFORM = 'oracle-reverse-dev', 'aarch64', 'linux/arm64'
DNS, IP, VNIC = 'trace-arm64.zhangxuemin.work', '140.245.61.236', '10.0.0.139'
ORIGIN = 'https://'+DNS
ATTEMPT, BUILD = 'attempt.j1mT36SL', '20261125162841'
BASE = 'c3723ca5f71e860ed19d1fa1a4305da930dc7428'
PRODUCER = '934c67f0cc71f403663e455deb18585e7ee822b5'
HEALTH = '406a0475d393767e7c57e32f2fd44784e5a7cb7d'
ADAPTER = '6002ac28cdcfe8d5c8ac0340f96d258de80038a8'
QA_REVISION = '3c8ec093ba22b714ab57d4685229505182c52d56'
QA_TAR = '9644fccc8ad9ef96316274294a431d9bc18fcf25534377594df955047d45ab6f'
QA_FIRST = 'a3df818a211dacd715b79945dce4185841ec554dc155981041f81db9adf1daa8'
QA_IMAGES = ('sha256:9073c375ff26a8248e055e54f1ca28f289d92fc7f253d36685973fa8ecdd33bc',
             'sha256:3551d08e4cb9096cd453542da67dbd17e0a79b44e88887ca5e6ddef2b699eb43')
QA_DIR = 'product/interactive/qa'
QA_TREES = ('7d1006a9d9e20e30abc0ebb3623272db85885b0b', 'afae41de95b763e104ddb40a6648a35781d63482')
QA_OLD_PEER = '661a6f0c34489df61133d858eded450e2dd963d19c91c809508e35c8bb566662'
QA_BLOBS = {'peer.py': 'e7e7bf1c15e6b457dbe0e4c677d1924b352d953947f9470a11bf01652d639af2',
            'test_qa.py': '0a82f62cb4c168b92aa4f824d5ae9df24ca3adf980fd25c08c6d5e4a68113f41',
            'client.py': '29cbdd644fabc1e54fe8ed64a449eb42d432d18f168ea1a4e20ef6c19690d72d'}
GECKO = '9a2dc53c369c7ae5172018b35988e1d2ffeff402'
DIFF = '58bef440831a743f5504a984504f171397cb409da4b56340a962283e244546e0'
TRACE_INPUT = '6086912b4fa649afb77be7dae15c21fbc58946aba6675d82090cc895c8003558'
RUNTIME = 'sha256:1e624ee86c8114f9d66732d54213fb8b213b3959a94ad4f940213ddb430586ec'
BUILDER = '4afb1045db0fbb9c552b2e7f1ececcf341ebd3481a6f217867679623d4478de8'
ARCHIVE = 'ruyitrace-public-edge-tls-lease-v1-linux-arm64.docker.tar.gz'
FIXTURE = '87895cfa1d3433d17f50f25eb07bf29828a07299e2489adb9149bca72e9509f4'
STOCK = 'de7b16588bf3ab11774f6c1b1461dafde943c1cf0ea93dc15aa5f7bd99aa1191'
VIEWER = 'sha256:9d3201e2689a974f431f090c31e08a3d2c2794da03e483cd31eada8badf0918a'
ROOTS = {'96bcec06264976f37460779acf28c5a7cfe8a3c0aae11a8ffcee05c0bddf08c6',
         '69729b8e15a86efc177a57afb7171dfc64add28c2fca8cf1507e34453ccb1470'}
TAGS = dict(cli='ruyitrace/cli:r5-cli2-arm64', interactive='ruyitrace/interactive:r5-cli2-v1-arm64',
            edge='ruyitrace/public-edge:tls-lease-v1-arm64')
IDENTITY = dict(host=HOST, platform=PLATFORM, attempt=ATTEMPT, build_id=BUILD)
RUNNER = dict(schema=1, host=HOST, source_revision=PRODUCER, run='release-v1', attempt=ATTEMPT, build_id=BUILD)
CASES = ('expire', 'revoke', 'worker-loss')
RAW = tuple(x+'.json' for x in '''kernel-release-summary kernel-configured kernel-archive-audit kernel-runtime-identity
kernel-baseline kernel-exception kernel-page kernel-gate-page kernel-package-result kernel-script-error-build
post-kernel-summary post-kernel-result cli-lock interactive-lock cli-readback
interactive-readback cli-product-manifest cli-doctor private-native private-first-failure private-readiness-recovery private-qa-checkpoint
edge-readback release-images production-verified-release archive-verified archive-export empty-engine loopback-expire loopback-revoke
loopback-worker-loss external-desktop post-cleanup'''.split())
GATES = ('immutable-source', 'kernel', 'locked-images', 'private-readiness-recovery', 'archive-receipts', 'isolated-engine',
         'loopback-lifecycle', 'external-desktop', 'site-cleanup')
TLS = ('TLSv1.2', 'TLSv1.3')
IMMUTABLE_BLOBS = {
    'product/arm64/release_after_kernel.py': '4d962a84eac7593773ebf63caaa0bed296525db87985cf5cc749bf0eea0efa1a',
    'product/arm64/offline/verify_empty.py': '00d2569eab996585fd9ecd8804d9fea54a5e761e4ecd2bbe9739001c4359bed5',
    'product/interactive/qa/public_native.py': 'fcd6c090a8879883c5479937a37749000ad03f5fcbe69ef044cea724d8f3d847',
    'product/arm64/ops/retest_input_ready.py': '502832c01a85b637dcab9605e21fcc80330df1e1bdc0f375c5df1c228c90c310',
}
LIMIT = 4*1024**2


class Failure(Exception):
    pass


def need(ok, reason):
    if not ok:
        raise Failure(reason)


def sha(data):
    return hashlib.sha256(data).hexdigest()


def match(pattern, value):
    return type(value) is str and re.fullmatch(pattern, value) is not None


def digest(value):
    return match('[a-f0-9]{64}', value)


def cid(value):
    return match('sha256:[a-f0-9]{64}', value)


def same(actual, expected):
    if type(actual) is not type(expected):
        return False
    if isinstance(expected, dict):
        return actual.keys() == expected.keys() and fields(actual, **expected)
    if isinstance(expected, list):
        return len(actual) == len(expected) and all(same(x, y) for x, y in zip(actual, expected))
    return actual == expected


def fields(obj, **expected):
    return isinstance(obj, dict) and all(k in obj and same(obj[k], v) for k, v in expected.items())


def pos(value, cap=2**63-1):
    return type(value) is int and 0 < value <= cap


def utc_seconds(value):
    need(match(r'\d{4}-\d\d-\d\dT\d\d:\d\d:\d\d(?:Z|\+00:00)', value), 'utc-timestamp')
    return datetime.fromisoformat(value.replace('Z', '+00:00')).timestamp()


@contextmanager
def gate(label):
    try:
        yield
    except (OSError, ValueError, KeyError, IndexError, TypeError, AttributeError, EOFError, RecursionError,
            subprocess.SubprocessError, tarfile.TarError, zlib.error) as exc:
        raise Failure(label) from exc


def raw_bytes(path):
    need(path.resolve(strict=True) == path, 'receipt-path')
    with os.fdopen(os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK), 'rb') as stream:
        s = os.fstat(stream.fileno())
        need(stat.S_ISREG(s.st_mode) and 0 < s.st_size <= LIMIT, 'receipt-size-or-type')
        data = stream.read(LIMIT+1)
        need(len(data) == s.st_size, 'receipt-size-changed')
        return data


def parse(data):
    def unique(pairs):
        obj = dict(pairs)
        need(len(obj) == len(pairs), 'duplicate-json-member')
        return obj
    def invalid(_):
        raise Failure('nonfinite-json-number')
    obj = json.loads(data, object_pairs_hook=unique, parse_constant=invalid)
    need(type(obj) is dict, 'receipt-not-object')
    return obj


def indexed(root, name, pin, key, files):
    raw = raw_bytes(root/name)
    need(sha(raw) == pin, 'historical-index-sha256')
    index = parse(raw)
    payload = {f: raw_bytes(root/f) for f in files}
    need(index[key] == {f: sha(b) for f, b in payload.items()}, 'historical-raw-sha256')
    return index, {f: (parse(b) if f.endswith('.json') else b) for f, b in payload.items()}


def preflight(root):
    routes = ('oracle-dsh.json', 'hk-relay.json')
    with gate('preflight-files'):
        stage, p = indexed(root/'preflight', 'stage.json', 'bf76f3adb0adcf7724c5d2e74737b755df674a66e9fff7efc8e0c828c7eddd48',
                           'raw_sha256', (*routes, 'host185.json', 'dns.json', 'renewal.json', 'reviewed-gecko-inputs.json',
                                          'oci-shape-and-network.json', 'site-health.json'))
        prov, b = indexed(root/'public-health-browser', 'provenance.json', '88c02a46cf2ae9df5593ef156447d586b60aff02a7213a15dfa215c7c2ab9c58',
                          'sha256', (*routes, 'fixture-closed-at', 'stock-dependencies.json', 'oracle-dsh-native-firefox.json'))
        oci, site, dns, renewal, patch = (p[k+'.json'] for k in ('oci-shape-and-network','site-health','dns','renewal','reviewed-gecko-inputs'))
        need(fields(stage, schema='ruyitrace-arm64-staging.v1', host=HOST, attempt=ATTEMPT, platform=PLATFORM,
                    provisional_build_id=BUILD, source_base=BASE, build_tool_source=PRODUCER) and len(stage['not_yet_established']) == 4
             and fields(oci, display_name=HOST, shape='VM.Standard.A1.Flex', ocpus=4.0, memory_gb=24.0, public_ip=IP, private_ip=VNIC,
                        changed_cloud_network=False) and fields(site, host=HOST, arch=ARCH, kernel_stage='build', kernel_qa_present=False,
                        active_builder=True, caddy='inactive', exact_original_rules=True, port_80=False, port_443=False)
             and fields(dns, host=DNS, ipv4=IP, type='A', proxied=False, created_readback=True)
             and fields(renewal, passed=True, public_certificate_unchanged=True, timer_active=True, port_80_and_443_closed=True)
             and fields(patch, exact_reviewed_patch=True, trace_input_sha256=TRACE_INPUT, gecko_diff_sha256=DIFF), 'preflight-site-or-build')
        leaf = p[routes[0]]['leaf_sha256']
        checks = [p[k] for k in (*routes, 'host185.json')] + [b[k] for k in routes]
        need(digest(leaf) and all(fields(x, schema=1, passed=True, kind='preflight', hostname=DNS, ipv4=IP, port=443,
             leaf_sha256=leaf, ready_status=200, negative_status=404, dns_verified=True,
             system_root_chain_and_hostname_verified=True) and x['tls'] in TLS for x in checks), 'preflight-https')
        firefox = b['oracle-dsh-native-firefox.json']; marker, route = firefox['events']
        need(fields(prov, source=HEALTH) and fields(firefox, passed=True, desktop_tested=False, client_arch=ARCH, exit=0,
                   transport='dsh-direct-stock', stock_firefox_archive_sha256=STOCK, fixture_sha256=FIXTURE,
                   remaining_client_containers=0, stock_dependencies_sha256=prov['sha256']['stock-dependencies.json'])
             and fields(marker, stage='firefox-health', passed=True, named_https=True, strict_certificate_validation=True, public_health_visible=True)
             and fields(route, stage='route-browser', passed=True, kind='preflight', dns=DNS, leaf_sha256=leaf, desktop_tested=False,
                        root_source='stock Mozilla built-in roots', root_sha256=[], viewer_public_dns_verified=True,
                        tls_bypass=False, public_health_visible=True)
             and route['wrong_authority']['kind'] in ('server-tls-alert-no-dns-sni','certificate-verification-failed')
             and utc_seconds(b['fixture-closed-at'].decode().strip()) >= max(utc_seconds(x['checked_utc']) for x in checks),
             'preflight-firefox-health-only')


def git(source, *args):
    env = dict(PATH='/usr/bin:/bin', HOME='/', LANG='C', GIT_CONFIG_NOSYSTEM='1', GIT_CONFIG_GLOBAL='/dev/null',
               GIT_NO_REPLACE_OBJECTS='1', GIT_NO_LAZY_FETCH='1', GIT_TERMINAL_PROMPT='0', GIT_OPTIONAL_LOCKS='0')
    return subprocess.check_output(['/usr/bin/git', '-C', str(source), *args], env=env, stderr=subprocess.DEVNULL, timeout=15)


def reviewed_source(source):
    with gate('immutable-source-unavailable'):
        chain = (BASE, PRODUCER, HEALTH, ADAPTER, QA_REVISION)
        for revision in chain:
            body = git(source, 'cat-file', 'commit', revision)
            frame = b'commit '+str(len(body)).encode()+b'\0'+body
            need(hashlib.sha1(frame).hexdigest() == revision, 'source-commit-object-id')
        for earlier, later in zip(chain, chain[1:]):
            git(source, 'merge-base', '--is-ancestor', earlier, later)
    return source


def source_blob(source, revision, path):
    raw = git(source, 'cat-file', 'blob', revision+':'+path)
    need(sha(raw) == IMMUTABLE_BLOBS[path], 'reviewed-source-blob-sha256')
    return raw


def producer_functions(source, revision, path):
    # Only the embedded reviewed commit IDs select executable code, never the receipt or the worktree.
    scope = {'__name__': 'reviewed_arm64_producer'}
    exec(compile(source_blob(source, revision, path), path, 'exec'), scope)
    return scope


def reviewed_qa(source):
    def tree(revision):
        return {path: row for row,path in (entry.split(b'\t',1) for entry in
                    git(source,'ls-tree','-rz',revision,'--',QA_DIR).split(b'\0') if entry)}
    def checksum(revision, name):
        return sha(git(source,'cat-file','blob',f'{revision}:{QA_DIR}/{name}'))
    original, corrected = tree(PRODUCER), tree(QA_REVISION)
    inventory = tuple(git(source,'rev-parse',f'{r}:{QA_DIR}').decode('ascii').strip() for r in (PRODUCER,QA_REVISION))
    need(inventory == QA_TREES and original.keys() == corrected.keys() and len(corrected) == 17
         and {p for p in corrected if corrected[p] != original[p]} == {f'{QA_DIR}/{n}'.encode() for n in ('peer.py','test_qa.py')}
         and checksum(PRODUCER,'peer.py') == QA_OLD_PEER and checksum(PRODUCER,'client.py') == QA_BLOBS['client.py']
         and all(checksum(QA_REVISION,n) == h for n,h in QA_BLOBS.items()), 'reviewed-private-qa-tree-or-blob')
    source_blob(source,QA_REVISION,'product/arm64/ops/retest_input_ready.py')
    archive = git(source,'-c','tar.umask=0002','archive','--format=tar',QA_REVISION,QA_DIR)
    need(sha(archive) == QA_TAR, 'reviewed-private-qa-archive-sha256')


def private_readiness(get, hashes, source, ids):
    reviewed_qa(source)
    original, fixed, proof, checkpoint = (get(k) for k in
        ('private-first-failure','private-native','private-readiness-recovery','private-qa-checkpoint'))
    ui = ids['interactive']; report_sha = hashes['private-native.json']; evidence = SITE+'/evidence/release-v1/'
    need((ids['cli'],ui) == QA_IMAGES and hashes['private-first-failure.json'] == QA_FIRST
         and fields(original, schema=1, passed=False, image_id=ui, platform=PLATFORM,
                    failure_phase='confirm capture off and reconnect',
                    failure='QA peer finish: timed out waiting for matching rendered Firefox fixture pixels')
         and fields(original['identity_after_reconnect'], build_id=BUILD)
         and fields(original['reconnect']['acks'][-1], clicks=2) and 'canvas_input_ready' not in original['reconnect']
         and 'native_after_stop' not in original, 'preserved-private-readiness-failure')
    need(fields(proof, schema=1, host=HOST, producer=PRODUCER, qa_revision=QA_REVISION, qa_tar_sha256=QA_TAR,
                expected_image=ui, old_sha256=QA_FIRST, old_peer_sha256=QA_OLD_PEER, new_peer_sha256=QA_BLOBS['peer.py'],
                old_source=SITE+'/source/product-'+PRODUCER, new_qa_source='/var/lib/ruyitrace-arm64-site/'+QA_REVISION,
                moved_from=[evidence+'private-native-report.json',evidence+'private-native-output'],
                preserved_in=evidence+'private-qa-failed-'+QA_FIRST[:16], passed=True,
                original_failed_receipt_preserved=True, production_image_changed=False, corrected_fixture_executed=True,
                canvas_input_ready=True, private_qa_sha256=report_sha, checkpoint_sha256=hashes['private-qa-checkpoint.json'])
         and same(checkpoint,dict(image_id=ui,sha256=report_sha))
         and utc_seconds(proof['checked_utc']) <= utc_seconds(proof['completion_utc']) <=
             utc_seconds(get('post-kernel-result')['started']), 'private-readiness-recovery-binding')
    need(fields(fixed['reconnect'], canvas_input_ready=True) and fields(fixed['page_final']['acks'][-1],
                    clicks=3,drops=1,submits=1,sliderOK=True,textOK=True,titleOK=True)
         and fixed['identity_after_reconnect']['run_id'] != original['identity_after_reconnect']['run_id'],
         'private-readiness-new-native-run')


def kernel(get):
    s, cfg, audit, ident, base, error, page = (get('kernel-'+x) for x in
        ('release-summary','configured','archive-audit','runtime-identity','baseline','exception','page'))
    configured = dict(arch=ARCH, pin=GECKO, generated_source_stamp=GECKO, generated_build_id=BUILD, sandbox=True,
                      wasm_sandbox=True, rust_target='aarch64-unknown-linux-gnu', rust_library_lto=True, rust_opt_level=1,
                      upstream_audit_sources='match', core_backend=True)
    rust = audit['sha256']; edge = audit['rust_edge_receipt_sha256']; elf = ident['elf_build_id']
    package = dict(kind='audited-candidate', arch=ARCH, build_id=BUILD, archive_sha256=ident['archive_sha256'],
                   libxul_sha256=ident['installed']['files']['libxul.so']['sha256'])
    need(fields(cfg, **configured, archive_audit='pending', browser_capture='pending') and fields(audit, **configured,
             archive='/work/build/obj-wasi159/aarch64-unknown-linux-gnu/release/libgkrust.a', exit_code=0,
             archive_audit='passed', archive_stability='sha256-before-after-v1', rust_edge_profile='arm64-gkrust-thin-v1')
         and all(digest(x) for x in (rust, edge, package['archive_sha256'], package['libxul_sha256']))
         and match('[a-f0-9]{16,128}', elf), 'original-arm64-rust-audit')
    build = dict(profile='arm64-window-script-error-audited-v1', trace_input_sha256=TRACE_INPUT, gecko_diff_sha256=DIFF,
                 attempt=ATTEMPT, source_stamp=GECKO, build_id=BUILD, rust_sha256=rust, elf_build_id=elf,
                 build_libxul_sha256=ident['window_script_error_build']['build_libxul_sha256'])
    need(fields(ident, schema=1, kind=package['kind'], arch=ARCH, attempt=ATTEMPT, audit_exit=0, rust_sha256=rust,
                rust_edge_profile='arm64-gkrust-thin-v1', rust_edge_receipt_sha256=edge, window_script_error_build=build)
         and digest(build['build_libxul_sha256']) and fields(ident['installed'], build_id=BUILD, version='159.0', source_stamp=GECKO)
         and same(get('kernel-script-error-build'),build) and fields(get('kernel-package-result'), passed=True,
                       phase='package_verified', archive_sha256=package['archive_sha256']), 'audited-package-identity')
    counts = {'off':0, 'opt-out':0, 'wrong-origin':0, 'gate-closed':0, 'on':1}; trace = base['gate_trace']
    need(fields(s, schema=1, passed=True, trace_revision=BASE, builder=BUILDER, attempt=ATTEMPT, runtime_image=RUNTIME,
                package=package, gecko_revision=GECKO, gecko_diff_sha256=DIFF, elf_build_id=elf, libgkrust_sha256=rust,
                upstream_audit_exit=0, gate=trace, exception_rows_by_case=counts) and pos(s['archive_bytes'])
         and fields(s['peak'], oom=0, oom_kill=0) and pos(s['peak']['memory'])
         and fields(trace, session_ids=[1,2], closed_markers_found=0) and len(set(trace['click_ids'])) == 2, 'kernel-release-join')
    need(all(fields(x, passed=True, runtime=package) and fields(x['isolation'], machine=ARCH, uid=1000, interfaces=['lo'],
                seccomp=2, no_new_privs=1, capabilities=0) for x in (base,error))
         and fields(base, mode='candidate', require_window_context=True, parent_window_transport=True, extended_producers=True)
         and fields(error, scope='window-script-error-summary', window_script_error_build=build, exception_rows_by_case=counts), 'same-package-native-qa')
    off, on = page['cases']; storage = base['storage_summary_file']
    need(fields(page, passed=True, mode='audited-package', runtime_identity=package) and isinstance(storage,str) and storage
         and fields(off, case='off', core_files=[], verified_storage_file=None) and fields(on, case='on', verified_storage_file=storage)
         and on['core_files'] and on['verified_event_files'] and fields(base, event_files_by_case={'off':[], 'on':on['core_files']})
         and all(fields(x, pid_domain='browser-parent', page_ack=True, png=True, require_window_context=True,
                        require_dom_shape=True, require_clicks=True, require_storage_summary=True, browser_exit=0)
                 and x['content_at_ack'] and match('[a-f0-9]{32}', x['marker']) for x in (off,on)), 'native-page-off-on')
    g = get('kernel-gate-page')
    need(fields(g, mode='audited-package-gate', passed=True, runtime_identity=package, pid_domain='browser-parent', trace=trace,
                png=True, load_barrier_seen=True, failed_step=None, browser_exit=0)
         and match('[a-f0-9]{32}',g['nonce']) and pos(g['observed_writer_pid'])
         and [step['step'] for step in g['steps']] == ['start1','stop1','start2','stop2','done'], 'native-page-two-session-gate')
    return package


def images(get, hashes, source, package):
    out, result = get('post-kernel-summary'), get('post-kernel-result')
    ids = out['images']; a = get('archive-verified'); layers = a['layers']
    need(set(ids) == set(TAGS) and len(set(ids.values())) == 3 and all(map(cid, ids.values())), 'distinct-arm64-image-ids')
    cli, ui, edge = (ids[k] for k in TAGS)
    need(fields(out, **RUNNER, passed=True, kernel_summary_sha256=hashes['kernel-release-summary.json'],
                kernel_archive_sha256=package['archive_sha256']) and fields(result, **RUNNER, passed=True, phase='complete',
                summary=SITE+'/evidence/post-kernel-v1/summary.json', summary_sha256=hashes['post-kernel-summary.json'])
         and match(r'\d{8}T\d{6}Z-[a-f0-9]{12}', result['invocation'])
         and utc_seconds(result['started']) <= utc_seconds(result['ended']), 'post-kernel-terminal-join')
    need(fields(a, archive=ARCHIVE, platform=PLATFORM, gzip_crc_verified=True, config_ids=sorted(ids.values()))
         and pos(a['bytes'], 2*1024**3) and digest(a['sha256']) and set(layers) == set(ids.values())
         and all(type(x) is list and 0 < len(x) <= 48 and all(map(cid,x)) for x in layers.values())
         and layers[ui][:-1] == layers[cli] and layers[edge][:-1] == layers[ui] and len(set(layers[edge])) == len(layers[edge])
         and same(out['archive'], dict(a, path=SITE+'/edge/release-v1/'+ARCHIVE))
         and same(get('archive-export'), dict(platform=PLATFORM, archive=ARCHIVE, bytes=a['bytes'], sha256=a['sha256'],
                                              edge_image=edge, interactive_image=ui, interactive_parent=cli)), 'archive-receipts-and-rootfs-chain')
    locks = {}
    for role, scope, report, key in (('cli','cli2-release','cli-doctor','doctor_sha256'),
                                     ('interactive','private-release','private-native','acceptance_sha256')):
        lock = locks[role] = get(role+'-lock'); read = get(role+'-readback'); parent = lock['parent_image']; manifest = lock['manifest_sha256']
        need(fields(lock, schema=2, platform=PLATFORM, name=TAGS[role], image_id=ids[role], source_revision=PRODUCER,
                    firefox_build_id=BUILD, gecko_attempt=ATTEMPT, runtime_base=RUNTIME, gecko_archive_sha256=package['archive_sha256'],
                    readback_sha256=hashes[role+'-readback.json']) and lock[key] == hashes[report+'.json']
             and fields(read, passed=True, platform=PLATFORM, scope=scope, tag=TAGS[role], image_id=ids[role], parent=parent,
                        local_parent_id=parent, manifest_sha256=manifest, rootfs_layers=layers[ids[role]]) and pos(read['files'])
             and digest(manifest) and cid(parent) and (parent == cli if role == 'interactive' else parent not in ids.values() and parent != RUNTIME)
             and fields(out['release_locks'][role], path=f'{SITE}/evidence/release-v1/release-locks/{role}/release-lock.json',
                        sha256=hashes[role+'-lock.json']), role+'-release-lock-and-native-readback')
    lock, read = locks['interactive'], get('cli-readback'); trust = read['system_trust']; manifest = get('cli-product-manifest')
    ca = '64e7c24b0536b525fb19b145768bd5e6e12ced0df3db837c34553ea789acd143'
    source_lock = '4d2f54e4be8a33c22ac80acfa78f6dcd740a5a82c594c99f866aa7e79cd7d5fc'
    kernel_bytes = hashes['kernel-runtime-identity.json']
    need(fields(lock, layer_manifest_sha256=lock['manifest_sha256']) and fields(read, runtime=package, runtime_base=RUNTIME,
                cli_revision=BASE, runtime_receipt_sha256=kernel_bytes, source_lock_sha256=source_lock,
                node={'version':'v22.14.0','arch':'arm64'}) and fields(trust, path='/usr/lib/ssl/cert.pem', root_count=120, sha256=ca)
         and set(trust['isrg_roots'].values()) == ROOTS, 'native-cli-runtime-and-public-root-store')
    need(read['manifest_sha256'] == hashes['cli-product-manifest.json'] and fields(manifest, schema=1, scope='cli2-release',
                platform=PLATFORM, cli_revision=BASE, runtime=package, runtime_base=RUNTIME, runtime_receipt_sha256=kernel_bytes,
                source_lock_sha256=source_lock, parent=read['parent'], node_version='22.14.0', ca_bundle_sha256=ca, ca_root_count=120,
                baseline_sha256=hashes['kernel-baseline.json'], exception_sha256=hashes['kernel-exception.json'])
         and len(manifest['files']) == read['files'], 'sealed-cli-manifest-and-raw-qa-sha256')
    manifest = out['edge']['manifest_sha256']; entry = dict(interactive_parent=cli, interactive_image=ui, edge_image=edge,
                  interactive_manifest_sha256=lock['manifest_sha256'], edge_manifest_sha256=manifest)
    need(digest(manifest) and len({manifest, lock['manifest_sha256'], locks['cli']['manifest_sha256']}) == 3
         and same(get('release-images'), {'schema':1,'images':{PLATFORM:entry}})
         and same(get('production-verified-release'), dict(entry,platform=PLATFORM))
         and fields(out['edge'], tag=TAGS['edge'], registry=SITE+'/edge/release-v1/readback/release-images.json',
                    registry_sha256=hashes['release-images.json'], native_readback_sha256=hashes['edge-readback.json']), 'arm64-edge-registry-and-production-readback')
    native = producer_functions(source, ADAPTER, 'product/arm64/offline/verify_empty.py')
    doctor = native['doctor'](get('cli-doctor')); rd = native['edge'](get('edge-readback'), dict(images=ids,edge_manifest=manifest))
    private = get('private-native'); first = private['identity_first_connected']; final = private['native_after_stop']
    keys = ('run_id','pid','start_ticks','owner_pid','owner_start_ticks','build_id')
    no_tcp = private['arm_empty_tcp']
    need(fields(private, schema=1, passed=True, image_id=ui, platform=PLATFORM, no_container_published_ports=True, framebuffer=[1280,720])
         and fields(no_tcp, listeners=[], viewer_ui_http=200, no_published_ports=True, machine=ARCH, interfaces=['lo'],
                    uid=1000, gid=1000, readonly=True, seccomp=2, no_new_privs=1, capabilities=dict.fromkeys(('CapInh','CapPrm','CapEff','CapBnd'),0))
         and fields(first, build_id=BUILD, headed_kiosk=True, private_rfb_0600=True, embedded_init=True, main_processes=1)
         and pos(first['pid']) and pos(first['owner_pid']) and all(match('[1-9][0-9]*', first[k]) for k in ('start_ticks','owner_start_ticks'))
         and isinstance(first['run_id'],str) and first['run_id'] and all(fields(private['identity_'+k], **{i:first[i] for i in keys}) for k in
             ('before_disconnect','after_reconnect')) and fields(final, run_id=first['run_id'])
         and fields(final['trace'], fixture_native_clicks=1, native_stop_observed=True, closed_title_markers=0), 'private-native-noVNC')
    empty = get('empty-engine')
    need(fields(empty, schema=1, platform=PLATFORM, passed=True, scope='native ARM64 isolated empty Docker engine archive acceptance',
                archive={k:a[k] for k in ('bytes','sha256')}, imported_config_ids=ids, initial_images=0, remaining_private_containers=0,
                rootfs_layer_counts={k:len(layers[v]) for k,v in ids.items()}, rootfs_prefix_chain_verified=True,
                private_namespaces=dict.fromkeys(('pid','mnt','net','ipc'),True), host_daemon_identity_unchanged=True, private_engine_stopped=True,
                cli_doctor=doctor, edge_readback=rd, interactive=dict(passed=True,viewer_uds_http=200,owner_exit=0,profile_and_socket_removed=True))
         and match(r'29\.\d+\.\d+(?:[.+-][\w.+-]+)?', empty['docker_server_version']), 'independent-empty-engine')
    return ids, a, utc_seconds(result['ended'])


def network(get, source, ids, archive, ended):
    harness = sha(source_blob(source, ADAPTER, 'product/interactive/qa/public_native.py'))
    checked = []
    for case in CASES:
        x = get('loopback-'+case)
        need(fields(x, schema=1, passed=True, platform=PLATFORM, scenario=case, phase='reconcile', public_listener=False,
                    scope='native loopback TLS fixture, two network-none Firefox sessions, no public demo',
                    harness_sha256=harness, edge_image_id=ids['edge'], interactive_image_id=ids['interactive'],
                    default_policy_seconds=1200, test_ttl_seconds=90 if case=='expire' else 140, loopback_bind_verified=True,
                    active_session_revoked=True, runtime_directory_removed=True, tls_listener_removed=True,
                    owned_containers_remaining=0, owner_exit=0, cli_orderly_stop=True, firewall='never-managed')
             and (fields(x, simulated_worker_loss=True) if case=='worker-loss' else 'simulated_worker_loss' not in x)
             and x['reason'] in {'expire':('expired',), 'revoke':('revoked',), 'worker-loss':('service_stopped',)}[case]
             and all(type(x[k]) is int and x[k] in (401,403,404) for k in ('unauthenticated_grant_status','unauthenticated_asset_status'))
             and type(x['second_redemption_status']) is int and x['second_redemption_status'] in (401,403,409,410)
             and type(x['checked_at']) is int and x['checked_at'] >= ended
             and fields(x['first_view'], stage='connected', tls_hostname_verified=True, fragment_cleared=True,
                        http_only_cookie_hidden_from_js=True, framebuffer=[1280,720], no_manual_code=True)
             and fields(x['reconnect'], stage='reconnected', reused_cookie=True, reused_invitation=False)
             and fields(x['disconnect'], stage='disconnected', active_ws_closed=True), 'native-loopback-'+case)
        checked.append(x['checked_at'])
    x = get('external-desktop'); t, connected, reconnect, disconnected = x['results']; leaf = t['leaf_sha256']
    scope = 'real public DNS/TLS/WSS/Firefox with '
    viewer = (fields(x, transport='dsh-direct-stock', client='oracle-dsh', client_arch=ARCH, stock_firefox_archive_sha256=STOCK,
                     scope=scope+'native Oracle DSH stock Firefox direct egress') and same(t['root_sha256'], []) or
              fields(x, transport='direct', client='host185', client_arch='x86_64', client_image=VIEWER,
                     scope=scope+'host185 direct egress') and type(t['root_sha256']) is list and
              0 < len(t['root_sha256']) == len(set(t['root_sha256'])) <= 2 and set(t['root_sha256']) <= ROOTS)
    need(viewer and digest(leaf) and leaf not in ROOTS and fields(x, schema=1, passed=True, origin=ORIGIN, ipv4=IP, target=HOST,
               target_arch=ARCH, target_cli_image=ids['cli'], target_interactive_image=ids['interactive'], target_edge_image=ids['edge'],
               fixture_sha256=FIXTURE, public_port_443_closed=True, remaining_lease_containers=0, remaining_client_containers=0, owner_exit=0)
         and fields(t, stage='tls', transport=x['transport'], public_ready=200, unauthorized_grant=403, public_dns_verified=True, tls_bypass=False)
         and t['tls'] in TLS and fields(connected, stage='connected', framebuffer=[1280,720], nonblank=True, secure_context=True,
                                      fragment_cleared=True, manual_access_code=False, js_visible_cookie=False)
         and fields(reconnect, stage='reconnected', fresh_url=True, existing_cookie=True, invitation_reuse_status=403)
         and fields(disconnected, stage='disconnected', public_ws_closed=True), 'independent-public-firefox-wss-and-cleanup')
    n = x['native_cli_tls']; external_at = utc_seconds(x['checked_utc'])
    need(external_at >= max(checked) and fields(n, stage='native-cli-public-tls', passed=True, platform=PLATFORM, image_id=ids['cli'],
              scope='target-vNIC; not independent public DNS reachability', leaf_sha256=leaf, ready_status=200,
              python_wrong_authority_verify_code=64, firefox_strict_https=True) and n['tls'] in TLS
         and match(r'insecure certificate|SSL_ERROR_BAD_CERT_DOMAIN|SEC_ERROR_UNKNOWN_ISSUER|MOZILLA_PKIX_ERROR_[A-Z_]+',
                   n['firefox_wrong_authority']), 'production-native-cli-public-ca-negative')
    c = get('post-cleanup')
    need(fields(c, **IDENTITY, schema='ruyitrace-arm64-post-cleanup.v1', os_arch=ARCH, archive_sha256=archive['sha256'],
                public_origin=ORIGIN, public_ipv4=IP, target_vnic=VNIC, public_port=443, public_leaf_sha256=leaf,
                public_chain_and_hostname_verified_with_system_ca=True, qa_private_key_removed=True,
                listeners_80_443=[], loaded_qa_units=[], remaining_lease_containers=0, remaining_qa_client_containers=0, remaining_qa_units=0,
                remaining_lease_runtime_directories=0, caddy='inactive', certbot_timer='active', ssh='active', docker='active')
         and digest(c['qa_ca_sha256']) and c['qa_ca_sha256'] not in {leaf,*ROOTS} and utc_seconds(c['checked_utc']) >= max(external_at,*checked)
         and all(digest(c[k]['before']) and fields(c[k], after=c[k]['before']) for k in ('iptables_sha256','oci_admission_sha256')), 'site-isolation-and-final-cleanup')


def release(root, source, archive, prepare):
    data, hashes = {}, {}
    for name in RAW:
        with gate('missing-or-invalid:'+name):
            raw = raw_bytes(root/name); data[name] = parse(raw); hashes[name] = sha(raw)
    get = lambda name: data[name+'.json']
    source = reviewed_source(source)
    with gate('kernel-receipt-shape'):
        pkg = kernel(get)
    with gate('image-receipt-shape-or-native-check'):
        ids, proof, ended = images(get,hashes,source,pkg)
    with gate('private-readiness-recovery-receipt-shape'):
        private_readiness(get,hashes,source,ids)
    with gate('network-receipt-shape'):
        network(get,source,ids,proof,ended)
    if archive is not None:
        with gate('archive-stream-integrity'):
            need(archive.resolve(strict=True) == archive and archive.lstat().st_size == proof['bytes'], 'archive-path-or-length')
            scanner = producer_functions(source,PRODUCER,'product/arm64/release_after_kernel.py')['archive_readback']
            observed = scanner(archive,proof['layers'])
            need(fields(proof, **observed), 'archive-digest-or-config-layer-mismatch')
    index = dict(IDENTITY, schema='ruyitrace-arm64-release-confirmation.v1', source_base=BASE, producer_revision=PRODUCER,
                 route_fixture_revision=HEALTH, public_fixture_sha256=FIXTURE, adapter_revision=ADAPTER,
                 private_qa_revision=QA_REVISION, private_qa_tar_sha256=QA_TAR,
                 raw_sha256=hashes, platform_checker=dict(mode='release-raw',passed=True,gates=list(GATES)))
    if prepare:
        return index
    with gate('release-confirmation-missing-or-invalid'):
        need(same(parse(raw_bytes(root/'confirmation.json')),index), 'release-confirmation-identity-or-raw-sha256')
    return dict(passed=True, mode='release', scope='native-arm64-release', platform=PLATFORM, build_id=BUILD,
                archive_bytes_checked=archive is not None)


def main(argv=None):
    cli = argparse.ArgumentParser(description=__doc__, allow_abbrev=False)
    mode = cli.add_mutually_exclusive_group(); mode.add_argument('--preflight',action='store_true'); mode.add_argument('--release',action='store_true')
    cli.add_argument('--receipts',type=Path,default=RECEIPTS,help='parent of preflight, public-health-browser and release')
    cli.add_argument('--trace-source', type=Path, help='local git checkout containing reviewed Trace revisions (HEAD is not used)')
    cli.add_argument('--archive',type=Path,help='also stream and verify the exact native Docker export')
    cli.add_argument('--prepare-index',action='store_true',help='emit the raw release checker result and SHA index instead of reading it')
    cli.add_argument('--text',action='store_true',help='emit a single human-readable result line')
    args = cli.parse_args(argv); name = 'preflight' if args.preflight else 'release'
    if args.preflight and (args.archive or args.prepare_index) or args.prepare_index and args.text:
        cli.error('archive and release index are release-only; index emits JSON')
    try:
        root = args.receipts.absolute()
        if args.preflight:
            preflight(root)
            value = dict(passed=True, mode=name, scope='preflight-and-public-health-only', product_release=False, desktop_tested=False)
        else:
            sibling = REPO.parent/'trace-arm64-lease-v1'
            source = args.trace_source or (sibling if sibling.is_dir() else REPO/'submodules/ruyitrace')
            value = release(root/'release',source,args.archive.absolute() if args.archive else None,args.prepare_index)
    except Failure as exc:
        value = dict(passed=False, mode=name, reason=str(exc))
    print(' '.join(f'{k}={v}' for k,v in sorted(value.items())) if args.text else json.dumps(value,sort_keys=True))
    return int(value.get('passed', True) is not True)


if __name__ == '__main__':
    raise SystemExit(main())
