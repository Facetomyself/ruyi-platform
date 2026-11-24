# 阶段总结与交接

**当前交付入口（2026-11-24）：[平台状态、源码与构建交接](docs/14-source-handoff.md)。** 下列记录保留为历史；其中“ARM64 插桩待验证”已由后续 ARM64 正式包和虚拟桌面回执更新。

**Linux 最新交接（2026-11-21）：**已审计的 x86_64 Firefox 159 `attempt.6D26B4Jt` 通过发行身份、真实页面 OFF/ON 及同包来源边界。OFF 零文件，ON 同一活跃窗口 9 条 DOM 与 2 条点击；父进程持有实际日志的可写 FD，异源 iframe 零输出。原始记录已在 ARM64 Electron 沙箱窗口复验，并组装了 amd64 便携目录。同包已在隔离 amd64 来宾的原生 Electron 窗口通过启动、采集和日志表验收；`attempt.d7DBYN4g` 已通过同包双会话闸门、独立 Storage 摘要实采及两条 amd64 原生窗口链路。`d7DBYN4g` 的原样 `launch-ruyitrace` 还通过了认证 Xvfb 下的 X11 主面板和 renderer 沙箱验证。`7d76dc1` 修正版的同一便携包已同时通过原生 Weston Wayland 与认证 Xvfb 的空参数启动；扩展 producer、ARM64 插桩内核与物理显示仍需独立验证。旧包 `attempt.H5K1EqGg` 的失败回执保留。见[实时进度](docs/13-ruyitrace-progress.md)及[机器状态](STATUS.yaml)。以下为历史交接。

本文是 17 轮工作的总账。目标：让一个新接手的人 10 分钟内知道
**做了什么、做到哪、可信度多少、下一步卡在哪**。

---

## 一、仓库现状

| 项 | 数量 |
| --- | ---: |
| 主体仓 commit | 48 |
| `ruyitrace` commit | 18 |
| `ruyihttp` commit | 5 |
| `ruyijs-inner` commit | 10 |
| 文档 | 41 篇 |
| C++ 源码 | 51 个文件 |
| 校验脚本 | 15 个 |
| 测试 | 38 项（domtrace 19 + ruyihttp 19） |

三个 submodule 全部接入，指针锁定，`verify-pins.sh` 七节全绿。

---

## 二、三件套各自的真实状态

### RuyiHttp — **可用了**

| 维度 | 状态 |
| --- | --- |
| 源码 | 100%（3932 行 Python + 三平台原生库） |
| 测试 | **19/19 通过**（Windows 假设已全部参数化） |
| wheel | 三平台可重建，**26 个原生文件 hash 全匹配** |
| Linux live | ❌ 未验证（本机 glibc 2.35 < 2.38） |
| 归档 | 旧 wheel 移到 `dist-v0.9.0-legacy/` 并附验证报告 |

**可交付**。卡点只有 glibc 版本，属环境问题。

### RuyiJS — **内部版需重建，官方 Linux 版已可用**

| 维度 | 状态 |
| --- | --- |
| Python 层 | 明文，19 文件 |
| `js.exe` 反编译 | 2038 identity 中 56 条严格命中 |
| operation 定位 | **37/39**（15 独立字符串 + 31 立即数） |
| 分发器 | 16 路跳转表 + movabs/SSE 三种校验，已反汇编 |
| 官方 Linux wheel | ✅ 存在（`ruyijs-0.4.1-manylinux_2_39`，73.9 MB，内含 `js` 66 MB） |

**关键差异**：官方 Linux 是 **SpiderMonkey 160 + OpenSSL**，
内部版是 **SpiderMonkey 159 + NSS**。不是同一套构建。

### RuyiTrace — **控制台完整，domtrace 技术路径已通但未编译**

| 维度 | 状态 |
| --- | --- |
| Electron 控制台 | 100%（74 文件 3644 行） |
| domtrace 开关读取点 | **74/74** |
| domtrace 开关语义 | **74/74**（10 种解析模式） |
| 记录结构 | **12/13**（env_inventory 等样本） |
| 记录写入器 | 3 类可写盘 |
| sink 调度 + 建目录 | **13/13**，端到端验证 |
| 插桩点位置 | ✅ `GenericGetter/Setter/Method` |
| Codegen 改名机制 | ✅ 三处改动，约 85 行 |
| 实际编译 | ❌ 需 `mach build` 环境 |

---

## 三、domtrace 的技术路径（这是本轮工作的核心）

### 已完成的七层

```
1. 74 个开关读取点    反编译 xul.dll 定位，74/74 配对
2. 74 个开关语义      10 种解析模式，逐条对齐汇编
3. 13 类记录结构      来源：原理手册（2659 行）
4. 记录写入器         core jsonl / jscall bin / trace-writer
5. sink 调度          13 类决策 + 路径派生，7 条与 cheatsheet 逐字符一致
6. 插桩点位置         BindingUtils.cpp 的三个 Generic*
7. Codegen 改名       三处改动约 85 行
```

### 每一层的验收方式

| 层 | 验收 |
| --- | --- |
| 1-2 | `scripts/domtrace-anchors.py` 可复现 |
| 3 | Python `json.loads` 逐行校验 |
| 4 | jscall 写入器被官方 `jscall_decode.py` 正确解码 |
| 5 | 12 组断言，含 Windows/POSIX 双路径 |
| 6-7 | 官方源码行号可查 |

### 唯一未做的

**实际编译验证**。需要一台能跑 `mach build` 的机器。

---

## 四、关键发现纪要

### 1. domtrace 是私有 fork，不是官方功能

```
官方 dom/bindings/ 323 个文件，grep domtrace → 0
RuyiTrace 的 39bfd14c 在官方仓库 git fetch 失败
```

这解释了为什么它必须改 Codegen 并重编。

### 2. 三个 Firefox commit 的真实归属

| commit | 是什么 | 官方存在 |
| --- | --- | --- |
| `9a2dc53c` | `FIREFOX_159_0_RELEASE` | ✅ |
| `2887d9de` | release 分支 2026-11-04 | ✅ |
| `39bfd14c` | RuyiTrace 内核 | ❌ |

### 3. 编译器会内联字符串比较

39 个 operation 里只有 15 个是独立字符串，其余被内联成立即数/SSE 比较。
**只扫字符串会漏 24 个**——这条教训写进了 `ruyijs-inner/docs/OPERATION_DISPATCH.md`。

### 4. Linux 运行时官方已有

不需要自己编 SpiderMonkey。`ff-ruyijs` 每个版本都发布三平台 wheel。

---

## 五、可信度（见 `docs/09-evidence-ledger.md`）

| 级别 | 条目 |
| --- | ---: |
| A 实测 | 约 25 条 |
| B 有依据推断 | 约 15 个键名（主要是 wasm） |
| C 待外部输入 | 5 项 |

---

## 六、下一步需要的三个外部条件

按优先级：

### 条件 1 · 一台能跑 `mach build` 的机器（最重要）

| 需求 | 最低 |
| --- | --- |
| 架构 | x86_64 |
| 内存 | 16 GB（构建 Firefox 需要） |
| 磁盘 | 60 GB 以上 |
| glibc | 2.38+ |

**用途**：验证 domtrace 的七层还原能否真的编出可运行的 `xul`。

**拿到机器后按 [`docs/10-build-runbook.md`](docs/10-build-runbook.md) 执行**——
7 个阶段，每阶段带验证点，关键节点是阶段 4（只编 `dom/bindings`，40 分钟就能
知道五个补丁对不对）。

**现有 fleet 不满足**：五台 aarch64，唯一 x86_64 的 `oracle-gateway` 只有 952 MB 内存。

### 条件 2 · 一次真机 `env_inventory` 采集

| 需求 | Windows + 已装 RuyiTrace |
| --- | --- |

**用途**：拿到 `env_inventory` 的 JSON 结构（手册只有一句「约 1.2 MB 接口清单」）。

### 条件 3 · glibc 2.38+ 的 x86_64 主机

**用途**：跑 ruyihttp 的 Linux live 验证 + 官方 ruyijs Linux wheel。

**条件 1 与 3 可以是同一台机器。**

---

## 七、本仓能自己继续做的事（无需外部条件）

| 项 | 价值 | 成本 |
| --- | --- | --- |
| `drain` / `put` 两个 operation 定论 | 低（2 个名字） | 半天 |
| 把 Codegen 三处改动写成实际 patch | 中（能编译时直接用） | 2 小时 |
| 其余 10 类记录的写入器补齐 | 中（现在只有 3 类能写） | 1-2 天 |

---

## 八、如何验证这个仓库是健康的

```bash
git clone --recurse-submodules https://github.com/Facetomyself/ruyi-platform
cd ruyi-platform
python3 -m pip install --user pyyaml pefile capstone
bash scripts/verify-pins.sh          # 七节全绿
cd submodules/ruyitrace && bash tests/run-tests.sh   # 17 项 PASS
cd ../ruyihttp && python3 -m unittest discover -s tests  # 19 tests OK
```

四步全过，说明仓库状态与本文描述一致。

---

## 九、文档地图

| 想知道什么 | 看哪 |
| --- | --- |
| 从零复现 | `REPRODUCE.md` |
| 三件套架构 | `docs/01-architecture.md` |
| 源码从哪来 | `docs/02-source-recovery.md` |
| Linux 怎么适配 | `docs/03-linux-port.md` |
| 有哪些缺口 | `docs/04-risks-and-gaps.md` |
| domtrace 怎么反编译 | `docs/05-reverse-analysis.md` |
| ruyijs 内部版怎么还原 | `docs/06-ruyijs-inner.md` |
| 在哪台机器构建 | `docs/07-build-hosts.md` |
| commit 归属 | `docs/08-firefox-commit-provenance.md` |
| **哪些结论可信** | `docs/09-evidence-ledger.md` |
| **domtrace 插在哪** | `projects/ruyitrace/instrumentation-sites.md` |
| **要改 Codegen 哪几处** | `projects/ruyitrace/codegen-changes.md` |

---

## 十、阶段完成判定（2026-11-19，第 24 轮）

本仓在「当前外部条件下」已经做完了。

### 已经做完且可验证的

| 类别 | 内容 | 验证方式 |
| --- | --- | --- |
| 基础设施 | 主体仓 + 3 submodule、15 个脚本、9 节校验 | `verify-pins.sh` 全绿 |
| domtrace 分析 | 74/74 开关、10 种语义、12/13 记录 | 18 项测试 |
| domtrace 补丁 | 5 个补丁 84 行 | 官方源码 `git apply --check` |
| ruyihttp | 19/19 测试、26 文件 hash | `unittest` + 重建校验 |
| 可交接性 | TIMELINE / HANDOVER / REPRODUCE / 证据总账 / 构建 runbook | 44 链接全解析 |

### 剩下的全部卡在外部条件

| 事项 | 卡什么 | 谁能解 |
| --- | --- | --- |
| 验证 5 个补丁能编译 | x86_64 + 16 GB + 60 GB | 新机器 |
| 补 `env_inventory` | Windows + RuyiTrace | 真机 |
| `linux_aarch64` 原生库 | Python 3.14 + 4 小时 | 评估后决定不做 |
| 官方 Linux wheel 验证 | glibc 2.38+ x86_64 | 新机器 |

### 唯一还能自己做的（价值低）

`drain` / `put` 两个 operation 的编码位置。能让 37/39 变成 39/39，
但这两个名字不影响功能完整性——它们已经存在于二进制里，只是扫描没定位到。

### 判定

**继续在本仓内找活干，边际收益趋近于零。** 这符合目标里「避免钻牛角尖」的要求：
识别出瓶颈不在仓库内容，而在外部资源。

下一轮如果有新条件（机器 / Windows / 样本），从 `docs/10-build-runbook.md` 或
`docs/11-aarch64-assessment.md` 接着做。
