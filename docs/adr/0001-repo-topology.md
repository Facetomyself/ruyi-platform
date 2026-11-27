# ADR 0001 · 仓库拓扑：单主体仓 + 三 submodule + 上游不挂载

- 状态：已接受。本文保留建仓时的三项目拓扑；[ADR 0004](0004-open-ruyijs-gitlink.md) 仅覆盖「公开 fork 不挂载」，内部版边界照旧。
- 日期：2026-11-19
- 决策者：项目主体维护者

## 背景

Ruyi 三件套（RuyiJS / RuyiHttp / RuyiTrace）有共同的 Firefox 159 血统，但产物形态完全不同：

- RuyiHttp 是库（3.9k 行 Python + 24 MB 原生库）
- RuyiJS 是进程（Python 绑定 + 49.5 MB 原生壳）
- RuyiTrace 是应用（Electron 控制台 + 178 MB 内核）

另有一个 public fork `Facetomyself/ff-ruyijs`，用于向上游提 PR。

## 候选方案

### A. 单仓 + 三 submodule（选中）

主体仓只放文档与规划，代码由 submodule 引入。

### B. 单仓内联（monorepo）

三项目源码直接放进一个仓库。

### C. 复用现有 ruyihttp 作为主体

不建新仓。

## 决策

**选 A**，并且：

1. `submodules/ruyijs` 指向**新建的** `Facetomyself/ruyijs-inner`（private），而非 `ff-ruyijs`
2. ~~`Facetomyself/ff-ruyijs` 不挂 submodule，只记录 pin~~（历史决定，由 [ADR 0004](0004-open-ruyijs-gitlink.md) 覆盖）
3. `ruyitrace` 独立建 private 库

## 理由

| 方案 | 否决理由 |
| --- | --- |
| B monorepo | 557 MB 发布包与 1.5 GB 解包产物会污染仓库；反编译中间产物无法隔离；三项目版本节奏不同 |
| C 复用 ruyihttp | 仓库名与职责不符；RuyiJS 与 RuyiTrace 无处安放 |

### 为什么 ff-ruyijs 不挂、内部版另建

以下是当时不挂载的理由。并列接入后，公开 fork 仍可作语义对照，但不是内部版来源；现行职责见 [ADR 0004](0004-open-ruyijs-gitlink.md)。

一旦把它挂成 submodule，会产生三个错误暗示：

1. 内部版基于它构建（实际是**独立反编译**）
2. 内部改动要进 public 仓（实际必须进 private 的 `ruyijs-inner`）
3. 两者的 firefox commit 一致（实际 fork 是 `2887d9de`，内部是 `9a2dc53c`）

## 后果

### 正面

- 文档与代码解耦，文档可以频繁更新而不触发代码 CI
- 三项目各自独立 push，版本节奏互不干扰
- 反编译产物有独立归属，不会混进产品仓
- 内部改动天然不进 public 仓，减少泄露风险

### 负面

- ~~clone 需要 `--recurse-submodules`~~。现行用普通 clone，并只初始化一级组件，见[复现手册](../../REPRODUCE.md#1-拉仓)。
- 跨项目改动（如 necko ABI 变更）需要三个仓一起提交
- 需要 `scripts/sync-submodules.sh` 与 `verify-pins.sh` 维持一致性

### 缓解

- ~~三仓共用一个基线（Firefox `39bfd14c`）~~。各项目构建及历史样本分别由 [PINS](../../PINS.md) 固定。
- `STATUS.yaml` 机器可读，脚本可校验
- 提交前跑 `verify-pins.sh` + `verify-links.py` + `verify-manifests.py`

## 关联

- [平台拓扑](../../README.md#二仓库拓扑)
- [公开 RuyiJS 开发 pin](../../PINS.md#open-ruyijs)；早期参考快照仍见 [PINS §3](../../PINS.md)
- [RuyiJS 内部版来源规则](../06-ruyijs-inner.md#0-三层边界先立规矩)
