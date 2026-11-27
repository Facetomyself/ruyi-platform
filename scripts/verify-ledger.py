#!/usr/bin/env python3
"""Check the RuyiJS ledger and the bytes available at the requested scope."""
import argparse
import hashlib
import os
from pathlib import Path, PurePosixPath
import re
import subprocess
import sys

import yaml

PLATFORM = Path(__file__).resolve().parents[1]
ROOT_VAR = 'RUYI_PLATFORM_EVIDENCE_ROOT'
SHA256 = re.compile(r'[0-9a-f]{64}')
# Scalar metadata on the historical x86 container is not a set of child blocks.
GUARDED_METADATA = {'tool', 'path', 'observed', 'limits', 'evidence', 'evidence_sha256',
                    'cxx_stage_evidence', 'cxx_stage_evidence_sha256',
                    'intermediate_libjsrust_bytes', 'private_product'}
ROOT_HINT = f'Pass --evidence-root /absolute/path or set {ROOT_VAR} to the archive root.'


def default_root():
    # .../Ruyi/ruyi-platform and .../Ruyi/acceptance/<checkout> share the same
    # archive layout. An override selects one root, with no fallback.
    parent = PLATFORM.parent
    return parent.parent if parent.name == 'acceptance' else parent


def digest(path):
    h = hashlib.sha256()
    with path.open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b''):
            h.update(chunk)
    return h.hexdigest()


def relative_path(value, prefix=()):
    if not isinstance(value, str) or not value or '\0' in value:
        return False
    path = PurePosixPath(value)
    return (not path.is_absolute() and '..' not in path.parts and len(path.parts) > len(prefix)
            and path.as_posix() == value and path.parts[:len(prefix)] == prefix)


def mapping(value, label):
    if not isinstance(value, dict) or not value:
        raise ValueError(f'{label}: expected a non-empty mapping')
    if any(not isinstance(key, str) or not key for key in value):
        raise ValueError(f'{label}: expected non-empty string keys')
    return value


def blocks():
    data = yaml.safe_load((PLATFORM / 'STATUS.yaml').read_bytes())
    scope = mapping(data, 'STATUS.yaml')
    for key in ('projects', 'ruyijs', 'verified'):
        scope = mapping(scope.get(key), f'STATUS.yaml {key}')
    x86 = mapping(scope.get('private_linux_x86_donor_source'), 'x86 donor source')
    guarded = mapping(x86.get('guarded_build'), 'x86 guarded_build')
    records = {k: v for k, v in guarded.items() if k not in GUARDED_METADATA or isinstance(v, dict)}
    mapping(records, 'x86 guarded_build blocks')
    arm = mapping(scope.get('private_linux_aarch64_stages'), 'ARM64 stages')
    return [*records.items(), *((f'arm64/{name}', item) for name, item in arm.items())]


def secondary(block):
    return ((key, value) for key, value in block.items() if 'sha256' in key and key != 'evidence_sha256')


def metadata_errors(records):
    for name, block in records:
        try:
            mapping(block, 'block')
        except ValueError as exc:
            yield f'{name}: {exc}'
            continue
        if not relative_path(block.get('evidence')):
            yield f'{name}: evidence must be a relative archive file path'
        if 'repository_receipt' in block and not relative_path(block['repository_receipt'], ('artifacts', 'receipts')):
            yield f'{name}: repository_receipt must be a relative file path under artifacts/receipts/'
        for key, value in [('evidence_sha256', block.get('evidence_sha256')), *secondary(block)]:
            if not isinstance(value, str) or not SHA256.fullmatch(value):
                yield f'{name}: {key} is not a SHA-256 digest'


def check_repository(records, failures):
    tracked = set()
    env = dict(os.environ, GIT_ALLOW_PROTOCOL='', GIT_NO_LAZY_FETCH='1', GIT_OPTIONAL_LOCKS='0')
    raw = subprocess.check_output(['git', 'ls-files', '--stage', '-z', '--', 'artifacts/receipts/'],
                                  cwd=PLATFORM, env=env)
    for entry in raw.split(b'\0'):
        if entry:
            fields, path = entry.split(b'\t', 1)
            mode, _, stage = fields.split()
            if stage == b'0' and mode in (b'100644', b'100755'):
                tracked.add(os.fsdecode(path))
    copies = {}
    for name, block in records:
        receipt = block.get('repository_receipt')
        if receipt is None:
            continue
        copy = PLATFORM / receipt
        # Reject links on the way to the receipt before looking through them.
        if receipt not in tracked or any(p.is_symlink() for p in (*reversed(copy.parents), copy)
                                         if PLATFORM in p.parents) or not copy.is_file():
            failures.append(f'{name}: repository receipt missing or not a regular tracked parent file at {receipt}')
        elif digest(copy) != block['evidence_sha256']:
            failures.append(f'{name}: repository receipt SHA-256 differs from evidence_sha256 at {receipt}')
        else:
            copies[name] = copy
    return copies


def check_originals(root, records, copies, failures):
    # Preserve the historical external evidence digest, byte-for-byte receipt
    # equality, and secondary-hash provenance (named file, wheel, or record).
    wheels = {digest(p) for p in root.glob('deliverables/**/*.whl')}
    traceable = 0
    missing = 0
    for name, block in records:
        evidence = block['evidence']
        path = root / evidence
        blob = ''
        if not path.is_file():
            missing += 1
            failures.append(f'{name}: external evidence missing at {path}')
        else:
            raw = path.read_bytes()
            if hashlib.sha256(raw).hexdigest() != block['evidence_sha256']:
                failures.append(f'{name}: evidence hash differs from the record')
            if name in copies and copies[name].read_bytes() != raw:
                failures.append(f'{name}: receipt is not a copy of the evidence')
            blob = raw.decode(errors='replace')
        for key, value in secondary(block):
            sibling = block.get(key.replace('_sha256', ''))
            if isinstance(sibling, str) and (root / sibling).is_file() and digest(root / sibling) == value:
                traceable += 1
            elif value in wheels or value in blob:
                traceable += 1
            else:
                failures.append(f'{name}: {key} cannot be traced to any file')
    if missing:
        print(f'{missing} external evidence file(s) missing under {root}. {ROOT_HINT}')
    print(f'secondary hashes traced: {traceable}')


def report(failures):
    for item in failures:
        print(f'  FAIL {item}', file=sys.stderr)
    if failures:
        print(f'failures: {len(failures)}', file=sys.stderr)
    return int(bool(failures))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    tiers = parser.add_mutually_exclusive_group()
    tiers.add_argument('--repo', action='store_true', help='verify the ledger and tracked copies only')
    tiers.add_argument('--full', action='store_true', help='also verify external originals and secondary hashes (default)')
    parser.add_argument('--evidence-root', help=f'absolute archive path for full checks; overrides {ROOT_VAR}')
    args = parser.parse_args()
    if args.repo and args.evidence_root is not None:
        parser.error('--evidence-root only applies to full verification')
    try:
        if not args.repo:
            root = Path(args.evidence_root if args.evidence_root is not None else os.environ.get(ROOT_VAR, default_root()))
            if not root.is_absolute():
                raise ValueError(f'evidence root must be absolute. {ROOT_HINT}')
            if not root.is_dir():
                raise ValueError(f'external evidence root missing or not a directory: {root}. {ROOT_HINT}')
            print(f'JS external evidence root: {root}')
        records = blocks()
        failures = list(metadata_errors(records))
        if failures:
            return report(failures)
        copies = check_repository(records, failures)
        print(f'JS ledger blocks checked for structure: {len(records)}; repository receipt SHA-256 verified: {len(copies)}')
        if args.repo:
            external_only = sum('repository_receipt' not in block for _, block in records)
            secondary_count = sum(1 for _, block in records for _ in secondary(block))
            print(f'JS repo scope: external originals not checked ({len(records)}, including {external_only} entries '
                  f'without a repository copy); secondary hash provenance not checked ({secondary_count}).')
        else:
            check_originals(root, records, copies, failures)
            if not failures:
                print('All JS evidence present, hashes match, and repository receipts are byte-identical to originals.')
        return report(failures)
    except (ValueError, OSError, yaml.YAMLError, subprocess.CalledProcessError) as exc:
        return report([str(exc)])


if __name__ == '__main__':
    sys.exit(main())
