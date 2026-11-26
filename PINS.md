# PINS — 外部依赖固定版本

本仓所有文档与脚本引用的版本，只认这张表。任何表外的版本号视为未验证。

**校验方式**：`./scripts/verify-pins.sh`

---

## 1. Firefox 内核

| 用途 | commit | BuildID | 出处 |
| --- | --- | --- | --- |
| **基线（本仓唯一）** | `39bfd14cb45c` | `20261101193257` | RuyiTrace 3.5.0 `kernel/application.ini` |
| ruyijs 内部 wheel 构建 | `9a2dc53c369c7ae5172018b35988e1d2ffeff402` | — | `_runtime/SOURCE_NOTICE.md` |
| ff-ruyijs 上游子模块 | `2887d9de1f69c0e9776413da80e7ba0d1225dd9b` | — | `Facetomyself/ff-ruyijs` `.gitmodules` |

**决策已更正（2026-11-19 实地核查）**：

| 用途 | commit | 官方可获取 |
| --- | --- | --- |
| **源码分析基线** | `9a2dc53c369c…` = `FIREFOX_159_0_RELEASE` | ✅ |
| 复现 RuyiTrace 内核 | `39bfd14cb45c` | ❌ **官方不存在** |
| 跟 ff-ruyijs | `2887d9de1f69…`（release 分支 2026-11-04） | ✅ |

原决策「以 `39bfd14c` 为唯一基线」的依据是「domtrace 只在这棵树上验证过」。
核查后这个依据不成立：该 commit 在 `mozilla-firefox/firefox` 里拉不到，
官方 `dom/bindings/` 里 grep `domtrace` 零命中——**domtrace 是私有 fork 的修改，不是官方功能**。

详见 [`docs/08-firefox-commit-provenance.md`](docs/08-firefox-commit-provenance.md)。

`ff-ruyijs` 的 `firefox` 子模块仍应 pin 到官方可验证的 commit，
不要 pin 到 `39bfd14c`（那会让 clone 失败）。

```bash
# 改 pin（在 ff-ruyijs 工作副本里）
cd upstream/ff-ruyijs
cd firefox && git fetch origin 39bfd14cb45c && git checkout 39bfd14cb45c && cd ..
git add firefox
git commit -m "chore: pin firefox to 39bfd14cb45c (RuyiTrace kernel build)"
```

---

## 2. NSS / NSPR / Neqo

| 平台 | NSS | NSPR | Neqo | 出处 |
| --- | --- | --- | --- | --- |
| `win_amd64` | 3.131 | 4.40 | 0.32.0 | 原 PyPI ruyihttp 0.9.0 的 6 个 DLL；保留 JSON 正文 ABI |
| `darwin_arm64` | 3.132 | 4.40 | 0.33.0 | 原生 Apple Silicon 源码构建，正文 ABI v1，minOS 26.0 |
| `linux_x86_64` | 3.132 | 4.40 | 0.33.0 | 原生 amd64 源码构建，正文 ABI v1，glibc 2.39 |
| `darwin_x86_64` | 3.132 | 4.40 | 0.33.0 | 原生 Intel Mac 源码构建，正文 ABI v1，minOS 15.0 |
| `linux_aarch64` | 3.132 | 4.40 | 0.33.0 | 原生 ARM64 源码构建，正文 ABI v1，glibc 2.39 |

**0.9.1 更新（2026-11-26）**：上表替代早期 donor wheel 与空槽位状态；原始 0.9.0 验收保留在项目历史。四个 POSIX 目标固定 ff-ruyijs `f557fcd437aae5f18f313eb330bd3ef50f5fc7df`，Firefox 源码 `2887d9de1f69c0e9776413da80e7ba0d1225dd9b`。Windows 的原始二进制来源以其固定 wheel SHA 为准，未推定对应的 Firefox Git 提交。原生文件和补丁哈希在所锁定子模块的 `native/<platform>/provenance.json`；交付包哈希与目标机作业见 [0.9.1 发布回执](artifacts/receipts/ruyihttp-0.9.1/qualification.json)。

```bash
cd submodules/ruyihttp
python3 tools/build_native.py --check
```

**硬规则**：core 与 QUIC 必须整组同版本，禁止 3.131 与 3.132 混搭。

---

## 3. ff-ruyijs（**只读参考 + PR 目标，非内部基线**）

| 项 | 值 |
| --- | --- |
| 开源上游 | `cutetailbud/ff-ruyijs`（public） |
| 我们的 fork | `Facetomyself/ff-ruyijs`（public） |
| 用途 ① | 向 `cutetailbud` 提 PR（能力单向流出） |
| 用途 ② | 反编译内部版时的**语义对照物** |
| 用途 ③ | necko 原生源码的公开参照（C/C++/Rust 的 ABI 实现） |
| **不作什么** | ❌ 不是 `ruyijs-inner` 的基线；❌ 不承载内部功能；❌ 不挂 submodule |

**硬规则**（详见 `docs/06-ruyijs-inner.md` §0）：
1. 内部改动一律进 `Facetomyself/ruyijs-inner`（private），不进 fork。
2. `ruyijs-inner` 的源码来自对内部产物的反编译还原，不是从 fork 复制。
3. 对照物必须固定 commit，漂移会导致结论失效。

### 本仓追踪的上游 commit

| 日期 | fork commit | 说明 |
| --- | --- | --- |
| 2026-11-19 | `3501a90` | `fix(editing): Selection state, contenteditable typing, IndexedDB upgrade writes (#44)` |

复查：

```bash
cd upstream/ff-ruyijs      # 本地只读克隆（gitignore，不入本仓历史）
git log --oneline -1
git ls-tree HEAD firefox   # 子模块 pin = 2887d9de1f69c0e9776413da80e7ba0d1225dd9b
```

> 注意：fork 的 firefox pin（`2887d9de`）与本仓基线（`39bfd14c`）不同。这进一步说明 fork 不能当内部基线。

---

## 3.1 ruyijs-inner（**内部版唯一来源**）

| 项 | 值 |
| --- | --- |
| 仓库 | `Facetomyself/ruyijs-inner`（private，**已存在**） |
| 创建 | 2026-11-04 |
| 大小 | 7,416 KB |
| 默认分支 | `main` |
| 挂载 | `submodules/ruyijs` |
| 描述 | `Private inner ruyiJS 0.2.2 tool tree` |
| 状态 | 语义重建进行中，见 `projects/ruyijs/reverse-analysis.md` |

### 还原进度（不动点）

| 分类 | 数量 |
| --- | ---: |
| identity 总数 | 2038 |
| eol-insensitive 对齐 0.2.1 | 1792 |
| hash_diff | 237（其中 56 identity 命中） |
| inner_only | 9（全部语义化，0 identity 命中） |

### Seed 关系

| 项 | 值 |
| --- | --- |
| seed 仓库 | `ff-ruyijs` |
| seed commit | `c69875b5b5c34ba95953c4f382bab6a74d55cfb4` |
| seed 版本 | **0.2.1** |
| 当前 fork HEAD | `3501a90`（0.4.1） |

> **注意**：seed 是 0.2.1，没有跨平台代码。0.4.1 的 `_pipe.py`（208 行含 AF_UNIX）是**后出现的能力**，不能反推 0.2.1 也有。见 ADR 0002。

### 分析笔记位置（该仓外部）

- `workspace/ruyijs-innner/agent-notes/`（在原开发机）
- 本仓只保留结论，不复制笔记

---

## 4. RuyiJS 内部构建

### 4.1 两个已知构建

| 版本 | sha256 | 大小 | 出处 | 关键差异 |
| --- | --- | --- | --- | --- |
| `0.2.2+inner.492ee47` | 见下 | 46,030,962 B | 用户交付 wheel | 含 `Engine` / `use_engine` / 26 个 examples |
| `0.2.2+inner.20261101191032` | `e3243d9b0dc078d97036f2f840d658da74f2b8246af7d00b4468698cc8ea8bef` | 46,616,022 B | RuyiTrace `resources/ruyijs/release.json` | 无 `Engine`，含 `ruyijs_client.dll` |

`492ee47` 的 sha256：`a7be9c4aa04823b32277562ec65082a4ae3844beb7ccf330a53271d8ec82a50e`（46,030,962 B，见附件元数据）

### 4.2 `20261101191032` 的构建身份

```json
{
  "version": "0.2.2+inner.20261101191032",
  "branch": "inner",
  "base_commit": "aa255fbb3dd5e806f0cac9119ec9c598fd10bdb3",
  "working_tree_changes": true,
  "runtime_sha256": "5fb68b2206d463d1a81c95b595374dde766efec37408142bf53b8e58f213bcca",
  "source_files_verified": 2038
}
```

> `working_tree_changes: true` 意味着构建时工作树不干净，**`base_commit` 不足以复现**。这是待解决问题（见 `docs/04-risks-and-gaps.md` C3）。

### 4.3 内部 wheel 与上游 0.4.1 的差异（只有 5 个 .py）

| 文件 | 内部 | 上游 0.4.1 |
| --- | --- | --- |
| `_pipe.py` | 127 行（Windows 独占） | 208 行（含 AF_UNIX） |
| `_runtime_paths.py` | 38 行 | 59 行 |
| `_context.py` | 418 行 | 495 行 |
| `_engine.py` | 214 行 | 215 行 |
| `_version.py` | `0.2.2+inner.*` | `0.4.1` |

其余 14 个 `.py` 逐字节一致。

---

## 5. necko ABI

**31 个 C 符号**，两平台各有实现，源码在 ff-ruyijs。

| 层 | 符号 |
| --- | --- |
| socket（9） | `necko_socket_open` / `_open_cancellable` / `_close` / `_read` / `_write` / `_write_some` / `_idle` / `_interrupt` / `_peer` |
| TLS（16） | `necko_tls_open` / `_open_profile` / `_read` / `_write` / `_write_some` / `_close` / `_pending` / `_alpn` / `_cipher` / `_version` / `_resumed` / `_error` / `_set_nonblocking` / `_nss_version` / `_nspr_version` |
| exchange（7） | `necko_exchange_open` / `_headers` / `_write` / `_receive` / `_read` / `_close` / `_reusable` |
| QUIC（3） | `necko_quic_call` / `_set_decoder` / `_version` |

### 源码位置

| 平台 | 文件 | 行数 |
| --- | --- | --- |
| Windows | `native/necko_tls/necko_tls.c` | 863 |
| Windows | `native/necko_tls/necko_exchange.c` | 823 |
| Linux | `native/necko_posix/src/tls.cpp` | 148 |
| Linux | `native/necko_posix/src/http1.cpp` | 144 |
| Linux | `native/necko_posix/src/socket.cpp` | 125 |
| 两平台 | `native/necko_quic/src/lib.rs` | 1007 |

### ABI 底线

```
GLIBC_2.38
GLIBCXX_3.4.31
CXXABI_1.3.9
```

`libnecko_core.so` 的 `RUNPATH = $ORIGIN:$ORIGIN/../../../../../../../lib`。

---

## 6. RuyiTrace 3.5.0

| 项 | 值 |
| --- | --- |
| zip sha256 | `72db039e1842eca59916fb10c4342dcfb344678d04c8ec6f8bb671b57b1f4cf7` |
| zip 大小 | 583,656,604 B |
| 来源 | `https://drop-cn.zhangxuemin.work/share/select?code=3JMR2` |
| 抓取时间 | 2026-11-19 14:11 +08:00 |
| `firefox.exe` sha256 | `9B5B0C5F003257780B4371DC3D7E6C3A5C33FEED9A742D1BB816638ACADB9BF2` |
| `xul.dll` sha256 | `666AAE7E73428E40A82DA789EF1441E713C348989A1F87E799F05A6E7006A0DB` |
| Electron 应用 | `trace-console` 3.5.0，MIT |
| bundle codex | 0.162.1，`x86_64-pc-windows-msvc` |
| domtrace 文档 | 10 文件，哈希与 `domtrace/manifest.json` 一致 |
| 开关数量 | **74**（`switches.js` 与 `xul.dll` strings 一致） |

---

## 6.1 Linux ARM64 R5 CLI2 与 TLS 租约

这条线与上面的 Win64 3.5.0 成品、以及 amd64 R5 回执分别固定。原生发行标签 [`arm64-r5-cli2-lease-v1`](https://github.com/Facetomyself/ruyitrace/releases/tag/arm64-r5-cli2-lease-v1)，源码提交 `f1253a6ddf03dffa178d349231facc61866e686b`。主机 `oracle-reverse-dev`；Firefox 159 BuildID `20261125162841`；原始 Gecko 编译输入 `9a2dc53c369c7ae5172018b35988e1d2ffeff402`。

| 实物 | 固定值 |
|---|---|
| 离线 Docker gzip | 381,640,590 B，SHA-256 `1de33f49c6ceac4cfd1686b42203bddb1255882c67cad80b4b617247c1c267cb` |
| 原生 Firefox XZ | 74,821,272 B，SHA-256 `1ae57564c96eec28453ef20bbdebe3b494b15524efcf99be510dd5d158cbb640` |
| CLI / interactive / edge | 三个精确 config ID、4 / 5 / 6 层，见[离线包读回](artifacts/receipts/trace-arm64-native-lease/release/archive-verified.json) |
| 发行证据 | [33 份实际回执的校验索引](artifacts/receipts/trace-arm64-native-lease/release/confirmation.json)：内核、镜像、空引擎、私有与真实公网桌面、清理；SHA-256 `b93cacc32627838fd7773f7d61d6c14a8f6359ff7b199a0ae61a2ecd61f1176c` |

ARM 编译工具为 Clang/LLD 19.1.1、Rust 1.100.0、cbindgen 0.29.4；CLI 运行时为 Node 22.14.0。请按[产品级操作手册](submodules/ruyitrace/product/arm64/README.md)导入与验证，不要把其他组件的编译器条件当作这一发行的依据。

## 7. 工具链

| 工具 | 版本要求 | 用途 |
| --- | --- | --- |
| Python | ≥ 3.10（necko 构建步骤需 3.14） | 绑定、脚本 |
| clang | 21（apt.llvm.org） | Firefox / necko 构建 |
| Rust / cargo | 最新稳定 | Neqo、necko_quic |
| cbindgen | 最新 | NSS 绑定 |
| Node | ≥ 22.12.0（以 `console/tooling/package.json` 的 engines 为准） | RuyiTrace 控制台构建；Electron 运行时另行固定 |
| glibc | **≥ 2.38** | Linux 原生库运行 |
| pefile / 类似 | — | domtrace 反编译（`scripts/env-anchors.py` 依赖） |

---

## 8. 更新规则

1. 任何 pin 变更必须同时改本文件**和** `STATUS.yaml`。
2. 旧 pin 不删除，移入「历史 pin」小节并注明被谁替代、为什么。
3. pin 变更后跑 `./scripts/verify-pins.sh`，失败不得提交。

## 9. ruyi-mcp

| 组件 | 源码仓 | 维护分支 | 平台固定提交 |
| --- | --- | --- | --- |
| ruyi-mcp | [Facetomyself/ruyi-mcp](https://github.com/Facetomyself/ruyi-mcp) | `linux` | `b5e204a76dc3974abadf1fe355392815ddddd6b7` |

```bash
cd /var/lib/dsh/Ruyi/ruyi-platform
git ls-tree HEAD -- submodules/ruyi-mcp
git config -f .gitmodules --get submodule.submodules/ruyi-mcp.branch
node -p "JSON.stringify(require('./submodules/ruyi-mcp/package.json').engines)"
```

浏览器制品身份独立于该源码 pin，按 [Linux 验收](docs/03-linux-port.md#6-ruyi-mcp-分阶段验收)记录。

### 历史 pin

- `8f3839b6bd3c52688a8a0d7d94d81e6820e8ca0b`：生产 M2 初版借用与停机证据，仍按原提交复核。本版细化租约、错目标与归还契约。

- `2797d3cd494ffeab0f0839109a2243b5b3024964`：`d7DBYN4g` MCP 自启基线，保留回执；后续生产借用版本绑定描述符身份和 RDP 租约回执。

- `d4f93cc81ec9d12e2c1ba7877be7d3eb35427713`：首个原生容器 CI 基线，由真实 Trace 内核验收后的 RDP 修订取代。
- `1c80d8889b47185f4b6f20be4b97cd9db99532f1`：首个 Docker 设计稿。

## 10. 2026-11-24 交接：开发基线与发行源码分开

四个组件的开发 pin 以 `git ls-tree HEAD:submodules` 为准；[状态账本](STATUS.yaml) 的 `submodules.*.commit` 是同一组完整 SHA。Trace 开发 pin 包含已验收的独立 CLI；历史 amd64 R5 仍使用独立的 [源码锁](artifacts/receipts/trace-amd64-r5/source-lock.json) 与原标签。发行、CLI、Win64 离线工具的完整提交与检出方式见[使用指南](docs/14-source-handoff.md)。
