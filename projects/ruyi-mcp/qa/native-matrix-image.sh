#!/usr/bin/env bash
# Stage a QA-only image on one already-selected native Engine. No pull, package installs or running staging containers.
set -euo pipefail
[[ $# == 3 ]] || { echo 'usage: native-matrix-image.sh amd64|arm64 /absolute/live-qa new-local-tag' >&2; exit 2; }
arch=$1; payload=$(realpath -e -- "$2"); tag=$3
[[ $(basename "$payload") == live-qa && -f "$payload/SHA256SUMS" && $tag =~ ^ruyi-qa/[a-z0-9._-]+:[a-z0-9._-]+$ ]]
case $arch in
  amd64) base=sha256:eb73d165ea9adc15864aeb054bc90a78670618c5c0606827997d357f1cae05c6;;
  arm64) base=sha256:9073c375ff26a8248e055e54f1ca28f289d92fc7f253d36685973fa8ecdd33bc;;
  *) exit 2;;
esac
[[ $(docker image inspect -f '{{.Os}}/{{.Architecture}} {{.Id}}' "$base") == "linux/$arch $base" ]]
[[ $(docker version -f '{{.Server.Arch}}') == "$arch" ]]
if docker image inspect "$tag" >/dev/null 2>&1; then echo 'choose an unused QA image tag' >&2; exit 1; fi
sha=$(sha256sum "$payload/SHA256SUMS" | cut -d' ' -f1)
nonce=$(python3 -c 'from uuid import uuid4; print(uuid4().hex)')
cid=$(docker create --network none --pull=never --label "ruyi.qa.stage=$nonce" --entrypoint /usr/local/bin/node "$base" --version)
cleanup(){
  if [[ $cid =~ ^[a-f0-9]{64}$ && $(docker container inspect -f '{{.Id}} {{.State.Status}} {{index .Config.Labels "ruyi.qa.stage"}}' "$cid") == "$cid created $nonce" ]]; then docker rm "$cid" >/dev/null; fi
}
trap cleanup EXIT
# Normalize owner and read/execute permissions; no credentials, profiles, or host mounts.
tar --numeric-owner --owner=0 --group=0 --mode='u+rwX,go+rX,go-w' -cf - -C "$(dirname "$payload")" live-qa | docker cp - "$cid:/opt"
id=$(docker commit --change "LABEL ruyi.qa.payload=$sha" --change "LABEL ruyi.qa.base=$base" "$cid" "$tag")
[[ $(docker image inspect -f '{{.Id}} {{index .Config.Labels "ruyi.qa.payload"}} {{.Config.User}}' "$tag") == "$id $sha 1000:1000" ]]
python3 - "$base" "$id" <<'PY'
import json, subprocess, sys
base,child=json.loads(subprocess.check_output(['docker','image','inspect',*sys.argv[1:]]))
a=base['RootFS']['Layers']; b=child['RootFS']['Layers']; assert b[:-1]==a and child['Architecture']==base['Architecture']
PY
docker run --rm --pull=never --network none --read-only --user 1000:1000 --cap-drop ALL --security-opt no-new-privileges=true --memory 256m --pids-limit 48 --entrypoint /bin/sh "$id" -ec 'cd /opt/live-qa; sha256sum -c --quiet SHA256SUMS; node cli/bin/ruyitrace --help >/dev/null; node -e "const m=require(\"./pins.json\"); console.log(m); console.log(process.platform,process.arch,process.version)"'
printf 'QA_IMAGE=%s BASE=%s MANIFEST=%s\n' "$id" "$base" "$sha"
