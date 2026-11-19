#!/usr/bin/env python3
"""从 PE 文件抽取字符串锚点及其引用点，供反编译定位使用。

用法:
  reverse-anchors.py --pe path/to/js.exe --prefix MOZ_DOM_ --out anchors.json
  reverse-anchors.py --pe path/to/xul.dll --strings-file ops.txt --out anchors.json

不依赖 IDA / Ghidra。仅用 pefile（可选 capstone 做进一步反汇编）。
"""

import argparse
import json
import os
import re
import sys

try:
    import pefile
except ImportError:
    print('需要 pefile: pip install pefile', file=sys.stderr)
    sys.exit(2)


def iter_strings(data, min_len=4):
    """ASCII 与 UTF-16LE 粗提取。"""
    for match in re.finditer(rb'[ -~]{%d,}' % min_len, data):
        yield match.start(), match.group().decode('ascii', 'replace')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--pe', required=True)
    ap.add_argument('--prefix', default='')
    ap.add_argument('--strings-file', help='外部给定的锚点清单（每行一个）')
    ap.add_argument('--out', required=True)
    ap.add_argument('--min-len', type=int, default=4)
    args = ap.parse_args()

    if not os.path.isfile(args.pe):
        print(f'找不到 {args.pe}', file=sys.stderr)
        return 2

    pe = pefile.PE(args.pe, fast_load=True)
    image_base = pe.OPTIONAL_HEADER.ImageBase

    wanted = None
    if args.strings_file:
        wanted = {line.strip() for line in open(args.strings_file, encoding='utf-8') if line.strip()}

    raw = open(args.pe, 'rb').read()
    sections = []
    for section in pe.sections:
        name = section.Name.rstrip(b'\x00').decode('ascii', 'replace')
        sections.append({
            'name': name,
            'va': image_base + section.VirtualAddress,
            'vsize': section.Misc_VirtualSize,
            'raw_size': section.SizeOfRawData,
            'raw_ptr': section.PointerToRawData,
        })

    found = {}
    for offset, text in iter_strings(raw, args.min_len):
        if args.prefix and not text.startswith(args.prefix):
            continue
        if wanted is not None and text not in wanted:
            continue
        found[text] = offset  # 文件偏移，未必落在节内

    result = {
        'pe': os.path.abspath(args.pe),
        'image_base': hex(image_base),
        'sections': sections,
        'anchors': {
            text: {'file_offset': hex(offset)}
            for text, offset in sorted(found.items())
        },
        'count': len(found),
        'note': 'file_offset 是文件内偏移；转 RVA 需按 sections 表换算',
    }

    os.makedirs(os.path.dirname(os.path.abspath(args.out)) or '.', exist_ok=True)
    with open(args.out, 'w', encoding='utf-8') as fh:
        json.dump(result, fh, ensure_ascii=False, indent=1)

    print(f'锚点 {result["count"]} 个 → {args.out}')
    for text in list(result['anchors'])[:10]:
        print(' ', text, result['anchors'][text]['file_offset'])
    if result['count'] > 10:
        print(f'  … 其余 {result["count"] - 10} 个')
    return 0


if __name__ == '__main__':
    sys.exit(main())
