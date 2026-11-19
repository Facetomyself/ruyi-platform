#!/usr/bin/env python3
"""三处一致性校验：switches.js / switches.json / domtrace-switchlist.h。

任一处的开关集合与数量不同即失败。
"""

import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
JS = os.path.join(ROOT, 'submodules/ruyitrace/console/shared/switches.js')
ANCHORS = os.path.join(ROOT, 'artifacts/analysis/domtrace/switches.json')
HEADER = os.path.join(ROOT, 'submodules/ruyitrace/domtrace/config/domtrace-switchlist.h')


def from_js(path):
    text = open(path, encoding='utf-8').read()
    return set(re.findall(r"\{\s*env:\s*'([A-Z0-9_]+)'", text))


def from_anchors(path):
    data = json.load(open(path, encoding='utf-8'))
    return {e['env'] for e in data['switches']}


def from_header(path):
    text = open(path, encoding='utf-8').read()
    body = text.split('kSwitches[] = {', 1)[-1]
    return set(re.findall(r'\{"(MOZ_DOM_[A-Z0-9_]+)"', body))


def main():
    missing = [p for p in (JS, ANCHORS, HEADER) if not os.path.isfile(p)]
    if missing:
        print('缺文件:')
        for p in missing:
            print('  ', p)
        return 1

    js = from_js(JS)
    anchors = from_anchors(ANCHORS)
    header = from_header(HEADER)

    print(f'switches.js : {len(js):3d}')
    print(f'anchors.json: {len(anchors):3d}')
    print(f'switchlist.h: {len(header):3d}')

    failures = 0
    if len(js) != len(anchors) or js != anchors:
        print(f'\nJS vs anchors 差异:')
        print(f'  仅 JS 有:      {sorted(js - anchors)}')
        print(f'  仅 anchors 有: {sorted(anchors - js)}')
        failures += 1
    if len(js) != len(header) or js != header:
        print(f'\nJS vs header 差异:')
        print(f'  仅 JS 有:     {sorted(js - header)}')
        print(f'  仅 header 有: {sorted(header - js)}')
        failures += 1
    if len(js) != 74:
        print(f'\n开关数应为 74，实际 {len(js)}')
        failures += 1

    if failures:
        print(f'\n{failures} 项不一致')
        return 1
    print('\nPASS  三处一致，共 74 个开关')
    return 0


if __name__ == '__main__':
    sys.exit(main())
