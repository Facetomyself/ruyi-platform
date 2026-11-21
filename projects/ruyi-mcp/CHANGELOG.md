# ruyi-mcp 变更日志

## 2026-11-21 — 纳入平台固定版本管理

- 以独立 Git 子模块接入组件 `linux` 分支的已发布提交，源码与组件发布继续在组件仓进行。
- 平台登记 RuyiTrace 的浏览器与 owner 会话边界，区分 RuyiJS 和 RuyiHttp 的并行职责。
- 验收使用平台 `bash scripts/verify-pins.sh` 与组件 `npm run check`；Linux 真浏览器、Trace 同会话与 Docker 实测另行验收。
