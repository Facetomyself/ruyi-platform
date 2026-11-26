"""Check frozen clean D desktop evidence without awarding a human pass."""

import importlib.util
import json
from pathlib import Path
import shutil
import tempfile
import unittest

ROOT = (Path(__file__).resolve().parents[1] / 'artifacts' / 'receipts' /
        'trace-linux-gap-closure-v1' / 'desktop-seat')
spec = importlib.util.spec_from_file_location('verify_desktop_seat', ROOT / 'verify_desktop_seat.py')
v = importlib.util.module_from_spec(spec)
spec.loader.exec_module(v)


def doc(name):
    n = name + '.projection.json' if name in v.SCRUB else name
    return v.load(v.read(ROOT / 'evidence' / n))


def clean(a='arm64'):
    return doc(f'seat-reconciliation/{a}-clean-D-fixture-selection.json')


def view():
    return (doc(v.PRESENT_FIXTURE), doc(v.PRESENT_PRODUCT),
            doc('present-observer/arm64-clean-d-resize.json'), doc('present-observer/RESULT.json'))


def diagnostics():
    return tuple(doc(f'seat-reconciliation/{n}') for n in v.A_B)


class HeldDesktopTests(unittest.TestCase):
    def test_default_matches_machine_receipt_and_holds_four_cells(self):
        r = v.verify(ROOT)
        self.assertEqual(r, json.loads((ROOT / 'desktop-seat-review.json').read_bytes()))
        self.assertEqual(set(r['cells']), {f'linux/{a}/{g}' for a in v.ARCH for g in ('physical-display', 'system-ime')})
        self.assertEqual(set(r['cells'].values()), {'held'})
        self.assertEqual(r['formal_approvals'], 0)
        self.assertFalse(r['human_signoff'])
        self.assertFalse(r['product_qualified'])
        self.assertEqual(r['published_operator_handoff'], v.DOWNLOADS + '/seat-operator-kit-v1.tar.gz')

    def test_callbacks_accounted_for_but_not_qualified(self):
        for a, totals in {'arm64': (164, 153, 11), 'amd64': (144, 137, 7)}.items():
            x = v.validate_clean(a, clean(a))
            self.assertEqual((x['accepted_stock_gtk_callbacks'], x['callbacks_within_recorded_rounds'],
                              x['callbacks_outside_recorded_rounds']), totals)
            self.assertEqual([k for k, r in x['rounds'].items() if r['strict_virtual_control_pass']], ['paste_control'])
            self.assertEqual(x['rounds']['select_candidate']['stock_gtk_commit'], 1)
            self.assertFalse(x['rounds']['focus_change']['final_primary_empty'])

    def test_reject_claiming_human_from_virtual_and_dirty(self):
        x = clean()
        x['human_attestation_present'] = True
        with self.assertRaisesRegex(ValueError, 'virtual machine evidence'):
            v.validate_clean('arm64', x)
        x = clean()
        x['diagnostic_only'] = True
        with self.assertRaisesRegex(ValueError, 'dirty diagnostic'):
            v.validate_clean('arm64', x)
        x = clean('amd64')
        with self.assertRaisesRegex(ValueError, 'wrong clean D'):
            v.validate_clean('arm64', x)

    def test_missing_round_or_reused_receipt_is_not_approval(self):
        x = clean()
        x['rounds'].pop('focus_change')
        with self.assertRaisesRegex(ValueError, 'incomplete.*round'):
            v.validate_clean('arm64', x)
        x = clean()
        x['receipt_sha256']['product-2'] = x['receipt_sha256']['product-1']
        with self.assertRaisesRegex(ValueError, 'duplicate original'):
            v.validate_clean('arm64', x)

    def test_no_zero_from_empty_dropped_or_unaccounted_stream(self):
        for key, value, reason in (('native_gtk_callback_events', 0, 'empty or dropped'),
                                   ('native_gtk_callback_sequence_gaps', 1, 'empty or dropped'),
                                   ('overflow', 1, 'empty or dropped')):
            with self.subTest(key=key):
                x = clean()
                x['native_totals'][key] = value
                with self.assertRaisesRegex(ValueError, reason):
                    v.validate_clean('arm64', x)
        x = clean()
        x['rounds']['focus_change']['stock_gtk_callbacks']['reset'] += 1
        with self.assertRaisesRegex(ValueError, 'overlapping GTK'):
            v.validate_clean('arm64', x)

    def test_equal_text_alone_is_not_ime_or_late_focus_evidence(self):
        x = clean()
        x['strict_virtual_join_pass'] = True
        with self.assertRaisesRegex(ValueError, 'paste-only'):
            v.validate_clean('arm64', x)
        x = clean()
        x['rounds']['focus_change']['field']['primary_empty'] = True
        with self.assertRaisesRegex(ValueError, 'stale original field'):
            v.validate_clean('arm64', x)
        x = clean()
        x['rounds']['select_candidate']['stock_gtk_callbacks']['commit_equal'] = 0
        with self.assertRaisesRegex(ValueError, 'native counts'):
            v.validate_clean('arm64', x)

    def test_dirty_type_is_never_assigned_to_clean_d(self):
        wrap, plain = diagnostics()
        wrap['proves_clean_D_event_type'] = True
        with self.assertRaisesRegex(ValueError, 'cannot assign event type'):
            v.validate_diagnostics(wrap, plain)
        wrap, plain = diagnostics()
        plain['steps']['cancel/before-record']['compositionend']['trusted'] = 1
        with self.assertRaisesRegex(ValueError, 'counts differ'):
            v.validate_diagnostics(wrap, plain)
        wrap, plain = diagnostics()
        plain['source_receipt_sha256'] = wrap['source_receipt_sha256']
        with self.assertRaisesRegex(ValueError, 'A/B reused'):
            v.validate_diagnostics(wrap, plain)

    def test_timer_is_not_pixmap_or_physical_panel(self):
        f, p, resize, result = view()
        f['events'][0]['window_update_indication'] = True
        with self.assertRaisesRegex(ValueError, 'timer and pixmap'):
            v.validate_display(f, p, resize, result)
        f, p, resize, result = view()
        p['summary']['compositor_scanout_or_monitor_identity_proven'] = True
        with self.assertRaisesRegex(ValueError, 'cannot prove physical scanout'):
            v.validate_display(f, p, resize, result)

    def test_zero_present_rows_need_complete_window(self):
        f, p, resize, result = view()
        p['duration_ns'] = 0
        with self.assertRaisesRegex(ValueError, 'requires the bounded observation period'):
            v.validate_display(f, p, resize, result)
        f, p, resize, result = view()
        p['period_complete'] = False
        with self.assertRaisesRegex(ValueError, 'wrong clean product Present'):
            v.validate_display(f, p, resize, result)

    def test_wrong_release_or_changed_projection_bytes_rejected(self):
        proof = doc('desktop-alpha/github-release-proof.json')
        proof['bundle_receipt_sha256']['arm64'] = 'a' * 64
        with self.assertRaisesRegex(ValueError, 'published release bundle mismatch'):
            v.validate_publication(proof)
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp).resolve() / 'seat'
            shutil.copytree(ROOT, path)
            p = path / 'evidence' / (v.PRESENT_PRODUCT + '.projection.json')
            p.write_bytes(b' ' + p.read_bytes())
            with self.assertRaisesRegex(ValueError, 'bounded evidence bytes changed'):
                v.verify(path)

    def test_scrubbed_identity_and_no_binary_deliverables(self):
        for n in v.SCRUB:
            b = v.read(ROOT / 'evidence' / (n + '.projection.json'))
            for private in (b'"pid"', b'"renderer_pid"', b'"exact_electron_pid"', b'"run_id"',
                            b'"server_pid"', b'profile_inode', b'/root/', b'/home/ubuntu/'):
                self.assertNotIn(private, b)
        self.assertFalse(list((ROOT / 'evidence').rglob('*.tar.gz')))


if __name__ == '__main__':
    unittest.main()
