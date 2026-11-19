# domtrace 反编译进度

方案：[`../../docs/05-reverse-analysis.md`](../../docs/05-reverse-analysis.md)
对象：`resources/kernel/xul.dll`，187,741,696 B

---

## 1. 契约表（74 行主表）

**状态：已完成。** 见 [`domtrace-contract.md`](domtrace-contract.md)。

自动化命令：

```bash
python3 ../../scripts/domtrace-anchors.py \
  --pe ../../artifacts/binaries/ruyitrace/xul.dll
```

实测输出：

```
开关字符串: 74
RVA 映射: 74
lea 引用: 104 条，覆盖 74 个字符串
getenv IAT: RVA=0xa185ad0
getenv 调用点: 15816 去重
读取点配对: 74/74
```

### 原始表（保留作对照）

字段定义见方案 §2.2。

| # | env | kind | default | range | group | depends_on | output | impl_rva | status |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | `MOZ_DOM_TRACE` | tristate | 不设 | `1`/`0` | 总开关与输出 | — | `domtrace\trace_process_<pid>.jsonl` | To be confirmed | 未开始 |
| 2 | `MOZ_DOM_TRACE_FILE` | path | — | — | 总开关与输出 | 启用核心 | 全部输出锚点 | To be confirmed | 未开始 |
| 3 | `MOZ_DOM_TRACE_SNAPSHOT` | default_on | 开 | `1`/`0` | 补环境探测 | `TRACE=1` | returnSnapshot/valueSnapshot | To be confirmed | 未开始 |
| … | … | … | … | … | … | … | … | … | … |

生成骨架：

```bash
# 从 switches.js 抽 74 条，生成 markdown 表格初稿
python3 - <<'PY'
import re
src = open('submodules/ruyitrace/console/src/shared/switches.js', encoding='utf-8').read()
rows = re.findall(r"\{ env: '([A-Z0-9_]+)', group: '([^']+)', kind: '([a-z_]+)'", src)
print('| # | env | group | kind |')
print('| --- | --- | --- | --- |')
for i, (env, group, kind) in enumerate(rows, 1):
    print(f'| {i} | `{env}` | {group} | {kind} |')
print(f'\n共 {len(rows)} 条')
PY
```

---

## 2. 符号定位

**状态：74/74 完成。** 见 [`domtrace-contract.md`](domtrace-contract.md) 与 [`domtrace-readers.md`](domtrace-readers.md)。

### 关键发现

| 项 | 值 |
| --- | --- |
| `getenv` 导入 DLL | `api-ms-win-crt-environment-l1-1-0.dll` |
| `getenv` IAT RVA | `0xa185ad0` |
| 开关字符串 | 74 个，每个只出现一次，全在 `.rdata` |
| `lea` 引用 | 104 条（有 30 个开关被多处引用） |
| `getenv` 调用点 | 15816 个（去重），形态分布见下 |

### 调用点形态（重要）

domtrace 的开关读取**不止一种形态**：

| 形态 | 数量 | 代码 |
| --- | ---: | --- |
| `direct` | 174 | `call qword ptr [rip + getenv_IAT]` |
| `r15` | 6147 | 函数头 `mov r15, [getenv_IAT]`，之后 `call r15` |
| `rbx` | 3730 | 同上 |
| `rsi` | 5192 | 同上 |
| `rax/rcx/rdx` | 573 | 同上 |

**这就是第一版脚本只配到 41/74 的原因**——只认 `direct` 形态。补齐寄存器形态后达到 74/74。

### 读取器聚类

74 个开关由 **5 个区域**的函数读取：

| 区域 | 开关数 | 函数起点 | 覆盖 |
| --- | ---: | --- | --- |
| `0x180600000` | 40 | `0x18065fbfa` | 总开关 + 补环境探测 + WASM + exception |
| `0x185600000` | 16 | `0x18563e213` | jscall 全组 |
| `0x182a00000` | 11 | `0x182ad0720` | event + exception 部分 |
| `0x181c00000` | 5 | `0x181c69103` | API 定制 / 随机数劫持 |
| `0x180a00000` | 2 | `0x180a96290` | HTTP packet + WS |

**含义**：只要还原这 5 个函数，就覆盖全部 74 个开关的读取逻辑。这大幅收窄了工作量。

---

## 3. 结构体还原

`jscall_decode.py` 已给 jscall 的布局，作为第一个对齐目标：

```python
HEADER_FORMAT = "<4sHHII"        # 16 字节，MAGIC = b"JSCT"
RECORD_FORMAT = "<QQIIHHBBH"     # 32 字节
FLAG_CONSTRUCT   = 1 << 0
FLAG_OK          = 1 << 1
FLAG_NATIVE      = 1 << 2
FLAG_SELF_HOSTED = 1 << 3
FLAG_SUSPENDED   = 1 << 4
```

**待还原的结构体清单**：

| # | 结构体 | 字段数 | 状态 |
| --- | --- | --- | --- |
| 1 | `JSCallRecord`（32 字节） | 9 | To be confirmed |
| 2 | `JSCallHeader`（16 字节） | 5 | To be confirmed |
| 3 | 核心 trace jsonl 记录 | 待定 | To be confirmed |
| 4 | `TimerLifecycle` 记录 | 待定 | To be confirmed |
| 5 | `EnvInventory` 输出 | 待定 | To be confirmed |
| 6 | `HttpPacket` 记录 | 待定 | To be confirmed |

---

## 4. 行为断言（交叉验证）

**状态：0/N。** 优先级最高的 5 个：

| # | 开关 | 文档声称 | 断言 | 状态 |
| --- | --- | --- | --- | --- |
| 1 | `MOZ_DOM_TRACE` | `0` 关核心，但 JSCall 等独立 | `TRACE=0` + `JSCALL_TRACE=1` → 核心文件无、jscall 文件有 | 待跑 |
| 2 | `MOZ_DOM_TRACE_UNFILTER` | 成员名精确匹配解除黑名单 | 默认 `getComputedStyle` 无记录；加入后有 | 待跑 |
| 3 | `MOZ_DOM_ABSENT_PROBE` | 按 (接口, 名字) 去重 | 循环读同一不存在属性 20000 次，计数为 1 | 待跑 |
| 4 | `MOZ_DOM_TRACE_SITE_CAP` | 首次超限写 `site_budget_capped` | 死循环触发，找该记录 | 待跑 |
| 5 | `MOZ_DOM_IDB_VALUE_MAX_BYTES` | 范围 256–24576 | 设 100 应被拒用默认 8192 | 待跑 |

---

## 5. 发现与陷阱

（逐步累积）

| 日期 | 发现 | 影响 |
| --- | --- | --- |
| 2026-11-19 | 文档称 69 个开关，实际 74 | 以 74 为准，cheatsheet 需重生成 |
| 2026-11-19 | `MOZ_DOM_HTTP_PACKET_TRACE_MAX_PENDING` 文档有、内核无 | 标记废弃 |
| 2026-11-19 | `kernel/moz-src/` 仅 572 文件删减片段 | 无法用于重编，只能参考 |
