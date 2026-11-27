# 工作主线：从空目录到当前状态

本文按「为什么做这件事」组织，不是按 commit 顺序。每段说明：**遇到什么问题 → 怎么解决 → 得出什么结论**。

平台与一级子模块共 **1553 个 commit**（platform 353 / ff-ruyijs 334 / ruyitrace 157 / ruyihttp 190 / ruyijs 454 / ruyi-mcp 65；按父仓修订及各自 gitlink 统计，含开源 fork 的上游历史，不含嵌套 Firefox 和独立 RuyiDOM）。

R433：RuyiJS 发布两只 Linux ARM64 wheel，并用实际下载包验证安装。`oracle-reverse-dev` 正式入口已切换至 R433，完整 R432 回滚与恢复均经实测。[发布与部署回执](artifacts/receipts/ruyijs-linux-aarch64-product-r433/validation.json)。

RuyiJS 在 `oracle-reverse-dev` 上有了与 RuyiDOM 并列的按需命令。固定完整版和纯基座恢复版均从正式入口实测，镜像归档另有独立私有密文回读。[主机部署回执](artifacts/receipts/ruyijs-oracle-arm64-host1/validation.json)。

RuyiTrace ARM64 R5 CLI2：BuildID `20261125162841` 在目标机通过原生编译、审计与采集；三个锁定镜像在同机隔离空引擎加载，独立 Firefox 经真实公网 WSS 看到桌面、重连并成功撤销。[证据链](artifacts/receipts/trace-arm64-native-lease/README.md) · [独立发行](https://github.com/Facetomyself/ruyitrace/releases/tag/arm64-r5-cli2-lease-v1)。

R432：ARM64 的 1,268 个私有 C++ 单元完成全量原生编译。基座、网络 companion 及离线安装命令经独立 venv 实跑，HTTP/3 另有原生正反例。[产品回执](artifacts/receipts/ruyijs-linux-aarch64-product-r432/validation.json) · [H3 回执](artifacts/receipts/ruyijs-linux-aarch64-h3-r432/validation.json)。

RuyiTrace：短时桌面改为 TLS 一次性邀请和 systemd 租约；[回环实机](artifacts/receipts/trace-public-lease-v1/README.md)验证免输码首连、重连、到期及异常回收。[正式交互归档](artifacts/receipts/trace-interactive-r5/README.md)独立完成空引擎复验，历史候选回执不再用作正式发布证明。

R431：Firefox 159 的私有 QUIC 组件在原生 Linux x86-64 以锁定依赖重建，并在独立进程中送出回环 Initial、关闭会话。验收停在 QUIC 首包，尚未到 HTTP/3 请求或 JS 路由。见[实机回执](artifacts/receipts/ruyijs-linux-quic-component-r431/validation.json)。


---

## 2026-11-26：RuyiHttp 0.9.4

原有直连 H3 和双跳 TCP 的分开通过记录，无法证明 UDP 走过代理。此版以限定目标的两种独立代理、专用 UDP 出口和真实原生 H3 源站分别观察链路，并校验负例。两种 Linux ABI 经 Bullseye 重编和 2.31 原生架构的普通 pip 实装复验；保留 v0.9.3 Release 的原 SHA 和标签。[对应提交与五平台精确 wheel](artifacts/receipts/ruyihttp-0.9.4/README.md)。

## 第一段 · 建仓（阶段 1–3）

### 起点

三个项目散在 `/var/lib/dsh/Ruyi/` 下，没有统一结构：
- `RuyiJS/` 只有两个内部 wheel
- `RuyiHttp/` 没有
- `RuyiTrace/` 只有下载的 zip

### 决策：单主体仓 + 三 submodule

候选方案对比后选 A（见 `docs/adr/0001`）：

| 方案 | 否决理由 |
| --- | --- |
| monorepo | 557 MB 发布包与 1.5 GB 解包会污染仓库 |
| 复用 ruyihttp | 仓库名与职责不符，另两个项目无处安放 |

**关键约束**：`ff-ruyijs` 是 public fork，只作 PR 目标与反编译对照，**不挂 submodule**。
内部版走独立反编译（`docs/adr/0002`）。

### 建成的结构

```
ruyi-platform/         37 commits
├── docs/              12 篇（架构 / 还原 / 移植 / 缺口 / 反编译 / 构建）
├── projects/          三项目纵向文档
├── scripts/           14 个校验与反编译脚本
├── artifacts/         manifest + 分析产物（二进制 gitignore）
└── submodules/        ruyihttp / ruyijs-inner / ruyitrace
```

---

## 第二段 · 反编译 domtrace（阶段 4–14）

### 问题

RuyiTrace 的内核 `xul.dll`（178 MB）带 74 个 `MOZ_DOM_*` 开关的插桩，
但发布包里没有源码。

### 逐层攻克

| 层 | 方法 | 结果 |
| --- | --- | --- |
| 开关读取点 | `strings` + RVA 映射 + `lea` 引用 + `getenv` 调用点 | **74/74 配对** |
| 开关语义 | 反汇编每条解析分支 | **10 种解析模式** |
| 记录结构 | 原理手册 2659 行逐节提取 | **12/13** |
| 记录写入器 | 序列化 + 文件写入 | jscall / core jsonl 可写盘 |
| sink 调度 | 13 类决策 + 路径派生 | 端到端验证 |
| 插桩点 | 官方 159 源码 | 三个 `Generic*` 函数 |
| Codegen 改名 | 五个补丁 | 84 行，apply 成功 |

### 两处纠错

**纠错 1：7 个 operation「不存在」是误判**

第一轮扫字符串，39 个 operation 里 7 个找不到，判断「可能被裁剪」。

后来发现编译器把 `if (op == "run_timer")` 内联成立即数异或 + SSE 比较，
不在 `.rdata` 留独立字符串。实际 **37/39 都存在**。

教训：判断符号是否存在，至少查 6 类编码（独立字符串 / 4 字节立即数 / 8 字节立即数 /
分段拼接 / SSE / 跳转表）。

**纠错 2：`39bfd14c` 不是官方 commit**

`PINS.md` 原定「以 `39bfd14c` 为唯一基线」，理由是「domtrace 只在这棵树上验证过」。

实拉官方仓库后发现：`git fetch 39bfd14c` 失败，官方 `dom/bindings/` grep domtrace 零命中。

**domtrace 是私有 fork，不是官方功能。** 基线改为官方 `9a2dc53c`（`FIREFOX_159_0_RELEASE`）。

---

## 第三段 · 补 ruyihttp（阶段 8、12）

### 问题 1：19 项测试里 6 项在 Linux 上必挂

断言硬编码 Windows 事实（`os.name == "nt"`、`necko_core.dll`、`host_platform() == "win_amd64"`）。

修法：按真实宿主分支，或用 `RUYIHTTP_PLATFORM` 显式指定目标平台。

顺带修了 `_nss.py` 的 zstd 导入——加三级 fallback
（`compression.zstd` → `backports.zstd` → `backports.zstd.zstd`）。

**结果：19/19 全绿。**

### 问题 2：`dist/` 两个 wheel 与 `native/` 脱钩

实测确认三个问题：
- `win_amd64` 的 manifest 是旧结构（无 `platforms` 段）
- `macosx_26_0_arm64` 的 dylib 哈希与 provenance 全不符，缺 quic
- 从未有 linux wheel

修法：归档到 `dist-v0.9.0-legacy/` + 附验证报告；三平台重新构建，
**26 个原生文件 hash 全匹配**。

踩坑：`.gitignore` 的 `dist-*/` 把归档目录也吃了，只有 `git mv` 前已跟踪的 `.whl` 留下。

---

## 第四段 · 可行性判断（阶段 15–23）

### 发现 1：Linux 运行时官方已有

原计划「在服务器上编 SpiderMonkey」——多余。

`ff-ruyijs` 每个版本都发三平台 wheel：
- `ruyijs-0.4.1-py3-none-manylinux_2_39_x86_64.whl`（73.9 MB）
- 内含 `dist/js` 66 MB + `libruyijs_client.so` + 26 个依赖 `.so`
- `runtime.json` 的 sha256 覆盖 26/26，自洽

**但与内部版不是同一套构建**：官方是 SpiderMonkey 160 + OpenSSL，
内部是 159 + NSS。

### 发现 2：现有 fleet 没有可用的构建机

| 主机 | 架构 | glibc | 内存 | 判断 |
| --- | --- | --- | ---: | --- |
| oracle-dsh | aarch64 | 2.35 | 5 G | 本机 |
| oracle-gateway | **x86_64** | 2.31 | **0.9 G** | 内存不足 |
| oracle-reverse-dev | aarch64 | 2.39 | 10 G | 架构不符 |
| 其余三台 | aarch64 | ≤2.39 | — | 架构不符 |

**六台里五台 aarch64**，唯一 x86_64 只有 952 MB 内存。

### 决定：aarch64 原生库不做

`build_necko_linux.py` 要求 Python 3.14+，远端 3.12；Ubuntu 24.04 源无 3.14；
sparse clone 缺 `security/nss`。

成本 3.5–5 小时，收益是「补一个可能无人使用的平台槽位」。
**评估后决定不做**，理由与重议条件写进 `docs/11`。

---

## 2026-11-21 · 纳入 ruyi-mcp

Linux 版 MCP 保留独立发布节奏，平台增加第四个子模块来复现固定版本，统一记录与其他组件的接口和验收状态。维护流程见 [ruyi-mcp 项目入口](projects/ruyi-mcp/README.md)。

## 2026-11-26 · 私有 ARM64 Trace 站点按需运行

`oracle-reverse-dev` 以固定用户命令维护两个真实版本。普通升级与回滚、活跃公网桌面的版本准入、实际管理进程中断恢复，以及避免改指其他镜像标签的离线重载均经实机验证。详见[运维回执](artifacts/receipts/trace-arm64-site-operations/README.md)和[正式附件下载核验](artifacts/receipts/trace-arm64-site-operations/github-release.json)。

## 2026-11-26 · Linux Trace 原生事件与 Electron 持有者

独立于现有站点登记两条私有预发行数据：在两种原生架构分别观察指定 JS/Wasm 边界与 HTTP 事务，并用干净 Electron 主进程直接持有 Firefox/BiDi 完成五类实际 MCP 生命周期。参见[原生证据](artifacts/receipts/trace-linux-gap-closure-v1/README.md)与[桌面 owner 回读](artifacts/receipts/trace-linux-gap-closure-v1/electron-owner/README.md)。Win64 开关定位、物理面板和现场输入法各自保留独立判据。

## 2026-11-26 · 双架构 Firefox 原生帧 Beta

[Native Events Beta 1](https://github.com/Facetomyself/ruyitrace/releases/tag/native-events-v0.2.0-beta.1) 于 15:40 UTC 发布。两个原生架构各跑 5 个 WS 案和相同新镜像上的 17 个回归，独立确认 44 个不同的运行；另测选路、超限真实部分观测及操作员自选的 GET/函数。[全部八个附件在发布后下载验 SHA](artifacts/receipts/trace-linux-gap-closure-v1/patched-websocket/beta-published.json)。本次没有更换站点版本；实体面板、人工输入法与原生浏览器事件分开验收。

## 2026-11-27 · 分开交付指针、源码和内部原件

此前普通使用者按首页指示递归检出，会遇到私仓访问要求；即使已检出全部固定源码，也欠缺旧版校验所需的内部原件。[复现手册](REPRODUCE.md#2-按取得的材料运行校验)区分这三种输入。09:26 的维护提交没有调整仓库权限或组件 pin。09:44（北京时间）随后按[公开父仓决策](docs/adr/0003-public-catalog-private-gitlinks.md)将现有平台仓原地设为 public；父仓及两个公开组件经匿名检出，私有组件权限和固定提交保持原样。

## 2026-11-27 · 纳入开源 RuyiJS 维护 fork

`ff-ruyijs` 成为第五个一级 gitlink（第三个公开组件），与私有内部产品分开维护。平台固定经过审核的 fork `main` 提交，公开版吸收上游并回送适合合入的单项优化与兼容修复；嵌套 Firefox 仅在源码构建时准备。见[维护规则与平台准入](projects/ff-ruyijs/README.md)和[版本依据](PINS.md#open-ruyijs)。

## 关键数字

| 项 | 值 |
| --- | ---: |
| 平台与一级子模块 commit | 1553 |
| 文档 | 52 篇（含本文）|
| C++ 文件 | 62 |
| 校验脚本 | 22 |
| domtrace 测试 | 20 项 |
| ruyihttp 测试 | 171 项（原生开关全开）；另有五平台双端点官方线路门禁 |
| 平台校验档位 | 目录、仓内、完整；用途见[复现手册](REPRODUCE.md#2-按取得的材料运行校验) |

> 口径：文档 = 排除 `submodules/` `upstream/` `artifacts/` 后的 `.md`；
> 校验脚本 = `scripts/` 下的 `.py` 与 `.sh`。两者都由
> `scripts/verify-timeline.py` 自动核对。

---

## 三次「本来会浪费时间」的转向

| 差点做的事 | 实际发现 | 省下 |
| --- | --- | --- |
| 手写跨平台 `_pipe.py` | 上游 ff-ruyijs 已有参考实现 | 数小时 |
| 给内部版补 7 个缺失 operation | 它们都存在于二进制里 | 数天 |
| 在服务器上编 SpiderMonkey | 官方 wheel 已含 linux 运行时 | 数小时 |

三次都是**先验证再动手**避免的。

---

## 第五段 · 真实构建验证（2026-11-20）

第一次把补丁放进真实 Firefox 构建。

### 结果

- Codegen 生成的表：✅ 正确（`kInterfaces` / `kMemberNames` 索引链闭合）
- C++ 编译：✅ 4431 个目标文件，含 `dom/bindings` 全部 42 个
- Rust `gkrust`：❌ OOM（**与补丁无关**）
- 完整 `libxul.so`：❌ 需 32 GB 以上内存

### 七个真实缺陷

| # | 缺陷 | 隐蔽度 |
| --- | --- | --- |
| 1 | `%` 运算符优先级 | 低 |
| 2 | `fill()` 要求 `$*{x}` 独占行 | 中 |
| 3 | `static const char*` 类内初始化非法 | 高（需换设计） |
| 4 | `CGStringTable` 不能用于复合键 | 中 |
| 5 | 插桩头放错位置会污染整棵树 | 中 |
| 6 | **`CGGeneric` 只输出 `define()`** | **最高（代码正确但产物为空）** |
| 7 | 构造函数需要模板 | 中 |

**全部是 `git apply --check` 发现不了的。**

### 时间教训

`gkrust` 占了 4 小时（3 次尝试），而它跟我们毫无关系。
4431 个目标文件里只有 42 个（0.95%）受补丁影响。

Mozilla 的构建系统强制完整依赖图，无法只编 `dom/bindings`。

## 当前交付

以上为分阶段历史。当前已验收的包、可检出的源码、管理面联验与 JS 产品链接缺口见[源码与构建交接](docs/14-source-handoff.md)。
