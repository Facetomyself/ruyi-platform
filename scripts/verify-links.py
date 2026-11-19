#!/usr/bin/env python3
"""校验 Markdown 内部链接可解析。相对路径以仓库根为基准。"""

import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LINK = re.compile(r'\[([^\]]+)\]\(([^)\s]+)\)')
SKIP_PREFIX = ('http://', 'https://', 'mailto:', '#', 'tel:')
EXCLUDE_DIRS = {'submodules', 'upstream', 'artifacts', '.git', 'node_modules', '__pycache__'}


def walk_md(root):
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in EXCLUDE_DIRS]
        for name in filenames:
            if name.endswith('.md'):
                yield os.path.join(dirpath, name)


def main():
    broken = []
    total = 0
    for path in walk_md(ROOT):
        with open(path, encoding='utf-8') as fh:
            text = fh.read()
        for match in LINK.finditer(text):
            target = match.group(2)
            if target.startswith(SKIP_PREFIX):
                continue
            target = target.split('#', 1)[0]
            if not target:
                continue
            total += 1
            resolved = os.path.normpath(os.path.join(os.path.dirname(path), target))
            if not os.path.exists(resolved):
                broken.append((os.path.relpath(path, ROOT), target))

    for src, tgt in broken:
        print(f'BROKEN  {src}  ->  {tgt}')
    if broken:
        print(f'\n{len(broken)} 个失效链接（共检查 {total} 个）')
        return 1
    print(f'链接全部可解析（{total} 个）')
    return 0


if __name__ == '__main__':
    sys.exit(main())
