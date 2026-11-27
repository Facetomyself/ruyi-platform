#!/usr/bin/env bash
# Use a clean checkout. Initialize pinned first-level components only.
set -euo pipefail
root=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd -P)
cd "$root"
if [[ ! -f .gitmodules ]]; then echo '缺少平台 .gitmodules' >&2; exit 1; fi
usage() { echo '用法：bash scripts/sync-submodules.sh [--public]；默认按 gitlink 同步全部一级组件，--public 只取公开组件，两档均不递归。'; }
if (( $# )); then
  [[ $# -eq 1 ]] || { usage >&2; exit 2; }
  case "$1" in
    --public) set -- submodules/ff-ruyijs submodules/ruyihttp submodules/ruyi-mcp ;;
    -h|--help) usage; exit 0 ;;
    *) usage >&2; exit 2 ;;
  esac
else
  # An explicit pathspec also works when the user's submodule.active is narrower.
  set -- submodules/
fi
git -c submodule.recurse=false submodule sync -- "$@"
git -c submodule.recurse=false submodule update --init --checkout -- "$@"
git -c submodule.recurse=false submodule status -- "$@"
