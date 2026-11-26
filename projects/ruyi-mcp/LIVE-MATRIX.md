# 双架构生产借用、意外退出与跨机 stdio

## 验收口径

每种 CPU 架构各有一个 QA 镜像 config ID。在该架构的正常归还、暂停中由 owner 停止、自然到期和跨机 stdio 场景中，**Trace CLI、MCP 构建、Node 生产依赖和经审计的 Firefox 都来自同一个镜像**。AMD64 与 ARM64 的架构及内核不同，分别有独立 ID；同一批的两张镜像使用相同的应用负载清单。QA 镜像用现有、已读回的 CLI2 发行作父层，新增一层验收负载。它既不是新的 CLI2 发行，也没有改变独立部署 MCP 或 Linux 默认无 UI 的约定。

[回执索引](../../artifacts/receipts/mcp-live-matrix-20261126/matrix.json)区分启动时的平台 gitlink 组合（`original`，Trace `e35e727` / MCP `b5e204a`）和本次发布组合（`corrected`，Trace `51852ce` / MCP `df0db85`），逐项登记原始结果、哈希和 UTC 起止时间。最终 AMD64 镜像 `sha256:f372860d05002dad9bc94937bbfbfcad4adcbad03b7a0613906be4293fe2966a`，ARM64 镜像 `sha256:eebf10482a9680fbf48480c6b7b481c70c5e90742187f942747d252a179e33d8`。两轮 native 都是真实的生产 owner、两个独立 MCP 进程和本地合成页面，非早期 ARM64 的租约替身。

| 项目 | 通过的依据 |
| --- | --- |
| 正常归还 | 原生断点、恢复、同页操作、同一 Firefox 代次、两次租约获取与归还；读回同 writer 闸门内的页面记录，单一 BiDi 正常结束。 |
| 暂停中停机 | 从真正暂停的断点发起 owner stop；在看门狗超时前观测到同页恢复记录，再见到 native `session_stopped`。 |
| 租约自然到期 | 等待真实的 120 秒；错范围 8 次均被挡住，页面只记录合法的 1 次点击，owner 清点 1 次归还及 1 次到期。 |
| 跨机 SSH stdio | 客户端 SDK 在 `oracle-dsh`，SSH 的另一端分别为 AMD64 和 ARM64 机器。`ssh -T` 在同一远端容器内 `docker exec -i` 启动 MCP，两端机器身份确实不同。两个 SSH MCP 客户端完成排他、实际 query/click、归还/重借及 EOF；在远端原生写入时段内读到对应页面标记。无浏览器端口发布或转发。 |
| Firefox 意外退出 | ARM64 私有 PID 命名空间内，验证 boot、进程代次、直接 owner、可执行文件、专属 profile 和 fixture 后，只对本次运行打开的 pidfd 注入故障。浏览器异常退出 137，原始采集保留为未完成，既无 `session.end` ACK，也无 verified drain。旧 owner、控制/relay、描述符和锁均退出，独立哨兵仍能响应。修订后有 1 次撤销；旧客户端确认原代际结束，返回 `lease_already_lost` 后可在同一 stdio 进程借用新 run 并成功完成一次采集。 |

**保留的反例：** 初始 Trace pin 在 Firefox 异常退出时已关闭端点，但漏记了在用租约，故故障门禁失败。修复前 MCP 对消失的描述文件只能报告传输出错；修复后，需要已绑定的同一 run、同一进程代际以及相符的私有终态证据才确认退出，单独缺文件仍按未知处理。另一份 ARM64 候选回执记录 `Trace CLI start exited 5`；同一镜像、相同参数在新的目录中复跑三项全部通过。首次失败留档，不归因于未经证实的原因。

## 在其他机器复跑

在平台递归检出的干净代码树中安装锁定依赖。构建器只允许固定的应用文件、无目标架构 ELF/native addon 的 Node 生产依赖、以及登记的回环 QA runner 进入测试层。Python 浏览器自启与借用是不同路径：这一矩阵只验后者。

```bash
set -euo pipefail
ROOT=$(pwd -P)  # ruyi-platform
Q="$ROOT/projects/ruyi-mcp/qa"
NEW=$(mktemp -d)
T="$ROOT/submodules/ruyitrace"; M="$ROOT/submodules/ruyi-mcp"
npm ci --prefix "$T/console/tooling" --ignore-scripts --no-audit --no-fund
node "$T/console/tooling/build-cli.mjs" "$NEW/cli"
(cd "$M" && npm ci && npm run build && git diff --exit-code -- build && npm prune --omit=dev --ignore-scripts)
python3 "$Q/stage-live-matrix.py" --platform "$ROOT" --trace "$T" --cli "$NEW/cli" --mcp "$M" --out "$NEW/live-qa"

# 操作端预先配置好受信任 SSH 别名；目标已加载相应架构及哈希的 CLI2 父镜像。
export DOCKER_HOST="ssh://$QA_HOST"
TAG="ruyi-qa/live-matrix:$ARCH-$(date +%s)"
bash "$Q/native-matrix-image.sh" "$ARCH" "$NEW/live-qa" "$TAG"
ID=$(docker image inspect -f '{{.Id}}' "$TAG")
bash "$Q/run-same-image.sh" "$ID" "$NEW/native"
node "$Q/ssh-stdio.mjs" "$QA_HOST" "$ID" "$M"
# 现代 Linux pidfd / 私有 PID namespace；不传入宿主 PID，也不在共用 namespace 注入故障。
bash "$Q/run-browser-loss.sh" "$ID" "$T/tests/linux/run_production_mcp_session.mjs" "$NEW/crash" --require-retired-client
```

单独核对本页的已入库回执：`python3 -B projects/ruyi-mcp/qa/verify-matrix.py`。全平台 `bash scripts/verify-pins.sh` 还会复验其他组件的本地历史原件；隔离 clone 与这些原件处于不同目录层级时，将 `RUYI_PLATFORM_EVIDENCE_ROOT` 设为包含对应 `deliverables/` 的绝对根目录，原件及哈希检查仍然必需。

镜像构建不会拉取或替换产品镜像标签；每次指定新 QA 标签。跨机流程默认使用已登记的机器 SSH 身份，传递的是描述文件的**路径**，不是其访问凭据。测试账户需要能够在该专用 Docker 测试引擎启动/回收自己的容器，这不是面向一般用户的 Docker 授权方案。

## 独立 Electron 发行线

使用[正式私有 Electron Owner Alpha 1](https://github.com/Facetomyself/ruyitrace/releases/tag/linux-electron-owner-v0.1.0-alpha.1)，打包标签 `2d58cbd`、已安装应用源码 `724ef8e`、实际借用客户端 `b5e204a`。平台已验证[每架构五个生命周期用例](../../artifacts/receipts/trace-linux-gap-closure-v1/electron-owner/README.md)。本轮分别重新校验完整发布归档和实际安装文件，用原始 `launch-ruyitrace` 在两个独立原生主机各复跑一次 [ARM64](../../artifacts/receipts/mcp-live-matrix-20261126/electron-arm64-fresh.json) / [AMD64](../../artifacts/receipts/mcp-live-matrix-20261126/electron-amd64-fresh.json) 借用—归还—再借。每轮均确认 Electron 45.4.1 主进程、同一 Firefox、单一 BiDi、两次合法点击、原生记录、正常关闸及零个遗留 owned 子进程；同时重算本轮原始结果和 writer 哈希。

这些是虚拟 Xvfb/Weston 席位的限定用例；没有给实体显示、人工系统输入法或一般产品签署结论。也没有将 Alpha 的 `b5e204a` 回执登记成维护 MCP 客户端版本的 Electron 复测。一次独立开发原型未观察到开闸 `session_started`，已排除该路径，未合入或用于签收。所有常驻产品与 Linux MCP 的默认无 UI 部署维持原样。
