#!/usr/bin/env bash
# 校验 PINS.md / STATUS.yaml 与实物一致。
# 退出码：0 全通过；1 有失败项。
set -uo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

fail=0
say() { printf '%-58s %s\n' "$1" "$2"; }
ok()  { say "$1" "PASS"; }
bad() { say "$1" "FAIL $2"; fail=1; }

echo "== 1. 必需文件 =="
for f in README.md PINS.md STATUS.yaml conventions.md docs/00-quickmap.md; do
  [ -f "$f" ] && ok "$f" || bad "$f" "missing"
done

echo
echo "== 2. STATUS.yaml 可解析 =="
python3 - "$ROOT/STATUS.yaml" <<'PY' || fail=1
import sys, yaml
try:
    d = yaml.safe_load(open(sys.argv[1], encoding='utf-8'))
except Exception as e:
    print(f'YAML 解析失败: {e}'); sys.exit(1)
need = {'generated_at', 'baseline', 'projects', 'artifacts', 'blockers'}
missing = need - set(d)
if missing:
    print(f'缺字段: {missing}'); sys.exit(1)
print(f'  baseline.firefox_commit = {d["baseline"]["firefox_commit"]}')
print(f'  projects = {list(d["projects"])}')
print(f'  blockers = {len(d["blockers"])}')
PY

echo
echo "== 3. Firefox 基线一致性 =="
base=$(python3 -c "import yaml;print(yaml.safe_load(open('STATUS.yaml'))['baseline']['firefox_commit'])")
for f in PINS.md docs/05-reverse-analysis.md artifacts/manifests/ruyitrace-3.5.0-win64.yaml; do
  [ -f "$f" ] || continue
  if grep -q "$base" "$f" 2>/dev/null; then
    ok "$f 含基线 $base"
  else
    say "$f 不含基线 $base" "SKIP"
  fi
done

echo
echo "== 3.5 开关三处一致性 =="
python3 scripts/verify-coverage.py || fail=1

echo
echo "== 3.6 证据等级总账 =="
python3 scripts/verify-ledger.py || fail=1

echo
echo "== 3.7 构建 runbook 一致性 =="
python3 scripts/verify-runbook.py || fail=1

echo
echo "== 3.8 TIMELINE 统计一致性 =="
python3 scripts/verify-timeline.py || fail=1

echo
echo "== 4. 文档内部链接 =="
python3 scripts/verify-links.py || fail=1

echo
echo "== 5. submodule 状态 =="
python3 - <<'PY' || fail=1
from pathlib import Path
import re
import subprocess
import sys
import yaml

path = 'submodules/ruyi-mcp'
key = f'submodule.{path}'
entry = yaml.safe_load(Path('STATUS.yaml').read_text(encoding='utf-8'))['submodules']['ruyi-mcp']

def git(*args):
    return subprocess.check_output(['git', *args], text=True).strip()

indexed = git('ls-files', '--stage', '--', path).split()
branch = git('config', '-f', '.gitmodules', '--get', f'{key}.branch')
url = git('config', '-f', '.gitmodules', '--get', f'{key}.url')
row = re.search(r'^\| ruyi-mcp \| .* \| `([^`]+)` \| `([0-9a-f]{40})` \|$',
                Path('PINS.md').read_text(encoding='utf-8'), re.M)
head = git('-C', path, 'rev-parse', 'HEAD')
valid = (len(indexed) == 4 and indexed[0] == '160000' and indexed[2] == '0' and row
         and indexed[1] == entry['commit'] == row[2] == head
         and branch == entry['branch'] == row[1] and url == entry['url'])
print(f'  ruyi-mcp gitlink / HEAD / PINS / STATUS / .gitmodules: {"PASS" if valid else "FAIL"}')
sys.exit(0 if valid else 1)
PY
python3 - <<'PY' || fail=1
import subprocess, sys
from pathlib import Path
import yaml

def git(*args):
    return subprocess.check_output(['git', *args], text=True).strip()

ok = True
pins = yaml.safe_load(Path('STATUS.yaml').read_text())['submodules']
for name, item in pins.items():
    path = 'submodules/' + name
    # A subdirectory without its own .git can resolve HEAD from its parent.
    raw = git('ls-files', '--stage', '--', path).split()
    pin = raw[1] if len(raw) == 4 and raw[0] == '160000' and raw[2] == '0' else None
    head = git('-C', path, 'rev-parse', 'HEAD') if (Path(path) / '.git').exists() else None
    good = pin is not None and pin == head == item.get('commit')
    print(f'  {name}: {"PASS" if good else "FAIL"} gitlink={pin} checkout={head} ledger={item.get("commit")}')
    ok &= good
sys.exit(0 if ok else 1)
PY

echo
echo "== 6. Trace amd64 R5 发行身份 =="
python3 -B scripts/verify-trace-release.py || fail=1

echo
echo "== 7. Trace CLI 实机证据对应源码 =="
python3 -B - <<'PY' || fail=1
from pathlib import Path, PurePosixPath
import hashlib, json, subprocess
import yaml

root = Path('submodules/ruyitrace').resolve(strict=True)
paths = yaml.safe_load(Path('STATUS.yaml').read_text())['projects']['ruyitrace']
receipt = json.loads(Path(paths['cli_native_receipt']).read_bytes())
r5 = json.loads(Path('artifacts/receipts/trace-amd64-r5/docker-save-readback.json').read_bytes())
assert receipt['passed'] is True and receipt['scope'] == 'linux-amd64-cli-native-smoke'
assert receipt['runtime_image_id'] == r5['local_image_id']
assert receipt['gate'] == {'sessions': [1, 2], 'paused_markers': 0, 'live_stop_verified': True}
assert receipt['exception'] == {'rows': 1, 'metadata_only': True}
files = receipt['runtime_modules_sha256']
assert len(files) == 14
subprocess.run(['git', '-C', root, 'merge-base', '--is-ancestor', receipt['source_commit'], 'HEAD'], check=True)
for name, expected in files.items():
    rel = PurePosixPath(name)
    assert rel.parts[0] == 'console' and '..' not in rel.parts and rel.suffix in ('.cjs', '.mjs'), name
    file = root / name
    assert file.resolve(strict=True) == file and hashlib.sha256(file.read_bytes()).hexdigest() == expected, name
print(f"PASS  Trace native CLI witness matches {len(files)} runtime modules and the R5 image")
PY

echo
if [ "$fail" -eq 0 ]; then echo "全部通过"; else echo "有失败项"; fi
exit "$fail"
