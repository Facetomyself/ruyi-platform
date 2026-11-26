#!/usr/bin/env python3
"""Assemble a private QA-only borrowing payload from clean platform pins (not a product image)."""
import argparse
import hashlib
import json
import re
from pathlib import Path
import shutil
import subprocess


def git(repo, *args):
    return subprocess.check_output(['git', '-C', str(repo), *args])


def require(ok, description):
    if not ok:
        raise SystemExit(description)


def sha(data):
    return hashlib.sha256(data).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('platform', 'trace', 'cli', 'mcp', 'out'):
        parser.add_argument('--' + name, required=True, type=Path)
    parser.add_argument('--candidate-trace', help='optional full candidate SHA, paired with --candidate-mcp')
    parser.add_argument('--candidate-mcp', help='optional full candidate SHA, paired with --candidate-trace')
    args = parser.parse_args()
    require(bool(args.candidate_trace)==bool(args.candidate_mcp), 'candidate pair must be specified together')
    platform, trace, cli, mcp = [getattr(args, key).resolve(strict=True) for key in ('platform', 'trace', 'cli', 'mcp')]
    out = args.out.resolve()
    require(not out.exists() and out.parent.is_dir(), 'choose a new output directory')
    require(all(out != repo and repo not in out.parents for repo in (platform, trace, cli, mcp)), 'output must be outside all inputs')
    pins = {}
    for name, repo in [('ruyitrace', trace), ('ruyi-mcp', mcp)]:
        pin = git(platform, 'rev-parse', f'HEAD:submodules/{name}').decode().strip()
        expected = (args.candidate_trace if name=='ruyitrace' else args.candidate_mcp) or pin
        require(re.fullmatch(r'[a-f0-9]{40}',expected) and git(repo,'rev-parse','HEAD').decode().strip() == expected and not git(repo,'status','--porcelain'), f'expected clean {name} at {expected}')
        if expected!=pin: git(repo,'merge-base','--is-ancestor',pin,expected)
        pins[name] = expected
    build = json.loads((cli/'build-receipt.json').read_bytes())
    require(build.get('cli_inputs_dirty') is False and build.get('linux_cli_directory') is True and build.get('mcp_live_cli') is True and build['source_revision'] == pins['ruyitrace'], 'invalid standalone build receipt')
    require(build['dependency_lock_sha256'] == sha(git(trace,'show','HEAD:console/tooling/package-lock.json')), 'Trace dependency lock mismatch')
    out.mkdir(mode=0o755)
    for name, expected in build['files'].items():
        src = cli/name
        require(src.resolve(strict=True) == src and cli in src.parents and src.is_file(), 'invalid CLI inventory path')
        data = src.read_bytes()
        require(expected == {'size':len(data), 'sha256':sha(data)}, 'CLI inventory mismatch: '+name)
        if name.startswith('src/'):
            require(git(trace,'show','HEAD:console/'+name[4:]) == data, 'CLI source mismatch: '+name)
        dest = out/'cli'/name
        dest.parent.mkdir(parents=True,exist_ok=True)
        shutil.copy2(src,dest)
    shutil.copy2(cli/'build-receipt.json',out/'cli/build-receipt.json')
    # Only committed runtime inputs and the explicit public QA runners enter the payload.
    for repo, target, specs in [(mcp, 'mcp', ['build', 'contracts', 'bridge', 'package.json','package-lock.json','scripts/borrowed-behaviors-native.mjs']),
                                (trace, 'trace', ['console/cli', 'tests/linux/run_production_mcp_session.mjs'])]:
        for b in git(repo,'ls-files','-z','--',*specs).split(b'\0'):
            if not b: continue
            name = b.decode(); src = repo/name
            require(src.is_file() and src.resolve(strict=True)==src, 'unexpected linked source')
            dest = out/target/name; dest.parent.mkdir(parents=True,exist_ok=True)
            shutil.copy2(src,dest)
    deps = mcp/'node_modules'
    require(deps.is_dir(), 'install production dependencies with npm ci/prune first')
    for src in deps.rglob('*'):
        if src.is_symlink():
            require(deps in src.resolve(strict=True).parents, 'symlink leaves installed dependencies')
        elif src.is_file():
            with src.open('rb') as f:
                require(src.suffix!='.node' and f.read(4)!=b'\x7fELF','target-specific binary found; use native dependencies')
    shutil.copytree(deps,out/'mcp/node_modules',symlinks=True)
    (out/'pins.json').write_text(json.dumps({'platform':git(platform,'rev-parse','HEAD').decode().strip(),**pins},sort_keys=True)+'\n')
    rows=[]
    for file in sorted(out.rglob('*')):
        if file.is_file():
            require('\n' not in str(file) and '\\' not in str(file), 'invalid inventory path')
            rows.append(sha(file.read_bytes())+'  '+file.relative_to(out).as_posix())
    manifest=('\n'.join(rows)+'\n').encode()
    (out/'SHA256SUMS').write_bytes(manifest)
    print(json.dumps({'scope':'QA borrower (no Python browser launch)', 'pins':pins, 'files':len(rows), 'manifest_sha256':sha(manifest)}))

if __name__ == '__main__':
    main()
