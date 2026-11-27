# ADR 0005 · 私有 RuyiDOM 作为第六个一级 gitlink 接入

- 状态：已接受
- 日期：2026-11-27

## 背景

[ADR 0003](0003-public-catalog-private-gitlinks.md) 保持了公开父仓和私有组件的访问边界；[ADR 0004](0004-open-ruyijs-gitlink.md) 接入公开 RuyiJS 时，RuyiDOM 仍在平台之外单独检出。RuyiDOM 现需和已有 runtime 直接 gitlink 使用同一套可复现的源码基线。

## 候选方案与取舍

| 方案 | 决定与理由 |
| --- | --- |
| 继续只登记独立仓与发行链接 | 未采用；平台提交缺少可直接用于检出的 RuyiDOM 源码指针。 |
| 用 `main` 顶端提交或标签对象作首个 pin | 未采用；分支顶端持续变化，附注标签对象也不是 gitlink 需要的提交，均偏离已选的 runtime 源码。 |
| 用原私仓的已验发行提交接入一级 gitlink | **采用**；沿用已有 runtime 固定源码，同时保留原来的发版和访问边界。 |

## 决策与边界

- `submodules/ruyidom` 指向 [Facetomyself/ruyidom.git](https://github.com/Facetomyself/ruyidom.git)（private）；维护分支为 `main`，取用以[平台固定提交](../../PINS.md#ruyidom-source)为准。首个 pin 沿用 runtime 直接 gitlink，等于正式 `v0.3.1^{commit}`，即 `b57891fb9348842e22bbc9395c3db810c0c569fc`。
- 现行六个一级 gitlink 中，RuyiHttp、ruyi-mcp、公开 RuyiJS 为公开组件，RuyiJS 内部版、RuyiTrace、RuyiDOM 为私有组件。父仓可匿名普通 clone，`--public` 仍只初始化原来三个公开组件。[复现手册](../../REPRODUCE.md#1-拉仓)列出精确路径。
- 后续源码升 pin 时须明确核对平台和 runtime 的直接 gitlink；同步源码与部署是两件事。官方 Firefox 136.0 可信脚本宿主与现用 `v0.3.0-host1` 都维持原状。私仓独立发版，供应商输入、受限制品与恢复材料保留原有权限与交付位置。[组件入口](../../projects/ruyidom/README.md)区分源码、发行和宿主回执。
