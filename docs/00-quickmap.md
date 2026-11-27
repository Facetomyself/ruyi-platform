# 00 · 一页索引

从哪进，看什么。

---

## 我是新来的

**最快**：读 [`../TIMELINE.md`](../TIMELINE.md)（工作主线与三次纠错）
或 [`../HANDOVER.md`](../HANDOVER.md)（10 分钟知道做了什么、做到哪、卡在哪）。

然后读这三份，按顺序：

1. [`../README.md`](../README.md) —— 本仓是什么、拓扑长什么样
2. [`01-architecture.md`](01-architecture.md) —— 各组件何时集成、何时独立运行
3. [`../PINS.md`](../PINS.md) —— 所有版本号在哪查

---

## 我要做某件具体的事

| 我要… | 看这里 |
| --- | --- |
| 判断是否需要同时安装几个项目，谁持有浏览器 | [五个一级组件 + 独立 RuyiDOM：硬依赖、借用与数据对照](01-architecture.md#下游先选依赖再选证据) |
| 拿到某个项目的源码 | [`02-source-recovery.md`](02-source-recovery.md) |
| 把某层移植到 Linux | [`03-linux-port.md`](03-linux-port.md) |
| 维护公开 RuyiJS 性能与 macOS/Linux 兼容、向上游提 PR | [公开 RuyiJS 项目入口](../projects/ff-ruyijs/README.md) · [公开开发 pin](../PINS.md#open-ruyijs) |
| 维护 ruyi-mcp、更新 pin 或验收 Docker | [ruyi-mcp 项目入口](../projects/ruyi-mcp/README.md) |
| 判断现在卡在哪、需要谁验收 | [交付缺口与通过条件](04-risks-and-gaps.md#当前交付缺口) + [机器状态](../STATUS.yaml) |
| 反编译 domtrace 内核 | [`05-reverse-analysis.md`](05-reverse-analysis.md) |
| **domtrace 该插在哪** | [`../projects/ruyitrace/instrumentation-sites.md`](../projects/ruyitrace/instrumentation-sites.md) |
| **要改 Codegen 的哪几处** | [`../projects/ruyitrace/codegen-changes.md`](../projects/ruyitrace/codegen-changes.md) |
| 反编译 ruyijs 内部版 | [`06-ruyijs-inner.md`](06-ruyijs-inner.md) |
| 要在哪台机器上构建 | [`07-build-hosts.md`](07-build-hosts.md) |
| **哪些结论可信、哪些是推断** | [`09-evidence-ledger.md`](09-evidence-ledger.md) |
| **有机器后怎么跑** | [`10-build-runbook.md`](10-build-runbook.md) |
| 要不要补 aarch64 原生库 | [`11-aarch64-assessment.md`](11-aarch64-assessment.md) |
| **补丁在真实 Firefox 里验证过吗** | [`12-real-build-findings.md`](12-real-build-findings.md) |
| **RuyiTrace 到底做到哪了** | [`13-ruyitrace-progress.md`](13-ruyitrace-progress.md) |
| 从零复现这个状态 | [`../REPRODUCE.md`](../REPRODUCE.md) |
| 写/改文档 | [`../conventions.md`](../conventions.md) |
| 提交前自检 | [`../conventions.md`](../conventions.md) §12 |

---

## 选定复用边界

先看[各组件的当前交付和源码获取方式](14-source-handoff.md)。平台开发基线用父仓提交的一级 gitlink；只读目录用普通 clone，只开发公开组件则选对应一级路径。复建已验收的 Trace amd64 无头 R5 用其专用源码标签。Win64 私有内核 `39bfd14c` 是产品来源标识，Linux 重建使用独立的[官方 Firefox pin](../PINS.md)。

## 目录速查

```
ruyi-platform/
├── README.md              本仓定位、拓扑、规则
├── PINS.md                所有版本号
├── STATUS.yaml            机器可读状态
├── conventions.md         文档规范
├── docs/                  跨项目结论（唯一权威）
├── projects/              单项目文档
├── artifacts/manifests/   发布物 hash 记录
├── scripts/               校验脚本
├── submodules/            ruyihttp / ruyijs / ruyitrace / ruyi-mcp / ff-ruyijs
└── upstream/              历史只读参考说明
```
