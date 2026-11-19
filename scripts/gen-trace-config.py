#!/usr/bin/env python3
"""从 annotated 反汇编生成 P1+P2 的开关落位表。

前置：
  python3 scripts/annotate-asm.py --start 0x18065fbfa --len 0x1b00 --out /tmp/p1p2.asm

用法：
  python3 scripts/gen-trace-config.py --asm /tmp/p1p2.asm \
    --out submodules/ruyitrace/domtrace/config/trace-config-slots.h
"""

import argparse
import os
import re
import sys

# 31-40 的解析器判定（来自逐条反汇编人工确认）
PARSERS = {
    'MOZ_DOM_TRACE_GATE':             'Tristate',
    'MOZ_DOM_TRACE_GATE_POLL_MS':     'StrToL10',
    'MOZ_DOM_TRACE_BUILTIN_ERROR':    'StrictOne',
    'MOZ_DOM_TRACE_BUILTIN_CAP':      'StrToL10',
    'MOZ_DOM_TRACE_SITE_CAP':         'StrToL10',
    'MOZ_DOM_TRACE_MAX_STRING_CHARS': 'StrToL10',
    'MOZ_DOM_IDB_VALUE':              'StrictOne',
    'MOZ_DOM_IDB_READ_VALUE':         'StrictOne',
    'MOZ_DOM_IDB_VALUE_MAX_BYTES':    'StrToL10',
    'MOZ_DOM_TRACE_PTYPE':            'CStringCopy',
}

SWITCH_RE = re.compile(r'★\s+(MOZ_DOM_\S+)')
MOV_RE = re.compile(r'^\S+\s+mov\w*\s+(.+),\s*(\S+)\s*$')


def parse(asm_path):
    lines = open(asm_path, encoding='utf-8').read().splitlines()
    rows = []
    for index, line in enumerate(lines):
        match = SWITCH_RE.search(line)
        if not match:
            continue
        call = line.split()[0]
        dst = src = None
        if index + 1 < len(lines):
            nxt = lines[index + 1].split(';')[0].strip()
            m = MOV_RE.match(nxt)
            if m:
                dst, src = m.group(1).strip(), m.group(2).strip()
        rows.append({
            'env': match.group(1),
            'call': call,
            'dst': dst,
            'src': src,
        })
    return rows


def render(rows):
    out = []
    out.append('// P1+P2 读取落位表 —— 从 xul.dll @ 0x18065fbfa 的反汇编逐条提取')
    out.append('//')
    out.append('// 生成：scripts/gen-trace-config.py')
    out.append('// 证据：docs/analysis/p1-p2-trace-config.asm')
    out.append('')
    out.append('#ifndef DOMTRACE_TRACE_CONFIG_SLOTS_H_')
    out.append('#define DOMTRACE_TRACE_CONFIG_SLOTS_H_')
    out.append('')
    out.append('#include <cstdint>')
    out.append('')
    out.append('namespace mozilla::dom::domtrace {')
    out.append('')
    out.append('enum class EnvParse : uint8_t {')
    out.append('  RawOnly,      // 只存 char*，无内联解析')
    out.append('  Tristate,     // nullptr / 单字符 "0" → false；其余 → true')
    out.append('  StrictOne,    // 严格等于 "1"')
    out.append('  StrToL10,     // strtol 十进制')
    out.append('  CStringCopy,  // 原样拷贝（PTYPE 用 cmovne 选默认值）')
    out.append('};')
    out.append('')
    out.append('struct TraceEnvSlot {')
    out.append('  const char* env;')
    out.append('  const char* slot;    // 汇编落位：r14 / [rsp+0xb8] / ...')
    out.append('  EnvParse    parse;')
    out.append('  uint64_t    callRva; // call getenv 的地址')
    out.append('};')
    out.append('')
    out.append(f'inline constexpr uint32_t kTraceEnvSlotCount = {len(rows)};')
    out.append('')
    out.append('inline constexpr TraceEnvSlot kTraceEnvSlots[] = {')
    for row in rows:
        slot = (row['dst'] or '').replace('"', '\\"')
        parse_kind = PARSERS.get(row['env'], 'RawOnly')
        call = int(row['call'], 16)
        out.append(f'  {{"{row["env"]}", "{slot}", EnvParse::{parse_kind}, {call:#x}ull}},')
    out.append('};')
    out.append('')
    out.append('}  // namespace mozilla::dom::domtrace')
    out.append('')
    out.append('#endif  // DOMTRACE_TRACE_CONFIG_SLOTS_H_')
    out.append('')
    return '\n'.join(out)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--asm', required=True)
    ap.add_argument('--out', required=True)
    args = ap.parse_args()

    if not os.path.isfile(args.asm):
        print(f'缺反汇编文件 {args.asm}', file=sys.stderr)
        return 2

    rows = parse(args.asm)
    if len(rows) != 40:
        print(f'警告：期望 40 条，实际 {len(rows)}', file=sys.stderr)

    os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)
    open(args.out, 'w', encoding='utf-8').write(render(rows))

    from collections import Counter
    counts = Counter(PARSERS.get(r['env'], 'RawOnly') for r in rows)
    print(f'{len(rows)} 条 → {args.out}')
    for kind, n in counts.most_common():
        print(f'  {kind:12s} {n}')
    return 0


if __name__ == '__main__':
    sys.exit(main())
