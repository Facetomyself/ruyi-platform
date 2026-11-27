# ruyi-platform

Ruyi 各组件的文档总入口：结构规划、源码还原与跨平台工程化。

代码在各组件仓维护。平台以一级 gitlink 接入五个项目：公开的 RuyiHttp、ruyi-mcp 和公开 RuyiJS，以及私有的 RuyiJS 内部版和 RuyiTrace。[RuyiDOM](docs/14-source-handoff.md#ruyidom-独立源码交接) 是独立维护的第六个相关项目，单独检出。

---

## 一、仓库定位

| | 本仓 | 代码仓 |
| --- | --- | --- |
| 职责 | 文档、规划、还原分析、移植路线、验收标准 | 各自的产品代码与构建 |
| 内容 | Markdown + 少量校验脚本 | 源码 + 原生库 + 测试 |
| 更新频率 | 每次结论变化 | 每次代码变化 |
| 可见性 | **public**，可匿名克隆；访问边界见[ADR 0003](docs/adr/0003-public-catalog-private-gitlinks.md) | 按项目分别设定，见 §三 |

**跨项目结论以本仓为准**：版本矩阵、组件间 ABI 契约与交付缺口集中记录；项目自身的构建方法以各组件手册为准。

---

## 二、仓库拓扑

```
ruyi-platform (public, 本仓)
├── submodules/
│   ├── ruyihttp      → Facetomyself/ruyihttp        (public)   ← RuyiHttp 代码
│   ├── ruyijs        → Facetomyself/ruyijs-inner    (private)  ← 内部版反编译 + 工程化
│   ├── ruyitrace     → Facetomyself/ruyitrace       (private)  ← RuyiTrace 主体
│   ├── ruyi-mcp      → Facetomyself/ruyi-mcp        (public)   ← Linux 自动化与调试控制面
│   └── ff-ruyijs     → Facetomyself/ff-ruyijs       (public)   ← 公开 RuyiJS；维护分支 main
│                        ↑ 公开上游：cutetailbud/ff-ruyijs
│
├── upstream/         历史只读参考说明；不包含现行组件或 Firefox 源码
│
└── docs/             全部规划与结论（唯一权威）
```

### 公开 RuyiJS 与内部版的来源边界

| 层 | 仓库 | 性质 | 允许做什么 |
| --- | --- | --- | --- |
| 开源上游 | `cutetailbud/ff-ruyijs` | public | 只读 |
| [公开 RuyiJS fork](projects/ff-ruyijs/README.md) | `Facetomyself/ff-ruyijs`（`main`） | public | 只做公开 RuyiJS 性能与 macOS/Linux 兼容，并向上游提 PR；保留 Windows 在共用主干上的既有行为 |
| **内部版** | `Facetomyself/ruyijs-inner` | **private** | **反编译分析 + 工程化 + 语义化**，内部 wheel 的唯一来源 |

`submodules/ff-ruyijs` 与 `submodules/ruyijs` 是并列的独立源码入口。公开实现可以用作内部还原时的语义对照，内部实现及验收以私有仓与内部产物为准。详细规则见[内部版来源约定](docs/06-ruyijs-inner.md#0-三层边界先立规矩)。

### 历史决策：公开 fork 曾独立于平台检出

**现已覆盖。** [ADR 0001](docs/adr/0001-repo-topology.md) 曾决定「~~公开 fork 不挂 submodule，只记录参考提交~~」。[ADR 0004](docs/adr/0004-open-ruyijs-gitlink.md) 将公开 fork 作为独立开发项目接入；[ADR 0002](docs/adr/0002-ruyijs-reverse-not-fork.md) 的内部来源规则仍有效。新的[公开开发 pin](PINS.md#open-ruyijs) 与早期只读样本、固定 donor 及已发布工件分别追溯。

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
| `submodules/ruyihttp` | `Facetomyself/ruyihttp` | **public**（2026-11-20 起） | ✅ 已有 | Python 源码和五平台原生运行时，见[项目记录](projects/ruyihttp/README.md) |
| `submodules/ruyijs` | `Facetomyself/ruyijs-inner` | private | ✅ 已有（2026-11-04） | **内部版反编译产物 + 工程化源码**，wheel 的唯一来源 |
| `submodules/ruyitrace` | `Facetomyself/ruyitrace` | private | ✅ 已有 | 控制台 + domtrace 还原 + 发布清单 |
| `submodules/ruyi-mcp` | `Facetomyself/ruyi-mcp` | public | ✅ 已纳管 | [MCP 项目入口](projects/ruyi-mcp/README.md)：Linux 控制面、Firefox 与 Trace 共会话 |
| `submodules/ff-ruyijs` | `Facetomyself/ff-ruyijs`（`main`） | public | ✅ 已纳管 | [公开 RuyiJS 项目入口](projects/ff-ruyijs/README.md)与[开发 pin](PINS.md#open-ruyijs) |

[RuyiDOM](docs/14-source-handoff.md#ruyidom-独立源码交接) 仍独立检出，平台父仓只登记上述一级 gitlink。

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
│   │                             / domtrace-contract / domtrace-readers
│   │                             / instrumentation-sites / codegen-changes
│   │                             / outputs-remaining / CHANGELOG
│   ├── ruyi-mcp/                 README / CHANGELOG
│   └── ff-ruyijs/                公开 RuyiJS 项目入口
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
| 原生库 `.so` / `.dll` / `.dylib` | ✅ **入库** | 每个已验收目标仅保留一套原生库，保证 wheel 可离线封装 |
| 内部 wheel（46 MB） | ❌ | 只记 SHA256 + 来源，见 `artifacts/manifests/` |
| RuyiTrace 包（557 MB zip / 1.5 GB 解包） | ❌ | 只记 SHA256 + 内核文件 hash |
| Firefox 源码树 | ❌ | 各构建各自固定；公开 RuyiJS 仅在构建时按 fork 自己的手册取得嵌套源码 |
| 反编译中间产物（`.idb` / `.i64` / dump） | ❌ | 体积大且可再生，目录 gitignore |

原生库入库的代价是仓库会随平台增加而膨胀，**因此规定**：每个平台的库目录一旦入库，不允许出现同一文件的多个版本；换代必须整目录替换并更新 `PINS.md` 与 `STATUS.yaml`。

---

## 七、快速开始

用 Git、Bash、Python 3 和 PyYAML，先匿名克隆公开父仓并核对目录。按路径检出公开组件无需登录；检出私有组件需相应子仓的读取权限。

```bash
git clone https://github.com/Facetomyself/ruyi-platform.git
cd ruyi-platform
bash scripts/verify-pins.sh --catalog
```

**公开开发**：只检出所需的一级组件；需要三个公开组件时执行：

```bash
git -c submodule.recurse=false submodule update --init --checkout -- \
  submodules/ruyihttp submodules/ruyi-mcp submodules/ff-ruyijs
```

**内部维护**：具备两个私仓读取权限时，在干净副本检出全部一级组件并校验：

```bash
git -c submodule.recurse=false submodule update --init --checkout
bash scripts/verify-pins.sh --repo
```

上述检出只到平台的一级组件。仅在构建公开 RuyiJS 需要 Firefox 时，按 [fork 的构建入口](projects/ff-ruyijs/README.md)处理其嵌套源码。

完整历史验收使用 `--full`（也是无参数时的严格默认档），须另备内部证据库并指定 `RUYI_PLATFORM_EVIDENCE_ROOT`。各档输入、退出码含义与单件原包核验见[复现手册](REPRODUCE.md#2-按取得的材料运行校验)。

---

## 八、交付与复用状态

**先选依赖，再选制品：**[项目关系表](docs/01-architecture.md#下游先选依赖再选证据)区分运行依赖、可选借用和数据对照；[当前交付缺口](docs/04-risks-and-gaps.md#当前交付缺口)列出逐项边界与通过条件。选择源码或制品见[交接手册](docs/14-source-handoff.md)，开发 pin 和已验收状态分别见 [PINS](PINS.md) 与 [STATUS](STATUS.yaml)。

| 项目 | 当前交付 |
| --- | --- |
| **RuyiTrace** | amd64 R5 历史包独立保留；[ARM64 R5 CLI2 正式发行](https://github.com/Facetomyself/ruyitrace/releases/tag/arm64-r5-cli2-lease-v1)供稳定站点使用，site2 在用、site1 可回退，浏览器和桌面按需运行，见[站点回执](artifacts/receipts/trace-arm64-site-operations/README.md)。[原生事件 Beta 1](artifacts/receipts/trace-linux-gap-closure-v1/patched-websocket/two-architecture-review.json)在 amd64、ARM64 各有 22 案；[Electron owner Alpha 1](artifacts/receipts/trace-linux-gap-closure-v1/electron-owner/README.md)是另一个按需预发行，只验虚拟席位。两者均未替换默认站点或平台 gitlink；[实体显示和人工 IME 仍待签收](docs/04-risks-and-gaps.md#当前交付缺口)。 |
| **RuyiHttp** | [0.9.4 已公开发行](https://github.com/Facetomyself/ruyihttp/releases/tag/v0.9.4)，[五平台精确 wheel 回执](artifacts/receipts/ruyihttp-0.9.4/README.md)保留固定构建与验收依据。Linux amd64、ARM64 均在 glibc 2.31 实装并验证直连 H1/H2/H3 和单跳 CONNECT-UDP 内层原生 H3；[v0.9.3](https://github.com/Facetomyself/ruyihttp/releases/tag/v0.9.3)继续保留。 |
| **RuyiJS 内部版** | **Linux ARM64：**[R433 私有双 wheel 正式发行](artifacts/receipts/ruyijs-linux-aarch64-product-r433/README.md)，`oracle-reverse-dev` 使用 `r433-host1`，已实测回到完整 `r432-host1` 再切回。[安装与回滚](submodules/ruyijs/docs/linux-arm64-r433.md) · [发布下载与生产验收](artifacts/receipts/ruyijs-linux-aarch64-product-r433/validation.json)。Linux amd64 的 [R356 离线 wheel](artifacts/receipts/ruyijs-linux-amd64-wheel-r356/validation.json)与 [R357 明文 HTTP/1 组件](artifacts/receipts/ruyijs-linux-http1-r357/validation.json)独立保留。 |
| **公开 RuyiJS** | [项目入口](projects/ff-ruyijs/README.md)及[源码 pin](PINS.md#open-ruyijs)用于检出与上游贡献；gitlink 只固定开发源码，历史固定 donor、公开发行工件与私有 wheel 均独立。 |
| **ruyi-mcp** | Firefox 自启与 owner 借用分开验收。[生产 CLI 矩阵](projects/ruyi-mcp/LIVE-MATRIX.md)覆盖 amd64、ARM64 各自同一 QA 镜像中的借用和跨机 SSH stdio；意外退出与同客户端恢复仅为 ARM64 CLI 证据。Electron Alpha 按其独立客户端和虚拟席位回执选用。 |
| **RuyiDOM（独立仓）** | **现有宿主**：在 `oracle-reverse-dev` 执行 `~/.local/bin/ruyidom verify`；按需、默认离线，沿用 v0.3.0 Noble 镜像。**取源码或对应制品**：现发行 v0.3.1，见[独立交接](docs/14-source-handoff.md#ruyidom-独立源码交接)及[发行与宿主的独立固定值](PINS.md#11-ruyidom-独立仓)；它仍是平台 gitlink 之外的第六个相关项目。 |

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
| [`docs/adr/`](docs/adr/) | 架构决策记录（含公开目录权限、两条 RuyiJS 来源规则及公开 fork 接入） |
| [`TIMELINE.md`](TIMELINE.md) | 工作主线（为何做、遇到什么、怎么解决） |
| [`HANDOVER.md`](HANDOVER.md) | 阶段总结与交接（做了什么、可信度、卡在哪） |
| [`REPRODUCE.md`](REPRODUCE.md) | 从零到当前状态的完整路径（已实测） |
| [`conventions.md`](conventions.md) | 写文档的规则 |
| [`PINS.md`](PINS.md) | 所有外部依赖的固定版本 |
| [`STATUS.yaml`](STATUS.yaml) | 机器可读状态 |
