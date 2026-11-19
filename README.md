# ruyi-platform

Ruyi 三件套的**主体维护仓**：文档、结构规划、源码还原与跨平台工程化的总入口。

代码不在本仓内联，由 submodule 引入。本仓只负责：**说清它们是什么、边界在哪、怎么还原、怎么移植、怎么验收**。

---

## 一、仓库定位

| | 本仓 | 代码仓 |
| --- | --- | --- |
| 职责 | 文档、规划、还原分析、移植路线、验收标准 | 各自的产品代码与构建 |
| 内容 | Markdown + 少量脚本 | 源码 + 原生库 + 测试 |
| 更新频率 | 每次结论变化 | 每次代码变化 |
| 访问 | private | private / public 混合 |

**本仓是唯一的事实来源（single source of truth）**：三件套的版本矩阵、ABI 契约、缺口清单都以本仓为准，代码仓里的 README 是入口，不是权威。

---

## 二、仓库拓扑

```
ruyi-platform (private, 本仓)
├── submodules/
│   ├── ruyihttp      → Facetomyself/ruyihttp        (private)  ← RuyiHttp 代码
│   ├── ruyijs        → Facetomyself/ruyijs-inner    (private)  ← 待建：内部版反编译 + 工程化
│   └── ruyitrace     → Facetomyself/ruyitrace       (private)  ← 待建：RuyiTrace 主体
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
3. `ff-ruyijs` 只用于两件事：给上游提 PR；反编译时当"公开实现长什么样"的对照物。
4. 内部版要向 `ff-ruyijs` 回流的能力，走 PR 流程单向流出，不回灌。

### 为什么 ff-ruyijs 不挂 submodule

因为它**不是内部产品的组成部分**，只是外部参考：

1. **PR 目标**——上游修复要回流到 `cutetailbud/ff-ruyijs`，走 public fork。
2. **反编译对照**——还原内部版时，需要知道"官方公开实现是怎么写的"，但这只是参照，不是来源。

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
| `submodules/ruyihttp` | `Facetomyself/ruyihttp` | private | ✅ 已有 | 完整源码树，含三平台原生库 |
| `submodules/ruyijs` | `Facetomyself/ruyijs-inner` | private | ✅ 已有（2026-11-04，7.4 MB） | **内部版反编译产物 + 工程化源码**，wheel 的唯一来源 |
| `submodules/ruyitrace` | `Facetomyself/ruyitrace` | private | ⏳ 待建 | 控制台 + domtrace 还原 + 发布清单 |

**不在 submodule 里**：`Facetomyself/ff-ruyijs`（public fork，只做 PR 与反编译对照）。

**三个 submodule 都锁定同一基线**：Firefox `39bfd14cb45c`、NSS 3.132、Neqo 0.33.0。详见 `PINS.md`。

---

## 四、目录约定

```
ruyi-platform/
├── README.md                     ← 本文件
├── PINS.md                       ← 所有外部依赖的固定版本
├── STATUS.yaml                   ← 三项目当前状态机（机器可读）
├── conventions.md                ← 文档规范（必读）
├── .gitignore
├── .gitmodules
│
├── docs/                         ← 规划与结论（唯一权威）
│   ├── 00-quickmap.md            ← 一页索引
│   ├── 01-architecture.md        ← 架构与数据流
│   ├── 02-source-recovery.md     ← 源码还原路线
│   ├── 03-linux-port.md          ← Linux 适配路线
│   ├── 04-risks-and-gaps.md      ← 缺口与待决策
│   ├── 05-reverse-analysis.md    ← 反编译分析方法论
│   └── adr/                      ← 架构决策记录
│
├── projects/                     ← 三项目各自的项目文档
│   ├── ruyijs/
│   │   ├── README.md
│   │   ├── structure.md          ← ruyijs-inner 期望目录
│   │   ├── reverse-analysis.md   ← 内部 wheel 反编译进度与发现
│   │   ├── provenance.md         ← wheel → commit → 源码 溯源表
│   │   └── CHANGELOG.md
│   ├── ruyihttp/
│   │   ├── README.md
│   │   ├── structure.md
│   │   └── CHANGELOG.md
│   └── ruyitrace/
│       ├── README.md
│       ├── structure.md
│       ├── domtrace-analysis.md  ← 反编译进度与发现
│       └── CHANGELOG.md
│
├── artifacts/                    ← 发布物清单（不含二进制）
│   ├── README.md
│   └── manifests/
│       ├── ruyijs-0.2.2+inner.492ee47.yaml
│       ├── ruyijs-0.2.2+inner.20261101191032.yaml
│       └── ruyitrace-3.5.0-win64.yaml
│
├── scripts/                      ← 校验与同步脚本
│   ├── verify-pins.sh
│   ├── verify-manifests.py
│   ├── sync-submodules.sh
│   └── env-anchors.py            ← 从 PE 抽 MOZ_DOM_* 锚点
│
├── submodules/                   ← git submodule（不入本仓历史）
│   ├── ruyihttp/
│   ├── ruyijs/
│   └── ruyitrace/
│
└── upstream/                     ← 只读参考（gitignore 代码，只留说明）
    ├── README.md
    └── PINS.md
```

### 为什么 `docs/` 和 `projects/` 分开

- `docs/` 是**跨项目的横向结论**：架构关联、还原路线、移植路线、缺口。
- `projects/` 是**单项目的纵向文档**：这个项目怎么建、怎么测、改了什么。

一条结论只能出现在一个地方，另一处必须链接过去，不允许复制。

---

## 五、写文档的硬规则

详见 `conventions.md`，这里只列最关键的六条：

1. **每个结论必须带可复现命令**。写「需要 glibc 2.38」，必须同时给 `objdump -T ... | grep GLIBC_` 的命令。
2. **未知用 `Unknown` / `To be confirmed`，不猜。** 反编译未完成的部分必须有明确进度标记。
3. **三个 commit 编号必须写全**：Firefox commit、ff-ruyijs commit、wheel sha256。缺一个就是不可追溯。
4. **二进制只记 SHA256 与来源 URL**，不入 git。唯一例外是原生库（见下）。
5. **修正必须留痕**：被推翻的判断不删除，改为删除线 + 「更正」段落 + 原因。
6. **文档里的路径一律相对仓库根**，不用绝对路径（绝对路径只出现在可执行命令块里）。

---

## 六、二进制策略

| 类型 | 入库 | 理由 |
| --- | --- | --- |
| 原生库 `.so` / `.dll` / `.dylib` | ✅ **入库** | 三平台合计 24 MB（win 7.2 / darwin 8.2 / linux 8.4），保证 wheel 可离线构建 |
| 内部 wheel（46 MB） | ❌ | 只记 SHA256 + 来源，见 `artifacts/manifests/` |
| RuyiTrace 包（557 MB zip / 1.5 GB 解包） | ❌ | 只记 SHA256 + 四个内核文件 hash |
| Firefox 源码树 | ❌ | 数十 GB，靠 submodule + pin |
| 反编译中间产物（`.idb` / `.i64` / dump） | ❌ | 体积大且可再生，目录 gitignore |

原生库入库的代价是仓库会随平台增加而膨胀，**因此规定**：每个平台的库目录一旦入库，不允许出现同一文件的多个版本；换代必须整目录替换并更新 `PINS.md`。

---

## 七、快速开始

```bash
# clone 带 submodule
git clone --recurse-submodules https://github.com/Facetomyself/ruyi-platform
cd ruyi-platform

# 已有 clone 补 submodule
git submodule update --init --recursive

# 校验所有 pin 与 manifesto
./scripts/verify-pins.sh
python3 scripts/verify-manifests.py

# 看当前状态
cat STATUS.yaml
```

---

## 八、当前状态

见 `STATUS.yaml`。一句话：

> RuyiHttp 源码 100% 就绪；RuyiJS **内部版反编译已在进行**（2038 identity 中 56 条严格命中、9 条 inner_only 已语义化，`ff-ruyijs` 只作对照不当基线）；RuyiTrace 控制台 100% 就绪、**domtrace 内核 0% 需反编译**。

**反编译是本仓两条主线**：`ruyijs-inner` 与 `ruyitrace/domtrace`。两件事的方法论相同（见 `docs/05-reverse-analysis.md`），区别在于：

| | ruyijs-inner | ruyitrace/domtrace |
| --- | --- | --- |
| 反编译对象 | `js.exe`（49.5 MB，C++） | `xul.dll`（178 MB，C++） |
| 当前进度 | 56/2038 identity 命中 + 9/9 inner_only 语义化 | 0/74 开关定位 |
| 已知锚点 | Python 绑定接口（`_context.py` 等 19 文件）、`build-identity.json` | 74 个 `MOZ_DOM_*` env 字符串、完整文档 |
| 对照物 | `ff-ruyijs` public 源码（**可读，但非基线**） | 无（官方 Firefox 是否含 domtrace 待验证） |
| 难度 | 中（有跨平台参考实现） | 高（无参考） |

## 九、文档索引

| 文档 | 用途 |
| --- | --- |
| `docs/00-quickmap.md` | 一页索引，从哪进 |
| `docs/01-architecture.md` | 三件套是什么、怎么连 |
| `docs/02-source-recovery.md` | 源码从哪来、缺什么 |
| `docs/03-linux-port.md` | 逐层移植清单 |
| `docs/04-risks-and-gaps.md` | 已知缺口与待决策 |
| `docs/05-reverse-analysis.md` | 反编译方法论（domtrace，同样适用于 ruyijs-inner） |
| `docs/06-ruyijs-inner.md` | 内部版反编译与工程化方案 |
| `conventions.md` | 写文档的规则 |
| `PINS.md` | 所有外部依赖的固定版本 |
| `STATUS.yaml` | 机器可读状态 |
