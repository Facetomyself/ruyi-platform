#!/usr/bin/env python3
"""Cross-check the platform's staged gitlinks and checkout-independent catalog."""
import argparse
import os
from pathlib import Path
import re
import subprocess
import sys

import yaml

ROOT = Path(__file__).resolve().parents[1]
GIT_ENV = dict(os.environ, GIT_ALLOW_PROTOCOL='', GIT_NO_LAZY_FETCH='1', GIT_OPTIONAL_LOCKS='0')
SHA = re.compile(r'[0-9a-f]{40}')
GITHUB = re.compile(r'https://github\.com/([A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+)')


def require(ok, message):
    if not ok:
        raise ValueError(message)


def git(*args, cwd=ROOT):
    return subprocess.check_output(['git', *args], cwd=cwd, env=GIT_ENV)


def same_set(label, actual, expected):
    missing, extra = expected - actual, actual - expected
    require(not (missing or extra), f'{label}: missing={sorted(missing)}, unexpected={sorted(extra)}')


def read_status():
    # Check duplicate keys only in the catalog mappings; the historical ledger
    # has its own interpretation of records below the project entries.
    loader = yaml.SafeLoader((ROOT / 'STATUS.yaml').read_text(encoding='utf-8'))
    try:
        root = loader.get_single_node()

        def mapping(node, label):
            require(isinstance(node, yaml.MappingNode), f'STATUS.yaml {label}: expected mapping')
            entries = {}
            for key, value in node.value:
                require(isinstance(key, yaml.ScalarNode) and key.tag == 'tag:yaml.org,2002:str',
                        f'STATUS.yaml {label}: expected string key')
                require(key.value not in entries, f'STATUS.yaml {label}: duplicate {key.value}')
                entries[key.value] = value
            return entries

        top = mapping(root, 'root')
        required = {'generated_at', 'baseline', 'projects', 'artifacts', 'blockers', 'submodules'}
        require(required <= top.keys(), f'STATUS.yaml: missing {sorted(required - top.keys())}')
        for scope in ('projects', 'submodules'):
            for name, node in mapping(top[scope], scope).items():
                mapping(node, f'{scope}.{name}')
        return loader.construct_document(root)
    finally:
        loader.dispose()


def index_entries():
    entries = {}
    for line in git('ls-files', '--stage', '-z').decode('utf-8', errors='surrogateescape').split('\0'):
        if line:
            fields, path = line.split('\t', 1)
            mode, oid, stage = fields.split()
            entries.setdefault(path, []).append((mode, oid, stage))
    return entries


def module_config():
    modules = {}
    raw = git('config', '--no-includes', '--file', '.gitmodules', '--null', '--list')
    for record in raw.decode('utf-8').split('\0'):
        if not record:
            continue
        key, _, value = record.partition('\n')
        match = re.fullmatch(r'submodule\.(.+)\.(path|url|branch)', key)
        require(match is not None, f'.gitmodules: unsupported entry {key!r}')
        section, field = match.groups()
        fields = modules.setdefault(section, {})
        require(field not in fields, f'.gitmodules: duplicate {key}')
        require(value and value == value.strip(), f'.gitmodules: missing or malformed {key}')
        fields[field] = value
    return modules


def github_slug(url):
    match = GITHUB.fullmatch(url.removesuffix('.git')) if isinstance(url, str) else None
    return match[1] if match else None


def check_document_pin(name, registration, lines):
    prefix = rf'\|\s*{re.escape(name)}\s*\|'
    rows = [line for line in lines if re.match(prefix, line)]
    require(len(rows) == 1, f'PINS.md: expected exactly one {name} pin row')
    row = re.fullmatch(prefix + r'\s*\[([^\]]+)\]\(([^)]+)\)\s*\|\s*'
                       r'`([^`]+)`\s*\|\s*`([0-9a-f]{40})`\s*\|\s*', rows[0])
    require(row and row[1] == github_slug(registration['url']) == github_slug(row[2])
            and row[3] == registration.get('branch') and row[4] == registration['commit'],
            f'PINS.md: {name} source URL, branch or SHA differs from STATUS.yaml')


def check_catalog():
    require(Path(os.fsdecode(git('rev-parse', '--show-toplevel').rstrip(b'\n'))) == ROOT,
            'run from a platform parent checkout')
    index = index_entries()
    for name in ('STATUS.yaml', '.gitmodules', 'PINS.md'):
        entry = index.get(name, [])
        path = ROOT / name
        require(len(entry) == 1 and entry[0][0] in ('100644', '100755') and entry[0][2] == '0'
                and not path.is_symlink() and path.is_file(), f'{name}: missing regular parent file in checkout/index')
    status = read_status()
    pins = status['submodules']
    for name in ('ruyi-mcp', 'ff-ruyijs', 'ruyijs'):
        require(name in pins, f'STATUS.yaml: missing {name} submodule registration')
    expected = {f'submodules/{name}': name for name in pins}
    modules = module_config()
    same_set('.gitmodules sections vs STATUS.yaml', modules.keys(), expected.keys())
    project_paths = {name for name, project in status['projects'].items() if 'submodule' in project}
    same_set('STATUS.yaml project submodule registrations', project_paths, pins.keys())
    gitlinks = {path for path, entries in index.items() if any(e[0] == '160000' for e in entries)}
    same_set('parent gitlinks vs STATUS.yaml', gitlinks, expected.keys())

    for path, name in sorted(expected.items()):
        pin, config, project = pins[name], modules[path], status['projects'][name]
        require(re.fullmatch(r'[A-Za-z0-9_-]+', name), f'STATUS.yaml: invalid submodule name {name!r}')
        require(isinstance(pin.get('commit'), str) and SHA.fullmatch(pin['commit']),
                f'{path}: missing or invalid STATUS.yaml commit SHA')
        require(index[path] == [('160000', pin['commit'], '0')],
                f'{path}: staged gitlink mode, stage or SHA differs from STATUS.yaml ({index[path]!r})')
        require(project['submodule'] == path == config.get('path'),
                f'{path}: path differs between STATUS.yaml project and .gitmodules')
        require(pin.get('state') == 'added', f'{path}: missing added registration in STATUS.yaml')
        slug = github_slug(pin.get('url'))
        repo_field = 'repo_inner' if name == 'ruyijs' else 'repo'
        require(slug and config.get('url') == pin['url'] and project.get(repo_field) == slug,
                f'{path}: source URL differs between STATUS.yaml and .gitmodules, or is missing')
        require('branch' not in pin and 'branch' not in config
                or isinstance(pin.get('branch'), str) and pin['branch'] == config.get('branch'),
                f'{path}: branch differs between STATUS.yaml and .gitmodules, or is missing')
        require(pin.get('visibility') in ('public', 'private'),
                f'{path}: missing or invalid visibility in STATUS.yaml')
    # The public performance/portability fork and the private product must
    # remain distinct even if the YAML and .gitmodules are edited together.
    public, inner = pins['ff-ruyijs'], pins['ruyijs']
    opened = status['projects']['ff-ruyijs']
    require(github_slug(public['url']) == 'Facetomyself/ff-ruyijs' and public['visibility'] == 'public'
            and public.get('branch') == 'main' and opened.get('upstream') == 'cutetailbud/ff-ruyijs'
            and opened.get('upstream_branch') == 'main' and opened.get('private_product_source') is False,
            'ff-ruyijs: wrong public fork, upstream, branch or private-source boundary')
    require(github_slug(inner['url']) == 'Facetomyself/ruyijs-inner' and inner['visibility'] == 'private',
            'ruyijs: the private product must remain separate from ff-ruyijs')
    for field in ('upstream_integrated', 'firefox_gitlink'):
        require(isinstance(opened.get(field), str) and SHA.fullmatch(opened[field]),
                f'ff-ruyijs: invalid {field} SHA in STATUS.yaml')
    lines = (ROOT / 'PINS.md').read_text(encoding='utf-8').splitlines()
    for name in ('ruyi-mcp', 'ff-ruyijs'):
        check_document_pin(name, pins[name], lines)
    for path, name in sorted(expected.items()):
        pin = pins[name]
        print(f"  PASS {path} {pin['commit']} (recorded visibility: {pin['visibility']})")
    print(f'PASS catalog: {len(expected)} gitlinks and parent registrations; source, receipts, and tests not checked here')
    return expected, pins


def check_checkouts(expected, pins):
    failures = []
    for path, name in sorted(expected.items()):
        checkout, pin = ROOT / path, pins[name]['commit']
        try:
            require((checkout / '.git').exists(), 'submodule checkout missing (initialize the pinned submodules)')
            top = Path(os.fsdecode(git('rev-parse', '--show-toplevel', cwd=checkout).rstrip(b'\n')))
            require(top == checkout, 'expected an independent submodule checkout at the registered path')
            head = git('rev-parse', '--verify', 'HEAD^{commit}', cwd=checkout).decode('ascii').strip()
            require(head == pin, f'checkout SHA {head} differs from pinned SHA {pin}')
            require(not git('status', '--porcelain', '--untracked-files=no', '--ignore-submodules=dirty', cwd=checkout),
                    'tracked checkout files differ from the pinned commit')
            print(f'  PASS {path} checked out at {head}')
        except (ValueError, OSError, subprocess.CalledProcessError) as exc:
            failures.append(f'{path}: {exc}')
    require(not failures, '\nFAIL '.join(failures))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--checkouts', action='store_true', help='also check the local pinned submodule commits')
    args = parser.parse_args()
    try:
        expected, pins = check_catalog()
        if args.checkouts:
            check_checkouts(expected, pins)
    except (ValueError, OSError, yaml.YAMLError, subprocess.CalledProcessError) as exc:
        print(f'FAIL {exc}', file=sys.stderr)
        return 1
    return 0


if __name__ == '__main__':
    sys.exit(main())
