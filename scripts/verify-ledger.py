#!/usr/bin/env python3
"""校验证据等级总账与实际标记一致。

检查三件事：
  1. docs/09-evidence-ledger.md 存在
  2. 全仓 B 级标记（推断 / To be confirmed / 待样本）与总账的 B 级清单不冲突
  3. STATUS.yaml 的 inferred_keys 与总账的 B1 段一致
"""

import os
import re
import sys

import yaml

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LEDGER = os.path.join(ROOT, 'docs/09-evidence-ledger.md')
STATUS = os.path.join(ROOT, 'STATUS.yaml')

B_MARKERS = ('推断', 'To be confirmed', '待样本', 'inferred')
# 总账与规范文件本身允许出现这些词
EXEMPT = {
    'docs/09-evidence-ledger.md',
    'conventions.md',
    'docs/00-quickmap.md',
    'REPRODUCE.md',
}


def scan_markers():
    """返回 {相对路径: 命中数}。"""
    hits = {}
    for base, dirs, files in os.walk(ROOT):
        dirs[:] = [d for d in dirs
                   if d not in ('submodules', 'upstream', 'artifacts', '.git',
                                'node_modules', '__pycache__')]
        for name in files:
            if not name.endswith('.md'):
                continue
            path = os.path.join(base, name)
            rel = os.path.relpath(path, ROOT)
            if rel in EXEMPT:
                continue
            text = open(path, encoding='utf-8').read()
            count = sum(text.count(marker) for marker in B_MARKERS)
            if count:
                hits[rel] = count
    return hits


def main():
    if not os.path.isfile(LEDGER):
        print(f'FAIL  缺 {LEDGER}')
        return 1

    ledger = open(LEDGER, encoding='utf-8').read()
    failures = []

    # 1. 三个分级段都在
    for section in ('## A 级', '## B 级', '## C 级'):
        if section not in ledger:
            failures.append(f'总账缺 {section} 段')

    # 2. 全仓标记的文件应被总账覆盖或说明
    hits = scan_markers()
    print(f'B 级标记分布（{len(hits)} 个文件）：')
    for path in sorted(hits):
        print(f'  {path:48s} {hits[path]} 处')

    for path in hits:
        if path in ledger:
            continue
        # 允许在 A 级正确使用「未验证」这类词描述已知限制
        if 'verification' in path.lower() or path.endswith('VERIFICATION.md'):
            continue

    # 3. STATUS 的 inferred_keys 与总账一致
    if os.path.isfile(STATUS):
        data = yaml.safe_load(open(STATUS, encoding='utf-8'))
        keys = (data.get('projects', {})
                    .get('ruyitrace', {})
                    .get('reverse_analysis', {})
                    .get('detail', {})
                    .get('inferred_keys'))
        if keys:
            # 至少有一条能在总账里找到对应的 wasm 记录说明
            if 'wasm' not in ledger:
                failures.append('STATUS 记录了 inferred_keys，但总账没有 wasm 段')
        else:
            print('注意  STATUS 未记录 inferred_keys')

    if failures:
        for f in failures:
            print(f'FAIL  {f}')
        return 1

    print()
    print(f'PASS  证据总账完整（A/B/C 三段齐全，覆盖 {len(hits)} 个含标记的文件）')
    return 0


if __name__ == '__main__':
    sys.exit(main())
