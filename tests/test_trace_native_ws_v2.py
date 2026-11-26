"""Offline negative tests for native WS V2 acceptance; arm64 ZIP integration is optional."""

from dataclasses import replace
import importlib.util
import io
from pathlib import Path
import subprocess
import sys
import unittest
from unittest.mock import patch


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

    def test_writer_budget_counts_rows_separately_from_scope_header(self):
        h = v.canonical(dict(self.ids, state='header', documentPath='/' + 'a' * 90))
        self.assertGreater(len(h), 256)
        self.assertEqual(len(v.rows_of(h + v.canonical(row(1, 'tx', 1, True, 5)))), 2)
        with self.assertRaisesRegex(ValueError, 'row/byte budget'):
            v.rows_of(h + v.canonical(dict(row(1, 'tx', 1, True, 5), unexpected='a' * 256)))


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
        self.assertEqual((v.json.dumps(report, indent=2, sort_keys=True) + '\n').encode(),
                         (RECEIPT / 'arm64-review.json').read_bytes())

    def test_amd_context_rejects_arm_release_even_if_manifest_hashes_are_supplied(self):
        amd_pins = replace(amd.admission(synthetic_pins()), archive_proof=v.ARCHIVE_PROOF,
                           image_manifest=v.IMAGE_MANIFEST)
        with self.assertRaisesRegex(ValueError, 'wrong export identity'):
            v.verify(self.blobs, pins=amd_pins, producer_intakes=True)

    def test_producer_layout_still_checks_packet_original_byte_joins(self):
        # ARM is the only real fixture while AMD acquisition is pending. Exercise
        # the alternative intake layout without constructing a synthetic AMD pass.
        blobs = dict(self.blobs)
        del blobs['intake/index.json']
        self.assertEqual(v.verify(blobs, producer_intakes=True), v.verify(self.blobs))
        name = 'intake/arm64-websocket/cases/fragment_and_ping/native/original.bin'
        blobs[name] = blobs[name][:-1]
        with self.assertRaisesRegex(ValueError, 'substitutes the four native originals'):
            v.verify(blobs, producer_intakes=True)

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


OMNI = importlib.util.spec_from_file_location('verify_amd64_omni', RECEIPT / 'verify_amd64_omni.py')
om = importlib.util.module_from_spec(OMNI)
AMD = importlib.util.spec_from_file_location('verify_patched_amd64', RECEIPT / 'verify_amd64.py')
amd = importlib.util.module_from_spec(AMD)
with patch.dict(sys.modules, verify=v, verify_amd64_omni=om):
    OMNI.loader.exec_module(om)
    AMD.loader.exec_module(amd)


def synthetic_pins():
    # Admission-shape probes only; these are explicitly not artifact identities.
    digest = lambda field: v.sha(('synthetic test only: ' + field).encode())
    out = {name: digest(name) for name in ('kernel_sha256', 'libxul_sha256', 'operator_sha256', 'export_proof_sha256',
                                           'image_receipt_sha256', 'evidence_index_sha256', 'native_omni_review_sha256')}
    return dict(out, schema='ruyitrace.patched-amd64-review-pins.v1', platform=amd.ARCH,
                image_id='sha256:' + digest('image'), elf_build_id=digest('elf')[:40],
                kernel_bytes=1, operator_bytes=2, runtime_source=v.PRODUCT, source_set_sha256=v.SOURCE_SET,
                capture_day_utc='2026-11-26')


class Amd64AdmissionControls(unittest.TestCase):
    def test_separate_native_build_and_machine(self):
        got = amd.admission(synthetic_pins())
        self.assertEqual((got.arch, got.native_arch, got.machine, got.host), ('linux/amd64', 'x86_64', 62, 'host185'))
        self.assertNotEqual(got.build, v.ARM64.build)
        self.assertEqual(got.kernel_name, 'firefox-159.0.en-US.linux-x86_64.tar.xz')

    def test_reject_stock_and_arm_artifact_pins(self):
        for field, wrong in (('image_id', amd.STOCK), ('image_id', v.IMAGE), ('kernel_sha256', v.KERNEL),
                             ('operator_sha256', v.ARCHIVE), ('libxul_sha256', v.LIBXUL)):
            with self.subTest(field=field), self.assertRaisesRegex(ValueError, 'substituted'):
                amd.admission(dict(synthetic_pins(), **{field: wrong}))

    def test_reject_changed_source_and_placeholder(self):
        with self.assertRaisesRegex(ValueError, 'runtime source'):
            amd.admission(dict(synthetic_pins(), runtime_source='0' * 40))
        with self.assertRaisesRegex(ValueError, 'empty digest pin'):
            amd.admission(dict(synthetic_pins(), kernel_sha256='0' * 64))
        p = synthetic_pins()
        del p['kernel_sha256']
        with self.assertRaisesRegex(ValueError, 'schema or platform'):
            amd.admission(p)

    def test_mismatched_index_cannot_qualify(self):
        with self.assertRaisesRegex(ValueError, 'original-byte index digest mismatch'):
            amd.verify_amd64({}, synthetic_pins(), None, None)

    def test_cli_emits_no_acceptance_on_missing_native_artifacts(self):
        args = [sys.executable, '-B', str(RECEIPT / 'verify_amd64.py')]
        for n in ('qualified', 'kernel-dir', 'baseline', 'image-receipt', 'patch', 'native-work',
                  'runtime-source', 'stock-control', 'stock-smoke'):
            args.extend(('--' + n, str(RECEIPT / 'missing-test-input')))
        sent = subprocess.run(args, text=True, capture_output=True, check=False)
        self.assertEqual(sent.returncode, 2)
        self.assertEqual(sent.stdout, '')
        self.assertIn('requires externally pinned identity and both full artifacts', sent.stderr)
        indexed = subprocess.run([*args, '--index-only'], text=True, capture_output=True, check=False)
        self.assertEqual(indexed.returncode, 1)
        self.assertEqual(indexed.stdout, '')
        self.assertIn('missing or nonregular original: identity.json', indexed.stderr)


class Amd64OmniDeltaControls(unittest.TestCase):
    @staticmethod
    def make_omni(build_config, script=b'const x = 7;', metadata=None):
        buf = io.BytesIO()
        with v.zipfile.ZipFile(buf, 'w') as z:
            z.writestr('before.txt', b'before')
            z.writestr(om.HTML, build_config)
            item = v.zipfile.ZipInfo('after.sys.mjs', (2026, 11, 26, 0, 0, 0))
            if metadata is not None:
                item.external_attr = metadata
            z.writestr(item, script)
        return buf.getvalue()

    def test_reconstructs_only_the_configure_token_and_zip_offsets(self):
        old = om.ANCHOR + b' --disable-tests</p>'
        new = old.replace(om.ANCHOR, om.ANCHOR + om.TOKEN)
        a, b = self.make_omni(old), self.make_omni(new)
        self.assertTrue(om.compare(a, b, count=3)['reconstructs_identical_archive'])
        with self.assertRaisesRegex(ValueError, 'another build member change'):
            om.compare(a, self.make_omni(new, script=b'const x = 8;'), count=3)
        with self.assertRaisesRegex(ValueError, 'metadata changed'):
            om.compare(a, self.make_omni(new, metadata=0o100777 << 16), count=3)
        with self.assertRaisesRegex(ValueError, 'other content changes'):
            om.compare(a, self.make_omni(new.replace(b'--disable-tests', b'--enable-tests')), count=3)

    def test_amd_requires_a_receipt_and_arm_rejects_the_exception(self):
        with self.assertRaisesRegex(ValueError, 'requires direct, pinned ZIP comparison'):
            v.reviewed_native_omni(None, amd.admission(synthetic_pins()))
        with self.assertRaisesRegex(ValueError, 'ARM native delta is frozen'):
            v.reviewed_native_omni({'schema': 'synthetic'}, v.ARM64)


@unittest.skipUnless((RECEIPT / 'amd64-originals.zip').is_file(), 'local AMD64 originals ZIP not present')
class Amd64FrozenReceiptControls(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        raw = v.object_at((RECEIPT / 'amd64-review-pins.json').read_bytes())
        cls.pins = amd.admission(raw)
        cls.blobs = v.load_zip(RECEIPT / 'amd64-originals.zip', index_sha=raw['evidence_index_sha256'])
        cls.omni = v.object_at((RECEIPT / 'amd64-native-omni-review.json').read_bytes())

    def test_real_amd_receipts_reproduce_exact_case_verdict(self):
        report = amd.verify_receipts(self.blobs, self.pins, self.omni)
        self.assertEqual((report['platform'], report['accepted_cases'], report['regression_cases_on_new_bytes']),
                         ('linux/amd64', 22, 17))
        self.assertEqual((v.json.dumps(report, indent=2, sort_keys=True) + '\n').encode(),
                         (RECEIPT / 'amd64-review.json').read_bytes())

    def test_rejects_substituted_producer_packet_index(self):
        name = 'qualified/summary.json'
        summary = v.object_at(self.blobs[name])
        summary['intakes']['websocket']['candidate_sha256'] = '0' * 64
        altered = dict(self.blobs, **{name: v.canonical(summary)})
        with self.assertRaisesRegex(ValueError, 'producer terminal summary is incomplete or mixed'):
            amd.verify_receipts(altered, self.pins, self.omni)

    def test_frozen_amd_allowance_rejects_conflated_omni_hash(self):
        name = 'image/image.json'
        img = v.object_at(self.blobs[name])
        img['pre_overlay_omni_sha256'] = img['package_sha256']['omni.ja']
        blob = v.canonical(img)
        mutated = dict(self.blobs, **{name: blob})
        with self.assertRaisesRegex(ValueError, 'runtime did not use exported installed bytes'):
            amd.verify_receipts(mutated, replace(self.pins, image_manifest=v.sha(blob)), self.omni)


@unittest.skipUnless((RECEIPT / 'amd64-review.json').is_file(), 'AMD64 cross-architecture report not present')
class TwoArchitectureJoinControls(unittest.TestCase):
    def test_join_requires_two_distinct_frozen_architecture_reports(self):
        j = importlib.util.spec_from_file_location('join_patched_reviews', RECEIPT / 'join_reviews.py')
        join = importlib.util.module_from_spec(j)
        with patch.dict(sys.modules, verify=v):
            j.loader.exec_module(join)
        reports = {arch: tuple((RECEIPT / (arch.split('/')[1] + ending)).read_bytes()
                              for ending in ('-review.json', '-full-byte-review.json')) for arch in join.PINS}
        self.assertEqual(join.join(reports)['cases'], 44)
        reports[amd.ARCH] = reports[v.ARCH]
        with self.assertRaisesRegex(ValueError, 'pre-reviewed verdict digest differs'):
            join.join(reports)


if __name__ == '__main__':
    unittest.main()
