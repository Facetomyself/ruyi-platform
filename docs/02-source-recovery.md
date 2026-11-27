# 02 · 源码还原路线

**历史研究路线，下文保留原始候选和命令。** 现行检出见[源码交接](14-source-handoff.md)；公开 RuyiJS 在[独立 fork](../projects/ff-ruyijs/README.md)开发。旧工作区资料和 0.4.1 只读样本不是现行公开开发 pin，也不是私有 RuyiJS 的实现来源。早期「覆盖内部文件」方案已由 [ADR 0002](adr/0002-ruyijs-reverse-not-fork.md) 否决；[ADR 0004](adr/0004-open-ruyijs-gitlink.md) 只改变公开 fork 的挂载。

历史目标：三个项目全部拿到**可重建的源码**，而不是只拿到二进制。

**先说一个决定性的好消息**（本轮新查证）：`necko` C ABI 的**跨平台实现源码是现成的**，就在 `cutetailbud/ff-ruyijs` 里，不是闭源。

---

## 0. 结论速览

| 项目 | 源码可得性 | 关键来源 | 预计工作量 |
| --- | --- | --- | --- |
| **RuyiHttp** | 🟢 **已有 100%** | 本地 `RuyiHttp/repo/` 就是完整源码树 | 0（只需合流维护） |
| **RuyiJS（早期误判）** | ~~内部源码约 95% 已有~~ | 旧 `ff-ruyijs` 0.4.1 样本是公开对照物，不是内部 wheel 对应源码 | ~~覆盖 4 个 py + 重编~~；内部来源及验收按 [ADR 0002](adr/0002-ruyijs-reverse-not-fork.md) |
| **RuyiTrace - Electron 层** | 🟢 **已有 100%** | `app-3.5.0/unpacked-asar/src/` 74 文件 3644 行 | 0 |
| **RuyiTrace - domtrace 内核** | 🔴 **源码不在包内** | 只能去 Firefox 159 源码树找 `dom/bindings/domtrace` | **大（本项目最重）** |

---

## 1. necko ABI：源码在哪（本轮实测确认）

这是三件套的中枢。ABI 有 31 个 C 符号，**两个平台各有独立实现，都在 ff-ruyijs 仓库里**：

| 平台 | 文件 | 行数 | 覆盖 ABI |
| --- | --- | --- | --- |
| **Windows** | `native/necko_tls/necko_tls.c` | **863** | 16 个 `necko_tls_*` |
| **Windows** | `native/necko_tls/necko_exchange.c` | **823** | 9 个 `necko_socket_*` + 7 个 `necko_exchange_*` |
| **Linux** | `native/necko_posix/src/tls.cpp` | 148 | TLS 封装 |
| **Linux** | `native/necko_posix/src/tls_client.cpp` | — | ClientHello profile |
| **Linux** | `native/necko_posix/src/tls_io.cpp` | — | 非阻塞 I/O |
| **Linux** | `native/necko_posix/src/http1.cpp` | 144 | HTTP/1.1 |
| **Linux** | `native/necko_posix/src/socket.cpp` | 125 | socket 层 |
| **Linux** | `native/necko_posix/src/brotli.cpp` | — | Brotli 解码 |
| **QUIC（两平台共用）** | `native/necko_quic/src/lib.rs` | **1007** | 3 个 `necko_quic_*` |

`necko_posix/README.md` 原文：

> The upstream native `necko_core.dll` source was not present in this checkout or the release archive. `src/` is a new Linux implementation of the ABI consumed by the upstream Python adapter. It uses POSIX sockets, NSS 3.131/NSPR 4.40 from the Firefox 159 source tree, and a bounded Brotli decoder.

**三件套的 Linux 原生层，已经有了一个可编译的参考实现。** 这不是要重写，是要接管和验证。

### 1.1 与 ruyihttp 现有 linux 库的关系

`ruyihttp/native/linux_x86_64/libnecko_core.so`（255 KB）是 **`ff-ruyijs` 0.4.1 的产物**，其源码就是上表 `necko_posix/src/*`。导出符号与 `necko_tls.c` 的宏定义一致（`NECKO_EXPORT` → `visibility("default")`）。

**验证**：
```bash
nm -D ruyihttp/native/linux_x86_64/libnecko_core.so | grep ' T necko_' | wc -l   # → 31
```
与 `ff-ruyijs` 两平台 C 文件里 `NECKO_EXPORT` 的函数数一致。

---

## 2. RuyiHttp 源码还原

### 2.1 现状：已经是完整源码树

```
RuyiHttp/repo/                      ← 已克隆，HEAD 6bc7a7d
├── ruyihttp/            13 个 .py，3932 行        ← Python 全部源码
├── native/              3 ready + 2 空位          ← 原生库（二进制 + provenance）
├── tools/               build_native.py / verify_runtime.py
├── tests/               19 个契约测试
├── ci/smoke_local.py
├── docs/                build-native / licensing / platform-support
├── setup.py             312 行，负责按平台装配 wheel
└── dist/                2 个旧 wheel（已与 native/ 脱钩）
```

### 2.2 缺的是什么

| 缺口 | 说明 | 补法 |
| --- | --- | --- |
| **原生库的 C/Rust 源码不在树内** | `docs/licensing.md` 明写「it does not contain the full ff-ruyijs native source」 | 从 `ff-ruyijs` 接管 `native/necko_posix/` + `native/necko_quic/` |
| `dist/` 两个旧 wheel 脱钩 | manifest 是旧结构，mac 包缺 quic | 重新构建，或归档到 `dist-v0.9.0-legacy/` |
| `darwin_x86_64` / `linux_aarch64` | `build-required`，无二进制 | 各自平台编，或交叉编译 |
| 测试有 Windows 硬编码 | 4 fail + 2 error 全是 `os.name=="nt"` 断言 | 参数化平台假设 |
| 依赖声明有坑 | `_nss.py` 无条件 `from backports import zstd`，pyproject 却带 `python_version < '3.14'` 条件 | 改导入写法或补命名空间包 |

### 2.3 还原动作（按顺序）

```bash
# 1. 把 ff-ruyijs 的 native 源码纳进来（当作 vendor，不改）
cd /var/lib/dsh/Ruyi/RuyiHttp/repo
git remote add ffruyijs https://github.com/cutetailbud/ff-ruyijs
git fetch --depth 1 ffruyijs
git read-tree --prefix=native/ffruyijs-src/ -u ffruyijs/main:native

# 2. 归档旧 wheel
mkdir -p dist-v0.9.0-legacy
git mv dist/*.whl dist-v0.9.0-legacy/ 2>/dev/null || mv dist/*.whl dist-v0.9.0-legacy/

# 3. 修依赖声明
#    编辑 ruyihttp/_nss.py，把 `from backports import zstd` 改为：
#    try: import zstd
#    except ImportError: from backports import zstd

# 4. 参数化测试（把 os.name=="nt" 断言改成按 runtime_platform() 取值）
```

---

## 3. RuyiJS 源码还原

本节的公开源码与内部 wheel 是不同样本；构建链及命令仅复述早期研究记录。实际构建公开 RuyiJS 查 [fork 自己的构建入口](../projects/ff-ruyijs/README.md)。

### 3.1 已有

| 层 | 状态 | 位置 |
| --- | --- | --- |
| Python 绑定 1605 行 | ✅ | `492ee47` wheel 内（本次抽出 `RuyiJS/source/ruyijs-0.2.2-src.zip`，含 `_engine.py`） |
| Python 绑定（不带 Engine） | ✅ | `20261101191032` wheel 内（1301 条目，含 `build-identity.json`） |
| `necko` Python 适配器 13 文件 | ✅ | 两版 wheel 的 `vendor/necko-derived/python/Lib/site-packages/necko/` |
| necko native 源码（C/C++/Rust） | ✅ | `ff-ruyijs` `native/` |
| **js 壳源码（`src/` 2069 文件）** | ✅ | `ff-ruyijs` 仓库 `src/` |
| Firefox 引擎源码 | ✅ | `ff-ruyijs` 的 `firefox` 子模块（`mozilla-firefox/firefox`，shallow） |
| **构建链** | ✅ | `ff-ruyijs` `ci/firefox/build.sh` + `ci/linux/build.sh` + `tools/build_necko_linux.py` |
| **跨平台 Python 层** | ✅ | 上游 `python/ruyijs/` 已支持 macOS arm64 + Linux x86_64（内部 wheel 落后） |

### 3.2 已确认的构建链（ff-ruyijs，Linux 侧）

```bash
ci/linux/build.sh deps    # apt 包、clang 21（apt.llvm.org）、cbindgen
ci/linux/build.sh donor   # SpiderMonkey standalone objdir → obj/js-linux
ci/linux/build.sh shell   # dist/js, dist/libruyijs_client.so  (tools/build_linux.py)
ci/linux/build.sh necko   # NSS/NSPR, libnecko_core, Neqo 和 helper
ci/linux/build.sh wheel   # manylinux wheel → wheelhouse/
ci/linux/build.sh test    # 13 个 smoke check
```

Windows 侧对应 `ci/firefox/build.sh js|browser|toolchain` + `ci/package/`。

### 3.3 缺的是什么

| 缺口 | 影响 | 补法 |
| --- | --- | --- |
| **内部 wheel 与公开 0.4.1 样本不同** | 旧内部 Win64 wheel 缺跨平台代码 | ~~覆盖 4 个 `.py`~~ 已否决；以[内部来源规则](06-ruyijs-inner.md#0-三层边界先立规矩)为准 |
| `+inner.492ee47` **没有 `build-identity.json`** | 无法追溯到 ff-ruyijs 的哪个 commit | 用 `20261101191032` 的 `base_commit aa255fbb…` 反推；或从 ff-ruyijs 重新构建 |
| `SOURCE_NOTICE.md` 写 `0.3.3`，版本号是 `0.2.2+inner` | 溯源链断裂 | 在 fork 里补一张 `PROVENANCE.md`：`wheel → ff-ruyijs commit → firefox commit` |
| `492ee47` 的 `_runtime/SHA256SUMS` 是 CRLF | 直接 `sha256sum -c` 全 FAILED | 已在文档记录：先 `sed 's/\r$//'` |
| `examples/` 在 `20261101191032` 被移除 | 26 个站点用例丢失 | 从 `492ee47` 版取回（本地已有） |

### 3.4 还原动作

```bash
# 1. 取 ff-ruyijs 源码（已有 /tmp/ffruyijs_probe，可移进工作区）
mv /tmp/ffruyijs_probe /var/lib/dsh/Ruyi/RuyiJS/upstream-ff-ruyijs
cd /var/lib/dsh/Ruyi/RuyiJS/upstream-ff-ruyijs
git sparse-checkout init --cone
git sparse-checkout set src python tools ci native   # 不拉 firefox 子模块（太大）

# 2. 对齐 commit：20261101191032 的 build-identity 记 base_commit = aa255fbb3dd5e806f0cac9119ec9c598fd10bdb3
git fetch origin aa255fbb3dd5e806f0cac9119ec9c598fd10bdb3
git checkout aa255fbb3dd5e806f0cac9119ec9c598fd10bdb3

# 3. 把两个内部 wheel 的 Python 层解出来做 diff
mkdir -p /var/lib/dsh/Ruyi/RuyiJS/source/{inner-492ee47,inner-1011}
python3 -c "import zipfile;zipfile.ZipFile('/tmp/ruyijs_whl/ruyijs.whl').extractall('/var/lib/dsh/Ruyi/RuyiJS/source/inner-492ee47')"
python3 -c "import zipfile;zipfile.ZipFile('/tmp/ruyijs-inner-1011.whl').extractall('/var/lib/dsh/Ruyi/RuyiJS/source/inner-1011')"
diff -r source/inner-492ee47/ruyijs source/inner-1011/ruyijs --exclude=_runtime | head -50
```

---

## 4. RuyiTrace 源码还原

分成两块，难度天差地别。

### 4.1 Electron 层：已完整（0 成本）

`app-3.5.0/unpacked-asar/` 里 74 个文件全是**未混淆源码**：

| 文件 | 行数 | 内容 |
| --- | --- | --- |
| `src/main/codex-ipc.js` | 913 | AI 对话页 IPC |
| `src/main/main.js` | 605 | Electron 主进程 + Firefox 启停 |
| `src/main/codex-config-file.js` | 276 | Codex 配置 |
| `src/agent/worker.mjs` | 244 | Agent worker |
| `src/main/fingerprint-file.js` | 240 | 指纹文件注入 |
| `src/main/socks5-proxy.js` | 231 | SOCKS5 |
| `src/shared/switches.js` | 175 | **74 个开关的单一真相源** |
| `src/main/codex-app-server.js` | 160 | Codex app-server 封装 |
| `src/shared/api-override-controls.js` | 110 | API 定制 |
| `src/shared/switch-config.mjs` | 104 | 开关配置 |
| 其余 60+ 个 | — | Vue 视图、composables、shared |

`dist/renderer/` 是 Vite 构建产物（已编译），但 `src/renderer/` 下 `.vue` 源码齐全，可重建。

### 4.2 domtrace 内核：源码不在包内（最大工作量）

**已确认**：
- `app.asar` 与 `kernel/` 中**没有** `dom/bindings/domtrace` 源码
- `kernel/moz-src/` 只有 572 文件 / 12 MB，是被删减的片段
- `ff-ruyijs` 仓库里 **grep `domtrace` 零命中**——这套插桩不是 ff-ruyijs 的

**唯一来源**：Firefox 159 源码树的 `dom/bindings/domtrace` 目录。RuyiTrace 的 `application.ini` 给了精确 pin：

```
Version=159.0
BuildID=20261101193257
SourceRepository=https://github.com/mozilla-firefox/firefox
SourceStamp=39bfd14cb45c
```

### 4.3 还原动作（按投入排序）

**历史方案 A（已排除）：试图在官方源码树找私有 domtrace。** 下面仅记录当时的试探命令，不用于平台或公开 RuyiJS 的检出。

```text
cd /tmp && git clone --depth 1 --filter=blob:none --sparse \
  https://github.com/mozilla-firefox/firefox ff159
cd ff159 && git sparse-checkout set dom/bindings
git checkout 39bfd14cb45c 2>/dev/null || echo "commit 需完整 fetch"
ls dom/bindings/ | grep -i trace
```

**方案 B：从 `xul.dll` 反推插桩点（可行但慢）**

已知 74 个开关名在 `xul.dll` strings 里。用这些字符串做锚点：

```bash
# 1. 导出所有 MOZ_DOM_ 字符串及其 RVA
strings -a -t x kernel/xul.dll | grep 'MOZ_DOM_' > /tmp/env_anchors.txt

# 2. 需要在 Windows 上跑（PE 解析），Linux 侧用 objdump 或 pefile
python3 -c "
import pefile
pe=pefile.PE('kernel/xul.dll')
for s in pe.sections: print(s.Name, hex(s.VirtualAddress), hex(s.Misc_VirtualSize))
"
```

**方案 C：直接问上游要 domtrace 源码**（`cutetailbud/ff-ruyijs` issue 或微信「如意」）。RuyiTrace 的 README 已写明 FF 159 内核「已按当前 domtrace 源码增量编译」，说明源码在作者手里。

### 4.4 三个方案的判断

| 方案 | 可行性 | 工作量 | 风险 |
| --- | --- | --- | --- |
| A 官方树 | 未知（domtrace 可能是私有 patch） | 低 | 若无此目录则失败 |
| B 反推 | 确定可行 | **极高**（74 个开关 × 每个 1-3 个插桩点） | 语义无法保证 |
| C 问上游 | 确定可行 | 低 | 需对方配合 |

**历史建议（已退役）**：~~先跑 A，再并行 B/C~~。现行 Trace 构建使用独立固定的官方 Firefox 基线加还原插桩，见[构建交接](14-source-handoff.md#真正重建时还需要什么)。

---

## 5. 源码还原完成后的目标形态

```
/var/lib/dsh/Ruyi/
├── RuyiJS/
│   ├── upstream-ff-ruyijs/     ← ✅ 已克隆，47 MB，源码齐全
│   ├── source/_wheel/          ← ✅ 492ee47 全解包（118 MB，含 _runtime）
│   └── source/ruyijs-0.2.2-src.zip ← 纯源码子集 1.2 MB
├── RuyiHttp/
│   └── repo/                   ← ✅ 完整源码，原生 C 源码待接 ff-ruyijs
└── RuyiTrace/
    └── app-3.5.0/              ← ✅ Electron 层源码齐全（unpacked-asar/）
                                ← ❌ domtrace 内核源码待补（方案 A/B/C）
```

三个 `native/necko_posix/` 副本（ff-ruyijs、RuyiHttp、RuyiJS）应当**收敛成一个 git submodule**，否则 Linux 适配时三个地方各修一次。
