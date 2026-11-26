"""Offline negative tests for native WS V2 acceptance; arm64 ZIP integration is optional."""

import importlib.util
from pathlib import Path
import unittest


RECEIPT = (Path(__file__).resolve().parents[1] / 'artifacts/receipts/trace-linux-gap-closure-v1/patched-websocket')
MOD = importlib.util.spec_from_file_location('verify_patched_websocket', RECEIPT / 'verify.py')
v = importlib.util.module_from_spec(MOD)
MOD.loader.exec_module(v)


def row(seq, direction, opcode, fin, length):
    return dict(family='websocket', kind='frame', connection=1, direction=direction, opcode=opcode,
                fin=fin, length=length, seq=seq)


class NativeWriterControls(unittest.TestCase):
    def setUp(self):
        self.ids = dict(schema=1, runId='f' * 32, origin='http://127.0.0.1:19081', mode='websocket',
                        documentPath='/harness', enabled=True, writerPid=8, contentPid=123,
                        browsingContextId=1, innerWindowId=123456789)
        self.ready, self.armed = (dict(self.ids, state=s) for s in ('ready', 'armed'))
        self.seal = dict(self.ids, state='sealed', accepted=0, complete=True, status='ok',
                         childSeen=0, childSent=0, drops=dict(v.DROPS), nativeTransport=dict(v.TRANSPORT))

    def test_exact_scalars_and_chronology(self):
        values = [('tx', 1, True, 5), ('rx', 1, True, 5), ('rx', 1, False, 4), ('rx', 9, True, 1),
                  ('tx', 10, True, 1), ('rx', 0, True, 4), ('tx', 8, True, 2), ('rx', 8, True, 2)]
        rows = [row(i, *x) for i, x in enumerate(values, 1)]
        self.assertEqual(len(v.project('websocket', 'fragment_and_ping', rows)), 8)
        with self.assertRaisesRegex(ValueError, 'frame order'):
            rows[3], rows[4] = dict(rows[4], seq=4), dict(rows[3], seq=5)
            v.project('websocket', 'fragment_and_ping', rows)
        with self.assertRaisesRegex(ValueError, 'row allowlist'):
            rows = [row(i, *x) for i, x in enumerate(values, 1)]
            rows[0]['payload'] = 'synthetic'
            v.project('websocket', 'fragment_and_ping', rows)

    def test_reject_application_messages_masquerading_as_frames(self):
        rows = [row(1, 'tx', 1, True, 5), row(2, 'rx', 1, True, 5), row(3, 'rx', 1, True, 8),
                row(4, 'tx', 8, True, 2), row(5, 'rx', 8, True, 2)]
        with self.assertRaisesRegex(ValueError, 'native frame order'):
            v.project('websocket', 'fragment_and_ping', rows)
        with self.assertRaisesRegex(ValueError, 'native frame order'):
            v.project('websocket', 'upgrade_only', [])

    def test_claimed_stock_unsupported_is_not_zero(self):
        v.validate_seal(self.ids, self.ready, self.armed, self.seal, 'websocket', 0)
        for armed, seal in [(None, dict(self.seal, status='unsupported', complete=False, childSent=None)),
                            (self.armed, dict(self.seal, status='unsupported', complete=True))]:
            with self.subTest(armed=armed is not None), self.assertRaises(ValueError):
                v.validate_seal(self.ids, self.ready, armed, seal, 'websocket', 0)

    def test_no_io_or_limit_loss_or_native_pending_can_be_counted(self):
        # Gecko counts queued callbacks and incomplete sends in nativeFailures;
        # the installed overlay adds nativeFailures to the writer protocol bucket.
        for field in ('protocol', 'io', 'limit', 'invalid', 'scope'):
            seal = dict(self.seal, drops=dict(self.seal['drops'], **{field: 1}))
            with self.subTest(field=field), self.assertRaisesRegex(ValueError, 'pending/protocol'):
                v.validate_seal(self.ids, self.ready, self.armed, seal, 'websocket', 0)
        for seal in (dict(self.seal, childSent=1), dict(self.seal, nativePendingSends=1),
                     dict(self.seal, complete=False, status='partial')):
            with self.assertRaises(ValueError):
                v.validate_seal(self.ids, self.ready, self.armed, seal, 'websocket', 0)

    def test_socket_process_observation_is_not_security_disable(self):
        for f in v.TRANSPORT:
            seal = dict(self.seal, nativeTransport=dict(v.TRANSPORT, **{f: not v.TRANSPORT[f]}))
            with self.subTest(field=f), self.assertRaisesRegex(ValueError, 'transport mismatch'):
                v.validate_seal(self.ids, self.ready, self.armed, seal, 'websocket', 0)

    def test_truncated_or_duplicate_field_in_native_original(self):
        for raw in (b'{"seq":1}', b'{"seq":1,"seq":2}\n', b'{"seq":1}\r\n'):
            with self.subTest(raw=raw), self.assertRaises(ValueError):
                v.rows_of(raw)


@unittest.skipUnless((RECEIPT / 'arm64-originals.zip').is_file(), 'local ARM64 originals ZIP not present')
class JoinedEvidenceControls(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.blobs = v.load_zip(RECEIPT / 'arm64-originals.zip')

    def replace(self, path, mutate):
        obj = v.object_at(self.blobs[path])
        mutate(obj)
        return dict(self.blobs, **{path: v.canonical(obj)})

    def test_real_qualification_passes_for_22_cases_on_one_image(self):
        report = v.verify(self.blobs)
        self.assertEqual(report['platform'], 'linux/arm64')
        self.assertEqual(report['accepted_cases'], 22)
        self.assertEqual(report['regression_cases_on_new_bytes'], 17)
        self.assertEqual(report['gates']['websocket']['native_rows'], 10)

    def test_reject_wrong_kernel_even_with_consistent_native_receipt_digests(self):
        bad = '0' * 64
        blobs = dict(self.blobs)
        for name in ('kernel/build.json', 'kernel/readback.json', 'kernel/lineage.json'):
            obj = v.object_at(blobs[name])
            if name.endswith('build.json'):
                obj['archive']['sha256'] = bad
            elif name.endswith('readback.json'):
                obj['archive']['sha256'] = bad
                obj['independent_reference'] = v.bytes_record(blobs['kernel/build.json'])
            else:
                obj['package'].update(sha256=bad, native_receipt=v.bytes_record(blobs['kernel/build.json']),
                                      independent_receipt=v.bytes_record(blobs['kernel/readback.json']))
            blobs[name] = v.canonical(obj)
        with self.assertRaisesRegex(ValueError, 'wrong kernel archive SHA'):
            v.verify(blobs)

    def test_reject_mixed_build_regressions(self):
        for path, bad in [('build_id', '20261123161729'), ('image_id', v.STOCK_OVERLAY)]:
            blobs = self.replace('lane/http--redirect/run.json', lambda j: j.update({path: bad}))
            with self.subTest(field=path), self.assertRaisesRegex(ValueError, 'http/redirect: mixed build'):
                v.verify(blobs)

    def test_reject_unscanned_pending_native_output(self):
        ctl = 'scope/websocket--skip/controls.json'
        blobs = self.replace(ctl, lambda j: j['native_root_members'].append('native-events.jsonl.pending'))
        idx = v.object_at(blobs['scope/index.json'])
        idx['scopes']['websocket--skip']['controls_sha256'] = v.sha(blobs[ctl])
        blobs['scope/index.json'] = v.canonical(idx)
        with self.assertRaisesRegex(ValueError, r'extra native output \(including .pending\)'):
            v.verify(blobs)

    def test_reject_dropped_native_output_even_with_recounted_seal(self):
        p = 'lane/websocket--fragment_and_ping/native/'
        names = p + 'native-events.jsonl', p + 'native-sealed.json'
        blobs = self.replace(names[1], lambda j: j.update(accepted=7))
        blobs[names[0]] = b'\n'.join(blobs[names[0]].splitlines()[:-1]) + b'\n'
        with self.assertRaisesRegex(ValueError, 'native frame order'):
            v.verify(blobs)

    def test_reject_stock_unsupported_disguised_as_success(self):
        blobs = self.replace('controls/unsupported/native-sealed.json', lambda j: j.update(complete=True, status='ok'))
        with self.assertRaisesRegex(ValueError, 'stock unsupported is not a sealed zero'):
            v.verify(blobs)


if __name__ == '__main__':
    unittest.main()
