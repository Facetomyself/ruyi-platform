#!/usr/bin/env python3
"""AMD64-only offline intake for completed qualify_patched.py originals; no AMD release defaults."""

import argparse
from datetime import date, datetime, timezone
from pathlib import Path

import verify as review
import verify_amd64_omni as omni

ARCH = 'linux/amd64'
BASE = 'sha256:eb73d165ea9adc15864aeb054bc90a78670618c5c0606827997d357f1cae05c6'
STOCK = 'sha256:14f2ce66295f7b041d74db4c22cf8cb24e3ea832df3f74063689e70502590d87'
BUILD = '20261123161729'
LIMIT = 131072


def original(path, limit=LIMIT):
    review.need(path.is_file() and not path.is_symlink() and path.resolve() == path.absolute(),
                'missing or nonregular original: ' + path.name)
    with path.open('rb') as stream:
        raw = stream.read(limit + 1)
    review.need(0 < len(raw) <= limit, 'original byte bound: ' + path.name)
    return raw


def input_members(args):
    root, logs = args.qualified, args.kernel_dir / 'logs'
    scope, lane, export = root / 'scope', root / 'integrated', root / 'export'
    aliases = {
        'qualified/identity.json': root / 'identity.json',
        'qualified/summary.json': root / 'summary.json',
        'qualified/offhost-archive.json': root / 'offhost/offhost-archive.json',
        'image/image.json': args.image_receipt,
        'kernel/baseline.json': args.baseline,
        'kernel/lineage.json': args.kernel_dir / 'lineage.json',
        'kernel/readback.json': args.kernel_dir / 'independent-package.json',
        'kernel/member-delta.json': args.kernel_dir / 'member-delta.json',
        'kernel/gecko-v2.patch': args.patch,
        'kernel/build.json': logs / 'candidate-package.json',
        'kernel/effective.diff': logs / 'candidate-gecko-websocket-effective.diff',
        'kernel/networking-audit.json': logs / 'candidate-archive-audit.json',
        'kernel/relinked-elf.txt': logs / 'relinked-libxul-elf.txt',
        'kernel/build.log': logs / 'candidate.log',
        'kernel/phases.log': logs / 'phases.log',
        'kernel/native-work.sh': args.native_work,
        'controls/stock-workload.json': args.stock_control,
        'scope/qa-snapshot.tar': scope / 'qa-snapshot.tar',
        'scope/index.json': scope / 'index.json',
        'lane/summary.json': lane / 'summary.json',
        'controls/unsupported/smoke.json': args.stock_smoke / 'smoke.json',
    }
    for name in ('native-events.jsonl', 'native-ready.json', 'native-sealed.json'):
        aliases[f'controls/unsupported/{name}'] = args.stock_smoke / 'run' / name
    for name in ('archive-proof.json', 'installed-package.json', 'controller.json'):
        aliases[f'export/{name}'] = export / name
    for name in review.SOURCES:
        aliases[f'source/{name}'] = args.runtime_source / (name if '/' in name else 'runtime/' + name)
    for gate, cases in review.CASES.items():
        packet = root / f'intake-{gate}'
        prefix = f'intake/amd64-{gate}'
        for name in ('candidate.json', 'intake-result.json'):
            aliases[f'{prefix}/{name}'] = packet / name
        roles = ('native', 'workload', *({'websocket': ('framePeer',), 'http': ('peer',)}.get(gate, ())))
        for case in cases:
            key = f'{gate}--{case}'
            for name in ('run.json', 'host.json', 'native-projection.json', 'page.json', 'peer.json',
                         *(f'native/{n}' for n in review.ORIGINALS)):
                aliases[f'lane/{key}/{name}'] = lane / key / name
            for name in ('native-config.json', 'controls.json'):
                aliases[f'scope/{key}/{name}'] = scope / key / name
            for role in roles:
                files = ('source.bin', 'observation.json', *(('original.bin',) if role == 'native' else ()))
                for name in files:
                    tail = f'cases/{case}/{role}/{name}'
                    aliases[f'{prefix}/{tail}'] = packet / tail
    return {name: original(path, 8 * 1024**2 if name == 'kernel/build.log' else LIMIT)
            for name, path in aliases.items()}


def index_bytes(blobs):
    return review.canonical({n: review.bytes_record(raw) for n, raw in blobs.items()})


def evidence_index(blobs):
    return review.sha(index_bytes(blobs))


def pack_originals(path, blobs):
    zipfile = review.zipfile
    with zipfile.ZipFile(path, 'x') as archive:
        for name, raw in sorted(dict(blobs, **{'original-byte-index.json': index_bytes(blobs)}).items()):
            entry = zipfile.ZipInfo(name, date_time=(2026, 11, 26, 0, 0, 0))
            entry.create_system = 3
            entry.external_attr = 0o100444 << 16
            archive.writestr(entry, raw, compress_type=zipfile.ZIP_DEFLATED, compresslevel=9)


def admission(pins):
    """The person reviewing the completed artifacts supplies these pins out of band."""
    required = {'schema', 'platform', 'image_id', 'kernel_sha256', 'kernel_bytes', 'libxul_sha256',
                'elf_build_id', 'operator_sha256', 'operator_bytes', 'runtime_source', 'source_set_sha256',
                'export_proof_sha256', 'image_receipt_sha256', 'evidence_index_sha256', 'native_omni_review_sha256',
                'capture_day_utc'}
    review.need(set(pins) == required and pins['schema'] == 'ruyitrace.patched-amd64-review-pins.v1'
                and pins['platform'] == ARCH, 'AMD review pins schema or platform mismatch')
    for name in required - {'schema', 'platform', 'image_id', 'kernel_bytes', 'operator_bytes', 'runtime_source',
                            'elf_build_id', 'capture_day_utc'}:
        review.match(pins[name], r'[a-f0-9]{64}', 'invalid or missing digest pin: ' + name)
    review.match(pins['image_id'], r'sha256:[a-f0-9]{64}', 'invalid candidate image pin')
    review.match(pins['runtime_source'], r'[a-f0-9]{40}', 'invalid source commit pin')
    review.match(pins['elf_build_id'], r'[a-f0-9]{32,64}', 'invalid GNU ELF build ID pin')
    review.match(pins['capture_day_utc'], r'[0-9]{4}-[0-9]{2}-[0-9]{2}', 'invalid UTC capture day pin')
    date.fromisoformat(pins['capture_day_utc'])
    review.same([pins['runtime_source'], pins['source_set_sha256']], [review.PRODUCT, review.SOURCE_SET],
                'AMD lane must use the same admitted runtime source bytes as ARM')
    for name in ('kernel_sha256', 'libxul_sha256', 'operator_sha256', 'export_proof_sha256', 'image_receipt_sha256',
                 'evidence_index_sha256', 'native_omni_review_sha256', 'elf_build_id'):
        review.need(int(pins[name], 16) != 0, 'empty digest pin: ' + name)
    review.need(int(pins['image_id'][7:], 16) != 0, 'empty image ID pin')
    for name, bound in (('kernel_bytes', 512 * 1024**2), ('operator_bytes', 2 * 1024**3)):
        review.need(type(pins[name]) is int and 0 < pins[name] <= bound, 'invalid artifact byte count pin: ' + name)
    review.need(pins['image_id'] not in {BASE, STOCK, review.IMAGE} and pins['kernel_sha256'] != review.KERNEL
                and pins['operator_sha256'] != review.ARCHIVE and pins['libxul_sha256'] != review.LIBXUL,
                'stock or ARM64 identity substituted for AMD64')
    return review.LanePins(arch=ARCH, machine=62, native_arch='x86_64', host='host185', elf_label='X86-64',
                           build=BUILD, product=pins['runtime_source'], base=BASE, stock_overlay=STOCK, image=pins['image_id'],
                           kernel=pins['kernel_sha256'], kernel_bytes=pins['kernel_bytes'], libxul=pins['libxul_sha256'],
                           archive=pins['operator_sha256'], archive_bytes=pins['operator_bytes'],
                           archive_proof=pins['export_proof_sha256'], image_manifest=pins['image_receipt_sha256'],
                           source_set=pins['source_set_sha256'], day=pins['capture_day_utc'],
                           native_omni_review_sha256=pins['native_omni_review_sha256'])


def utc(text):
    value = datetime.fromisoformat(text[:-1] + '+00:00' if text.endswith('Z') else text)
    review.need(value.tzinfo == timezone.utc, 'chronology must use explicit UTC')
    return value


def validate_producer(blobs, pins, verified):
    """Cross-check producer terminal receipts, never use them in place of verification."""
    obj = lambda n: review.object_at(blobs[n])
    summary = obj('qualified/summary.json')
    ident = dict(schema='ruyitrace.patched-lane-identity.v1', arch=ARCH, image_id=pins.image, build_id=BUILD,
                 source=pins.product, source_set_sha256=pins.source_set, kernel_name=pins.kernel_name,
                 kernel_sha256=pins.kernel, kernel_bytes=pins.kernel_bytes, patch_sha256=review.PATCH,
                 libxul_sha256=pins.libxul, elf_build_id=verified['libxul_elf_build_id'])
    actual = obj('qualified/identity.json')
    label = actual['export_label']
    review.match(label, r'[a-z0-9][a-z0-9-]{1,39}', 'invalid producer label')
    review.same(actual, dict(ident, export_label=label), 'producer identity differs from independent inputs')
    packets = {}
    for gate, cases in review.CASES.items():
        root = f'intake/amd64-{gate}'
        packets[gate] = dict(cases=len(cases), candidate_sha256=review.sha(blobs[f'{root}/candidate.json']),
                             intake_sha256=review.sha(blobs[f'{root}/intake-result.json']))
    review.same(summary, dict(schema='ruyitrace.patched-operator-lane.v1', identity=ident, case_count=len(review.CELLS),
                              intakes=packets, archive_name=pins.archive_name, archive_sha256=pins.archive,
                              archive_bytes=pins.archive_bytes, scope_index_sha256=review.sha(blobs['scope/index.json']),
                              transport=review.TRANSPORT,
                              scope='installed native receipts and independent bytes; separate reviewer, no physical or IME credit'),
                'producer terminal summary is incomplete or mixed')
    local, proof = obj('qualified/offhost-archive.json'), obj('export/archive-proof.json')
    review.same(local, dict(schema='ruyitrace.native-offhost-archive.v1', actual_archive_from_native_host=True,
                            archive_bytes=pins.archive_bytes, archive=pins.archive_name, archive_sha256=pins.archive,
                            platform=ARCH, image_id=pins.image, config_ids=[pins.image], repository_tags=0,
                            diffid_readback=True, gzip_crc_verified=True, offhost_readback=True,
                            native_export_proof_sha256=pins.archive_proof, rootfs_diffids=proof['rootfs_diffids'],
                            checked_utc=local['checked_utc']), 'offhost archive receipt differs from export and pins')
    completion = obj('kernel/lineage.json')['completion']
    review.match(completion, r'\S+ candidate package_verified 0 started=\S+', 'missing successful native build completion')
    ended, _, _, _, began = completion.split()
    write_windows = [obj(f'lane/{key}/run.json') for key in sorted(review.CELLS)]
    first = min(utc(run['started_utc']) for run in write_windows)
    last = max(utc(run['finished_utc']) for run in write_windows)
    review.need(utc(began.removeprefix('started=')) < utc(ended) <= first <= last <= utc(proof['utc'])
                <= utc(local['checked_utc']), 'native build, runtime, export or escrow chronology mismatch')


def verify_receipts(blobs, pins, native_omni_review):
    semantic = {n: raw for n, raw in blobs.items() if not n.startswith('qualified/')}
    out = review.verify(semantic, pins=pins, producer_intakes=True, native_omni=native_omni_review)
    validate_producer(blobs, pins, out)
    return out


def verify_amd64(blobs, raw_pins, kernel, docker, *, baseline_docker=None):
    pins = admission(raw_pins)
    index = evidence_index(blobs)
    review.same(index, raw_pins['evidence_index_sha256'], 'AMD original-byte index digest mismatch')
    for path in (kernel, docker, baseline_docker):
        review.need(path is not None and path.is_file() and not path.is_symlink(), 'actual full AMD artifact is required')
    review.need(kernel.name == pins.kernel_name and docker.name == pins.archive_name, 'full artifact basenames differ from pin')
    review.same([pins.kernel, pins.kernel_bytes], [omni.CANDIDATE_KERNEL, omni.CANDIDATE_KERNEL_BYTES],
                'native AMD omni exception is bound to a different kernel')
    source_omni, native_omni = omni.original_release_omni(baseline_docker), omni.native_omni(kernel)
    native_omni_review = omni.checked_review(source_omni, native_omni)
    del source_omni
    out = verify_receipts(blobs, pins, native_omni_review)
    native = review.object_at(blobs['kernel/readback.json'])
    review.same(out['libxul_elf_build_id'], raw_pins['elf_build_id'], 'extra GNU ELF identity pin')
    review.read_kernel_archive(kernel, native, pins=pins)
    proof = review.object_at(blobs['export/archive-proof.json'])
    operator = review.read_operator_archive(docker, proof, pins=pins, layer_path=True)
    image = review.object_at(blobs['image/image.json'])
    installed = omni.operator_omni(docker, operator['overlay_blob'], image, blobs['export/installed-package.json'])
    overlay = omni.compare_overlay(native_omni, installed, {n: blobs[f'source/{n}'] for n in review.SOURCES}, image)
    full = dict(schema='ruyitrace.patched-websocket-full-byte-review.v1', platform=ARCH, passed=True,
                evidence_index_sha256=index, installed_archive_proof_sha256=pins.archive_proof,
                native_firefox=dict(native['archive'], checked_members=len(native['members']), **native['metadata'],
                                    elf=native['packaged_libxul']), operator=operator,
                native_omni_review_sha256=pins.native_omni_review_sha256, operator_omni=overlay)
    return dict(review=out, full_bytes=full)


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    paths = ('qualified', 'kernel-dir', 'baseline', 'image-receipt', 'patch', 'native-work',
             'runtime-source', 'stock-control', 'stock-smoke')
    for name in paths:
        p.add_argument('--' + name, type=Path)
    action = p.add_mutually_exclusive_group()
    action.add_argument('--index-only', action='store_true', help='print a candidate index digest, not an acceptance result')
    action.add_argument('--pack-originals', type=Path, help='make a deterministic originals ZIP using the frozen index')
    action.add_argument('--receipt-replay', type=Path, metavar='NATIVE_OMNI_REVIEW',
                        help='replay archived receipt semantics without reopening binaries or issuing new qualification')
    p.add_argument('--zip', type=Path, help='read indexed originals from ZIP instead of the original directory paths')
    p.add_argument('--pins', type=Path, help='reviewer-frozen AMD64 pins')
    p.add_argument('--pins-sha256', help='external expected SHA-256 of original pins JSON')
    p.add_argument('--kernel-tar', type=Path)
    p.add_argument('--operator-tar', type=Path)
    p.add_argument('--baseline-docker', type=Path, help='actual original R5 CLI2 AMD64 Docker archive')
    args = p.parse_args(argv)
    supplied = [getattr(args, n.replace('-', '_')) for n in paths]
    if (args.zip and any(supplied)) or (not args.zip and not all(supplied)):
        p.error('pass either --zip or all original input paths')
    binary_review = not (args.index_only or args.pack_originals or args.receipt_replay)
    if binary_review and not (args.pins and args.pins_sha256 and args.kernel_tar and args.operator_tar and args.baseline_docker):
        p.error('AMD acceptance requires externally pinned identity and both full artifacts plus the original Docker baseline')
    if (not args.index_only or args.zip) and not (args.pins and args.pins_sha256):
        p.error('this action requires both --pins and --pins-sha256')
    try:
        raw_pins = None
        if args.pins:
            data = original(args.pins)
            review.same(review.sha(data), args.pins_sha256, 'AMD review pins SHA does not match the out-of-band pin')
            raw_pins = review.object_at(data)
            pins = admission(raw_pins)
        blobs = review.load_zip(args.zip, index_sha=raw_pins['evidence_index_sha256']) if args.zip else input_members(args)
        index = evidence_index(blobs)
        if raw_pins is not None:
            review.same(index, raw_pins['evidence_index_sha256'], 'AMD original-byte index digest mismatch')
        if args.index_only or args.pack_originals:
            if args.pack_originals:
                pack_originals(args.pack_originals, blobs)
            result = dict(originals=len(blobs), evidence_index_sha256=index)
        elif args.receipt_replay:
            result = verify_receipts(blobs, pins, review.object_at(original(args.receipt_replay)))
            review.same(result['libxul_elf_build_id'], raw_pins['elf_build_id'], 'extra GNU ELF identity pin')
            archived = (review.json.dumps(result, indent=2, sort_keys=True) + '\n').encode()
            result = dict(schema='ruyitrace.amd64-receipt-replay.v1', artifacts_reopened=False,
                          accepted_case_receipts=result['accepted_cases'], original_byte_index_sha256=index,
                          archived_case_verdict_sha256=review.sha(archived))
        else:
            result = verify_amd64(blobs, raw_pins, args.kernel_tar, args.operator_tar, baseline_docker=args.baseline_docker)
        print(review.json.dumps(result, indent=2, sort_keys=True))
    except (ValueError, KeyError, OSError, EOFError, TypeError, review.tarfile.TarError, review.zipfile.BadZipFile,
            review.struct.error) as exc:
        p.exit(1, f'AMD qualification failed: {exc}\n')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
