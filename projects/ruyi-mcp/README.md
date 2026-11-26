# ruyi-mcp：Firefox 自动化与调试控制面

平台在 `submodules/ruyi-mcp` 固定经过验收的源码版本；组件在独立仓库的 `linux` 分支提交与发布。版本看 [PINS](../../PINS.md#9-ruyi-mcp)，进度看 [STATUS](../../STATUS.yaml)，跨项目接口看 [架构](../../docs/01-architecture.md#5-ruyi-mcp-控制面与组件边界)。独立开发工作副本与平台锁定检出可以同时存在。

本地 QA 的 Electron、MCP 与 Trace owner 分工见 [管理面验收与交接](MANAGEMENT-HANDOFF.md)。从干净检出继续开发、构建 CLI 或重跑 R5 生产借用，按[异机开发与验收手册](PRODUCTION-OWNER.md)执行。

实际支持范围见[双架构同镜像验收矩阵](LIVE-MATRIX.md)：原生 CLI 借用、真实 SSH stdio、故障后的客户端回收和独立 Electron 发行，各用各自的真机回执。

[双架构验收矩阵](LIVE-MATRIX.md)给出原生 CLI 借用、跨机 SSH stdio、Firefox 意外退出与同客户端恢复，以及独立 Electron 预发行的回执、版本和复测入口。

## 检出并验证

```bash
cd /var/lib/dsh/Ruyi/ruyi-platform
git submodule update --init --checkout -- submodules/ruyi-mcp
git submodule status -- submodules/ruyi-mcp
cd submodules/ruyi-mcp
python3 -m venv .venv
. .venv/bin/activate
python -m pip install -r requirements.txt
npm ci
npm run check
```

`check` 验证 MCP 与实际 Python bridge、构建及协议测试，无需浏览器。部署依赖和真机验收见组件 [Linux 说明](../../submodules/ruyi-mcp/docs/linux-port.md)，容器阶段见 [Docker 设计](../../submodules/ruyi-mcp/docs/docker-design.md)。

## 借用行为门禁

在 MCP 根目录用 `npm run build && npm run check:borrowed-behaviors` 验证三个公开契约：租约状态与 owner 存活分开、错页或错 frame 在任何 owner IPC 前返回 `UNSUPPORTED_SCOPE`、借用退出只按实际回执说明归还结果。该协议门禁已纳入 `npm run check`。真机复现另见 [MCP 运行说明](../../submodules/ruyi-mcp/README.md#借用-trace-活会话) 中的 `check:borrowed-native`；对照[原生 R5 回执](../../artifacts/receipts/trace-amd64-r5/borrowed-behaviors-b5e204a.json)。

## AMD64 容器与 Trace 制品

[原生容器 CI](https://github.com/Facetomyself/ruyi-mcp/actions/runs/45308474899) 通过双架构 `core` 和 AMD64 ESR 对照。2026-11-24 在原生 AMD64 Docker 使用 `d7DBYN4g` 的实际 Firefox 159.0 / BuildID `20261121110134`：MCP stdio 自启、BiDi 导航、查询状态、正常退出、下载字节校验与 **19/19 项 RDP 门禁**全部通过。容器及产物身份、退出码与原始日志哈希见 [真机回执](../../artifacts/receipts/ruyi-mcp-amd64-d7DBYN4g-20261124.json)。

首次 RDP 验收在首条语句断点处失败：Firefox 的异步 `forwardingCancelled` 被误当作 root 的 `getTab` 应答。修订将其单独分流，保留浏览器身份校验；重连测试复用原上下文，避免碰到额外标签页时猜选。复跑确认首语句暂停、按原上下文重连和看门狗恢复均通过。

在有 Docker 的原生 AMD64 主机上，令 `TRACE_ARCHIVE` 指向平台审核的发布包。校验并只解出内核目录，然后按 [组件容器说明](../../submodules/ruyi-mcp/docs/docker-design.md) 执行下载与 RDP 门禁：

```bash
set -euo pipefail
: "${TRACE_ARCHIVE:?请指定 d7DBYN4g 发布包的绝对路径}"
[ "$(uname -m)" = x86_64 ]
printf '%s  %s\n' 797cf3ce15b72b3059e7ab519e29298d12672aa4db8bc4f2d5f1746ec71d07e2 "$TRACE_ARCHIVE" | sha256sum -c -
qa_root=$(mktemp -d)
tar -xzf "$TRACE_ARCHIVE" -C "$qa_root" --no-same-owner ruyitrace-linux-amd64/resources/kernel
export FIREFOX_DIR="$qa_root/ruyitrace-linux-amd64/resources/kernel"
printf '%s  %s\n' 8c5225f8b76a5167ed4a010cdaa4e680a3fe2d39fa675a5b3f23b4a3198d04bf "$FIREFOX_DIR/firefox" | sha256sum -c -
grep -Fx 'BuildID=20261121110134' "$FIREFOX_DIR/application.ini"
cd /var/lib/dsh/Ruyi/ruyi-platform/submodules/ruyi-mcp
docker build --platform linux/amd64 --target browser --build-arg "RUYI_MCP_REVISION=$(git rev-parse HEAD)" -t ruyi-mcp:browser .
node scripts/container-smoke.mjs ruyi-mcp:browser browser "$FIREFOX_DIR"
```

这是 **MCP 自启该 Firefox** 的验收。生产活会话需要 Trace owner 实际发布 descriptor，并提供页面操作、租约、回环 RDP 与正常 flush。Trace 的采集门禁和独立 owner fixture 各自有证据，二者均与生产同会话验收分开。

## 跨仓更新顺序

1. 在组件仓 `linux` 分支提交、推送，并核对 CI 对应提交。
2. 在平台把 `submodules/ruyi-mcp` 切换到该明确提交；分支声明用于发现更新，平台日常检出使用固定 gitlink。
3. 同步 [PINS](../../PINS.md)、[STATUS](../../STATUS.yaml)、[变更日志](CHANGELOG.md) 及 [TIMELINE](../../TIMELINE.md) 的统计。若改变 Trace 接口，同步相应架构和验收记录。
4. 运行平台 `bash scripts/verify-pins.sh` 和组件 `npm run check` 后提交平台 pin。真实浏览器与 Trace 同会话另行运行并记录制品身份及报告。
