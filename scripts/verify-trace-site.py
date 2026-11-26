#!/usr/bin/env python3
"""Verify the fixed final ARM64 site-operation publication, offline."""
import argparse
from datetime import datetime
import hashlib
import json
import os
from pathlib import Path
import re
import stat
import subprocess

REPO = Path(__file__).resolve().parents[1]
ROOT = REPO / 'artifacts/receipts/trace-arm64-site-operations'
LINK = 'submodules/ruyitrace'
HOST, ARCH, PLATFORM = 'oracle-reverse-dev', 'aarch64', 'linux/arm64'
ORIGIN, IPV4 = 'https://trace-arm64.zhangxuemin.work', '140.245.61.236'
STABLE = '/home/ubuntu/.local/bin/ruyitrace'
BASE = 'f1253a6ddf03dffa178d349231facc61866e686b'
EDGE_SOURCE = '41a5fbf5a760922ce442729080e8bb711418a5a4'
HOST_SOURCE = '317b6f5575c5c55a215d7b1d66dc52e61f002185'
GUARD_SOURCE = '776b6d24c327f308b252d6d8ae3c3c7586a72ff7'
GUARD_TAR = '0a5a896c45b4e235915f370eaa9a7da9ba9224aac8c311de4cca8e51b8cede67'
GUARD_FILES = {'archive_names.py': 'd63e67f97e5cccf692e169a8ffd4cb869eb94a60817001354ce00a3dfc23bebe',
               'install.py': '34567482a142bc981ba24f7ead5bbbb03d75ad59bd498959702998592ba0d678'}
ARCHIVE_READER = '4d962a84eac7593773ebf63caaa0bed296525db87985cf5cc749bf0eea0efa1a'
CAPTURE_RAW = '2963fa28ec379e97d5c7c261a5b170a49f6e01e08349af954ecd0421abd1aee5'
TAG = 'arm64-site-ops-v1'
MANAGER = '79af5d55f9ef366b2bf223165064ce482b4dd6c6a4d0f929fccf200392dbc667'
ORIGINALS = dict(cli='sha256:9073c375ff26a8248e055e54f1ca28f289d92fc7f253d36685973fa8ecdd33bc',
                 interactive='sha256:3551d08e4cb9096cd453542da67dbd17e0a79b44e88887ca5e6ddef2b699eb43')
EDGES = ('sha256:928dfcbbfb4718a6020d8de96c8d24dbb095a26b51b104e3bfe7e4f98f7ba691',
         'sha256:87518680ba27c6564e6b5895350d23da09e278fbdd1c33fbea5773f481fee7c5')
MANIFESTS = ('55af3676c433c4db0db228187b6838b70db21b374058dc3ea8c4f1285ceaa600',
             '2d376eeed54510f870264f50a4c099faff56e7f4b9303fdf9e6734e7f3766acb')
ARCHIVES = (('ruyitrace-public-edge-tls-lease-v1-linux-arm64.docker.tar.gz', 381640590,
             '1de33f49c6ceac4cfd1686b42203bddb1255882c67cad80b4b617247c1c267cb'),
            ('ruyitrace-public-edge-tls-lease-v1-arm64.site2.docker.tar.gz', 381656666,
             'e228e6ce839b6f3c0216ca81e978a6d655ed77a146acf5476f6fc82f2a23be75'))
READBACKS = dict(cli='aa412b3769f06cd1044c1113253f0875cc40cbaed9d58f1682df4465aeec242b',
                 interactive='53c8584dd5dd5f65cc90737ccbf8521dd461a195eb29110a49d273b64bea1ff6',
                 edge=('76ea1b3083c3ac301b0a3f8e45a7d890ecd59f9928a0a746b62eaa41d2cae51a',
                       'ec237d96a8cf4bbc32b073f55aeba5289073c37f8147770d968729199e5d7272'))
STOCK = 'de7b16588bf3ab11774f6c1b1461dafde943c1cf0ea93dc15aa5f7bd99aa1191'
DEPS = 'b58a45b27a43e9b1ab76f09773bf7b1efa9a295966838c94fd37f2e2c6394f70'
FIXTURE = '87895cfa1d3433d17f50f25eb07bf29828a07299e2489adb9149bca72e9509f4'
ACTIONS = ('adopt-site1', 'upgrade-site2', 'rollback-site1', 'upgrade-site2-final')
NORMAL = {x + '.json' for x in '''bootstrap-installed bootstrap-idempotent user-link-install user-link-idempotent
 two-approved-versions noop-plan noop-plan-invocation desktop-site1 desktop-site2 default-ttl surface-baseline surface-after
 site-before site-after site2-final-status core-guarded-installed core-guarded-idempotent guarded-reload-site1
 guarded-reload-site2 guarded-before guarded-after guarded-final-check stable-native-capture'''.split()}
NORMAL |= {f'{s}{tail}.json' for s in ACTIONS for tail in ('', '-history', '-receipt')}
NORMAL |= {f'{template.format(i=i)}.json' for i in (1, 2) for template in (
    'site{i}/release', 'site{i}/slot-review', 'enroll-site{i}', 'idempotent-r5-arm64-site{i}', 'site{i}-verify', 'site{i}-last-verified')}
EMERGENCY = {f'emergency-{x}.json' for x in ('kill', 'pending', 'recover', 'history', 'receipt', 'post-status')}
EMERGENCY |= {f'restore-site2-after-emergency{x}.json' for x in ('', '-history', '-receipt')}
CONCURRENT = {x + '.json' for x in ('concurrent-ruyijs', 'surface-repeat-before', 'surface-repeat-after', 'post-concurrent-smoke')}
JS_INFRA_REF = '8cdf2740b9d8e316b14246b453d74edf0408fe8e'
JS_TAG_REF = 'e3aa1f3fd98baff69802e9e022d456da93d71694'
JS_PROOF_SHA = 'd46e3b65d2b14c413063daa0c9580dfb9804fa5798f4450c9568989400014d5e'
JS_ALIAS = 'ruyijs:arm64-use'
JS_IMAGE = 'sha256:82dcd7b11350ccf90dc38805b5c1d10df9e89c59c2c4a67c5b1b2cfedd28602c'
JS_COMMANDS = ['ruyijs', 'ruyijsctl']
LIMIT = 1024 * 1024


class Failure(ValueError):
    pass


def need(ok, label):
    if not ok:
        raise Failure(label)


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def hexid(value, width=64):
    return type(value) is str and re.fullmatch(f'[a-f0-9]{{{width}}}', value) is not None


def positive(value):
    return type(value) is int and value > 0


def fields(doc, label, **expected):
    # JSON equality is type-strict recursively (Python bool is an int).
    need(type(doc) is dict and all(k in doc and json.dumps(doc[k], sort_keys=True) ==
         json.dumps(v, sort_keys=True) for k, v in expected.items()), label)


def utc(value):
    need(type(value) is str and re.fullmatch(r'\d{4}-\d\d-\d\dT\d\d:\d\d:\d\d(?:\.\d{1,9})?(?:Z|\+00:00)', value), 'UTC timestamp')
    # Docker emits nanoseconds; older Python ISO parsers accept exactly six fractional digits.
    value = re.sub(r'\.(\d+)', lambda m: '.' + m[1][:6].ljust(6, '0'), value)
    return datetime.fromisoformat(value.replace('Z', '+00:00')).timestamp()


def unique(pairs):
    doc = dict(pairs)
    need(len(doc) == len(pairs), 'duplicate JSON member')
    private = {'session', 'invite_url', 'invitation_url', 'invitation_token', 'private_key', 'authorization', 'cookie', 'token', 'password', 'secret'}
    need(not private.intersection(k.lower() for k in doc), 'private JSON member')
    return doc


def read(path):
    need(path.resolve(strict=True) == path, 'receipt symlink')
    with os.fdopen(os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK), 'rb') as f:
        s = os.fstat(f.fileno())
        need(stat.S_ISREG(s.st_mode) and 0 < s.st_size <= LIMIT, 'receipt type/size')
        raw = f.read(LIMIT + 1)
        need(len(raw) == s.st_size and os.fstat(f.fileno()).st_ctime_ns == s.st_ctime_ns, 'receipt changed during read')
    need(not re.search(rb'/#[A-Za-z0-9_-]{16,}|-----BEGIN [A-Z ]*PRIVATE KEY-----', raw), 'private receipt material')
    doc = json.loads(raw.decode('utf-8'), object_pairs_hook=unique,
                     parse_constant=lambda _: need(False, 'non-finite JSON number'))
    need(type(doc) is dict, 'JSON object required')
    return raw, doc


def receipts(root, required):
    _, idx = read(root / 'index.json')
    fields(idx, 'index schema and host release tag', schema='ruyitrace-site-operations-index.v1', source_tag=TAG)
    commit, emergency, hashes = (idx[k] for k in ('source_commit', 'emergency', 'raw_sha256'))
    need(set(idx) == {'schema', 'source_commit', 'source_tag', 'emergency', 'raw_sha256'} and hexid(commit, 40) and
         type(emergency) is bool, 'index source and flags')
    need(emergency or not required, 'emergency receipt required')
    raw = root / 'raw'
    need(type(hashes) is dict, 'fixed receipt index')
    names = NORMAL | (EMERGENCY if emergency else set()) | (CONCURRENT if hashes.keys() & CONCURRENT else set())
    need(set(hashes) == names and raw.is_dir() and not raw.is_symlink(), 'fixed receipt index')
    allowed = names | {'site1', 'site2'}
    need({p.relative_to(raw).as_posix() for p in raw.rglob('*')} == allowed, 'fixed raw directory')
    docs = {}
    for name in sorted(names):
        data, docs[name] = read(raw / name)
        need(sha(data) == hashes[name], 'byte hash: ' + name)
    return idx, docs


def check_slots(d, hashes):
    approved = d('two-approved-versions')
    fields(approved, 'approved versions', schema='ruyitrace-site-versions.v1', ok=True,
           platform=PLATFORM, active=None, previous=None)
    need(type(approved['versions']) is list and len(approved['versions']) == 2, 'two approved slots')
    manifests, refs, inventory, enroll = [], [], [], []
    for i, row in enumerate(approved['versions']):
        num, version = i + 1, f'r5-arm64-site{i + 1}'
        pin, arc = MANIFESTS[i], dict(zip(('name', 'bytes', 'sha256'), ARCHIVES[i]))
        ids = dict(ORIGINALS, edge=EDGES[i])
        meta = dict(platform=PLATFORM, version=version, host_source=HOST_SOURCE, product_source=(BASE, EDGE_SOURCE)[i],
                    readiness_contract=num, image_ids=ids, archive=arc)
        manifest = d(f'site{num}/release')
        fields(manifest, 'immutable slot manifest', schema='ruyitrace-host-release.v1', **meta)
        need(hashes[f'site{num}/release.json'] == pin, 'unapproved raw release manifest')
        fs = manifest['files']
        need({'host.py', 'health.py', 'cli-lock.json', 'interactive-lock.json', 'archive-proof.json', 'release-images.json'} <= set(fs)
             and all(hexid(v) for v in fs.values()), 'slot file digest map')
        review = d(f'site{num}/slot-review')
        fields(review, 'slot review', version=version, host_source=HOST_SOURCE, product_source=meta['product_source'],
               manifest_sha256=pin, product_archive_sha256=arc['sha256'], slot_archive=f'ruyitrace-site-slot-{version}.tar.gz', files=len(fs) + 1)
        need(hexid(review['tar_sha256']) and positive(review['tar_bytes']), 'slot bundle SHA/size')
        event = d(f'enroll-site{num}')
        fields(event, 'live enrollment and Docker load', schema='ruyitrace-site-enroll.v1', version=version, ok=True,
               bundle_sha256=review['tar_sha256'], release_sha256=pin, image_ids=ids, archive_sha256=arc['sha256'],
               archive_bytes=arc['bytes'], archive_gzip_and_layers_verified=True, docker_load_executed=True, slot_new=True,
               activated=False, public_listener_started=False, archive_new=bool(i), already_present=dict(cli=True, interactive=True, edge=not i))
        repeat = d(f'idempotent-{version}')
        expected = dict(event, archive_new=False, slot_new=False, docker_load_executed=False, already_present=dict.fromkeys(ids, True))
        del expected['utc']
        fields(repeat, 'actual immutable slot enrollment repeat', **expected)
        need(utc(repeat['utc']) > utc(event['utc']), 'reinstall must be a separate later run')
        ref = dict(version=version, sha256=pin, inventory_sha256=row['inventory_sha256'])
        fields(row, 'approved installed inventory', **ref, archive=arc, image_ids=ids)
        need(hexid(ref['inventory_sha256']), 'installed slot inventory hash')
        manifests.append(dict(meta, release_sha256=pin)); refs.append(ref); inventory.append(fs); enroll.append(utc(event['utc']))
    need(refs[0]['inventory_sha256'] != refs[1]['inventory_sha256'] and enroll[0] < enroll[1], 'distinct slot inventories/ordering')
    return manifests, refs, inventory, enroll


def installers(d, first):
    installed = d('bootstrap-installed')
    fields(installed, 'bootstrap install', ok=True, source=HOST_SOURCE, new_core=True, modified_existing_broker=False, opened_listener=False)
    need(set(installed['installed']) == {'manager.py', 'install.py', 'archive_readback.py'} and
         installed['installed']['manager.py'] == MANAGER and all(hexid(x) for x in installed['installed'].values()) and
         hexid(installed['bundle_sha256']), 'reviewed manager bytes')
    repeat = d('bootstrap-idempotent')
    fields(repeat, 'bootstrap repeat mutated state', **dict(installed, new_core=False))
    need(repeat.keys() == installed.keys(), 'bootstrap repeat schema changed')
    link = d('user-link-install')
    fields(link, 'stable command installation', ok=True, changed=True, user=1001, command=STABLE, version=first['version'],
           target=f'/opt/ruyitrace/releases/{first["version"]}/host.py',
           installed_links=['/home/ubuntu/.local/share/ruyitrace/releases', '/home/ubuntu/.local/share/ruyitrace/current', STABLE])
    repeat = d('user-link-idempotent')
    fields(repeat, 'stable command repeat mutated state', **dict(link, changed=False, installed_links=[]))
    need(repeat.keys() == link.keys(), 'stable command repeat schema changed')


def transaction(d, stem, action, old, new, ids, recovered=False):
    result = d(stem + ('-recover' if recovered else ''))
    tid = result['transaction_id']
    need(hexid(tid, 32), 'transaction identity')
    fields(result, stem, schema='ruyitrace-site-action.v1', ok=True, action='recover' if recovered else action,
           changed=True, active=new, previous=old)
    history, receipt = d(stem + '-history'), d(stem + '-receipt')
    common = dict(id=tid, action=action, old=old, new=new)
    fields(history, stem + ' history', schema='ruyitrace-site-history.v1', **common)
    fields(receipt, stem + ' receipt', schema='ruyitrace-site-receipt.v1', **common,
           current='releases/' + new['version'], image_ids=ids)
    active = receipt['active']
    fields(active, stem + ' active registry', schema='ruyitrace-site-active.v1', active=new, previous=old)
    need(positive(history['started']) and all(hexid(x) for x in (receipt['endpoint_policy_sha256'], active['registry_sha256'],
                                                                 active['config_sha256'])), 'transaction time or digests')
    return tid, history['started'], receipt['endpoint_policy_sha256'], active['registry_sha256']


def idle(site, leaf):
    fields(site, 'final lease/listener idle', state='idle', live_leases=0, ready_leases=0, listener_443=False,
           docker_published_443=False, tls=dict(material_verified=True, leaf_sha256=leaf, ready_lease_handshake=False))


def native_verify(d, i, release, ref, files, leaf):
    health, saved = d(f'site{i}-verify'), d(f'site{i}-last-verified')
    fields(health, 'stable verify', schema='ruyitrace-host-health.v1', command='verify', passed=True,
           checked_utc=saved['verified_utc'], release=release)
    fields(saved, 'last-verified readback', schema='ruyitrace-host-verified.v1', release=release,
           inventory_sha256=ref['inventory_sha256'], payload_files=len(files))
    need(set(saved) == {'schema', 'verified_utc', 'release', 'archive', 'registry', 'installed_manifests', 'fixtures',
                       'payload_files', 'inventory_sha256'}, 'unexpected last-verified fields')
    fields(health, 'persisted verification differs from stable stdout', **{k: v for k, v in saved.items() if k != 'schema'})
    archive = release['archive']
    fields(saved['archive'], 'verified archive', **archive,
           path=f'/var/lib/ruyitrace-arm64-site/artifacts/{archive["sha256"]}/{archive["name"]}')
    checks = health['checks']
    fields(checks, 'verified installed payload', installed_image_ids=release['image_ids'], inventory_sha256=ref['inventory_sha256'],
           checked_payload_files=len(files), timers={u: dict(active=True, enabled=True) for u in ('certbot.timer', 'ruyitrace-demo-sweep.timer')})
    idle(checks['site'], leaf)
    readback, fixtures = saved['installed_manifests'], saved['fixtures']
    need(set(readback) == set(ORIGINALS) | {'edge'} and all(hexid(x['manifest_sha256']) and positive(x['files']) for x in readback.values()),
         'native installed manifest readbacks')
    manifest_shas = dict(READBACKS, edge=READBACKS['edge'][i - 1])
    need({k: v['manifest_sha256'] for k, v in readback.items()} == manifest_shas, 'exact native manifest readback identities')
    fields(saved['registry'], 'verified production registry', **{role + '_manifest_sha256': manifest_shas[role]
                                                                 for role in ('edge', 'interactive')})
    need(set(fixtures) == {'baseline', 'exception'}, 'strict native doctor fixture coverage')
    for record in fixtures.values():
        fields(record, 'strict native doctor', exit=0, page_ack=True, native_trace_verified=True, firefox_filter_verified=True)
        need(positive(record['isolated_content_processes']), 'native Firefox isolation witness')
    fields(fixtures['baseline'], 'Storage native evidence', storage_fixture_rows_verified=16, click_files=fixtures['baseline']['core_files'])
    need(positive(fixtures['baseline']['core_files']), 'native click/core evidence')
    fields(fixtures['exception'], 'native uncaught error evidence', exception_rows=1)
    return utc(saved['verified_utc'])


def desktop(d, i, release, ref, other, leaf, registry):
    w = d(f'desktop-site{i}')
    fields(w, 'independent native TLS/WSS desktop', schema='ruyitrace-site-live-desktop.v1', passed=True, stage='complete',
           observer='oracle-dsh', observer_arch=ARCH, browser='Mozilla Firefox 159.0', rootless_read_only_sandbox=True,
           stock_firefox_archive_sha256=STOCK, stock_dependencies_sha256=DEPS, fixture_sha256=FIXTURE,
           target=HOST, target_arch=ARCH, stable_user='ubuntu', stable_command=STABLE, slot=release['version'],
           release_sha256=release['release_sha256'], inventory_sha256=ref['inventory_sha256'], manager_sha256=MANAGER,
           broker_registry_sha256=registry, image_ids=release['image_ids'], ready_contract=i, ttl_seconds=180,
           public_origin=ORIGIN, public_ipv4=IPV4, browser_direct_public=True, framebuffer=[1280, 720], nonblank=True,
           reconnect=True, spent_invite_status=403, unauthorized_grant_status=403, session_linkage_verified=True,
           active_pointer_and_registry_unchanged=True, viewer_connection_survived=True, viewer_disconnected_after_revoke=True,
           owner_exit=0, remaining_lease_containers=0, public_port_443_closed=True, private_handoff_cleanup_verified=True)
    need(not {'error', 'failure_cleanup', 'live_target_actions', 'observer_cleanup_verified'}.intersection(w), 'desktop was not clean live execution')
    ready = w['last_public_ready']
    fields(ready, 'public ready version/header identity', status=200, body_ready=True, header_version=None if i == 1 else '2',
           public_dns_verified=True, system_ca_and_hostname_verified=True, leaf_sha256=leaf)
    need(ready['tls'] in ('TLSv1.2', 'TLSv1.3'), 'public TLS negotiation')
    busy = w['upgrade_plan']
    if busy == {'tested': False}:
        return False
    fields(busy, 'actual ordinary upgrade admission', tested=True, target_version=other['version'], target_sha256=other['sha256'],
           exit=2, error='broker_busy', mutation_path_executed=False)
    return True


def surface(row):
    fields(row, 'site surface identity', host=HOST, arch=ARCH, active_trace_leases=0)
    required = {'cpus', 'docker_engine', 'docker_sock_dev_inode', 'neighbor_project_dirs', 'non_trace_containers',
                'non_trace_containers_sha256', 'operator_user', 'initial_ledger_count', 'ruyidom_wrapper_target'}
    need(required <= row.keys(), 'incomplete host surface')
    for key in ('sshd_config_hashes', 'ruyidom_files', 'ruyijs_wheels'):
        need(type(row[key]) is dict and bool(row[key]) and all(hexid(x) for x in row[key].values()), 'surface SHA map: ' + key)
    imgs, cmds = row['non_trace_images'], row['user_commands']
    need(type(imgs) is list and imgs == sorted(set(imgs)) and all(re.fullmatch(r'\S+ sha256:[0-9a-f]{64}', x) for x in imgs),
         'neighbor image inventory')
    tags = dict(x.split() for x in imgs)
    need(len(tags) == len(imgs) and all(any(x.startswith(p) for x in tags) for p in ('ruyidom', 'ruyijs')) and
         sha(json.dumps(imgs, separators=(',', ':')).encode()) == row['non_trace_images_sha256'] and
         type(cmds) is list and cmds == sorted(set(cmds)) and 'ruyidom' in cmds and
         type(row['listener_addresses']) is list and 'tcp 0.0.0.0:22' in row['listener_addresses'], 'neighbor hash/list and SSH listener')
    for unit in ('ssh.service', 'ssh.socket', 'docker.service'):
        need(type(row['units'][unit]) is list and 'ActiveState=active' in row['units'][unit], 'inactive surface unit: ' + unit)
    containers = row['non_trace_containers']
    need(type(containers) is list and sha(json.dumps(containers, separators=(',', ':')).encode()) == row['non_trace_containers_sha256'],
         'neighbor container fingerprint')
    return tags


def snapshots(d):
    before, after = d('surface-baseline'), d('surface-after')
    sb, sa = d('site-before'), d('site-after')
    leaf = sb['host']['public_leaf_sha256']
    for row in (sb, sa):
        fields(row, 'site snapshot', schema=1)
        host, cloud = row['host'], row['cloud']
        fields(host, 'closed site snapshot', hostname=HOST, arch=ARCH, system_ca_verified=True, projected_key_permissions='root:0400',
               public_leaf_sha256=leaf, existing_host_allow80_and_443=True, production_broker_installed=True, qa_loaded_units=[],
               qa_unit_files=0, qa_private_dirs=0, production_runtime_sessions=0, port80_listening=False,
               port443_listening=False, raw5900_listening=False, host_ip_443_dnat=0,
               scoped_containers={k: 0 for k in ('io.ruyitrace.demo.scope', 'io.ruyitrace.demo.qa-client',
                                                 'io.ruyitrace.qa.native-public', 'io.ruyitrace.qa.public-client')})
        fields(cloud, 'OCI ingress identity', public_ip=IPV4, private_ip='10.0.0.139', tcp_80_and_443_admission=True)
        for values, prior, key in ((host, sb['host'], 'host_iptables_input_sha256'), (cloud, sb['cloud'], 'oci_ingress_sha256')):
            need(hexid(values[key]) and values[key] == prior[key], 'firewall changed: ' + key)
    need(hexid(leaf), 'current TLS leaf hash')
    return leaf, max(utc(before['time']), utc(sb['host']['utc'])), min(utc(after['time']), utc(sa['host']['utc']))


def surface_delta(d, hashes, release):
    documented = CONCURRENT <= hashes.keys()
    before, after = d('surface-baseline'), d('surface-after')
    old, new = surface(before), surface(after)
    variable = {'time', 'initial_ledger_count', 'non_trace_images', 'non_trace_images_sha256', 'user_commands'}
    need(before.keys() == after.keys(), 'surface snapshot fields changed')
    for key in sorted(before.keys() - variable):
        fields(after, 'surface changed: ' + key, **{key: before[key]})
    old_cmds, new_cmds = (set(s['user_commands']) - {'ruyitrace'} for s in (before, after))
    need('ruyitrace' not in before['user_commands'] and 'ruyitrace' in after['user_commands'], 'stable command surface')
    if old == new and old_cmds == new_cmds:
        need(not documented, 'unexpected concurrent change evidence for matching surfaces')
        return
    need(documented, 'observed non-Trace image/command drift; independent attribution required')
    need(old.get(JS_ALIAS) is None and JS_IMAGE in old.values() and new == dict(old, **{JS_ALIAS: JS_IMAGE}) and
         new_cmds == old_cmds | set(JS_COMMANDS) and not old_cmds.intersection(JS_COMMANDS) and
         before['non_trace_images_sha256'] != after['non_trace_images_sha256'], 'change exceeds exact concurrent RuyiJS registration')
    need(hashes['concurrent-ruyijs.json'] == JS_PROOF_SHA, 'independently reviewed RuyiJS provenance bytes')
    provenance = d('concurrent-ruyijs')
    fields(provenance, 'independent RuyiJS attribution', schema='ruyitrace-site-concurrent-ruyijs.v1', host=HOST,
           equal_remaining_protected_fields=sorted(before.keys() - variable))
    for row, k, snap in ((before, 'surface_before', 'surface-baseline.json'), (after, 'surface_after', 'surface-after.json')):
        fields(provenance[k], 'attributed snapshot byte link', path=snap, sha256=hashes[snap], time=row['time'])
    fields(provenance['non_trace_images'], 'attributed image delta', alias=JS_ALIAS, preexisting_image_id=JS_IMAGE,
           preexisting_tag='ruyijs:arm64-r432-host1', platform=PLATFORM, added=[f'{JS_ALIAS} {JS_IMAGE}'], removed=[], retagged=[],
           added_unique_image_ids=[], removed_unique_image_ids=[], aggregate_equal=False, before_count=len(old), after_count=len(new),
           before_sha256=before['non_trace_images_sha256'], after_sha256=after['non_trace_images_sha256'])
    need(old['ruyijs:arm64-r432-host1'] == JS_IMAGE, 'baseline RuyiJS source tag')
    fields(provenance['user_commands'], 'attributed command delta', before=before['user_commands'], after=after['user_commands'],
           added=JS_COMMANDS + ['ruyitrace'], removed=[], concurrent_ruyijs_additions=JS_COMMANDS, trace_addition='ruyitrace')
    source = provenance['independently_corroborating_source']
    fields(source, 'independent deployed RuyiJS source and release', repository='Facetomyself/ruyijs-inner', github_release_id=458848655,
           release_tag='oracle-arm64-r432-host1', release_tag_commit=JS_TAG_REF, tools_match_deployed_and_tagged_commit=True)
    fields(source['infra_docs'], 'independent host observation', commit=JS_INFRA_REF, repository='Facetomyself/openclaw-infra')
    left, right = d('surface-repeat-before'), d('surface-repeat-after')
    smoke = d('post-concurrent-smoke')
    checked = d('site2-verify')
    fields(smoke, 'actual stable B repeat smoke', schema='ruyitrace-host-health.v1', command='smoke', passed=True,
           release=release, checks=checked['checks'], fixtures=checked['fixtures'])
    start, end = utc(before['time']), utc(after['time'])
    need(utc(provenance['non_trace_images']['docker_image_created_utc']) < start < utc(source['infra_docs']['reported_checked_utc']) <= end <=
         utc(left['time']) <= utc(smoke['checked_utc']) <= utc(right['time']) <= utc(provenance['live_readback_utc']) and
         utc(left['time']) < utc(right['time']), 'concurrent attribution and repeat chronology')
    for row in (left, right):
        need(row.keys() == after.keys(), 'repeat surface schema differs')
        fields(row, 'repeat surface differs', **{k: v for k, v in after.items() if k != 'time'})


def hardened(d, releases, repeat):
    old = d('bootstrap-installed')
    need(old['installed']['archive_readback.py'] == ARCHIVE_READER, 'original archive reader bytes')
    installed = dict(GUARD_FILES, **{'archive_readback.py': ARCHIVE_READER, 'manager.py': MANAGER})
    for stem, upgraded in (('core-guarded-installed', True), ('core-guarded-idempotent', False)):
        fields(d(stem), 'guarded root core exchange and repeat', source=GUARD_SOURCE, bundle_sha256=GUARD_TAR,
               installed=installed, core_upgraded=upgraded, new_core=False, ok=True, scope='root site enrollment tools only',
               invite_runtime='/run/ruyitrace-site-invites', state_dir='/var/lib/ruyitrace-site-manager',
               modified_existing_broker=False, opened_listener=False)
    before, after = d('guarded-before'), d('guarded-after')
    prior = d('surface-repeat-after' if repeat else 'surface-after')
    for row in (before, after):
        surface(row)
        need(row.keys() == prior.keys(), 'guarded host surface schema')
        fields(row, 'guarded Docker loads changed sampled host surface', **{k: v for k, v in prior.items() if k != 'time'})
    capture = d('stable-native-capture')
    fields(capture, 'stable isolated native capture', schema='ruyitrace-site-capture-acceptance.v1', passed=True, platform=PLATFORM,
           command='ruyitrace capture demo --case network', variants=['fetch', 'xhr', 'skip-request'], page_readback=[42, 42, None],
           server_requests=[1, 1, 0], interfaces=['lo'], distinct_process_profile_origin=True, host_port_published=False,
           raw_sha256=CAPTURE_RAW)
    loaded = []
    for i, release in enumerate(releases, 1):
        row, ids = d(f'guarded-reload-site{i}'), release['image_ids']
        approval = {k: v for k, v in d(f'idempotent-{release["version"]}').items() if k != 'utc'}
        approval['docker_load_executed'] = True
        fields(row, 'real guarded reload of immutable approved slot', **approval)
        fields(row['archive_naming'], 'ID-only Docker and OCI archive naming', schema=1, approved=True, config_ids=sorted(ids.values()),
               docker_manifest_entries=3, oci_index_entries=1, oci_index_config_ids=[ids['cli']], repository_tags=0, repositories='absent')
        loaded.append(utc(row['utc']))
    check = d('guarded-final-check')
    fields(check, 'idle B after guarded Docker loads', schema='ruyitrace-host-health.v1', command='check', passed=True,
           release=releases[1], checks=d('site2-verify')['checks'], last_verified=d('site2-final-status')['last_verified'])
    need(utc(prior['time']) <= utc(capture['checked_utc']) <= utc(before['time']) < loaded[0] < loaded[1] <=
         utc(check['checked_utc']) <= utc(after['time']), 'capture, guarded load, and final idle chronology')


def verify(root, require_emergency=False):
    idx, docs = receipts(root, require_emergency)
    def d(stem):
        return docs[stem + '.json']
    releases, refs, inventory, enrolled = check_slots(d, idx['raw_sha256'])
    a, b = refs
    installers(d, a)
    leaf, begin, end = snapshots(d)
    txs = [transaction(d, stem, action, old, refs[new], releases[new]['image_ids']) for stem, action, old, new in zip(
        ACTIONS, ('adopt', 'activate', 'rollback', 'activate'), (None, a, b, a), (0, 1, 0, 1))]
    tids, times, policies, registry = zip(*txs)
    t0, t1, t2, t3 = times
    need(len(set(tids)) == 4 and len(set(policies)) == 1 and registry[1] == registry[3] and registry[1] != registry[0] and
         begin < enrolled[0] < enrolled[1] <= t0 < t1 < t2 < t3 < end, 'ordinary A/B transaction ordering, identities and endpoint policy')
    noop = d('noop-plan')
    fields(noop, 'idle exact-release plan', schema='ruyitrace-site-action.v1', ok=True, action='activate', changed=False,
           eligible=True, transaction_id=None, active=b, previous=a)
    invocation = d('noop-plan-invocation')
    fields(invocation, 'no-op plan command evidence', schema='ruyitrace-site-invocation.v1', exit=0,
           argv=[STABLE, 'upgrade', b['version'], '--sha256', b['sha256'], '--plan'],
           stdout_sha256=idx['raw_sha256']['noop-plan.json'])
    need(t3 <= utc(invocation['checked_utc']) <= end, 'no-op plan is for the final selected B')
    va, vb = (native_verify(d, i + 1, release, refs[i], inventory[i], leaf) for i, release in enumerate(releases))
    wa, wb = (utc(d(f'desktop-site{i}')['checked_utc']) for i in (1, 2))
    ttl = d('default-ttl')
    slot = a if ttl['slot'] == a['version'] else b
    fields(ttl, 'actual default TTL', schema='ruyitrace-site-default-ttl.v1', stable_command=STABLE,
           stable_argv=['desktop', '--write-invite', '[private]'], slot=slot['version'], release_sha256=slot['sha256'], exit=0,
           ttl_seconds=1200, owner_exit=0, session_linkage_verified=True, public_port_443_closed=True,
           private_handoff_cleanup_verified=True, existing_cert_and_timers_preserved=True)
    created, ready, expires, closed = (ttl[k] for k in ('created_at', 'ready_at', 'expires_at', 'closed_at'))
    windows = ((t0, t1), (t2, t3)) if slot == a else ((t1, t2), (t3, end))
    need(all(positive(x) for x in (created, ready, expires, closed)) and expires - created == 1200 and
         created <= ready <= closed < expires and any(lo <= created <= closed <= hi for lo, hi in windows),
         'measured TTL, active slot and closure')
    need((t0 <= wa <= t1 or t2 <= wa <= t3) and (t0 <= va <= t1 or t2 <= va <= t3) and
         (t1 <= wb <= t2 or t3 <= wb <= end) and t3 <= vb <= end, 'A/B witness windows and final verification')
    desktop(d, 1, releases[0], a, b, leaf, registry[0 if wa <= t1 else 2])
    need(desktop(d, 2, releases[1], b, a, leaf, registry[1 if wb <= t2 else 3]) and wa != wb,
         'distinct live desktops and real B upgrade-busy admission')
    final = d('site2-final-status')
    fields(final, 'stable final status and persisted readback', schema='ruyitrace-host-health.v1', command='status',
           release=releases[1], manager_pending=False, previous=dict(version=a['version'], release_sha256=a['sha256']),
           last_verified=dict(state='historical', verified_utc=d('site2-last-verified')['verified_utc'], release_sha256=b['sha256']))
    idle(final['site'], leaf)
    if idx['emergency']:
        emergency(d, refs, releases, tids, policies[0], registry[1:3], t1, wb, t2)
    surface_delta(d, idx['raw_sha256'], releases[1])
    hardened(d, releases, CONCURRENT <= docs.keys())
    return idx


def emergency(d, refs, releases, tids, policy, registry, upgrade, rendered, rollback):
    a, b = refs
    wait = d('emergency-pending')
    fields(wait, 'interrupted manager still selected B', schema='ruyitrace-site-status.v1', ok=True, platform=PLATFORM,
           active=b, previous=a, current_target='releases/' + b['version'])
    p = wait['pending']
    fields(p, 'emergency pending real B→A slot switch', action='activate', old=b, new=a)
    need(p['phase'] in ('prepared', 'config_fenced', 'registry_installed', 'cli_alias_set', 'interactive_alias_set', 'edge_alias_set'),
         'emergency manager stopped before pointer commit')
    tid, started, ep, reg_a = transaction(d, 'emergency', 'activate', b, a, releases[0]['image_ids'], recovered=True)
    fields(p, 'pending transaction linkage', id=tid)
    killed = d('emergency-kill')
    fields(killed, 'native manager SIGKILL', schema='ruyitrace-site-emergency-kill.v1', target=HOST, manager_sha256=MANAGER,
           transaction_id=tid, signal='SIGKILL', wait_returncode=-9, real_manager_process=True, noninjected=True,
           fence_confirmed=True)
    fields(d('emergency-post-status'), 'recovered current selection', schema='ruyitrace-site-status.v1', ok=True, platform=PLATFORM,
           current_target='releases/' + a['version'], active=a, previous=b, pending=None)
    restore, when, ep_b, reg_b = transaction(d, 'restore-site2-after-emergency', 'activate', a, b, releases[1]['image_ids'])
    need(len(set((*tids, tid, restore))) == 6 and ep == ep_b == policy and (reg_b, reg_a) == registry and
         positive(killed['pid']) and upgrade <= rendered <= started <= utc(killed['killed_at']) <= when < rollback,
         'independent emergency transaction and ordered B restore')


def git(repo, *argv):
    return subprocess.check_output(['git', '-C', str(repo), *argv], stderr=subprocess.DEVNULL, timeout=10)


def verify_git(idx, source):
    commit, tag = idx['source_commit'], idx['source_tag']
    if (REPO / '.git').exists():
        need(git(REPO, 'ls-files', '-s', '--', LINK).decode().strip() == f'160000 {commit} 0\t{LINK}', 'final source/gitlink mismatch')
    repo = source or REPO / LINK
    if source is not None or (repo / '.git').exists():
        need(git(repo, 'rev-parse', '--verify', f'refs/tags/{tag}^{{commit}}').decode().strip() == commit, 'final source tag mismatch')
        need(git(repo, 'rev-parse', '--verify', 'HEAD').decode().strip() == commit, 'current source checkout differs from final tag')
        for ref in (BASE, EDGE_SOURCE, HOST_SOURCE, GUARD_SOURCE):
            git(repo, 'merge-base', '--is-ancestor', ref, commit)
        for name, expected in (('manager.py', MANAGER), ('host.py', '62e9281e4d64b300e078257158c7004438920aa1edfd3f10447d16bc89e52b1e'),
                               ('health.py', 'deed667d5ea5b32bef5e20b45dbd72933e7cd411a135114ccb9c14eb068b64e3')):
            for ref in (HOST_SOURCE, commit):
                need(sha(git(repo, 'show', f'{ref}:product/arm64/site/{name}')) == expected, 'installed source bytes: ' + name)
        guarded_paths = {f'product/arm64/site/{name}': h for name, h in GUARD_FILES.items()}
        guarded_paths['product/arm64/release_after_kernel.py'] = ARCHIVE_READER
        for path, expected in guarded_paths.items():
            for ref in (GUARD_SOURCE, commit):
                need(sha(git(repo, 'show', f'{ref}:{path}')) == expected, 'guarded enrollment source bytes: ' + path)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--receipts', type=Path, default=ROOT)
    p.add_argument('--source', type=Path)
    p.add_argument('--require-emergency', action='store_true')
    a = p.parse_args()
    try:
        idx = verify(a.receipts.absolute(), a.require_emergency)
        verify_git(idx, a.source)
    except Failure as exc:
        p.exit(1, f'trace site: {exc}\n')
    except (OSError, ValueError, KeyError, TypeError, AttributeError, IndexError, RecursionError, subprocess.SubprocessError):
        p.exit(1, 'trace site: missing, unexpected or malformed receipt/source evidence\n')
    print('trace site: final ARM64 site evidence verified' + (' (including emergency recovery)' if idx['emergency'] else ''))
    if CONCURRENT <= idx['raw_sha256'].keys():
        print(f'trace site: attributed concurrent RuyiJS addition: {JS_ALIAS} → {JS_IMAGE}; commands ruyijs, ruyijsctl. '
              'Whole-span image-tag fingerprints differ; post-registration repeat matched.')


if __name__ == '__main__':
    main()
