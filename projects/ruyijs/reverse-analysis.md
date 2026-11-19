# RuyiJS 内部版反编译进度

**已有实质进展，不是从 0 开始。**

| 项 | 值 |
| --- | --- |
| 还原仓库 | `Facetomyself/ruyijs-inner`（private，2026-11-04 创建，7.4 MB） |
| 挂载 | `submodules/ruyijs` |
| 反编译对象 | `dist/js.exe` 49,569,792 B，sha256 `5fb68b22…13bcca` |
| 方案 | [`../../docs/06-ruyijs-inner.md`](../../docs/06-ruyijs-inner.md) |
| 仓库自述 | `RECOVERY.md`（该仓自有，本文件不替代它） |

---

## 1. 总体进度

identity 总基数 **2038**（来自 `build-identity.json` 的 `source_inputs`）。

| 分类 | 数量 | 说明 |
| --- | ---: | --- |
| `eol-insensitive` 对齐 0.2.1 | 1792 | 仅换行差异，正文按 0.2.1 |
| `hash_diff` | 237 | 内容与 0.2.1 不同 |
| ├ identity SHA 命中 | **56** | 工作区字节与 `build-identity.json` 一致 |
| └ 未命中 | **181** | 仍是缺口 |
| `inner_only` | 9 | inner 独有，已全部语义化 |
| ├ identity SHA 命中 | 0 | — |
| └ 语义化完成 | 9 | evidence-backed 6 / partial 3 |

**覆盖率（严格口径）**：`56 / 2038` identity 命中。剩余 1982 个是 0.2.1 正文对齐或未命中，未声称 1:1。

---

## 2. 已还原的 inner_only（9 个）

| path | 完成度 | 内容 |
| --- | --- | --- |
| `src/browser_environment/locale_platform.h` | evidence-backed | `HostOsLocale` |
| `src/browser_environment/locale_platform.cpp` | evidence-backed | `GetUserDefaultLocaleName` + wchar narrow |
| `src/domain/styling/css_color_space.h` | evidence-backed | tag 0..14 签名 |
| `src/domain/styling/css_color_space.cpp` | evidence-backed | `ToSrgb` switch |
| `src/web_geometry/local_fonts.h` | evidence-backed | `LocalFontFamilyInstalled` |
| `src/web_geometry/local_fonts.cpp` | evidence-backed | DWrite 缓存 |
| `src/web_graphics/framebuffer_storage.cpp` | partial | 状态码/attach 有证据；尺寸表未定位 |
| `src/web_graphics/glsl_exec.cpp` | partial | atom/product/sum/ctor/swizzle |
| `src/web_trusted_types/enforcement.cpp` | partial | CreatePolicy CSP 门控 |

---

## 2.5 operation 全集与 js.exe 锚点（新增，2026-11-19）

### operation 全集（已枚举）

从 19 个 `.py` 提取：**37 个一级 operation + 2 个 page action**。

| 文件 | 数量 | 列表 |
| --- | ---: | --- |
| `_scheduling.py` | 14 | `advance` `configure` `configure_message_replay` `configure_navigation_replay` `configure_timer_replay` `drain` `event_loop` `navigation_replay_status` `pending_messages` `pending_timers` `run_message` `run_timer` `status` `timer_realm` |
| `_context.py` | 8 | `checkpoint` `close` `collect` `expose` `expose_data` `native` `page` `set` |
| `_resources.py` | 7 | `clear` `cookies` `get` `log` `put` `resource` `status` |
| `_inspector.py` | 4 | `api_log` `clear` `get` `peek` |
| `_context_eval.py` | 3 | `eval` `host_value` `locals` |
| `_random.py` | 3 | `configure_crypto_replay` `configure_random` `crypto_replay_status` |
| `_environment.py` | 2 | `configure` `defaults` |
| `_input.py` | 2 | `input` `user` |
| `_console.py` | 1 | `console` |
| page action | 2 | `load` `navigate` |

产物：`artifacts/analysis/ruyijs/operations.json`

### ~~关键发现：7 个 operation 在 js.exe 里不存在~~ → **已推翻**

**上一轮判断错了。** 这 7 个 operation **全部存在于二进制里**，只是编码形式不同：
编译期把 `if (op == "run_timer")` 优化成立即数异或比较，不在 `.rdata` 留独立
NUL 结尾字符串；部分走 16 路跳转表 + SSE `pcmpeqb`。

详见 [`operation-dispatch.md`](operation-dispatch.md)。

**扫描结果**（`scripts/ruyijs-ops-scan.py`）：

```
operation 总数: 39
  字符串池命中: 15
  立即数命中:   31
  合计定位:     37/39
  仍缺失: ['drain', 'put']
```

### 上一轮 32/39 是子串误报

| operation | 实际命中的上下文 | 是否 operation |
| --- | --- | --- |
| `advance` | `confirmCurrentadvancesharing…` | ✗ 子串 |
| `status` | `countryregioncommonstatusevents…` | ✗ 子串 |
| `drain` | `ondrain` | ✗ 子串 |
| `event_loop` | `event_loop field must be a finite number` | ✗ 错误消息 |
| `run_message` | 独立字符串池 | ✓ 真命中 |

真实的独立字符串只有 15 个，不是 32 个。

### 仍然缺失的 2 个

| operation | 来源 | 状态 |
| --- | --- | --- |
| `drain` | `_scheduling.py` | To be confirmed（4 字符，可能内联为 imm32） |
| `put` | `_resources.py` | To be confirmed（3 字符，低于 imm32 粒度） |

---

## 3. hash_diff 中已抬出的独特控制流

这些不是 identity 命中，是 dump 得到的行为细节（**有价值但不可声称等价**）：

| 文件 | 发现 |
| --- | --- |
| `font_face.cpp` | CSS `src` comma-split / local-url / `ParseLocalName` + `ConsumeIdent` |
| `node_receiver.cpp` | kind-iface `BrandText` |
| `page_storage.cpp` | `Storage.key` 用 `JS::ToUint32` |
| `web_audio/render.cpp` | `AudioBufferSource` 每 quantum 复制 128 frames |
| `web_console/render.cpp` | `%s/%d/%i/%f/%o/%O/%c/%%` Join |
| `http_exchange.h` | 20e9 ns / 20000 ms QPC 超时常量 |
| `css_color_resolve.cpp` | lab/oklab/lch/oklch/hwb/`color()`（无 color-mix） |
| `css_color_value.cpp` | color-mix 104 字 `CssSplit`；color() 94 字含 `display-p3-linear` |
| `web_kit.cpp` | ConstructProto 报 `"Illegal "`（不是 `"Illegal constructor."`） |
| `model_internal.h` | Protect catch 只回 ErrorCode |
| `box_input.cpp` / `box_layout.h` | `LayoutVisit 0x1406CF4B0` 在 img/video 且宽高均 >0 时写 `replaced_aspect=w/h` |
| `box_layout.cpp` | `Place 0x140544630` 按 `replaced_aspect>0` 用 BoxRound 耦合缺失边，缺省 300×150 |

---

## 4. `src/client/*`（来自 `ruyijs_client.dll`）

| 项 | 还原情况 |
| --- | --- |
| 导出 | C 导出 |
| 帧上限 | 16 MiB |
| `callback_active` | `-2` |
| 关闭协议 | close JSON |
| 传输 | Win32 named-pipe |
| `lifecycle.cpp` / `ruyijs.h` | identity 命中 |
| `sizeof(ruyijs_context)` | **不是** dump 的 `0x78`（未解决） |
| `transport.cpp` | dump 有保护，未用 OSS 冲掉 memcmp/len==0 |

---

## 5. 最大缺口（181 个未命中）

| 模块 | 状态 |
| --- | --- |
| `page_storage` | 缺口最大 |
| `browsing_context` | 缺口 |
| `draw` | 缺口 |
| `css_color_resolve` | 缺口 |

**已穷尽手段**：独特 ASCII / UTF-16 / RTTI 针。无独特串的 TU 仍是 `unknown` / `partial`。

---

## 6. 不能声称的事（照抄还原仓的自我约束）

- 与 wheel 内 `js.exe` 全部功能/行为等价
- 剩余差异只是编译器结构差
- 用本树重编即可得到同一 `js.exe` / 同一 `build-identity.json` 哈希
- 全 API L3 parity

**本仓立场**：这些约束继续有效，`docs/06-ruyijs-inner.md` 的验收标准以行为断言为准，不以 identity 命中率代替。

---

## 7. 下一步优先级

| 优先级 | 动作 | 依据 |
| --- | --- | --- |
| P0 | 补 181 个未命中里的高价值模块：`page_storage` / `browsing_context` | 缺口最大 |
| P1 | `src/client/*` 的 `sizeof(ruyijs_context)` 与 `transport.cpp` | 服务端集成必需 |
| P2 | Linux 构建验证：`native/` 与 `python/` 的跨平台分支 | 见 `docs/03-linux-port.md` L2 |
| P3 | 行为断言集（`docs/06-ruyijs-inner.md` §4）落到 `tests/contract/` | 验收标准 |

---

## 8. 与 ff-ruyijs 的关系

`ruyijs-inner` 的 seed 是 `ff-ruyijs` **0.2.1**（`c69875b5`），不是当前的 `3501a90`（0.4.1）。

差异后果：

- 0.2.1 没有跨平台代码（`_pipe.py` 是 Windows 独占）
- 0.4.1 的 `_pipe.py` 208 行含 AF_UNIX——**这是内部版要做的事，不是已完成的事**

详见 [`../../docs/06-ruyijs-inner.md`](../../docs/06-ruyijs-inner.md) §0 与 ADR 0002。
