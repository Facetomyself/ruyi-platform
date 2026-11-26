"""Reproduce the clean D receipt review and challenge its rejection paths."""

import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

ROOT = (Path(__file__).resolve().parents[1] / 'artifacts' / 'receipts' /
        'trace-linux-gap-closure-v1' / 'electron-owner')
s = importlib.util.spec_from_file_location('verify_candidate_d', ROOT / 'verify_candidate_d.py')
v = importlib.util.module_from_spec(s)
s.loader.exec_module(v)


class CandidateDTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.proof = v.source_custody(ROOT)
        cls.criteria = v.obj(v.read(ROOT / 'custody' / 'criteria.json'))['gates']['electron_owner']['cases']

    def get(self, a, case):
        return v.obj(v.read(ROOT / 'runs' / f'{a}-{case}.json'))['run']

    def validate(self, case, run, reason, a='arm64'):
        with self.assertRaisesRegex(ValueError, reason):
            v.validate_run(run, a, case, self.proof[a], self.criteria[case])

    def test_both_exact_five_case_lanes_and_machine_receipt(self):
        result = v.verify(ROOT)
        self.assertEqual(result, json.loads((ROOT / 'candidate-d-review.json').read_bytes()))
        self.assertEqual(result['verified_qa_receipts'], 10)
        self.assertFalse(result['local_raw_result_trace_rehashed'])
        self.assertFalse(result['local_binary_archive_rehashed'])
        self.assertFalse(result['product_qualified'])
        self.assertFalse(result['human_signoff'])
        self.assertEqual(result['native_originals_sha_linked_by_read_only_readback'], 10)
        self.assertIn('pending_strict_external_review', result['status'])
        for a in v.BUNDLES:
            cell = result['cells'][f'linux/{a}/installed-electron-main-single-firefox-bidi']
            cases = cell['cases']
            self.assertEqual(set(cases), set(v.MARKERS))
            self.assertEqual(sum(c['native_readback']['state'] == 'ordered_close_read_back' for c in cases.values()), 4)
            self.assertEqual(cases['browser_lost']['native_readback']['state'], 'unclean_reported')
            self.assertGreaterEqual(cases['borrower_lost']['borrower_exit_to_reborrow_ms'], 120000)
            self.assertLess(cases['paused_owner_stop']['pause_to_stop_ms'], 25000)

    def test_preliminary_c_and_wrong_architecture_rejected(self):
        case = 'borrow_return_reborrow'
        run = self.get('arm64', case)
        run['artifact']['installReceiptSha256'] = '0' * 64
        self.validate(case, run, 'historical C')
        run = self.get('amd64', case)
        run['arch'] = 'arm64'
        self.validate(case, run, 'wrong architecture')
        run['passed'] = False
        self.validate(case, run, 'failed attempt')

    def test_no_cli_owner_or_second_browser(self):
        case = 'borrow_return_reborrow'
        run = self.get('arm64', case)
        run['main']['owner_kind'] = 'cli-main'
        self.validate(case, run, 'preregistered main')
        run = self.get('arm64', case)
        run['process']['firefox_instances'] = 2
        self.validate(case, run, 'preregistered process')
        run = self.get('arm64', case)
        run['witness']['finalResult']['bidi']['sessionNew'] = 2
        self.validate(case, run, 'number of BiDi')

    def test_lost_borrower_must_expire_not_fake_release(self):
        case = 'borrower_lost'
        run = self.get('arm64', case)
        run['witness']['finalResult']['leases'].update(leasesReleased=2, leasesExpired=0)
        self.validate(case, run, 'lease release, expiry')
        run = self.get('arm64', case)
        run['process']['owner_firefox_survived'] = False
        self.validate(case, run, 'preregistered process')

    def test_denied_request_has_no_extra_page_effect(self):
        case = 'exclusive_and_stale'
        run = self.get('arm64', case)
        run['client']['expired_admin_denied'] = False
        self.validate(case, run, 'negative controls')
        run = self.get('arm64', case)
        effect = run['witness']['writers'][0]['effects'][0]
        run['witness']['writers'][0]['effects'].insert(0, dict(effect, index=effect['index'] - 1))
        self.validate(case, run, 'authorized page effects')

    def test_paused_stop_order_and_native_rdp(self):
        case = 'paused_owner_stop'
        run = self.get('arm64', case)
        run['witness']['rdp']['source'] = 'mock'
        self.validate(case, run, 'RDP pause absent')
        run = self.get('arm64', case)
        run['witness']['rdp']['ownerStopElapsedMs'] = 30000
        self.validate(case, run, 'watchdog')
        run = self.get('arm64', case)
        effects = run['witness']['writers'][0]['effects']
        effects[0]['value'], effects[1]['value'] = effects[1]['value'], effects[0]['value']
        self.validate(case, run, 'authorized page effects')

    def test_browser_kill_cannot_be_clean_flush(self):
        case = 'browser_lost'
        run = self.get('arm64', case)
        run['witness']['finalResult']['nativeOwner']['flushAcknowledged'] = True
        self.validate(case, run, 'unclean disposition')
        run = self.get('arm64', case)
        run['witness']['finalResult']['gateConfirmation'] = 'session-stopped'
        self.validate(case, run, 'gate tail claim')

    def test_timed_expiry_and_stop_require_live_chronology(self):
        case = 'borrower_lost'
        run = self.get('arm64', case)
        for call in run['witness']['mcpCalls'][3:]:
            call['startMs'] -= 2000
            call['endMs'] -= 2000
        run['witness']['borrowerLoss']['reborrowAckMs'] -= 2000
        with self.assertRaisesRegex(ValueError, 'before the production expiry window'):
            v.verify_chronology(run, case)
        case = 'paused_owner_stop'
        run = self.get('arm64', case)
        run['witness']['rdp']['pauseAckMs'] = run['witness']['adminControls'][-1]['startMs'] + 2
        with self.assertRaisesRegex(ValueError, 'pause acknowledgement'):
            v.verify_chronology(run, case)
        case = 'browser_lost'
        run = self.get('amd64', case)
        run['witness']['browserLoss']['instance_sha256'] = '1' * 64
        with self.assertRaisesRegex(ValueError, 'different instance'):
            v.verify_chronology(run, case)

    def test_original_owner_and_ordered_native_edge_are_joined(self):
        case = 'paused_owner_stop'
        name = f'arm64-{case}.json'
        run = self.get('arm64', case)
        p = v.obj(v.read(ROOT / 'readback' / name))
        p['state']['firefox_instance_sha256'] = '2' * 64
        with self.assertRaisesRegex(ValueError, 'state/owner/Firefox identity'):
            v.validate_readback(run, p, case)
        p = v.obj(v.read(ROOT / 'readback' / name))
        p['writers'][0]['selected_rows'][1]['line'] += 2
        with self.assertRaisesRegex(ValueError, 'native.*order|trace edge.*order'):
            v.validate_readback(run, p, case)
        p = v.obj(v.read(ROOT / 'readback' / name))
        p['writers'][0]['complete_tail'] = False
        with self.assertRaisesRegex(ValueError, 'complete tail'):
            v.validate_readback(run, p, case)

    def test_scoped_release_excludes_process_and_context_values(self):
        for a in v.BUNDLES:
            for c in v.MARKERS:
                for group in ('runs', 'readback'):
                    text = v.read(ROOT / group / f'{a}-{c}.json')
                    for field in (b'electronPid', b'firefoxPid', b'electronStart', b'firefoxStart', b'context_id',
                                  b'renderer_pid', b'contextId', b'"pid"', b'"generation"', b'capability',
                                  b'"startTime"', b'/root/', b'/home/ubuntu/', b'/admin-'):
                        self.assertNotIn(field, text)

    def test_retained_inputs_require_matching_originals(self):
        with self.assertRaisesRegex(ValueError, 'requires exact original QA'):
            v.verify(ROOT, raw_runs=ROOT)
        with self.assertRaisesRegex(ValueError, 'nonregular|No such file'):
            v.verify(ROOT, original_runs=ROOT)

    def test_adversarial_writer_tail_impl(self):
        # Model-only parser fixture; it adds no product evidence.
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp).resolve()
            (path / 'domtrace').mkdir()
            trace = path / 'domtrace' / 'trace_process_6.jsonl'
            run = self.get('arm64', 'borrow_return_reborrow')
            writer = run['witness']['writers'][0]
            writer.update(pid=6, generation='555', closed=3, sessionRows=4)
            for i, effect in enumerate(writer['effects'], 1):
                effect.pop('context_sha256')
                effect.update(index=i, contextId=9)
            native = run['witness']['finalResult']
            result = dict(schema=2, passed=True, exit=0, completion=native['completion'], nativeOwner=native['nativeOwner'],
                          browser=native['browserExit'], mcp=dict(native['leases'], bidi=native['bidi']),
                          gate=dict(confirmation=native['gateConfirmation'], observed='closed',
                                    writers=[dict(pid=6, startTime='555', session=1)]))
            raw = v.wire(result)
            (path / 'result.json').write_bytes(raw)
            native['sha256'] = v.sha(raw)
            original = [dict(type='session_started', session=1, pid=6),
                        *(dict(type='set', interface='Document', member='title', session=1, pid=6,
                               ctx_origin='http://127.0.0.1:8080', ctx='top', ctx_id=9, value=x)
                          for x in v.MARKERS['borrow_return_reborrow']),
                        dict(type='session_stopped', session=1, pid=6)]
            writer_raw = b''.join(map(v.wire, original))
            trace.write_bytes(writer_raw)
            writer.update(fileSha256=v.sha(writer_raw), byteLength=len(writer_raw))
            self.assertEqual(v.validate_retained('arm64', 'borrow_return_reborrow', v.wire(run), path)['state'],
                             'ordered_close_read_back')
            trace.write_bytes(writer_raw[:-1])
            with self.assertRaisesRegex(ValueError, 'native writer bytes or missing tail'):
                v.validate_retained('arm64', 'borrow_return_reborrow', v.wire(run), path)
            tampered = writer_raw + v.wire(original[1])
            trace.write_bytes(tampered)
            writer.update(fileSha256=v.sha(tampered), byteLength=len(tampered), sessionRows=5)
            with self.assertRaisesRegex(ValueError, 'post-close data'):
                v.validate_retained('arm64', 'borrow_return_reborrow', v.wire(run), path)


if __name__ == '__main__':
    unittest.main()
