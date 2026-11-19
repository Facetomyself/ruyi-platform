#!/usr/bin/env python3
"""校验 build runbook 引用的补丁与文件都存在，且顺序正确。"""

import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RUNBOOK = os.path.join(ROOT, 'docs/10-build-runbook.md')
PATCH_DIR = os.path.join(ROOT, 'submodules/ruyitrace/domtrace/patches')


def main():
    if not os.path.isfile(RUNBOOK):
        print(f'FAIL  缺 {RUNBOOK}')
        return 1

    text = open(RUNBOOK, encoding='utf-8').read()
    failures = []

    # runbook 里按出现顺序收集补丁名
    names = re.findall(
        r'(0001-codegen-prototype-name|0002-codegen-jitinfo-name-table|'
        r'0004-codegen-member-name-table|0005-codegen-member-range-table|'
        r'0003-bindingutils-instrument)', text)
    seen = []
    for n in names:
        if n not in seen:
            seen.append(n)

    print(f'runbook 引用的补丁（按首次出现顺序）：{len(seen)} 个')
    for n in seen:
        path = os.path.join(PATCH_DIR, f'{n}.patch')
        ok = os.path.isfile(path)
        print(f'  {"OK  " if ok else "MISS"} {n}')
        if not ok:
            failures.append(f'补丁不存在: {n}')

    # 顺序必须匹配 patches/README.md 的声明
    readme = os.path.join(PATCH_DIR, 'README.md')
    expected = ['0001', '0002', '0004', '0005', '0003']
    if os.path.isfile(readme):
        rm = open(readme, encoding='utf-8').read()
        declared = re.findall(
            r'应用顺序.*?([0-9]{4}) → ([0-9]{4}) → ([0-9]{4}) → ([0-9]{4}) → ([0-9]{4})',
            rm)
        if declared:
            got = list(declared[0])
            if got != expected:
                failures.append(f'README 声明的顺序 {got} 与预期 {expected} 不符')
            else:
                print(f'  README 声明的顺序与预期一致: {" → ".join(got)}')

    # 实际出现顺序应与声明一致
    actual = [n[:4] for n in seen]
    if actual != expected:
        failures.append(f'runbook 中的顺序 {actual} 与声明 {expected} 不符')

    if failures:
        for f in failures:
            print(f'FAIL  {f}')
        return 1
    print()
    print('PASS  runbook 引用的补丁齐全，顺序与 patches/README.md 一致')
    return 0


if __name__ == '__main__':
    sys.exit(main())
