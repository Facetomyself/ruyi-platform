#!/usr/bin/env python3
"""Verify Trace R5 source inputs and receipt identity, without running a browser or extracting archives."""
import argparse
import hashlib
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RECEIPTS = ROOT / 'artifacts/receipts/trace-amd64-r5'


def digest(path):
    sha = hashlib.sha256()
    with path.open('rb') as f:
        for block in iter(lambda: f.read(1024 * 1024), b''):
            sha.update(block)
    return sha.hexdigest()


def require(test, message):
    if not test:
        raise ValueError(message)


def verify(args):
    lock = json.loads((RECEIPTS / 'source-lock.json').read_text())
    data = {}
    for name, expected in lock['receipt_sha256'].items():
        path = RECEIPTS / name
        require(digest(path) == expected, f'receipt digest mismatch: {name}')
        data[name] = json.loads(path.read_text())
    runtime = data['runtime-identity.json']
    stage = data['guarded-stage.json']
    image = data['docker-save-readback.json']
    require(stage['passed'] and stage['input_revision'] == lock['source_commit'] and
            stage['input_sha256'] == lock['frozen_source_tar_sha256'], 'source staging mismatch')
    require(runtime['audit_exit'] == 0 and image['passed'] and image['architecture'] == 'linux/amd64',
            'archive audit / architecture mismatch')
    for name in ('oci-reloaded-baseline.json', 'oci-reloaded-script-error.json'):
        row = data[name]
        require(row['passed'] and row['local_image_id'] == image['local_image_id'] and
                row['archive_sha256'] == runtime['archive_sha256'] and
                row['runtime_receipt_sha256'] == lock['receipt_sha256']['runtime-identity.json'],
                f'reloaded acceptance identity mismatch: {name}')
    require(data['oci-reloaded-script-error.json']['exception_rows_by_case'] ==
            {'off': 0, 'opt-out': 0, 'wrong-origin': 0, 'gate-closed': 0, 'on': 1},
            'exception acceptance counts mismatch')
    print(f"OK {len(data)} receipts, BuildID {runtime['installed']['build_id']}, image {image['local_image_id']}")
    if args.source:
        repo = args.source.resolve()
        head = subprocess.check_output(['git', '-C', repo, 'rev-parse', 'HEAD'], text=True).strip()
        require(head == lock['source_commit'], f"wrong source HEAD: {head}; expected {lock['source_commit']}")
        require(not subprocess.check_output(['git', '-C', repo, 'status', '--porcelain', '--untracked-files=all']),
                'source checkout has local changes; verify a separate clean clone')
        for name, sha in lock['input_files_sha256'].items():
            require(digest(repo / name) == sha, f'frozen source input differs: {name}')
        print(f"OK clean {head}, {len(lock['input_files_sha256'])} frozen files")
    for name, path, sha in [('inputs', args.inputs, stage['input_sha256']),
                            ('package', args.package, runtime['archive_sha256']),
                            ('docker-save', args.docker_save, image['archive_sha256'])]:
        if path is not None:
            require(digest(path) == sha, f'{name} digest mismatch')
            print(f'OK {name} {sha}')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, help='separate clean checkout of the exact R5 source tag')
    for opt in ('inputs', 'package', 'docker-save'):
        parser.add_argument('--' + opt, type=Path, help='optional local archive; byte check only')
    try:
        verify(parser.parse_args())
    except (OSError, ValueError, KeyError, subprocess.CalledProcessError) as exc:
        sys.exit(f'FAIL: {exc}')
