# 生产 Trace 活会话：异机开发与验收

生产接入点为 **RuyiTrace Linux CLI `start --mcp`**，不是 Electron 窗口，也不是 MCP 自启浏览器。Trace 持有 Firefox 进程、一个 BiDi 会话及采集闸门；MCP 借用同一 Firefox 的排他租约，通过 owner 执行同源页面操作，必要时连接租约内的回环 RDP。部署以专用账号和私有网络命名空间为边界，Trace、Firefox 和 MCP 放在同一空间，容器无需发布控制端口。

## 1. 在新机器从 GitHub 复现源码

预备 Git、Node ≥22.12（验收用 Node 24）、Python ≥3.10、Python venv、PyYAML、C++17 编译器和 npm。真机门禁另需目标架构的 Linux Firefox 依赖或 Docker。私有仓读取权限由该机器的 Git 凭据配置负责。

```bash
git clone --recurse-submodules https://github.com/Facetomyself/ruyi-platform.git
cd ruyi-platform
# 要复现某份验收时，先切到该回执所在的平台提交，再初始化对应 gitlink。
git submodule update --init --recursive --checkout
git ls-tree HEAD:submodules
bash scripts/verify-pins.sh
```

保留子模块检出在版本清单指定的提交；开发到各自组件仓创建分支，组件先提交并推送，平台再更新 gitlink、[PINS](../../PINS.md) 和 [STATUS](../../STATUS.yaml)。平台固定的 MCP、Trace 源码、R5 浏览器输入和实际制品是不同层，禁止用当前分支头冒充历史制品。

## 2. 构建 Trace CLI、可选桌面与 MCP

从平台根目录执行；输出目录为本次新建目录，独立于源码。

```bash
root="$PWD"
output=$(mktemp -d)
cd "$root/submodules/ruyitrace"
RUYITRACE_REQUIRE_CLEAN=1 bash tests/linux/check_developer_checkout.sh
node console/tooling/build-cli.mjs "$output/trace-cli"
node "$output/trace-cli/bin/ruyitrace" --help
# 可选：重建 Electron 应用目录（内核与 Electron 本体另配）。
node console/tooling/build-linux.mjs "$output/trace-app"

cd "$root/submodules/ruyi-mcp"
python3 -m venv .venv
. .venv/bin/activate
python -m pip install -r requirements-container.txt
npm ci
npm run check
git diff --exit-code -- build
```

本轮从 GitHub 干净检出构建了 [42 个独立 CLI 文件](../../artifacts/receipts/trace-amd64-r5/m2-cli-build.json)及 83 个 Electron 应用文件、6 条 renderer 路由。MCP [双架构 CI](https://github.com/Facetomyself/ruyi-mcp/actions/runs/45313415350)全绿；Trace [托管检查](https://github.com/Facetomyself/ruyitrace/actions/runs/45315913318)因账户计费限制未启动 runner，Trace 源码门禁已在干净检出本机执行。

独立 Trace CLI 可整体搬到新宿主，构建回执记录源码提交、输入洁净程度、依赖锁及逐文件 SHA-256。目标机器仍需 Linux Node 和**本机架构**的审计版 Firefox。要从 Firefox 源码重编，在新 objdir 中走 [Trace 内核构建手册](../../submodules/ruyitrace/docs/linux-build-from-source.md)；它与上面的 CLI/MCP 编译独立。R5 复现标签和归档校验命令见 [源码交接](../../docs/14-source-handoff.md#无需编译先验证-r5-源码确实可取)。

## 3. 执行真实同会话门禁

已审核 AMD64 R5 的三件输入：`candidate.tar.xz`、[runtime-identity.json](../../artifacts/receipts/trace-amd64-r5/runtime-identity.json) 和同包的 [oci-image-acceptance.json](../../artifacts/receipts/trace-amd64-r5/oci-image-acceptance.json)。清单固定 BuildID `20261123161729` 和关键文件摘要。原包保留在有权访问的 AMD64 制品主机 `/home/ruyitrace-amd64-delivery-8jy9TYpn/candidate.tar.xz`，Git 里只存回执。目标机从平台根目录先用 `python3 scripts/verify-trace-release.py --package "$TRACE_ARCHIVE"` 核验归档，再解到新目录；若包内模式为 `0700`，只为运行账号授予解包副本所需的读取/执行权限，容器内仍只读挂载。

下面用源代码 runner 自己创建回环页面并开停 Trace。`FF`、`RECEIPT`、`ACCEPTANCE` 是已核验文件的绝对路径，`QA_ROOT` 是已存在、运行用户可写的新目录。所有进程必须使用同一私有网络空间及运行用户。

```bash
cd "$root/submodules/ruyitrace"
export RUYI_MCP_PYTHON="$root/submodules/ruyi-mcp/.venv/bin/python"
node tests/linux/run_production_mcp_session.mjs \
  --trace-cli "$output/trace-cli/bin/ruyitrace" \
  --firefox "$FF" --receipt "$RECEIPT" --acceptance "$ACCEPTANCE" \
  --mcp-root "$root/submodules/ruyi-mcp" --work "$QA_ROOT"
```

门禁使用两个独立 MCP stdio 客户端，验证排他、同页 DOM 动作、RDP 真暂停/恢复、归还与重借，以及 CLI 停止后的原生 `session_stopped` 和采集读回。另一轮追加 `--owner-stop-while-paused`，检查暂停中发起停止、同页恢复记录和待归还租约的撤销。读取验收回执的 `passed`、各项检查及清理状态，而非仅看进程是否启动。远程使用在 Trace 执行机运行的 MCP，客户机以 SSH stdio 传输；原机的描述符和 Firefox profile 留在原处，新执行机重新启动 owner 并产生独立回执。
