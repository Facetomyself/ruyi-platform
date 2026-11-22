# RuyiJS（内部版）

仓库：`Facetomyself/ruyijs-inner`（private，**已存在**：2026-11-04 创建，7.4 MB，默认分支 `main`）
挂载：`submodules/ruyijs`
上游参考：`Facetomyself/ff-ruyijs`（public fork，**只作 PR 与对照，不作基线**）

## 是什么

Firefox 159 的 SpiderMonkey + 38 个浏览器子系统的 Python 可编程封装。跑在独立进程里，通过本地帧传输与 Python 通信。

## 三层结构

| 层 | 体积 | 源码状态 |
| --- | --- | --- |
| Python 绑定 `ruyijs/*.py` | 60 KB / 19 文件 | ✅ 明文 |
| `necko` 适配器 `vendor/.../necko/` | 200 KB / 13 文件 | ✅ 明文 |
| 原生壳 `dist/js.exe` | 49.5 MB | ❌ 需反编译 |
| 内嵌 CPython 3.14 | ~15 MB | ✅ 官方产物 |

## 两个已有构建

| 版本 | 大小 | Engine | examples | client.dll |
| --- | --- | --- | --- | --- |
| `0.2.2+inner.492ee47` | 46.0 MB | ✅ | 26 个 | ❌ |
| `0.2.2+inner.20261101191032` | 46.6 MB | ❌ | 0 | ✅ |

记录：`artifacts/manifests/ruyijs-inner-*.yaml`

## 期望目录（ruyijs-inner 建库后）

```
ruyijs-inner/
├── src/                      反编译还原的 C++（2069 文件，按 build-identity 的 2038 条路径）
├── python/ruyijs/            19 个 .py（明文，从 wheel 取）
├── native/                   necko C/C++/Rust
│   ├── necko_tls/            Windows：necko_tls.c 863 / necko_exchange.c 823
│   ├── necko_posix/          Linux：tls.cpp 148 / http1.cpp 144 / socket.cpp 125
│   └── necko_quic/           两平台：lib.rs 1007
├── tests/                    契约断言（见 docs/06 §4）
├── tools/                    构建脚本
└── docs/                     本项目文档
```

## 反编译方案

见 [`../../docs/06-ruyijs-inner.md`](../../docs/06-ruyijs-inner.md)。

**优先级**：P0（eval/set/expose/load_page/navigate）→ P1（管道协议）→ P2（指纹配置）→ P3–P6。

## 当前状态

**语义重建进行中**（不是从 0 开始）。

| 分类 | 数量 |
| --- | ---: |
| identity 总数 | 2038 |
| eol-insensitive 对齐 0.2.1 | 1792 |
| hash_diff | 237（56 条 identity 命中） |
| inner_only | 9（全部语义化） |

最大缺口：`page_storage` / `browsing_context` / `draw` / `css_color_resolve`。

详细进度见 [`reverse-analysis.md`](reverse-analysis.md)。

### Linux x86_64 私有 donor

2026-11-22 在 `host185` 通过 Trace 让行和资源检查后，以 0.5 CPU、2 GiB 内存运行单独的离线快照。借用的 Firefox Git 对象库是 partial clone，实际 `checkout` 因缺少 blob 返回失败；其私有目录和日志保留，未启动 standalone 编译，容器 `OOMKilled=false`。

主机已从 Mozilla 官方仓库核对 `FIREFOX_159_0_RELEASE` 对应 `9a2dc53c369c7ae5172018b35988e1d2ffeff402`。同额度的独立源码容器在 `/home/ruyijs-donor-isolated-moz159/firefox` 浅取该 tag，没有 Trace 挂载，实际 `official_source_ready 0`。联网仅用于取官方源码。证据位于工作区 `deliverables/linux-ruyijs-donor-r66/source-stage.json`。

同机原生 amd64 断网预检以只读方式挂官方源码，Clang 21、`JS_STANDALONE=1`、`JS_SHARED_LIBRARY=1`、x86_64 目标和 247 个生成后端文件均确认。首次仅头文件步骤误从子目录调用，保留 `headers 2`；`959de74` 改用顶层两个确切目标，生成 `js-config.h` 与 `js-confdefs.h` 后 `configured_only 0`。配置及头文件复验均无 OOM，证据 `deliverables/linux-ruyijs-donor-r67/native-configure.json`。新增 2 项配置回归与 21 项隔离回归通过；仍无 `dist/bin/js` 或私有产品 `Context.eval` 结果。

`fb4d68f` 加入 cgroup v1 单作业看门狗：从实际在用内存中扣除有界的非活跃文件缓存，工作量连续三次达到 3,750,000,000 字节即停止本次进程组；每 30 秒保留数值。主机 `/home/ruyijs-donor-isolated-moz159/full-r68` 使用配置的独立副本，在原生 amd64 容器内以只读源码、无网络、2 CPU／4 GiB（无额外 swap）启动 `make -j1`。06:37 +08:00 已生成 JIT 构建输入，OOM 为零；原预检保持原样。两项看门狗回归通过。阶段性证据 `deliverables/linux-ruyijs-donor-r68/native-build-start.json`。候选只有链接后通过 ELF／对象清单、版本和本地 JavaScript／Promise 才算源 donor 通过，且与私有产品行为验收分开。

随后同一任务生成中间 `libjsrust.a`（65,114,854 字节），继续编译 `js/src/builtin/Unified_cpp_js_src_builtin4.o`，阶段性实证为 `deliverables/linux-ruyijs-donor-r68/native-cxx-stage.json`。

07:15 +08:00 已确认 `standalone_donor_verified 0`：候选链接的原生 x86_64 `dist/bin/js` 为 288,896,464 字节，SHA-256 `edd591e42f99ed3436e6f8112b2939a0a74b458fa09de261cc45214733bead80`，28 个 shell 对象齐备，实际 `--version` 为 `JavaScript-C159.0`，断网执行的求值与 Promise 回执 `{eval:42,promise:[7]}`。内存看门狗采样工作量峰值 2,795,630,592 字节、未触发停止，Docker `OOMKilled=false`，原预检副本仍未链接。回执 `deliverables/linux-ruyijs-donor-r68/standalone-verified.json`。这是原版 Mozilla donor，和私有版验收分开。

07:30 +08:00，`23409f7` 在独立断网容器按真实构建记录重放原始链接，只改变输出路径。28 个原对象和三个静态库通过只读挂载；产物和原版 `dist/bin/js` **逐字节一致**（同为 288,896,464 字节、SHA-256 `edd591e42f99ed3436e6f8112b2939a0a74b458fa09de261cc45214733bead80`），重链 ELF 也实跑得到 `JavaScript-C159.0` 和 `{eval:42,promise:[7]}`。重复或变更链接命令会失败，两项新增回归通过。证据 `deliverables/linux-ruyijs-donor-r72/exact-relink.json`。该回执仅用于未修改对象的链接对照。

随后 `12e33c7` 以已提交的私有生成器及头文件，从真实 Mozilla donor 生成私有 `js.cpp`、统一单元与 codec 头。100 项原始编译参数经摘要固定，只更改输出、依赖文件和输入的路径并新增私有 include。断网原生编译生成 x86_64 ET_REL `shell0.o`：6,958,728 字节，SHA-256 `82f7bb61f0a9509e56e3e09c67a5fc6a21d13546f16e96e0c2968dd1a308e2a8`；检查到 `Arguments::Prepare`、`Run`、`RunWorker` 与两类异常处理的五个待链接钩子。原 donor 对象摘要不变，容器退出 0、未 OOM，继续保留在独立目录 `/home/ruyijs-donor-isolated-moz159/private-shell0-r73`。见 `deliverables/linux-ruyijs-private-shell0-r73/compile-evidence.json`。该轮只生成待链接对象。

`94436d5` 核对、提交 POSIX 参数分支，实际 C++ 回归覆盖 UTF-8 路径和原始 argv 字节、二进制读取、`{pid}` 展开与显式路径优先。`host185` 从同一真实 donor 的编译配置断网编译 `arguments`、`exception_capture`、`runtime`、`worker_mode` 四个私有单元，再用 `ld.lld -r` 与上一轮 `shell0.o` 合并。回执 `native_hooks_verified 0`，含 **五个原始钩子定义**，对应引用均闭合；合并后的 x86_64 ET_REL 是 8,237,552 字节，SHA-256 `dda86055255d47912212dd17af9c14e9c8e611f228e3b6ba01533e82d60ed965`。没有 OOM；仍有 **229 条其他私有未解析符号**。列表及四个原始对象摘要在 `deliverables/linux-ruyijs-native-hooks-r74/hook-link-evidence.json`。`Context.eval` 仍待实际运行。

`deae44b` 复验并纳入 POSIX `Pipe` 实现，本机 AF_UNIX 试验通过同步／异步、16 MiB 帧、背压与关闭清理。再在 `host185` 用已有只读 donor 和私有输入编译 17 个实际单元，生成 11,250,344 字节的 x86_64 ET_REL（SHA-256 `951edd890376963f5987dbe961441a91602eb3d650d1816f5a4a38a3255c4345`）。按 ELF 原始符号身份而不是相似名称，上一轮 229 条私有引用消除 30 条（包含 `Pipe::ConnectAsync`），新增 68 条，**当前 267 条**。容器退出 0 且无 OOM，前版对象摘要不变。实证在 `deliverables/linux-ruyijs-native-batch-r75/symbol-delta.json`。符号继续闭合，尚无私有可执行文件。

`bca6c12` 在同一原生 x86_64 donor 旁使用 `scheduling-v1` 分批编译整个执行调度域。49 个已提交单元逐一通过，6 个模型单元启用异常处理；部分链接所得 x86_64 ET_REL 为 19,266,376 字节，SHA-256 `71e106976ac290d6c6d643e538dd46182d443f0939d11852bccd2714f7811edf`。上一轮 267 条引用解决 20 条（均属于调度域），新增 7 条，剩 254 条，其中 `execution_scheduling` 引用为 **0**。前版对象摘要保持原样；容器退出 0、无 OOM。实证 `deliverables/linux-ruyijs-native-sched-r76/scheduling-symbol-delta.json`；仅为部分链接，调度的产品运行验收与完整 `Context.eval` 仍待实跑。

`c7e6eaa` 使用已提交的环境配置生成 `firefox_environment_profile.h`，然后原生断网编译全部 64 个 `browser_environment` 单元（3 个模型单元沿用异常策略）。新 x86_64 ET_REL 为 44,501,600 字节，SHA-256 `26591bd914028753f73dfc481a7e7d26112c49f1d9cfe5084cbcca729a71d572`；上一轮 254 条引用消除 26 条，新增 14 条，剩 242 条，其中 `browser_environment` 引用为 **0**。前版对象、配置来源和生成头均复核摘要一致，容器退出 0、无 OOM。宿主 locale 等平台语义仍需产品实跑；此处仅验收链接。证据 `deliverables/linux-ruyijs-native-env-r77/environment-symbol-delta.json`。

`ce0247e` 将交互和消息域放入同一原生批次，按域保存对象，避免不同目录内的 `realm.cpp` 等同名文件碰撞。主机启动器先核对同架构只读 donor、配置提交、容器隔离和资源上限，实际编译逐一运行，并保留新旧符号身份。

`host185` 已实跑 `native_interaction_verified 0`：82 个交互单元和 5 个消息单元全部编译通过，新 ET_REL 60,678,392 字节、SHA-256 `e2430213b921e9df8ab2bb83f89bb996460e76631df57f7a72f611cf15634c15`。交互 15 条和消息 10 条上一轮引用全部闭合，新增 2 条其他引用，未解析总数 **242 → 219**。容器退出 0、无 OOM，前一批摘要不变。本机 5 项批次与隔离回归通过；回执 `deliverables/linux-ruyijs-native-interact-r78/interaction-symbol-delta.json`。该部分链接没有运行交互或消息功能，完整私有版仍待构建和运行验收。

`e477bf3` 将 Linux Necko helper 移植落入私有源码：使用 POSIX 进程、描述符和原有小端帧，保留旧 Windows 路径。原生 aarch64 本机通过实际回环 HTTP，150,000 字节二进制 POST 完整回返，计时字段、帧内错误后的 session 复用、子进程关闭／回收也通过。对端是 `http.client` 试件；非浏览器 Necko/NSS、非真实 QUIC 握手。x86_64 原生 7 个受限编译单元的部分链接另得 SHA-256 `feb197e098fda4d17449d4bb8712846ec18c47c2c775721fb4aea7bd67901b70`，消除 `AsyncHttp::Wait` 与 `PrewarmNeckoSessions` 两条旧引用，新增 9 条，**219 → 226**；前一批摘要不变、无 OOM。回执 `deliverables/linux-ruyijs-native-carrier-r79/carrier-symbol-delta.json`。其余 AsyncHttp／Abort／资源域实现仍需继续编译和实跑。

`aa029f7` 启动单作业 `resource-network-v1`，包含 177 个已提交资源单元中剩余的 168 个（排除两个 Windows 专用和上批七个），17 个模型文件保持异常策略。`host185` 在 09:25 +08:00 的实际样本为 **80/168** 个已成功编译，断网、2 CPU／4 GiB，未发生 OOM，尚未完成部分链接。证据 `deliverables/linux-ruyijs-native-net-r80/compile-sample.json`；该样本只是阶段性进度。

资源网络随后 `native_resource_network_verified 0`：168/168 单元成功，ET_REL 109,858,816 字节、SHA-256 `ca4f1e6ff50e950d902db1fb146c54d35a5b1e62c67872d26bd30d9d0752e378`；消除 39 条旧引用、引入 10 条新引用，**226 → 197**，`resource_network` 归零。证据在 `deliverables/linux-ruyijs-native-net-r80/resource-symbol-delta.json`。没有 OOM，真实 Necko/NSS 与 QUIC 行为仍未验收。

`72b50b9` 的 Linux Worker POSIX 进程适配通过本机协议试件，真实测试覆盖 dedicated/shared/service 子进程、关闭继承描述符、提前退出、最后一帧及进程组清理；并未执行 JS Worker realm。另以该对象接入原生 x86_64 20 单元 `workers-v1`：`native_workers_verified 0`，消除全部 12 条 Worker 引用且未新增私有未解析引用，**197 → 185**。产物仍是 ET_REL（114,077,432 字节），前一批对象摘要不变，无 OOM。证据 `deliverables/linux-ruyijs-native-workers-r81/worker-symbol-delta.json`。私有可执行文件和 `Context.eval` 仍待实际验收。

## Seed 关系（重要）

`ruyijs-inner` 的 seed 是 `ff-ruyijs` **0.2.1**（`c69875b5`），不是当前的 0.4.1（`3501a90`）。

**0.2.1 没有跨平台代码**——`python/ruyijs/_pipe.py` 仍是 Windows 独占的 127 行。0.4.1 的 AF_UNIX 分支（208 行）是后出现的能力，只能作可行性证据，不能作内部版现状依据。

## 与其他项目的关系

- 与 **RuyiHttp** 共享 31 个 C 符号的 necko ABI（见 `docs/01-architecture.md` §1.2）
- 与 **RuyiTrace** 构成 trace 对账闭环：`trace_diff.py` 比对两者行为差异
- 与 [ruyi-mcp](../../docs/01-architecture.md#5-ruyi-mcp-控制面与组件边界) 的关系是浏览器行为对照。
