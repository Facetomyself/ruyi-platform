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
    n = 0
    for base, _dirs, files in os.walk(os.path.join(ROOT, 'submodules/ruyitrace')):
        n += sum(1 for f in files if f.endswith(('.cpp', '.h')))
    return n


def count_scripts():
    d = os.path.join(ROOT, 'scripts')
    return sum(1 for f in os.listdir(d) if f.endswith(('.py', '.sh')))


def count_commits(path):
    out = subprocess.run(['git', 'log', '--oneline'], cwd=path,
                         capture_output=True, text=True)
    return len(out.stdout.strip().splitlines())


def main():
    if not os.path.isfile(TIMELINE):
        print(f'FAIL  缺 {TIMELINE}')
        return 1

    text = open(TIMELINE, encoding='utf-8').read()
    failures = []

    actual = {
        'docs': count_md(),
        'cpp': count_cpp(),
        'scripts': count_scripts(),
        'platform_commits': count_commits(ROOT),
        'ruyitrace_commits': count_commits(os.path.join(ROOT, 'submodules/ruyitrace')),
        'ruyihttp_commits': count_commits(os.path.join(ROOT, 'submodules/ruyihttp')),
        'ruyijs_commits': count_commits(os.path.join(ROOT, 'submodules/ruyijs')),
    }
    total = sum(actual[k] for k in
                ('platform_commits', 'ruyitrace_commits',
                 'ruyihttp_commits', 'ruyijs_commits'))

    checks = [
        ('文档', r'\| 文档 \| (\d+) 篇', actual['docs']),
        ('C++ 文件', r'\| C\+\+ 文件 \| (\d+) \|', actual['cpp']),
        ('校验脚本', r'\| 校验脚本 \| (\d+) \|', actual['scripts']),
        ('commit 总数', r'四个仓库共 \*{0,2}(\d+)\*{0,2} 个 commit', total),
    ]

    print('TIMELINE.md 数字核对：')
    for label, pattern, expected in checks:
        m = re.search(pattern, text)
        if not m:
            print(f'  SKIP  {label}（模式未命中）')
            continue
        declared = int(m.group(1))
        ok = declared == expected
        print(f'  {"OK  " if ok else "FAIL"} {label}: 声明 {declared}，实际 {expected}')
        if not ok:
            failures.append(f'{label}: 声明 {declared} 实际 {expected}')

    # 分仓 commit 数
    m = re.search(r'platform (\d+) / ruyitrace (\d+) / ruyihttp (\d+) / ruyijs (\d+)', text)
    if m:
        declared = list(map(int, m.groups()))
        expected = [actual['platform_commits'], actual['ruyitrace_commits'],
                    actual['ruyihttp_commits'], actual['ruyijs_commits']]
        ok = declared == expected
        print(f'  {"OK  " if ok else "FAIL"} 分仓: {declared} vs {expected}')
        if not ok:
            failures.append(f'分仓 commit 数: {declared} vs {expected}')
    else:
        print('  SKIP  分仓 commit 数（模式未命中）')

    if failures:
        for f in failures:
            print(f'FAIL  {f}')
        return 1
    print()
    print('PASS  TIMELINE.md 的统计数字与仓库实际一致')
    return 0


if __name__ == '__main__':
    sys.exit(main())
