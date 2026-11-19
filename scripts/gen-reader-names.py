#!/usr/bin/env python3
"""为 domtrace 读取器生成地址→符号名映射，让反汇编输出可读。

输出：
  artifacts/analysis/domtrace/address-names.json   原始映射
  artifacts/analysis/domtrace/address-names.h      C++ 常量表

用法:
  python3 scripts/gen-reader-names.py
"""

import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ANCHORS = os.path.join(ROOT, 'artifacts/analysis/domtrace/switches.json')
OUT_DIR = os.path.join(ROOT, 'artifacts/analysis/domtrace')

# 已知函数入口（反编译确定，见 docs/analysis/）
KNOWN_FUNCS = {
    0x18065fbfa: 'TraceConfigFull',
    0x18065fc15: 'TraceConfigInitGate',
    0x18563e213: 'JSCallConfigFromEnv',
    0x181c69103: 'ApiOverrideConfigFromEnv',
    0x181c69230: 'ParseNumericOverride',
    0x181c694a0: 'ParseMathRandomOverride',
    0x181c695f0: 'ParseCryptoValuesOverride',
    0x181c69930: 'ParseSequenceTail',
    0x181c69a80: 'ParseCryptoSequence',
    0x1882e60a0: 'strcmp',
    0x1882e5b80: 'memset',
    0x18000bcb0: 'strncpy_or_assign',
}

# 开关 → 符号名：MOZ_DOM_TRACE_FILE → gSwitch_TraceFile
def symbol_for(env):
    name = env[len('MOZ_DOM_'):]
    parts = [p.capitalize() for p in name.split('_')]
    return 'gSwitch_' + ''.join(parts)


def main():
    data = json.load(open(ANCHORS, encoding='utf-8'))
    names = {hex(k): v for k, v in KNOWN_FUNCS.items()}

    by_call = {}
    for entry in data['switches']:
        call = entry.get('getenv_call')
        if not call:
            continue
        by_call[call] = symbol_for(entry['env'])

    # 每个 getenv 调用点是一个「开关字段读取」，命名成 Read_<Env>
    for call, sym in by_call.items():
        names[call] = sym.replace('gSwitch_', 'Read_')

    os.makedirs(OUT_DIR, exist_ok=True)
    json.dump({'functions': names, 'switches': by_call},
              open(os.path.join(OUT_DIR, 'address-names.json'), 'w', encoding='utf-8'),
              ensure_ascii=False, indent=1)

    header = []
    header.append('// 由 scripts/gen-reader-names.py 生成 —— 请勿手改')
    header.append('// 供反汇编标注使用：地址 → 语义名')
    header.append('')
    header.append('#ifndef DOMTRACE_ADDRESS_NAMES_H_')
    header.append('#define DOMTRACE_ADDRESS_NAMES_H_')
    header.append('')
    header.append('#include <cstdint>')
    header.append('')
    header.append('namespace mozilla::dom::domtrace::names {')
    header.append('')
    header.append('struct AddressName {')
    header.append('  uint64_t    address;')
    header.append('  const char* name;')
    header.append('};')
    header.append('')
    header.append(f'inline constexpr uint32_t kAddressNameCount = {len(names)};')
    header.append('')
    header.append('inline constexpr AddressName kAddressNames[] = {')
    for addr in sorted(names, key=lambda a: int(a, 16)):
        header.append(f'  {{{addr}ull, "{names[addr]}"}},')
    header.append('};')
    header.append('')
    header.append('}  // namespace mozilla::dom::domtrace::names')
    header.append('')
    header.append('#endif  // DOMTRACE_ADDRESS_NAMES_H_')
    header.append('')

    path = os.path.join(OUT_DIR, 'address-names.h')
    open(path, 'w', encoding='utf-8').write('\n'.join(header))
    print(f'函数 {len(KNOWN_FUNCS)} 个，开关读取点 {len(by_call)} 个 → {path}')
    return 0


if __name__ == '__main__':
    sys.exit(main())
