#!/usr/bin/env python3
"""校验 artifacts/manifests/*.yaml 的结构，并在本地有实物时核对 hash。"""

import argparse
import hashlib
import os
import sys

import yaml

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MANIFEST_DIR = os.path.join(ROOT, 'artifacts', 'manifests')
BIN_DIR = os.path.join(ROOT, 'artifacts', 'binaries')

REQUIRED = ('name', 'version', 'filename', 'size', 'sha256', 'source')


def sha256(path, chunk=1 << 20):
    digest = hashlib.sha256()
    with open(path, 'rb') as fh:
        for block in iter(lambda: fh.read(chunk), b''):
            digest.update(block)
    return digest.hexdigest()


def find_local(filename):
    """返回本地实物路径；悬空符号链接视同不存在。

    artifacts/binaries/ 下允许放指向仓外的符号链接（大体积发布物不入 git）。
    链接目标被移走后 os.walk 仍会列出该名字，直接 getsize 会抛
    FileNotFoundError 中断全部核对，因此这里必须解引用后确认可读。
    """
    for dirpath, _dirnames, filenames in os.walk(BIN_DIR):
        if filename in filenames:
            candidate = os.path.join(dirpath, filename)
            if os.path.isfile(candidate):
                return candidate
            print(f'     提示：{candidate} 是悬空链接（目标已移走），按缺失处理')
    return None


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--require-local', action='store_true',
                        help='缺少任意登记原件时也以失败返回')
    args = parser.parse_args(argv)
    if not os.path.isdir(MANIFEST_DIR):
        print(f'缺目录 {MANIFEST_DIR}')
        return 1

    verified = skipped = failures = 0
    manifests = sorted(f for f in os.listdir(MANIFEST_DIR) if f.endswith('.yaml'))
    if not manifests:
        print('manifests/ 为空')
        return 1

    for name in manifests:
        path = os.path.join(MANIFEST_DIR, name)
        try:
            with open(path, encoding='utf-8') as stream:
                data = yaml.safe_load(stream)
        except Exception as error:
            print(f'FAIL  {name}: YAML 解析失败 {error}')
            failures += 1
            continue

        missing = [k for k in REQUIRED if k not in (data or {})]
        if missing:
            print(f'FAIL  {name}: 缺字段 {missing}')
            failures += 1
            continue

        local = find_local(data['filename'])
        if not local:
            skipped += 1
            print(f'SKIP  {name}: 本地无 {data["filename"]}（未核对 hash）')
            continue

        size = os.path.getsize(local)
        digest = sha256(local)
        size_ok = size == int(data['size'])
        hash_ok = digest == data['sha256']
        if size_ok and hash_ok:
            verified += 1
            print(f'PASS  {name}: {size} B  {digest[:16]}…')
        else:
            print(f'FAIL  {name}: size {size} vs {data["size"]} | sha {digest[:16]}… vs {data["sha256"][:16]}…')
            failures += 1

    print()
    print(f'{len(manifests)} 份清单：实物已核 {verified}，缺件跳过 {skipped}，失败 {failures}')
    if args.require_local and skipped:
        print('FAIL  --require-local 要求每份清单都有可核对的本地原件')
    return int(bool(failures or (args.require_local and skipped)))


if __name__ == '__main__':
    sys.exit(main())
