# 03 · Linux 适配路线

**现行路线先分项目：**公开 RuyiJS 的性能与 macOS/Linux 兼容工作在 [公开 fork](../projects/ff-ruyijs/README.md)开展，向公开上游提 PR；保持 Windows 在共用主干上的既有行为。平台检出只到一级；公开 fork 的 Firefox 仅在需要构建时按其自己的手册取得。私有内部版的来源见[内部版规则](06-ruyijs-inner.md#0-三层边界先立规矩)，交付看[分平台回执](14-source-handoff.md#选择交付物)，公开源码、历史 donor 与固定工件各用自己的 pin。

**历史说明：**开头及 §1–§5 保留早期三件套的样本、方案和依赖。当时的统一 Firefox pin、覆盖内部源码和 glibc 门槛均不是现行要求；[当前交付缺口](04-risks-and-gaps.md#当前交付缺口)给出各制品范围。

历史样本前置：目标机需要 **glibc ≥ 2.38**。本机 2.35，`libnecko_core.so` 直接 `dlopen` 失败（`cannot open shared object file`，`DT_NEEDED` 满足但 `GLIBC_2.38` 符号版本不满足）。这不是代码问题，是跑测试的机器版本不够。

```bash
# 检查
ldd --version | head -1        # 需 ≥ 2.38
objdump -T libnecko_core.so | grep -o 'GLIBC_[0-9.]*' | sort -uV | tail -1   # GLIBC_2.38
```

Ubuntu 24.04 起满足。Ubuntu 22.04（glibc 2.35）上**只能跑静态分析**，无法 live 验证。

---

## 1. 第零步：统一版本基线（历史方案，已退役）

三套 Firefox 提交号不一致，Linux 适配会互相污染：

| 来源 | Firefox commit | 位置 |
| --- | --- | --- |
| ruyijs `js.exe` | `9a2dc53c369c7ae5172018b35988e1d2ffeff402` | `_runtime/SOURCE_NOTICE.md` |
| RuyiTrace 内核 | `39bfd14cb45c` | `kernel/application.ini` → `SourceStamp` |
| ff-ruyijs 子模块 | `2887d9de1f69c0e9776413da80e7ba0d1225dd9b` | `.gitmodules` + `git ls-tree HEAD firefox` |

**早期决定（已更正）**：~~统一到 `39bfd14cb45c`~~。该值标识 Trace 的 Win64 私有内核；各组件现在各自固定构建来源，见 [PINS](../PINS.md)。下列原命令只作历史记录，不是可执行的现行构建步骤。

```text
# 历史方案：在 ff-ruyijs 里改子模块 pin
cd /var/lib/dsh/Ruyi/RuyiJS/upstream-ff-ruyijs
cd firefox && git fetch origin 39bfd14cb45c && git checkout 39bfd14cb45c && cd ..
git add firefox && git commit -m "chore: pin firefox to 39bfd14cb45c (RuyiTrace kernel build)"
```

原方案随后计划重跑 `ci/linux/build.sh donor/shell/necko`，这一串步骤与上面的统一 pin 一起退役。

---

## 2. 分层改造清单

按「隔离度从高到低」排列，每层独立可验证。

### L0 · necko ABI（原生层）—— 已就绪

| 项 | 状态 | 说明 |
| --- | --- | --- |
| `native/necko_posix/src/*` | ✅ 有源码 | 148+144+125 行 C++ |
| `native/necko_quic/src/lib.rs` | ✅ 有源码 | 1007 行 Rust |
| NSS/NSPR 从 FF 159 树编译 | ✅ 有脚本 | `tools/build_necko_linux.py --http3` |
| 依赖闭包完整 | ✅ 14 个 `.so` 无缺 | `$ORIGIN` runpath |
| 运行时 ABI 要求 | ⚠️ glibc 2.38 / GLIBCXX 3.4.31 | 见本文第 0 节 |

**动作**：无。只需在 glibc ≥ 2.38 的机器上跑一次 live 验证。

```bash
# 在 Ubuntu 24.04 上
cd /var/lib/dsh/Ruyi/RuyiHttp/repo
python3 - <<'PY'
import ctypes as ct
lib = ct.CDLL('./native/linux_x86_64/libnecko_core.so')
print('NSS', lib.necko_tls_nss_version())
print('NSPR', lib.necko_tls_nspr_version())
PY
```

### L1 · ruyihttp Python 层 —— 几乎就绪

| 硬点 | 位置 | 改法 |
| --- | --- | --- |
| `_load_library()` 已支持 `.so` | `_transport.py:94-130` | ✅ 已写好，走 `sys.platform != "darwin"` 分支 |
| 平台选择 | `_firefox.py:43-72` `client_platform()` | ✅ 已支持 linux，UA 为 `X11; Linux x86_64` |
| TLS profile | `_tls_profiles.py:158` | ⚠️ 三平台共用同一张表（见 §4） |
| `backports` 依赖 | `_nss.py:34` 无条件 import | ❗ 修 |
| 契约测试 Windows 假设 | `tests/test_runtime.py` 6 处 | ❗ 参数化 |

修依赖：

```python
# ruyihttp/_nss.py 第 34 行附近
try:
    import zstd                      # Python 3.14+ 标准库
except ImportError:
    from backports import zstd       # 3.10–3.13
```

修测试：

```python
# tests/test_runtime.py
# 原: self.assertEqual(os.name, "nt")
# 改:
from ruyihttp._firefox import runtime_platform
self.assertEqual(runtime_platform(), expected_platform_for_this_host)
```

### L2 · ruyijs 内部版 —— **上游有参照，但不能直接抄**

> **补充（2026-11-19）**：ff-ruyijs v0.4.1 已发布
> `ruyijs-0.4.1-py3-none-manylinux_2_39_x86_64.whl`（73.9 MB），内含构建好的
> `dist/js`（66 MB，SpiderMonkey **160**）、`libruyijs_client.so` 与 26 个依赖 `.so`，
> 依赖自洽，`runtime.json` 的 sha256 覆盖 26/26。
>
> 这意味着 **Linux 侧能立刻跑起来，不必自己编 SpiderMonkey**。
> 但它与内部版不是同一套构建（SP160 vs SP159，OpenSSL vs NSS），
> 只能做链路验证，不能当内部版的 Linux 等价物。详见 `07-build-hosts.md`。

> **本条经两次更正。**
>
> 初版：判定「`_pipe.py` 需整文件重写 127 行」——**错**。
> 二版：发现 `ff-ruyijs` 0.4.1 的 `_pipe.py` 已 208 行含 AF_UNIX，判定「直接取上游 4 个文件」——**部分错**。
>
> **对内部版仍有效**：公开实现只作**语义对照**，不作内部基线；内部实现来自内部产物的还原，以二进制行为验收。平台接入公开 fork 不改变这条规则，见 [ADR 0002](adr/0002-ruyijs-reverse-not-fork.md)与 [ADR 0004](adr/0004-open-ruyijs-gitlink.md)。
>
> 上游那 4 个跨平台文件（`_pipe.py` 208 行 / `_runtime_paths.py` 59 行 / `_context.py` 495 行 /
> `_engine.py` 215 行）证明了一件事：**这件事有人做成过，方案可行**。但代码不能直接搬——
> 内部 `js.exe` 基于 Firefox `9a2dc53c`，fork 子模块 pin 是 `2887d9de`，两者行为会漂移。
>
> **实际工作量**：L2 的 Python 层改动小（19 文件里只有 5 个有差异，且 `_pipe.py` 的帧格式有公开参照），
> 真正的成本在 `js.exe` 反编译（见 `06-ruyijs-inner.md` P0–P2）。

内部 wheel 与上游 `python/ruyijs/` 的差异清单（实测 `diff -rq`）：

```
_context.py         ↑ 418 → 495 行
_engine.py          ↑ 214 → 215 行
_pipe.py            ↑ 127 → 208 行   ← 关键：新增 macOS/Linux 分支
_runtime_paths.py   ↑  38 →  59 行   ← 关键：新增平台判据
_version.py         （0.2.2+inner → 0.4.1）
```

其余 14 个 `.py` **逐字节一致**。

#### L2.1 `_pipe.py` —— 上游方案可作参照，代码需自行还原

内部版第 14 行是：

```python
if os.name != "nt":
    raise OSError("ruyijs currently requires Windows")
```

上游 0.4.1 改成了条件导入（同文件、同帧格式）：

```python
"""Bounded local frame transport.

Windows keeps the overlapped named pipe. macOS uses a Unix socket with the
same 4-byte little-endian length prefix and 16 MiB frame cap.
"""

MAX_FRAME = 16 * 1024 * 1024

if os.name == "nt":
    ...  # kernel32 overlapped named pipe
else:
    import socket
    class Pipe:
        def __init__(self):
            root = os.environ.get("TMPDIR") or "/tmp"
            # Basename grammar shared with the shell: ruyijs-<16-64 hex>.sock
            self.name = os.path.join(root, "ruyijs-" + uuid.uuid4().hex + ".sock")
            ...
            self._server.bind(self.name)
            os.chmod(self.name, 0o600)     # ← 权限收紧
            self._server.listen(1)
```

**帧格式两边完全一致**：`4 字节长度前缀 + 16 MiB 上限`。C++ 端在 ff-ruyijs `src/` 里已有对应实现。

#### L2.2 `_runtime_paths.py`（上游给出参考判据）

内部版第 16 行：

```python
if os.name != "nt" or platform.machine().lower() not in ("amd64", "x86_64"):
    raise OSError("ruyijs requires Windows x64")
...
if (root / "dist" / "js.exe").is_file():      # 硬编码 .exe
```

上游 0.4.1 已改成平台函数（`python/ruyijs/_runtime_paths.py`，59 行）：

```python
def macos_arm64():
    return sys.platform == "darwin" and platform.machine().lower() in ("arm64", "aarch64")

def linux_x86_64():
    return sys.platform.startswith("linux") and platform.machine().lower() in ("x86_64", "amd64")

def shell_filename():
    """Basename of the SpiderMonkey shell this host launches."""
    return "js" if macos_arm64() or linux_x86_64() else "js.exe"

def glue_filename():
    """Donor glue library copied beside the shell."""
    return "libmozglue.dylib" if macos_arm64() else "mozglue.dll"

def get_runtime_path():
    if not macos_arm64() and not linux_x86_64() and (
            os.name != "nt" or platform.machine().lower() not in ("amd64", "x86_64")):
        raise OSError("ruyijs requires Windows x64, macOS arm64 or Linux x86_64")
    ...
```

**注意两点**：
1. `linux_x86_64()` **不含 aarch64**——上游不支持 Linux ARM64。要让 aarch64 可用需自行扩这个函数 **并且** 编出 `dist/js`（见 `02-source-recovery.md`）。
2. `glue_filename()` 对 Linux 返回 `mozglue.dll`——这是上游的疏漏，Linux 应为 `libmozglue.so`。**移植时要修这一处**。

#### L2.3 `_context.py`（418 → 495 行，上游给出参考分支）

上游已按平台分支 spawn：

| 项目 | 内部（418 行） | 上游（495 行） |
| --- | --- | --- |
| `creationflags=DETACHED_PROCESS` | 无条件传 | 第 166-169 行 `if os.name == "nt":` 才传 |
| `error.winerror == 109` | 直取 | 第 196 行 `os.name == "nt" and isinstance(...)` 才取 |
| `_prefer_bundled_crt()` | 直接 import `winreg` | 第 104 行在函数内条件导入 |
| darwin 分支 | 无 | 第 132 行 `if sys.platform == "darwin":` |

**旧建议（已否决）**：~~把这 4 个文件从上游覆盖进内部 wheel 的 `ruyijs/`~~。此表仅比较历史实现差异；内部移植以[来源约定](06-ruyijs-inner.md#0-三层边界先立规矩)为准。

#### L2.4 帧格式：Python 与 C++ 必须对齐

上游 `_pipe.py` 的 docstring 已写明契约：

> Windows keeps the overlapped named pipe. macOS uses a Unix socket with the **same 4-byte little-endian length prefix and 16 MiB frame cap**.

即：
- 前缀：**4 字节 little-endian** 长度（不是 big-endian）
- 上限：`MAX_FRAME = 16 * 1024 * 1024`
- socket 路径语法：`ruyijs-<16-64 hex>.sock`（与 C++ 端共享的规则）

以下是历史样本当时的对照命令；现行公开源码入口见[项目说明](../projects/ff-ruyijs/README.md)。C++ 对照代码在样本 `src/runtime/`（156 个文件）：

```bash
cd /var/lib/dsh/Ruyi/RuyiJS/upstream-ff-ruyijs
grep -rn 'ruyijs-.*sock\|\.sock' src/ | head
```

#### L2.5 js 壳（C++）的 IPC 端

上游 `_pipe.py` 的 docstring 已说明 C++ 端也做了平台分支。核对：

```bash
cd /var/lib/dsh/Ruyi/RuyiJS/upstream-ff-ruyijs
grep -rn 'CreateNamedPipe\|AF_UNIX\|\.sock' src/ | head -12
```

**当时的协议兼容目标**是保留 named pipe 与 AF_UNIX 共用的帧格式（4 字节小端长度前缀 + 16 MiB 上限 + JSON 体）。公开样本用于对照；内部编码、回调和句柄行为按内部产物验证。

---

### L2 收敛后的实际工作量

| 层 | 初版判断 | 定论 | 依据 |
| --- | --- | --- | --- |
| `_pipe.py` | 🔴 整文件重写 127 行 | 🟡 按上游帧格式重写，工作量小 | 帧格式公开可参照，逻辑要自己还原 |
| `_runtime_paths.py` | 🟡 改判据 + 改 `.exe` | 🟢 小改，判据可参照 | 逻辑简单，无版本耦合 |
| `_context.py` | 🟡 改 3 处 | 🟢 小改（平台分支） | 同上 |
| `_engine.py` | — | 🟢 差 1 行 | 实测 |
| js 壳 C++ | 🔴 要写 socket 版 IPC | 🔴 **仍需还原** | 二进制里才有真实现 |
| **净工作量** | — | **Python 层小，原生壳大** | — |

**结论**：L2 的 Python 层从「主战场」降为「小改」，但**成本转移到了 `js.exe` 反编译**（`06-ruyijs-inner.md` P0–P2）。
Linux 适配能否完成，取决于原生壳能不能还原出可编译版本，不取决于 Python 层。

### L3 · RuyiTrace Electron 层

| 项 | 状态 | 工作量 |
| --- | --- | --- |
| Electron 本身 | ✅ 跨平台 | 0 |
| `src/main/main.js` spawn 路径 | ⚠️ 硬编码 `kernel/firefox.exe` | 小 |
| `src/shared/firefox-environment.cjs` | ✅ 纯 JS，无平台假设 | 0 |
| `src/shared/switches.js` | ✅ 纯数据 | 0 |
| `src/main/socks5-proxy.js` | ⚠️ 需检查 Windows API | 小 |
| `src/main/fingerprint-file.js` | ⚠️ 可能用注册表 | 中 |
| `src/main/codex-*.js` | ⚠️ codex 二进制是 `x86_64-pc-windows-msvc` | 中（换 Linux 版 codex） |

`main.js:25-34` 的路径逻辑：

```js
// 现在
return path.join(process.resourcesPath || '', 'kernel', 'firefox.exe')
return 'D:\\firefox\\src\\firefox\\obj-release\\dist\\bin\\firefox.exe'   // 开发态

// 改
const EXE = process.platform === 'win32' ? 'firefox.exe' : 'firefox'
```

### L4 · domtrace 内核（最大不确定项）

`xul.dll` 的 74 个 `MOZ_DOM_*` 是编译期插桩，**Linux 要复现必须重编 xul**。

| 前置 | 状态 |
| --- | --- |
| domtrace 源码 | ❌ 不在包内，见 `02-source-recovery.md` §4 |
| Firefox 159 Linux 完整构建链 | ✅ `ci/firefox/build.sh` 支持 linux，但只编到 `browser` 层（Skia + NSS + mozglue），**不编 xul** |
| 完整 xul 构建 | ❌ 需要 `--enable-application=browser` 全量编，约 4-8 小时 / 32 核，磁盘 40+ GB |

**结论**：**L4 是唯一可能做不完的一层**。建议先完成 L0-L3（RuyiHttp 和 RuyiJS 在 Linux 完全可用），L4 单独立项。

---

## 3. 建议的执行顺序（历史，保留）

以下保留初期排期作为记录。其中 [A] 覆盖内部源码及 [D] 合并 Firefox pin 已被上面的更正覆盖，整表不是当前任务清单。

```
阶段 1（半天到 1 天，全并行）
├─ [A] 覆盖上游 python/ruyijs 4 个文件进内部 wheel           （L2，约 2 小时）
├─ [B] 修 _runtime_paths.glue_filename() 的 Linux 分支        （L2.2 已知疏漏）
├─ [C] RuyiHttp：修 backports 依赖 + 参数化 6 个测试           （L1）
└─ [D] 统一 Firefox pin → 39bfd14cb45c（可延到阶段 2 再动）   （§1）

阶段 2（2–3 天）
├─ [E] Ubuntu 24.04 上跑 ci/linux/build.sh donor + shell + necko
├─ [F] ruyijs + ruyihttp 端到端冒烟（§5 的三行输出）
└─ [G] 抓 ClientHello 比对真实 Firefox Linux 的 JA3（R1）

阶段 3（1 周）
├─ [H] darwin_x86_64 / linux_aarch64 补齐原生库
├─ [I] RuyiTrace Electron 层平台化 + 先做 CLI 复现（决策 7）
└─ [J] 三套 necko_posix 合并成单一 submodule

阶段 4（单独立项，占整体 70% 工作量）
└─ [K] domtrace 源码获取 + xul Linux 全量重编
```

**关键判断**：阶段 1–2 做完，RuyiHttp + RuyiJS 在 Linux 就能用了，这个投入产出比最高。阶段 4 的风险与投入都不成比例，应单独立项评估。

---

## 4. 已知风险（Linux 适配时必然踩到）

### R1 · TLS 指纹不保证字节一致

`_tls_profiles.py:158` 三平台共用 `PROFILES` 表，注释自己承认「validated by cipher/group/key-share counts, not by byte-identical ClientHello」。

**后果**：Linux 版 JA3/JA4 与真 Firefox Linux 可能不一致，反爬可能识别。

**验证方法**：
```bash
# 抓 ClientHello 比对
openssl s_client -connect example.com:443 -tls1_3 -msg < /dev/null 2>&1 | head -60
# 或 tcpdump + tshark 提取 JA3
tshark -r cap.pcap -Y 'tls.handshake.type==1' -T fields -e tls.handshake.ja3
```

**RuyiTrace 能直接给答案**：`MOZ_DOM_HTTP_PACKET_TRACE=1` 抓真 Firefox Linux 的报文，与 ruyihttp 的报文逐字段比。

### R2 · HTTP/2 与 HTTP/3 的平台差异未被覆盖

`_http2.py` 做的是 SETTINGS 和 header 顺序，文档说「platform-independent in this tree」。**实际上 Firefox Linux 和 Windows 的 H2 帧行为可能有细微差异**，需要用 RuyiTrace 的 `http_packet` trace 对比。

### R3 · Wine CRT workaround 只该在 nt 分支

`_context.py` 的 `_prefer_bundled_crt()` 是 Wine 专用（写 `HKCU\Software\Wine\AppDefaults\...\DllOverrides`）。上游 0.4.1 已把 `import winreg` 放进函数内条件导入（第 104 行），**非 Windows 不会触发**。

仍需确认：Linux 版 `js` 链接的是 `libstdc++.so.6`（`native/necko_posix` 的 `DT_NEEDED` 里有），**构建机 glibc 版本决定产物下限**——和 A2 同源问题。

### R4 · `ruyijs_client.dll` 只有 Windows 版

`+inner.20261101191032` 的 `dist/` 里有 `ruyijs_client.dll`（35 KB），是给外部集成的客户端库。Linux 侧对应产物是 `dist/libruyijs_client.so`（`ci/linux/build.sh shell` 会产出），当时的内部 Win64 样本没有 Linux 制品。公开 fork 的 Linux 构建只产出公开工件；内部 C ABI 与私有 Linux 制品见[内部交接](14-source-handoff.md#选择交付物)。

### R5 · 测试覆盖缺口

| 项目 | 测试数 | Linux 可用 |
| --- | --- | --- |
| RuyiHttp | 19 契约 + 1 smoke | 6 项必挂（Windows 断言） |
| RuyiJS（内部 wheel） | 无 tests/ | — |
| RuyiJS（上游 ff-ruyijs） | `ci/*_check.py` 13 个 + `tests/` | 需重编后跑 |
| RuyiTrace | 201 项（README 自述） | 源码不在，无法跑 |

**当时的内部 wheel 没有自带测试套件。** `ff-ruyijs` 样本的 `ci/smoke_test.py`、`atob_check.py`、`fetch_abort_check.py`、`load_timer_check.py`、`network_smoke.py`、`socks_proxy_check.py`、`engine_check.py` 等 13 个检查针对公开样本，不能替代私有制品的单独验收。

---

## 5. 端到端验证脚本（历史阶段 2 的出口标准）

```python
"""[占位符] verify_linux.py —— 三件套 Linux 冒烟"""

import os, sys

# L1: ruyihttp 直接发请求
import ruyihttp
with ruyihttp.Session(firefox="159") as s:
    r = s.get("https://example.com/", timeout=20)
    assert r.status_code == 200, r.status_code
    assert r.tls["alpn"] == "h2", r.tls
    print("[L1] ruyihttp OK:", r.status_code, r.tls["nss"])

# L2: ruyijs Context
from ruyijs import Context
with Context() as ctx:
    assert ctx.eval("1+1") == 2
    ua = ctx.eval("navigator.userAgent")
    assert "Linux" in ua, ua
    print("[L2] ruyijs OK:", ua)

# L2 桥接：Context 里的 fetch 走同一套 necko
with Context() as ctx:
    ctx.load_page("https://example.com/", "")
    ctx.eval("globalThis.r=null; fetch('/').then(x=>r=x.status)")
    ctx.advance(5000)
    print("[L2+] in-page fetch:", ctx.eval("r"))

# L3: RuyiTrace（阶段 3 才有意义）
# L4: domtrace（阶段 4）
```

**出口标准**：`[L1]`、`[L2]`、`[L2+]` 三行都打印出来，且 `r.tls["nss"]` 是 manifest 里声明的版本。

## 6. ruyi-mcp 分阶段验收

1. [项目验证](../projects/ruyi-mcp/README.md)：先跑 Linux 控制面；Docker `core` 的构建、stdio 与进程回收另跑容器门禁。
2. [原生 Linux Firefox 验收](../submodules/ruyi-mcp/docs/linux-port.md#原生浏览器验收)：在相同 CPU 架构测试 BiDi、下载与 RDP。普通 Firefox 的结果只适用于该内核与制品身份；`browser` 镜像按架构分别认证。
3. [Trace 共会话](../submodules/ruyi-mcp/docs/docker-design.md#4-trace-与共享服务是后续两条独立演进路径)：结合平台的 Trace 内核与 owner 进度，单独验收租约、暂停/恢复、detach、flush 与 DOMTrace。组件 pin 和控制面通过均与这一门禁独立。
