#!/usr/bin/env python3
"""校验 TIMELINE.md 里的统计数字与实际一致。"""

import os
import re
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TIMELINE = os.path.join(ROOT, 'TIMELINE.md')


def count_md():
    """全仓 .md，排除 submodules / upstream / artifacts 与虚拟环境目录。"""
    skip = {'submodules', 'upstream', 'artifacts', '.git',
            'node_modules', '__pycache__', 'build'}
    n = 0
    for base, dirs, files in os.walk(ROOT):
        # 只按目录名过滤，不因为路径里含 ".git" 子串就整棵剪掉
        dirs[:] = [d for d in dirs if d not in skip]
        n += sum(1 for f in files if f.endswith('.md'))
    return n


def count_cpp():
    # Count versioned sources only: a local draft or build product must not
    # change the expected inventory of a fresh recursive clone.
    files = subprocess.check_output(['git', 'ls-files', '-z'],
                                    cwd=os.path.join(ROOT, 'submodules/ruyitrace'))
    return sum(path.endswith((b'.cpp', b'.h')) for path in files.split(b'\0'))


def count_scripts():
    d = os.path.join(ROOT, 'scripts')
    return sum(1 for f in os.listdir(d) if f.endswith(('.py', '.sh')))


def count_commits(path):
    revision = 'HEAD'
    if path != ROOT:
        relative = os.path.relpath(path, ROOT)
        revision = subprocess.check_output(
            ['git', 'rev-parse', f':{relative}'], cwd=ROOT, text=True).strip()
    return int(subprocess.check_output(
        ['git', 'rev-list', '--count', revision], cwd=path, text=True))


def main():
    if not os.path.isfile(TIMELINE):
        print(f'FAIL  缺 {TIMELINE}')
        return 1

    text = open(TIMELINE, encoding='utf-8').read()
    failures = []

    actual = {'docs': count_md(), 'cpp': count_cpp(), 'scripts': count_scripts()}
    # Count the actual first-level gitlinks, not a hand-written component list.
    entries = subprocess.check_output(['git', 'ls-files', '--stage', '-z', '--', 'submodules/'], cwd=ROOT)
    counts = {'platform': count_commits(ROOT)}
    for entry in filter(None, entries.split(b'\0')):
        meta, raw_path = entry.split(b'\t', 1)
        if meta.split()[0] != b'160000':
            continue
        path = os.fsdecode(raw_path)
        name = path.removeprefix('submodules/')
        if '/' in name or name in counts or meta.split()[2] != b'0':
            sys.exit(f'FAIL  意外的一级 gitlink: {path}')
        counts[name] = count_commits(os.path.join(ROOT, path))
    total = sum(counts.values())

    # commit 数有一个已知的循环性：更新 TIMELINE 的提交本身会让计数 +1。
    # 所以声明值允许落后 1（未提交的工作区状态）或落后 2（该更新本身又被提交）。
    checks = [
        ('文档', r'\| 文档 \| (\d+) 篇', actual['docs'], 0),
        ('C++ 文件', r'\| C\+\+ 文件 \| (\d+) \|', actual['cpp'], 0),
        ('校验脚本', r'\| 校验脚本 \| (\d+) \|', actual['scripts'], 0),
        ('commit 总数', r'平台与一级子模块共 \*{0,2}(\d+) 个 commit', total, 2),
        ('commit 表格', r'\| 平台与一级子模块 commit \| (\d+) \|', total, 2),
    ]

    print('TIMELINE.md 数字核对：')
    for label, pattern, expected, tolerance in checks:
        m = re.search(pattern, text)
        if not m:
            failures.append(f'{label}: 缺少当前统计行')
            continue
        declared = int(m.group(1))
        ok = abs(declared - expected) <= tolerance
        note = f'（容差 ±{tolerance}）' if tolerance else ''
        print(f'  {"OK  " if ok else "FAIL"} {label}: 声明 {declared}，实际 {expected}{note}')
        if not ok:
            failures.append(f'{label}: 声明 {declared} 实际 {expected}')

    m = re.search(r'^平台与一级子模块共 [^\n（]*（([^；）\n]+)', text, re.M)
    if not m:
        failures.append('缺少平台与一级子模块的分仓统计')
    else:
        declared = {}
        for item in m[1].split(' / '):
            row = re.fullmatch(r'([\w-]+) (\d+)', item)
            if not row or row[1] in declared:
                failures.append(f'重复或无效的分仓统计: {item}')
                continue
            declared[row[1]] = int(row[2])
        ok = counts.keys() == declared.keys() and all(
            abs(count - declared[name]) <= (2 if name == 'platform' else 0)
            for name, count in counts.items())
        print(f'  {"OK  " if ok else "FAIL"} 分仓: {declared} vs {counts}（platform 容忍 ±2）')
        if not ok:
            failures.append('分仓 commit 数或一级仓库集合不符')

    if failures:
        for f in failures:
            print(f'FAIL  {f}')
        return 1
    print()
    print('PASS  TIMELINE.md 的统计数字与仓库实际一致')
    return 0


if __name__ == '__main__':
    sys.exit(main())
