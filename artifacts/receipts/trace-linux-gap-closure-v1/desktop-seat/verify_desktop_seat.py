#!/usr/bin/env python3
"""Offline replay of the frozen, non-qualifying clean D desktop-seat evidence."""

import argparse
import hashlib
import json
from pathlib import Path
import re
import stat

HERE = Path(__file__).resolve().parent
SOURCE = '724ef8e147dc1c688601346cb4d25cb3f26a8942'
APP = 'f7914d94b77947000e176771d934a28ae2f381c3df3944d5a5de78167e331481'
TAG = 'linux-electron-owner-v0.1.0-alpha.1'
RELEASE = f'https://github.com/Facetomyself/ruyitrace/releases/tag/{TAG}'
DOWNLOADS = f'https://github.com/Facetomyself/ruyitrace/releases/download/{TAG}'
INDEX = 'bca250f5ea50ffbecc6cfd4529d42128fef3b2c88cfbd628cfa201e2125f669f'
ROUNDS = ('select_candidate', 'cancel', 'paste_control', 'focus_change')
ARCH = {
    'arm64': {'uname': 'aarch64', 'bundle': '7cf94a281832de9331cb03d22210993b34f5e1d32d1a47859c434594ba89c131',
              'callbacks': 164, 'outside': 11, 'archive': '727c9d600721aba58a562b9a8ba55dc303aeb067b70982ec2344e9542aa1db76',
              'bytes': 235142912, 'xvfb': 'arm64-clean-electron-xvfb.txt'},
    'amd64': {'uname': 'x86_64', 'bundle': 'e35f4f879a1fe08125bcc9af68daf10a4a11a3cc805daca064c4feff8a6f495c',
              'callbacks': 144, 'outside': 7, 'archive': '791e4b0c2fe8b0fa08478b610e8503d0a5fae1a188d494eca44282a864c22829',
              'bytes': 239522229, 'xvfb': 'amd64-clean-electron-xvfb-retry.txt'},
}
KITS = {
    'seat/seat-operator-kit-v1.tar.gz': 'bd6ddaa4c2c0fcb0e80361db196aeb5a46588df1c4e0981b18132fbb603f0d8c',
    'seat-observer/seat-observer-kit-v2.tar.gz': '59ac75105b0ebe6db296f1223b09d5baa9621c6a58554fe02197f80be732e5e1',
    'seat-reconciliation/seat-technical-qa-kit-v1.tar.gz': '0650dd6d5f5ef22695c4c269a27c2d5f1cf03c524636a00670844633eae8488a',
}
A_B = ('arm64-diagnostic-only-event-types.json', 'arm64-diagnostic-only-plain-gtk-event-types.json')
PRESENT_FIXTURE = 'present-observer/arm64-native-fixture.json'
PRESENT_PRODUCT = 'present-observer/arm64-clean-d-xvfb.json'
V2_EARLIER = 'seat-observer/arm64-gtk-native-final-live.json'
ORIGINAL = (
    'desktop-alpha/github-release-proof.json', 'seat-reconciliation/RESULT.json', 'seat-reconciliation/REPORT.md',
    'seat-reconciliation/SHA256SUMS', *(f'seat-reconciliation/{a}-clean-D-fixture-selection.json' for a in ARCH),
    *(f'seat-reconciliation/{name}' for name in A_B),
    'present-observer/RESULT.json', 'present-observer/EVIDENCE.sha256', 'present-observer/arm64-clean-d-resize.json',
    'present-observer/arm64-release-pins.json', 'seat-observer/RESULT.json', 'seat-observer/SHA256SUMS',
)
SCRUB = (PRESENT_FIXTURE, PRESENT_PRODUCT, V2_EARLIER, *(f'seat/{p["xvfb"]}' for p in ARCH.values()))
COUNTS = ('starts', 'updates', 'ends', 'matching_composition_ends', 'paste_events', 'paste_inputs',
          'other_inputs', 'synthetic_events', 'delayed_matching_ends')
FLAGS = ('expected_equal', 'primary_empty', 'primary_focused', 'secondary_empty', 'second_focused', 'moved_while_composing')
GTK = ('commit', 'commit_equal', 'focus_in', 'focus_out', 'preedit_change', 'preedit_end', 'preedit_start', 'reset')
PANEL = ('focus_in', 'focus_out', 'preedit_updates', 'visible_lookup_updates')


def need(ok, text):
    if not ok:
        raise ValueError(text)


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def wire(obj):
    return (json.dumps(obj, sort_keys=True, separators=(',', ':'), ensure_ascii=True, allow_nan=False) + '\n').encode('ascii')


def eq(actual, expected, reason):
    need(wire(actual) == wire(expected), reason)


def strict_fields(items):
    d = dict(items)
    need(len(d) == len(items), 'duplicate JSON key or manifest name')
    return d


def load(raw):
    obj = json.loads(raw, object_pairs_hook=strict_fields)
    need(type(obj) is dict, 'JSON evidence must be an object')
    return obj


def read(path, cap=100_000):
    s = path.lstat()
    need(path.resolve(strict=True) == path and stat.S_ISREG(s.st_mode) and s.st_nlink == 1 and 0 < s.st_size <= cap,
         'unsafe, empty or oversized evidence input')
    raw = path.read_bytes()
    need(len(raw) == s.st_size, 'changed evidence during read')
    return raw


def digest(h):
    need(type(h) is str and re.fullmatch(r'[a-f0-9]{64}', h), 'invalid evidence digest')
    return h


def sums(raw):
    return strict_fields([(line.split('  ')[1], digest(line.split('  ')[0]))
                          for line in raw.decode('ascii').splitlines()])


def scrub(name, raw):
    if name.startswith('seat/'):
        rows = [load(line) for line in raw.splitlines() if line.startswith(b'{')]
        need(len(rows) == 3, 'missing Xvfb initial, shape or window receipt')
        plan, shape, rec = rows
        need(plan['mode'] == 'panel' and plan['challenges_written_to_private_plan_only'] is True and
             rec['run_id'] == plan['run_id'], 'Xvfb plan and observation identity differ')
        eq(shape, dict(observed_at=rec['observed_at'], physical_candidate=rec['physical_candidate'],
                       virtual_output=rec['virtual_output'], window_viewable=rec['viewable']), 'Xvfb observation conflicts')
        return {k: rec[k] for k in ('active_local_seat', 'arch', 'backend', 'electron_executable_matches', 'environment',
                                    'output', 'owner_verified', 'physical_candidate', 'release_receipt_sha256',
                                    'renderer_sandbox_verified', 'source', 'viewable', 'virtual_output',
                                    'window_on_selected_output', 'x_server', 'window_rect')} | {'same_run_plan': True}
    rec = load(raw)
    if name == V2_EARLIER:
        n, window, rows = rec['native'], rec['window'], rec['product_rounds']
        bound = (n['exact_electron_pid'] == window['window_pid'] and
                 n['process_start_ticks'] == window['process_start_ticks'] and n['run_id'] == window['run_id'] and
                 n['release_receipt_sha256'] == window['release_receipt_sha256'] and
                 all(r['pid'] == window['window_pid'] and r['run_id'] == window['run_id'] for r in rows))
        return {'identity_bound': bound, 'product_rounds': [r['round'] for r in rows],
                'native': {k: n[k] for k in ('environment', 'human_attestation_present', 'claim_awarded', 'standard_ibus_engine',
                                            'kernel_peer_to_private_engine_verified', 'native_gtk_callback_events',
                                            'native_gtk_callback_discarded', 'native_gtk_callback_sequence_gaps', 'overflow',
                                            'release_receipt_sha256')},
                'gtk_rounds': {k: {m: v['gtk_callbacks'][m] for m in GTK} for k, v in n['rounds'].items()}}
    armed, closed, events = (rec[k] for k in ('armed', 'closed', 'events'))
    for row in (armed, closed):
        need(type(row['mono_ns']) is int and row['mono_ns'] > 0, 'invalid Present observation clock')
    need(all(armed['mono_ns'] <= e['mono_ns'] <= closed['mono_ns'] for e in events), 'Present event outside measurement')
    clean = dict(schema=rec['schema'], duration_ns=closed['mono_ns'] - armed['mono_ns'],
                 edge_states=[armed['record'], closed['record']], present_version=armed['present_version'],
                 closed_event_count=closed['events'], geometry_restored=armed['window_rect'] == closed['window_rect'],
                 events=[{k: e[k] for k in ('kind', 'kind_name', 'mode', 'mode_name', 'record', 'serial',
                                            'window_update_indication')} for e in events], summary=rec['summary'])
    if name == PRESENT_FIXTURE:
        return clean | {k: rec[k] for k in ('separate_native_fixture', 'virtual_only', 'wrong_owner_rejected_before_arming',
                                           'requested_serials', 'peer_issued_notify_msc_not_renderer_proof')}
    d, p = rec['display'], rec['product_identity']
    bound = armed['xres_local_pid'] == p['pid'] and armed['server_pid'] == d['server_pid']
    return clean | {k: rec[k] for k in ('architecture', 'bundle_receipt_sha256', 'environment', 'period_complete',
                                       'release_tag', 'source_revision', 'input_sha256')} | {
        'window_and_server_identity_bound': bound, 'sandbox_verified': p['renderer_sandbox_verified'],
        'private_profile_verified': p['private_profile_verified'],
        'display': {k: d[k] for k in ('selected_connector_context', 'server', 'virtual_only')}}


def validate_publication(doc):
    eq([doc[k] for k in ('actual_shipped_source_sha', 'app_receipt_sha256', 'tag', 'release_url', 'private', 'prerelease', 'passed')],
       [SOURCE, APP, TAG, RELEASE, True, True, True], 'wrong sealed desktop release')
    eq(doc['bundle_receipt_sha256'], {a: p['bundle'] for a, p in ARCH.items()}, 'published release bundle mismatch')
    pins = {f'ruyitrace-linux-{a}-electron-owner-724ef8e.tar.gz': (p['archive'], p['bytes']) for a, p in ARCH.items()}
    pins['seat-operator-kit-v1.tar.gz'] = (KITS['seat/seat-operator-kit-v1.tar.gz'], 33242)
    for asset, (h, size) in pins.items():
        v = doc['assets'][asset]
        eq([v['sha256'], v['github_digest'], v['bytes'], v['browser_download_url']],
           [h, f'sha256:{h}', size, f'{DOWNLOADS}/{asset}'], 'download/readback pin mismatch')


def validate_clean(a, doc):
    p = ARCH[a]
    need(not any(k in doc for k in ('diagnostic_only', 'diagnostic_app_sha256', 'steps')),
         'dirty diagnostic supplied in place of clean D')
    eq([doc[k] for k in ('architecture', 'bundle_receipt_sha256', 'app_receipt_sha256', 'scenario')],
       [p['uname'], p['bundle'], APP, 'focus-then-record'], 'wrong clean D app/bundle/architecture or stale scenario')
    eq([doc[k] for k in ('virtual_native_XTest', 'human_attestation_present', 'qualification_awarded',
                         'exact_window_and_native_peer_bound', 'zero_detected_channel_discards_gaps_and_overflow')],
       [True, False, False, True, True], 'virtual machine evidence cannot award human approval')
    evidence = doc['receipt_sha256']
    need(set(evidence) == {'plan', 'product-window', 'native-panel-observer', 'release', 'x11-1',
                           *(f'product-{i}' for i in range(1, 5))} and len(set(evidence.values())) == len(evidence),
         'missing/duplicate original per-run record')
    for h in evidence.values():
        digest(h)
    digest(doc['stock_gtk_module_sha256'])
    eq(doc['receipt_count'], 4, 'missing actual product field receipt')
    eq(sorted(doc['rounds']), sorted(ROUNDS), 'incomplete or replaced IME round')
    t = doc['native_totals']
    eq([t[k] for k in ('native_gtk_callback_events', 'callbacks_outside_recorded_round_windows',
                       'native_gtk_callback_discarded', 'native_gtk_callback_sequence_gaps', 'overflow')],
       [p['callbacks'], p['outside'], 0, 0, 0], 'empty or dropped native callback channel')
    accounted = 0
    outcomes = {}
    for name in ROUNDS:
        row = doc['rounds'][name]
        f, g, panel = (row[k] for k in ('field', 'stock_gtk_callbacks', 'native_panel'))
        eq(sorted(f), sorted((*COUNTS, *FLAGS)), 'field projection adds or drops evidence')
        eq(sorted(g), sorted(GTK), 'stock GTK count set differs')
        eq(sorted(panel), sorted((*PANEL, 'last_observed_fixture_rank')), 'native panel projection fields differ')
        need(all(type(f[k]) is bool for k in FLAGS) and
             all(type(d[k]) is int and 0 <= d[k] <= 1000 for d, ks in ((f, COUNTS), (g, GTK), (panel, PANEL)) for k in ks),
             'unbounded or malformed evidence counter')
        accounted += sum(g[k] for k in GTK if k != 'commit_equal')
        quiet = not any(f[k] for k in ('paste_events', 'paste_inputs', 'other_inputs'))
        app_pre = f['starts'] > 0 and f['updates'] > 0
        native_pre = panel['visible_lookup_updates'] > 0 and min(g['preedit_start'], g['preedit_change']) > 0
        dom = f['synthetic_events'] == 0 and f['primary_focused']
        if name == 'select_candidate':
            native = native_pre and panel['last_observed_fixture_rank'] == 2 and g['commit'] == g['commit_equal'] == 1
            product = quiet and app_pre and f['expected_equal'] and f['matching_composition_ends'] == 1
            eq([f['synthetic_events'], f['ends'], f['matching_composition_ends'], f['other_inputs'], f['expected_equal']],
               [1, 0, 0, 1, True], 'clean D select observation differs')
        elif name == 'cancel':
            native = native_pre and g['commit'] == g['commit_equal'] == 0
            product = quiet and app_pre and f['primary_empty'] and f['matching_composition_ends'] == 0
            eq([f['synthetic_events'], f['ends'], f['matching_composition_ends'], f['primary_empty']],
               [1, 0, 0, True], 'clean D cancel observation differs')
        elif name == 'paste_control':
            native = panel['visible_lookup_updates'] == panel['preedit_updates'] == 0 and panel['last_observed_fixture_rank'] is None and g['commit'] == g['commit_equal'] == 0
            product = f['expected_equal'] and f['paste_inputs'] == f['paste_events'] == 1 and not any(
                f[k] for k in ('starts', 'updates', 'ends', 'matching_composition_ends', 'other_inputs'))
        else:
            native = native_pre and g['focus_out'] > 0 and g['focus_in'] > 0 and g['commit'] == g['commit_equal'] == 0
            product = quiet and app_pre and f['second_focused'] and f['moved_while_composing'] and f['primary_empty'] and \
                f['secondary_empty'] and f['delayed_matching_ends'] == 0
            eq([f['second_focused'], f['moved_while_composing'], f['primary_empty'], f['secondary_empty'],
                f['synthetic_events'], f['ends'], f['delayed_matching_ends']], [True, True, False, True, 1, 0, 0],
               'clean D active focus stale original field observation differs')
        strict = bool(dom and product)
        eq([native, strict, row['native_stage_pass'], row['strict_product_pass']],
           [True, name == 'paste_control', True, name == 'paste_control'], 'virtual strict result, native counts or trust differs')
        outcomes[name] = dict(native_stage_observed=True, strict_virtual_control_pass=strict, stock_gtk_commit=g['commit'],
                              trusted_matching_ends=f['matching_composition_ends'], trusted_ends=f['ends'],
                              untrusted_aggregate=f['synthetic_events'], final_primary_empty=f['primary_empty'])
    eq(accounted + p['outside'], p['callbacks'], 'repeated, omitted or overlapping GTK round counts')
    eq(doc['strict_virtual_join_pass'], False, 'paste-only result is not strict virtual IME qualification')
    return dict(actual_field_receipts=4, accepted_stock_gtk_callbacks=p['callbacks'],
                callbacks_within_recorded_rounds=accounted, callbacks_outside_recorded_rounds=p['outside'],
                zero_detected_gaps_discards_or_overflow=True, rounds=outcomes)


def validate_diagnostics(w, plain):
    for i, doc in enumerate((w, plain)):
        eq([doc[k] for k in ('architecture', 'clean_D_base_sha256', 'diagnostic_only', 'proves_clean_D_event_type',
                             'qualification_awarded', 'stock_gtk_callback_wrapper_loaded')],
           [ARCH['arm64']['uname'], ARCH['arm64']['bundle'], True, False, False, i == 0],
           'dirty diagnostic cannot assign event type or qualification to clean D')
        for k in ('diagnostic_app_sha256', 'diagnostic_receipt_sha256', 'diagnostic_fixture_sha256', 'source_receipt_sha256'):
            digest(doc[k])
        need(doc['diagnostic_app_sha256'] != APP and doc['diagnostic_receipt_sha256'] != ARCH['arm64']['bundle'],
             'dirty diagnostic relabeled as clean release')
    keys = ('diagnostic_app_sha256', 'diagnostic_receipt_sha256', 'diagnostic_fixture_sha256', 'steps')
    eq([w[k] for k in keys], [plain[k] for k in keys], 'wrapped and unwrapped GTK diagnostic counts differ')
    need(w['source_receipt_sha256'] != plain['source_receipt_sha256'], 'A/B reused a run')
    steps = w['steps']
    stages = set(ROUNDS) - {'paste_control'}
    eq(sorted(steps), sorted({'paste_control/before-record', *(f'{c}/{s}' for c in stages for s in ('after-preedit', 'before-record'))}),
       'missing separately timed diagnostic step')
    for c in stages:
        eq(steps[f'{c}/after-preedit']['compositionend'], dict(trusted=0, untrusted=0), 'premature diagnostic end')
        eq(steps[f'{c}/before-record']['compositionend'], dict(trusted=0, untrusted=1), 'diagnostic failed to distinguish end trust')
        eq(steps[f'{c}/before-record']['input-insertText'], dict(trusted=int(c == 'select_candidate'), untrusted=0),
           'different dirty diagnostic input-type control')
    for k in ('secondary-focus', 'secondary-pointerdown'):
        eq(steps['focus_change/before-record'][k], dict(trusted=1, untrusted=0), 'unbound diagnostic pointer focus observation')
    for k in ('paste', 'input-paste'):
        eq(steps['paste_control/before-record'][k], dict(trusted=1, untrusted=0), 'dirty diagnostic equal-paste control failed')
    eq(steps['paste_control/before-record']['compositionend'], dict(trusted=0, untrusted=0), 'paste produced a diagnostic composition end')
    return dict(architecture='linux/arm64', separately_dirty_artifact=True, unwrapped_stock_gtk_agrees=True,
                before_record_click=True, untrusted_compositionend=1, trusted_matching_end=0,
                proves_clean_d_event_type=False)


def validate_display(fixture, prod, resize, result):
    for x in (fixture, prod):
        eq([x['edge_states'], x['present_version'], x['geometry_restored']], [['armed', 'closed'], [1, 2], True],
           'unarmed/incomplete Present capture')
        eq(x['closed_event_count'], len(x['events']), 'Present tail counts differ')
        eq([x['summary'][k] for k in ('challenge_pixmap_attribution', 'compositor_scanout_or_monitor_identity_proven',
                                      'physical_panel_witness', 'qualification_awarded', 'product_round')],
           [False, False, False, False, None], 'virtual Present or a timer cannot prove physical scanout')
    eq([fixture[k] for k in ('separate_native_fixture', 'virtual_only', 'wrong_owner_rejected_before_arming',
                             'peer_issued_notify_msc_not_renderer_proof')], [True, True, True, True], 'invalid native calibration control')
    a, b = fixture['requested_serials']
    eq(fixture['events'], [dict(kind=1, kind_name='notify_msc', mode=0, mode_name='copy', record='complete', serial=a, window_update_indication=False),
                           dict(kind=0, kind_name='pixmap', mode=0, mode_name='copy', record='complete', serial=b, window_update_indication=True)],
       'timer and pixmap completions classified incorrectly')
    need(a != b and 2_000_000_000 <= fixture['duration_ns'] <= 4_000_000_000, 'bad native calibration interval')
    eq([fixture['summary'][k] for k in ('count', 'pixmap_completions', 'notify_msc_completions', 'pixmap_update_indications')],
       [2, 1, 1, 1], 'fixture Present count mismatch')
    eq([prod[k] for k in ('source_revision', 'release_tag', 'architecture', 'bundle_receipt_sha256', 'environment',
                          'period_complete', 'window_and_server_identity_bound', 'sandbox_verified', 'private_profile_verified')],
       [SOURCE, TAG, 'aarch64', ARCH['arm64']['bundle'], 'virtual-control', True, True, True, True], 'wrong clean product Present period')
    eq(prod['display'], dict(selected_connector_context=None, server='Xvfb', virtual_only=True), 'product display is not a named physical output')
    eq([prod['events'], *(prod['summary'][k] for k in ('count', 'pixmap_completions', 'notify_msc_completions', 'pixmap_update_indications'))],
       [[], 0, 0, 0, 0], 'not the completed zero-XCB-event control')
    need(6_000_000_000 <= prod['duration_ns'] <= 6_100_000_000, 'zero requires the bounded observation period')
    eq(resize, dict(resize_rounds_observed=3, initial_size_restored=True, synthetic_input_events=0), 'wrong product resize control')
    eq([result[k] for k in ('source_revision', 'release_tag', 'xorg_physical_runtime_tested', 'amd64_native_runtime_tested',
                            'independent_physical_panel_witness', 'qualification_awarded', 'display_gate_v1', 'ime_gate_v1')],
       [SOURCE, TAG, False, False, False, False, 'held', 'held'], 'no physical panel validated by observation')
    eq([result['installed_clean_d'][k] for k in ('period_complete', 'own_drawable_resizes_observed_and_restored',
                                                'total_present_complete_notify', 'challenge_rounds_observed')],
       [True, 3, 0, 0], 'unreconciled product Present disposition')
    return dict(arm64_native_calibration_pixmap_copy=1, arm64_native_calibration_notify_msc_timer=1,
                arm64_product_resizes=3, arm64_product_present_completions=0,
                arm64_product_period_ns=prod['duration_ns'], measured_renderer_backend=False,
                amd64_native_present_calibration=False, physical_panel_witness=False, scanout_proven=False)


def verify(root, originals=None):
    index_raw = read(root / 'evidence-index.json')
    need(sha(index_raw) == INDEX, 'wrong frozen desktop-seat evidence digest')
    index = load(index_raw)
    eq(sorted(index), sorted((*ORIGINAL, *SCRUB)), 'missing/additional frozen evidence')
    blobs = {}
    for name, data in index.items():
        clean_name = name if name in ORIGINAL else name + '.projection.json'
        raw = blobs[name] = read(root / 'evidence' / clean_name)
        digest(data['original_sha256'])
        eq(data['evidence_sha256'], sha(raw), 'bounded evidence bytes changed')
        eq(data['kind'], 'exact-original' if name in ORIGINAL else 'scrubbed-projection', 'evidence kind differs')
        if name in ORIGINAL:
            eq(data['original_sha256'], sha(raw), 'reserialized an exact original')
        if originals is not None:
            original = read(originals / name)
            eq(data['original_sha256'], sha(original), 'source original changed')
            eq(sha(raw), sha(original if name in ORIGINAL else wire(scrub(name, original))), 'projection differs from original')
    for group, manifest in (('seat-reconciliation', 'SHA256SUMS'), ('seat-observer', 'SHA256SUMS'),
                            ('present-observer', 'EVIDENCE.sha256')):
        map_ = sums(blobs[f'{group}/{manifest}'])
        for key, h in map_.items():
            name = f'{group}/{key}'
            if name in index:
                eq(h, index[name]['original_sha256'], 'upstream original hash differs from frozen receipt')
            elif name in KITS:
                eq(h, KITS[name], 'wrong handoff kit original digest')
    if originals is not None:
        for name, h in KITS.items():
            eq(sha(read(originals / name)), h, 'wrong separately retained handoff kit')
    doc = lambda n: load(blobs[n])
    validate_publication(doc('desktop-alpha/github-release-proof.json'))
    clean = {a: doc(f'seat-reconciliation/{a}-clean-D-fixture-selection.json') for a in ARCH}
    ime = {a: validate_clean(a, clean[a]) for a in ARCH}
    need(ime['arm64']['rounds'] == ime['amd64']['rounds'], 'architectures differ in fixed product outcomes')
    need(set(clean['arm64']['receipt_sha256'].values()).isdisjoint(clean['amd64']['receipt_sha256'].values()),
         'cross-architecture receipt hash reuse')
    for a, p in ARCH.items():
        w = doc(f'seat/{p["xvfb"]}')
        eq([w[k] for k in ('arch', 'release_receipt_sha256', 'same_run_plan', 'environment', 'x_server', 'backend',
                           'viewable', 'owner_verified', 'electron_executable_matches', 'renderer_sandbox_verified',
                           'physical_candidate', 'active_local_seat', 'window_on_selected_output', 'virtual_output', 'output')],
           [p['uname'], p['bundle'], True, 'virtual-control', 'Xvfb', 'x11', True, True, True, True, False, False, False, True, None],
           'virtual controls cannot substitute for enrolled local Xorg and physical output')
    result = doc('seat-reconciliation/RESULT.json')
    eq([result[k] for k in ('qualification_awarded', 'physical_display', 'system_ime', 'mechanical_round_collection_pass',
                            'strict_clean_D_virtual_technical_pass', 'strict_round_pass_both_architectures')],
       [False, {a: 'held' for a in ARCH}, {a: 'held' for a in ARCH}, {a: True for a in ARCH},
        {a: False for a in ARCH}, {c: c == 'paste_control' for c in ROUNDS}], 'derived four-cell held disposition differs')
    diag = validate_diagnostics(*(doc(f'seat-reconciliation/{name}') for name in A_B))
    display = validate_display(doc(PRESENT_FIXTURE), doc(PRESENT_PRODUCT), doc('present-observer/arm64-clean-d-resize.json'),
                               doc('present-observer/RESULT.json'))
    pin = index['present-observer/arm64-release-pins.json']['original_sha256']
    eq(doc(PRESENT_PRODUCT)['input_sha256']['release'], pin, 'Present period was pinned to a different release receipt')
    eq(doc('seat-reconciliation/arm64-clean-D-fixture-selection.json')['receipt_sha256']['release'], pin,
       'ARM IME was pinned to a different release receipt')
    earlier, v2 = doc(V2_EARLIER), doc('seat-observer/RESULT.json')
    eq([earlier['identity_bound'], earlier['product_rounds'], earlier['native']['native_gtk_callback_events'],
        earlier['native']['human_attestation_present'], earlier['native']['claim_awarded'], v2['qualification_awarded']],
       [True, list(ROUNDS[:3]), 108, False, False, False], 'earlier native three-round observer is not final clean D')
    eq([earlier['gtk_rounds'][c]['commit'] for c in ROUNDS[:3]], [1, 0, 0], 'earlier native control counts differ')
    return dict(schema='ruyitrace.platform-held-desktop-seat-evidence.v1', evidence_sha256=INDEX, evidence_members=len(index),
                status='technical_evidence_verified_physical_display_and_system_ime_held', source=SOURCE, release_tag=TAG,
                published_operator_handoff=f'{DOWNLOADS}/seat-operator-kit-v1.tar.gz',
                published_release=RELEASE, published_guide=f'{DOWNLOADS}/DESKTOP-ALPHA-ZH.md', kits_sha256=KITS,
                product_qualified=False, human_signoff=False, formal_approvals=0,
                cells={f'linux/{a}/{gate}': 'held' for a in ARCH for gate in ('physical-display', 'system-ime')},
                clean_d_virtual_ime=ime, dirty_diagnostic_only=diag, native_virtual_present=display,
                earlier_arm_observer=dict(accepted_callbacks=108, actual_field_receipts=3, qualification_awarded=False),
                constraints=['frozen technical evidence only; the verifier has no human-pass path',
                             'stock GTK counts are peer-bound record windows, not per-DOM-field or post-window proof',
                             'virtual Present can distinguish a timer from a pixmap but cannot attest final scanout',
                             'separate dirty diagnostic event types must not be imputed to sealed clean D',
                             'binary archives and raw identity-bearing lab artifacts remain outside Git'])


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--evidence', type=Path, default=HERE)
    p.add_argument('--originals-root', type=Path)
    a = p.parse_args()
    try:
        result = verify(a.evidence.resolve(), a.originals_root.resolve() if a.originals_root else None)
    except (KeyError, ValueError, OSError, IndexError, TypeError) as exc:
        print(json.dumps(dict(status='evidence_rejected', formal_approvals=0, human_signoff=False, reason=str(exc))))
        return 1
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
