# ruyi-mcp 变更日志

## 2026-11-24 — 锁定通过原生 CI 的 Docker 版本

- 引入非 root `core` 和可挂载 Firefox 的 `browser` 镜像目标，运行镜像内保留源码修订号用于证据溯源。
- [组件 CI](https://github.com/Facetomyself/ruyi-mcp/actions/runs/45303990325) 通过 AMD64/ARM64 `core` 及 AMD64 ESR 导航和退出；平台固定该提交。
- 核对 AMD64 Trace 制品的归档 SHA-256、Firefox 二进制 SHA-256、ELF 架构和 BuildID；记录 [挂载及验收步骤](README.md#amd64-容器与-trace-制品)。实际挂载 Trace Firefox 与生产活会话为后续独立门禁。

## 2026-11-21 — 纳入平台固定版本管理

- 以独立 Git 子模块接入组件 `linux` 分支的已发布提交，源码与组件发布继续在组件仓进行。
- 平台登记 RuyiTrace 的浏览器与 owner 会话边界，区分 RuyiJS 和 RuyiHttp 的并行职责。
- 验收使用平台 `bash scripts/verify-pins.sh` 与组件 `npm run check`；Linux 真浏览器、Trace 同会话与 Docker 实测另行验收。
