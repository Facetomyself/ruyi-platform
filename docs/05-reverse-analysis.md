# 05 · 反编译分析方法论（domtrace 内核还原）

目标：把 `kernel/xul.dll` 里那套 domtrace 插桩**还原成可维护的源码**，并能在 Linux 上重编。

这不是「猜代码」，是**从产物反推契约，再用契约重建实现**。

---

## 0. 为什么必须做这件事

| 事实 | 后果 |
| --- | --- |
| domtrace 源码不在发布包内 | 无法直接重编 |
| `kernel/moz-src/` 只有 572 文件 / 12 MB 删减片段 | 不含 `dom/bindings/domtrace` |
| `ff-ruyijs` 仓库 grep `domtrace` 零命中 | 不是这个上游的功能 |
| 官方 Firefox 是否含此目录 | `To be confirmed`（方案 A 未验证） |
| 跨平台编译必须理解源码 | Linux 版不是换编译器就行，要重建插桩点 |

**结论**：不做反编译，RuyiTrace 永远只能在 Windows 上跑。这不是可选项。

---

## 1. 五步法

```
① 契约提取  从文档 + 二进制抽全部对外可见的常量与结构
② 符号定位  从 PE 找到实现这些常量的函数
③ 语义重建  把汇编还原成有名字、有类型的伪 C++
④ 交叉验证  用真机行为对照：设开关 → 看输出 → 验证重建的语义
⑤ 工程化    落成可编译的 C++ 源码，进 DOM 绑定层
```

每一步都有**退出标准**，没达到不进入下一步。

---

## 2. 第一步：契约提取

### 2.1 输入

| 来源 | 内容 | 可提取什么 |
| --- | --- | --- |
| `xul.dll` strings | 74 个 `MOZ_DOM_*` | 开关全名 |
| `README.md`（2659 行） | 原理手册，103 章节 | 语义、字段、边界条件 |
| `README-cheatsheet.md`（449 行） | 取值 / 默认 / 用途 / 生效条件 | 类型与默认值 |
| `switches.js`（175 行） | `kind` / `default` / `choices` / 分组 | **类型系统的权威** |
| `jscall_decode.py`（536 行） | 二进制格式 | 记录布局（32 字节定长） |
| `trace_diff.py`（109 行） | 字段名 | JSON 记录 schema |
| 真机 trace 输出 | 实测 jsonl | 字段全集与取值域 |

### 2.2 产出：契约表

`projects/ruyitrace/domtrace-analysis.md` 里维护一张主表，74 行：

| 字段 | 来源 | 示例 |
| --- | --- | --- |
| `env` | strings | `MOZ_DOM_TRACE_SITE_CAP` |
| `kind` | switches.js | `int` |
| `default` | switches.js + cheatsheet | `4096` |
| `range` | cheatsheet | `0-4294967295` |
| `group` | switches.js | `总开关与输出` |
| `depends_on` | cheatsheet「生效条件」 | `MOZ_DOM_TRACE=1` |
| `output` | cheatsheet §0.2 | `domtrace\trace_process_<pid>.jsonl` |
| `impl_rva` | **第二步填** | `To be confirmed` |
| `status` | 分析进度 | `located` / `reconstructed` / `verified` |

### 2.3 退出标准

- [ ] 74 个开关全部有 `kind` + `default` + `depends_on`
- [ ] 输出文件清单（12 类）与开关的对应关系完整
- [ ] 三个记录格式（core jsonl / jscall bin / detail bin）的字段表完成

**当前进度：契约提取可完成度约 90%**（文档很详细，缺的是个别边界的实测确认）。

---

## 3. 第二步：符号定位

### 3.1 工具链

```bash
# 本机可用
objdump  readelf  nm          # binutils
# 需安装
pip install pefile capstone   # PE 解析 + 反汇编
# 可选
ghidra / ida / radare2        # 交互式分析
```

### 3.2 锚点

74 个 env 字符串是天然锚点。它们通过 `getenv()` 读取，所以：

```bash
# 1. 定位字符串的 RVA
python3 scripts/env-anchors.py \
  --pe artifacts/binaries/kernel/xul.dll \
  --prefix MOZ_DOM_ \
  -o artifacts/analysis/domtrace/env-anchors.json

# 输出：{ "MOZ_DOM_TRACE": {"rva": "0x...", "refs": ["0x..."]}, ... }
```

```bash
# 2. 找引用该字符串的指令（x64 下是 lea rcx, [rip+off]）
#    用 capstone 扫 .text 段，找 RIP 相对寻址指向该 RVA 的点
```

### 3.3 关键点：`getenv` 的调用形态

MSVC x64 下典型序列：

```asm
lea     rcx, [rip + <str_rva>]      ; "MOZ_DOM_TRACE"
call    qword ptr [getenv]          ; 或 call getenv_impl
test    rax, rax
je      <skip>
```

`call` 目标是 `getenv` 的 thunk。先用 `dumpbin /imports` 或 pefile 找 `getenv` 的 IAT 槽位，再扫 `call qword ptr [rip+iat_off]`。

**注意**：mingw/clang 编译的产物可能不经过 IAT，而是直接 `call getenv`（静态链接）。`xul.dll` 是 MSVC 构建，应该走 IAT。

### 3.4 退出标准

- [ ] 74 个 env 字符串的 RVA 全部确定
- [ ] ≥ 60 个找到 `getenv` 调用点（即开关的读取位置）
- [ ] 每个调用点的**所在函数起始地址**已确定

**当前进度：0/74。**

---

## 3.5 插桩点已经找到（2026-11-19）

官方 159.0 源码里，**全部 WebIDL 属性读写与方法调用收敛到三个函数**：

| 函数 | 位置 |
| --- | --- |
| `GenericGetter` | `dom/bindings/BindingUtils.cpp:3054` |
| `GenericSetter` | 同上 |
| `GenericMethod` | 同上 |

`Codegen.py` 生成这些函数的调用（6 种 `ThisPolicy` 变体），是结构性保证。

详见 [`../projects/ruyitrace/instrumentation-sites.md`](../projects/ruyitrace/instrumentation-sites.md)。

---

## 4. 第三步：语义重建

### 4.1 从调用点向外扩散

一个开关的读取点通常长这样：

```cpp
// 重建目标
static const bool kTraceTimers = ReadBoolEnv("MOZ_DOM_TRACE_TIMERS", false);
```

而实际二进制里是：

```asm
; 函数入口附近
call  getenv
test  rax, rax
je    .default
movzx eax, byte ptr [rax]
cmp   al, '1'
sete  cl
; cl = (value[0] == '1')
```

重建顺序：

```
读取点 → 该函数的完整控制流 → 它写入的全局变量 / 静态成员
       → 谁读这个全局 → 生产者函数（写 trace 的地方）
       → 该函数调用的结构体字段 → 记录 schema
```

### 4.2 命名策略

不要用 `sub_1400A2B30` 这种名字。用**语义命名**：

| 重建对象 | 命名规则 | 例 |
| --- | --- | --- |
| 开关全局 | `gTrace<Feature>` | `gTraceTimers` |
| 记录结构体 | `<Kind>Record` | `TimerLifecycleRecord` |
| 写入器 | `Write<Kind>Record` | `WriteTimerLifecycle` |
| 预算/上限 | `<Kind>Budget` | `SiteBudgetCapped` |
| 环境读取 | `Read<N>Env` | `ReadIntEnv` |

命名表单独维护在 `projects/ruyitrace/domtrace-analysis.md` 的「符号命名表」小节。

### 4.3 结构体还原

`jscall_decode.py` 已经给了 jscall 的布局（这是最强的证据）：

```python
HEADER_FORMAT = "<4sHHII"          # 16 字节
RECORD_FORMAT = "<QQIIHHBBH"       # 32 字节
MAGIC = b"JSCT"
FLAG_CONSTRUCT  = 1 << 0
FLAG_OK         = 1 << 1
FLAG_NATIVE     = 1 << 2
FLAG_SELF_HOSTED= 1 << 3
FLAG_SUSPENDED  = 1 << 4
```

`<QQIIHHBBH` = `u64 call_id, u64 func_id, u32 ?, u32 ?, u16 ?, u16 ?, u8 flags, u8 ?, u16 ?`

> 这个格式**必须与二进制里的写入代码逐字节对上**。对不上说明解码脚本与内核版本不一致——这本身就是重要发现。

### 4.4 退出标准

- [ ] 每个已定位开关能写出 3-10 行等价伪代码
- [ ] 主要记录结构体的字段顺序与大小确定（≥ 6 个结构体）
- [ ] 记录写出路径的函数调用链画出来

**当前进度：0%。**

---

## 5. 第四步：交叉验证（最有价值的一步）

重建出来的语义必须用**真机行为**验证，否则就是自说自话。

### 5.1 验证闭环

```
假设：MOZ_DOM_TRACE_TIMER_LIMIT 默认 16384，范围 1-1000000，非法值回退默认
  ↓
实验：设 MOZ_DOM_TRACE_TIMERS=1，MOZ_DOM_TRACE_TIMER_LIMIT=0（非法）
  ↓
预期（若假设成立）：日志里 timer 记录上限为 16384，且首次超限写 timer_trace_gap
  ↓
实测：对比记录条数与 gap 标记
  ↓
结论：假设成立 / 不成立 / 部分成立
```

### 5.2 可自动化的验证

每个开关都有**文档声称的行为**，逐条变成断言：

| 开关 | 文档声称 | 可测断言 |
| --- | --- | --- |
| `MOZ_DOM_TRACE` | `0` 关核心及跟随模块，但 JSCall 等独立 | 设 `TRACE=0` + `JSCALL_TRACE=1`，核心文件不存在、jscall 文件存在 |
| `MOZ_DOM_TRACE_UNFILTER` | 按成员名精确匹配解除黑名单 | 默认 `getComputedStyle` 无记录；加进 UNFILTER 后有记录 |
| `MOZ_DOM_ABSENT_PROBE` | 按 (接口, 名字) 去重，读 20000 次只记 1 条 | 循环读同一不存在属性，计数为 1 |
| `MOZ_DOM_TRACE_SITE_CAP` | 首次超限写 `site_budget_capped` | 死循环触发，找该记录 |
| `MOZ_DOM_IDB_VALUE_MAX_BYTES` | 范围 256-24576 | 设 100，应被拒用默认 8192 |

**这套断言本身就该进 `ruyitrace` 仓的测试**——它是「重建是否成功」的客观标准。

### 5.3 退出标准

- [ ] 74 个开关中 ≥ 50 个有可执行断言
- [ ] 断言跑过一遍，失败项归因为「假设错误」或「测试写错」
- [ ] 记录 schema 与 `jscall_decode.py` 逐字节对上

---

## 6. 第五步：工程化

### 6.1 目标产物

```cpp
// dom/bindings/domtrace/TraceTimers.cpp（示意）
#include "TraceConfig.h"
#include "TraceRecord.h"

namespace mozilla::dom::domtrace {

static const bool kTimersEnabled = ReadBoolEnv("MOZ_DOM_TRACE_TIMERS", false);
static const uint32_t kTimerLimit  = ReadUintEnv("MOZ_DOM_TRACE_TIMER_LIMIT", 16384, 1, 1000000);

MOZ_ALWAYS_INLINE void OnTimerRegister(nsIWindow* win, int32_t handle, uint32_t delay) {
  if (!kTimersEnabled) return;
  if (gTimerEvents >= kTimerLimit) { WriteGapOnce(); return; }
  WriteTimerLifecycle(Phase::Register, win, handle, delay);
}

}  // namespace
```

**要求**：
- 与 `switches.js` 的 `kind`/`default`/`range` 一一对应
- 与重建出的二进制结构体布局一致
- 命名遵循 Mozilla 代码风格（`mozilla::dom::domtrace` 命名空间）

### 6.2 接入点

插桩点在 DOM 绑定层。参考 Firefox 现有的 trace / telemetry 接入方式：

```
dom/bindings/BindingUtils.cpp
dom/bindings/Codegen.py            ← WebIDL 代码生成，getter/setter 包装在这里
dom/bindings/WebIDLGlobalNameHash.cpp
js/xpconnect/wrappers/              ← proxy 层，属性探测在这里
```

### 6.3 退出标准

- [ ] 能 `mach build` 出带插桩的 `xul`（Linux 与 Windows 各一次）
- [ ] 开关行为与原始 `xul.dll` 一致（用 §5 的断言验证）
- [ ] 记录格式与 `jscall_decode.py` / `trace_diff.py` 兼容

---

## 7. 风险与止损

| 风险 | 概率 | 止损 |
| --- | --- | --- |
| 官方树无 domtrace 目录 | 中 | 方案 C（问上游要源码）优先 |
| 反编译出的语义与真机不符 | 高（正常） | §5 交叉验证作为唯一验收标准 |
| 插桩点太多（74 开关 × 多个点） | 高 | **按开关价值排序**，先做 top 10 |
| Linux 全量编译 xul 耗时不可接受 | 中 | 增量编译 + ccache；只编 `dom/bindings` 增量 |
| 重建后性能退化 | 中 | 文档已给实测数据（`new Error()` 插桩 12840ns vs 95ns），照此 benchmark |

### 优先级排序（建议）

先做**输出量最大、语义最清晰**的开关：

1. `MOZ_DOM_TRACE` + `MOZ_DOM_TRACE_FILE`（总开关与锚点）
2. `MOZ_DOM_TRACE_SNAPSHOT`（返回对象快照，默认开）
3. `MOZ_DOM_TRACE_TIMERS`（定时器生命周期）
4. `MOZ_DOM_ABSENT_PROBE`（宿主属性探测）
5. `MOZ_DOM_UNFILTER`（解除成员过滤）

这 5 个覆盖了 trace 的主要价值，也最容易验证。做完再评估剩余 69 个的投入产出。

---

## 8. 与主线的衔接

```
反编译还原（本文）
   ↓ 产出可编译的 domtrace 源码
RuyiTrace 内核重编（docs/03-linux-port.md L4）
   ↓ 产出 Linux xul
三件套 Linux 闭环（docs/03-linux-port.md §5 验证脚本）
```

**反编译不是终点，是 L4 的前置。** 没有它，L4 层不成立；有了它，L4 才从「不可能」变成「耗时」。

---

## 9. 本仓不做的事

| 不做 | 理由 |
| --- | --- |
| 在本仓存二进制与 dump | 体积大可再生，`artifacts/` 已 gitignore |
| 在本仓写还原后的 C++ | 归 `ruyitrace` 仓的 `domtrace/` |
| 承诺时间表 | 反编译进度不可线性预估，只报当前进度百分比 |
