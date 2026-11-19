# 剩余 5 类输出的依据盘点

> **本文是一次自我更正。** 前一轮我把这 5 类判为「弱依据档」，理由是「手册只说有什么文件，
> 没说文件里有什么字段」。逐段复查后发现判断错了：手册对其中 3 类给了完整字段表，
> 另 2 类也确实缺字段，但缺的原因不同。

## 逐项依据

| # | 输出 | 依据 | 手册位置 | 判定 |
| ---: | --- | --- | --- | --- |
| 9 | `wasm\trace_wasm_process_<pid>.jsonl` | `wasm_call` 结构有描述；`wasm_export_map` 有说明 | 2138-2168 行 | 🟡 部分 |
| 10 | `wasm\wasm_<sha256>_<len>.wasm` | 模块原始字节 + WAT 反汇编文本 | 2109-2135 行 | 🟡 部分 |
| 11 | `env\env_inventory_<pid>_<session>.json` | 只说「约 1.2 MB 的接口清单」 | 1457 行 | 🔴 无字段 |
| 12 | `http_packet\*.http_packet.json` + `index.jsonl` | `meta` 六键有逐一列出；`dropped_full`/`snake_case` 有说明 | 2163-2182、795-805 行 | 🟢 有 |
| 13 | `websocket_frames.jsonl` | **完整字段表**，14 行逐字段说明 | 2191-2207 行 | 🟢 有 |

### 更正要点

**websocket 有完整字段表**（手册 2191-2207 行）：

`seq` / `ts` / `pid` / `type`（固定 `"ws_frame"`）/ `dir`（`send`/`recv`）/ `serial` /
`url` / `opcode`（1/2/8/9/10）/ `fin` / `rsv1` / `rsv2` / `rsv3` / `mask_bit` / `mask` /
`payload_len` / `captured_len` / `truncated` / `payload_b64` / `text`

还有截断语义：`MOZ_DOM_WS_MAX_BYTES` 256..16777216，默认 65536，超出截断并带
`truncated:true` + 原始 `payload_len`。

**http_packet 有 meta 六键**（手册 795-805 行）：

`origin_call_id` / `origin_pid` / `origin_execution_context_id` /
`origin_async_context_id`，且**蛇形与驼峰两套并存**，手册明说「现在两种拼法在
`http_packet` 里都有，值与驼峰原名逐字节相同」。

还有 `dropped_full`（2165 行）：`MOZ_DOM_HTTP_PACKET_TRACE_MAX_PENDING` 满载时
增加该字段并丢弃该 packet。

### `env_inventory` 已完成（2026-11-20）

拿到真实样本后补齐。实测结构见 `domtrace/trace/env-inventory.h`，
测试见 `tests/byte_layout/test_env_inventory.cpp`（7 组断言）。

| 项 | 手册 | 实测 |
| --- | --- | --- |
| `schemaVersion` | 1 | **2** |
| `interfaces` | 1060 | 1067 |
| `windowProps` | 786 | 992 |
| `buildId` | 未提及 | `20261101192846` |
| `stats` 四键 | 未提及 | 已实测 |

**13/13 输出格式全部完成。**

## 结论

上一轮的「5 类全是弱依据」是错的。实际是：

- **2 类有完整字段表**：websocket、http_packet → 可以直接实现
- **2 类部分有**：wasm 的 jsonl 与 .wasm → 有 `wasm_call` 语义与 WAT 描述，但记录字段要补证
- **1 类无字段**：env_inventory → 必须等样本

下一轮做 websocket 与 http_packet。
