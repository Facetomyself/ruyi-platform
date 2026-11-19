#!/usr/bin/env python3
"""domtrace 开关锚点提取 —— 从 xul.dll 定位 74 个 MOZ_DOM_* 的读取点。

原理：
  1. MOZ_DOM_* 字符串在 .rdata，每个只出现一次
  2. 找 lea r, [rip+disp] 指向该字符串的位置
  3. lea 之后跟 call [getenv IAT] 或 call r15（r15 预先载入 getenv）即为读取点

输出：
  artifacts/analysis/domtrace/switches.json   74 条完整锚点表

用法：
  python3 scripts/domtrace-anchors.py --pe artifacts/binaries/ruyitrace/xul.dll
"""

import argparse
import json
import os
import re
import struct
import sys

try:
    import pefile
except ImportError:
    print('需要 pefile: pip install pefile', file=sys.stderr)
    sys.exit(2)

PREFIX = b'MOZ_DOM_'
MAX_ENV_LEN = 64


def load_sections(pe, image_base):
    return {
        s.Name.rstrip(b'\x00').decode('ascii', 'replace'): {
            'va': image_base + s.VirtualAddress,
            'vsize': s.Misc_VirtualSize,
            'ptr': s.PointerToRawData,
            'raw': s.SizeOfRawData,
        }
        for s in pe.sections
    }


def find_strings(raw):
    """返回 {name: file_offset}。"""
    found = {}
    start = 0
    while True:
        index = raw.find(PREFIX, start)
        if index < 0:
            break
        end = raw.find(b'\x00', index)
        token = raw[index:end]
        if 4 < len(token) <= MAX_ENV_LEN and all(32 <= c < 127 for c in token):
            found[token.decode('ascii')] = index
        start = index + 1
    return found


def find_getenv_iat(pe, image_base):
    """返回 getenv 的 IAT 槽位 RVA。"""
    for entry in pe.DIRECTORY_ENTRY_IMPORT:
        for imp in entry.imports:
            if imp.name and imp.name.decode() == 'getenv':
                return imp.address - image_base
    return None


def scan_lea(code, code_va, targets):
    """48 8D xx disp32 → 目标 RVA。返回 {target_rva: [instruction_rva]}。"""
    hits = {}
    index = 0
    limit = len(code) - 7
    while index < limit:
        if code[index] == 0x48 and code[index + 1] == 0x8D and (code[index + 2] & 0xC7) == 0x05:
            disp = struct.unpack_from('<i', code, index + 3)[0]
            target = code_va + index + 7 + disp
            if target in targets:
                hits.setdefault(target, []).append(code_va + index)
            index += 7
        else:
            index += 1
    return hits


def scan_getenv_calls(code, code_va, iat_va):
    """FF 15 disp32 → call [rip+disp]。返回调用点 RVA 列表。"""
    calls = []
    index = 0
    limit = len(code) - 6
    while index < limit:
        if code[index] == 0xFF and code[index + 1] == 0x15:
            disp = struct.unpack_from('<i', code, index + 2)[0]
            if code_va + index + 6 + disp == iat_va:
                calls.append(code_va + index)
            index += 6
        else:
            index += 1
    return calls


REG_CALL = {
    # getenv 预载到寄存器的调用形态
    0xD7: 'r15',   # 41 FF D7
    0xD3: 'rbx',   # FF D3
    0xD6: 'rsi',   # FF D6
    0xD0: 'rax',   # FF D0
    0xD1: 'rcx',   # FF D1
    0xD2: 'rdx',   # FF D2
}


def scan_reg_calls(code, code_va):
    """call r64（getenv 预载到寄存器）。返回 [(rva, kind)]。"""
    calls = []
    index = 0
    limit = len(code) - 3
    while index < limit:
        if code[index] == 0x41 and code[index + 1] == 0xFF and code[index + 2] in REG_CALL:
            calls.append((code_va + index, REG_CALL[code[index + 2]]))
            index += 3
        elif code[index] == 0xFF and code[index + 1] in REG_CALL:
            calls.append((code_va + index, REG_CALL[code[index + 1]]))
            index += 2
        else:
            index += 1
    return calls


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--pe', required=True)
    ap.add_argument('--out', default='artifacts/analysis/domtrace/switches.json')
    args = ap.parse_args()

    pe = pefile.PE(args.pe, fast_load=True)
    pe.parse_data_directories(directories=[pefile.DIRECTORY_ENTRY['IMAGE_DIRECTORY_ENTRY_IMPORT']])
    image_base = pe.OPTIONAL_HEADER.ImageBase
    raw = open(args.pe, 'rb').read()
    sections = load_sections(pe, image_base)

    strings = find_strings(raw)
    print(f'开关字符串: {len(strings)}')

    def rva_of(offset):
        for name, sec in sections.items():
            if sec['ptr'] <= offset < sec['ptr'] + sec['raw']:
                return sec['va'] + (offset - sec['ptr']), name
        return None, None

    string_rva = {}
    for name, offset in strings.items():
        rva, section = rva_of(offset)
        string_rva[rva] = {'name': name, 'section': section, 'file_offset': offset}
    print(f'RVA 映射: {len(string_rva)}')

    text = sections['.text']
    code = raw[text['ptr']: text['ptr'] + text['vsize']]
    code_va = text['va']

    leas = scan_lea(code, code_va, set(string_rva))
    print(f'lea 引用: {sum(len(v) for v in leas.values())} 条，覆盖 {len(leas)} 个字符串')

    iat_rva = find_getenv_iat(pe, image_base)
    iat_va = image_base + iat_rva if iat_rva else None
    print(f'getenv IAT: RVA=0x{iat_rva:x}' if iat_rva else 'getenv IAT: 未找到')

    direct = sorted(scan_getenv_calls(code, code_va, iat_va)) if iat_va else []
    reg_calls = scan_reg_calls(code, code_va)
    call_kind = {addr: kind for addr, kind in reg_calls}
    for addr in direct:
        call_kind[addr] = 'direct'
    call_points = sorted(call_kind)
    kinds = {}
    for kind in call_kind.values():
        kinds[kind] = kinds.get(kind, 0) + 1
    print(f'getenv 调用点: {len(call_points)} 去重 {kinds}')

    import bisect
    result = []
    for target_rva, info in sorted(string_rva.items(), key=lambda kv: kv[1]['name']):
        entry = {
            'env': info['name'],
            'string_rva': hex(target_rva),
            'section': info['section'],
            'string_file_offset': hex(info['file_offset']),
            'lea_refs': [hex(x) for x in leas.get(target_rva, [])],
            'getenv_call': None,
            'call_kind': None,
            'gap': None,
        }
        for lea in leas.get(target_rva, []):
            idx = bisect.bisect_left(call_points, lea)
            for j in (idx, idx + 1):
                if 0 <= j < len(call_points):
                    gap = call_points[j] - lea
                    if 0 <= gap <= 16:
                        entry['getenv_call'] = hex(call_points[j])
                        entry['call_kind'] = call_kind.get(call_points[j], 'unknown')
                        entry['gap'] = gap
                        break
            if entry['getenv_call']:
                break
        result.append(entry)

    located = sum(1 for e in result if e['getenv_call'])
    print(f'读取点配对: {located}/{len(result)}')

    os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)
    payload = {
        'pe': os.path.abspath(args.pe),
        'image_base': hex(image_base),
        'getenv_iat_rva': hex(iat_rva) if iat_rva else None,
        'string_count': len(strings),
        'lea_ref_count': sum(len(v) for v in leas.values()),
        'getenv_call_sites': {k: v for k, v in kinds.items()},
        'located': located,
        'switches': result,
    }
    with open(args.out, 'w', encoding='utf-8') as fh:
        json.dump(payload, fh, ensure_ascii=False, indent=1)
    print(f'→ {args.out}')
    return 0


if __name__ == '__main__':
    sys.exit(main())
