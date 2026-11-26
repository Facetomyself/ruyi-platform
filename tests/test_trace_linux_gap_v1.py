"""Candidate-002 frozen-evidence and adversarial offline verification tests."""

import importlib.util
import json
from pathlib import Path
import stat
import subprocess
import sys
import tempfile
import unittest
import warnings
import zipfile

RECEIPT = (Path(__file__).resolve().parents[1] / 'artifacts' / 'receipts' / 'trace-linux-gap-closure-v1')
BUNDLE = RECEIPT / 'candidate-002-originals.zip'
VERIFIER = RECEIPT / 'verify_candidate_002.py'
spec = importlib.util.spec_from_file_location('verify_candidate_002', VERIFIER)
v = importlib.util.module_from_spec(spec)
spec.loader.exec_module(v)

ARM = 'integrated-arm64-002/'
AMD = 'integrated-amd64-002/'
NATIVE = 'native/native-'


def change(members, name, **changes):
    obj = v.object_at(members[name])
    obj.update(changes)
    members[name] = v.canonical(obj)


class Candidate002Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.original = v.read_evidence(BUNDLE)
        cls.controls = RECEIPT / 'controls'

    def check_bad(self, data, reason):
        # Bypass the outer byte pin to independently challenge semantic checks.
        with self.assertRaisesRegex(ValueError, reason):
            v.verify(data, self.controls)

    def test_frozen_six_cells_and_machine_receipt(self):
        result = v.verify(self.original, self.controls)
        self.assertEqual(result['verified_cases'], 34)
        self.assertEqual(result['stock_workloads_only'], 44)
        self.assertEqual(result['structurally_eligible_observers'], 80)
        self.assertFalse(result['product_qualified'])
        self.assertEqual(result['websocket'], 'unsupported_on_candidate_002_base_kernels')
        self.assertEqual(len(result['cells']), 6)
        for a in v.PINS:
            for g, (cases, native_rows, zeros) in {
                'wasm': (6, 8, 4), 'jscall': (5, 8, 3), 'http': (6, 4, 3),
            }.items():
                cell = result['cells'][f'linux/{a}/{v.CELL_NAMES[g]}']
                self.assertEqual((cell['cases'], cell['observed_native_rows'], len(cell['sealed_zero_cases'])),
                                 (cases, native_rows, zeros))
                self.assertEqual(cell['status'], 'bounded_raw_evidence_verified_pending_strict_external_review')
            result['images'][a]['local_archive_rehashed'] = False
        self.assertEqual(result, json.loads((RECEIPT / 'candidate-002-review.json').read_bytes()))

    def test_wrong_arch_and_wrong_image(self):
        for name, other, reason in (
            (ARM + 'http--fetch/host.json', AMD + 'http--fetch/host.json', 'wrong arch'),
            ('export-arm64-002/archive-proof.json', 'export-amd64-002/archive-proof.json', 'wrong fixed archive'),
        ):
            with self.subTest(name=name):
                data = dict(self.original)
                data[name] = data[other]
                self.check_bad(data, reason)
        data = dict(self.original)
        change(data, ARM + 'http--fetch/host.json', image_id=v.PINS['arm64']['base'])
        self.check_bad(data, 'wrong host, image layer chain')

    def test_repeat_is_exact_file_equality(self):
        data = dict(self.original)
        name = 'runtime/arm64/repeat-002/image.json'
        data[name] = (json.dumps(v.object_at(data[name]), indent=2) + '\n').encode('ascii')
        self.assertNotEqual(data[name], self.original[name])
        self.assertEqual(v.object_at(self.original[name]), v.object_at(data[name]))
        self.check_bad(data, 'Runtime repeat bytes')

    def test_wrong_revision_and_failed_attempt(self):
        for changes in (
            {'snapshot_sha256': '0' * 64}, {'code': 1}, {'base': True}, {'remaining_containers': 1},
            {'additional_native_event_files': ['other-events.jsonl']},
        ):
            with self.subTest(changes=changes):
                data = dict(self.original)
                change(data, ARM + 'wasm--compile_only/host.json', **changes)
                self.check_bad(data, 'wrong host, image layer chain, snapshot, output scan or historical/failed attempt')
        data = dict(self.original)
        change(data, ARM + 'wasm--compile_only/run.json', browser_exit=-15)
        self.check_bad(data, 'normal exit')
        data = dict(self.original)
        change(data, ARM + 'wasm--compile_only/run.json', started_utc='2026-11-25T10:00:00+00:00')
        self.check_bad(data, 'historical run window')

    def test_page_only_and_negative_without_valid_tail(self):
        prefix = ARM + 'wasm--compile_only/' + NATIVE
        for suffix in ('events.jsonl', 'ready.json', 'armed.json', 'sealed.json'):
            with self.subTest(suffix=suffix):
                data = dict(self.original)
                data.pop(prefix + suffix)
                self.check_bad(data, 'missing .*native-')
        data = dict(self.original)
        data[prefix + 'events.jsonl'] = data[prefix + 'events.jsonl'].rstrip(b'\n')
        self.check_bad(data, 'missing original writer newline')
        for changes in ({'complete': False}, {'childSent': 1}, {'accepted': 1},
                        {'drops': dict(v.DROPS, io=1)}, {'drops': {}}, {'drops': dict(v.DROPS, protocol=False)}):
            with self.subTest(changes=changes):
                data = dict(self.original)
                change(data, prefix + 'sealed.json', **changes)
                self.check_bad(data, 'negative tail')

    def test_duplicate_original_case_cannot_substitute(self):
        data = dict(self.original)
        skip, normal = ARM + 'jscall--skip/', ARM + 'jscall--normal/'
        for fname in v.ORIGINALS:
            # The criteria use normal then skip. Both are enabled; duplicate
            # matched scopes are detected before checking page receipt contents.
            data[skip + 'native/' + fname] = data[normal + 'native/' + fname]
        self.check_bad(data, 'duplicate candidate/witness run id')

    def test_design_packet_must_keep_original_bytes(self):
        data = dict(self.original)
        path = 'intake-002/arm64-http/cases/cache_hit/workload/source.bin'
        data[path] = b' ' + data[path]
        self.check_bad(data, 'packet resserialized page or peer original')
        data = dict(self.original)
        path = 'intake-002/arm64-http/cases/cache_hit/native/original.bin'
        data[path] += data[path]
        self.check_bad(data, 'packet duplicates or reserializes native originals')

    def test_scope_cannot_be_widened_or_reserialized(self):
        data = dict(self.original)
        config = 'candidate-002-scopes/arm64/jscall--normal/native-config.json'
        ctrls = 'candidate-002-scopes/arm64/jscall--normal/controls.json'
        index = 'candidate-002-scopes/index.json'
        change(data, config, jsStartLine=14)
        self.check_bad(data, 'scope index original hashes')
        scope = v.object_at(data[index])
        scope['scopes']['arm64']['jscall--normal'] = dict(config_sha256=v.sha(data[config]),
                                                         controls_sha256=v.sha(data[ctrls]))
        data[index] = v.canonical(scope)
        self.check_bad(data, 'selected native config differs')

    def test_cache_and_foreign_caller_use_raw_independent_witness(self):
        data = dict(self.original)
        change(data, ARM + 'http--cache_hit/peer.json', pre_measure_http=[])
        self.check_bad(data, 'independent server prewarm')
        data = dict(self.original)
        change(data, ARM + 'http--other_origin/peer.json', documents_ready=['primary'])
        self.check_bad(data, 'peer completion, second document')
        data = dict(self.original)
        change(data, ARM + 'http--other_origin/page.json', ack_role='primary')
        self.check_bad(data, 'independent page workload or caller role')

    def test_native_metadata_allowlist_and_paired_redirect(self):
        for case, patch in (
            ('http--redirect', {'chain': 2}), ('wasm--call_export', {'moduleId': 2}),
            ('jscall--normal', {'arguments': [39, 3]}), ('jscall--normal', {'seq': 1}),
        ):
            with self.subTest(case=case, patch=patch):
                data = dict(self.original)
                path = ARM + case + '/' + NATIVE + 'events.jsonl'
                rows = v.jsonl(data[path])
                rows[2].update(patch)
                data[path] = b''.join(map(v.canonical, rows))
                self.check_bad(data, 'native row order, pairing, metadata allowlist')

    def test_ws_unsupported_is_not_completed_zero(self):
        data = dict(self.original)
        change(data, 'runtime/amd64/smoke-009/run/native-sealed.json',
               status='ok', complete=True, childSent=0)
        self.check_bad(data, 'negative tail')

    def test_duplicate_json_and_zip_entries(self):
        with self.assertRaisesRegex(ValueError, 'duplicate JSON field'):
            v.object_at(b'{"schema":1,"schema":1}')
        with tempfile.TemporaryDirectory() as tmp, warnings.catch_warnings():
            warnings.simplefilter('ignore', UserWarning)
            path = Path(tmp) / 'duplicated.zip'
            with zipfile.ZipFile(path, 'w') as z:
                f = zipfile.ZipInfo('member-sha256.json')
                f.create_system = 3
                f.external_attr = (stat.S_IFREG | 0o644) << 16
                z.writestr(f, b'{"x":1}')
                z.writestr(f, b'{"x":1}')
            with self.assertRaisesRegex(ValueError, 'duplicate or nonregular'):
                v.read_evidence(path)

    def test_rehashed_reserialization_never_replaces_fixed_originals(self):
        restored = dict(self.original)
        name = ARM + 'jscall--normal/' + NATIVE + 'events.jsonl'
        restored[name] = b''.join(v.canonical(x) for x in v.jsonl(restored[name]))
        self.assertNotEqual(restored[name], self.original[name])
        restored['member-sha256.json'] = v.canonical({k: v.sha(b) for k, b in restored.items()})
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'reserialized.zip'
            with zipfile.ZipFile(path, 'w') as z:
                for k, b in restored.items():
                    i = zipfile.ZipInfo(k)
                    i.create_system = 3
                    i.external_attr = (stat.S_IFREG | 0o644) << 16
                    z.writestr(i, b, compress_type=zipfile.ZIP_DEFLATED)
            result = subprocess.run([sys.executable, '-B', str(VERIFIER), '--bundle', str(path)],
                                    capture_output=True, check=False)
            self.assertEqual(result.returncode, 1)
            report = json.loads(result.stdout)
            self.assertFalse(report['product_qualified'])
            self.assertIn('wrong fixed evidence digest', report['reason'])

    def test_small_standin_is_not_candidate_archive(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'fake.docker.tar.gz'
            path.write_bytes(b'archive proof is not the archive')
            with self.assertRaisesRegex(ValueError, 'wrong candidate archive file size/type'):
                v.verify_archive_bytes(path, 'amd64')


if __name__ == '__main__':
    unittest.main()
