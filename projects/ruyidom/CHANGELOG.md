# RuyiDOM · 平台侧变更记录

此处记录 RuyiDOM 与平台的接入，不替代[组件发行记录](https://github.com/Facetomyself/ruyidom/releases)。

## 2026-11-27 · 接入私有一级 gitlink

- 平台新增 `submodules/ruyidom`，指向 [Facetomyself/ruyidom.git](https://github.com/Facetomyself/ruyidom.git)（private），维护分支 `main`。首个 [源码 pin](../../PINS.md#ruyidom-source) 沿用 runtime 已有的直接 gitlink `b57891fb9348842e22bbc9395c3db810c0c569fc`，即[正式 `v0.3.1`](https://github.com/Facetomyself/ruyidom/releases/tag/v0.3.1) 的提交。
- 平台现有六个一级组件，三公开、三私有；匿名 `--public` 仍取原来三个公开组件。见[接入决定](../../docs/adr/0005-ruyidom-gitlink.md)。
- 官方 Firefox 136.0 可信脚本宿主与现用 `v0.3.0-host1` 保持原状；[v0.3.1 发行验收](../../artifacts/receipts/ruyidom-source-portability-v0.3.1.json)与[宿主读回](../../artifacts/receipts/ruyijs-linux-aarch64-product-r433/independent-live.json)分别留档。组件继续独立发版，供应商输入与恢复材料沿用受控交付。
