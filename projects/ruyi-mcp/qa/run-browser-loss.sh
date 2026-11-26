#!/usr/bin/env bash
# Isolated fault test of the newly provisioned Firefox only. Docker's default PID mode is private.
set -euo pipefail
[[ $# -ge 3 && $# -le 4 && $1 =~ ^sha256:[0-9a-f]{64}$ && -f $2 && ! -e $3 ]] || { echo 'usage: run-browser-loss.sh QA-image-id runner.mjs fresh-receipt-dir [--require-retired-client]' >&2; exit 2; }
id=$1; runner=$(realpath -e -- "$2"); dest=$3; extra=(); if [[ $# == 4 ]]; then [[ $4 == --require-retired-client ]]; extra+=("$4"); fi
[[ $(docker image inspect -f '{{.Config.User}}' "$id") == 1000:1000 ]]
[[ $(docker image inspect -f '{{index .Config.Labels "ruyi.qa.payload"}}' "$id") =~ ^[0-9a-f]{64}$ ]]
mkdir -m 0700 -- "$dest"; sha256sum "$runner" | cut -f1 -d' ' >"$dest/runner.sha256"; printf '%s\n' "$id" >"$dest/image-id"
rc=0
docker run --rm --pull=never -i --network none --ipc private --read-only --user 1000:1000 --cap-drop ALL --security-opt no-new-privileges=true --cpus=2 --memory=2500m --pids-limit=512 --shm-size=256m --tmpfs /tmp:rw,nosuid,nodev,mode=1777,size=1g --env HOME=/tmp/home --env XDG_RUNTIME_DIR=/tmp/xdg --entrypoint /bin/sh "$id" -ec '
    mkdir -m700 /tmp/home /tmp/xdg /tmp/evidence; mkdir -p /tmp/probe/tests/linux
    ln -s /opt/live-qa/trace/console /tmp/probe/console; tee /tmp/probe/tests/linux/run.mjs >/dev/null
    exec node /tmp/probe/tests/linux/run.mjs --browser-loss --trace-cli /opt/live-qa/cli/bin/ruyitrace --firefox /browser/firefox --receipt /identity-input --acceptance /opt/ruyitrace/proofs/baseline.json --mcp-root /opt/live-qa/mcp --work /tmp/evidence "$@"
' gate "${extra[@]}" <"$runner" >"$dest/result.json" 2>"$dest/stderr" || rc=$?
printf '%s\n' "$rc" >"$dest/exit"; exit "$rc"
