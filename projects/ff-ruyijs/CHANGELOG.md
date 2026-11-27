# ff-ruyijs 平台变更记录

## 2026-11-27 — 将开源 RuyiJS 维护线纳入公开目录

- 改动：为公开 fork 添加一级固定 gitlink、独立项目入口与上游贡献规则。公开和私有两种 RuyiJS 不共享产品 pin 或发布回执。
- 原因：最初的只读对照登记没有体现 fork 已承担的上游同步、macOS/Linux 兼容和性能维护职责。[fork 内部 PR #39](https://github.com/Facetomyself/ff-ruyijs/pull/39) 已合入维护规则；该 PR 没有发往上游。
- 核对：在平台根运行 `bash scripts/verify-pins.sh --catalog`；取得一级源码后运行 `bash scripts/verify-pins.sh --repo`。产品构建与性能对照属于具体功能 PR 的门禁。
