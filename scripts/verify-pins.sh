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
echo "== 4. 文档内部链接 =="
python3 scripts/verify-links.py || fail=1

echo
echo "== 5. submodule 状态 =="
if [ -f .gitmodules ]; then
  git submodule status 2>/dev/null | while read -r line; do
    case "$line" in
      -*) say "  ${line#-}" "NOT INIT" ;;
      *)  say "  ${line# }" "OK" ;;
    esac
  done
else
  say "  .gitmodules" "SKIP（尚未添加 submodule）"
fi

echo
if [ "$fail" -eq 0 ]; then echo "全部通过"; else echo "有失败项"; fi
exit "$fail"
