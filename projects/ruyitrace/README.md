# RuyiTrace

仓库：`Facetomyself/ruyitrace`（private，待建）
挂载：`submodules/ruyitrace`
发布物记录：`artifacts/manifests/ruyitrace-3.5.0-win64.yaml`

## 是什么

定制 Firefox 159（domtrace 插桩）+ Electron 控制台。用于跑 domtrace 探针、分析抓取结果。

## 三层

| 层 | 体积 | 源码状态 |
| --- | --- | --- |
| Electron 控制台 | 1.4 MB / 74 文件 / 3644 行 | ✅ 完整（从 app.asar 抽出） |
| 定制 Firefox 内核 | `firefox.exe` 188 MB + `xul.dll` 178 MB | ❌ **domtrace 插桩需反编译** |
| 内部 ruyijs wheel | 46.6 MB | 归档物，不参与运行时 |

## 期望目录

```
ruyitrace/
├── console/                     Electron 源码 74 文件
│   ├── src/main/                main.js 605 / codex-ipc.js 913 / fingerprint-file.js 240
│   ├── src/renderer/            10 个 Vue 视图
│   ├── src/shared/              switches.js 175（74 开关单一真相源）
│   └── dist/renderer/           Vite 产物
├── domtrace/                    反编译还原的内核插桩源码
│   ├── binding/                 DOM 绑定层接入点
│   ├── trace/                   记录写出器
│   └── config/                  74 个开关的读取与校验
├── kernel/                      内核构建脚本与 patch
└── docs/                        domtrace-analysis.md
```

## domtrace 关键事实

| 项 | 值 |
| --- | --- |
| 开关数 | **74**（`switches.js` 与 `xul.dll` strings 一致） |
| 文档声称 | 69（cheatsheet 陈旧） |
| 幽灵开关 | `MOZ_DOM_HTTP_PACKET_TRACE_MAX_PENDING`（文档有，内核无） |
| 源码 | ❌ 不在包内，`moz-src/` 只有 572 文件删减片段 |
| 输出 | 12 类文件（jsonl / bin / wasm / packet） |

## 复现一条 trace（不需要 Electron）

照 `console/src/shared/firefox-environment.cjs` 的三步逻辑即可：

1. 剔除父进程所有 `MOZ_DOM_*`
2. 写入开关
3. 补 `MOZ_DOM_TRACE_RUN_ID`

## 当前状态

控制台 100%，domtrace 0%。反编译方案见 [`../../docs/05-reverse-analysis.md`](../../docs/05-reverse-analysis.md)。
