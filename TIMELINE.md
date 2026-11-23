# 工作主线：从空目录到当前状态

本文按「为什么做这件事」组织，不是按 commit 顺序。每段说明：**遇到什么问题 → 怎么解决 → 得出什么结论**。

五个仓库共 **511 个 commit**（platform 174 / ruyitrace 88 / ruyihttp 8 / ruyijs 188 / ruyi-mcp 53）。

---

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

## 关键数字

| 项 | 值 |
| --- | ---: |
| 五个仓库 commit | 359 |
| 文档 | 43 篇（含本文）|
| C++ 文件 | 61 |
| 校验脚本 | 16 |
| domtrace 测试 | 20 项 |
| ruyihttp 测试 | 19 项 |
| 校验节数（verify-pins） | 8 |

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

## 当前状态一句话

**RuyiHttp 可用（19/19）；RuyiJS 内部版需重建；RuyiTrace 的 domtrace 技术路径已通但未编译。**

剩下的每一项都卡在：x86_64 构建机、Windows 机器、或真机样本。
