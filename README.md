# ruyi-platform

Ruyi 三件套、RuyiDOM 与自动化控制面 **ruyi-mcp** 的文档总入口：结构规划、源码还原与跨平台工程化。

代码在各组件仓维护。四个现有组件由 submodule 接入；[RuyiDOM](docs/14-source-handoff.md#ruyidom-独立源码交接) 是独立维护仓，单独检出。本仓负责说明各组件的边界、还原、移植与验收方式。

---

## 一、仓库定位

| | 本仓 | 代码仓 |
| --- | --- | --- |
| 职责 | 文档、规划、还原分析、移植路线、验收标准 | 各自的产品代码与构建 |
| 内容 | Markdown + 少量校验脚本 | 源码 + 原生库 + 测试 |
| 更新频率 | 每次结论变化 | 每次代码变化 |
| 可见性 | private | 按项目分别设定，见 §三 |

**本仓是唯一的事实来源（single source of truth）**：三件套的版本矩阵、ABI 契约、缺口清单都以本仓为准。代码仓里的 README 是入口，不是权威。

---

## 二、仓库拓扑

```
ruyi-platform (private, 本仓)
├── submodules/
│   ├── ruyihttp      → Facetomyself/ruyihttp        (public)   ← RuyiHttp 代码
│   ├── ruyijs        → Facetomyself/ruyijs-inner    (private)  ← 内部版反编译 + 工程化
│   ├── ruyitrace     → Facetomyself/ruyitrace       (private)  ← RuyiTrace 主体
│   └── ruyi-mcp      → Facetomyself/ruyi-mcp        (public)   ← Linux 自动化与调试控制面
│
├── upstream/         只读参考（不挂 submodule）
│   ├── ff-ruyijs     → Facetomyself/ff-ruyijs        (public fork)
│   │                    用途：① 向上游 cutetailbud 提 PR；② 反编译时的对照基线
│   │                    禁止：把它的代码当作内部版来源
│   └── firefox       → mozilla-firefox/firefox      只记 commit
│
└── docs/             全部规划与结论（唯一权威）
```

### RuyiJS 的三层关系（**重要，不要混**）

| 层 | 仓库 | 性质 | 允许做什么 |
| --- | --- | --- | --- |
| 开源上游 | `cutetailbud/ff-ruyijs` | public | 只读 |
| 我们的 fork | `Facetomyself/ff-ruyijs` | public | **只做 PR 贡献 + 反编译对照**，不当内部版基线 |
| **内部版** | `Facetomyself/ruyijs-inner` | **private** | **反编译分析 + 工程化 + 语义化**，内部 wheel 的唯一来源 |

**硬规则**：

1. `ff-ruyijs` 是公开仓库，**不承载内部功能**。内部改动一律进 `ruyijs-inner`。
2. `ruyijs-inner` 的源码来自**对内部 wheel 的反编译还原**，而不是从 `ff-ruyijs` 抄。
3. `ff-ruyijs` 只用于两件事：给上游提 PR；反编译时当「公开实现长什么样」的对照物。
4. 内部版要向 `ff-ruyijs` 回流的能力，走 PR 流程单向流出，不回灌。

### 为什么 ff-ruyijs 不挂 submodule

因为它**不是内部产品的组成部分**，只是外部参考：

1. **PR 目标**——上游修复要回流到 `cutetailbud/ff-ruyijs`，走 public fork。
2. **反编译对照**——还原内部版时，需要知道「官方公开实现是怎么写的」，但这只是参照，不是来源。

挂成 submodule 会让人误以为内部版基于它构建。实际关系是：**内部版独立反编译，ff-ruyijs 提供语义参照。**

所以本仓只记录它指向的 commit（见 `PINS.md` §3），不引入代码。

### 为什么 RuyiTrace 单独建私有库

RuyiTrace 有三块互不重叠的内容，混在一个仓里会互相污染版本节奏：

| 块 | 性质 | 放哪 |
| --- | --- | --- |
| Electron 控制台（74 文件 / 3644 行） | 已有完整源码 | `ruyitrace/console/` |
| domtrace 内核（Firefox 159 插桩） | **需反编译还原** | `ruyitrace/domtrace/` |
| 发布产物与校验 | 557 MB zip，不入 git | 只记 manifest |

反编译工作会产生大量中间产物与迭代，独立成库便于本地推进，也便于将来单独开源或闭源。

---

## 三、submodule 清单

| 目录 | 远端 | 可见性 | 状态 | 说明 |
| --- | --- | --- | --- | --- |
| `submodules/ruyihttp` | `Facetomyself/ruyihttp` | **public**（2026-11-20 起） | ✅ 已有 | 完整源码树，含 26 个原生库文件 |
| `submodules/ruyijs` | `Facetomyself/ruyijs-inner` | private | ✅ 已有（2026-11-04） | **内部版反编译产物 + 工程化源码**，wheel 的唯一来源 |
| `submodules/ruyitrace` | `Facetomyself/ruyitrace` | private | ✅ 已有 | 控制台 + domtrace 还原 + 发布清单 |
| `submodules/ruyi-mcp` | `Facetomyself/ruyi-mcp` | public | ✅ 已纳管 | [MCP 项目入口](projects/ruyi-mcp/README.md)：Linux 控制面、Firefox 与 Trace 共会话 |

**不在 submodule 里**：`Facetomyself/ff-ruyijs`（public fork，只做 PR 与反编译对照）。

ruyi-mcp 以 [固定 gitlink](PINS.md#9-ruyi-mcp) 接入，同时继续在组件仓 `linux` 分支独立维护。它连接 RuyiTrace 的 Firefox 运行时，与 RuyiJS、RuyiHttp 的关系见 [组件架构](docs/01-architecture.md#5-ruyi-mcp-控制面与组件边界)。原生组件的 Firefox、NSS、Neqo 基线各自见 [PINS](PINS.md)，MCP 源码 pin 与浏览器发布制品独立。

---

## 四、目录结构与文件职责

```
ruyi-platform/
├── README.md                     ← 本文件
├── PINS.md                       ← 所有外部依赖的固定版本
├── STATUS.yaml                   ← 项目当前状态机（机器可读）
├── TIMELINE.md                   ← 工作主线（为何做、遇到什么、怎么解决）
├── HANDOVER.md                   ← 阶段总结与交接
├── REPRODUCE.md                  ← 从零到当前状态的完整路径（已实测）
├── conventions.md                ← 文档规范（必读）
├── .gitignore / .gitmodules
│
├── docs/                         ← 跨项目横向结论（唯一权威）
│   ├── 00-quickmap.md            ← 一页索引
│   ├── 01-architecture.md        ← 架构与数据流
│   ├── 02-source-recovery.md     ← 源码还原路线
│   ├── 03-linux-port.md          ← Linux 适配路线
│   ├── 04-risks-and-gaps.md      ← 缺口与待决策
│   ├── 05-reverse-analysis.md    ← 反编译方法论
│   ├── 06-ruyijs-inner.md        ← 内部版反编译与工程化方案
│   ├── 07-build-hosts.md         ← 构建主机调查
│   ├── 08-firefox-commit-provenance.md ← Firefox commit 归属
│   ├── 09-evidence-ledger.md     ← 证据等级总账
│   ├── 10-build-runbook.md       ← 构建执行清单
│   ├── 11-aarch64-assessment.md  ← linux_aarch64 可行性
│   ├── 12-real-build-findings.md ← 真实构建验证结论
│   ├── 13-ruyitrace-progress.md  ← RuyiTrace 整体进度评估
│   └── adr/                      ← 架构决策记录
│
├── projects/                     ← 单项目纵向文档
│   ├── ruyihttp/                 README / structure / CHANGELOG
│   ├── ruyijs/                   README / structure / reverse-analysis
│   │                             / operation-dispatch / CHANGELOG
│   ├── ruyitrace/                README / structure / domtrace-analysis
│   └── ruyi-mcp/                 README / CHANGELOG
│                                 / domtrace-contract / domtrace-readers
│                                 / instrumentation-sites / codegen-changes
│                                 / outputs-remaining / CHANGELOG
│
├── artifacts/                    ← 发布物清单（不含二进制）
│   ├── README.md
│   └── manifests/                4 份发布物记录（ruyijs ×2 / ruyitrace ×1）
│
├── scripts/                      ← 校验与反编译辅助脚本（15 个）
├── submodules/                   ← git submodule
└── upstream/                     ← 只读参考（代码 gitignore，只留说明）
```

### 为什么 `docs/` 和 `projects/` 分开

- `docs/` 是**跨项目的横向结论**：架构关联、还原路线、移植路线、缺口。
- `projects/` 是**单项目的纵向文档**：这个项目怎么建、怎么测、改了什么。

一条结论只能出现在一个地方，另一处必须链接过去，不允许复制。

---

## 五、写文档的硬规则

详见 `conventions.md`，这里只列最关键的六条：

1. **每个结论必须带可复现命令**。写「需要 glibc 2.38」，必须同时给 `objdump -T ... | grep GLIBC_` 的命令。
2. **未知用 `Unknown` / `To be confirmed` / `Not yet documented`，不猜。** 反编译未完成的部分必须有明确进度标记。
3. **三个 commit 编号必须写全**：Firefox commit、ff-ruyijs commit、wheel sha256。缺一个就是不可追溯。
4. **二进制只记 SHA256 与来源 URL**，不入 git。唯一例外是原生库（见 §六）。
5. **修正必须留痕**：被推翻的判断不删除，改为删除线 + 「更正」段落 + 原因，并在 `docs/04-risks-and-gaps.md` 末尾「更正记录」表加一行。
6. **文档里的路径一律相对仓库根**，绝对路径只出现在可执行命令块里。

---

## 六、二进制策略

| 类型 | 入库 | 理由 |
| --- | --- | --- |
| 原生库 `.so` / `.dll` / `.dylib` | ✅ **入库** | 三平台合计 24 MB，保证 wheel 可离线构建 |
| 内部 wheel（46 MB） | ❌ | 只记 SHA256 + 来源，见 `artifacts/manifests/` |
| RuyiTrace 包（557 MB zip / 1.5 GB 解包） | ❌ | 只记 SHA256 + 内核文件 hash |
| Firefox 源码树 | ❌ | 数十 GB，靠 submodule + pin |
| 反编译中间产物（`.idb` / `.i64` / dump） | ❌ | 体积大且可再生，目录 gitignore |

原生库入库的代价是仓库会随平台增加而膨胀，**因此规定**：每个平台的库目录一旦入库，不允许出现同一文件的多个版本；换代必须整目录替换并更新 `PINS.md` 与 `STATUS.yaml`。

---

## 七、快速开始

```bash
# clone 带 submodule
git clone --recurse-submodules https://github.com/Facetomyself/ruyi-platform
cd ruyi-platform

# 已有 clone 补 submodule
git submodule update --init --recursive

# 校验所有 pin 与发布物
./scripts/verify-pins.sh
python3 scripts/verify-manifests.py

# 看当前状态
cat STATUS.yaml
```

---

## 八、交付与复用状态（2026-11-24）

**先选依赖，再选制品：**[项目关系表](docs/01-architecture.md#下游先选依赖再选证据)区分运行依赖、可选借用和数据对照；[当前交付缺口](docs/04-risks-and-gaps.md#当前交付缺口)列出每项阻塞的用途和通过条件。拉源码、构建或校验制品见[交接手册](docs/14-source-handoff.md)，机器账本见 [STATUS.yaml](STATUS.yaml)。

| 项目 | 当前交付 |
| --- | --- |
| **RuyiTrace** | Linux 有范围明确的浏览器、桌面与无头实采验收。amd64 R5 提供独立源码标签和同包核验入口；管理面另行迭代。 |
| **RuyiHttp** | Python 客户端及三平台既有原生运行库可复用；[Linux amd64 HTTPS 验收](projects/ruyihttp/README.md)。新平台原生库是另一项交付。 |
| **RuyiJS 内部版** | [私有 Linux amd64 wheel](artifacts/receipts/ruyijs-linux-amd64-wheel-r354/validation.json)已从本地文件安装。默认 `Context()` 和 C 客户端的 13 组安装态检查均通过；[离线安装与复建](submodules/ruyijs/docs/linux-amd64-wheel.md)。真实网络和 ARM64 产品另验。 |
| **ruyi-mcp** | 可自启 Firefox，也可在原生 amd64 上借用 Trace CLI 持有的 R5 会话；生产同会话已验，ARM64 与 Electron owner 另验。[管理面交接](projects/ruyi-mcp/MANAGEMENT-HANDOFF.md) |
| **RuyiDOM（独立仓）** | Firefox 136 的离线 DOM 和显式浏览器导航；维护源码、供应商输入及历史 P3 镜像分开管理。见 [v0.1.0 源码交接](docs/14-source-handoff.md#ruyidom-独立源码交接)，它不占用平台 gitlink。 |

**反编译是本仓两条主线**：`ruyijs-inner` 与 `ruyitrace/domtrace`。方法论相同（见 `docs/05-reverse-analysis.md`），对象与难度不同：

| | ruyijs-inner | ruyitrace/domtrace |
| --- | --- | --- |
| 反编译对象 | `js.exe`（49.5 MB，C++） | `xul.dll`（178 MB，C++） |
| 证据层次 | [Win64 语义还原](projects/ruyijs/reverse-analysis.md)与 [R353 离线运行](artifacts/receipts/ruyijs-linux-amd64-r353/validation.json)分别核对 | 74 个开关是 Win64 静态清单；Linux 实际可签收的采集项以[具体包的验收](docs/14-source-handoff.md)为准 |
| 已知锚点 | Python 绑定接口、`build-identity.json` | 74 个 `MOZ_DOM_*` env 字符串、完整原理手册 |
| 对照物 | `ff-ruyijs` public 源码（可读，但非基线） | 无（官方 Firefox 不含 domtrace） |
| 难度 | 中（有跨平台参考实现） | 高（无参考） |

---

## 九、文档索引

| 文档 | 用途 |
| --- | --- |
| [`docs/00-quickmap.md`](docs/00-quickmap.md) | 一页索引，从哪进 |
| [`docs/01-architecture.md`](docs/01-architecture.md) | 三件套是什么、怎么连 |
| [`docs/02-source-recovery.md`](docs/02-source-recovery.md) | 源码从哪来、缺什么 |
| [`docs/03-linux-port.md`](docs/03-linux-port.md) | 逐层移植清单 |
| [`docs/04-risks-and-gaps.md`](docs/04-risks-and-gaps.md) | 已知缺口与待决策 |
| [`docs/05-reverse-analysis.md`](docs/05-reverse-analysis.md) | 反编译方法论 |
| [`docs/06-ruyijs-inner.md`](docs/06-ruyijs-inner.md) | 内部版反编译与工程化方案 |
| [`docs/07-build-hosts.md`](docs/07-build-hosts.md) | 构建主机调查（架构/内存/磁盘实测） |
| [`docs/08-firefox-commit-provenance.md`](docs/08-firefox-commit-provenance.md) | 三个 Firefox commit 的真实归属 |
| [`docs/09-evidence-ledger.md`](docs/09-evidence-ledger.md) | 证据等级总账（实测 / 推断 / 待样本） |
| [`docs/10-build-runbook.md`](docs/10-build-runbook.md) | 构建机到位后的执行清单（7 阶段） |
| [`docs/11-aarch64-assessment.md`](docs/11-aarch64-assessment.md) | linux_aarch64 原生库可行性评估 |
| [`docs/12-real-build-findings.md`](docs/12-real-build-findings.md) | 补丁在真实 Firefox 树里的验证结论 |
| [`docs/13-ruyitrace-progress.md`](docs/13-ruyitrace-progress.md) | RuyiTrace 整体进度评估 |
| [`docs/adr/`](docs/adr/) | 架构决策记录（0001 仓库拓扑 / 0002 ruyijs 反编译而非 fork） |
| [`TIMELINE.md`](TIMELINE.md) | 工作主线（为何做、遇到什么、怎么解决） |
| [`HANDOVER.md`](HANDOVER.md) | 阶段总结与交接（做了什么、可信度、卡在哪） |
| [`REPRODUCE.md`](REPRODUCE.md) | 从零到当前状态的完整路径（已实测） |
| [`conventions.md`](conventions.md) | 写文档的规则 |
| [`PINS.md`](PINS.md) | 所有外部依赖的固定版本 |
| [`STATUS.yaml`](STATUS.yaml) | 机器可读状态 |
