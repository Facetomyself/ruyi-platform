#!/usr/bin/env python3
"""反汇编并按 address-names.json 标注语义名。

用法:
  python3 scripts/annotate-asm.py --start 0x18065fc15 --len 0x300
  python3 scripts/annotate-asm.py --start 0x181c69103 --out artifacts/analysis/domtrace/p5.txt
"""

import argparse
import json
import os
import sys

try:
    import capstone
    import pefile
except ImportError:
    print('需要 pefile capstone', file=sys.stderr)
    sys.exit(2)

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PE = os.path.join(ROOT, 'artifacts/binaries/ruyitrace/xul.dll')
NAMES = os.path.join(ROOT, 'artifacts/analysis/domtrace/address-names.json')
ANCHORS = os.path.join(ROOT, 'artifacts/analysis/domtrace/switches.json')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--start', required=True, help='十六进制地址，如 0x18065fc15')
    ap.add_argument('--len', default='0x200', help='字节数，默认 0x200')
    ap.add_argument('--out', help='输出文件，缺省打印到 stdout')
    ap.add_argument('--limit', type=int, default=0, help='最多输出多少条指令')
    args = ap.parse_args()

    start = int(args.start, 16)
    length = int(args.len, 16)

    pe = pefile.PE(PE, fast_load=True)
    ib = pe.OPTIONAL_HEADER.ImageBase
    raw = open(PE, 'rb').read()
    secs = {s.Name.rstrip(b'\x00').decode(): {
        'va': ib + s.VirtualAddress, 'vsize': s.Misc_VirtualSize,
        'ptr': s.PointerToRawData, 'raw': s.SizeOfRawData} for s in pe.sections}

    def read(rva, n):
        for s in secs.values():
            if s['va'] <= rva < s['va'] + s['vsize']:
                o = s['ptr'] + (rva - s['va'])
                return raw[o:o + n]
        return b''

    names = {}
    if os.path.isfile(NAMES):
        names = {int(k, 16): v for k, v in
                 json.load(open(NAMES, encoding='utf-8'))['functions'].items()}
    switch_at = {}
    if os.path.isfile(ANCHORS):
        for e in json.load(open(ANCHORS, encoding='utf-8'))['switches']:
            if e.get('getenv_call'):
                switch_at[int(e['getenv_call'], 16)] = e['env']

    md = capstone.Cs(capstone.CS_ARCH_X86, capstone.CS_MODE_64)
    md.detail = True

    lines = []
    count = 0
    for ins in md.disasm(read(start, length), start):
        note = ''
        if ins.address in switch_at:
            note = f'   ; ★ {switch_at[ins.address]}'
        elif ins.address in names:
            note = f'   ; <{names[ins.address]}>'
        # 也标注操作数里出现的已知地址
        try:
            for op in ins.operands:
                if op.type == capstone.x86.X86_OP_MEM and op.mem.disp:
                    pass
        except Exception:
            pass
        lines.append(f'{ins.address:#012x}  {ins.mnemonic:8s} {ins.op_str}{note}')
        count += 1
        if args.limit and count >= args.limit:
            break

    text = '\n'.join(lines) + '\n'
    if args.out:
        os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)
        open(args.out, 'w', encoding='utf-8').write(text)
        print(f'{count} 条指令 → {args.out}')
    else:
        sys.stdout.write(text)
    return 0


if __name__ == '__main__':
    sys.exit(main())
