# 04 · 已知缺口、矛盾点与待决策项

下文保留分阶段调查及已降级结论。**当前交付缺口**以[其他项目的接入边界](14-source-handoff.md)及[管理面 M0–M3 门禁](../projects/ruyi-mcp/MANAGEMENT-HANDOFF.md)为准，特别要区分已验收的 Trace 浏览器与仍待联验的管理面；JS 产品链接是独立工程。

---

## A 级：会阻断 Linux 适配

### ~~A1 · `_pipe.py` 是 Windows 独占~~ → **已降级为 B 级**

**初版误判**。复查 `ff-ruyijs` 0.4.1 源码后发现：

```bash
cd /var/lib/dsh/Ruyi/RuyiJS/upstream-ff-ruyijs
head -5 python/ruyijs/_pipe.py
# """Bounded local frame transport.
#  Windows keeps the overlapped named pipe. macOS uses a Unix socket with the
#  same 4-byte little-endian length prefix and 16 MiB frame cap."""
grep -c 'AF_UNIX' python/ruyijs/_pipe.py    # ≥1 → 已实现
```

上游 `_pipe.py` **208 行，已含非 Windows 的 AF_UNIX 分支**；`_runtime_paths.py`（59 行）、`_context.py`（495 行）同样已平台化。

**真正的问题改成**：内部 wheel `0.2.2+inner.*` 是上游 0.4.1 之前的快照，没合这些代码。

- **影响**：只需覆盖 4 个 `.py`（约 2 小时），不是重写
- **改法**：见 `03-linux-port.md` L2
- **验证**：`diff -rq RuyiJS/upstream-ff-ruyijs/python/ruyijs RuyiJS/source/_wheel/ruyijs` 只剩 `_runtime`/`examples` 差异

### A2 · `libnecko_core.so` 要求 glibc 2.38

```bash
objdump -T RuyiHttp/repo/native/linux_x86_64/libnecko_core.so \
  | grep -o 'GLIBC_[0-9.]*' | sort -uV | tail -1     # → GLIBC_2.38
ldd --version | head -1                              # 本机 → 2.35
```

本机 `dlopen` 报 `cannot open shared object file`（`DT_NEEDED` 齐但符号版本不满足）。

- **影响**：Ubuntu 22.04 / Debian 12 及更旧系统直接用不了
- **选项**：
  1. 目标机升级到 Ubuntu 24.04+（wheel tag 已是 `manylinux_2_39`）
  2. 降 `--target-glibc` 重编（`docs/build-native.md` 说支持 `RUYIHTTP_GLIBC`）
- **决策**：待定，倾向选项 1

### A3 · ruyijs 内部版原生壳无源码，需反编译

```bash
# 内部 wheel 只有二进制壳
unzip -l '/tmp/ruyijs_whl/ruyijs.whl' | grep '_runtime/dist'
# → dist/js.exe 50,256,896 B / mozglue.dll / CRT
```

Python 层 19 文件是明文，但 `dist/js.exe`（49.5 MB，含 38 个浏览器子系统与管道 IPC 服务端）只有二进制。

- **影响**：`ruyijs-inner` 无法在 Linux 上产出，除非还原出可编译源码
- **减压因素**：`build-identity.json` 给出 2038 个源文件的**路径 + sha256**，是罕见 ground truth
- **方案**：见 `06-ruyijs-inner.md`，P0–P2 优先
- **决策**：反编译先行；P0–P2 完成即可覆盖主要用途

### A4 · RuyiTrace 内核 domtrace 源码缺失

```bash
grep -r 'domtrace' RuyiTrace/app-3.5.0/resources/kernel/ --include='*.py' --include='*.c' -l | head
# → 无输出
find RuyiTrace/app-3.5.0/resources/kernel/moz-src -type d -name domtrace   # → 无输出
```

`kernel/moz-src/` 只有 572 文件 / 12 MB，是被删减的片段，不含 `dom/bindings/domtrace`。`ff-ruyijs` 仓库 grep `domtrace` 也是零命中。

- **影响**：Linux 上复现 domtrace 等于从零实现 74 个开关的插桩
- **选项**：见 `02-source-recovery.md` §4.3 方案 A/B/C
- **决策**：**建议先跑方案 A（10 分钟验证存在性），失败立刻并行 C（问上游）+ B（反推）**

---

## B 级：会拖慢维护

### B1 · `necko` Python 层被 fork 成两份

| 位置 | 版本 | `_transport.py` |
| --- | --- | --- |
| `RuyiHttp/repo/ruyihttp/` | `0.9.0` | 1260 行 |
| ruyijs wheel `vendor/.../necko/` | `0.8.2` | 1337 行 |

`__init__.py` 只有 1 行差异（版本号），`_http3.py` 差 220 行，`_transport.py` 差 362 行。

- **后果**：每个 Linux bug 要修两次，且两边会渐行渐远
- **建议**：合流成一个外部包（例如 `ruyinecko`），两边都当依赖引用
- **验证**：`diff -r RuyiHttp/repo/ruyihttp /tmp/necko_from_ruyijs | wc -l` → 约 1100 行差异

### B2 · 三份 `necko_posix` 源码副本

| 副本 | 来源 |
| --- | --- |
| `ff-ruyijs/native/necko_posix/` | 上游 |
| `RuyiHttp/repo/native/linux_x86_64/` | 二进制，源码未纳入 |
| ruyijs wheel `vendor/necko-derived/` | Python 层，原生库为 dll |

- **建议**：抽成 submodule，三处共享
- **验证**：`git ls-tree -r HEAD native/necko_posix/src/ | wc -l` → 8 个源文件

### B3 · `backports` 依赖写错

```bash
cd RuyiHttp/repo && python3 -c "import ruyihttp"
# → ModuleNotFoundError: No module named 'cryptography.x509.verification'（旧 cryptography）
# → ModuleNotFoundError: No module named 'publicsuffixlist'
# → ModuleNotFoundError: No module named 'backports'
```

`_nss.py:34` 是 `from backports import zstd`（无条件），而 `pyproject.toml` 写 `backports.zstd>=1.0; python_version < '3.14'`。PyPI 包名 `backports.zstd` 的导入名是 `backports.zstd`，`from backports import zstd` 依赖隐式命名空间包行为，Python 3.10 上会失败。

- **改法**：`try: import zstd / except ImportError: from backports import zstd`
- **验证**：干净 venv 里 `pip install -e .` 后 `import ruyihttp` 无异常
- **注意**：上游 ruyijs 的 `vendor/.../necko/_nss.py` 有同样写法，**合流时要一起修**

### ~~B4 · `dist/` 两个 wheel 与 `native/` 脱钩~~ → **已解决**（2026-11-19）

已归档到 `submodules/ruyihttp/dist-v0.9.0-legacy/`，三个平台重新构建并通过
hash 校验（26 个原生文件全匹配）。详见该目录的 `VERIFICATION.md`。

| wheel | 问题 |
| --- | --- |
| `ruyihttp-0.9.0-py3-none-win_amd64.whl` | manifest 是旧结构（`platform` + 扁平 `sha256`），文件在包根 |
| `ruyihttp-0.9.0-py3-none-macosx_26_0_arm64.whl` | dylib 哈希与 `native/darwin_arm64/provenance.json` **全部不符**，**缺 `libnecko_quic.dylib`** |
| linux | **不存在** |

- **建议**：`git mv dist/ dist-v0.9.0-legacy/`，重新构建三平台
- **验证**：新的 linux wheel 里 `unzip -l` 应含 14 个 `.so`

---

## C 级：文档与实现不一致

### C1 · domtrace 开关数量三处不一致

| 来源 | 数量 |
| --- | --- |
| `README-cheatsheet.md` 开头 | 69 |
| `switches.js` 注释 | 67（+1 废弃） |
| `switches.js` 实际数组 | **74** |
| `xul.dll` strings | **74** |

```bash
# 复现
cd RuyiTrace/app-3.5.0/resources
python3 -c "
import re
t=open('../unpacked-asar/src/shared/switches.js',encoding='utf-8').read()
print('switches.js:', len(re.findall(r\"env: '([A-Z0-9_]+)'\", t)))
"
strings -a kernel/xul.dll | grep -oE 'MOZ_DOM_[A-Z0-9_]+' | sort -u | wc -l
```

- **结论**：**74 是正确的**，文档陈旧
- **建议**：以 `switches.js` 做单一真相源，自动生成 cheatsheet，别手写

### C2 · `MOZ_DOM_HTTP_PACKET_TRACE_MAX_PENDING` 是幽灵开关

只在 cheatsheet 出现，`xul.dll` 没有，`switches.js` 注释确认「内核已不再读取」。

```bash
grep -c 'HTTP_PACKET_TRACE_MAX_PENDING' RuyiTrace/app-3.5.0/resources/domtrace/README-cheatsheet.md  # ≥1
strings -a RuyiTrace/app-3.5.0/resources/kernel/xul.dll | grep -c 'HTTP_PACKET_TRACE_MAX_PENDING'   # 0
```

### C3 · ruyijs `SOURCE_NOTICE` 指向 0.3.3，版本号却是 0.2.2+inner

```bash
cat RuyiJS/source/_wheel/ruyijs/_runtime/SOURCE_NOTICE.md   # 已随解包删除，需重新解
# Package: https://pypi.org/project/ruyijs/0.3.3/
# Version: 0.2.2+inner.492ee47
```

两个内部构建：
- `+inner.492ee47`：**无** `build-identity.json`，溯源链断裂
- `+inner.20261101191032`：**有** `base_commit aa255fbb…`、`working_tree_changes: true`、`source_files_verified: 2038`

- **建议**：fork 里补 `PROVENANCE.md`，每个 wheel 必须带 `wheel → ff-ruyijs commit → firefox commit` 三元组

### C4 · `SHA256SUMS` 用 CRLF 分隔

```bash
cd RuyiJS/source/_wheel/ruyijs/_runtime
sha256sum -c SHA256SUMS                    # → 全部 "FAILED open or read"
sed 's/\r$//' SHA256SUMS > /tmp/sums.txt
sha256sum -c /tmp/sums.txt | grep -c ': OK$'   # → 1579
```

**文件本身没问题**，只是行尾 CR 让 `sha256sum` 找不到文件。文档里要写明。

### C5 · `kernel/moz-src/` 不是完整源码

```bash
find RuyiTrace/app-3.5.0/resources/kernel/moz-src -type f | wc -l   # → 572
du -sh RuyiTrace/app-3.5.0/resources/kernel/moz-src                 # → 12M
```
完整 Firefox 源码约 30 万文件 / 3 GB。这是删减片段，**只能参考不能重编**。

---

## D 级：环境与工具

### D1 · 本机 glibc 2.35 无法 live 验证 linux 原生库

见 A2。当前所有 linux 侧结论都是**静态检查**（ELF/ABI/符号/manifest），没有一条是实际发请求。

### D2 · 测试套件 6 项 Windows 假设

```bash
cd RuyiHttp/repo && /tmp/ruyivenv/bin/python -m unittest discover -s tests
# → 13 ok, 4 fail, 2 error
```

失败项：
- `test_windows_host_stays_win_amd64`（断言 `os.name=="nt"`）
- `test_default_core_names_follow_the_platform`（断言消息含 `necko_core.dll`）
- `test_windows_build_copies_native_dlls`
- `test_platform_profiles_and_user_agents`
- `test_quic_names_and_environment_override`（临时目录无 `.so`）
- `test_nss_gate_compares_packaged_version`

**这不是代码 bug，是测试的参数化缺失。** Linux 移植时必须修，否则 CI 永远红。

### D3 · RuyiJS 无测试套件

本地 `ruyijs` 包里没有任何 `tests/`。`ff-ruyijs` 有 13 个 smoke 脚本（`ci/*_check.py`），但那是对 ff-ruyijs 自己的构建，不是对内部 wheel。

- **建议**：Linux 移植后用 `ruyihttp` 的契约测试 + `ci/smoke_test.py` 当外环，内部至少补 `Context.eval` / `load_page` / `net_log` 三个冒烟。

---

### D-MCP · Linux 生产 Trace owner 同会话验收

AMD64 R5 的 Linux CLI [生产门禁](../projects/ruyi-mcp/PRODUCTION-OWNER.md)已通过。Electron owner、ARM64 生产、部署中的跨机器 SSH stdio，以及真实浏览器上的独立租约到期和进程丢失仍为 `To be confirmed`；独立 ARM64 fixture 的回执仍只覆盖其有界范围。

## 待决策清单

| # | 决策项 | 选项 | 建议 | 阻塞什么 |
| --- | --- | --- | --- | --- |
| 1 | 目标 glibc | 24.04+ / 降版本重编 | **24.04+** | A2 全部 |
| 2 | Firefox commit 基线 | `9a2dc53c` / `39bfd14c` / `2887d9de` | **`39bfd14c`**（RuyiTrace 内核） | 阶段 1 全部 |
| 3 | domtrace 源码 | A 官方树 / B 反推 / C 问上游 | **A 先验证 10 分钟，C 并行** | 阶段 4（占 70% 工作量） |
| 4 | `necko` Python 层 | 两份独立 / 合流成一个包 | **合流** | B1，长期维护成本 |
| 5 | `necko_posix` 源码 | 三份副本 / submodule | **submodule** | B2 |
| 6 | ruyijs 内部版路线 | 以上游 0.4.1 为基 / **反编译还原** | **反编译还原**；上游只作对照（`ff-ruyijs` 不得承载内部功能） | A3、B1、B2 |
| 8 | ruyijs 反编译范围 | 全量 / P0–P2 | **P0–P2**（eval/set/expose/load_page/navigate + 管道 + 指纹配置） | A3 |
| 7 | RuyiTrace Linux 形态 | 完整移植 / 只做 CLI 复现 | **先做 CLI**（跳过 Electron，直接照 `firefox-environment.cjs` 拼 env 拉 firefox） | L3 |


---

## 附：本文的更正记录

| 轮次 | 更正内容 |
| --- | --- |
| 初版 | A1 判定「`_pipe.py` 需整文件重写 127 行」 |
| **更正** | 上游 ff-ruyijs 0.4.1 `python/ruyijs/_pipe.py` 已 208 行且含 AF_UNIX 分支；内部 wheel 只是旧快照。降级为「覆盖 4 个文件」。 |
| 初版 | 预估 RuyiJS Linux 适配为「中（重编 js 壳）」 |
| 二次更正 | 曾判定「Python 层覆盖上游 4 个文件即可」。**再更正**：`ff-ruyijs` 是 public fork，只作 PR 目标与反编译对照，**不作内部基线**。内部版 `js.exe` 需反编译还原，见 `06-ruyijs-inner.md`。 |
| **定论** | Python 层改动小（19 文件仅 5 处差异）；**真正成本在 `js.exe` 反编译**（49.5 MB C++）。Linux 适配的成败取决于原生壳能否还原。 |
