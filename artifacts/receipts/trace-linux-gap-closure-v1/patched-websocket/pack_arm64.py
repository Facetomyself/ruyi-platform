#!/usr/bin/env python3
"""Assemble a deterministic ZIP of allowlisted receipt originals; no product binaries."""

import argparse
from pathlib import Path
from zipfile import ZipFile, ZipInfo, ZIP_DEFLATED

from verify import CASES, ORIGINALS, SOURCES, canonical, bytes_record, sha, INDEX_SHA


def entries(receipts, product):
    lane, scope = 'integrated-arm64-kernelv2-01', 'scope-arm64-kernelv2-01'
    export, intake = 'export-arm64-kernelv2-01', 'intake-kernelv2'
    kl = 'kernel/aarch64/logs'
    stock = 'runtime/arm64/smoke-009'
    aliases = {
        'image/image.json': 'runtime/patched-final-001/arm64/image/image.json',
        'kernel/baseline.json': 'kernel/arm-baseline-archive-readback.json',
        'kernel/lineage.json': 'kernel/aarch64/lineage.json',
        'kernel/readback.json': 'kernel/aarch64/independent-package.json',
        'kernel/member-delta.json': 'kernel/aarch64/member-delta.json',
        'kernel/gecko-v2.patch': 'kernel/gecko159-websocket-metadata.'
                                 '3cecbf0b086ff1b630f79ce493d2c4f64782bdf96feb05a9d0a9db57fff3e45b.patch',
        'kernel/build.json': f'{kl}/candidate-package.json',
        'kernel/effective.diff': f'{kl}/candidate-gecko-websocket-effective.diff',
        'kernel/networking-audit.json': f'{kl}/candidate-archive-audit.json',
        'kernel/relinked-elf.txt': f'{kl}/relinked-libxul-elf.txt',
        'kernel/build.log': f'{kl}/candidate.log',
        'kernel/phases.log': f'{kl}/phases.log',
        'scope/qa-snapshot.tar': f'{scope}/qa-snapshot.tar',
        'scope/index.json': f'{scope}/index.json',
        'lane/summary.json': f'{lane}/summary.json',
        'intake/index.json': f'{intake}/arm64-index.json',
        'controls/stock-workload.json': 'control-arm64.json',
        'controls/unsupported/smoke.json': f'{stock}/smoke.json',
    }
    for name in ('archive-proof.json', 'installed-package.json', 'controller.json'):
        aliases[f'export/{name}'] = f'{export}/{name}'
    for name in ('native-events.jsonl', 'native-ready.json', 'native-sealed.json'):
        aliases[f'controls/unsupported/{name}'] = f'{stock}/run/{name}'
    for gate, cases in CASES.items():
        packet = f'arm64-{gate}'
        for name in ('candidate.json', 'intake-result.json'):
            aliases[f'intake/{packet}/{name}'] = f'{intake}/{packet}/{name}'
        roles = ('native', 'workload', *({'websocket': ('framePeer',), 'http': ('peer',)}.get(gate, ())))
        for case in cases:
            key = f'{gate}--{case}'
            for name in ('run.json', 'host.json', 'native-projection.json', 'page.json', 'peer.json',
                         *(f'native/{n}' for n in ORIGINALS)):
                aliases[f'lane/{key}/{name}'] = f'{lane}/{key}/{name}'
            for name in ('native-config.json', 'controls.json'):
                aliases[f'scope/{key}/{name}'] = f'{scope}/{key}/{name}'
            for role in roles:
                for name in ('source.bin', 'observation.json', *(('original.bin',) if role == 'native' else ())):
                    tail = f'{packet}/cases/{case}/{role}/{name}'
                    aliases[f'intake/{tail}'] = f'{intake}/{tail}'
    sources = {f'source/{n}': f'runtime/{n}' if '/' not in n else n for n in SOURCES}
    sources['kernel/native-work.sh'] = 'kernel/native-work.sh'
    for base, mapping in ((receipts, aliases), (product, sources)):
        for name, path in mapping.items():
            full = base / path
            if full.is_symlink() or not full.is_file() or not 0 < full.stat().st_size <= 131072:
                raise ValueError(f'expected a bounded regular original: {name}')
            yield name, full.read_bytes()


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('receipts', type=Path)
    p.add_argument('product_native_events', type=Path)
    p.add_argument('output', type=Path)
    opts = p.parse_args()
    blobs = dict(entries(opts.receipts, opts.product_native_events))
    index = canonical({name: bytes_record(raw) for name, raw in blobs.items()})
    digest = sha(index)
    if INDEX_SHA != digest:
        p.exit(1, f'original-byte index SHA mismatch: {digest}\n')
    with ZipFile(opts.output, 'x', compression=ZIP_DEFLATED, compresslevel=9) as z:
        for name, raw in sorted(dict(blobs, **{'original-byte-index.json': index}).items()):
            i = ZipInfo(name, date_time=(2026, 11, 26, 0, 0, 0))
            i.create_system = 3
            i.external_attr = 0o100444 << 16
            z.writestr(i, raw, compress_type=ZIP_DEFLATED, compresslevel=9)
    print(f'{len(blobs)} originals; original-byte index SHA-256 {digest}')


if __name__ == '__main__':
    main()
