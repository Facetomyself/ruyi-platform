# RuyiTrace

仓库：`Facetomyself/ruyitrace`（private）
挂载：`submodules/ruyitrace`
发布物记录：`artifacts/manifests/ruyitrace-3.5.0-win64.yaml`

## 是什么

定制 Firefox 159（domtrace 插桩）+ Linux CLI，可选 Electron 控制台。用于采集和分析 DOM、点击与脱敏摘要。Linux 命令行开发从 [CLI 手册](../../submodules/ruyitrace/console/cli/README.md) 开始；重建内核看[跨机器构建](../../submodules/ruyitrace/docs/linux-build-from-source.md)。

需要人工操作时用独立的[交互镜像](../../submodules/ruyitrace/product/interactive/README.md)：私有 noVNC 操作同一个 Firefox，断线重连保持同一进程与 run，采集仍走 `capture on/off`；默认不录屏、不记键值、不落轨迹。验收回执见 [`artifacts/receipts/trace-interactive-r5/interactive-image.json`](../../artifacts/receipts/trace-interactive-r5/interactive-image.json)。另有 **opt-in** 的临时公网演示：`demo-public.sh` 在宿主一个已发布预算端口上开随机 48 位 token 路径，可选在页面内自动填写会话码，到点自毁容器与规则；它必须显式提供 `PUBLIC_HOST`，脚本本身不改动防火墙，也不属于默认的仅回环姿态，明文 HTTP 下链接等同会话凭据。

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
