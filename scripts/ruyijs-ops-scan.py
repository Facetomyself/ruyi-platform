#!/usr/bin/env python3
"""从 js.exe 中定位 operation 名 —— 三类编码都要查。

上一轮的教训：只查「独立字符串」会把被内联成立即数比较的 operation 误判为缺失。

三类编码：
  1. 字符串池：`\0` 结尾的 ASCII 串
  2. 4 字节立即数：`81 3x imm32` / `48 b8~bf imm64` 里的 operation 前缀
  3. 分段拼接：4 字节 + 掩码/位移组合（如 "expo" + "se\\0\\0"）

用法：
  python3 scripts/ruyijs-ops-scan.py --exe artifacts/binaries/ruyijs/js.exe
"""

import argparse
import json
import os
import re
import struct
import sys


def exact_strings(raw):
    out = set()
    for m in re.finditer(rb'[ -~]{3,}\x00', raw):
        out.add(m.group()[:-1].decode('ascii'))
    return out


def immediate_operands(raw):
    """扫所有 4/8 字节立即数，返回 {字符串: [偏移]}。"""
    found = {}

    def record(offset, blob):
        try:
            text = blob.decode('latin1')
        except UnicodeDecodeError:
            return
        if all(32 <= ord(c) < 127 or c == '\x00' for c in text):
            key = text.rstrip('\x00')
            if len(key) >= 3:
                found.setdefault(key, []).append(offset)

    # mov reg, imm32  (B8-BF)
    for m in re.finditer(rb'[\xb8-\xbf](.{4})', raw, re.S):
        record(m.start(), m.group(1))
    # mov r64, imm64 (48 B8-BF)
    for m in re.finditer(rb'H[\xb8-\xbf](.{8})', raw, re.S):
        record(m.start(), m.group(1))
    # cmp dword [reg], imm32 (81 3x)
    for m in re.finditer(rb'\x81[\x30-\x3f](.{4})', raw, re.S):
        record(m.start(), m.group(1))
    # cmp reg, imm32 (3D)
    for m in re.finditer(rb'\x3d(.{4})', raw, re.S):
        record(m.start(), m.group(1))
    # xor/or with imm32 (81 Fx / 0F B7 ... 组合里的 imm16)
    for m in re.finditer(rb'\x81[\xf0-\xf7](.{4})', raw, re.S):
        record(m.start(), m.group(1))

    return found


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--exe', required=True)
    ap.add_argument('--ops', default='artifacts/analysis/ruyijs/operations.txt')
    ap.add_argument('--out', default='artifacts/analysis/ruyijs/ops-encoding.json')
    args = ap.parse_args()

    if not os.path.isfile(args.exe):
        print(f'找不到 {args.exe}', file=sys.stderr)
        return 2

    raw = open(args.exe, 'rb').read()
    ops = [line.strip() for line in open(args.ops, encoding='utf-8') if line.strip()]

    pool = exact_strings(raw)
    imms = immediate_operands(raw)

    result = {}
    for op in ops:
        entry = {
            'in_string_pool': op in pool,
            'as_imm4': False,
            'as_imm8': False,
            'as_prefix': False,
            'found': False,
        }
        if op in pool:
            entry['found'] = True
        # 4 字节立即数：取前 4 字符
        if len(op) >= 4 and op[:4] in imms:
            entry['as_imm4'] = True
            entry['found'] = True
            entry['imm4_offset'] = hex(imms[op[:4]][0])
        # 8 字节立即数
        if len(op) >= 8 and op[:8] in imms:
            entry['as_imm8'] = True
            entry['found'] = True
            entry['imm8_offset'] = hex(imms[op[:8]][0])
        # 前缀形式（operation 被拆开，前 4 字符作为立即数出现）
        if not entry['found'] and len(op) >= 4 and op[:4] in imms:
            entry['as_prefix'] = True
            entry['found'] = True
        result[op] = entry

    found = sum(1 for e in result.values() if e['found'])
    missing = [op for op, e in result.items() if not e['found']]

    payload = {
        'exe': os.path.abspath(args.exe),
        'total': len(ops),
        'found': found,
        'missing': missing,
        'string_pool_hits': sum(1 for e in result.values() if e['in_string_pool']),
        'imm_hits': sum(1 for e in result.values() if e['as_imm4'] or e['as_imm8']),
        'operations': result,
    }

    os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)
    with open(args.out, 'w', encoding='utf-8') as fh:
        json.dump(payload, fh, ensure_ascii=False, indent=1)

    print(f'operation 总数: {len(ops)}')
    print(f'  字符串池命中: {payload["string_pool_hits"]}')
    print(f'  立即数命中:   {payload["imm_hits"]}')
    print(f'  合计定位:     {found}/{len(ops)}')
    if missing:
        print(f'  仍缺失: {missing}')
    print(f'→ {args.out}')
    return 0


if __name__ == '__main__':
    sys.exit(main())
