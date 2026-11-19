# ruyitrace 期望目录结构

```
ruyitrace/
├── console/                        ← 从 app.asar/src 抽出，74 文件 / 3644 行
│   ├── src/
│   │   ├── main/                   
│   │   │   ├── main.js             605   Electron 主进程 + Firefox 启停
│   │   │   ├── codex-ipc.js        913   AI 对话页 IPC
│   │   │   ├── codex-config-file.js 276
│   │   │   ├── fingerprint-file.js 240
│   │   │   ├── socks5-proxy.js     231
│   │   │   ├── codex-app-server.js 160
│   │   │   └── profile-paths.js     36
│   │   ├── agent/
│   │   │   ├── worker.mjs          244
│   │   │   ├── python-client.mjs    92
│   │   │   └── browser-tools.mjs    43
│   │   ├── preload/preload.js
│   │   ├── shared/
│   │   │   ├── switches.js         175   ← 74 开关的单一真相源
│   │   │   ├── api-override-controls.js 110
│   │   │   ├── switch-config.mjs   104
│   │   │   ├── firefox-environment.cjs 62   ← env 组装逻辑
│   │   │   ├── browser-fingerprint-schema.json 205
│   │   │   └── …
│   │   └── renderer/               10 个 Vue 视图
│   └── dist/renderer/              Vite 产物
│
├── domtrace/                       ← 反编译还原（新建）
│   ├── config/                     74 开关的读取与校验
│   ├── trace/                      记录写出器（12 类输出）
│   ├── binding/                    DOM 绑定层接入点
│   └── docs/                       规则文档（10 文件，来自发布包）
│
├── kernel/                         ← 内核构建
│   ├── patches/                    对 Firefox 159 的 patch
│   ├── mozconfig/                  Windows / Linux
│   └── build.sh
│
└── docs/
    ├── domtrace-analysis.md        反编译进度
    └── PROVENANCE.md               包 → 内核 commit → 源码
```

## console 源码完整性

| 检查 | 结果 |
| --- | --- |
| 文件数 | 74 |
| 总行数 | 3644 |
| 是否混淆 | 否 |
| Vue 源文件 | ✅ 10 个视图齐全 |
| Vite 产物 | ✅ `dist/renderer/` |

## domtrace 源码缺失

- `kernel/moz-src/` 只有 572 文件 / 12 MB，不含 `dom/bindings/domtrace`
- 反编译对象：`xul.dll` 178 MB
- ground truth：74 个 `MOZ_DOM_*` 字符串 + 完整文档（2659 行 README + 449 行 cheatsheet）
