#!/usr/bin/env python3
"""从 switches.js + domtrace anchors 生成 domtrace-switchlist.h。

唯一真相源：console/shared/switches.js（74 条）
二进制证据：artifacts/analysis/domtrace/switches.json（RVA + getenv 调用点）

用法:
  python3 scripts/contract-gen.py \
    --js submodules/ruyitrace/console/shared/switches.js \
    --anchors artifacts/analysis/domtrace/switches.json \
    --out submodules/ruyitrace/domtrace/config/domtrace-switchlist.h
"""

import argparse
import datetime
import json
import os
import re
import sys

# switches.js 里 kind 的枚举，与 C++ 侧一一对应
KIND_ENUM = {
    'bool': 'Bool',
    'tristate': 'Tristate',
    'default_on': 'DefaultOn',
    'enum': 'Enum',
    'enum_free': 'EnumFree',
    'int': 'Int',
    'path': 'Path',
    'dir': 'Dir',
    'csv': 'Csv',
    'text': 'Text',
}

ENTRY_RE = re.compile(
    r"\{\s*env:\s*'([A-Z0-9_]+)',\s*group:\s*'([^']+)',\s*kind:\s*'([a-z_]+)'(.*?)\},?\s*(?:\n|$)",
    re.S,
)


def parse_switches(path):
    text = open(path, encoding='utf-8').read()
    entries = []
    for match in ENTRY_RE.finditer(text):
        env, group, kind, rest = match.groups()
        default = re.search(r"default:\s*'([^']*)'", rest)
        placeholder = re.search(r"placeholder:\s*'([^']*)'", rest)
        note = re.search(r"note:\s*'((?:[^'\\]|\\.)*)'", rest)
        hidden = 'hidden: true' in rest
        entries.append({
            'env': env,
            'group': group,
            'kind': kind,
            'default': default.group(1) if default else '',
            'placeholder': placeholder.group(1) if placeholder else '',
            'note': (note.group(1) if note else '').replace("\\'", "'"),
            'hidden': hidden,
        })
    return entries


def c_escape(value):
    return value.replace('\\', '\\\\').replace('"', '\\"')


def extract_range(note):
    """从 note 抽区间：优先 '范围 A-B' / 'A-B' / 'A..B'，取第一个命中。"""
    patterns = [
        r'范围\s*(\d+)\s*[-~到\.]{1,3}\s*(\d+)',
        r'(\d+)\s*[-~]\s*(\d+)\s*[，,、]',
        r'区间\s*(\d+)\s*[-~到\.]{1,3}\s*(\d+)',
        r'(\d+)\s*-\s*(\d+)',
    ]
    for pattern in patterns:
        m = re.search(pattern, note)
        if m:
            return f'{m.group(1)}-{m.group(2)}'
    return ''


def extract_depends(note):
    """抽前置开关：'需 X 已启用' / '需 X 或 Y 已启用' / '需核心已启用'。

    核心 = MOZ_DOM_TRACE。返回逗号分隔的 env 名列表，空串表示无前置。
    """
    m = re.search(r'需\s*([^·。]+?)\s*已启用', note)
    if not m:
        return ''
    raw = m.group(1)
    tokens = re.findall(r'[A-Z][A-Z0-9_]{3,}', raw)
    if '核心' in raw and 'MOZ_DOM_TRACE' not in tokens:
        tokens.insert(0, 'MOZ_DOM_TRACE')
    if 'IDB_VALUE' in raw:
        for name in ('MOZ_DOM_IDB_VALUE', 'MOZ_DOM_IDB_READ_VALUE'):
            if name not in tokens:
                tokens.append(name)
    if 'JSCall' in raw or 'jscall' in raw:
        tail = re.findall(r'MOZ_DOM_JSCALL_[A-Z_]+', raw)
        for name in tail:
            if name not in tokens:
                tokens.append(name)
    # DOMTRACE 缩写 → 完整 env 名
    ALIAS = {
        'TRACE': 'MOZ_DOM_TRACE',
        'SNAPSHOT': 'MOZ_DOM_TRACE_SNAPSHOT',
        'TIMERS': 'MOZ_DOM_TRACE_TIMERS',
        'IDB_VALUE': 'MOZ_DOM_IDB_VALUE',
        'IDB_READ_VALUE': 'MOZ_DOM_IDB_READ_VALUE',
        'JSCALL_TRACE': 'MOZ_DOM_JSCALL_TRACE',
        'EVENT_TRACE_FULL': 'MOZ_DOM_EVENT_TRACE_FULL',
        'HTTP_PACKET_TRACE': 'MOZ_DOM_HTTP_PACKET_TRACE',
        'WS_TRACE': 'MOZ_DOM_WS_TRACE',
        'EXCEPTION_TRACE': 'MOZ_DOM_EXCEPTION_TRACE',
        'ABSENT_PROBE': 'MOZ_DOM_ABSENT_PROBE',
        'HOST_MUTATION': 'MOZ_DOM_HOST_MUTATION',
        'IFACE_PROBE': 'MOZ_DOM_IFACE_PROBE',
        'ENV_INVENTORY': 'MOZ_DOM_ENV_INVENTORY',
        'WASM_CALL': 'MOZ_DOM_WASM_CALL',
        'WASM_INSN': 'MOZ_DOM_WASM_INSN',
        'WASM_DUMP': 'MOZ_DOM_WASM_DUMP',
        'TRACE_GATE': 'MOZ_DOM_TRACE_GATE',
        'TRACE_UNFILTER': 'MOZ_DOM_TRACE_UNFILTER',
        'API_OVERRIDE': 'MOZ_DOM_API_OVERRIDE',
        'TRACE_TIMERS': 'MOZ_DOM_TRACE_TIMERS',
        'TRACE_SNAPSHOT': 'MOZ_DOM_TRACE_SNAPSHOT',
        'TRACE_BUILTIN_ERROR': 'MOZ_DOM_TRACE_BUILTIN_ERROR',
        'JSCALL_OBJECT_FUNCS': 'MOZ_DOM_JSCALL_OBJECT_FUNCS',
    }
    seen = []
    for token in tokens:
        full = ALIAS.get(token, token)
        if full.startswith('MOZ_DOM_') and full not in seen:
            seen.append(full)
    return ','.join(seen)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--js', required=True)
    ap.add_argument('--anchors', required=True)
    ap.add_argument('--out', required=True)
    args = ap.parse_args()

    switches = parse_switches(args.js)
    anchors = {e['env']: e for e in json.load(open(args.anchors, encoding='utf-8'))['switches']}

    unknown_kind = {s['kind'] for s in switches} - set(KIND_ENUM)
    if unknown_kind:
        print(f'未知 kind: {unknown_kind}', file=sys.stderr)
        return 2

    only_js = [s['env'] for s in switches if s['env'] not in anchors]
    only_bin = [e for e in anchors if e not in {s['env'] for s in switches}]
    if only_js:
        print(f'switches.js 有但二进制无锚点: {only_js}', file=sys.stderr)
    if only_bin:
        print(f'二进制有但 switches.js 无: {only_bin}', file=sys.stderr)

    lines = []
    lines.append('// 由 scripts/contract-gen.py 生成 —— 请勿手改')
    lines.append(f'// 生成时间: {datetime.datetime.now().isoformat(timespec="seconds")}')
    lines.append(f'// 真相源:   {os.path.basename(args.js)}（{len(switches)} 条）')
    lines.append(f'// 证据:     {os.path.basename(args.anchors)}（{len(anchors)} 条锚点）')
    lines.append('')
    lines.append('#ifndef DOMTRACE_SWITCHLIST_H_')
    lines.append('#define DOMTRACE_SWITCHLIST_H_')
    lines.append('')
    lines.append('#include <cstdint>')
    lines.append('')
    lines.append('namespace mozilla::dom::domtrace {')
    lines.append('')
    lines.append('enum class SwitchKind : uint8_t {')
    for index, name in enumerate(KIND_ENUM.values()):
        comma = ',' if index < len(KIND_ENUM) - 1 else ','
        lines.append(f'  {name}{comma}')
    lines.append('};')
    lines.append('')
    lines.append('struct SwitchSpec {')
    lines.append('  const char* env;        // 环境变量名')
    lines.append('  const char* group;      // UI 分组')
    lines.append('  SwitchKind  kind;')
    lines.append('  const char* defaultValue;')
    lines.append('  const char* range;      // 空串表示无显式区间')
    lines.append('  const char* dependsOn;  // 空串表示无前置')
    lines.append('  const char* note;')
    lines.append('  uint64_t    stringRva;     // xul.dll 中字符串 RVA')
    lines.append('  uint64_t    getenvCallRva; // 读取点（call getenv）')
    lines.append('  bool        hidden;')
    lines.append('};')
    lines.append('')
    lines.append(f'inline constexpr uint32_t kSwitchCount = {len(switches)};')
    lines.append('')
    lines.append('inline constexpr SwitchSpec kSwitches[] = {')
    for s in switches:
        anchor = anchors.get(s['env'], {})
        rva = anchor.get('string_rva', '0x0')
        call = anchor.get('getenv_call') or '0x0'
        kind = KIND_ENUM[s['kind']]
        rng = c_escape(extract_range(s['note']))
        dep = c_escape(extract_depends(s['note']))
        lines.append(
            f'  {{"{c_escape(s["env"])}", "{c_escape(s["group"])}", SwitchKind::{kind}, '
            f'"{c_escape(s["default"])}", "{rng}", "{dep}", '
            f'"{c_escape(s["note"][:120])}", {rva}ull, {call}ull, '
            f'{"true" if s["hidden"] else "false"}}},'
        )
    lines.append('};')
    lines.append('')
    lines.append(f'static_assert(kSwitchCount == {len(switches)}, "kSwitchCount 与 kSwitches 长度不符");')
    lines.append(f'static_assert(sizeof(kSwitches) / sizeof(kSwitches[0]) == kSwitchCount, "契约不一致");')
    lines.append('')
    lines.append('}  // namespace mozilla::dom::domtrace')
    lines.append('')
    lines.append('#endif  // DOMTRACE_SWITCHLIST_H_')
    lines.append('')

    os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)
    open(args.out, 'w', encoding='utf-8').write('\n'.join(lines))
    located = sum(1 for s in switches if anchors.get(s['env'], {}).get('getenv_call'))
    print(f'生成 {args.out}')
    print(f'  开关 {len(switches)} 条，有锚点 {len(anchors)} 条，有 getenv 调用点 {located} 条')
    return 0


if __name__ == '__main__':
    sys.exit(main())
