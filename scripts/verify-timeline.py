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

    actual = {
        'docs': count_md(),
        'cpp': count_cpp(),
        'scripts': count_scripts(),
        'platform_commits': count_commits(ROOT),
        'ruyitrace_commits': count_commits(os.path.join(ROOT, 'submodules/ruyitrace')),
        'ruyihttp_commits': count_commits(os.path.join(ROOT, 'submodules/ruyihttp')),
        'ruyijs_commits': count_commits(os.path.join(ROOT, 'submodules/ruyijs')),
        'ruyi_mcp_commits': count_commits(os.path.join(ROOT, 'submodules/ruyi-mcp')),
    }
    total = sum(value for key, value in actual.items() if key.endswith('_commits'))

    # commit 数有一个已知的循环性：更新 TIMELINE 的提交本身会让计数 +1。
    # 所以声明值允许落后 1（未提交的工作区状态）或落后 2（该更新本身又被提交）。
    checks = [
        ('文档', r'\| 文档 \| (\d+) 篇', actual['docs'], 0),
        ('C++ 文件', r'\| C\+\+ 文件 \| (\d+) \|', actual['cpp'], 0),
        ('校验脚本', r'\| 校验脚本 \| (\d+) \|', actual['scripts'], 0),
        ('commit 总数', r'五个仓库共 \*{0,2}(\d+)\*{0,2} 个 commit', total, 2),
    ]

    print('TIMELINE.md 数字核对：')
    for label, pattern, expected, tolerance in checks:
        m = re.search(pattern, text)
        if not m:
            print(f'  SKIP  {label}（模式未命中）')
            continue
        declared = int(m.group(1))
        ok = abs(declared - expected) <= tolerance
        note = f'（容差 ±{tolerance}）' if tolerance else ''
        print(f'  {"OK  " if ok else "FAIL"} {label}: 声明 {declared}，实际 {expected}{note}')
        if not ok:
            failures.append(f'{label}: 声明 {declared} 实际 {expected}')

    # 分仓 commit 数
    m = re.search(r'platform (\d+) / ruyitrace (\d+) / ruyihttp (\d+) / ruyijs (\d+) / ruyi-mcp (\d+)', text)
    if m:
        declared = list(map(int, m.groups()))
        expected = [actual['platform_commits'], actual['ruyitrace_commits'],
                    actual['ruyihttp_commits'], actual['ruyijs_commits'],
                    actual['ruyi_mcp_commits']]
        # 分仓同样允许 platform 侧落后 2（更新 TIMELINE 的提交）
        ok = (declared[1:] == expected[1:] and
              abs(declared[0] - expected[0]) <= 2)
        print(f'  {"OK  " if ok else "FAIL"} 分仓: {declared} vs {expected}'
              f'（platform 容忍 ±2）')
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
