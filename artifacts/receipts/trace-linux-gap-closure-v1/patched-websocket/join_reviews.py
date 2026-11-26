#!/usr/bin/env python3
"""Join only the four independently verified, frozen ARM64/AMD64 machine reports."""

import argparse
import json
from pathlib import Path

import verify as v

HERE = Path(__file__).resolve().parent
PINS = {
    'linux/arm64': dict(machine=183,
        review='25241a28d98136e26d215d9c05580e87aea20fad5487e374263ab42e2198a77a',
        full='d0a611a1ce6be4d8040a20f6d10b68b19b0aa992772356d995329c3bb57a2a85'),
    'linux/amd64': dict(machine=62,
        review='b6f269eaa52b32c3b064347750a24825b0dacec5a85c39ed6d1f1fd1cb470494',
        full='33ffe0f3dd12291d1e4f45585d5ece952c8b86493bf1284619a052b35f1db7e5'),
}


def join(reports):
    v.same(sorted(reports), sorted(PINS), 'need exactly the two architecture proofs')
    seen, details, sets = set(), {}, {}
    for platform, (raw, full) in sorted(reports.items()):
        expected = PINS[platform]
        v.same([v.sha(raw), v.sha(full)], [expected['review'], expected['full']], 'pre-reviewed verdict digest differs')
        r, f = map(v.object_at, (raw, full))
        v.same([r['schema'], r['status'], r['platform'], r['accepted_cases'], r['regression_cases_on_new_bytes'],
                f['schema'], f['passed'], f['platform']],
               ['ruyitrace.patched-websocket-offline-review.v1', 'qualified', platform, 22, 17,
                'ruyitrace.patched-websocket-full-byte-review.v1', True, platform], 'architecture qualification mismatch')
        v.same([r['runtime_source'], r['source_set_sha256'], r['gecko_source'], r['patch_sha256']],
               [v.PRODUCT, v.SOURCE_SET, v.GECKO, v.PATCH], 'runtime source or Gecko patch drift')
        v.same([r['native_transport'], r['websocket_positive']['native_order']],
               [v.TRANSPORT, v.WS_ORDER], 'native transport or frame observation drift')
        firefox, oci = f['native_firefox'], f['operator']
        v.same([firefox['checked_members'], firefox['elf']['machine'], firefox['sha256'], firefox['bytes'],
                firefox['elf']['sha256'], firefox['elf']['elf_build_id'], firefox['upstream_build_id'],
                oci['sha256'], oci['bytes'], oci['config'], oci['gzip_crc']],
               [56, expected['machine'], r['firefox_archive_sha256'], r['firefox_archive_bytes'],
                r['libxul_sha256'], r['libxul_elf_build_id'], r['build_id'], r['operator_archive_sha256'],
                r['operator_archive_bytes'], r['browser_image_id'], True], 'full artifacts differ from runtime review')
        v.same(sorted(r['gates']), sorted(v.CASES), 'missing gate in joined review')
        for gate, cases in v.CASES.items():
            g = r['gates'][gate]
            v.same([g['cases'], sorted(g['originals'])], [len(cases), sorted(cases)], 'joined gate case census')
            for c, n in cases.items():
                row = g['originals'][c]
                v.same(row['rows'], len(n), 'joined case row count')
                v.need(row['run_id'] not in seen, 'reused run identity across case or architecture')
                seen.add(row['run_id'])
        for k in ('build_id', 'browser_image_id', 'libxul_sha256', 'firefox_archive_sha256', 'operator_archive_sha256'):
            st = sets.setdefault(k, set())
            v.need(r[k] not in st, 'architecture-specific proof substituted: ' + k)
            st.add(r[k])
        details[platform] = dict(cases=r['accepted_cases'], regression_cases_on_new_bytes=r['regression_cases_on_new_bytes'],
                                 browser_image_id=r['browser_image_id'], build_id=r['build_id'],
                                 operator_archive_sha256=r['operator_archive_sha256'],
                                 native_firefox_sha256=r['firefox_archive_sha256'], gnu_elf_build_id=r['libxul_elf_build_id'],
                                 original_byte_index_sha256=f['evidence_index_sha256'], review_sha256=expected['review'],
                                 full_byte_review_sha256=expected['full'])
    v.same(len(seen), 44, 'incomplete cross-architecture case count')
    return dict(schema='ruyitrace.patched-websocket-two-architecture-review.v1',
                scope='approved synthetic loopback workloads on exact installed images', cases=44, gate_architecture_cells=8,
                websocket_cases=10, regression_cases_on_new_bytes=34, runtime_source=v.PRODUCT,
                gecko_source=v.GECKO, patch_sha256=v.PATCH, architectures=details)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--receipt-dir', type=Path, default=HERE)
    opts = parser.parse_args()
    try:
        reports = {arch: tuple((opts.receipt_dir / (arch.split('/')[1] + suffix)).read_bytes()
                               for suffix in ('-review.json', '-full-byte-review.json')) for arch in PINS}
        print(json.dumps(join(reports), indent=2, sort_keys=True))
    except (ValueError, KeyError, OSError) as exc:
        parser.exit(1, f'cross-architecture receipt join failed: {exc}\n')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
