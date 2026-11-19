#!/usr/bin/env bash
# 初始化/更新 submodule，并报告每个的状态。
set -uo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

if [ ! -f .gitmodules ]; then
  echo "尚无 .gitmodules —— 先按 README §三 添加 submodule"
  echo "参考命令："
  echo "  git submodule add https://github.com/Facetomyself/ruyihttp    submodules/ruyihttp"
  echo "  git submodule add https://github.com/Facetomyself/ruyijs-inner submodules/ruyijs"
  echo "  git submodule add https://github.com/Facetomyself/ruyitrace   submodules/ruyitrace"
  exit 0
fi

git submodule sync --recursive
git submodule update --init --recursive

echo
echo "== 状态 =="
git submodule status --recursive | while read -r line; do
  case "$line" in
    -*) printf '%-70s %s\n' "${line#-}" "NOT INIT" ;;
    +*) printf '%-70s %s\n' "${line#+}" "COMMIT MISMATCH" ;;
    *)  printf '%-70s %s\n' "${line# }" "OK" ;;
  esac
done
