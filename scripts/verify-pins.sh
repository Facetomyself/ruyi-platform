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
    body = subprocess.check_output(['git', '-C', root, 'show', f"{receipt['source_commit']}:{rel}"])
    assert hashlib.sha256(body).hexdigest() == expected, name
print(f"PASS  historical Trace CLI witness matches {len(files)} exact source modules and the R5 image")
PY

echo
echo "== 8. Trace 生产 MCP 同会话 =="
python3 -B - <<'PY' || fail=1
import hashlib, json, subprocess
from pathlib import Path
import yaml

status = yaml.safe_load(Path('STATUS.yaml').read_text())
receipt_path = Path(status['projects']['ruyitrace']['mcp_production_receipt'])
receipt = json.loads(receipt_path.read_bytes())
assert receipt['schema'] == 'ruyitrace-production-mcp-delivery.v1'
for name, digest in receipt['evidence_sha256'].items():
    assert Path(name).name == name and hashlib.sha256((receipt_path.parent / name).read_bytes()).hexdigest() == digest, name

def read(name):
    return json.loads((receipt_path.parent / name).read_bytes())

def git(cwd, *args):
    return subprocess.check_output(['git', '-C', cwd, *args])

runtime = read('runtime-identity.json')
assert runtime['installed']['build_id'] == receipt['firefox_build_id'] and runtime['archive_sha256'] == receipt['firefox_archive_sha256']
for name, key in [('ruyitrace', 'trace_source'), ('ruyi-mcp', 'mcp_source')]:
    root = f'submodules/{name}'
    subprocess.run(['git','-C',root,'merge-base','--is-ancestor',receipt[key],'HEAD'],check=True)

build = read('m2-cli-build.json')
assert build['source_revision'] == receipt['trace_source'] and build['cli_inputs_dirty'] is False and build['mcp_live_cli'] is True
root = 'submodules/ruyitrace'
lock = git(root, 'show', f"{receipt['trace_source']}:console/tooling/package-lock.json")
assert hashlib.sha256(lock).hexdigest() == build['dependency_lock_sha256']
for name, signature in build['files'].items():
    if name.startswith('src/'):
        body = git(root, 'show', f"{receipt['trace_source']}:console/{name[4:]}")
        assert signature == {'size': len(body), 'sha256': hashlib.sha256(body).hexdigest()}, name
for mode, file in [('standard', 'm2-standard.json'), ('paused', 'm2-owner-stop-paused.json')]:
    case = read(file)
    assert case['passed'] and len(case['checks']) == 8 and all(case['cleanup'].values()), mode
    stop = case['checks'][-1]
    assert stop['name'] == 'stop-and-readback' and stop['coreRows'] > 0 and stop['confirmedWriters'] > 0
    assert stop['sessionNew'] == stop['sessionEnd'] == 1 and stop['sessionEndAcknowledged']
    assert stop['leasesAcquired'] == 2 and stop['leasesExpired'] == 0 and stop['drainVerified'] and stop['descriptorRemoved']
    if mode == 'paused':
        assert stop['leasesReleased'] == stop['leasesRevoked'] == 1 and stop['resumedInSameWindowBeforeGateClose'] and stop['stoppedBeforeBorrowerWatchdog']
    else:
        assert stop['leasesReleased'] == 2 and stop['leasesRevoked'] == 0
assert read('m2-owner-stop-paused-initial.json')['passed'] is False
print('PASS  native R5 production owner receipts, clean relocated CLI inventory and source bindings')
PY

echo
if [ "$fail" -eq 0 ]; then echo "全部通过"; else echo "有失败项"; fi
exit "$fail"
