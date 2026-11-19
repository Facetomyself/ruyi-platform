# 00 · 一页索引

从哪进，看什么。

---

## 我是新来的

**最快：读 [`../HANDOVER.md`](../HANDOVER.md)** —— 10 分钟知道做了什么、做到哪、卡在哪。

然后读这三份，按顺序：

1. [`../README.md`](../README.md) —— 本仓是什么、拓扑长什么样
2. [`01-architecture.md`](01-architecture.md) —— 三件套怎么连
3. [`../PINS.md`](../PINS.md) —— 所有版本号在哪查

---

## 我要做某件具体的事

| 我要… | 看这里 |
| --- | --- |
| 搞清三个项目的边界 | [`01-architecture.md`](01-architecture.md) |
| 拿到某个项目的源码 | [`02-source-recovery.md`](02-source-recovery.md) |
| 把某层移植到 Linux | [`03-linux-port.md`](03-linux-port.md) |
| 知道现在卡在哪 | [`04-risks-and-gaps.md`](04-risks-and-gaps.md) + [`../STATUS.yaml`](../STATUS.yaml) |
| 反编译 domtrace 内核 | [`05-reverse-analysis.md`](05-reverse-analysis.md) |
| **domtrace 该插在哪** | [`../projects/ruyitrace/instrumentation-sites.md`](../projects/ruyitrace/instrumentation-sites.md) |
| **要改 Codegen 的哪几处** | [`../projects/ruyitrace/codegen-changes.md`](../projects/ruyitrace/codegen-changes.md) |
| 反编译 ruyijs 内部版 | [`06-ruyijs-inner.md`](06-ruyijs-inner.md) |
| 要在哪台机器上构建 | [`07-build-hosts.md`](07-build-hosts.md) |
| **哪些结论可信、哪些是推断** | [`09-evidence-ledger.md`](09-evidence-ledger.md) |
| **有机器后怎么跑** | [`10-build-runbook.md`](10-build-runbook.md) |
| 要不要补 aarch64 原生库 | [`11-aarch64-assessment.md`](11-aarch64-assessment.md) |
| 从零复现这个状态 | [`../REPRODUCE.md`](../REPRODUCE.md) |
| 写/改文档 | [`../conventions.md`](../conventions.md) |
| 提交前自检 | [`../conventions.md`](../conventions.md) §12 |

---

## 三条主线的当前位置

```
RuyiHttp ────────●──────────────────── 源码 100%，测试 19/19 全绿
                 │                     剩 glibc 2.38（需 24.04 主机）

RuyiJS 内部版 ───●────○────────────── Python 层明文；js.exe 反编译进行中
                 │                    2038 identity 中 56 命中

RuyiTrace ───────●────●●●○─────────── 控制台 100%
                       │               domtrace: 开关 74/74, 输出 1/12
```

`●` = 完成　`○` = 待做

### domtrace 细分

| 层 | 进度 |
| --- | --- |
| 开关读取点定位 | **74/74** |
| 开关读取语义 | **74/74**（10 种解析模式） |
| jscall bin 写入器 | **1/1**（端到端被发布方解码器验证） |
| 其余 11 类输出 | 0/11 |

## 一分钟版本

| 项目 | 一句话 |
| --- | --- |
| **RuyiHttp** | Firefox Necko/NSS 的 Requests 风格客户端。源码完整，三平台原生库齐全（24 MB）。挡路的是 glibc 2.38 和 6 个 Windows 断言测试。 |
| **RuyiJS** | 内部 wheel ≠ 公开 ff-ruyijs。Python 层 19 文件是明文，`js.exe`（49.5 MB）需反编译。有 2038 条源文件 hash 作 ground truth。 |
| **RuyiTrace** | Electron 控制台源码完整（74 文件）。内核 domtrace 插桩无源码，需反编译 178 MB 的 `xul.dll`。这是最重的一块。 |

---

## 关键数字

| 项 | 值 |
| --- | --- |
| 唯一 Firefox 基线 | `39bfd14cb45c` / BuildID `20261101193257` |
| necko ABI | 31 个 C 符号 |
| 原生库体积 | win 7.2 MB + darwin 8.2 MB + linux 8.4 MB = 24 MB（入库） |
| domtrace 开关 | **74**（`switches.js` 与 `xul.dll` 一致；文档写 69 是旧的） |
| ruyijs RPC operation | 待枚举（19 个 `.py` 里全有） |
| glibc 底线 | 2.38 |

---

## 目录速查

```
ruyi-platform/
├── README.md              本仓定位、拓扑、规则
├── PINS.md                所有版本号
├── STATUS.yaml            机器可读状态
├── conventions.md         文档规范
├── docs/                  跨项目结论（唯一权威）
├── projects/              单项目文档
├── artifacts/manifests/   发布物 hash 记录
├── scripts/               校验脚本
├── submodules/            ruyihttp / ruyijs / ruyitrace
└── upstream/              只读参考（gitignore）
```
