# 01 · 组件级架构与数据流

## 下游先选依赖，再选证据

`ruyi-platform` 是**版本与交接仓，不是需要启动的服务**。[四个 gitlink](../.gitmodules) 分别锁定 Trace、MCP、JS、Http；RuyiDOM 是[独立发布的第五个相关项目](14-source-handoff.md#ruyidom-独立源码交接)。以下按实际接口区分依赖，不能把共享 Firefox 技术来源画成产品之间的调用链。

| 谁使用谁 | 关系与所有权 | 下游可以省掉什么 |
|---|---|---|
| Trace CLI 或 Electron → 匹配架构的插桩 Firefox | **运行依赖**。CLI 与 Electron 是两种入口。由启动方持有进程、profile、采集闸门和最终刷盘；amd64 R5 内核的冻结输入与管理 CLI 的维护提交不同。[构建与制品](14-source-handoff.md) | 无头采集无需 Electron、MCP、RuyiJS、RuyiHttp 或 RuyiDOM。旧包附带的内部 JS wheel 是可选工具资源。 |
| MCP → Python bridge → Firefox | **自启模式**。MCP 管自己的进程、profile 与 BiDi；可选用 Trace Firefox 做浏览器，但导航和 RDP 通过本身不等于产生 DOMTrace。[自启验收](../artifacts/receipts/ruyi-mcp-amd64-d7DBYN4g-20261124.json) | 仅需自动化或调试时，无需先运行 Trace owner。 |
| MCP → Trace owner → 已运行的 Firefox | **借用模式，可选集成**。MCP 只持排他租约，经回环 owner IPC 做页面操作；RDP 调试是独立通道。Trace 保留唯一 BiDi 会话、进程和 flush 权；MCP 归还后浏览器继续运行。证据分别看 [M2 两种停止方式](../artifacts/receipts/trace-amd64-r5/m2-delivery.json)及[自然到期和范围检查](../artifacts/receipts/trace-amd64-r5/borrowed-behaviors-b5e204a.json)。 | 不启动第二个 Firefox，不把“归还租约”实现成关闭 owner 的浏览器。无需 JS/Http 库。 |
| Python 或 C 客户端 → RuyiJS 私有壳 | **运行依赖**。[R355 干净原生归档](../submodules/ruyijs/docs/linux-amd64-clean.md)将私有壳、C 客户端、绑定与运行库成套分发；[R354 wheel](../submodules/ruyijs/docs/linux-amd64-wheel.md)封装的是 R353。两者均未打包在线导航所需的[匹配 Necko helper 和原生栈](../submodules/ruyijs/src/resource_network/necko_linux.cpp)。 | 离线 DOM/JS 无需浏览器 owner。安装 RuyiHttp 本身不构成 JS 侧联网验收。 |
| Python 调用方 → RuyiHttp → 自带的 Necko/NSS/QUIC 运行库 | **独立传输客户端**。与 RuyiJS 的派生适配有共同的协议/ABI 来源；双方有各自的包、依赖和验收。[HTTP 的平台矩阵](../projects/ruyihttp/README.md) | 发 HTTP 请求无需浏览器、MCP、JS 壳或 DOM。HTTP 的 h2 成功也不是 JS 联网或 H3 验收。 |
| 调用方 → RuyiDOM → Firefox **136** + 供应商 JS | **独立工具链**。`native` 用 xpcshell 做离线 DOM；显式 `browser` 后端使用真实内容进程导航。供应商输入在 Git 外，详见[固定版本输入清单](https://github.com/Facetomyself/ruyidom/blob/4009bae850f9b64d413bd41a94dd7b3c56f86b40/docs/INPUTS.md)。 | RuyiDOM 不是 RuyiJS 的别名、Trace 159 的前端或第五个子模块；不把 136 的行为当作 159 的发布证据。 |

**跨项目对照只传数据。** 在自有测试页上，业务项目可把同一 fixture 的 Trace 记录、RuyiJS/RuyiDOM 求值结果、RuyiHttp 响应分开存档，以 fixture 摘要、组件 SHA、架构和运行时版本关联。它们是可选的结果对照；不存在一条需要同时运行五个产品的流水线。发布阻塞及验收顺序见[当前缺口](04-risks-and-gaps.md#当前交付缺口)。

下文保留三件套的实现细节；涉及旧 Win64 包的描述按该包理解。

---

## 1. RuyiJS：单进程 + 命名管道

### 1.1 进程模型

```
┌──────────────────────┐        Windows Named Pipe        ┌───────────────────────┐
│  Python 进程          │  ◄──────── 16 MB 帧上限 ───────► │  js.exe 子进程         │
│  ruyijs.Context      │        overlapped I/O            │  SpiderMonkey 159     │
│  ├ _pipe.py          │                                  │  ├ 38 个浏览器子系统    │
│  ├ _values.py 编解码  │                                  │  ├ Skia 2D            │
│  └ _callbacks.py     │                                  │  └ Necko 网络栈        │
└──────────────────────┘                                  └───────────────────────┘
```

- **传输**：`_pipe.py` 用 `CreateNamedPipeW` + `ConnectNamedPipe` + overlapped `ReadFile`/`WriteFile`，`MAX_FRAME = 16 * 1024 * 1024`。
- **启动**：`subprocess.Popen(..., stdin=DEVNULL, stdout=DEVNULL, stderr=PIPE, creationflags=subprocess.DETACHED_PROCESS)`。文件头注释解释了为什么不用 `CREATE_NO_WINDOW`——那会额外拉起一个 `conhost.exe`（约 6 MiB）。
- **协议**：JSON + 二进制混合帧，`_request(operation, **fields)` 分发到各 Control 混入类。
- **清理**：超时或协议坏掉即 `kill` 子进程并置 `_closed`。

### 1.2 Context 的九层混入

`Context` 用多重继承组合了 9 个能力，每个对应一个文件、一组 operation：

| 混入 | 文件 | 关键方法 | 作用 |
| --- | --- | --- | --- |
| `EnvironmentControl` | `_environment.py` | `configure_fingerprint` / `configure_environment` / `get_defaults` | Navigator / Screen / viewport / TZ / locale |
| `SchedulingControl` | `_scheduling.py` | `configure_clock` / `advance` / `tick` / `run_timer` / `configure_navigation_replay` | 逻辑时钟、定时器重放 |
| `RandomControl` | `_random.py` | — | 随机数覆盖 |
| `ResourceControl` | `_resources.py` | `put_resource` / `get_resource` / `export_cookies` / `cookie_header` / `net_log` | 离线响应、cookie 导出 |
| `ConsoleControl` | `_console.py` | `console_log` | 控制台记录 |
| `InspectorControl` | `_inspector.py` | `get_api_log` / `peek_api_log` | API 调用记录 |
| `InputControl` | `_input.py` | `dispatch_input` / `click` / `type` / `press` | 输入事件注入 |
| `EvaluationControl` | `_context_eval.py` | `eval` / `locals` | JS 求值 |
| 本体 | `_context.py` | `load_page` / `navigate` / `set` / `expose` / `native` / `checkpoint` | 生命周期 |

### 1.3 平台硬编码（Linux 移植的直接障碍）

**内部 wheel `0.2.2+inner.*` 的硬编码**：

| 文件 | 行 | 代码 | 影响 |
| --- | --- | --- | --- |
| `_pipe.py` | 14 | `if os.name != "nt": raise OSError(...)` | **整个包 import 即失败** |
| `_runtime_paths.py` | 16 | `if os.name != "nt" or machine not in ("amd64","x86_64")` | 运行时定位失败 |
| `_runtime_paths.py` | 35 | `(root / "dist" / "js.exe").is_file()` | 硬编码 `.exe` |
| `_context.py` | ~105 | `creationflags=subprocess.DETACHED_PROCESS` | Windows-only 常量 |
| `_context.py` | ~120 | `error.winerror == 109` | ERROR_BROKEN_PIPE |
| `_context.py` | 40-58 | `_prefer_bundled_crt()` 写 Wine 注册表 | 仅 Wine 用 |
| `_context.py` | 60 | `import winreg` | Windows-only |

> **重要更正**：这 7 处**上游 ff-ruyijs 0.4.1 已经全部解决**。其 `python/ruyijs/`
> 的 `_pipe.py`（208 行）、`_runtime_paths.py`（59 行）、`_context.py`（495 行）都是跨平台的。
>
> **但这不等于内部版可以抄。** 按 `06-ruyijs-inner.md` §0 的硬规则：
> `ff-ruyijs` 是 public fork，**只作 PR 目标与反编译对照**，不作内部基线。
> 内部版 `js.exe` 与它的构建 commit 不同（`9a2dc53c` vs `2887d9de`），行为会漂移。
> 正确做法是：反编译还原内部版 → 用上游做语义对照 → 结论标注「参照」或「与二进制一致，采用」。
> 详见 [`06-ruyijs-inner.md`](06-ruyijs-inner.md)。

内部与上游 `python/ruyijs/` 的差异仅 5 个文件：

| 文件 | 内部 | 上游 0.4.1 |
| --- | --- | --- |
| `_pipe.py` | 127 | **208**（新增 AF_UNIX 分支） |
| `_runtime_paths.py` | 38 | **59**（新增 `macos_arm64()`/`linux_x86_64()`） |
| `_context.py` | 418 | **495**（spawn 按平台分支） |
| `_engine.py` | 214 | 215 |
| `_version.py` | `0.2.2+inner.*` | `0.4.1` |

其余 14 个 `.py` 逐字节一致。

### 1.4 两个内部构建的差异

| | `+inner.492ee47` | `+inner.20261101191032`（RuyiTrace 自带） |
| --- | --- | --- |
| `_engine.py` | ✅ 有 `Engine` / `use_engine` | ❌ 已删除 |
| `examples/` | 26 个站点（Akamai / DataDome / 极验 / 数美 / 瑞数…） | ❌ 全部移除 |
| `build-identity.json` | ❌ | ✅ `base_commit aa255fbb…`，`working_tree_changes: true`，`source_files_verified: 2038` |
| `_runtime/SHA256SUMS` | ✅ 1579 条 | ❌ 无（由 RECORD 代替） |
| `dist/` 内容 | js.exe + 3 CRT | js.exe + 5 CRT + **`ruyijs_client.dll`** + TwemojiMozilla.ttf |
| vendor 文件数 | 1062 | 1216 |

**要做多会话（Engine）必须用 `492ee47` 那版**；要做服务端集成（`ruyijs_client.dll`）必须用 `20261101191032`。

---

## 2. RuyiHttp：库，不是进程

### 2.1 调用栈

```
用户代码
  └ ruyihttp.Session(firefox="159", context="navigation"|"fetch")
      └ requests.Session（继承，保留全套 hooks / auth / redirect 语义）
          └ ruyihttp._transport.HTTPAdapter  （替换 urllib3 传输层）
              ├ _connect.py      TCP 连接 + 代理解析
              ├ _nss.py          ctypes 绑定 necko_tls_*（31 个 C 符号里的 TLS 组）
              ├ _http2.py        自己实现的 HTTP/2（非 h2 库直用）
              ├ _http3.py        QUIC，走 necko_quic_call
              ├ _firefox.py      请求头顺序 / UA / cookie 语义
              ├ _tls_profiles.py 100–159 的 ClientHello cluster 表
              └ _transport.py    exchange 抽象 + 重试 + 缓存
```

### 2.2 三个平台档位的差异

| | `win_amd64` | `darwin_arm64` | `linux_x86_64` |
| --- | --- | --- | --- |
| 状态 | ready | ready | ready（amd64 Ubuntu 24.04 / glibc 2.39 已实测 HTTPS） |
| NSS | 3.131 | 3.132 | 3.132 |
| Neqo | 0.32.0 | 0.33.0 | 0.33.0 |
| wheel tag | `py3-none-win_amd64` | `py3-none-macosx_26_0_arm64` | `py3-none-manylinux_2_39_x86_64` |
| 原生文件数 | 6 | 6 | 14 |
| UA | `Windows NT 10.0; Win64; x64` | `Macintosh; Intel Mac OS X 10.15` | `X11; Linux x86_64` / `aarch64` |
| 实测 | ✅ 200 / ALPN h2 / NSS 3.131 | ✅ 200 / ALPN h2 / NSS 3.132（Mac mini） | [HTTPS 200 / TLS 1.3 / h2](../projects/ruyihttp/README.md#linux-x86_64-验收记录)；QUIC 库装载与 H3 握手分别验收 |

### 2.3 TLS profile 的真实情况（重要）

`_tls_profiles.py` 第 158-166 行：

```python
PLATFORM_PROFILES = {
    "win_amd64": PROFILES,
    "darwin":    PROFILES,
    "linux":     PROFILES,
}
```

**三个平台共用同一张 cluster 表**（60 个版本 × 15 ciphers × 5 groups），注释也写明「macOS and Linux select the same clusters」，只做了 cipher/group/key-share **计数**对照，**不是字节级一致的 ClientHello**。

> 含义：Linux 版的 JA3/JA4 指纹**未必**和真 Firefox Linux 一致。这是已知缺口，记在 `04-risks-and-gaps.md`。

### 2.4 Linux 原生依赖闭包（实测）

`libnecko_core.so` 的 `DT_NEEDED`：
```
libssl3.so  libnss3.so  libnssutil3.so  libnspr4.so
libstdc++.so.6  libm.so.6  libgcc_s.so.1  libc.so.6  ld-linux-x86-64.so.2
```

版本底线（`readelf -V`）：
```
GLIBC_2.38          ← 决定性
GLIBCXX_3.4.31
CXXABI_1.3.9
```

`RUNPATH = $ORIGIN:$ORIGIN/../../../../../../../lib`，配合 `native/linux_x86_64/` 里自带的 14 个 `.so` 构成完整闭包（已核对无缺项）。

---

## 3. RuyiTrace：三层套娃

### 3.1 分层

```
┌──────────────────────────────────────────────────────────────┐
│ Electron 3.5.0（MIT）  RuyiTrace.exe 188 MB                    │
│  src/main/main.js        605 行  spawn kernel/firefox.exe      │
│  src/shared/firefox-environment.cjs  62 行  env 组装            │
│  src/shared/switches.js 175 行  74 个开关的单一真相源           │
│  src/main/codex-ipc.js  913 行  AI 对话页                      │
└───────────────────────┬──────────────────────────────────────┘
                        │ spawn + env
┌───────────────────────▼──────────────────────────────────────┐
│ 定制 Firefox 159.0  kernel/firefox.exe + kernel/xul.dll       │
│  dom/bindings/domtrace 插桩（74 个 MOZ_DOM_* env）              │
│  输出：jsonl / bin / wasm / packet                            │
└───────────────────────┬──────────────────────────────────────┘
                        │ 可选
┌───────────────────────▼──────────────────────────────────────┐
│ 内部 ruyijs wheel（资源，不参与运行时）                         │
│  resources/ruyijs/ruyijs-0.2.2+inner.20261101191032…whl        │
└──────────────────────────────────────────────────────────────┘
```

### 3.2 启动链路（实测代码）

`src/main/main.js:330-350`：
```js
launchArgs = [...proxyResult.args]              // socks5 代理参数
launchArgs = [...prepareFingerprintFile(...)]   // 指纹文件注入
const env = buildFirefoxEnvironment(process.env, switches)
for (const dir of traceOutputDirectories(switches)) fs.mkdirSync(dir, { recursive: true })
ffProc = spawn(firefoxPath, launchArgs, { env })
```

`src/shared/firefox-environment.cjs` 的逻辑是**复现 trace 的钥匙**：
1. 从父进程环境里**剔除所有** `MOZ_DOM_*`（`DOMTRACE_ENV_PATTERN = /^MOZ_DOM_/i`）
2. 写入 UI 的 switches
3. 若有任何 trace 开关，自动补 `MOZ_DOM_TRACE_RUN_ID = randomUUID()`

> 手写脚本直接 `firefox.exe` 复现一条 trace，照这三步做即可，不需要 Electron。

### 3.3 domtrace 输出契约

设 `MOZ_DOM_TRACE_FILE=D:\trace\run.jsonl` 后：

| 路径 | 内容 | 触发开关 |
| --- | --- | --- |
| `domtrace\trace_process_<pid>.jsonl` | 核心 DOM/BOM | `MOZ_DOM_TRACE=1` |
| `cookie\` / `storage\` / `eval\` / `event\` / `descriptor\` | 各 sidecar | 核心跟随 |
| `exception\trace_exception_process_<pid>.jsonl` | JS 异常 | `MOZ_DOM_EXCEPTION_TRACE` |
| `wasm\trace_wasm_process_<pid>.jsonl` + `.wasm` | WASM 边界/模块 | `MOZ_DOM_WASM_CALL` / `_DUMP` |
| `env\env_inventory_<pid>_<session>.json` | 全量接口清单（~1.2 MB） | `MOZ_DOM_ENV_INVENTORY` |
| `jscall\trace_jscall_process_<pid>.bin` + `.dict.jsonl` | 函数调用（32 字节定长记录） | `MOZ_DOM_JSCALL_TRACE` |
| `http_packet\*.http_packet.json` + `index.jsonl` | HTTP 报文 | `MOZ_DOM_HTTP_PACKET_TRACE` |
| `websocket_frames.jsonl` | WS 帧 | `MOZ_DOM_WS_TRACE` |

**四条硬规则**（cheatsheet §0.3）：
1. 必须 **Firefox 启动前**设，进程内缓存；运行中只能切 `MOZ_DOM_TRACE_GATE`
2. 附属参数不能单独启用功能
3. `MOZ_DOM_TRACE=0` **不是总关**——JSCall / HTTP packet / WebSocket / API override 独立
4. 过滤器全是逗号/分号分隔的**子串**（大小写敏感），例外：`TRACE_UNFILTER` 精确匹配、四个 JSCall URL 过滤器认 `iframe`/`web`/`*` 语义 token

### 3.4 开关数量矛盾（已实测）

| 来源 | 数量 |
| --- | --- |
| `README-cheatsheet.md` 开头自述 | 69 |
| `switches.js` 注释自述 | 67（+1 已废弃） |
| `switches.js` 实际 `SWITCHES` 数组 | **74** |
| `xul.dll` strings 里的 `MOZ_DOM_*` | **74**（与上一条完全一致） |

**原生开关清单以 `switches.js` / `xul.dll` 的 74 为准。** 另一个层次的 `MOZ_DOM_HTTP_PACKET_TRACE_MAX_PENDING` 由随包 `HttpPacketTrace.sys.mjs` 的 `getMaxPendingWrites()` 读取，控制 JS 待写队列。在原生 DLL 查不到同名字符串，不能据此判定这个 JS 配置无效。

---

## 4. 三者的交叉点：Trace 数据怎么喂回 JS 引擎

RuyiTrace 的产出（trace jsonl）有两条消费路径：

```
trace jsonl ──► jscall_decode.py ──► 函数调用树 / 值快照
            ──► trace_diff.py    ──► Firefox trace vs ruyijs trace 逐 API 行为 diff
                                      │
                                      ▼
                                ruyijs `configure_fingerprint()` /
                                `configure_environment()` /
                                `put_resource()` 的补丁参数
```

`trace_diff.py` 的 docstring 直接写明用途：

> 对每个 `(type, interface, member)` 聚合两边的「返回值形状/类型/集合」，找出 Firefox 有而 ruyijs 缺、或返回不同类型/不同类的 API —— 这些就是 CF 环境检测能看出 ruyijs 与真实 Firefox 不同的点。

**这是三件套形成闭环的设计意图**：RuyiTrace 采集真 Firefox 行为 → diff 出 ruyijs 的环境缺口 → 补 ruyijs → 用 RuyiHttp 发请求验证。

Linux 适配后这条链路应保持，只是两端都换成 Linux 二进制（见 `03-linux-port.md` §5）。

## 5. ruyi-mcp 控制面与组件边界

| 组件 | 与 ruyi-mcp 的关系 | 交接边界 |
| --- | --- | --- |
| [RuyiTrace](../projects/ruyitrace/README.md) | 直接运行集成：可使用经校验的 Firefox，也可借用 Trace 正在运行的 Firefox | 独立运行时 ruyi-mcp 管理自己的浏览器；借用时 Trace owner 独占 BiDi 和进程生命周期，MCP 通过 loopback owner IPC 与租约发出操作，经 loopback RDP 调试；Trace 负责 flush 和 DOMTrace |
| [RuyiJS](../projects/ruyijs/README.md) | 并行参考：真实浏览器脚本行为与独立 JS/DOM 运行时可做对照 | 无直接运行依赖；新对照用例显式定义 fixture、版本和结果格式 |
| [RuyiHttp](../projects/ruyihttp/README.md) | 并行参考：浏览器请求观察与独立 HTTP 客户端可比较 | 无直接运行依赖；用各自输出对比同一 fixture 的 HTTP 行为，MCP 无需加载 RuyiHttp 原生库 |

MCP 的 BiDi 事件、RDP 调试记录和内核 DOMTrace 是三种独立证据。同一用例可关联 run ID、浏览器 BuildID 与制品哈希，仍须区分各自的采集来源。Linux 真机与 Docker 的阶段边界见 [迁移路线](03-linux-port.md#6-ruyi-mcp-分阶段验收)。
