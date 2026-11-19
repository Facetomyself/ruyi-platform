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

**决策**：以 `39bfd14cb45c` 为唯一基线。理由：

- domtrace 插桩只在这棵树上验证过，换 commit 需重编全部内核。
- `9a2dc53c` 是更早的构建，与 RuyiTrace 不一致。
- `2887d9de` 是上游跟随的最新，但含上游自己的改动，不能直接当内部基线。

**后果**：`ff-ruyijs` 的 `firefox` 子模块需要改 pin 到 `39bfd14cb45c`，然后重跑 `ci/linux/build.sh donor/shell/necko`。

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
| `win_amd64` | 3.131 | 4.40 | 0.32.0 | 原 ruyihttp 0.9.0 wheel |
| `darwin_arm64` | 3.132 | 4.40 | 0.33.0 | ruyijs 0.4.1 macOS wheel |
| `linux_x86_64` | 3.132 | 4.40 | 0.33.0 | ruyijs 0.4.1 manylinux wheel |
| `darwin_x86_64` | 3.132（预期） | 4.40 | 0.33.0 | 未构建 |
| `linux_aarch64` | 3.132（预期） | 4.40 | 0.33.0 | 未构建 |

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

## 7. 工具链

| 工具 | 版本要求 | 用途 |
| --- | --- | --- |
| Python | ≥ 3.10（necko 构建步骤需 3.14） | 绑定、脚本 |
| clang | 21（apt.llvm.org） | Firefox / necko 构建 |
| Rust / cargo | 最新稳定 | Neqo、necko_quic |
| cbindgen | 最新 | NSS 绑定 |
| Node | ≥ 20.20 / ≥ 22 | RuyiTrace 控制台 |
| glibc | **≥ 2.38** | Linux 原生库运行 |
| pefile / 类似 | — | domtrace 反编译（`scripts/env-anchors.py` 依赖） |

---

## 8. 更新规则

1. 任何 pin 变更必须同时改本文件**和** `STATUS.yaml`。
2. 旧 pin 不删除，移入「历史 pin」小节并注明被谁替代、为什么。
3. pin 变更后跑 `./scripts/verify-pins.sh`，失败不得提交。
