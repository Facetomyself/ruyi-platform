# 06 · RuyiJS 内部版反编译与工程化

对象：内部 wheel `ruyijs 0.2.2+inner.*`。目标：把它的原生壳与 Python 层还原成**自有、可维护、可跨平台编译**的源码树，落在 `Facetomyself/ruyijs-inner`（private）。

---

## 0. 三层边界（先立规矩）

```
cutetailbud/ff-ruyijs      public   只读，看不到就 clone
        ↓ fork
Facetomyself/ff-ruyijs     public   ① 向上游提 PR；② 反编译时的语义对照
        ↓ 仅参考，不作基线
Facetomyself/ruyijs-inner  private  ← 内部版的唯一来源
```

| 规则 | 内容 |
| --- | --- |
| R1 | `ff-ruyijs` 不承载任何内部功能，内部改动一律进 `ruyijs-inner` |
| R2 | `ruyijs-inner` 的代码来自**对内部产物的反编译还原**，不是从 `ff-ruyijs` 复制 |
| R3 | `ff-ruyijs` 只当「公开实现长什么样」的对照物；对照结论必须标注「参照，未采用」或「与二进制一致，采用」 |
| R4 | 内部版有能力回流上游时，走 `ff-ruyijs` → `cutetailbud` 的 PR 单向流出，不回灌 |

**为什么这条边界重要**：内部 wheel 的 `js.exe` 与 `ff-ruyijs` 的 `js` 是**不同构建**（前者 Firefox `9a2dc53c`，后者子模块 `2887d9de`，而 RuyiTrace 内核是 `39bfd14c`）。混用会带来无法定位的行为差异。

---

## 1. 反编译对象分解

内部 wheel 由两大部分组成，难度差一个数量级：

| 部分 | 体积 | 性质 | 反编译难度 |
| --- | --- | --- | --- |
| **Python 层**（`ruyijs/*.py`，19 文件 1605 行） | 60 KB | **明文源码** | 🟢 不需要反编译，直接读 |
| `necko` Python 适配器（`vendor/.../necko/`，13 文件） | 200 KB | 明文源码 | 🟢 不需要 |
| **原生壳** `dist/js.exe` | 49.5 MB | C++ 编译产物，未 strip | 🟡 需反编译 |
| `dist/mozglue.dll` | 250 KB | Gecko glue | 🟡 需反编译 |
| `dist/ruyijs_client.dll` | 35 KB | 客户端库（仅 1011 版） | 🟢 小，快 |
| 内嵌 CPython（`vendor/.../python/`） | ~15 MB | 官方 CPython 3.14 + 预编译包 | 🟢 无需反编译 |
| Necko 原生（`necko_core.dll` 等 6 个） | — | 与 ruyihttp 同源 | 🟢 源码在 `ff-ruyijs/native/` |

> **关键判断**：Python 层是明文，原生壳是真正的反编译对象。所以 ruyijs-inner 的难点集中在 `js.exe`。

---

## 2. 反编译对象：`js.exe`

### 2.1 它是什么

```
js.exe = SpiderMonkey js shell（Firefox 9a2dc53c）
       + ruyijs 的 38 个浏览器子系统（src/ 2069 文件那一批）
       + 命名管道 IPC 服务端
       + 内嵌 Necko 调用
```

它不是普通 `js` 命令行壳。`_context.py` 的注释说明它被当作「the shell」通过管道驱动。

### 2.2 逆向切入点（从 Python 侧反推）

Python 绑定是最好的契约文档——它精确描述了每一个 RPC：

```python
# _context.py
def _request(self, operation, **fields):
    ...
```

`operation` 的取值来自各 Control 类。把它们全部枚举出来，就是 `js.exe` 必须实现的 RPC 全集：

| 来源文件 | 方法 | 对应 operation（待从二进制确认） |
| --- | --- | --- |
| `_context_eval.py` | `eval` / `locals` | `eval` / `locals` |
| `_context.py` | `load_page` / `navigate` / `set` / `expose` / `native` / `checkpoint` / `collect_garbage` | 同名 |
| `_environment.py` | `configure_fingerprint` / `configure_environment` / `get_defaults` | 同名 |
| `_scheduling.py` | `configure_clock` / `clock_status` / `configure_timer_replay` / `pending_timers` / `timer_realm` / `configure_message_replay` / `pending_messages` / `run_message` / `run_timer` / `configure_navigation_replay` / `navigation_replay_status` / `advance` / `drain_timers` / `sleep` / `tick` | 同名 |
| `_resources.py` | `export_cookies` / `cookie_header` / `put_resource` / `get_resource` / `resource_status` / `net_log` / `clear_resources` | 同名 |
| `_inspector.py` | `peek_api_log` / `get_api_log` / `clear_api_log` | 同名 |
| `_input.py` | `dispatch_input` / `click` / `type` / `press` | 同名 |
| `_random.py` | （随机数控制） | 待定 |

**第一步产出**：一张 `operation → 期望行为 → 二进制实现地址` 的表。operation 字符串是现成的锚点。

### 2.3 锚点获取

```bash
# 1. operation 名称串（Python 侧已给全集）
python3 - <<'PY'
import zipfile, re
z = zipfile.ZipFile('/tmp/ruyijs_whl/ruyijs.whl')
names = set()
for n in z.namelist():
    if n.startswith('ruyijs/') and n.endswith('.py'):
        s = z.read(n).decode()
        names |= set(re.findall(r'"(?:operation=)?"([a-z_]+)"', s))
print(sorted(names))
PY

# 2. 在 js.exe 里定位这些字符串的 RVA
python3 scripts/reverse-anchors.py \
  --pe artifacts/binaries/ruyijs/js.exe \
  --strings-from artifacts/analysis/ruyijs/operations.txt \
  -o artifacts/analysis/ruyijs/anchors.json

# 3. 找引用该字符串的指令（RIP 相对寻址），得到分发器
```

### 2.4 分发器定位

RPC 服务端必然有一个 `std::string → handler` 的映射。x64 下典型形态：

```
; 读帧 → 解析 operation 字段 → 比较 → 跳转
lea rcx, [operation]        ; 或 mov rcx, [rbp+...]
lea rdx, [rip+"eval"]
call strcmp / std::string::operator==
```

**目标**：找到那个几十个分支的 `if/else if` 链或跳转表。找到它就找到了全部 handler 入口。

---

## 3. 五步法（复用 `05-reverse-analysis.md`）

方法论与 domtrace 完全相同，这里只写 ruyijs 特有的部分。

### 步骤 1 · 契约提取

| 来源 | 可提取 |
| --- | --- |
| `ruyijs/*.py` 19 文件 | 全部 operation 名、参数结构、返回值类型 |
| `_values.py` / `_public_values.py` | 值编解码：JS ↔ Python 的类型映射表 |
| `_pipe.py` 的帧格式 | 4 字节小端长度前缀 + 16 MiB 上限 |
| `_jsvalue.py` | `JSObject` / `JSFunction` 句柄语义 |
| `build-identity.json`（1011 版） | `source_files_verified: 2038`，`src/` 目录清单 |
| `_runtime/SHA256SUMS`（492ee47 版） | 1579 个文件的完整清单与 hash |

> **清单是金矿**：`SHA256SUMS` 里列出了 `_runtime/vendor/` 的每一个文件，等于给了目录结构；`build-identity.json` 的 `source_inputs` 数组含 2038 个 `src/*.h` 的路径、大小、hash，**等于给了源码树的结构**。

```bash
# 从 build-identity 提取源码树结构
python3 - <<'PY'
import json, zipfile, io
z = zipfile.ZipFile('/tmp/ruyijs-inner-1011.whl')
bi = json.loads(z.read('ruyijs/_runtime/build-identity.json'))
paths = sorted({i['path'] for i in bi['source_inputs']})
print(f'共 {len(paths)} 个源文件')
for p in paths[:40]: print(' ', p)
PY
```

### 步骤 2 · 符号定位

锚点：operation 字符串、错误消息串、日志串。

```bash
strings -a artifacts/binaries/ruyijs/js.exe | grep -iE '^(eval|load_page|navigate|advance|put_resource)$'
```

因为 `js.exe` **未 strip**（49.5 MB 且 `strings` 能取到大量内容），很可能保留了部分符号：

```bash
# 检查是否有导出/调试符号
python3 -c "
import pefile
pe = pefile.PE('artifacts/binaries/ruyijs/js.exe')
print('sections:', [(s.Name.decode().strip(chr(0)), hex(s.Misc_VirtualSize)) for s in pe.sections])
print('export dir:', pe.OPTIONAL_HEADER.DATA_DIRECTORY[0].VirtualAddress)
"
```

### 步骤 3 · 语义重建

产出目标是一份能编出同样行为的 C++：

```
ruyijs-inner/
├── src/                        ← 从 build-identity 的 2038 条路径重建目录骨架
│   ├── application/
│   ├── domain/
│   ├── runtime/
│   ├── browser_environment/
│   ├── web_canvas/
│   ├── web_graphics/
│   ├── resource_network/
│   ├── execution_scheduling/
│   └── ...（共 2069 文件）
├── python/ruyijs/              ← 明文，直接取（但要判定是否需要改）
└── native/                     ← necko C/C++/Rust，从 ff-ruyijs 参照实现
```

**关键**：`build-identity.json` 的 `source_inputs` 给了**每个文件的路径与 sha256**。这意味着：

1. 目录结构已知（2038 条路径）
2. 每个文件的内容 hash 已知 → 反编译出内容后**可以直接验证是否还原正确**

这是反编译里罕见的奢侈品：**有 ground truth hash**。

### 步骤 4 · 交叉验证

| 断言 | 方法 |
| --- | --- |
| Python 侧 19 个 `.py` 的每个 RPC 都有对应实现 | 逐 operation 发一次调用，看是否返回预期结构 |
| 值编解码一致 | 构造边界值（`undefined` / `NaN` / `BigInt` / 循环引用），比对 `_values.py` 的期望 |
| 帧协议一致 | 抓管道字节，验证长度前缀与 JSON 体 |
| 定时器语义一致 | `configure_clock("logical")` + `advance()`，比对确定性 |

```python
# [占位符] 契约断言样本
from ruyijs import Context
with Context() as ctx:
    assert ctx.eval("1+1") == 2
    assert ctx.eval("undefined") is UNDEFINED
    ctx.set("obj", {"a": [1, 2]})
    assert ctx.eval("obj.a[1]") == 2
    ctx.configure_clock("logical", epoch_ms=1700000000000)
    ctx.eval("globalThis.r=0; setTimeout(()=>{r=42},10)")
    ctx.advance(10)
    assert ctx.eval("r") == 42
```

### 步骤 5 · 工程化

| 目标 | 验收 |
| --- | --- |
| Linux 可编译 | `js` 产出，`Context().eval("1+1")` 通过 |
| Windows 可编译 | 产出与内部 wheel 行为一致 |
| Python 层可直接复用 | 19 个 `.py` 与上游 0.4.1 的差异只有已知的 5 个文件 |
| 测试套件 | 至少覆盖 §4 的断言集 |

---

## 4. 优先级（先做什么）

`js.exe` 太大，不可能一次全还原。按「价值 / 成本」排序：

| 优先级 | 范围 | 理由 | 预估 |
| --- | --- | --- | --- |
| **P0** | `eval` / `set` / `expose` / `load_page` / `navigate` | 最小可用闭环，能跑 `Context().eval()` | 小 |
| **P1** | 管道协议 + 帧编解码 + 生命周期 | 没有它跑不起来 | 小 |
| **P2** | `configure_fingerprint` / `configure_environment` | 补环境的核心价值 | 中 |
| **P3** | `configure_clock` / `advance` / `tick` | 确定性重放 | 中 |
| **P4** | `put_resource` / `net_log` / `cookie_header` | 离线回放与网络观测 | 中 |
| **P5** | `dispatch_input` / `click` / `type` | 事件注入 | 大 |
| **P6** | 38 个浏览器子系统的完整性 | 反检测覆盖度 | 很大 |

**P0–P2 做完，ruyijs-inner 就能替代内部 wheel 在 Linux 上的核心用途。**

---

## 5. 与 `ff-ruyijs` 的对照纪律

反编译时`ff-ruyijs` 非常有用（公开实现给了语义参照），但必须守纪律：

### 允许

| 场景 | 做法 |
| --- | --- |
| 不知道某个 operation 该返回什么结构 | 看 `ff-ruyijs/src/` 对应的 C++，形成假设，**再用二进制验证** |
| 不确定某个边界值 | 看公开实现，形成假设，**再用真机行为验证** |

### 禁止

| 场景 | 后果 |
| --- | --- |
| 直接把 `ff-ruyijs` 的 `src/` 拷进 `ruyijs-inner` | 违反 R2，且两版 commit 不同，行为会漂移 |
| 因为「上游这么写」就判定内部版也这么写 | 内部版有 `working_tree_changes: true`，存在已知差异 |
| 把 `ff-ruyijs` 的 Python 层当内部版 Python 层 | 内部版删了 `Engine`、删了 examples、加了 `ruyijs_client.dll` |

### 记录格式

每一条对照结论都写进 `projects/ruyijs/reverse-analysis.md`：

```markdown
| operation | 二进制行为（实测） | ff-ruyijs 参照 | 结论 |
| --- | --- | --- | --- |
| `configure_clock` | 接受 mode/epoch_ms，返回 status 对象 | 签名一致 | 采用 |
| `native` | 构造 native 函数，构造器模式 | 未见 | 内部新增，需自行定义 |
```

---

## 6. 与主线衔接

```
① 契约提取（Python 19 文件 + build-identity）
      ↓
② js.exe 锚点定位（operation 字符串 → 分发器 → handler）
      ↓
③ 语义重建（2038 条路径 + sha256 ground truth 验证）
      ↓
④ 交叉验证（RPC 断言 + 值编解码 + 定时器确定性）
      ↓
⑤ ruyijs-inner 可编译（Linux 优先）
      ↓
   与 ruyihttp 共享 necko ABI          → docs/01-architecture.md §1.2
   与 ruyitrace 的 trace 对账          → docs/01-architecture.md §4
```

---

## 7. 风险

| 风险 | 概率 | 止损 |
| --- | --- | --- |
| `js.exe` 体积导致全量还原不现实 | 高 | **只还原 P0–P2**，其余保持二进制 |
| 无 `js.exe` 的调试符号 | 中 | 靠 operation 字符串 + 行为断言，不靠符号 |
| 反编译出的实现与二进制行为有细微差异 | 高（正常） | 以 §4 断言集为唯一验收 |
| `working_tree_changes: true` 导致基线不确定 | 高 | 反编译对象就是**内部 wheel 本身**，不追 base_commit |
| 上游 `ff-ruyijs` 持续演进，对照物漂移 | 中 | 对照时固定 commit（`3501a90`），写进 `PINS.md` |

---

## 8. 当前进度

| 步骤 | 进度 |
| --- | --- |
| 契约提取 | Python 层与 build-identity 已解析；operation 全集待枚举 |
| 符号定位 | 0/74 |
| 语义重建 | 0% |
| 交叉验证 | 0/40 断言 |
| 工程化 | 未开始 |

**下一步（P0）**：枚举 operation 全集，在 `js.exe` 里定位 `eval` 的分发点。
