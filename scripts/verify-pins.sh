#!/usr/bin/env bash
# 校验 PINS.md / STATUS.yaml 与实物一致。
# 退出码：0 所选层通过；1 验证失败；2 参数错误。
set -uo pipefail

usage() {
  printf '%s\n' \
    '用法: bash scripts/verify-pins.sh [--catalog | --repo | --full] [--evidence-root /absolute/path]' \
    '  --catalog  仅核对父仓 gitlink、STATUS、.gitmodules 与 MCP、开源 RuyiJS、RuyiDOM 的 PINS 行；无需子模块、外部材料或网络。' \
    '  --repo     核对固定子模块、现有源/回执门禁及 RuyiJS 仓内副本；仓外原件和次级哈希出处未核。' \
    '  --full     核对同一组门禁，再核对 RuyiJS 仓外原件与次级哈希出处；无参数默认此层。' \
    '  --evidence-root /absolute/path  仅用于 full，优先于 RUYI_PLATFORM_EVIDENCE_ROOT。' \
    '  --help, -h  显示此帮助。'
}
usage_error() { printf '参数错误: %s\n' "$1" >&2; usage >&2; exit 2; }

if [[ $# -eq 1 && ( $1 == --help || $1 == -h ) ]]; then usage; exit 0; fi
tier=''
evidence_args=()
while (( $# )); do
  case "$1" in
    --catalog|--repo|--full)
      [[ -z $tier ]] || usage_error '只能指定一个验收层'
      tier=${1#--}
      shift ;;
    --evidence-root)
      [[ ${#evidence_args[@]} -eq 0 && ${2-} == /* ]] || usage_error '--evidence-root 需要一个绝对路径，且只能指定一次'
      evidence_args=(--evidence-root "$2")
      shift 2 ;;
    *) usage_error "未知参数 $1" ;;
  esac
done
tier=${tier:-full}
[[ $tier == full || ${#evidence_args[@]} -eq 0 ]] || usage_error '--evidence-root 仅用于 full'

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd -P)" || exit 1
cd "$ROOT" || exit 1
# These checks use local Git data, including when a checkout is a partial clone.
export GIT_ALLOW_PROTOCOL= GIT_NO_LAZY_FETCH=1 GIT_OPTIONAL_LOCKS=0
export PYTHONDONTWRITEBYTECODE=1 PYTHONOPTIMIZE=0

if [[ $tier == catalog ]]; then exec python3 -B scripts/verify-catalog.py; fi
printf '== %s：父仓登记与固定子模块检出 ==\n' "$tier"
python3 -B scripts/verify-catalog.py --checkouts || exit 1

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
python3 -B scripts/verify-ledger.py "--$tier" "${evidence_args[@]}" || fail=1
python3 scripts/verify-claims.py || fail=1

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
echo "== 6. Trace amd64 R5 发行身份 =="
python3 -B scripts/verify-trace-release.py || fail=1

echo
echo "== 6.5 Trace 交互镜像证据对齐 =="
python3 -B scripts/verify-trace-interactive.py || fail=1
python3 -B -m unittest discover -s tests -p 'test_interactive_release_identity.py' -q || fail=1
echo "== 6.6 临时 TLS 租约与回收回执 =="
python3 -B -m unittest discover -s tests -p 'test_public_lease_proof.py' -q || fail=1

echo
echo "== 6.7 Trace ARM64 主机、真实 TLS 与产品发行分开校验 =="
python3 -B scripts/verify-trace-arm64.py --preflight || fail=1
python3 -B -m unittest discover -s tests -p 'test_arm64_proof.py' -q || fail=1
arm_proof=$(python3 -B - <<'PY'
from pathlib import Path
import yaml
want = 'artifacts/receipts/trace-arm64-native-lease/release/confirmation.json'
item = yaml.safe_load(Path('STATUS.yaml').read_bytes())['projects']['ruyitrace'].get('arm64_release')
if item == want and Path(want).is_file(): print('release')
elif item is None and not Path(want).parent.exists(): print('preflight-only')
else: raise SystemExit('ARM64 发行登记与确认文件不一致')
PY
) || fail=1
case "$arm_proof" in
    release)
        python3 -B scripts/verify-trace-arm64.py --release || fail=1
        python3 -B -m unittest discover -s tests -p 'test_trace_arm_publication.py' -q || fail=1 ;;
    preflight-only) echo 'ARM64: only preparatory evidence registered; no product release claimed.' ;;
    *) fail=1 ;;
esac

echo
echo "== 6.8 ARM64 私有站点，两槽实装、真实公网与恢复 =="
python3 -B scripts/verify-trace-site.py --source "$ROOT/submodules/ruyitrace" --require-emergency --maintained-gitlink || fail=1
python3 -B -m unittest discover -s tests -p 'test_trace_site_publication.py' -q || fail=1

echo
echo "== 6.9 独立原生事件与 Electron owner 预发行（不替代稳定站点） =="
trace_gaps=artifacts/receipts/trace-linux-gap-closure-v1
if python3 -B "$trace_gaps/verify_candidate_002.py" | cmp -s - "$trace_gaps/candidate-002-review.json"; then ok '双架构 JSCall / Wasm / HTTP 六个有界实采格'; else bad 'Trace native 002 proof' 'byte or semantic mismatch'; fi
if python3 -B "$trace_gaps/electron-owner/verify_candidate_d.py" | cmp -s - "$trace_gaps/electron-owner/candidate-d-review.json"; then ok '双架构 Electron main 持有的十次真实生命周期'; else bad 'Trace Electron owner proof' 'byte or semantic mismatch'; fi
if python3 -B "$trace_gaps/patched-websocket/verify.py" | cmp -s - "$trace_gaps/patched-websocket/arm64-review.json"; then ok 'ARM64 元数据内核/帧句柄与同镜像 22 案'; else bad 'Trace native WS ARM evidence' 'byte or semantic mismatch'; fi
trace_ws=$trace_gaps/patched-websocket
if python3 -B "$trace_ws/verify_amd64.py" --zip "$trace_ws/amd64-originals.zip" --receipt-replay "$trace_ws/amd64-native-omni-review.json" --pins "$trace_ws/amd64-review-pins.json" --pins-sha256 55663f92213e105a82f40d3fc18080996e1a75323ca8d2b4c96665d2e7905135 >/dev/null && python3 -B "$trace_ws/join_reviews.py" | cmp -s - "$trace_ws/two-architecture-review.json"; then ok 'AMD64 的 419 份原件和双架构 44 个独立 run'; else bad 'Trace native WS dual evidence' 'byte or semantic mismatch'; fi
python3 -B -m unittest discover -s tests -p 'test_trace_native_beta_publication.py' -q || fail=1
if python3 -B "$trace_gaps/desktop-seat/verify_desktop_seat.py" | cmp -s - "$trace_gaps/desktop-seat/desktop-seat-review.json"; then ok '真实虚拟席位观测和未签的实体/人工 IME 分级'; else bad 'Trace local seat evidence' 'scope or semantic mismatch'; fi
python3 -B -m unittest discover -s tests -p 'test_trace_gap_prereleases.py' -q || fail=1

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
gate = status['projects']['ruyi-mcp']['container']['trace_owner_production']['borrowed_behavior_gate']
subprocess.run(['git','-C','submodules/ruyi-mcp','merge-base','--is-ancestor',gate['mcp_source'],'HEAD'], check=True)
raw = Path(gate['evidence']).read_bytes()
assert hashlib.sha256(raw).hexdigest() == gate['sha256']
case = json.loads(raw)
assert case['schema'] == 'ruyi-mcp-native-borrowed-behaviors.v1' and case['passed'] is True
assert case['expiryVerified'] and case['browserRetained'] and case['wrongScopeRejected'] == 8
assert case['canaryClicks'] == {'beforeLegitimate': 0, 'afterLegitimate': 1, 'beforeExpired': 1, 'afterExpired': 1}
stop = case['nativeCleanup']
assert (stop['leasesAcquired'], stop['leasesReleased'], stop['leasesExpired'], stop['leasesRevoked']) == (2, 1, 1, 0)
assert stop['drainVerified'] and stop['sessionEndAcknowledged'] and stop['sessionNew'] == stop['sessionEnd'] == 1
print('PASS  borrowed lease expiry, scoped page effects and acknowledged release')
PY

echo
echo '== 8.1 同镜像双架构生产借用、浏览器退出和跨机 SSH stdio =='
python3 -B projects/ruyi-mcp/qa/verify-matrix.py || fail=1

echo
echo '== 9. RuyiDOM 私有源码指针、发行回执与主机入口 =='
python3 -B -m unittest discover -s tests -p 'test_ruyidom_handoff.py' -q || fail=1

echo
echo '== 10. RuyiHTTP 公开发行与 CI 工件回执 =='
python3 -B -m unittest discover -s tests -p 'test_ruyihttp_public_release.py' -q || fail=1

echo
echo '== 11. 开源 RuyiJS：上游祖先与固定 Firefox 树项（仅源码） =='
python3 -B -m unittest discover -s tests -p 'test_open_ruyijs_handoff.py' -q || fail=1

echo
if [ "$fail" -ne 0 ]; then
  printf '%s 验收有失败项\n' "$tier"
elif [[ $tier == repo ]]; then
  echo 'repo 验收通过；RuyiJS 仓外原件与次级哈希出处未核。'
else
  echo 'full 验收通过；含 RuyiJS 仓外证据。'
fi
exit "$fail"
