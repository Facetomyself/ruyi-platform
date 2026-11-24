# 证据等级总账

> 13 轮做下来，仓库里的结论混着三个可信度层级。本文把这些结论收拢成一张表，
> 后来的人可以一眼看清：**哪些是实测的、哪些是推断的、哪些在等外部输入。**

## 分级定义

| 级别 | 含义 | 判定标准 |
| --- | --- | --- |
| **A · 实测** | 跑过命令、看过输出、结果可复现 | 有具体命令 + 具体输出 |
| **B · 有依据推断** | 结构来自官方源码或文档明文，但**具体值/键名**是推的 | 能指到源码行号或文档段落 |
| **C · 待外部输入** | 缺数据源，本仓无法自行确认 | 明确写出缺什么 |

---

## A 级：实测（可直接信任）

### A1 · domtrace 开关

| 结论 | 证据 | 复现 |
| --- | --- | --- |
| 74 个 `MOZ_DOM_*` 字符串，每个唯一 | `strings` + RVA 映射 | `scripts/domtrace-anchors.py` |
| 104 条 `lea` 引用 | 扫描 `.text` 8.2 亿字节 | 同上 |
| 15816 个 `getenv` 调用点，7 种形态 | 寄存器预载识别 | 同上 |
| **74/74 读取点配对** | 每个 `lea` 后 16 字节内有 `getenv` call | 同上 |
| 10 种解析模式 | 逐条反汇编确认 | `trace-config-slots.h` |
| 5 个读取器区域 | 地址聚类 | `domtrace-readers.md` |

### A2 · ruyijs operation

| 结论 | 证据 |
| --- | --- |
| 39 个 operation 名 | 19 个 `.py` 枚举 |
| 15 个独立字符串 + 31 个立即数 = 37 定位 | `scripts/ruyijs-ops-scan.py` |
| 分发器是 16 路跳转表 + movabs/SSE 三种校验 | `0x1400bcf93` 反汇编 |
| `advance`/`status`/`drain` 的"命中"是子串误报 | 逐个查上下文 |

### A3 · 版本溯源

| 结论 | 证据 |
| --- | --- |
| `9a2dc53c` = `FIREFOX_159_0_RELEASE` | `git ls-remote --tags`（**必须用远程查询**：sparse clone 的本地 tag 表不全，`git tag --points-at` 会返回空） |
| `2887d9de` 在官方 release 分支 | `git fetch --depth 1` 成功 |
| **`39bfd14c` 官方不存在** | `couldn't find remote ref` |
| 官方 `dom/bindings/` grep domtrace = 0 | `git ls-tree -r` |

### A3 补 · 复现时的一个坑

`git tag --points-at 9a2dc53c` 在 sparse clone 里**返回空**——本地没有完整 tag 表。
必须用远程查询：

```bash
git ls-remote --tags origin | grep 9a2dc53c
# 9a2dc53c... refs/tags/FIREFOX_159_0_BUILD1
# 9a2dc53c... refs/tags/FIREFOX_159_0_RELEASE
# 9a2dc53c... refs/tags/FIREFOX-ANDROID_159_0_RELEASE
```

同一个 commit 同时是桌面与 Android 的 159.0 release。

### A4 · 插桩点

| 结论 | 证据 |
| --- | --- |
| `GenericGetter/Setter/Method` 是全部 WebIDL 入口 | `Codegen.py` 生成 6 种 ThisPolicy 调用 |
| `BindingUtils.cpp:3054` 等 3 处 | 源码行号 |
| `JSJitInfo` 只有 16 字节 | `static_assert` 原文 |
| `nativeOp` 与 `depth` 共用 | union 定义 |

### A5 · 实现与测试

| 结论 | 证据 |
| --- | --- |
| 17 项 domtrace 测试全通 | `bash tests/run-tests.sh` |
| 19 项 ruyihttp 测试全通 | `unittest discover` |
| jscall 写入器与官方解码器互通 | 端到端写→读→比对 |
| 8 个 sink 真实写盘 | 磁盘文件 + Python `json.loads` |
| 三平台 wheel 26 个原生文件 hash 全匹配 | 重建 + 逐文件校验 |

---

## B 级：有依据的推断（**键名/取值需要验证**）

### B1 · wasm 记录的 JSON 键名

**依据**：手册 §3（2107-2160 行）给了语义与文件名格式。

**推断的具体项**：

| 键名 | 依据等级 | 说明 |
| --- | --- | --- |
| `type` | 推断 | 手册未给 jsonl 的 type 值 |
| `dumped` / `skip_reason` | 推断 | `DUMP_MAX`/`DUMP_TOTAL` 拦截语义有依据，键名无 |
| `mem_window` / `data_b64` | 推断 | 「i32 落在 [1, memLength) 附带窗口」有依据，键名无 |
| `func_index` / `export` / `phase` | 推断 | `wasm_export_map` 与 enter/leave 有依据，键名无 |
| `exports[].index` / `.name` | 推断 | 同上 |

**验证方式**：一次真机 `MOZ_DOM_WASM_CALL=1` 采集，对比输出。

### B2 · 部分记录字段的完整性

| 记录 | 有明确依据的字段 | B 级字段 |
| --- | --- | --- |
| exception | `error` 五字段、`stack_count` | 无 |
| event | 14 类事件名、`event_id`、采样规则 | listener 的具体键名 |
| descriptor | `valueType`、`value` | `configurable`/`enumerable`/`writable` |
| cookie | 五种通路、`source`/`readType` | `httpOnly`/`secure`/`session`/`aHttpBound` |
| storage | 截断规则、`oldValue`、`valueIsNull`、`requestId` | `dbName`/`storeName` |
| http_packet | `meta` 六键（蛇形驼峰双写）、`dropped_full` | body/header 的具体键名 |
| websocket | **完整 14 行字段表** | 无 |

---

## C 级：待外部输入（本仓无法自行确认）

| 项 | 缺什么 | 谁来补 |
| --- | --- | --- |
| `env_inventory` 的 JSON 结构 | 手册只有「约 1.2 MB 接口清单」一句 | 真机采集 |
| `drain` / `put` 两个 operation 的编码 | 名字太短，需逐函数反汇编全部分支 | 反编译 |
| 内部版 `js.exe` 的 181 个 identity 缺口 | `RECOVERY.md` 说已穷尽独特锚点 | 行为断言 |
| domtrace 重编后的实际行为 | 需 `mach build` 环境 | 构建主机 |
| 重建 wheel 的 live 验证 | glibc 2.38+ 主机 | 构建主机 |

---

## 汇总统计

| 级别 | 条目数 |
| --- | ---: |
| A · 实测 | 5 类，约 25 条具体结论 |
| B · 有依据推断 | 2 类，约 15 个键名 |
| C · 待外部输入 | 5 项 |

## 使用建议

1. **写代码时**：A 级的直接用；B 级的用，但在注释里标 `// 键名待样本`；C 级不要用
2. **评审时**：看到 B 级结论，问「验证要什么」——表里都写了
3. **新增结论时**：先想清属于哪一级，A 级必须带可复现命令

## 验证纪律（R387/R388 的教训）

两条来自真实事故的规矩，写在这里因为它们比任何单条结论都更常被违反。

**一、没有对照就不能声称因果。**
R387 引入了一个未绑定变量的缺陷，那一轮却写下「不带 cutoff 的对照也失败，可排除本轮改动」——当时**没有 r386 对照组**，"同一个错误出现两次"被当成了"两件事无关"。补上对照后立即推翻：同一环境同一用例，已签收的 r386 返回 200，r387 失败。
→ 判定「不是这次改的」必须有一个**已知可用的对照版本**在同一环境跑同一用例。

**二、绕开既有的受控工具，等于放弃它已经处理好的边界。**
R213 为了赶进度，跳过 `run_host.py` 自行拼 docker 命令，连续制造两个错误：tmpfs 漏 `exec` 导致 `ldd` 无法映射 DSO、输出目录属主不对导致写入失败。改回 `run()`（它本就处理这两点）后一次成功。
→ 受控脚本里的每条 docker 参数都是有理由的；临时命令容易漏掉其中一条，而遗漏的后果往往表现为与本意无关的报错。

**附：自制静态检查器的教训。**
R215 尝试写一个「读取未绑定名字」的检查器，连续四轮未收敛：先漏掉闭包自由变量，修后又把闭包参数误报为未绑定。没有成熟 linter 可用时应改用**运行真实代码路径**来验证（本轮用 `load_pins` + `inspect.signature` 走了一遍配置路径），而不是自己重造一个不完整的分析器。

## 维护规则

- 任何 B 级项被实测确认后，**升级到 A 级并删除原标记**
- 任何 A 级项被推翻，**不删除，加更正记录**（见 `conventions.md` §6）
- 本文与 `STATUS.yaml` 的 `inferred_keys` 保持同步
