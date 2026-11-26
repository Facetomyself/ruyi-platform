# RuyiTrace Native Events Beta 1 · Linux 操作指南

## 下载、限制与隔离

从 [私有预发行 `native-events-v0.2.0-beta.1`](https://github.com/Facetomyself/ruyitrace/releases/tag/native-events-v0.2.0-beta.1) 下载本机架构资产。`uname -m` 为 `aarch64` 选 ARM64；为 `x86_64` 选 AMD64。用有仓库读取权限的 GitHub 账号登录。此版本是 Firefox **159.0** 的独立原生元数据采集路径 `ruyitrace-native`，实际运行时代码为 `f177682d8dc4e028ad450a00f2d78acc4063e321`。普通 CLI2 的 `core,click,storage,exception` 与现有站点发行保持原样。ARM64 和 AMD64 的最终镜像各通过 **22/22** 项：Wasm 6、JSCall 5、HTTP 6、WebSocket 5；每个架构另外跑了本指南所列的操作员补充对照。

在原生 Linux Docker Engine 上运行，使用本地 `/run/docker.sock`、Bash、Python 3 和 GNU coreutils。隔离测试容器使用默认 seccomp、UID/GID `1000:1000`、只读根、cap-drop ALL、no-new-privileges、仅回环网络。保留独立空证据父目录并预留数 GiB 用于导入与证据。Docker gzip 是可运行镜像；Firefox tar.xz 是独立的裸内核身份资产，不是镜像或桌面包。直接运行独立内核文件并不会安装本发布的 writer/actor 运行时。AMD64 独立内核相对旧包仅有 `libxul.so` 和根 `omni.ja` 两个条目变化；后者解码后只有 `about:buildconfig` 多显示一项配置，镜像中的运行时启动钩子是其后单独加上的覆盖层。

## 1. 校验附件并导入精确镜像

在下载目录用 **Bash** 运行。下例只要求下载相应架构的 Docker/内核以及本指南、`native-events-beta.json`、`SHA256SUMS`；若也下载便携 skill ZIP，可一并核对。先把下面记录的两个变量留在当前终端。

```bash
set -euo pipefail
case "$(uname -m)" in aarch64) arch=arm64;; x86_64) arch=amd64;; *) exit 2;; esac
verify_asset() {
  awk -v n="$1" '$2==n {print; found++} END{if(found!=1) exit 1}' SHA256SUMS | sha256sum --check --strict -
}
verify_asset native-events-beta.json
verify_asset BETA-ZH.md
read -r image build docker_archive kernel_archive < <(python3 -B - "$arch" <<'PY'
import json,sys
with open('native-events-beta.json',encoding='utf-8') as h:
    m=json.load(h)
assert m['tag']=='native-events-v0.2.0-beta.1'
a=m['architectures'][sys.argv[1]]
print(a['image_id'],a['firefox_build_id'],a['artifacts']['docker']['name'],a['artifacts']['kernel']['name'])
PY
)
verify_asset "$docker_archive"
verify_asset "$kernel_archive"
if [[ -f ruyitrace-skill-v0.2.0.zip ]]; then verify_asset ruyitrace-skill-v0.2.0.zip; fi
docker --host unix:///run/docker.sock image load --input "$docker_archive"
test "$(docker --host unix:///run/docker.sock image inspect --format '{{.Id}} {{.Os}}/{{.Architecture}} {{.Config.User}}' "$image")" = "$image linux/$arch 1000:1000"
docker --host unix:///run/docker.sock run --rm --pull never --network none --read-only \
  --user 1000:1000 --cap-drop ALL --security-opt no-new-privileges "$image" verify
```

`verify` 确认安装身份与源成员，不等于运行浏览器采集。源码驱动从同一标签的私有源码检出，或从同标签发布的对应便携 skill 取得（如有）。源码链接和命令均不需要分享登录凭据。

## 2. 运行真实浏览器与独立夹具

下例在该标签源码根目录用 **Bash** 运行，沿用上一步的 `arch`、`image`、`build`。输出只写到新建的专用父目录；若当前账号并非 UID/GID 1000，只为这个新目录调整所有者。

```bash
runs=$(mktemp -d "$PWD/native-beta-runs.XXXXXXXX")
test "$(stat -c %u:%g "$runs")" = 1000:1000 || sudo chown 1000:1000 "$runs"
for trial in 'wasm call_export' 'wasm trap' 'jscall normal' 'jscall throw' \
             'http redirect' 'http cache_hit' 'websocket fragment_and_ping' 'websocket upgrade_only' \
             'websocket skip' 'websocket disabled' 'websocket other_origin'; do
  read -r gate name <<<"$trial"
  bash product/native-events/qa/local_case.sh "$image" "linux/$arch" "$build" "$gate" "$name" "$runs"
done
```

对照页面、独立 peer 与原生 writer 的回执。常规回执名称为 `page.json`、适用网络案的 `peer.json`、`native/native-events.jsonl`、`native/native-sealed.json` 与 `run.json`。只有 `status:"ok"`、`complete:true`、drop 全 0、运行标识及原生序号一致、正常收尾，才是完整观察（包括完整零行）。`partial`、`unsupported`、缺失收尾或错文档只得到未就绪，均不是完整零行。

- **WebSocket：**固定片段/交错 ping/pong 夹具在两架构均记录 **3 TX、5 RX**；独立 peer 核对了方向、opcode、FIN 与字节长度。只升级案记录双向 close，各一行。skip、关闭与跨 origin 为完整零行。另有两个两架构补充对照：固定选择路径时 peer 收到两条路径的 5 和 9 字节记录，native 只保留选中路径的三行；65,537 字节反例导致 `drops.limit=1`、`status=partial`、`complete:false`，native 只余两条关闭帧。补充对照单列，独立于常规 22 项。
- **HTTP：**常规锁定夹具测合成 GET 200、302→200 链、缓存命中且独立 peer 无新 GET，以及关闭/来源对照；原生 HTTP channel 元数据不是 pcap。
- **JSCall：**外部经典脚本中的已知命名同步函数，核对 enter 对应 return / throw；并非所有 JS 或 JIT 执行轨迹。**Wasm：**仅固定 `/target.js` 第 31 行的非流式编译点与登记的 `add`/`trap`，函数索引 0，入口偏移分别 35/33。`add` 示例三组返回 `42, -5, -2147483648`，原生六行；`trap` 为 enter/throw 两行。只编译、仅实例化、停用与跨 origin 的相应夹具有完整零行。流式、worker、内部 Wasm 调用与优化快路径各需独立证据。

## 3. 操作员自选精确范围：302→418 与替换的命名 JS 函数

下面的复核脚本通过 `ruyitrace-native init/run` 调用真正产品，使用容器内私有回环 fixture。运行时只接受 `http://127.0.0.1:PORT`（1024–65535）、显式且精确的顶层文档路径，路由也按完整路径匹配。禁止使用生产 URL、端口发布或挂入日常浏览器配置。`init` 默认关闭，必须显式 `--enable`；启动本身不打开采集窗，由授权本地程序等待 Ready→Start→Armed，再触发页面，最后 Stop 并核对 seal。下面的脚本代办这些步骤。

```bash
pilot=$(realpath -e product/native-events/runtime/smoke_operator.py)
probe=$(mktemp -d "$PWD/native-beta-operator.XXXXXXXX")
test "$(stat -c %u:%g "$probe")" = 1000:1000 || sudo chown 1000:1000 "$probe"
docker --host unix:///run/docker.sock run --rm --pull never --network none --read-only \
  --user 1000:1000 --cap-drop ALL --security-opt no-new-privileges --ipc private \
  --pids-limit 450 --memory 1500m --memory-swap 1500m --cpus 1 --shm-size 192m \
  --tmpfs /tmp:rw,nosuid,nodev,mode=1777,size=256m \
  --mount "type=bind,src=$probe,dst=/proof" \
  --mount "type=bind,src=$pilot,dst=/qa/smoke_operator.py,readonly" \
  --entrypoint /usr/bin/python3 "$image" -IB /qa/smoke_operator.py --image "$image" --out /proof/results
```

- 选 `--http-path /owned/redirect --redirect-path /owned/status`：核对同链 `GET 302`、`GET 418` 两个 native row。页面明确收到终点 418，还访问另一路线 `/owned/ignored` 收到 202；后者应只出现于 peer/page，不在选定 native chain。单独用 `--http-path /owned/status` 则只观察一条 418。
- 选 `--script-path /owned/client.js --function-name quoteTotal --js-line 3 --js-column 22`：Gecko 坐标是一基，选中同步函数应有 enter/return 两行。另一个 `ignoreQuote` 同时运行并回报 13，选中 `quoteTotal` 回报 42；多出的页面回报不应产生选中函数的行。`--wasm-selector add|trap` 属不同模式，仅接受固定注册指纹，不能替换为任意 Wasm 模块。
- 以上直接 418、302→418 和 `quoteTotal` 三项，已在两架构的最终 Beta 镜像上实测。另跑了同源但路径错误的对照：两个架构的页面/peer 都观察到 418，但 1,200 ms 内无 IPC Ready，记录为 `out_of_scope_no_ipc_ready`、测量未完成；这与常规 22 项里已封存的跨 origin 零行是两类证据。

这批能力记录限定的结构元数据，不是 HTTP 报文正文、请求头、WebSocket 帧载荷、源代码、函数参数、Wasm 指令或通用流量监控。TLS/HTTP2/HTTP3、其他网络路径、其他浏览器/发行版与真实物理面板、系统 IME 属独立验收。将有界计数、产物摘要及清洁后的回执走私有渠道交接；完整 profile、凭据、启动控制文件与私有页面数据留在本机。
