# ADR 0001 · 仓库拓扑：单主体仓 + 三 submodule + 上游不挂载

- 状态：已接受
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
2. `Facetomyself/ff-ruyijs` **不挂 submodule**，只记录 pin
3. `ruyitrace` 独立建 private 库

## 理由

| 方案 | 否决理由 |
| --- | --- |
| B monorepo | 557 MB 发布包与 1.5 GB 解包产物会污染仓库；反编译中间产物无法隔离；三项目版本节奏不同 |
| C 复用 ruyihttp | 仓库名与职责不符；RuyiJS 与 RuyiTrace 无处安放 |

### 为什么 ff-ruyijs 不挂、内部版另建

`ff-ruyijs` 是 **public** fork。它承担两个职责：向 `cutetailbud` 提 PR、提供反编译时的语义对照。

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

- clone 需要 `--recurse-submodules`
- 跨项目改动（如 necko ABI 变更）需要三个仓一起提交
- 需要 `scripts/sync-submodules.sh` 与 `verify-pins.sh` 维持一致性

### 缓解

- `PINS.md` 是唯一版本真相源，三仓共用一个基线（Firefox `39bfd14c`）
- `STATUS.yaml` 机器可读，脚本可校验
- 提交前跑 `verify-pins.sh` + `verify-links.py` + `verify-manifests.py`

## 关联

- `README.md` §二 仓库拓扑
- `PINS.md` §3（ff-ruyijs 定位）
- `docs/06-ruyijs-inner.md` §0（三层边界规则）
