#!/usr/bin/env bash
# Run the existing two production M2 scenarios and the real 120s lease check in identical image bytes.
set -euo pipefail
[[ $# == 2 ]] || { echo 'usage: run-same-image.sh immutable-QA-config-id new-local-receipt-dir' >&2; exit 2; }
id=$1; dir=$2
[[ $id =~ ^sha256:[0-9a-f]{64}$ && -n $dir && ! -e $dir ]]
mkdir -m 0700 -- "$dir"; dir=$(realpath -e -- "$dir")
manifest=$(docker image inspect -f '{{index .Config.Labels "ruyi.qa.payload"}}' "$id"); [[ $manifest =~ ^[0-9a-f]{64}$ ]]
[[ $(docker version -f '{{.Server.Arch}}') == "$(docker image inspect -f '{{.Architecture}}' "$id")" ]]
base=(--rm --pull=never --network=none --read-only --user 1000:1000 --cap-drop=ALL --security-opt=no-new-privileges=true --memory=2500m --pids-limit=512 --cpus=2 --shm-size=256m --tmpfs /tmp:rw,nosuid,nodev,mode=1777,size=1g --env HOME=/tmp/live-home --env XDG_RUNTIME_DIR=/tmp/live-runtime --entrypoint /opt/ruyitrace/tini "$id" -- /bin/sh -ec)
docker run "${base[@]}" 'cd /opt/live-qa; sha256sum --quiet -c SHA256SUMS; node -e "const f=require(\"node:fs\"),c=require(\"node:crypto\");const sha=p=>c.createHash(\"sha256\").update(f.readFileSync(p)).digest(\"hex\"); const lines=f.readFileSync(\"/proc/self/status\",\"utf8\").split(/\\n/);console.log(JSON.stringify({pins:require(\"./pins.json\"),arch:process.arch,node:process.version,uid:process.getuid(),firefoxBuild:JSON.parse(f.readFileSync(\"/identity-input\")).installed.build_id,identitySha:sha(\"/identity-input\"),baselineSha:sha(\"/opt/ruyitrace/proofs/baseline.json\"),cliReceipt:sha(\"cli/build-receipt.json\"),manifestSha:sha(\"SHA256SUMS\"),interfaces:f.readdirSync(\"/sys/class/net\"),isolation:lines.filter(l=>/^(Seccomp|NoNewPrivs|CapEff):/.test(l))}))"' >"$dir/runtime.json"
printf '%s\n' "$id" >"$dir/image-id"
for mode in standard paused expiry; do
  printf 'Running %s on %s\n' "$mode" "$id"
  start=$(date -u +%FT%TZ)
  rc=0
  docker run "${base[@]}" 'mkdir -m 0700 "$HOME" "$XDG_RUNTIME_DIR" /tmp/check; p=/opt/live-qa
    if [ "$1" = expiry ]; then
      export RUYI_MCP_ROOT="$p/mcp" TRACE_CLI="$p/cli/bin/ruyitrace" RUYI_FIREFOX_PATH=/browser/firefox TRACE_RECEIPT=/identity-input TRACE_ACCEPTANCE=/opt/ruyitrace/proofs/baseline.json
      exec timeout 225 node "$p/mcp/scripts/borrowed-behaviors-native.mjs"
    fi
    case "$1" in paused) set -- --owner-stop-while-paused;; standard) set --;; *) exit 2;; esac
    exec timeout 150 node "$p/trace/tests/linux/run_production_mcp_session.mjs" --trace-cli "$p/cli/bin/ruyitrace" --firefox /browser/firefox --receipt /identity-input --acceptance /opt/ruyitrace/proofs/baseline.json --mcp-root "$p/mcp" --work /tmp/check "$@"' gate "$mode" >"$dir/$mode.json" 2>"$dir/$mode.stderr" || rc=$?
  printf '%s %s %s %s\n' "$mode" "$rc" "$start" "$(date -u +%FT%TZ)" >>"$dir/exits"
  if [[ $rc != 0 ]]; then echo "$mode failed (exit $rc)" >&2; exit "$rc"; fi
  python3 - "$dir/$mode.json" "$mode" <<'PY'
import json,sys
from pathlib import Path
r=json.loads(Path(sys.argv[1]).read_bytes()); assert r['passed'] is True
mode=sys.argv[2]
if mode=='expiry':
    assert r['expiryVerified'] and r['wrongScopeRejected']==8 and r['browserRetained'] and r['nativeCleanup']['leasesExpired']==1
else:
    end=r['checks'][-1]; assert all(r['cleanup'].values()) and end['sessionNew']==end['sessionEnd']==1 and end['sessionEndAcknowledged'] and end['drainVerified'] and end['coreRows']>0 and end['leasesAcquired']==2
    if mode=='paused': assert end['leasesRevoked']==1 and end['resumedInSameWindowBeforeGateClose']
    else: assert end['leasesReleased']==2
print(mode,'verified')
PY
done
