# ruyi-mcp 变更日志

## 2026-11-24 — 生产 Trace 活会话在 AMD64 R5 通过

- 锁定 Trace `f8eeb0e` 与 MCP `8f3839b`。用两个真实 stdio 客户端验证排他租约、同页 query/click、RDP 真断点、正常归还与重借；另做暂停中由 owner 主动停止，见 [M2 身份及回执](../../artifacts/receipts/trace-amd64-r5/m2-delivery.json)。
- 保留暂停中停止的初次状态读取失败；修订对原子替换导致的短暂读冲突有限重试，测试确认仍拒绝硬链接。复跑确认同页在关闸前恢复并读回原生记录。
- 从干净 GitHub 检出重建独立 CLI 和 MCP，检查 42 项 CLI 清单并迁移到另一台机器跑门禁；[异机手册](PRODUCTION-OWNER.md)区分应用重编、R5 制品复验及 Firefox 源码构建。

## 2026-11-24 — 通过原生 AMD64 Trace Firefox 容器门禁

- 固定 `2797d3c` 及对应的 [原生 CI](https://github.com/Facetomyself/ruyi-mcp/actions/runs/45308474899)。修复 Firefox 换进程时异步通知占用 `getTab` 应答的问题，坚持用已确认上下文重连。
- 在原生 AMD64 Docker 以只读方式挂载 `d7DBYN4g`；MCP 自启和退出、下载内容校验、19 项 RDP 均通过。[真机回执](../../artifacts/receipts/ruyi-mcp-amd64-d7DBYN4g-20261124.json)保留修复前失败和修复后通过的日志摘要。
- 生产 Trace owner 活会话仍待集成，独立 ARM64 租约 fixture 只作前置证据。

## 2026-11-24 — 锁定通过原生 CI 的 Docker 版本

- 引入非 root `core` 和可挂载 Firefox 的 `browser` 镜像目标，运行镜像内保留源码修订号用于证据溯源。
- [组件 CI](https://github.com/Facetomyself/ruyi-mcp/actions/runs/45303990325) 通过 AMD64/ARM64 `core` 及 AMD64 ESR 导航和退出；平台固定该提交。
- 核对 AMD64 Trace 制品的归档 SHA-256、Firefox 二进制 SHA-256、ELF 架构和 BuildID；记录 [挂载及验收步骤](README.md#amd64-容器与-trace-制品)。实际挂载 Trace Firefox 与生产活会话为后续独立门禁。

## 2026-11-21 — 纳入平台固定版本管理

- 以独立 Git 子模块接入组件 `linux` 分支的已发布提交，源码与组件发布继续在组件仓进行。
- 平台登记 RuyiTrace 的浏览器与 owner 会话边界，区分 RuyiJS 和 RuyiHttp 的并行职责。
- 验收使用平台 `bash scripts/verify-pins.sh` 与组件 `npm run check`；Linux 真浏览器、Trace 同会话与 Docker 实测另行验收。
