#!/usr/bin/env python3
"""Bounded offline review of candidate D Electron-owner evidence; never signs a product."""

import argparse
import hashlib
import json
from pathlib import Path
import re
import stat

HERE = Path(__file__).resolve().parent
SOURCE = '724ef8e147dc1c688601346cb4d25cb3f26a8942'
APP = 'f7914d94b77947000e176771d934a28ae2f381c3df3944d5a5de78167e331481'
MCP = 'b5e204a76dc3974abadf1fe355392815ddddd6b7'
LAUNCHER = '85888811c637a43850246bbc4ac452c1054920863d200d649bda26fd8110223e'
BASE = 'e35e7278a49d4e67c9ad9e480308bf5e11273493'
DESIGN_CRITERIA = '9a3cffd1a51e5423fab047e12f8b5c25eb2a61e76e5543eb0c739db75216871a'
INDEX_SHA = '5fe4cbf294b5503ed03bd841f18e63fd0002577ecedb9571c41d7c989b341ea0'
INTAKE = '26ee1a2520b787ab21a979931715cfd82539e3e3204687a07705e2745e7d02dd'
SUMS = 'aa7037599cd395082f3859883c5c474604d0a828c7b2176de16c763651f59e83'
ARCHIVES = {
    'arm64': (235142912, '727c9d600721aba58a562b9a8ba55dc303aeb067b70982ec2344e9542aa1db76'),
    'amd64': (239522229, '791e4b0c2fe8b0fa08478b610e8503d0a5fae1a188d494eca44282a864c22829'),
}
BUNDLES = {
    'amd64': ('x64', 'e35f4f879a1fe08125bcc9af68daf10a4a11a3cc805daca064c4feff8a6f495c',
              'sha256:eb73d165ea9adc15864aeb054bc90a78670618c5c0606827997d357f1cae05c6'),
    'arm64': ('arm64', '7cf94a281832de9331cb03d22210993b34f5e1d32d1a47859c434594ba89c131',
              'sha256:9073c375ff26a8248e055e54f1ca28f289d92fc7f253d36685973fa8ecdd33bc'),
}
MARKERS = {
    'borrow_return_reborrow': ['electron-owner-click-1', 'electron-owner-click-2'],
    'exclusive_and_stale': ['electron-owner-click-1'],
    'paused_owner_stop': ['electron-owner-pause-pending', 'electron-owner-resumed'],
    'borrower_lost': [],
    'browser_lost': [],
}
LEASES = {
    'borrow_return_reborrow': (2, 2, 0, 0), 'exclusive_and_stale': (1, 1, 0, 0),
    'paused_owner_stop': (1, 0, 0, 1), 'borrower_lost': (2, 1, 1, 0), 'browser_lost': (1, 0, 0, 0),
}
LEASE_FIELDS = ('leasesAcquired', 'leasesReleased', 'leasesExpired', 'leasesRevoked')
INPUTS = {
    'console/cli/owner.mjs': 'src/cli/owner.mjs',
    'console/main/main.js': 'src/main/main.js',
    'console/main/native-owner-install.cjs': 'src/main/native-owner-install.cjs',
    'console/main/native-owner.mjs': 'src/main/native-owner.mjs',
    'console/tooling/assemble-linux.py': None,
    'console/tooling/build-linux.mjs': None,
    'product/desktop-seat/fixture.mjs': None,
    'product/desktop-seat/index.html': 'src/desktop-seat/index.html',
    'product/desktop-seat/preload.cjs': 'src/desktop-seat/preload.cjs',
    'product/desktop-seat/seat-main.cjs': 'src/desktop-seat/seat-main.cjs',
    'product/desktop-seat/seat.css': 'src/desktop-seat/seat.css',
    'product/desktop-seat/stage-assets.mjs': None,
}
# The committed change includes twelve product inputs and two test files.
# The build also consumes package-lock.json; record it separately as input 13.
INPUTS['console/tooling/package-lock.json'] = None


def need(ok, reason):
    if not ok:
        raise ValueError(reason)


def sha(b):
    return hashlib.sha256(b).hexdigest()


def wire(value):
    return (json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False) + '\n').encode('ascii')


def eq(value, expected, reason):
    need(wire(value) == wire(expected), reason)


def digest(value):
    need(type(value) is str and re.fullmatch(r'[0-9a-f]{64}', value), 'malformed evidence digest')
    return value


def pairs(items):
    d = dict(items)
    need(len(d) == len(items), 'duplicate JSON field')
    return d


def obj(data):
    value = json.loads(data, object_pairs_hook=pairs)
    need(type(value) is dict, 'object evidence required')
    return value


def read(path, limit=2**20):
    st = path.lstat()
    need(path == path.resolve(strict=True) and stat.S_ISREG(st.st_mode) and st.st_nlink == 1
         and 0 < st.st_size <= limit, f'nonregular, unsafe or oversized file: {path.name}')
    raw = path.read_bytes()
    need(len(raw) == st.st_size, 'evidence file changed while reading')
    return raw


def source_custody(root):
    app_raw = read(root / 'custody' / 'build-receipt.json')
    need(sha(app_raw) == APP and read(root / 'custody' / 'repeat-build-receipt.json') == app_raw,
         'candidate D app or repeat byte mismatch')
    app = obj(app_raw)
    eq([app[k] for k in ('format', 'source_revision', 'console_inputs_dirty', 'electron_native_owner',
                         'electron_native_seat', 'mcp_live_cli', 'electron_bundled', 'kernel_bundled')],
       [2, SOURCE, False, True, True, True, False, False], 'not detached clean D app')
    raw_provenance = read(root / 'custody' / 'source-inputs.json')
    provenance = obj(raw_provenance)
    need(provenance['source'] == SOURCE and provenance['app_receipt_sha256'] == APP,
         'wrong 13-input source custody')
    inputs = provenance['source_inputs']
    need(set(inputs) == set(INPUTS), 'missing or additional product inputs')
    for name, installed in INPUTS.items():
        need(inputs[name]['installed_path'] == installed, 'wrong app input locus')
        h = digest(inputs[name]['sha256'])
        if installed:
            need(app['files'][installed]['sha256'] == h, 'compiled app changed copied source')
    need(inputs['console/tooling/package-lock.json']['sha256'] == app['dependency_lock_sha256'], 'different build dependency lock')
    tree = sha(wire(app['files']))
    need(provenance['app_inventory_sha256'] == provenance['repeat_inventory_sha256'] == tree
         and provenance['installed_file_count'] == len(app['files']) == 91, 'independent app tree hashes disagree')
    proofs = {}
    for a, (_, expected_sha, r5) in BUNDLES.items():
        b = read(root / 'custody' / f'{a}-bundle-receipt.json')
        need(sha(b) == expected_sha, 'wrong architecture or different bundle receipt bytes')
        p = obj(b)
        eq([p[k] for k in ('arch', 'kind', 'source_revision', 'source_has_local_patch', 'source_baseline',
                           'app_receipt_sha256', 'launcher_sha256', 'mcp_source', 'electron_version', 'cli_product_image_id')],
           [a, 'ruyitrace-local-native-qa-candidate', SOURCE, False, BASE, APP, LAUNCHER, MCP, '45.4.1', r5],
           'wrong installed Electron package or historical C evidence')
        for k in ('electron_sha256', 'chrome_sandbox_sha256', 'runtime_receipt_sha256', 'acceptance_sha256',
                  'mcp_entry_sha256', 'mcp_lock_sha256'):
            digest(p[k])
        for k in ('firefox', 'libxul.so', 'browser/omni.ja', 'omni.ja'):
            digest(p['kernel_files'][k]['sha256'])
            need(type(p['kernel_files'][k]['size']) is int and p['kernel_files'][k]['size'] > 0, 'empty kernel artifact')
        proofs[a] = p
    return proofs


def require_subset(actual, expected, reason):
    need(type(actual) is dict and set(expected) <= set(actual), reason)
    eq({k: actual[k] for k in expected}, expected, reason)


def validate_run(run, a, case, proof, criteria):
    eq([run[k] for k in ('schema', 'arch', 'case', 'backend', 'passed')],
       ['ruyitrace-electron-owner-native-qa.v1', BUNDLES[a][0], case,
        'wayland' if case == 'paused_owner_stop' else 'x11', True], 'wrong architecture/case, not genuine backend, or failed attempt')
    need('failure' not in run, 'failed attempt mixed with a successful row')
    eq(run['artifact'], dict(installReceiptSha256=BUNDLES[a][1], electronSha256=proof['electron_sha256'],
                             launcherSha256=LAUNCHER, appBuildSha256=APP, traceSource=SOURCE, mcpPin=MCP,
                             runtimeReceiptSha256=proof['runtime_receipt_sha256'], acceptanceSha256=proof['acceptance_sha256']),
       'wrong architecture, historical C, or mixed product/mcp bytes')
    for role, expected in criteria.items():
        require_subset(run[role], expected, f'preregistered {role} witness differs')
    require_subset(run['main'], dict(owner_kind='electron-main', descriptor_issued=True), 'installed owner identity')
    require_subset(run['process'], dict(firefox_instances=1, same_process_start=True, interfaces=['lo'],
        renderer_seccomp=2, renderer_no_new_privs=1, owned_children_remaining=0, bidi_sessions=1),
        'single owned native Firefox/BiDi, renderer sandbox, or process cleanup differs')
    if case == 'exclusive_and_stale':
        require_subset(run['client'], dict(expired_admin_denied=True, unsafe_admin_denied=True,
                                          unauthenticated_control_denied=True), 'additional negative controls lack denial')
    lost = case == 'browser_lost'
    final = run['witness']['finalResult']
    digest(final['sha256'])
    eq(final['nativeOwner'], dict(kind='electron-main', descriptorRevoked=True, resumedBeforeGateClose=not lost,
        flushAcknowledged=not lost, disposition='unclean' if lost else 'clean', browserLost=lost), 'invalid clean/unclean disposition')
    eq(final['browserExit'], dict(code=None, signal='SIGKILL' if lost else 'SIGTERM'), 'browser exit status differs')
    require_subset(final['bidi'], dict(sessionNew=1, sessionEnd=0 if lost else 1, sessionEndAcknowledged=not lost),
                   'wrong number of BiDi sessions or release acknowledgement')
    need(type(final['bidi']['getTree']) is int and final['bidi']['getTree'] > 0, 'missing live BiDi readback')
    eq(final['completion'], 'browser-exit' if lost else 'requested-stop', 'wrong state exit path')
    eq(final['gateConfirmation'], 'awaiting-session-stopped' if lost else 'session-stopped', 'unexpected native gate tail claim')
    eq(final['leases'], dict(zip(LEASE_FIELDS, LEASES[case])), 'wrong lease release, expiry or revocation counts')
    writers = run['witness']['writers']
    need(type(writers) is list and (not writers if lost else 1 <= len(writers) <= 4), 'missing original closed writer witness')
    for wr in writers:
        require_subset(wr, {'session': 1, 'opened': 0}, 'unexpected native writer session/head')
        need(type(wr['closed']) is int and 0 < wr['closed'] == wr['sessionRows'] - 1 and
             type(wr['byteLength']) is int and 0 < wr['byteLength'] <= 2**20, 'unsealed or clipped writer witness')
        digest(wr['fileSha256'])
        effects = wr['effects']
        indices = [r['index'] for r in effects]
        need(all(type(i) is int and wr['opened'] < i < wr['closed'] for i in indices) and
             indices == sorted(set(indices)), 'page effect unordered or outside native writer edges')
        need(len({r['context_sha256'] for r in effects}) <= 1, 'page effects across different browsing contexts')
        for effect in effects:
            digest(effect['context_sha256'])
            eq(set_as_list(effect), ['context_sha256', 'index', 'kind', 'value'], 'unexpected page-witness fields')
            eq(effect['kind'], 'Document.title', 'unexpected effect type')
        eq([r['value'] for r in effects], MARKERS[case], 'exact authorized page effects differ')
    if case == 'paused_owner_stop':
        rdp = run['witness']['rdp']
        require_subset(rdp, dict(source='pinned-mcp-native-rdp', reason='breakpoint', line=5,
                                 fixturePath='/electron-owner.js', watchdogSeconds=30), 'real RDP pause absent')
        need(type(rdp['ownerStopElapsedMs']) is int and 0 < rdp['ownerStopElapsedMs'] < 25000,
             'owner stop failed to beat independent watchdog window')
    else:
        need('rdp' not in run['witness'], 'foreign RDP witness in trial')


def set_as_list(o):
    return sorted(o)


def anon(a, kind, fields):
    return sha(wire([f'linux/{a}', kind, fields]))


def anonymize(a, raw):
    """Omit namespace PID/ticks and context IDs; strong hashes label joins, not external identity."""
    run = obj(raw)
    process = run['process']
    for pid in ('electronPid', 'firefoxPid', 'renderer_pid'):
        need(type(process[pid]) is int and process[pid] > 1, 'missing isolated process identity')
    need(len({process[k] for k in ('electronPid', 'firefoxPid', 'renderer_pid')}) == 3, 'reused process roles')
    for start in ('electronStart', 'firefoxStart'):
        need(type(process[start]) is str and re.fullmatch(r'[1-9][0-9]{0,19}', process[start]), 'wrong process start identity')
    need(int(process['electronStart']) <= int(process['firefoxStart']), 'Firefox predates its owner')
    process['electron_instance_sha256'] = anon(a, 'electron', [process.pop('electronPid'), process.pop('electronStart')])
    process['firefox_instance_sha256'] = anon(a, 'firefox', [process.pop('firefoxPid'), process.pop('firefoxStart')])
    process.pop('renderer_pid')
    for wr in run['witness']['writers']:
        need(type(wr['pid']) is int and wr['pid'] > 1 and type(wr['generation']) is str and
             re.fullmatch(r'[1-9][0-9]{0,19}', wr['generation']), 'missing isolated native writer identity')
        wr['writer_instance_sha256'] = anon(a, 'writer', [wr.pop('pid'), wr.pop('generation')])
        for eff in wr['effects']:
            need(type(eff['contextId']) is int and eff['contextId'] > 0, 'missing isolated browsing context')
            eff['context_sha256'] = anon(a, 'context', [eff.pop('contextId')])
    for key in ('borrowerLoss', 'browserLoss'):
        if key in run['witness']:
            loss = run['witness'][key]
            pid, start = loss.pop('pid'), loss.pop('startTime')
            need(type(pid) is int and pid > 1 and type(start) is str and start.isdecimal(), 'invalid killed process identity')
            loss['instance_sha256'] = anon(a, 'firefox' if key == 'browserLoss' else 'borrower', [pid, start])
    return dict(schema='ruyitrace.electron-owner-qa-scrubbed.v1', original_sha256=sha(raw), run=run)


def verify_chronology(run, case):
    w = run['witness']
    calls, admin = w['mcpCalls'], w['adminControls']
    for sequence in (calls, admin):
        need(type(sequence) is list and len(sequence) <= 30 and
             all(type(r[k]) is int for r in sequence for k in ('startMs', 'endMs')) and
             all(0 <= r['startMs'] <= r['endMs'] < 300000 for r in sequence) and
             all(x['endMs'] <= y['startMs'] for x, y in zip(sequence, sequence[1:])), 'nonmonotonic QA chronology')
    def rpc(n, tool, action=None, outcome='ok', seen=None):
        return n, 'ruyi_' + tool, action, outcome, seen
    def attach(n):
        return rpc(n, 'attach_trace_session', seen=attached)
    def query(n, count):
        return rpc(n, 'trace_control', 'query', seen={'elementCount': 1, 'fixtureText': f'Click count {count}'})
    def click(n):
        return rpc(n, 'trace_control', 'click')
    def quit_(n):
        return rpc(n, 'browser_quit', seen={'quit': True})
    attached = dict(alive=True, borrowed=True, pageCount=1)
    expected = [attach(1), query(1, 0)]
    if case == 'borrow_return_reborrow':
        expected += [click(1), query(1, 1), quit_(1), attach(2), query(2, 1), click(2), query(2, 2), quit_(2)]
    elif case == 'exclusive_and_stale':
        expected += [rpc(2, 'attach_trace_session', outcome='lease-busy'), rpc(2, 'trace_control', 'click', 'denied'),
                     query(1, 0), rpc(1, 'browser_status', seen=attached), click(1), query(1, 1), quit_(1)]
    elif case == 'paused_owner_stop':
        expected += [rpc(1, 'debug_enable', seen={'started': True}), rpc(1, 'debug_list_sources'),
                     rpc(1, 'debug_set_breakpoint', seen={'line': 5}), click(1),
                     rpc(1, 'debug_wait_paused', seen={'paused': True}), rpc(1, 'trace_control', 'query', 'denied')]
    elif case == 'borrower_lost':
        expected += [rpc(2, 'attach_trace_session', outcome='lease-busy'), attach(2), query(2, 0), quit_(2)]
    else:
        expected += [rpc(1, 'trace_control', 'query', 'denied')]
    eq([(x['borrower'], x['tool'], x.get('action'), x['outcome'], x.get('observed')) for x in calls], expected,
       'scoped MCP operations, denials or actual page effects differ')
    eq([(r['kind'], r['ok'], r['stopped'], r.get('code')) for r in admin],
       ([('stale-stop', False, False, 3), ('expired-stop', False, False, 5), ('unsafe-mode-stop', False, False, 3)]
        if case == 'exclusive_and_stale' else []) +
       ([] if case == 'browser_lost' else [('current-stop', True, True, None)]), 'scoped admin stop history differs')
    if case == 'exclusive_and_stale':
        need(calls[3]['endMs'] <= admin[0]['startMs'] <= admin[2]['endMs'] <= calls[4]['startMs'],
             'negative controls were outside the checked zero-effect window')
    if case == 'paused_owner_stop':
        rdp = w['rdp']
        need(calls[-2]['endMs'] <= rdp['pauseAckMs'] <= admin[-1]['startMs'] <= admin[-1]['endMs'] <= calls[-1]['startMs'] and
             abs(admin[-1]['endMs'] - rdp['pauseAckMs'] - rdp['ownerStopElapsedMs']) <= 5,
             'pause acknowledgement, owner stop and detached borrower order differs')
        return dict(pause_to_stop_ms=rdp['ownerStopElapsedMs'])
    if case == 'borrower_lost':
        loss = w['borrowerLoss']
        digest(loss['instance_sha256'])
        eq([loss['signal'], loss['productionLeaseSeconds']], ['SIGKILL', 120], 'wrong borrower-kill case or shortened lease')
        need(calls[1]['endMs'] <= loss['sentMs'] <= loss['exitObservedMs'] <= calls[2]['startMs'] and
             calls[3]['startMs'] - calls[2]['endMs'] >= 120000 and loss['reborrowAckMs'] == calls[3]['endMs'],
             'borrower reattached before the production expiry window')
        return dict(borrower_exit_to_reborrow_ms=loss['reborrowAckMs'] - loss['exitObservedMs'])
    if case == 'browser_lost':
        loss = w['browserLoss']
        eq([loss['signal'], loss['instance_sha256']], ['SIGKILL', run['process']['firefox_instance_sha256']],
           'browser loss targeted a different instance')
        need(calls[1]['endMs'] <= loss['sentMs'] <= loss['revocationObservedMs'] <= calls[-1]['startMs'],
             'browser kill, descriptor revocation and stale denial order differs')
        return dict(browser_kill_to_revocation_ms=loss['revocationObservedMs'] - loss['sentMs'])
    return {}


def scrub_readback(a, raw, receipt):
    """Create a bounded projection after joining original readback to its exact run."""
    p, run = obj(raw), obj(receipt)
    result, state = p['result'], p['state']
    need(p['schema'] == 'ruyitrace-electron-owner-originals-projection.v1' and
         p['arch'] == run['arch'] and p['case'] == run['case'], 'wrong original readback lane/case')
    out = p['guest_output']
    need(re.fullmatch(r'/(?:root|home/ubuntu)/ruyitrace-gap-electron-v1/output-(?:x11|wayland)\.[A-Za-z0-9]+', out),
         'unexpected local run root')
    prefix = result.pop('path').removesuffix('/result.json')
    need(re.fullmatch(re.escape(out) + r'/admin-[A-Za-z0-9]+/run', prefix) and
         state.pop('path') == prefix + '/state.json', 'mixed original result/state paths')
    eq(state.pop('owner'), dict(pid=run['process']['electronPid'], startTime=run['process']['electronStart']), 'original owner instance differs')
    eq(state.pop('browser'), dict(pid=run['process']['firefoxPid'], startTime=run['process']['firefoxStart']), 'original Firefox instance differs')
    writers = []
    for item in p['writers']:
        path = item.pop('path')
        m = re.fullmatch(re.escape(prefix) + r'/domtrace/trace_process_([1-9][0-9]*)\.jsonl', path)
        need(m is not None, 'writer is outside exact run')
        pid = int(m[1])
        matching = [row for row in run['witness']['writers'] if row['pid'] == pid]
        need(len(matching) <= 1, 'duplicate writer identity')
        if matching:
            item['writer_instance_sha256'] = anon(a, 'writer', [pid, matching[0]['generation']])
        for selected in item.get('selected_rows', []):
            if 'pid' in selected:
                eq(selected.pop('pid'), pid, 'native edge belongs to another writer')
            if 'context_id' in selected:
                selected['context_sha256'] = anon(a, 'context', [selected.pop('context_id')])
        writers.append(item)
    projected = anonymize(a, receipt)['run']['process']
    state.update(electron_instance_sha256=projected['electron_instance_sha256'],
                 firefox_instance_sha256=projected['firefox_instance_sha256'])
    return dict(schema='ruyitrace.electron-owner-readback-scrubbed.v1', original_projection_sha256=sha(raw),
                run_root_sha256=anon(a, 'run-root', [out]), result=result, state=state, writers=writers)


def validate_readback(run, projection, case):
    eq(projection['schema'], 'ruyitrace.electron-owner-readback-scrubbed.v1', 'wrong original projection schema')
    lost = case == 'browser_lost'
    actual, state = projection['result'], projection['state']
    mcp, expected = actual['mcp'], run['witness']['finalResult']
    digest(state['sha256'])
    eq(state, dict(sha256=state['sha256'], owner_kind='electron-main', phase='failed' if lost else 'exited',
         electron_instance_sha256=run['process']['electron_instance_sha256'],
         firefox_instance_sha256=run['process']['firefox_instance_sha256']), 'readback state/owner/Firefox identity differs')
    eq([actual['sha256'], actual['exit'], actual['browser'], actual['completion'], actual['native_owner'], actual['gate'],
        mcp['bidi'], {k: mcp[k] for k in LEASE_FIELDS}],
       [expected['sha256'], 137 if lost else 0, expected['browserExit'], expected['completion'], expected['nativeOwner'],
        {'observed': 'unacknowledged' if lost else 'closed', 'confirmation': expected['gateConfirmation']},
        expected['bidi'], expected['leases']], 'original product result differs or claims an unsupported clean flush')
    eq(mcp['drainVerified'], not lost, 'original product drain status differs')
    if case == 'paused_owner_stop':
        need(type(mcp['debuggerPauseNotices']) is int and mcp['debuggerPauseNotices'] > 0 and mcp['debuggerObserved'] is True,
             'original product missed paused debugger drain')
    raw_writers = projection['writers']
    expected_writers = run['witness']['writers']
    if lost:
        need(all('selected_rows' not in w for w in raw_writers), 'kill trace falsely qualified as a sealed writer')
    else:
        need(len(raw_writers) == len(expected_writers), 'unexpected extra or missing clean writer originals')
    for raw in raw_writers:
        digest(raw['sha256'])
        need(type(raw['bytes']) is int and 0 < raw['bytes'] <= 2**20, 'invalid writer original byte length')
    for wr in expected_writers:
        matches = [w for w in raw_writers if w.get('writer_instance_sha256') == wr['writer_instance_sha256']]
        need(len(matches) == 1, 'original writer instance is missing or duplicated')
        w = matches[0]
        eq([w['sha256'], w['bytes'], w['complete_tail']], [wr['fileSha256'], wr['byteLength'], True],
           'original writer bytes, count or complete tail differ')
        rows = w['selected_rows']
        unique = {digest(row['row_sha256']) for row in rows}
        need(len(unique) == len(rows), 'duplicate selected raw line digest')
        eq([{k: v for k, v in r.items() if k != 'row_sha256'} for r in rows],
           [dict(line=wr['opened'] + 1, type='session_started', session=wr['session']),
            *(dict(line=r['index'] + 1, type='Document.title:set', session=wr['session'],
                   context_sha256=r['context_sha256'], value=r['value']) for r in wr['effects']),
            dict(line=wr['closed'] + 1, type='session_stopped', session=wr['session'])],
           'original trace edge or fixture action order differs')
    return dict(result_sha256=actual['sha256'], state_sha256=state['sha256'],
                native_writer_sha256=[w['sha256'] for w in raw_writers],
                state='unclean_reported' if lost else 'ordered_close_read_back')


def validate_retained(a, case, orig, raw_root):
    """Rehash exact retained final result and native writer bytes, never copy raw values into output."""
    run = obj(orig)
    result_raw = read(raw_root / 'result.json')
    expected = run['witness']['finalResult']
    need(sha(result_raw) == expected['sha256'], 'wrong retained original final result bytes')
    result = obj(result_raw)
    lost = case == 'browser_lost'
    eq([result['schema'], result['passed']], [2, not lost], 'retained product result completion differs')
    need(type(result['exit']) is int and (result['exit'] != 0 if lost else result['exit'] == 0), 'retained product result exit differs')
    r_mcp, r_gate = result['mcp'], result['gate']
    eq([result['completion'], result['nativeOwner'], result['browser'], r_mcp['bidi'], r_gate['confirmation'],
        {k: r_mcp[k] for k in LEASE_FIELDS}], [expected['completion'], expected['nativeOwner'], expected['browserExit'],
        expected['bidi'], expected['gateConfirmation'], expected['leases']], 'retained product result differs from witness')
    if lost:
        need(result['nativeOwner']['flushAcknowledged'] is False, 'SIGKILL cannot claim clean flush')
        return dict(result_sha256=sha(result_raw), native_writer_sha256=[], state='unclean_reported')
    eq(r_gate['observed'], 'closed', 'unclosed retained product gate')
    writers = run['witness']['writers']
    eq(sorted((w['pid'], w['startTime'], w['session']) for w in r_gate['writers']),
       sorted((w['pid'], w['generation'], w['session']) for w in writers), 'wrong retained product writer identity')
    if case == 'paused_owner_stop':
        need(type(r_mcp['debuggerPauseNotices']) is int and r_mcp['debuggerPauseNotices'] > 0 and
             r_mcp['drainVerified'] is True, 'retained product result lacks debugger drain')
    linked = []
    for wr in writers:
        b = read(raw_root / 'domtrace' / f'trace_process_{wr["pid"]}.jsonl')
        need(sha(b) == wr['fileSha256'] and len(b) == wr['byteLength'] and b.endswith(b'\n'), 'wrong retained native writer bytes or missing tail')
        lines = [obj(line) for line in b.splitlines()]
        rows = [row for row in lines if row.get('session') == wr['session']]
        need(wr['sessionRows'] == len(rows) and rows[wr['opened']].get('type') == 'session_started' and
             rows[wr['closed']].get('type') == 'session_stopped' and
             rows[wr['opened']]['pid'] == rows[wr['closed']]['pid'] == wr['pid'] and
             sum(row.get('type') == 'session_stopped' for row in rows) == 1 and
             not any(r.get('type') in {'get', 'set', 'call'} for r in rows[wr['closed'] + 1:]),
             'retained writer lacks matching complete opening/close or has post-close data')
        significant = []
        marks = set(MARKERS['paused_owner_stop'] + MARKERS['borrow_return_reborrow'])
        for i, row in enumerate(rows):
            if (row.get('type'), row.get('interface'), row.get('member')) != ('set', 'Document', 'title'):
                continue
            value = row.get('value')
            if value in marks or isinstance(value, str) and re.fullmatch(r'electron-owner-click-[0-9]+', value):
                need(isinstance(row.get('ctx_origin'), str) and re.fullmatch(r'http://127\.0\.0\.1:[1-9][0-9]{3,4}', row['ctx_origin'])
                     and row.get('ctx') == 'top', 'unexpected original effect origin/context')
                significant.append(dict(index=i, kind='Document.title', value=value, contextId=row['ctx_id']))
        eq(significant, wr['effects'], 'original native writer effects or unauthorized click count differs')
        linked.append(sha(b))
    return dict(result_sha256=sha(result_raw), native_writer_sha256=linked, state='ordered_close_read_back')


def verify(root, original_runs=None, raw_runs=None):
    index_raw = read(root / 'evidence-index.json')
    need(sha(index_raw) == INDEX_SHA, 'wrong fixed Electron evidence index')
    index = obj(index_raw)
    fixed = ['custody/criteria.json', 'custody/source-inputs.json', 'custody/build-receipt.json',
             'custody/repeat-build-receipt.json', 'custody/contract.json', 'custody/SHA256SUMS',
             *(f'custody/{a}-{f}.json' for a in BUNDLES for f in ('bundle-receipt', 'archive-proof')),
             *(f'runs/{a}-{c}.json' for a in BUNDLES for c in MARKERS),
             *(f'readback/{a}-{c}.json' for a in BUNDLES for c in MARKERS)]
    eq(sorted(index), sorted(fixed), 'missing/additional evidence index members')
    for name in fixed:
        need(sha(read(root / name)) == index[name], 'Electron evidence changed after freeze')
    criteria_raw = read(root / 'custody' / 'criteria.json')
    need(sha(criteria_raw) == DESIGN_CRITERIA, 'wrong preregistered Electron acceptance')
    criteria = obj(criteria_raw)['gates']['electron_owner']['cases']
    eq(sorted(criteria), sorted(MARKERS), 'wrong exact five-case registration')
    proofs = source_custody(root)
    intake_raw = read(root / 'custody' / 'contract.json')
    sums_raw = read(root / 'custody' / 'SHA256SUMS')
    need(sha(intake_raw) == INTAKE and sha(sums_raw) == SUMS, 'wrong final D structural intake or original hash manifest')
    intake = obj(intake_raw)
    eq([intake['source'], intake['app_receipt_sha256'], intake['criteria_sha256'], intake['review_state']],
       [SOURCE, APP, DESIGN_CRITERIA, 'eligible_for_manual_review'], 'intake granted excess product credit')
    sums = pairs([(line.split('  ')[1].removeprefix('./'), digest(line.split('  ')[0]))
                  for line in sums_raw.decode('ascii').splitlines()])
    eq(sorted(sums), sorted(['contract.json', *(f'{p}{a}-{c}.json' for a in BUNDLES for c in MARKERS
                                               for p in ('', 'originals/'))]), 'wrong final D manifest members')
    eq(sums['contract.json'], INTAKE, 'contract manifest mismatch')
    need(raw_runs is None or original_runs is not None, 'raw retained evidence requires exact original QA receipts too')
    all_ids = set()
    results = {}
    for a in BUNDLES:
        reviewed = {}
        size, archive_sha = ARCHIVES[a]
        archive = obj(read(root / 'custody' / f'{a}-archive-proof.json'))
        eq(archive, dict(architecture=a, path=f'ruyitrace-linux-{a}-electron-owner-724ef8e.tar.gz',
                         archive_bytes=size, archive_sha256=archive_sha, source=SOURCE, bundle_receipt_sha256=BUNDLES[a][1],
                         native_export_checksum_readback=True), 'wrong final D package hash/readback')
        arch_intake = intake['architectures'][a]
        eq([arch_intake['bundle_receipt_sha256'], sorted(arch_intake['cases'])], [BUNDLES[a][1], sorted(MARKERS)],
           'wrong architecture or case set in final intake')
        for c in MARKERS:
            try:
                name = f'{a}-{c}.json'
                projected = obj(read(root / 'runs' / name))
                readback = obj(read(root / 'readback' / name))
                eq(projected['schema'], 'ruyitrace.electron-owner-qa-scrubbed.v1', 'wrong bounded receipt schema')
                run = projected['run']
                eq(arch_intake['cases'][c], dict(file=name, sha256=sums[name], backend=run['backend']), 'wrong per-case intake provenance')
                eq([projected['original_sha256'], readback['original_projection_sha256']],
                   [sums[name], sums[f'originals/{name}']], 'original receipt or readback projection SHA differs')
                validate_run(run, a, c, proofs[a], criteria[c])
                ordering = verify_chronology(run, c)
                retained = validate_readback(run, readback, c)
                for identity in (projected['original_sha256'], retained['result_sha256'], retained['state_sha256'],
                                 readback['original_projection_sha256'], readback['run_root_sha256'],
                                 run['process']['electron_instance_sha256'], run['process']['firefox_instance_sha256'],
                                 *retained['native_writer_sha256'], *(w['writer_instance_sha256'] for w in run['witness']['writers'])):
                    digest(identity)
                    need(identity not in all_ids, 'duplicated process, writer or original proof')
                    all_ids.add(identity)
                if original_runs is not None:
                    original = read(original_runs / name)
                    eq(anonymize(a, original), projected, 'projected receipt differs from unchanged original')
                    eq(scrub_readback(a, read(original_runs / 'originals' / name), original), readback,
                       'scrubbed readback differs from source projection')
                if raw_runs is not None:
                    direct = validate_retained(a, c, original, raw_runs / name[:-5])
                    need(direct['result_sha256'] == retained['result_sha256'] and direct['state'] == retained['state'],
                         'raw retained bytes disagree with native projection')
                reviewed[c] = dict(status='observed_in_final_d', backend=run['backend'],
                    original_qa_receipt_sha256=projected['original_sha256'], native_readback=retained, **ordering)
            except (OSError, ValueError, KeyError, IndexError, TypeError) as exc:
                raise ValueError(f'linux/{a} {c}: {exc}') from exc
        results[f'linux/{a}/installed-electron-main-single-firefox-bidi'] = dict(cases=reviewed,
            bundle_receipt_sha256=BUNDLES[a][1], archive_sha256=archive_sha, archive_bytes=size,
            scope='isolated local Xvfb or Weston-headless with sandboxed renderer')
    return dict(schema='ruyitrace.platform-electron-owner-d-review.v1', evidence_sha256=INDEX_SHA,
        source=SOURCE, app_receipt_sha256=APP, product_qualified=False, human_signoff=False, verified_qa_receipts=10,
        native_originals_sha_linked_by_read_only_readback=10, local_binary_archive_rehashed=False,
        local_raw_result_trace_rehashed=raw_runs is not None,
        status='bounded_electron_owner_d_evidence_verified_pending_strict_external_review',
        external_independence=['no live process or physical panel attestation',
            'OS hierarchy, observed MCP outcomes and RDP pause are QA witnesses; original native result/state/writer hashes from separate retained readback',
            'headful isolated X11/Wayland is owner evidence, not physical display or IME qualification',
            'no release, product signing or global closure credit'], cells=results)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--evidence', type=Path, default=HERE)
    p.add_argument('--original-runs', type=Path)
    p.add_argument('--raw-runs', type=Path)
    a = p.parse_args()
    try:
        report = verify(a.evidence.resolve(), a.original_runs and a.original_runs.resolve(),
                        a.raw_runs and a.raw_runs.resolve())
    except (OSError, ValueError, KeyError, IndexError, TypeError) as exc:
        print(json.dumps(dict(status='evidence_rejected', product_qualified=False, reason=str(exc))))
        return 1
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
