# ADR 0004 · 公开 RuyiJS fork 作为独立一级 gitlink 接入

- 状态：已接受
- 日期：2026-11-27

## 背景

[ADR 0001](0001-repo-topology.md) 曾把公开 fork 留在平台 gitlink 之外。公开 RuyiJS 现在需要可复现的开发入口；历史只读对照、固定 donor 和发行工件依然各有固定版本，不能拿现行开发指针替代它们。

## 候选方案与取舍

| 方案 | 决定与理由 |
| --- | --- |
| 继续只记录外部参考提交 | 未采用；平台无法像其他组件一样用一级 gitlink 表达公开开发基线。 |
| 以公开 fork 替换私有 `submodules/ruyijs` | 未采用；会混淆公开开发与内部实现的来源和验收。 |
| 并列接入独立的 `submodules/ff-ruyijs` | **采用**；同一平台提交记录两套独立的源码身份，各自维护、构建与发布。 |

## 决策与边界

- 本 ADR 接入的 `submodules/ff-ruyijs` 当时是第五个一级 gitlink，指向公开 fork [Facetomyself/ff-ruyijs](https://github.com/Facetomyself/ff-ruyijs)，维护分支为 `main`，复现以[平台开发 pin](../../PINS.md#open-ruyijs)为准。只做公开 RuyiJS 性能和 macOS/Linux 兼容，将可公开的改动以 PR 提交给 [cutetailbud/ff-ruyijs](https://github.com/cutetailbud/ff-ruyijs)；保留 Windows 在共用主干上的既有行为。
- 此次公开 fork 接入时，平台有三个公开、两个私有一级组件，RuyiDOM 当时在平台外独立检出。2026-11-27 的 [ADR 0005](0005-ruyidom-gitlink.md) 将现行拓扑更新为三个公开、三个私有；父仓继续用普通 clone，之后只检出所需的一级 gitlink。Firefox 留在 fork 自己的构建流程中，仅在需要构建时按[项目手册入口](../../projects/ff-ruyijs/README.md)取得。
- 只覆盖 ADR 0001 的「公开 fork 不挂载」一项。[ADR 0002](0002-ruyijs-reverse-not-fork.md) 的内外来源规则及 [ADR 0003](0003-public-catalog-private-gitlinks.md) 的访问边界继续有效。公开源码可以做语义对照，内部实现仍以 `ruyijs-inner` 与内部产物为准。
