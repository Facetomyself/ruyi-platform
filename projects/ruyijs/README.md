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

`76a6ea3` 启动完整 `document-v1`：248 个已提交文档单元，60 个模型文件沿用异常策略，使用固定 Mozilla Sanitizer 源和事件表生成头文件。本机 AArch64 的 C++ 数据检查通过，固定表为 121 个默认元素、58 个默认属性、147 个事件属性；`script`、`onclick` 排除在默认允许表，`onclick` 位于移除表。记录 `deliverables/linux-ruyijs-native-doc-r82/sanitizer-data-check.json`，仅覆盖生成表，无页面 Sanitizer 准入结论。

09:55 +08:00，`native-doc-r82` 断网单作业已编译 38 个单元，`document_metadata.cpp` 因 Windows-only `localtime_s` 失败，OOM 为零，批次仍使用原提交继续。`bbca26b` 保留 Windows 接口并用 POSIX `localtime_r`，本机实跑校验固定日期、闰日及跨午夜时区，格式保持 `MM/DD/YYYY HH:MM:SS`。旧日志保留。早期采样 `deliverables/linux-ruyijs-native-doc-r82/compile-sample.json`。

首批终态 `native_batch 1`：247 个成功、仅 `document_metadata` 失败、未发生 OOM，保留实际部分对象与终态回执 `deliverables/linux-ruyijs-native-doc-r82/original-terminal.json`。`a9f237f` 逐项比较新旧整个私有源树，只准两个日期文件变动；核对 247 个旧对象与其依赖记录、Sanitizer 输入及旧聚合摘要后，仅重编 `document_metadata.cpp` 并重新部分链接。`native_document_repair_verified 0` 产物 202,261,184 字节，SHA-256 `efd8bb5bf88f4cf6b39cdc29b016c1ebe04395ad91abc5d9e9cbaca67cf86925`；相对 Worker 基线消除 10 条旧引用、新增 15 条，总数 **185 → 190**，`document_model` 引用为 0。无 OOM，首批旧对象保持原样。证据 `deliverables/linux-ruyijs-native-docfix-r83/document-repair-symbol-delta.json`。这里只验收文档域 ET_REL；产品链接、完整页面行为和 `Context.eval` 尚待实跑。

`72d124d` 为对象 URL 的 UUID 保留 Windows BCrypt 路径，Linux 使用内核 `getrandom`，并保留原有前缀及版本／变体位。本机 AArch64 C++ helper 真运行通过；`host185` 的 3.10 内核及此次断网容器也实际返回了随机字节（未输出内容）。该小型测试未运行对象 URL 的完整 JS 创建或撤销语义。

原生 `web-platform-v1`（53 个 Web 平台单元＋共用 `WebKit`）终态 `native_batch 1`，51/54 编译成功，无 OOM。Brotli 和 zlib 单元缺本次归档遗漏的**已跟踪 vendor 头**；URLPattern 正则单元是手写 SpiderMonkey 前置声明与 GCC hidden pragma 下的公开可见性不一致。部分 ET_REL 实测消除 30 条旧引用、引入 10 条、**190 → 170**，`WebKit` 的 15 条旧引用全部闭合，但 Web 平台仍有 9 条引用。回执 `deliverables/linux-ruyijs-native-webplat-r84/partial-web-platform.json` 保留原始编译错误。`1208a11` 改用 donor 的 `js/TypeDecls.h`；后续须带上固定 Brotli/zlib 头、重编三个失败单元及此头的旧依赖者，再确认完整批次。没有私有可执行文件或对象 URL 产品行为结论。

`a1a98c2` 按真实依赖清单选出三个失败单元及依赖改动头的 `url_pattern.cpp`，核对剩余 50 个旧对象。带上 8 个固定 vendor 头后，第一轮复验的 Brotli 已通过，zlib 曝出旧断言 `112 == 88`；`d058a5e` 保留 Windows x64 `uLong=4/z_stream=88`，新增 Linux LP64 `8/112` 校验，原私有 zlib-rs 符号前缀保持原样。原生 AArch64 的实际适配器编译及头布局测试通过，未链接 Rust runtime。

最终 `native_web_platform_repair_verified 0`：4 个重编单元与 50 个已核对复用对象重新部分链接，54/54 无错误，ET_REL 213,252,296 字节、SHA-256 `5d74f088a91a904b759492bf1a1b189dcc8a67bc3ab4e65a1db0a8fbdfc8e707`。相对修复前文档基线消除 30 条、引入 1 条，**190 → 161**，`web_platform` 归零；无 OOM，首次失败和旧聚合对象保持原样。回执 `deliverables/linux-ruyijs-native-webabi-r85/web-repair-symbol-delta.json`。此处未运行压缩、URLPattern 或私有 `Context.eval`。

`d57a927` 在断网原生 x86_64 容器实际构建并链接私有 codec：181 个固定文件按摘要检查，沿用 donor Rust 1.100.0，核对六个 `RUYIJS_CS_Z_*` 导出，并编译 35 个 Brotli C 单元。真实 C++ 适配器以小块往返 65,537 字节二进制数据，zlib／raw deflate／gzip／Brotli 压缩长度分别为 2,985／2,979／2,997／1,871，解压逐字节一致，`native_codecs_verified 0`、无 OOM。证据 `deliverables/linux-ruyijs-native-codecs-r86/native-roundtrip.json`。独立探针的 Rust staticlib 包含 std，不能混进最终 SpiderMonkey；产品的 JS CompressionStream、URLPattern 和 `Context.eval` 仍待运行验收。

`35e8197` 为私有主程序配置 `runtime-rest-v1`：90 个已提交 runtime 单元中，精确排除前序已链接的实现和 Windows 专用管道，保留其余 63 个。断网编译使用已提交的 Firefox 绑定顺序头及前序 donor 配置；该批次检查链接依赖，不运行页面导航或消息行为。

`native-runtime-r87` 终态 `native_batch 1`，实际编译 62/63 个单元、无 OOM。唯一错误是 `worker_nested.cpp` 首先引入手写 `JSContext` 声明，与 donor API 的可见性冲突。`8cbeac3` 在该单元最前引入规范 `js/TypeDecls.h`，保留共享头，避免改变已经编译的依赖者；原生重编仍待完成。实际 62 单元部分 ET_REL（SHA-256 `e3a40ea6bdbaab90fd02f62663440cd732f612d9d9f711bf4aab7690e9c2f9d9`）消除 68 条旧引用，暴露 139 条新依赖，剩 232 条。回执 `deliverables/linux-ruyijs-native-runtime-r87/runtime-partial.json`。失败日志和前序对象保留；尚无私有可执行文件。

`f7bb5f8` 复验已 `native_runtime_repair_verified 0`：核对完整私有源树、绑定表、62 个复用对象和依赖记录，只重编修正后的 `worker_nested.cpp` 再部分链接。相对前序基线消除 70 条，暴露 139 条，**余 230 条**；实证是原生 x86_64 ET_REL，SHA-256 `582aed88bedafcb67717252b4971cb4b715f6c39c8e2367f855fcfe94cbab112`。无 OOM，旧部分对象保持原样。证据 `deliverables/linux-ruyijs-native-runtimefix-r88/runtime-repair-symbol-delta.json`。私有可执行文件与真实 JS 行为仍待验收。

样式域首批同时独立编译桥接和 CSS 实现，真实 native `ld.lld` 拦截重复定义；六个展开单元另报告 no-exceptions 失败。原日志独立保留在 `deliverables/linux-ruyijs-native-styling-r91/original-failure.json`。源清单复核发现 52 个 CSS 实现已由三个桥接单元唯一包含，独立编译仅需 `css_color_space.cpp` 加 55 个桥接单元。`b4040ec` 将所有权纳入校验，并以原生 AArch64 最新源码实跑纯 C++ 逻辑：CSS 声明重要性覆盖、margin 简写及选择器优先级通过；这不是 SpiderMonkey 页面行为验收。

修正后的 `native-stylefix-r91` 在同一只读前序 native x86_64 ET_REL 上编译 56 个唯一拥有者，`native_styling_verified 0`、无 OOM。ET_REL SHA-256 `368563a2ccfa06073820a4220a25093512e0d3eef91be27c323456f3484e138f`。消除 26 条桥接和 15 条 CSS 实现引用，未引入私有未解析引用，**230 → 189**。前序摘要不变。回执 `deliverables/linux-ruyijs-native-styling-r91/styling-symbol-delta.json`；全部 10 项批次回归通过，完整产品与页面样式运行仍待验证。

`057ce17` 将 59 个几何单元分成 41 个可移植单元与 18 个字体／字形／SVG 原生后端单元，后者保留待移植，不以空实现填充。原生 AArch64 的独立 C++ 试验通过矩阵平移与二维判定、SVG 相对控制点和无效输入检查；无浏览器 DOM 或原生描边验收。11 项批次回归通过。

`native-geometry-r92` 原生 x86_64 断网单作业 `native_geometry_portable_verified 0`：41 个单元编译与部分链接均通过，消除 20 条旧引用并新增 8 条，总数 **189 → 177**。目前仍有 12 条几何后端引用（主要是字体配置、度量和 SVG 描边），待使用合适的原生 Linux 后端，不代表完整几何域通过。ET_REL SHA-256 `a884d0cd88125485af75062a1b7ea0653d647eb387c2630672da7e56274e7ff7`，前序对象摘要不变、无 OOM。回执 `deliverables/linux-ruyijs-native-geometry-r92/geometry-symbol-delta.json`，产品可执行文件与 `Context.eval` 仍待验。

`f0cf666` 将 `font_config` 与 `font_preferences` 的可移植逻辑从 DirectWrite 后端分开，Linux 共享严格 Unicode 标量转换。本机原生 C++ 验证非 BMP、错误／截断／过长序列原子拒绝。原生 x86_64 使用固定 HarfBuzz 头和已提交字体表，2 个单元 `native_font_profile_verified 0`，消除 6 条、不新增私有引用，**177 → 171**，剩 6 条几何符号主要是 `SystemFonts` 和 `SvgPathBounds`。新 ET_REL SHA-256 `c4b324cbbf9ae034d06bfcdc725c0d880e405001a746c20e126ab371b78240f9`、前序对象不变、无 OOM。

`a915eef` 的独立运行探针直接用这两个真实对象，链接同一 donor 中实际提供 `moz_xmalloc` 与 `gMozCrashReason` 的对象（之前两次失败保留）。断网实跑 `en-US → serif`，`ja-JP`／`zh-CN → sans-serif`，DPR=1／2 的自动文本优化阈值 20／10。这只验证配置与决策，不选择已安装字体、不进行度量或绘制。见 `deliverables/linux-ruyijs-native-fontprofile-r93/font-profile-validation.json`。

`69946ae` 为 Linux `SvgPathBounds` 接入 Cairo，Windows 保留 Direct2D。实现覆盖直线、二次／三次曲线、旋转 SVG 椭圆弧及平头斜接描边，并限制 Cairo 固定点坐标范围；越界返回失败且保留原输出。使用 Ubuntu `libcairo2-dev` 头、实际 AArch64 Cairo 1.16.0 库原生链接并运行 17 个用例，UBSan 检查与矩阵／SVG 解析回归通过。Linux 最终链接需要 Cairo 开发头及 `-lcairo`；这一阶段只实跑独立后端。回执 `deliverables/linux-ruyijs-svg-path-r94/svg-native-validation.json`。

随后 `c95d91b` 在 x86_64 donor 配方下解决两层实际失败：Firefox 自带头要求生成的 `cairo-platform.h`，改用签名 Ubuntu Noble 索引核对的公开开发头；donor 默认隐藏符号会阻止链接真实 Cairo 动态库，故只把这些 C 声明恢复为默认可见。`native_svg_path_relocation_verified 0` 闭合 `SvgPathBounds`，私有引用 **171 → 170**（余 5 条几何引用均在 `SystemFonts`），前序 ET_REL 不变。精确复用该批次的 `svg_path.o`，单独链接并以 UID 1000 断网实跑 Ubuntu 24.04 Cairo 1.18.0 的全部 17 项用例，实查 17 个 Cairo 导入可见性和加载，未发生 OOM。回执 `deliverables/linux-ruyijs-svg-abi-r95/svg-abi-validation.json`。其余私有产品的完整链接和页面 `getBBox()` 仍待验收。

`c500b3c` 给 Linux `SystemFonts` 接入 Fontconfig 选字与 FreeType 行高、SVG `ex/ch/ic/cap` 度量；Windows 继续使用原 DirectWrite 实现。Linux 使用系统配置排序，在打开字体前调用字体配置过滤器，按 CSS app unit 舍入；此批仅处理可缩放字体。原生 AArch64 在仅有 DejaVu Sans/Serif 的隔离字体目录实跑，验证 16px 行高 18.633333、`ex=8.75`、`ch=10.183333`、`ic=16`、`cap=11.666667`，覆盖尺寸缩放、候选过滤、无可选字体和无效输入。用系统真实 Fontconfig 2.13.1、FreeType 2.11.1 通过 UBSan；生产适配层通过独立编译检查。最终 Linux 链接需 Fontconfig/FreeType 的开发头与动态库。这份 ARM64 回执未改变 x86_64 聚合符号计数。回执 `deliverables/linux-ruyijs-font-metrics-r96/font-metrics-validation.json`。

`1ae925d` 用签名 Ubuntu Noble 开发包固定的 58 个头编译 `system_font` 与 `font_metrics_linux`，`native_font_metrics_relocation_verified 0` 闭合 4 条私有引用（构造、析构、行高、SVG 字体单位），**170 → 166**，未引入新的私有引用；实查 23 个默认可见的外部 Fontconfig/FreeType 导入。用这两个真实对象与已有 CSS、字体配置和 donor 分配器对象链接独立探针，原二进制 6,623,096 字节，首次仅超过输出回收上限，核对摘要后直接重放同一 ELF。UID 1000、断网、两种 DejaVu 独立字体；直接调用 `SystemFonts` 验证 16px 与 32px 度量、非法或零尺寸、默认字体路径，未发生 OOM。回执 `deliverables/linux-ruyijs-native-fontmetrics-r97/font-metrics-abi-validation.json`。该 x86_64 聚合对象的几何域只剩 `SystemFonts::Measure`。

`9a8ae1f` 实现 Linux `SystemFonts::Measure` 的水平 SVG 文本后端：沿用 Fontconfig 候选与字体可见性过滤，用 FreeType 打开可缩放 SFNT 字型，HarfBuzz 塑形、FriBidi 计算双向嵌入等级，按逻辑 UTF-16 索引回填字簇，并投影仿射边界。原生 AArch64 用隔离 DejaVu 字体和真实库通过 `ffi`、组合符、代理对、希伯来文混排、阿拉伯文 lam-alif、回退、输入校验及 UBSan，实测 16px `ffi=15.4667px`、阿拉伯样例 `32.8500px`。Fontconfig/FreeType 行高回归及 11 项批次回归通过，生产适配层通过编译检查。回执 `deliverables/linux-ruyijs-svg-text-r98/svg-text-validation.json`。这份 ARM64 回执未改变 x86_64 聚合符号计数。

`13954bf` 的独立 x86_64 重建从前字体阶段基线（177 条）重编六单元，闭合几何域全部 12 条，余 165 条私有引用；相对已公示的行高批次 **166 → 165**，唯一差异是 `SystemFonts::Measure`。第一版保留的实际 ET_REL 仍含两个 `HIDDEN` 的旧 HarfBuzz 导入；修复后全聚合中 69 个系统几何导入均为 `DEFAULT`，已验 `SvgPathBounds` 对象仍逐字节相同。用同一批次对象运行 137,440 字节独立探针，断网 UID 1000，真实 HarfBuzz 8.3.0／FriBidi 1.0.13：行高和 SVG 单位回归通过；`ffi=15.4667px`、阿拉伯样例 `32.8500px`、希伯来与拉丁混排 `75.6167px`，UTF-16 字簇和仿射变换通过。无 OOM，12 项批次回归通过。回执 `deliverables/linux-ruyijs-geometry-abi-r99/geometry-abi-validation.json`。Canvas 栅格、页面／完整产品和更广的 SVG 文字布局仍待验收。

`a74bd1e` 将 18 个 Web API 域的 116 个翻译单元接到已经核验的几何基线；按域区分同名对象，异常开启仅限两个 IndexedDB 模型单元。原生 x86_64 `native_web_services_verified 0`，116 个均通过编译及 ET_REL，消除 102 条原引用、新增 2 条，**165 → 65**，新依赖为 `web_crypto::ComputeDigest` 与 `web_geometry::LocalFontFamilyInstalled`；其余未闭合来自 Audio、Canvas、Crypto、GPU、Graphics、Media 和 RTC。回执 `deliverables/linux-ruyijs-webservices-r100/web-services-validation.json`。编译与部分链接暂无完整 Web API 或页面验收结论。

真实 IndexedDB 模型复现了 `2^53+1` 被舍入的旧错误；修复后最后可用的自动键 `2^53` 仅生成一次，耗尽标记随写事务提交，回滚恢复生成器。原生 AArch64 UBSan 测试与 x86_64 同批精确对象的独立探针均验证提交、回滚、唯一索引、源隔离、版本升级回滚与生成器耗尽。ARM64 原始失败保留在 `deliverables/linux-ruyijs-indexeddb-r100/`；13 项批次回归通过、无远端 OOM。该模型运行不等同于 JS IndexedDB 页面或持久化验收。

`f138943` 给 Linux `local()` 接入真实 Fontconfig 全名／PostScript 名查找：精确匹配忽略大小写，查询不走替代字体，按字体 profile 过滤，拒绝 NUL 和无效宽字符；Windows 路径保持原样。验证闭合该字体查询，以及 30 个 WebAudio、23 个 WebRTC 单元；54 个全部原生编译及部分链接，**65 → 46**，消除 19 条旧引用、零新增，余 Canvas 13、Crypto 6、GPU 4、Graphics 6、Media 17。71 个系统几何导入保持默认可见，未发生 OOM。

ARM64 UBSan 与同对象 x86_64 探针实际通过 Fontconfig 两字体的全名／PostScript、隐藏和替代名过滤，也实跑 48kHz 的 1kHz PCM，两个 128 帧量子与 256 帧连续运行逐样本一致，另过方波和参数限幅／实例隔离。x86_64 断网 UID 1000，使用真实 profile 对象。14 项批次回归通过。证据 `deliverables/linux-ruyijs-audiortc-r101/audio-rtc-font-validation.json` 与 `deliverables/linux-ruyijs-audio-font-r101/audio-font-validation.json`；WebRTC 当前只验证部分链接，JS 页面、音频设备、RTC 媒体传输及完整私有程序仍待验收。

在完全干净的 Git 源快照中，WebGPU 模型的旧实现允许负限制值。`75cf2bc` 修复非有限及负限制值，初始化改用 RAII，功能集直接使用底层聚合状态而不维护副本。ARM64 原生 UBSan 实际运行软件 GLSL 与 MSAA、能力子集回滚和 64 位限制值；实得 RGBA `[255,127,0,255]`、抽样覆盖 `[4,2,0]`。原始失败与修复验证位于 `deliverables/linux-ruyijs-graphics-r102/graphics-software-validation.json`。两处既有本地 WebGL 修改未纳入快照；此回执不覆盖页面、驱动或硬件 GPU。

原生 x86_64 `native_graphics_gpu_verified 0`：33 个 Web Graphics 和 17 个 WebGPU 单元全部通过 ET_REL，消除 10 条旧引用、未引入新私有引用，**46 → 36**，余 Canvas 13、Crypto 6、Media 17。用同批五个精确对象与 donor 分配器构建断网探针，顶点 `[0.5,-1,0,1]`、颜色 `[255,127,0,255]`、MSAA 覆盖 `[4,2,0]` 与 ARM64 结果一致，4 GiB 数值、非法限制拒绝和能力回滚均通过。无 OOM，15 项批次回归通过。见 `deliverables/linux-ruyijs-graphicsgpu-r102/graphics-gpu-abi-validation.json`；仍无真实网页、GPU 设备或完整私有程序验收。

`99796e9` 将 Media 的 APNG／WebP 动画接口与 WIC 解耦，Linux 静态和帧补丁分别以 libpng／libwebp 真实解码，再做预乘 BGRA 合成和缩放。Windows 继续走 WIC。Linux 校验源、目标及累计帧像素预算，动画重建还检查累计编码字节；无效整图解码保留原结果。AArch64 独立 C++ 探针在仅 lo 的命名空间用系统 libpng 1.6.37／libwebp 1.2.2 通过 UBSan、静态图像、两帧 APNG／WebP、缩放像素、流中前缀和截断 EOF 区分。支持查询仅报 PNG／WebP；JPEG、GIF、AVIF、BMP、ICO、ICC 色彩转换、x86_64 私有聚合和浏览器 ImageDecoder 待验。这份 ARM64 记录未重测当时的 x86_64 私有余量。运行记录 `deliverables/linux-ruyijs-imagecodec-r103/image-codec-validation.json`。

`b00a758` 从已核验 Graphics/GPU 基线构建 65 个 Media 单元，排除未移植的 `image_avif`、`image_color` 和 `image_gif`，并锁定签名 Ubuntu Noble 包的 9 个开发头。原生 x86_64 `native_media_png_webp_verified 0`，**36 → 19**，消除 Media 的全部 17 条旧私有引用，零新增；剩 Canvas 13、Crypto 6。聚合 ELF 实查 32 个 libpng／WebP 导入均为默认可见。使用同批六个精确对象和真实 Noble 动态库，在断网 UID 1000 原生重跑静态 PNG／WebP、两帧 APNG／WebP、预乘 BGRA、缩放、截断 EOF 与损坏输入，均复现 ARM64 结果。无 OOM，16 项批次回归通过。回执 `deliverables/linux-ruyijs-media-r105/media-png-webp-validation.json`。Media 私有符号闭合只覆盖该已编译范围；剩余格式、ICC 和浏览器页面仍待验证。

`6356385` 纳入已审阅的 Linux OpenSSL 字节后端，系统 libcrypto 声明保持默认可见，Windows CNG 单元原样保留。新增固定原版 Windows PE 在 Wine 9 的 29 个合成向量：摘要、HMAC、CBC、GCM；在 21 组 GCM 中兼容原件的 5 组接受和 16 组拒绝。ARM64 UBSan 与 AMD64 同批精确对象实跑均逐项匹配，另验证三条 EC 曲线及失败解密保留调用者输出。原生 x86_64 `native_crypto_openssl_verified 0`：19 个 Crypto 单元（排除两份 Windows 后端），135 个签名 OpenSSL 公共开发头、58 个默认可见导入；闭合全部 6 条旧引用、零新增，**19 → 13**，均为 Canvas。AMD64 断网 UID 1000，libcrypto 3.0.13，未发生 OOM，17 项批次回归通过。[固定 PE 向量](../../submodules/ruyijs/ci/fixtures/openssl-windows-pe-contract.json)；运行回执 `deliverables/linux-ruyijs-crypto-r106/crypto-openssl-abi-validation.json`、`deliverables/linux-ruyijs-crypto-arm64-r106/crypto-openssl-validation.json`。第三方 Linux wheel 继续只作对照；WebCrypto Promise／WebIDL、产品构建接线和完整 `dist/js` 仍待验收。

`b2830b8` 在 Crypto 基线上编译 63 个可移植 Canvas 单元，暂时排除仍依赖平台字形与 Skia 后端的 `skia_target` 与 `skia_subset_stubs`，不以空实现顶替。原生 x86_64 `native_canvas_portable_verified 0`：13 条旧私有引用全部闭合、零新增，余 12 条（`skia_target` 8 条、字体几何 4 条）。同时修复一个真实缺陷：`raster_fill.cpp` 原先在把坐标转成 `int` 之后才检查范围，ARM64 UBSan 在 `-1e+20` 上直接报越界；改为逐点在舍入与转换之前检查有限性与既有 ±8191 边界，正常像素逐字节不变，并把 `EncodePNG`／`Base64`／`PngMetadataHex` 的声明从 SpiderMonkey 头迁到 `png_codec.h`。同批对象在断网环境实跑 8×6 RGBA 栅格与 PNG 回环，独立 CRC、zlib 和 Sub 滤波器反推逐像素核对 48 个像素（28 透明／16 红／4 蓝），94 字节 PNG 摘要固定；ARM64 先复现后修复。无 OOM。回执 `deliverables/linux-ruyijs-canvas-r107/canvas-portable-validation.json`、`deliverables/linux-ruyijs-canvas-raster-r107/raster-bounds-validation.json`、图片 `deliverables/linux-ruyijs-canvas-r107/canvas.png`。这里没有 Skia 目标、字体栅格或浏览器 Canvas。

`804b6ef` 把 Canvas 剩余的 Skia 后端第一次接到固定 Firefox 原点真实的原生 Skia 产物上。先只读审计：要求 Firefox 提交与基线完全一致、`gfx/skia` 工作区无改动，实查 x86_64 objdir 中 **76 个**原生 ET_REL（76,498,176 字节）、`backend.mk` 含 `MOZ_SKIA` 与 `TRIMMED=1`，并要求 `SkSurfaces::WrapPixels` 与 `SkCanvas::drawRect` 是真定义而不只是重定位。第一次链接失败给出确切的第一个阻塞点：`/usr/bin/ld: hidden symbol 'hb_face_destroy' isn't defined`。原因是探针只带 Skia 与 mozalloc／mfbt，没带 Firefox 自己的 HarfBuzz；该 provider 不在 `gfx/harfbuzz` 目录，而是 `gfx/harfbuzz/src` 下的单个统一对象 `Unified_cpp_gfx_harfbuzz_src0.o`（38 MB，定义 28,044 个 `hb_` 符号，链接可见性为 `HIDDEN`）。补上该真实对象后，符号闭合剩余 222 条，其中 176 条由镜像内真实共享库（libc／libm／libstdc++／libgcc_s／libexpat／libz）提供，46 条只被 `--gc-sections` 回收掉的 subsetter 与 typeface 段引用（29 条 FreeType、9 条 Mozilla FreeType 胶水、3 条 `MOZ_Z_`、2 条 `PrintfTarget`）。

这一轮还暴露一个与代码无关的真实运行条件：探针镜像给 `/tmp` 挂的是 `noexec`，所以二进制虽然成功生成（7,010,232 字节）却根本起不来，前两次运行据此写出空结果。第三次显式使用可执行 tmpfs 后，`skia_cpu_probe_draw 0`：4×4 `kBGRA_8888` 预乘 CPU surface，`SkSurfaces::WrapPixels` 后 `drawRect` 落在 (1,1)-(3,3)，得到 4 个不透明红、12 个透明，`bgra.json` 逐像素断言通过。容器为 network none、只读根、1 CPU、2 GiB RAM+swap，`OOMKilled=false`、退出码 0。回执 `deliverables/linux-ruyijs-skia-cpu-r112/skia-cpu-probe-validation.json`。这次通过只说明该 CPU 光栅与绘制路径可用；Canvas 文字字形、度量与掩码、私有 `CanvasSkiaTarget` 集成、`dist/js`、浏览器渲染与 PDF subset API 都还没验收。

`39607d9` 把 Canvas 文字第一次真正接到固定 Firefox 的 Skia 上，结论是**链接通了、绘制没通**，而且失败点被精确定位到 `main` 之前。可复用的技术事实有四条。第一，固定 Skia 产物里**只有** `SkFontHost_cairo.o` 一个从 FT_Face 造 typeface 的入口，`SkFontHost_FreeType_common.o` 一个 `SkTypeface`/`SkFontMgr` 工厂都不定义。第二，这个 Cairo 端口把传入的 context 原样保存，并在每个字形上回调 `mozilla_*SharedFTFace`，所以传 `nullptr` 必然在 `mozilla_LockSharedFTFace` 解引用空指针——换成真实 `SharedFTFace` 后该崩溃消失。第三，用 WebRender 的真实 Rust 导出满足 `mozilla_glyphslot_embolden_less` 是对的：整个 `libgkrust.a` 里该符号所在 CGU 是 1.47 GB 单体，2 GiB 容器直接 OOMKilled；只取 `wr_glyph_rasterizer` 那个 7.7 MB 成员即可，因为该导出自带独立 text 段、只调用 `FT_MulFix`/`FT_Outline_Embolden`/`FT_GlyphSlot_Embolden`。第四，FreeType 的间接依赖（libpng/libbz2/libbrotlidec/libz）不在编译镜像里，`DT_RUNPATH` 只覆盖二进制自身的直接依赖，必须给运行期搜索路径。

最终可执行文件 8,413,304 字节、链接成功（`link_rc=0`），运行以 `SIGSEGV` 退出，且 `stderr` 只有 `stage:ctor` 一行、`rip 0x0`、`advance anchor 0x0`——说明故障发生在本探针构造函数之后、`main` 写入任何阶段标记之前，是某个静态初始化通过空函数指针发起调用。这一轮没有画出任何字形、没有比较任何像素，所以**不构成 Canvas 文字验收**。回执 `deliverables/linux-ruyijs-skia-text-r138/skia-text-attempt-validation.json`。定位这个静态初始化需要初始器级别的追踪，而不是继续加阶段标记。

这一轮的**方法本身**给出了可复用的结论，值得单独记下来：用一个什么都不做的 `main`（只写一行 `main reached`）逐级叠加真实 donor 对象，就能把「静态初始化是否干净」和「业务代码是否正确」彻底分开。阶梯十步全部打印 `main reached`：`mozalloc+mfbt` → 76 个 Skia → HarfBuzz 统一对象 → gfx/2d 与运行时 FreeType → XPCOM string → libpref → XPCOM base0 → base1 → threads0 → 真实 `libnspr4.so`。

这同时**纠正了上一轮的错误判断**。上一轮把「加入 `xpcom/base2` 就崩」读成「base2 不安全」，实际是 base2 恰好是第一个需要 `mozilla::Mutex` 的步骤，而定义 `BlockingResourceBase` 的对象此时还没进链接，于是 mutex 在未构造状态下被使用。base0、base1、threads0 各自单独都能通过，它们才是 `BlockingResourceBase` 的真正定义者。回执 `deliverables/linux-ruyijs-ctor-bisect-r144/ctor-ladder-validation.json`。

剩下的问题收敛得很具体：即使 base0/base1/threads0 和 `libnspr4` 都已链接、且 `libnspr4.so` 已实测是 `NEEDED` 项，文字探针仍在 `SharedFTFace` 构造内部以 `rip 0x0` 结束——mutex 构造函数里还有一处间接调用解析到地址 0。这条路径要真正打通，需要在探针里提供 XPCOM 的静态初始化入口，而不是继续逐个对象试链。此前所有文字相关结论保持为「未验收」。

这一轮找到了剩余 12 条私有引用里那 4 条字体几何引用的**真正根因**，并且是工程缺陷而不是缺依赖：私有 `src/web_geometry/font_backend.h` 无条件 `#include <windows.h>`、`<dwrite.h>`、`<wrl/client.h>`，所以四个 Canvas 文字 owner（`MeasureCanvas`、`BuildCanvasGlyphMasks`、`CanvasGlyphRuns`、`ReleaseCanvasGlyphRuns`）在非 Windows 上**根本无法编译**，Linux 分支自然一行实现都没有。

按上游树早已采用的同一约定修好：Windows 路径保持逐字节不变，非 Windows 提供 owner 实际用到的 DirectWrite 值类型与接口面（`DWRITE_FONT_METRICS`、`DWRITE_GLYPH_METRICS`、`DWRITE_GLYPH_OFFSET`、`DWRITE_GLYPH_RUN`、`DWRITE_MAKE_OPENTYPE_TAG`、`SUCCEEDED`/`FAILED`、`ComPtr`、`IDWriteFontFace`），Darwin 继续走 `font_face_mac.cpp`。

新增 `src/web_geometry/font_face_linux.cpp` 用真实 FreeType 实现这层接口，数值语义按 DirectWrite 而不是 FreeType 的默认：度量取 design unit、`advanceWidth` 无符号、侧边距有符号、`verticalOriginY` 取 y 向下墨迹顶、`TryGetFontTable` 返回带所有权释放上下文的缓冲、tag 字节序按 owner 既有假设。编译过程暴露三个真实错误：`const void*` 到 `FT_Face` 的 `static_cast` 掉限定符且无法用那种形式的 `const_cast` 恢复；`TT_OS2` **根本没有下划线字段**，下划线数据在 post 表里、FreeType 直接挂在 face 上。

结果：原生 AMD64 `compile_rc 0`，12 个接口方法（含两个构造、析构、`GetMetrics`、`GetGlyphIndices`、`GetDesignGlyphMetrics`、`GetGdiCompatibleGlyphMetrics`、`TryGetFontTable`、`ReleaseFontTable`、`AddRef`、`Release`、`CoreFont`）逐一在目标文件里确认为已定义，对象 SHA-256 `49252f2b…`。**这只是编译**：没有打开任何字体、没有查任何字形、没有比对任何度量。`GetGlyphRunOutline` 属于独立的描边接口、Linux 侧仍未实现，那 4 个 `SystemFonts` 方法也还没有函数体。回执 `deliverables/linux-ruyijs-font-face-r155/font-face-compile-validation.json`。

平台拆分之后立刻得到两个真实结论，一个好消息、一个坏消息，都必须分开记。

**好消息：`canvas_text` 与 `glyph_runs` 第一次在 Linux 上编译通过。** 原生 AMD64，对象 SHA-256 分别是 `53b3dbdc…`、`1dea82aa…`。而剩余 4 条私有引用——`MeasureCanvas`、`BuildCanvasGlyphMasks`、`CanvasGlyphRuns`、`ReleaseCanvasGlyphRuns`——**全部定义在这两个文件里**，不在别处。所以之前认为「还要另找实现」的判断是错的，实现一直都在，只是编译不了。过程中还纠正了第二个真缺陷：`IDWriteFontFace` 原先被我放进命名空间，而 `glyph_mask.h` 按 Windows 头的习惯在**全局**前向声明它，于是报“member access into incomplete type”——把它移回全局作用域后 `glyph_runs` 立即通过。

**坏消息：能编译不等于能链接。** 逐个查这两个对象未定义的私有符号，得到的清单是：`canvas_text` 需要 `CanvasFontBaselines`、`FontCollection::Initialize`、`FontCollection::Select`、`MissingFontRun`、`ShapeFont`；`glyph_runs` 需要 `FontCollection::Initialize`、`FontCollection::Select`、`GlyphColorMask`、`GlyphMask`、`ShapeFont`。这些符号的**定义方本身仍然只在 Windows 上可编译**：`glyph_mask`／`glyph_color`／`glyph_palette`／`glyph_style` 分别要 `dwrite_2.h` 的 rendering params、COLR 接口和 palette 接口，`canvas_text_path` 要 `d2d1.h` 的 Direct2D 几何 sink，`GetGlyphRunOutline` 更是整个缺失。

所以真实的剩余工作量不是「补 4 个函数」，而是「把 mask／colour／palette／style／outline 五个 owner 从 DirectWrite 专有接口上剥下来」。这一轮把这句话从推测变成了有清单的实测。回执 `deliverables/linux-ruyijs-canvastext-r156/canvas-text-compile-validation.json`。没有链接、没有打开字体、没有查字形、没有任何度量或像素比对。

这一轮把「字体选择」这一层真正打通了。`FontCollection::Initialize` 与 `Select` 原本只有 DirectWrite 实现，现在有了 Linux 版：用 Fontconfig 解析同一个 `FontInput`（家族列表、引号、generic 替换、`-moz-default`），再用 FreeType 打开选中文件，交给上层的 `SelectedFont` 与 Windows 完全同形——所以四个 Canvas owner 这一层不需要任何平台分支。`LineMetrics`／`SvgLengthMetrics` 用的 Fontconfig/FreeType 度量集合也挂在同一个对象上，不再走第二条路径。

四个单元连同真实依赖一起编译通过（原生 AMD64）：

| 单元 | 对象 SHA-256 |
|---|---|
| `font_face_linux` | `404e9154…` |
| `font_collection_linux` | `dbc87472…` |
| `canvas_text` | `28a21287…` |
| `glyph_runs` | `827872df…` |

**关键进展在未定义符号清单上**：`font_collection_linux` 现在剩下的私有依赖全是**可移植代码**——`CssSplit`／`CssTrim`／`CssLower`、`DefaultGenericFamily`、`GenericFamilyOverride`、`FontFamilyVisible`、`LinuxResolveFonts`。这些在 Linux 上都已能编译，不再是 Windows 专有接口。也就是说字体选择这条链已经解决。

真正还剩的是上层：`ShapeFont`、`CanvasFontBaselines`、`MissingFontRun` 在 `font_shaping.cpp`／`font_missing.cpp`，`GlyphMask`／`GlyphColorMask` 在 `glyph_mask.cpp`／`glyph_color.cpp`，它们仍然要 `dwrite_2.h`。这一轮如实把缺口缩小成这两组，而不是笼统说「Canvas 文字还没好」。回执 `deliverables/linux-ruyijs-lincollect-r158/lin-collection-validation.json`。仍然没有链接、没有打开字体、没有查字形、没有任何度量或像素比对。

这一轮把缺口又缩小了一格，并且把一个「看起来只是路径问题」的坑判成了设计耦合。

**打通：`font_shaping` 编译通过**（对象 SHA-256 `d99f83bb…`）。它正好定义 `ShapeFont` 与 `CanvasFontBaselines`——上一轮清单里五个 Windows 专有符号中的两个，现在有了能在 Linux 上编译的真实实现。

**卡住：`font_missing`（`MissingFontRun`）。** 它从 Mozilla 只借了一个二元属性 `Default_Ignorable_Code_Point`，但那个头文件 `mozilla/intl/UnicodeProperties.h` 会连带拉进整棵树，且每修一处就露出更深一层：

```
UnicodeProperties.h  →  mfbt (需 XP_UNIX，否则 UniquePtrExtensions 报 "Unsupported OS?")
                     →  nsError.h  →  ErrorList.h（objdir 生成文件）
                     →  nsISupportsImpl.h  →  prthread.h（NSPR）
                     →  prtypes.h  →  obsolete/protypes.h
```

我一开始把它当成挂载路径没配全，逐个补了 `XP_UNIX`、objdir 根、NSPR include——每补一个就前进一层，但这一层背后永远还有一层。到 `obsolete/protypes.h` 时判定：这已经不是路径问题，而是**为一个布尔值把 mfbt／XPCOM／NSPR 整条头文件链和运行时都绑进私有树**的权衡问题。

**这是一个需要决策的分叉，不是继续试错能解决的**：要么把真实 Mozilla 头文件链及其运行时接进来，只为这一个判断；要么在私有树里自己实现 `Default_Ignorable_Code_Point`。注意 HarfBuzz 只暴露 general category，**没有**这个二元属性，而用 category 近似会把集合里的 `Lo` 与 `Mn` 成员判错，所以不能拿 category 糊弄过去。

回执 `deliverables/linux-ruyijs-shaping-r160/shaping-compile-validation.json`。仍然没有链接、没有打开字体、没有查字形、没有任何度量或像素比对。

上一轮那个「为一个布尔值拉进整条 Mozilla 头文件链」的分叉，这一轮选了第二条路：**在私有树里自己实现 `Default_Ignorable_Code_Point`**，不再依赖 `mozilla/intl`。

关键是不能凭印象写。第一版我就是凭记忆列了一小张表，**整个 Cf 与 White_Space 部分全漏了**——如果只抽样测几个码点，这个错误完全测不出来。所以做法是从规范定义出发：`Other_Default_Ignorable_Code_Point + Cf + Variation_Selector + White_Space` 减去列明的例外，用 Unicode 数据算出完整集合，压缩成 **23 个连续区间、4204 个码点**。

然后用**全集合比对**验证，而不是抽样：

| 项 | 值 |
|---|---|
| 目标 Unicode 版本 | 13.0.0 |
| 独立基准（Python `unicodedata`） | 4204 |
| 私有实现输出 | 4204 |
| 缺失 | 无 |
| 多余 | 无 |

比对过程还暴露了一个容易误判的地方：host185 镜像里的 Python 是 **Unicode 9.0**，拿它当基准会把 `0x13439–0x1343f`（Unicode 14 才分配的埃及象形文字格式控制符）报成“缺失”。在 13.0 与 9.0 之间做比对，差异来自版本而不是表。所以现在基准**锁定 13.0**，版本不符时明确报 `inconclusive`，而不是报 mismatch。

这里要记清一条判断依据：**HarfBuzz 只暴露 general category，没有这个二元属性**；而这个属性既不是“Cf”也不是“White_Space”——它会加上变体选择符、又会减掉两者的成员，用近似集合会判错真实码点。

回执 `deliverables/linux-ruyijs-unicode-r161/unicode-ignorable-validation.json`。`font_missing` 还没链接、没打开字体、没查字形。

这一轮做了一件此前一直没有做过的事：**真正执行了 Linux 字体路径**，而不只是编译。用的单元是自足的 `font_metrics_linux` 与 `font_shape_linux`——`font_config` 把 fonts 配置组和 SpiderMonkey 绑定写在同一个文件里，属于完整产品链接，不该为探针拆开，所以 `MeasureCanvas` 这一轮没跑。

真实运行 12 项全部通过，且数字与历史基准**逐项一致**：

| 指标 | 本轮 x86_64 | r99 x86_64 exact-probe | 结论 |
|---|---|---|---|
| `line` | 18.6333 | 18.6333 | 一致 |
| `ex` | 8.75 | 8.75 | 一致 |
| `ch` | 10.1833 | 10.1833 | 一致 |

`ic=16.0000`、`cap=11.6667`，32px 时各项**翻倍**，0.001px 的尺寸**向下取整为零且不报错**，HarfBuzz／FriBidi 塑形 `Hamburgefonstiv` 得到 `length=138.0667`、每个字符都有盒子、盒子有高度。

过程中暴露了真实的依赖闭包，这是之前从未测到的：Fontconfig 需要配置文件与字体目录（否则**一个字体都选不到**），而完整运行时闭包是 `libfreetype`、`libfontconfig`、`libharfbuzz`、`libfribidi`、`libexpat`、`libglib-2.0`、`libpcre2-8`、`libgraphite2`、`libpng16`、`libbz2`、`libbrotlidec`、`libz`——每缺一个就在加载期失败，逐个才补齐。

一个细节值得记：只读运行时下 Fontconfig 会打印 `No writable cache directories`，那是**缓存警告而不是查找失败**，所有度量都正常解析。

回执 `deliverables/linux-ruyijs-font-measure-r163/font-measure-validation.json`。

这一轮把上一轮刻意没跑的 `MeasureCanvas` 真正链接并执行了：13 个单元编译、链接成功，**10 项检查通过 9 项**。为此先做了一次按职责的重构——`font_config.cpp` 原来把配置值、读访问器和 SpiderMonkey 写入入口塞在一个文件里，导致「只读配置」的单元也要 `jsapi` 才能编译。把配置状态与三个读访问器拆到 `font_config_state.cpp`（只依赖标准库），JS 写入侧留在原处；Windows 两个单元都链接，行为不变。

按单元实测的边界现在是：`font_preferences`、`font_config_state`、`font_shaping`、`canvas_text`、`system_font`、`css_components`、`unicode_default_ignorable` 全部独立成立，只有 `font_config.cpp` 需要 SpiderMonkey——因为它是 JS 入口，这个划分是对的。

链接过程中还补上了两处真实的平台缺口，而不是绕过：

- `FrameMaxDescent` 整个落在 `_WIN32` 分支里，但它的算法只是对字体度量做算术，唯一平台耦合点是 `BadUnderlineFamily`。把函数移到平台块之外共用，并为 Linux 用 SFNT `name` 表实现同一张 CJK 家族名单的判定。
- `BadUnderlineFamily` 因此在头文件里有了跨平台声明，Windows 定义也要离开匿名命名空间以匹配——**函数体一字未改**。

**通过 9 项**：单字推进为正、单字有墨迹、墨迹在字体盒内、alphabetic baseline 为零、ascent/descent 为正、两字推进大于一字、两字等于一字的 2 倍、空格有推进、双倍尺寸双倍推进。实测 `width16=8.0000`、`width32=16.0000`、`ascent=15.0000`、`descent=4.0000`。

**失败 1 项，是个真实语义问题**：`spaces report no ink`。三个空格报告的墨迹框是 `left=0.7969 top=-14.1094 right=27.9969 bottom=4.7188`——纵向与单字 `H` 完全一致。原因是 `font_shaping.cpp` 处理空格推进后**继续走通用墨迹累积**，把按推进算出的框并进了 run ink。这不是移植引入的：`font_shaping.cpp` 是共享单元，Windows 走同一条路径。而 r99 的探针从未测过空格，所以此前没有任何回执覆盖到它。

修它会同时改变两个平台的生产行为，因此**这一轮不改**——那是一个应当单独决定的问题，不该夹在移植探针里顺手做掉。回执 `deliverables/linux-ruyijs-measure-canvas-r163/measure-canvas-validation.json`。

上一轮我把 `spaces report no ink` 的失败判成「共享代码的既有行为」，理由是 `font_shaping.cpp` 是共享单元。**这个判断是错的**，错在我没有验证输入。这一轮直接测了每个码点的真实设计度量：

```
space  gid=3  adv=651  lsb=0  rsb=651  advH=2048  voy=0  ink_w=0  ink_h=2048
```

问题一眼就出来了：**`ink_h=2048`**。所有者读这些字段时是把它们当一个墨迹矩形用的——高度 = `advanceHeight - tsb - bsb`、顶 = `tsb - voy`。而我写的 `GetDesignGlyphMetrics` 把 `advanceHeight` 取了 FreeType 的 `vertAdvance`（字体无 vmtx 时返回 em 高度），`topSideBearing` 又来自**水平**方位。于是每个字形都报成 em 高，宽度为零的空格也就有了盒子。

按 Mac 实现的语义修正后：

| 码点 | 修正前 `ink_h` | 修正后 `ink_h` |
|---|---|---|
| `H` | 2048 | 1493 |
| `space` | 2048 | **0** |
| `0` | 2048 | 1549（墨迹底 −29） |

`0` 的 −29 是真实的：DejaVu Sans 的零确实下沉 29/2048 em 做视觉对齐。修正后的数值经得起核对，修正前只是把一切都抹成 em 高。

对 `MeasureCanvas` 的效果：`H` 的墨迹盒从 `[-14.1094, 4.7188]` 变成 `[-11.2812, 2.8281]`——这才是真实的 ink 盒。

**但空格仍然报墨迹**，而根因已经查到底：`font_shaping.cpp` 用 `InkBox ink{0, -ascent, 0, descent}` 起手，这个框本身就有高度，随后 `ink.right = max(ink.right, advance)` 又把它撑到整个推进。算术核对完全吻合（ascent 900、descent 240、推进 1440 app units）。这一段**这一轮没改**：它与 Windows 共享，而 r99 的基准数字又出自同一份代码，改它会同时移动生产行为和参照值——那是应当单独决定的事。

回执 `deliverables/linux-ruyijs-glyphmetrics-r179/glyph-metrics-validation.json`。

`MeasureCanvas` 现在**十项全过**（`failures: 0`）。这个结果不是靠调整预期得来的——是修掉三个真缺陷之后自然成立的。

**缺陷一：tag 被交换了两次（最关键）。** `TryGetFontTable` 的调用方传入的是 DirectWrite tag，也就是四字符 tag 的字节反转读法：HarfBuzz 要 `'cmap'`，共享的 `ReadTable` 先做一次 `_byteswap_ulong` 再交下来。我却又按数值高位重建了一遍，等于换回原样再翻转，于是每次查表实际问的是 `'pamc'`。后果是**所有表都取不到**，`ShapeFont` 对任何字符都返回 glyph 0——`H` 和空格都必须用 `.notdef` 的度量。

这一点是靠直接调用 `ShapeFont` 打印 run 才看见的：修之前 `glyph ids: 0`，修之后 `43`（H）与 `3`（space）。

**缺陷二：`Select` 每次调用都新建 face。** Canvas owner 用**指针比较**来切分 run，指针永不相等就意味着每个字符各自成一个 run。改为在 collection 内按文件与索引缓存。

**缺陷三：缓存交给 `ComPtr` 时用了 `Attach`。** `Attach` 把裸指针交给一个新的 `shared_ptr`，于是同一对象有两个主人，探针直接以 SIGABRT 退出。新增 `Share` 复制所有权。

修复后的实测值经得起对账：

| 项 | 值 | 对账 |
|---|---|---|
| `width16` | 12.0333 | 与 HarfBuzz 设计推进 12.0312 一致 |
| `width32` | 24.0667 | 正好翻倍 |
| `ShapeFont("H")` | 722 app / glyph 43 | 正确字形 |
| `ShapeFont(" ")` | 305 app / glyph 3 / **ink 为空** | 空格无墨迹 |

同时纠正了前两轮的判断：把空格报墨迹说成「共享代码既有行为」是错的，根因在本移植的度量与 tag 处理。`font_shaping` 的 run ink 初值也改为空——`ProjectInk` 本身会合并字体盒，SVG 结果不受影响，这个等价关系先用算术验证过，再用十项全过的 canvas 结果确认。

回执 `deliverables/linux-ruyijs-measure-pass-r190/measure-pass-validation.json`。

字形掩码（`GlyphMask`）现在也在 Linux 上真正跑通了：**13 项全过**。

实现方式和 `MeasureCanvas` 那条链不同——掩码不需要绕 XPCOM，直接交给 FreeType：把 face 设成设备 em，把 `linear` 矩阵作为轮廓变换传进去，亚像素偏移折进 `FT_Set_Transform`（y 轴翻转），渲染普通灰阶位图，最后用**同一张 Skia mask 表**做校正。这样它的输出语义与 DirectWrite 那条路一致，而实现只依赖 FreeType。

实测 `H` 在 32px 下：

| 项 | 值 |
|---|---|
| glyph | 43 |
| box | `[3, -23, 18×23]` |
| 覆盖像素 | 214 / 414 |
| 最暗值 | 0（纯黑） |

这些数字互相自洽：18 像素宽对应约 0.56 em，23 像素高对应约 0.72 em，起点在笔位右 3px、基线之上 23px——正是一个 `H` 该有的位置。检查项还包括双倍尺寸把宽高都翻倍、亚像素偏移不改变位图尺寸、以及**空格产出空掩码而不是失败**（空格有推进、没有轮廓，空掩码就是正确答案）。

过程中做了一次必要的职责重划：`glyph_style.cpp` 是 DirectWrite 的**渲染模式选择器**，它读渲染参数、比较 `DWRITE_RENDERING_MODE` 常量，Linux 上根本没有这个概念。于是整个单元归为 Windows-only，由 Linux 掩码单元自己回答 `GlyphStyle`、`SystemTextGamma`、`SystemTextContrast`——canvas 要的只有灰阶一种模式。

上一轮那个 `LINK_FAIL` 的真实原因也记下来了：探针的编译单元列表漏了 `glyph_style`，而 `SystemTextGamma` 定义在那里。补上之后才暴露出更根本的问题——那个单元本身不该在 Linux 编译。

回执 `deliverables/linux-ruyijs-glyphmask-r191/glyph-mask-validation.json`。

彩色字形的第一层——**调色板解析**——在 Linux 上通了。`GlyphPalette` 原本走 `IDWriteFontFace2::GetPaletteEntries`，Linux 版直接解析 CPAL 表；`GlyphColorMask` 里 `sampled` 分支用的 `IDWriteFontFace1` head 盒也改成读 SFNT `head` 表（xMin/yMin/xMax/yMax 在 36/38/40/42，y 向上，所以盒顶是 yMax、盒底是 yMin）。

验证用了两款**真实**字体，不是构造数据：

| 字体 | 结果 |
|---|---|
| `TwemojiMozilla.ttf`（带 COLR+CPAL） | 1063 个 entry，首个为 `0x0e000000` |
| `DejaVuSans.ttf`（纯文本） | 无调色板 |

`0x0e000000` 与我用 Python 独立解析同一张 CPAL 表算出的值**完全一致**——这是交叉验证，不是自证。

过程中查出一个真实字体怪癖，值得单记：**TwemojiMozilla 把 entry 数量写在了第一个 color record index 的位置**，于是那个索引指向数组末尾之外一个 entry。按规范应当拒绝，但 Firefox 的 table reader 是容错的、而且能正常渲染这个字体——拒绝它等于丢掉一个浏览器能显示的彩色字体。所以按真实行为容错：仅当从 0 起算记录能放下时才接受（`8 + 1063×4 = 4260 ≤ 4266`）。同时纠正了一处偏移错误：记录数组起点是「6 + 每调色板 2 字节」，不是 12。

这也是为什么先用「malformed」预期跑出 `ok` 反而说明问题——那个 `ok` 掩盖了解析器根本没读到颜色。改成真正验证成功路径后才暴露。

回执 `deliverables/linux-ruyijs-glyphcolour-r195/glyph-palette-validation.json`。

彩色字形的第二层——**COLR 图层路径**——也通了。用真实的 `TwemojiMozilla.ttf` 里第一个 base glyph（`0x0f`，两层）：

| 项 | 值 |
|---|---|
| 图层数 | 2（表中就是 2） |
| 图层盒 | `[0,-28,32×32]`、`[7,-23,16×22]` |
| 图层颜色 | `rgba(225,255,0,170)` |

颜色与独立 Python 解析的 palette entry 658（`BGRA 0,255,225,170` → `rgba 225,255,0,170`）**逐字节一致**。纯文本字体则干净地报告“无图层”，而不是空成功。

## 两个探针自身的错误，都被数据纠正了

**一是传了空变换。** 探针给 `GlyphColorMask` 传 `linear = nullptr`，而 `sampled=false` 路径会解引用它，于是 SIGSEGV。真实调用方永远会传矩阵，是探针错了。

**二是断言写反了。** 我断言“两层颜色应当不同”，实测两层都是 `225,255,0,170`。查真实表才发现：**两层确实共用 palette index 658**，所以相同颜色才是正确答案。断言改成检查“是否为表中命名的那个 entry”，而不是“是否互不相同”。

这两处都说明同一件事：**断言要跟着数据走，不能跟着直觉走**。如果第一次就把“颜色不同”当成 bug 去改代码，会把正确的实现改坏。

顺带解除最后一处平台耦合：`glyph_color.cpp` 在非 Windows 下不再包含 `dwrite_2.h`——COLR 表读取和 head 盒都不需要它。

回执 `deliverables/linux-ruyijs-colr-r195/colr-validation.json`。

## Seed 关系（重要）

`ruyijs-inner` 的 seed 是 `ff-ruyijs` **0.2.1**（`c69875b5`），不是当前的 0.4.1（`3501a90`）。

**0.2.1 没有跨平台代码**——`python/ruyijs/_pipe.py` 仍是 Windows 独占的 127 行。0.4.1 的 AF_UNIX 分支（208 行）是后出现的能力，只能作可行性证据，不能作内部版现状依据。

## 与其他项目的关系

- 与 **RuyiHttp** 共享 31 个 C 符号的 necko ABI（见 `docs/01-architecture.md` §1.2）
- 与 **RuyiTrace** 构成 trace 对账闭环：`trace_diff.py` 比对两者行为差异
- 与 [ruyi-mcp](../../docs/01-architecture.md#5-ruyi-mcp-控制面与组件边界) 的关系是浏览器行为对照。
