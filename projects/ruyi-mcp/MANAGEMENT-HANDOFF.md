# Firefox 管理面：本地 QA 与会话交接

面向回环测试页的日常 QA：**人用 RuyiTrace Electron 控制台看配置、进程和日志；自动化客户用 ruyi-mcp；借用现有会话时，Trace owner 仍是 Firefox 与 BiDi 的唯一所有者。** 交接时分别记桌面 UI、MCP 协议、浏览器动作、RDP 和内核采集结果。[组件边界](../../docs/01-architecture.md#5-ruyi-mcp-控制面与组件边界)

## 分工与现有证据

| 层 | 接口与职责 | 已具备 / 待验收 |
| --- | --- | --- |
| **RuyiTrace Electron** | 主进程与 preload 管理桌面配置、选定内核、启停采集和分页预览；renderer 显示 DOM、点击与脱敏 Storage 记录。[主进程](../../submodules/ruyitrace/console/main/main.js) | x86_64 `d7DBYN4g` 和 ARM64 `gIhdRoB6` 均有真实 Firefox 采集及同包 Electron 回执；各有虚拟 X11/Wayland 启动证据，物理显示另验。证据来自 Trace 自身，MCP 未参与。[Trace 进度](../../docs/13-ruyitrace-progress.md) |
| **ruyi-mcp** | [Node/TypeScript stdio 入口](../../submodules/ruyi-mcp/src/index.ts) 提供工具与生命周期；[Python bridge](../../submodules/ruyi-mcp/bridge/ruyi_bridge.py) 接 ruyiPage；[RDP](../../submodules/ruyi-mcp/src/rdp/)与 BiDi 自动化各自留证。MCP 自启时管理自己的 Firefox 和临时 profile。 | 平台固定 `1c80d88` 的 Linux 无浏览器记录：64 项 Python、16 项 Node 加 MCP smoke 通过，覆盖真实 bridge 冷启动、协议、工具发现、退出与 RDP 协议单测。真实 Linux Firefox 的 BiDi/下载/RDP 和全链回收仍待验收。[Linux 验收](../../submodules/ruyi-mcp/docs/linux-port.md) |
| **Trace owner + 借用客户端** | owner 创建并持有唯一 BiDi session，发布权限受限的描述文件和回环 IPC；MCP 取租约并通过 owner 转发页面操作，可单独连接回环 RDP。恢复/断开调试和释放租约后，由 owner 执行生产采集的 flush 与封存。借用态的 `ruyi_browser_quit` 走释放分支，保留 owner 的 Firefox。[借用工具](../../submodules/ruyi-mcp/src/tools/borrowed-session.ts) · [关闭路径](../../submodules/ruyi-mcp/src/ruyi-context.ts) | Trace 独立分支 `handoff/owner-arm64-fixture-20261124` 的 `b4ba3a8` 已有审计后的 ARM64 Firefox fixture：用配套 MCP stage-1 借用客户端验过状态、租约排他和释放重取、进程丢失；租约活跃时由固定测试页触发的基础 DOM ON/OFF 有记录。此分支与平台默认 Trace pin 分开；fixture 只实现状态/获取/释放，`rdp: null`，未验证 Electron 发布 descriptor、MCP 转发页面动作、RDP 暂停恢复或生产 flush。独立分支说明见 `docs/trace-arm64-fixture-owner.md`。 |
| **RuyiHttp / RuyiJS** | 用同一合成输入分别做 HTTP 和 JS/DOM 对照，各自运行、各自记录版本和结果。 | 两者均为并行参考，MCP 启动和借用的验收无需引入其原生库或 JS 壳。[平台状态](../../STATUS.yaml) |

### 待集成的无头 CLI

Trace 私有仓的[管理 CLI 候选](https://github.com/Facetomyself/ruyitrace/tree/1452154c64437b00494c005cbd54a5003c77def3)与 Electron 并列；它不是另一个 MCP 服务，也未加入 R5 内核。2026-11-24 从 GitHub 的干净副本依锁构建出 77 个应用文件、6 个 renderer 路由和可执行的 `bin/ruyitrace`。CLI 与组装各有 8 项通过；有真实页面动作的生产生命周期尚待签收。先验证 `run --gate auto` 是否在同一 marker 上重复开闸，再接生产 owner/租约并跑 M2。构建复现见[源码交接](../../docs/14-source-handoff.md)。

## 各项目的本地构建与测试入口

在对应组件的隔离工作副本执行，先备齐锁定依赖。命令用于复现指定层次，产物和测试回执放到每次新建的 QA 目录；它们并非本次文档更新产生的新测试结果。

| 组件 | 在组件根目录运行 | 产物或覆盖范围 |
| --- | --- | --- |
| [ruyi-mcp](README.md) | `export RUYI_MCP_PYTHON="$PWD/.venv/bin/python"`；`npm run check` | Node 构建、Python 契约与 bridge、stdio/工具/生命周期、RDP 协议单测；无需 Firefox。 |
| [RuyiTrace](../../submodules/ruyitrace/tests/linux/README.md) | `bash tests/run-tests.sh`；`python3 -B -m unittest discover -s tests/linux -p 'test_*.py'` | 原生数据布局/接线及 Linux 资格、打包、回执等回归；用于区分模型、合成数据与真实采集。 |
| [RuyiTrace Electron](../../submodules/ruyitrace/console/tooling/build-linux.mjs) | `node console/tooling/build-linux.mjs "$QA_ROOT/trace-app"` | Node ≥22.12，先备齐 `console/tooling` 锁定依赖；`QA_ROOT` 为本次可写绝对目录，`trace-app` 尚不存在。仅打包应用目录，不含 Electron 或 Firefox。 |
| [RuyiHttp](../ruyihttp/README.md) | `python3 -B -m unittest discover -s tests`；`python3 -B tools/verify_runtime.py`；在 amd64 目标环境预装 `setuptools >= 77` 和 `wheel` 后：`RUYIHTTP_PLATFORM=linux_x86_64 RUYIHTTP_GLIBC=2.39 python3 -m pip wheel --no-index --no-deps --no-build-isolation -w "$QA_ROOT/http-wheels" .` | 验证契约和入库库文件；用既有库重打 wheel，不编译 Necko/NSS。历史 amd64 实测为 glibc 2.39、HTTPS/TLS 1.3/h2；H3 和代理另验。 |
| [RuyiJS 内部版](../ruyijs/README.md) | `python3 -B ci/test_linux_donor.py`；`cmake -S src/client -B "$QA_ROOT/js-client" -DCMAKE_CXX_COMPILER=clang++-21`；`cmake --build "$QA_ROOT/js-client"` | donor 输入单测与 Linux C ABI 客户端库。整壳 `dist/js` 与实际 `Context.eval` 仍待验收；客户端构建结果只覆盖传输层。[客户端 CMake](../../submodules/ruyijs/src/client/CMakeLists.txt) |

## 下一阶段验收表

为每次运行保留一个新 profile 和一个回环 fixture；按组件、架构与制品分别填行。前置条件缺失记 `blocked`，尚未运行记 `not-run`，执行失败保留错误与退出码。

| 门禁 / 当前状态 | 操作 | 通过证据 |
| --- | --- | --- |
| **M0 无浏览器 / 已通过** | 在准备好的 Linux 工作副本执行 `npm run check`。用 stdio 客户端依次发 `initialize`、`tools/list`、`ruyi_browser_status {}`，再关闭 stdin；另一次走 SIGTERM。 | MCP stdout 只有协议消息；实际 Python bridge 就绪、`alive: false`、进程退出且 bridge 子进程回收。 |
| **M1 MCP 自启原生 Firefox / 待验收** | 固定本机架构的 Firefox 路径、版本、BuildID 和制品 SHA-256。运行下方已有脚本；另经 stdio 在本地 fixture 执行建页、读取或点击、下载、退出。 | 回环页面结果、五项 automation 报告、RDP 报告及断点暂停/恢复证据；对照文件内容校验下载，确认本次 PID 与临时 profile 回收。系统 Firefox 的结果只证明对应构建。 |
| **M2 生产 Trace owner 同会话 / 待验收** | 使用能发布真实 descriptor、支持页面命令和 RDP 的生产 owner。以 `ruyi_attach_trace_session` 获取租约；第二个客户端尝试借用，应被挡住。运行回环页的 query/click，单独验 RDP 断点暂停/恢复；调用 `ruyi_browser_quit` 后由 owner 停止并 flush；再做过期或进程丢失的独立负例。 | attach/detach 前后为同一 Firefox PID 与启动代次、同一 BiDi context，未创建第二条 BiDi session；退出后角色归还、owner Firefox 仍存活。owner 停止后登记完整 DOMTrace 的行数及哈希，并实际读回结果。独立 ARM64 fixture 的基础 DOM ON/OFF 可作前置对照，不能替代此项。 |
| **M3 容器 / 设计阶段** | 先实现 `core` 镜像，在原生 arm64/amd64 重跑 M0（包括 EOF 与 SIGTERM）；再用匹配架构、可核对制品身份的 `browser` 镜像重跑 M1。容器内借用会话另跑 M2。 | 每架构独立镜像 digest、stdio/回收结果和原生浏览器证据；profile、下载与证据目录隔离。当前平台 pin 尚无 Dockerfile 或验收镜像。[Docker 阶段](../../submodules/ruyi-mcp/docs/docker-design.md#5-分阶段验收) |

M1 的现成脚本（从 MCP 组件根目录运行，`RUYI_FIREFOX_PATH` 指向匹配架构的已验证 Firefox 绝对路径，`QA_ROOT` 指向本次空的可写绝对目录）：

```bash
: "${RUYI_FIREFOX_PATH:?请指定验收 Firefox 的绝对路径}"
: "${QA_ROOT:?请指定本次 QA 目录的绝对路径}"
export RUYI_FIREFOX_PATH
export RUYI_MCP_PYTHON="$PWD/.venv/bin/python"
export RUYI_MCP_PROFILE_ROOT="$QA_ROOT/profiles"
export RUYI_RDP_EVIDENCE_ROOT="$QA_ROOT/rdp"
export RUYI_RDP_INTERVENTION_ROOT="$QA_ROOT/rdp-intervention"
file -- "$RUYI_FIREFOX_PATH"
sha256sum -- "$RUYI_FIREFOX_PATH"
"$RUYI_FIREFOX_PATH" --version
"$RUYI_MCP_PYTHON" scripts/run-automation-gates.py --firefox "$RUYI_FIREFOX_PATH" --output "$QA_ROOT/automation"
npm run check:rdp-runtime
npm run check:rdp-intervention
```

## 示例约定

- **输入**：仅使用合成数据。fixture 绑定 `127.0.0.1` 的临时端口，`/qa.html` 有稳定选择器 `#run-qa`、`#qa-result`；一次点击将结果从 `ready` 改为 `done`。下载用固定字节和预先记录的 SHA-256。项目对照固定 `fixture_id` 与输入摘要。
- **工具参数**：独立会话使用 `ruyi_new_page`，例如 `{"url":"http://127.0.0.1:18765/qa.html","headless":true}`（端口以实际监听值替换）。借用会话在 owner 发布真实描述文件后调用 `ruyi_attach_trace_session`，参数 `{"sessionPath":"/absolute/private/session.json"}`；接着向 `ruyi_trace_control` 传 `{"action":"click","selector":"#run-qa","timeoutMs":3000}`，再 query `#qa-result`。这是生产联验约定；独立 ARM64 fixture 只用于状态与租约，页面动作由该 fixture 自己触发。
- **回执**：用同一 `run_id` 关联 `fixture_id`、组件提交、架构、Firefox 版本/BuildID/制品 SHA-256、浏览器 PID 与启动代次、上下文 ID 摘要、退出码和证据路径。分别入档 `mcp-stdio`、`bidi`、`rdp`、`domtrace`、`desktop`，缺项记明状态。归档仅收脱敏结果及摘要；描述文件、租约能力值和临时 profile 留在权限受限的运行目录，由对应 owner 回收。
