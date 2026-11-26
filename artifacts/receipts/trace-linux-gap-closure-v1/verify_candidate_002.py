#!/usr/bin/env python3
"""Offline, stdlib-only review of the six frozen candidate-002 platform cells."""

import argparse
import datetime as dt
import hashlib
import io
import json
from pathlib import Path
import re
import stat
import struct
import tarfile
import zipfile

HERE = Path(__file__).resolve().parent
PRODUCT = '815556bd57d6f2918f6794f67533b80bc5965fbe'
QA_INITIAL = '7850d6a83cfef818f44ff14d9cef3c96e7c6cdf9'
FIXTURE = 'b831052eca466c39856b182b96029051791766de22633a31d317610251074658'
SCRIPT = 'e59743eb8c208764e7ddb1ea43ad3f80c39a1fa989d05d2fdfecee52ba4b314f'
DESIGN = '5128c4dbd4d160c1d6e0f2588773d6af52799885a0b9902ca4c5d70e566bdd58'
CONTROL_INDEX = 'f3c1b67c4668b7fc5d151f57b485312a2b9f847583651903a452b41ff2d8f0b5'
EVIDENCE = '0253ecf8967eea348ba331df953627d2cde310edde0b15275ec63f02772f387e'
MAX_MEMBER = 100_000
PINS = {
    'arm64': {
        'image': 'sha256:1ae4616eeabc8d3b4317e25162221fe2f47dc1c60d8a14f91af2a4d22215791e',
        'base': 'sha256:9073c375ff26a8248e055e54f1ca28f289d92fc7f253d36685973fa8ecdd33bc',
        'build': '20261125162841', 'host': 'oracle-reverse-dev',
        'archive': 'fa0cdf41ac245318fb51d1a62b6771b644ad0cb6220036a66ccbe3740793ba13',
        'archive_size': 390055722,
        'archive_proof': 'aba373f5097ca2020d74ea3a75ed636731975a08b74bc57c38d01a3cc80a4791',
        'runtime': '299540737e64e4a84a95345b4595a053cf05ed29cf4562e9b846f691faf2ae06',
    },
    'amd64': {
        'image': 'sha256:14f2ce66295f7b041d74db4c22cf8cb24e3ea832df3f74063689e70502590d87',
        'base': 'sha256:eb73d165ea9adc15864aeb054bc90a78670618c5c0606827997d357f1cae05c6',
        'build': '20261123161729', 'host': 'host185',
        'archive': '79c2005f2d020e68f614624c3e0e7765715bc1cca14e9f1571450dacb3dfbcca',
        'archive_size': 396067353,
        'archive_proof': '8a0ceb9551b39d0f4251bd02d31cd0ea3f437fcaf2786b103d8ed53e29257d75',
        'runtime': '571dbc6b0b3ecdaf3dbffde0131534f12744eb9890ca90a4b167423aba2fa11e',
    },
}
# Rows independently specified from the registered experiment, including each negative.
PAIRS = [[call, kind] for call in (1, 2, 3) for kind in ('enter', 'return')]
THROW = [[1, 'enter'], [1, 'throw']]
CASES = {
    'wasm': {'call_export': PAIRS, 'compile_only': [], 'instantiate_only': [],
             'trap': THROW, 'disabled': [], 'other_origin': []},
    'jscall': {'normal': PAIRS, 'throw': THROW, 'skip': [], 'disabled': [], 'other_origin': []},
    'http': {'fetch': [[1, 'network', 'GET', 200]], 'skip': [], 'disabled': [],
             'redirect': [[1, 'network', 'GET', 302], [1, 'network', 'GET', 200]],
             'cache_hit': [[1, 'cache', 'GET', 200]], 'other_origin': []},
}
CELL_NAMES = {
    'wasm': 'registered-wasm-export-boundary',
    'jscall': 'selected-fixedAdd-debugger-frame',
    'http': 'scoped-loopback-get-transaction',
}
CASES_FLAT = {f'{g}--{c}' for g, cs in CASES.items() for c in cs}
SCOPE_FIELDS = ('schema', 'runId', 'origin', 'mode', 'enabled', 'writerPid', 'contentPid',
                'browsingContextId', 'innerWindowId')
ORIGINALS = ('native-ready.json', 'native-armed.json', 'native-events.jsonl', 'native-sealed.json')
MARKERS = ('native-start', 'native-stop', 'native-writer.lock')
ROOT_MEMBERS = sorted((*ORIGINALS, *MARKERS, 'native-config.json', 'profile', 'home', 'xdg'))
DROPS = dict(invalid=0, scope=0, limit=0, protocol=0, io=0)
SOURCES = ('Policy.sys.mjs', 'RuyiNativeTelemetryChild.sys.mjs', 'RuyiNativeTelemetryParent.sys.mjs',
           'Start.sys.mjs', 'Writer.sys.mjs', 'build_image.py', 'compute/Compute.sys.mjs',
           'config.py', 'launch.py', 'net/Network.sys.mjs')
QA_MEMBERS = ('contract/criteria.json', 'contract/intake.py', 'qa/fixture.py',
              'qa/run_case.py', 'qa/target.js')


def need(test, context):
    if not test:
        raise ValueError(context)


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def canonical(obj):
    return (json.dumps(obj, sort_keys=True, separators=(',', ':'), ensure_ascii=True,
                       allow_nan=False) + '\n').encode('ascii')


def equal(actual, expected, context):
    need(canonical(actual) == canonical(expected), context)


def pairs(items):
    obj = dict(items)
    need(len(obj) == len(items), 'duplicate JSON field')
    return obj


def json_value(raw):
    def bad_constant(value):
        raise ValueError(f'non-JSON constant {value}')
    need(0 < len(raw) <= MAX_MEMBER, 'JSON member size')
    return json.loads(raw.decode('utf-8'), object_pairs_hook=pairs, parse_constant=bad_constant)


def object_at(raw):
    obj = json_value(raw)
    need(type(obj) is dict, 'expected JSON object')
    return obj


def match(text, pattern, context):
    need(type(text) is str and re.fullmatch(pattern, text) is not None, context)


def member_name(name):
    match(name, r'[A-Za-z0-9_.-]+(?:/[A-Za-z0-9_.-]+)*', 'unsafe member name')
    need(all(part not in {'.', '..'} for part in name.split('/')), 'unsafe member path')


def read_evidence(path):
    need(path.is_file() and not path.is_symlink() and path.stat().st_size <= 1_000_000,
         'bounded regular evidence ZIP required')
    with zipfile.ZipFile(path) as z:
        infos = z.infolist()
        need(1 < len(infos) <= 750 and sum(i.file_size for i in infos) <= 2_000_000,
             'evidence member count or expansion limit')
        members = {}
        for i in infos:
            name = i.filename
            member_name(name)
            need(name == i.orig_filename and name not in members and not i.is_dir()
                 and stat.S_ISREG(i.external_attr >> 16) and 0 < i.file_size <= MAX_MEMBER,
                 'duplicate or nonregular evidence member')
            raw = z.read(i)
            need(len(raw) == i.file_size, 'evidence member length')
            members[name] = raw
    manifest = members.pop('member-sha256.json')
    need(sha(manifest) == EVIDENCE, 'wrong fixed evidence digest (changed original or manifest)')
    equal(object_at(manifest), {name: sha(raw) for name, raw in members.items()},
          'evidence original-byte hash mismatch')
    return members


class Evidence:
    def __init__(self, members):
        self.members = members
        self.used = set()
        self.run_ids = set()
        self.attempts = set()
        self.obs_hashes = set()

    def raw(self, name):
        self.used.add(name)
        need(name in self.members, f'missing {name}')
        return self.members[name]

    def obj(self, name):
        return object_at(self.raw(name))

    def unique(self, pool, value, context):
        need(value not in pool, f'duplicate {context}: {value}')
        pool.add(value)


def read_criteria(raw):
    need(sha(raw) == FIXTURE, 'installed QA bundle SHA mismatch')
    with tarfile.open(fileobj=io.BytesIO(raw), mode='r:') as t:
        members = t.getmembers()
        need(tuple(i.name for i in members) == QA_MEMBERS and
             all(i.isfile() and i.mode == 0o444 and 0 < i.size <= MAX_MEMBER for i in members),
             'unexpected QA fixture members')
        files = {i.name: t.extractfile(i).read() for i in members}
    need(sha(files['qa/target.js']) == SCRIPT, 'target script SHA mismatch')
    target = files['qa/target.js'].decode('ascii').splitlines()
    need(target[12][19:].startswith('(') and 'function fixedAdd(' in target[12]
         and 'new WebAssembly.Module(' in target[30], 'registered source loci changed')
    for name, index, digest, prefix in (
        ('add', 7, 'f61fd62f57c41269c3c23f360eeaf1090b1db9c38651106674d48bc65dba88ba', 'f2f415504deccd0e'),
        ('trap', 8, '77b3dd4987550501c5bd40138997cf63798dea1c1f8d5c50c6bbc5405ee2798a', '14de952378bf4340'),
    ):
        module = re.fullmatch(rf"  const {name}Hex = '([0-9a-f]+)';", target[index])
        need(module is not None, 'registered module source changed')
        raw_module = bytes.fromhex(module[1])
        need(sha(raw_module) == digest and hashlib.sha1(raw_module).hexdigest()[:16] == prefix,
             'registered module bytes changed')
    return object_at(files['contract/criteria.json'])


def read_controls(e, root, criteria):
    index = (root / 'index.json').read_bytes()
    need(sha(index) == CONTROL_INDEX, 'wrong R5 control index')
    idx = object_at(index)
    need(idx['design_sha256'] == DESIGN and idx['trace_source'] == QA_INITIAL and
         idx['status'] == 'workload_verified_only' and set(idx['targets']) == set(PINS), 'R5 index')
    controls = {}
    for a, p in PINS.items():
        raw = (root / f'{a}.json').read_bytes()
        data = object_at(raw)
        equal(idx['targets'][a], dict(cases=22, native_product_credit=0, sha256=sha(raw)), 'R5 control SHA')
        need(data['arch'] == f'linux/{a}' and data['source_image'] == p['base'] and
             data['firefox_build_id'] == p['build'] and data['page_source_sha256'] == SCRIPT and
             data['passed_workload_cases'] == len(data['cases']) == 22 and data['passed_new_product_sinks'] == 0,
             'not original stock workload-only control')
        cases = {(x['gate'], x['case']): x for x in data['cases']}
        need(len(cases) == 22, 'duplicate R5 control case')
        for (g, c), rec in cases.items():
            spec = criteria['gates'][g]['cases'][c]
            need(rec['writer_observed'] is False and rec['browser_exit'] == -15, 'R5 receipt reports producer credit')
            match(rec['run_id'], r'[a-f0-9]{32}', 'R5 control UUID')
            e.unique(e.run_ids, rec['run_id'], 'stock/candidate run id')
            equal(rec['page'], spec['workload'], 'R5 workload mismatch')
            equal(rec['peer'], spec.get('peer', spec.get('framePeer')), 'R5 peer mismatch')
            need(rec['source_role'] == ('other' if c == 'other_origin' else 'primary'), 'R5 ack origin')
        controls[a] = cases
    return controls


def read_archive(e, a, source_map, repeat):
    p = PINS[a]
    custody = e.raw(f'candidate-002-custody/{a}-image.json')
    # Compare the original manifests byte-for-byte (candidate ID alone is insufficient).
    need(sha(custody) == p['runtime'] and custody == e.raw(f'runtime/{a}/candidate-002/image.json')
         == e.raw(f'runtime/{a}/repeat-002/image.json'), 'Runtime repeat bytes or original manifest mismatch')
    equal(repeat, dict(id=p['image'], manifest_file_sha256=p['runtime'], same_bytes=True), 'Runtime repeat claim')
    image = object_at(custody)
    export = f'export-{a}-002'
    proof_raw = e.raw(f'{export}/archive-proof.json')
    need(sha(proof_raw) == p['archive_proof'], 'wrong fixed archive proof bytes')
    proof = object_at(proof_raw)
    need(proof['schema'] == 'ruyitrace.native-artifact-readback.v1' and proof['source'] == PRODUCT
         and proof['platform'] == f'linux/{a}' and proof['image_id'] == p['image'] and proof['base'] == p['base']
         and proof['build_id'] == p['build'] and proof['archive_sha256'] == p['archive']
         and proof['archive_bytes'] == p['archive_size'] and proof['passed'] is True
         and proof['diffid_readback'] is True and proof['gzip_crc_verified'] is True
         and proof['installed_bytes_match'] is True and proof['patched_kernel_sha256'] is None,
         'archive ID, architecture, source, or actual readback mismatch')
    equal(proof['config_ids'], [p['image']], 'archive imported a different configuration')
    equal(proof['repository_tags'], 0, 'archive uses mutable tag')
    need(proof['archive'] == f'ruyitrace-native-{a}-{p["image"][7:23]}.docker.tar.gz', 'archive file identity')
    layers = proof['rootfs_diffids']
    need(len(layers) == len(set(layers)) == 5 and layers[-1] == image['overlay_diff_id'], 'archive diffid chain')
    for layer in layers:
        match(layer, r'sha256:[a-f0-9]{64}', 'layer digest')
    package_raw = e.raw(f'{export}/installed-package.json')
    package = object_at(package_raw)
    need(sha(package_raw) == image['manifest_sha256'] == proof['installed_package_sha256'], 'installed manifest digest')
    equal(image, dict(package, candidate_image_id=p['image'], overlay_diff_id=layers[-1],
                      manifest_sha256=sha(package_raw)), 'export and tested image manifest mismatch')
    need(package['architecture'] == a and package['base_image_id'] == p['base']
         and package['build_id'] == package['old_build_id'] == p['build']
         and package['scope'] == 'native-events-candidate' and package['patched_firefox_archive_sha256'] is None,
         'mixed candidate package or patched kernel')
    equal(package['source_sha256'], source_map, 'installed product source map')
    equal(proof['source_files'], source_map, 'archive source files')
    equal(package['archive_modules'], {'modules/ruyi-native/' + k: v for k, v in source_map.items()
                                      if k.endswith('.sys.mjs')}, 'installed chrome module hashes')
    need(package['source_set_sha256'] == sha(canonical(source_map)), 'source-set canonical digest')
    before, after = package['old_package_sha256'], package['package_sha256']
    need(all(before[k] == after[k] for k in ('firefox', 'libxul.so', 'browser/omni.ja')) and
         before['omni.ja'] != after['omni.ja'], 'candidate changed the base browser kernel or lacks overlay')
    controller = e.obj(f'{export}/controller.json')
    need(controller['ok'] is True and controller['image'] == p['image'] and controller['source'] == PRODUCT,
         'export controller identity')
    return proof


def jsonl(raw):
    need(raw.endswith(b'\n') and b'\r' not in raw, 'missing original writer newline or changed byte envelope')
    return [object_at(line) for line in raw[:-1].split(b'\n')]


def read_writer(raw, ready, armed, sealed, gate, enabled, prev_unsupported=False):
    header, *rows = jsonl(raw)
    ids = {k: header[k] for k in SCOPE_FIELDS}
    match(ids['runId'], r'[a-f0-9]{32}', 'native run identity')
    match(ids['origin'], r'http://127\.0\.0\.1:[1-9][0-9]{3,4}', 'nonliteral or non-loopback writer origin')
    need(1024 <= int(ids['origin'].split(':')[-1]) <= 65535, 'writer origin port')
    equal([ids['schema'], ids['mode'], ids['enabled']], [1, gate, enabled], 'native scope schema/mode/opt-in')
    need(all(type(ids[k]) is int and ids[k] > 0 for k in SCOPE_FIELDS[5:]) and
         ids['writerPid'] > 1 and ids['writerPid'] != ids['contentPid'], 'invalid browser/window identity')
    equal(header, dict(ids, state='header'), 'writer header shape')
    equal(ready, dict(ids, state='ready'), 'ready scope mismatch')
    equal(armed, None if prev_unsupported else dict(ids, state='armed'), 'armed scope mismatch')
    child = len(rows) if gate in ('wasm', 'jscall') else 0
    equal(sealed, dict(ids, state='sealed', complete=not prev_unsupported,
                       status='unsupported' if prev_unsupported else 'ok', accepted=len(rows), drops=DROPS,
                       childSent=None if prev_unsupported else child, childSeen=child),
          'missing negative tail, drop counter, drain equality, or scope match')
    return ids, rows


def validate_scope(config, config_bytes, controls, scope_index, run, host, ids, gate, case):
    expected = {k: ids[k] for k in ('schema', 'runId', 'origin', 'mode', 'enabled')}
    expected['profile'] = '/runs/case/native/profile'
    if gate == 'jscall':
        expected.update(scriptPath='/target.js', functionName='fixedAdd', jsStartLine=13, jsStartColumn=20)
    elif gate == 'wasm':
        trap = case == 'trap'
        expected.update(scriptPath='/target.js', functionName='trap' if trap else 'add', wasmCompileLine=31,
                        wasmFunctionIndex=0, wasmModuleHash='14de952378bf4340' if trap else 'f2f415504deccd0e',
                        wasmEntryOffset=33 if trap else 35)
    else:
        expected['httpPath'] = {'redirect': '/qa-redirect', 'cache_hit': '/qa-cache'}.get(case, '/qa-http')
    equal(config, expected, 'selected native config differs from registered scope')
    need(run['scope_sha256'] == sha(ids['origin'].encode('ascii')) == sha(config['origin'].encode('ascii')),
         'authorized origin digest mismatch')
    equal(controls, dict(attempt=host['attempt'], run_id=ids['runId'], native_root_members=ROOT_MEMBERS,
                         files={
                             'native-config.json': dict(mode='0o600', bytes=len(config_bytes), sha256=sha(config_bytes)),
                             **{k: dict(mode='0o400' if k == 'native-writer.lock' else '0o600', bytes=0,
                                        sha256=sha(b'')) for k in MARKERS},
                         }), 'scope readback or whole-output enumeration mismatch')
    need(scope_index['config_sha256'] == sha(config_bytes), 'config bytes differ from readback index')


def project_rows(gate, rows, projected):
    if gate == 'http':
        expected = [dict(family=gate, kind='transaction', chain=chain, transport=transport,
                         method=method, status=status, seq=i)
                    for i, (chain, transport, method, status) in enumerate(projected, 1)]
    else:
        expected = [dict(family=gate, kind=kind, call=call, functionKind='wasm' if gate == 'wasm' else 'js',
                         seq=i, **({'moduleId': 1, 'functionIndex': 0} if gate == 'wasm' else {}))
                    for i, (call, kind) in enumerate(projected, 1)]
    equal(rows, expected, 'native row order, pairing, metadata allowlist, or multiplicity mismatch')
    return projected


def witness_metrics(g, case, peer):
    before = [['/qa-cache', 200]] if (g, case) == ('http', 'cache_hit') else []
    routes = {
        'fetch': [['/qa-http', 200]], 'disabled': [['/qa-http', 200]],
        'other_origin': [['/qa-http', 200]], 'redirect': [['/qa-redirect', 302], ['/qa-final', 200]],
    }
    measured = routes.get(case, []) if g == 'http' else []
    equal(peer['pre_measure_http'], before, 'independent server prewarm differs')
    equal(peer['measured_http'], measured, 'independent server route/status differs')
    if g != 'http':
        return None
    if case == 'redirect':
        return {'statuses': [row[1] for row in measured]}
    if case == 'cache_hit':
        return {'new_route_gets': len(measured)}
    if case == 'other_origin':
        return {'other_route_gets': len(measured)}
    result = {'route_gets': len(measured)}
    if case != 'skip':
        result['responses_200'] = sum(row[1] == 200 for row in measured)
    return result


def validate_case(e, a, g, c, proof, preregistered, scope_idx, control):
    pin = PINS[a]
    case = f'{g}--{c}'
    prefix = f'integrated-{a}-002/{case}'
    raw = lambda name: e.raw(f'{prefix}/{name}')
    obj = lambda name: object_at(raw(name))
    run, host = obj('run.json'), obj('host.json')
    page_raw, peer_raw = raw('page.json'), raw('peer.json')
    page, peer = object_at(page_raw), object_at(peer_raw)
    originals = [raw(f'native/{name}') for name in ORIGINALS]
    ready_b, armed_b, rows_b, seal_b = originals
    ids, native = read_writer(rows_b, object_at(ready_b), object_at(armed_b), object_at(seal_b), g, c != 'disabled')
    rid = ids['runId']
    e.unique(e.run_ids, rid, 'candidate/witness run id')
    attempt = host['attempt']
    match(attempt, r'run-[a-f0-9]{20}', 'fresh host attempt ID')
    e.unique(e.attempts, attempt, 'candidate host attempt')
    common = dict(arch=f'linux/{a}', gate=g, case=c)
    for witness in (run, host, page, peer):
        equal({k: witness[k] for k in common}, common, 'wrong arch/gate/case in joined receipt')
    equal(host, dict(common, schema='ruyitrace.gap-host-run.v1', attempt=attempt, host=pin['host'],
                     remote='/var/lib/ruyitrace-gap-qa-v1/attempts/' + attempt, code=0, remaining_containers=0,
                     docker_local_socket=True, base=False, image_id=pin['image'], snapshot_sha256=FIXTURE,
                     additional_native_event_files=[], rootfs_layers=proof['rootfs_diffids']),
          'wrong host, image layer chain, snapshot, output scan or historical/failed attempt')
    need(run['schema'] == 'ruyitrace.native-run.v1' and run['build_id'] == pin['build']
         and run['image_id'] == pin['image'] and run['fixture_js_sha256'] == SCRIPT and run['run_id'] == rid
         and run['scope'] == 'installed-product-native-observation' and 'issue' not in run,
         'runtime mixed source, run or page-only evidence')
    equal([run[k] for k in ('native_product_pass', 'passed', 'browser_reaped', 'browser_exit',
                            'native_status', 'native_files_scan', 'open_public_ports', 'page_witness', 'peer_witness')],
          [True, True, True, 0, 'ok', ['native-events.jsonl'], False, True, g == 'http'],
          'runtime lacked normal exit/whole-output scan or witness')
    times = tuple(dt.datetime.fromisoformat(run[k]) for k in ('started_utc', 'finished_utc'))
    need(all(t.tzinfo == dt.timezone.utc and t.date() == dt.date(2026, 11, 26) for t in times)
         and 0 < (times[1] - times[0]).total_seconds() <= 165, 'unexpected/historical run window')
    role = 'other' if c == 'other_origin' else 'primary'
    equal(run['page_origin_control'], role, 'page role in runtime receipt')
    process = run['writer_process']
    need(type(process['start_ticks']) is int and process['start_ticks'] > 0, 'writer process start missing')
    equal(process, dict(pid=ids['writerPid'], start_ticks=process['start_ticks'], executable='/browser/firefox',
                        libxul_mapped=True, uid=1000, no_new_privs=1, seccomp=2, cap_eff='0000000000000000'),
          'writer process is not isolated Firefox')
    readback = f'candidate-002-scopes/{a}/{case}'
    conf = e.raw(f'{readback}/native-config.json')
    ctrl = e.raw(f'{readback}/controls.json')
    equal(scope_idx, dict(config_sha256=sha(conf), controls_sha256=sha(ctrl)), 'scope index original hashes')
    validate_scope(object_at(conf), conf, object_at(ctrl), scope_idx, run, host, ids, g, c)
    equal(page, dict(common, schema=1, run_id=rid, ack_role=role, observation=preregistered['workload']),
          'independent page workload or caller role')
    metrics = witness_metrics(g, c, peer)
    equal(metrics, preregistered.get('peer'), 'independent peer projection disagrees with design')
    equal(peer, dict(common, schema=1, run_id=rid, measured=True, result_count=1, failures=[],
                     documents_ready=['other', 'primary'] if role == 'other' else ['primary'],
                     pre_measure_http=peer['pre_measure_http'], measured_http=peer['measured_http'],
                     upgrades_101=0, client_to_server=[], server_to_client=[], server_messages=0, metrics=metrics),
          'peer completion, second document, or request provenance mismatch')
    equal([page['observation'], metrics], [control['page'], control['peer']], 'R5 falsification workload drift')
    projected = project_rows(g, native, CASES[g][c])
    equal(run['native_rows'], len(projected), 'runner native count mismatch')
    equal(run['native_metrics'], preregistered['native'], 'derived runtime metric mismatch')
    equal(obj('native-projection.json'), dict(run_id=rid, rows=projected, original_sha256=sha(rows_b),
                                             seal_sha256=sha(seal_b)), 'derived projection lost raw custody')
    brief = dict(gate=g, case=c, passed=True, scope=run['scope'], issue=None, attempt=attempt,
                 native_rows=len(projected))
    return dict(rid=rid, original=originals, page=page_raw, peer=peer_raw, rows=projected,
                scope=run['scope_sha256'], process=process, host=host['host'], brief=brief, times=times)


def validate_packet(e, a, g, cases, observers, manifest_row):
    pin = PINS[a]
    path = f'intake-002/{a}-{g}'
    candidate_raw = e.raw(f'{path}/candidate.json')
    expected = dict(gate=g, arch=f'linux/{a}', source=PRODUCT, artifact_sha256=pin['archive'],
                    fixture_sha256=FIXTURE, build_id=pin['build'])
    observer_count = 0
    manifest_cases = {}
    for case, value in cases.items():
        rid = value['rid']
        seen = {}
        for role in ('native', 'workload', 'peer') if g == 'http' else ('native', 'workload'):
            name = f'{path}/cases/{case}/{role}'
            body = e.raw(f'{name}/source.bin')
            obs = e.raw(f'{name}/observation.json')
            observer_count += 1
            obs_info = dict(expected, schema='ruyitrace.proposed-observation.v1', case=case, run_id=rid,
                            observer=observers[role], complete=True, dropped=0, io_errors=0, source_sha256=sha(body))
            if role == 'native':
                original = b'RUI_NATIVE_ORIGINALS_1\n' + b''.join(struct.pack('>Q', len(b)) + b for b in value['original'])
                need(e.raw(f'{name}/original.bin') == original, 'packet duplicates or reserializes native originals')
                equal(object_at(body), dict(schema='ruyitrace.proposed-native-projection.v1', gate=g,
                                            arch=f'linux/{a}', case=case, run_id=rid, artifact_sha256=pin['archive'],
                                            fixture_sha256=FIXTURE, original_sha256=sha(original),
                                            authorized_scope_sha256=value['scope'],
                                            writer_instance_sha256=sha(canonical(dict(os=value['process'],
                                                image=pin['image'], host=value['host'], run_id=rid))),
                                            all_run_outputs_scanned=True, posthoc_origin_exclusion=False,
                                            source_members=4, unexpected_fixture_rows=0, tail_complete=True,
                                            dropped=0, io_errors=0, rows=value['rows']), 'packet projected different native source')
            else:
                need(body == value['page' if role == 'workload' else 'peer'], 'packet resserialized page or peer original')
                obs_info['metrics'] = object_at(body)['observation' if role == 'workload' else 'metrics']
            equal(object_at(obs), obs_info, 'packet observer identity mismatch')
            seen[role] = sha(obs)
            e.unique(e.obs_hashes, seen[role], 'intake observer receipt')
        manifest_cases[case] = {'run_id': rid, 'observers': seen}
    equal(object_at(candidate_raw), dict(expected, schema='ruyitrace.proposed-candidate.v1',
                                         collection_kind='product-run', cases=manifest_cases), 'wrong intake candidate')
    verdict = e.obj(f'{path}/intake-result.json')
    equal(verdict, dict(arch=f'linux/{a}', cases=len(cases), gate=g, observations=observer_count,
                        product_qualified=False, status='eligible_for_manual_review',
                        reason='package authenticity, origin attribution, independent collector and human witness still require review'),
          'intake result exceeds structural review or misses cases')
    equal(manifest_row, dict(answer=verdict, archive_sha256=pin['archive'], image_id=pin['image'],
                             packet_sha256=sha(candidate_raw)), 'cross-architecture intake manifest mismatch')
    return sha(candidate_raw)


def read_runtime_controls(e, a, summary, proof, source_map):
    pin = PINS[a]
    need(summary['architecture'] == a and summary['base'] == pin['base'] and
         summary['candidate'] == pin['image'] and summary['build_id'] == pin['build'] and
         summary['manifest_file_sha256'] == pin['runtime'] and
         summary['source_set_sha256'] == sha(canonical(source_map)), 'runtime control revision mismatch')
    package = e.obj(f'export-{a}-002/installed-package.json')
    need(summary['old_omni'] == package['old_package_sha256']['omni.ja'] and
         summary['candidate_omni'] == package['package_sha256']['omni.ja'] and
         pin['image'] == proof['image_id'], 'runtime smoke image differs from exported product')
    checks = {rec['kind']: rec for rec in summary['checks']}
    need(len(summary['checks']) == 3 and set(checks) == {'disabled-real-zero', 'positive-http', 'stock-ws-unsupported'},
         'runtime falsification checks')
    for num, name in enumerate(('disabled-real-zero', 'positive-http', 'stock-ws-unsupported'), 7):
        ws = num == 9
        prefix = f'runtime/{a}/smoke-{num:03}'
        smoke = e.obj(f'{prefix}/smoke.json')
        blob = e.raw(f'{prefix}/run/native-events.jsonl')
        seal_raw = e.raw(f'{prefix}/run/native-sealed.json')
        seal = object_at(seal_raw)
        ready = e.obj(f'{prefix}/run/native-ready.json')
        armed = None if ws else e.obj(f'{prefix}/run/native-armed.json')
        ids, rows = read_writer(blob, ready, armed, seal, 'websocket' if ws else 'http', num != 7, ws)
        e.unique(e.run_ids, ids['runId'], 'runtime falsification run id')
        project_rows('http', rows, CASES['http']['fetch'] if num == 8 else [])
        peer = {'peer_gets': 1, 'page_readback': True} if num == 8 else None
        equal([smoke['image'], smoke['browser_exit'], smoke['peer'], smoke['ready'], smoke['armed'], smoke['sealed'], smoke['raw']],
              [PINS[a]['image'], 0, peer, ready, armed, seal, jsonl(blob)], 'runtime original and smoke differ')
        equal(checks[name], dict(kind=name, complete=not ws, status='unsupported' if ws else 'ok', rows=len(rows),
                                 raw_sha256=sha(blob), seal_sha256=sha(seal_raw), peer=peer,
                                 writer_pid=ids['writerPid'], content_pid=ids['contentPid']), 'runtime summary lost original')


def verify(members, control_root):
    e = Evidence(members)
    criteria = read_criteria(e.raw('candidate-002-scopes/qa-snapshot.tar'))
    prior = read_controls(e, control_root, criteria)
    need(e.raw('candidate-002-custody/source-commit') == (PRODUCT + '\n').encode(), 'committed product source pin')
    source_map = e.obj('candidate-002-custody/runtime-sources.json')
    equal(source_map, {name: sha(e.raw(f'source/{name}')) for name in SOURCES}, 'source bytes differ from custody')
    scope_idx = e.obj('candidate-002-scopes/index.json')
    need(scope_idx['schema'] == 'ruyitrace.authorized-scope-readback.v1' and scope_idx['qa_snapshot_sha256'] == FIXTURE
         and set(scope_idx['scopes']) == set(PINS), 'wrong raw scope index')
    repeat = e.obj('runtime/reproducibility.json')['native_repeat']
    runtime = e.obj('runtime/native-runtime-summary.json')
    need(runtime['source_revision_at_worktree_checkout'] == QA_INITIAL, 'unexpected initial QA provenance')
    need(len(runtime['comparison']) == len(PINS), 'unexpected runtime architecture count')
    runtime = {x['architecture']: x for x in runtime['comparison']}
    need(set(runtime) == set(PINS), 'mixed runtime architectures')
    intake = e.obj('intake-002/manifest.json')
    by_key = {(x['answer']['arch'], x['answer']['gate']): x for x in intake['rows']}
    need(intake['schema'] == 'ruyitrace.cross-arch-gate-submission.v1' and len(by_key) == len(intake['rows']) == 6,
         'missing/duplicate intake cells')
    cells = {}
    images = {}
    for a, p in PINS.items():
        proof = read_archive(e, a, source_map, repeat[a])
        read_runtime_controls(e, a, runtime[a], proof, source_map)
        equal(sorted(scope_idx['scopes'][a]), sorted(CASES_FLAT), 'scope index incomplete')
        lane = f'integrated-{a}-002'
        images[a] = dict(image_id=p['image'], archive_sha256=p['archive'], archive_bytes=p['archive_size'],
                         runtime_manifest_sha256=p['runtime'], build_id=p['build'], repeat_equal=True)
        briefs, windows = [], []
        for g, cases in CASES.items():
            expected = criteria['gates'][g]['cases']
            need(set(expected) == set(cases), 'case set differs from preregistration')
            records = {}
            for c in expected:
                try:
                    records[c] = value = validate_case(e, a, g, c, proof, expected[c],
                        scope_idx['scopes'][a][f'{g}--{c}'], prior[a][g, c])
                except (KeyError, ValueError) as exc:
                    raise ValueError(f'linux/{a} {g}--{c}: {exc}') from exc
                briefs.append(value['brief'])
                windows.append(value['times'])
            packet = validate_packet(e, a, g, records, criteria['observer_sources'], by_key[f'linux/{a}', g])
            cells[f'linux/{a}/{CELL_NAMES[g]}'] = dict(cases=len(records),
                observed_native_rows=sum(len(value['rows']) for value in records.values()),
                sealed_zero_cases=[c for c, value in records.items() if not value['rows']],
                packet_sha256=packet, status='bounded_raw_evidence_verified_pending_strict_external_review')
        need(all(first[1] <= second[0] for first, second in zip(windows, windows[1:])), 'lane run windows overlap')
        equal(e.obj(f'{lane}/summary.json'), dict(schema='ruyitrace.gap-lane.v1', arch=f'linux/{a}',
            image_id=p['image'], stock_control=False, snapshot=FIXTURE, requested=17, completed=17,
            passed=True, observations=briefs), 'wrong lane or failed/missing/reordered attempts')
    need(set(members) == e.used, 'extra/unreviewed evidence members')
    need(len(e.obs_hashes) == 80 and len(e.run_ids) == 84 and len(e.attempts) == 34, 'observer/run accounting')
    return dict(schema='ruyitrace.platform-candidate-002-review.v1', evidence_sha256=EVIDENCE,
                evidence_digest_kind='sha256 of exact member-sha256.json bytes in the evidence ZIP',
                evidence_members=len(members), product_source=PRODUCT, initial_qa_source=QA_INITIAL,
                integrated_qa_bundle_sha256=FIXTURE, design_sha256=DESIGN, verified_cases=34,
                structurally_eligible_observers=80, stock_workloads_only=44, images=images, cells=cells,
                status='bounded_raw_evidence_verified_pending_strict_external_review', product_qualified=False,
                websocket='unsupported_on_candidate_002_base_kernels',
                unqualified=['websocket', 'ime', 'display', 'electron'],
                constraints=['synthetic opt-in literal IPv4 loopback, exact top-level /harness',
                             'selected external fixedAdd frame and two registered nonstreaming Wasm exports; metadata only',
                             'only tested HTTP GET cases: network, linked redirect, cache, disabled, skip and foreign caller',
                             'local offline review of recorded custody, not a new capture, product signature or external witness',
                             'no Win74/JIT, all-origin capture, payload capture, production release or site change'])


def verify_archive_bytes(path, architecture):
    """Optional disk-byte rehash; the signed-release question remains separate."""
    pin = PINS[architecture]
    st = path.lstat()
    need(stat.S_ISREG(st.st_mode) and st.st_size == pin['archive_size'], 'wrong candidate archive file size/type')
    digest = hashlib.sha256()
    size = 0
    with path.open('rb') as stream:
        for part in iter(lambda: stream.read(2**20), b''):
            size += len(part)
            need(size <= pin['archive_size'], 'archive changed during read')
            digest.update(part)
    need(size == pin['archive_size'] and digest.hexdigest() == pin['archive'], 'wrong architecture or archive bytes')


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--bundle', type=Path, default=HERE / 'candidate-002-originals.zip')
    p.add_argument('--controls', type=Path, default=HERE / 'controls')
    p.add_argument('--archive-arm64', type=Path, help='optional separately retained archive for local hash check')
    p.add_argument('--archive-amd64', type=Path, help='optional separately retained archive for local hash check')
    args = p.parse_args()
    try:
        report = verify(read_evidence(args.bundle), args.controls)
        for architecture in PINS:
            path = getattr(args, f'archive_{architecture}')
            if path is not None:
                verify_archive_bytes(path, architecture)
            report['images'][architecture]['local_archive_rehashed'] = path is not None
    except (OSError, KeyError, IndexError, TypeError, ValueError, tarfile.TarError, zipfile.BadZipFile) as exc:
        print(json.dumps({'status': 'evidence_rejected', 'product_qualified': False, 'reason': str(exc)}))
        return 1
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
