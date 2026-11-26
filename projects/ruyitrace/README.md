# RuyiTrace

仓库：`Facetomyself/ruyitrace`（private）
挂载：`submodules/ruyitrace`
发布物记录：`artifacts/manifests/ruyitrace-3.5.0-win64.yaml`

## 是什么

定制 Firefox 159（domtrace 插桩）+ Linux CLI，可选 Electron 控制台。用于采集和分析 DOM、点击与脱敏摘要。Linux 命令行开发从 [CLI 手册](../../submodules/ruyitrace/console/cli/README.md) 开始；重建内核看[跨机器构建](../../submodules/ruyitrace/docs/linux-build-from-source.md)。

需要人工操作时用独立的[交互镜像](../../submodules/ruyitrace/product/interactive/README.md)：私有 noVNC 操作同一个 Firefox，断线重连保持同一进程与 run，采集仍走 `capture on/off`；默认不录屏、不记键值、不落轨迹。验收回执见 [`artifacts/receipts/trace-interactive-r5/interactive-image.json`](../../artifacts/receipts/trace-interactive-r5/interactive-image.json)。短时分享另走[独立 TLS 网关与可核对的租约回收](../../submodules/ruyitrace/product/interactive/public-demo.md)：预授权精确来源和绑定地址，通过一次性邀请兑换 Secure/HttpOnly 会话，默认 20 分钟；撤销/到期先断开已连接的桌面，再让 CLI 收尾。systemd 为中途失败及跨启动的遗留资源对账，服务从不管理防火墙。旧明文入口已停用；不影响镜像标签或私有工作流。[正式归档重新验收](../../artifacts/receipts/trace-interactive-r5/README.md)与[网关回环实机回执](../../artifacts/receipts/trace-public-lease-v1/README.md)分开记录。

**ARM64 R5 已正式发布**：[私有 GitHub Release](https://github.com/Facetomyself/ruyitrace/releases/tag/arm64-r5-cli2-lease-v1) · [部署手册](../../submodules/ruyitrace/product/arm64/README.md) · [实机证据及原始回执](../../artifacts/receipts/trace-arm64-native-lease/README.md)。`oracle-reverse-dev`（4 OCPU / 24 GB）原生编译 Firefox 159 `20261125162841`，空引擎从真实归档加载 CLI、私有交互、TLS Edge 三个 ARM 镜像。另一台物理机 `oracle-dsh` 的 Firefox 从公网完成邀请兑换、WSS 桌面、重连和主动撤销。生产站点空闲时不开放桌面；SSH、证书续期和回收定时器保持运行。此结论不借用历史 ARM 包、TLS 健康页或 amd64 回执。

**`oracle-reverse-dev` 日常入口**：以 `ubuntu` 运行 `/home/ubuntu/.local/bin/ruyitrace`。当前 `r5-arm64-site2`、回滚 `r5-arm64-site1`；`check` 核对状态，`verify` 重算归档 SHA 并实跑三镜像读回与原生 Firefox，`desktop` 才领取默认 20 分钟的一次性 HTTPS 邀请。两版实装、忙时准入、真实回滚及管理器中断恢复都已验证。见[固定版操作手册](../../submodules/ruyitrace/product/arm64/site/README.md)、[私有站点发行](https://github.com/Facetomyself/ruyitrace/releases/tag/arm64-site-ops-v1)和[60 份实机运维回执](../../artifacts/receipts/trace-arm64-site-operations/README.md)。

**新增原生事件（独立私有预发行，不切站点）**：[Alpha 1 下载与取证](https://github.com/Facetomyself/ruyitrace/releases/tag/native-events-v0.1.0-alpha.1) 在真实 amd64、ARM64 Firefox 上各跑 17 项：显式标定的 JSCall、Wasm 导出边界、指定回环 GET/重定向/缓存事务。每个架构另有 22 个旧镜像页面/协议对照，绝不计入新原生覆盖。Alpha 1 的帧模式明确返回 `unsupported`，不是零帧通过。原始观测、错来源/关闭反例、完整归档摘要及[可复核的范围](../../artifacts/receipts/trace-linux-gap-closure-v1/README.md)与旧 R5 及 Win64 静态开关分列。

**应用 WebSocket 帧另验**：在原版 `libxul` 仅能报告“不支持”的地方，ARM64 已原生重编元数据专用接口并通过[同镜像的 22 项独立复核](../../artifacts/receipts/trace-linux-gap-closure-v1/patched-websocket/README.md)。真实端点与浏览器原生 writer 分别观察到发送 3 帧、接收 5 帧；页面只收到 2 条消息。编译、Firefox 原归档的 56 个成员和最终镜像均绑定到实际字节。此 ARM 回执不为其它架构、委托 socket 传输或公网站点代签。

**Electron 持有者是另一条发行线**：[两架构桌面预发行与中文现场包](https://github.com/Facetomyself/ruyitrace/releases/tag/linux-electron-owner-v0.1.0-alpha.1)。正式打包的 Electron 主进程直接持有同一个 Firefox/BiDi，真实 MCP 借还、排他和旧句柄拦截、暂停中停止、借用进程丢失/到期、Firefox 异常退出均按架构保留独立计时和落盘佐证。它不是旧 amd64 CLI-owner 的复用证明。详见[范围与原始读回](../../artifacts/receipts/trace-linux-gap-closure-v1/electron-owner/README.md)。Xvfb/Weston 支持会话生命周期验收；实体显示与本地人工系统输入法仍须现场观测。

同一 Firefox 会话的 MCP 接入见 [ruyi-mcp 与组件边界](../../docs/01-architecture.md#5-ruyi-mcp-控制面与组件边界)。

## 三层

| 层 | 体积 | 源码状态 |
| --- | --- | --- |
| Electron 控制台 | 1.4 MB / 74 文件 / 3644 行 | ✅ 完整（从 app.asar 抽出） |
| 定制 Firefox 内核 | `firefox.exe` 188 MB + `xul.dll` 178 MB | Win64 私有源未发布；Linux 重建子集见下方正式包验收 |
| 内部 ruyijs wheel | 46.6 MB | 归档物，不参与运行时 |

## 源码入口

```
ruyitrace/
├── console/                     Electron 源码 74 文件
│   ├── main/                main.js 605 / codex-ipc.js 913 / fingerprint-file.js 240
│   ├── renderer/            10 个 Vue 视图
│   ├── shared/              switches.js 175（74 开关单一真相源）
│   └── tooling/                 Node 锁文件与控制台构建、组装入口
├── domtrace/                    反编译还原的内核插桩源码
│   ├── binding/                 DOM 绑定层接入点
│   ├── trace/                   记录写出器
│   └── config/                  74 个开关的读取与校验
├── tests/linux/                 审计构建、打包与隔离验收入口
└── docs/                        组件手册；Win64 专项另见交接分支
```

## domtrace 关键事实

| 项 | 值 |
| --- | --- |
| 开关数 | **74**（`switches.js` 与 `xul.dll` strings 一致） |
| 文档声称 | 69（cheatsheet 陈旧） |
| JS 队列参数 | `MOZ_DOM_HTTP_PACKET_TRACE_MAX_PENDING` 由随包 JS 读取，与原生开关清单分开，见 [C2 勘误](../../docs/04-risks-and-gaps.md#c2--moz_dom_http_packet_trace_max_pending-的读取层) |
| 源码 | ❌ 不在包内，`moz-src/` 只有 572 文件删减片段 |
| 输出 | 12 类文件（jsonl / bin / wasm / packet） |

## 复现一条 trace（不需要 Electron）

照 `console/shared/firefox-environment.cjs` 的三步逻辑即可：

1. 剔除父进程所有 `MOZ_DOM_*`
2. 写入开关
3. 补 `MOZ_DOM_TRACE_RUN_ID`

## 当前状态

以[平台源码与构建交接](../../docs/14-source-handoff.md)区分正式包、候选管理面和离线证据。Linux domtrace 子集已经编译、打包并在真实 Firefox 上采集，详见[运行验收历史](../../docs/13-ruyitrace-progress.md)；原 Win64 私有内核源树并未随包发布。下表是历史输出格式还原清单，不是 Linux 全量 producer 的运行验收清单。

## 输出格式进度

| # | 输出 | 触发开关 | 状态 |
| ---: | --- | --- | --- |
| 1 | `domtrace\trace_process_<pid>.jsonl` | `MOZ_DOM_TRACE` | ✅ 已实现 |
| 2 | `jscall\trace_jscall_*.bin` | `MOZ_DOM_JSCALL_TRACE` | ✅ 已实现，端到端解码验证 |
| 3 | `cookie\trace_cookie_process_<pid>.jsonl` | 核心跟随 | ✅ 已实现 |
| 4 | `storage\trace_storage_process_<pid>.jsonl` | 核心跟随 | ✅ 已实现 |
| 5 | `eval\trace_eval_process_<pid>.jsonl` | 核心跟随 | ✅ 已实现 |
| 6 | `event\trace_event_process_<pid>.jsonl` | 核心跟随 | ✅ 已实现 |
| 7 | `descriptor\trace_descriptor_process_<pid>.jsonl` | 核心跟随 | ✅ 已实现 |
| 8 | `exception\trace_exception_process_<pid>.jsonl` | `MOZ_DOM_EXCEPTION_TRACE` | ✅ 已实现 |
| 9 | `wasm\trace_wasm_process_<pid>.jsonl` | `MOZ_DOM_WASM_CALL` / `_INSN` | ✅ 已实现（键名部分推断） |
| 10 | `wasm\wasm_<sha256>_<len>.wasm` | `MOZ_DOM_WASM_DUMP` | ✅ 已实现 |
| 11 | `env\env_inventory_<pid>_<session>.json` | `MOZ_DOM_ENV_INVENTORY` | ⏸ 无字段依据，等样本 |
| 12 | `http_packet\*.http_packet.json` + `index.jsonl` | `MOZ_DOM_HTTP_PACKET_TRACE` | ✅ 已实现 |
| 13 | `websocket_frames.jsonl` | `MOZ_DOM_WS_TRACE` | ✅ 已实现 |

进度 **12/13**（1 项等样本）（cheatsheet 的 12 类是合并了 wasm 的两项，拆分后是 13 项）。

### 已验证的实现

- `domtrace/trace/jscall-writer.cpp` —— 写出的 .bin 能被发布方
  `tools/jscall_decode.py` 正确解码（call_id / depth / name / url /
  entry_path / detail 值全部正确）
- `domtrace/trace/trace-record.cpp` —— 核心 jsonl 行被 Python `json.loads`
  解析通过，19 个字段，无裸换行
