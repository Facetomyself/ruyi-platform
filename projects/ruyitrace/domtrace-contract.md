# domtrace 契约主表（74 开关）

生成方式：`scripts/domtrace-anchors.py` 从 `xul.dll` 提取读取点，与 `console/shared/switches.js` 合并。

- PE image base: `0x180000000`
- `getenv` IAT RVA: `0xa185ad0`
- 开关字符串: **74**，`lea` 引用 **104** 条
- `getenv` 调用点: **15816** `{'rsi': 5192, 'rbx': 3730, 'r15': 6147, 'rax': 249, 'rcx': 161, 'rdx': 163, 'direct': 174}`
- **读取点配对: 74/74**

## 状态图例

| 状态 | 含义 |
| --- | --- |
| `located` | 字符串 RVA + lea 引用 + getenv 调用点均已确定 |
| `reconstructed` | 已写出等价伪代码 |
| `verified` | 行为断言通过 |

## 主表

| # | env | kind | default | group | string RVA | getenv call | 形态 | 间隔 | 状态 |
| ---: | --- | --- | --- | --- | --- | --- | --- | ---: | --- |
| 1 | `MOZ_DOM_API_CRYPTO_RANDOM_VALUES` | text | — | API 定制 / 随机数劫持 | `0x189f33a37` | `0x181c6920b` | rbx | 7 | located |
| 2 | `MOZ_DOM_API_DATE_NOW` | text | — | API 定制 / 随机数劫持 | `0x189f2a7db` | `0x181c691b7` | rbx | 14 | located |
| 3 | `MOZ_DOM_API_MATH_RANDOM` | text | — | API 定制 / 随机数劫持 | `0x189f3ef47` | `0x181c691ed` | rbx | 7 | located |
| 4 | `MOZ_DOM_API_OVERRIDE` | tristate | — | API 定制 / 随机数劫持 | `0x189f4d118` | `0x181c69188` | direct | 7 | located |
| 5 | `MOZ_DOM_API_PERFORMANCE_NOW` | text | — | API 定制 / 随机数劫持 | `0x189f2a7f0` | `0x181c691d2` | rbx | 7 | located |
| 6 | `MOZ_DOM_HTTP_PACKET_TRACE` | tristate | — | HTTP / WebSocket | `0x189f4d542` | `0x18065fdef` | r15 | 7 | located |
| 7 | `MOZ_DOM_HTTP_PACKET_TRACE_DIR` | dir | — | HTTP / WebSocket | `0x189f36e8b` | `0x180a96328` | direct | 7 | located |
| 8 | `MOZ_DOM_WS_ASYNC` | default_on | — | HTTP / WebSocket | `0x189f57bdd` | `0x182af8f7d` | direct | 7 | located |
| 9 | `MOZ_DOM_WS_MAX_BYTES` | int | 65536 | HTTP / WebSocket | `0x189f33aaa` | `0x180a9629b` | direct | 7 | located |
| 10 | `MOZ_DOM_WS_TRACE` | tristate | — | HTTP / WebSocket | `0x189f4d55c` | `0x18065fdfc` | r15 | 7 | located |
| 11 | `MOZ_DOM_WASM_CALL` | bool | — | WASM | `0x189f40d64` | `0x18065fd7c` | r15 | 7 | located |
| 12 | `MOZ_DOM_WASM_CALL_MAX` | int | 0 | WASM | `0x189f29a03` | `0x18065fd9a` | r15 | 7 | located |
| 13 | `MOZ_DOM_WASM_DUMP` | bool | — | WASM | `0x189f3a011` | `0x18065fcb2` | r15 | 7 | located |
| 14 | `MOZ_DOM_WASM_DUMP_MAX` | int | 268435456 | WASM | `0x189f299d6` | `0x18065fcc4` | r15 | 7 | located |
| 15 | `MOZ_DOM_WASM_DUMP_TOTAL` | int | 2147483648 | WASM | `0x189f421f8` | `0x18065fcd6` | r15 | 7 | located |
| 16 | `MOZ_DOM_WASM_INSN` | bool | — | WASM | `0x189f3bdda` | `0x18065fce8` | r15 | 7 | located |
| 17 | `MOZ_DOM_WASM_INSN_FUNC_INDEX` | int | -1 | WASM | `0x189f2978b` | `0x18065fcfa` | r15 | 7 | located |
| 18 | `MOZ_DOM_WASM_INSN_MAX_BYTES` | int | 1048576 | WASM | `0x189f33abf` | `0x18065fd19` | r15 | 7 | located |
| 19 | `MOZ_DOM_WASM_INSN_MAX_FUNCS` | int | 0 | WASM | `0x189f34868` | `0x18065fd07` | r15 | 7 | located |
| 20 | `MOZ_DOM_WASM_MEM_BYTES` | int | 256 | WASM | `0x189f33b18` | `0x18065fd8b` | r15 | 7 | located |
| 21 | `MOZ_DOM_EXCEPTION_FLUSH_INTERVAL` | int | 256 | exception | `0x189f4217a` | `0x182ae928d` | direct | 7 | located |
| 22 | `MOZ_DOM_EXCEPTION_LIMIT` | int | 50000 | exception | `0x189f2f272` | `0x182ae925e` | direct | 7 | located |
| 23 | `MOZ_DOM_EXCEPTION_MAX_STRING_CHARS` | int | 4096 | exception | `0x189f31ec9` | `0x182ae92fb` | direct | 7 | located |
| 24 | `MOZ_DOM_EXCEPTION_STACK_FRAMES` | int | 8 | exception | `0x189f342b2` | `0x182ae92c3` | direct | 7 | located |
| 25 | `MOZ_DOM_EXCEPTION_TRACE` | tristate | — | exception | `0x189f4d56d` | `0x18065fe09` | r15 | 7 | located |
| 26 | `MOZ_DOM_EXCEPTION_TRACE_FILE` | path | — | exception | `0x189f4ad33` | `0x18065fe16` | r15 | 7 | located |
| 27 | `MOZ_DOM_JSCALL_BASELINE` | bool | — | jscall | `0x189f4a054` | `0x18563e552` | direct | 7 | located |
| 28 | `MOZ_DOM_JSCALL_CLOSURE_MAX_BYTES` | int | 262144 | jscall | `0x189f33af7` | `0x18563e799` | direct | 7 | located |
| 29 | `MOZ_DOM_JSCALL_CLOSURE_URL` | csv | — | jscall | `0x189f4018d` | `0x18563e68e` | rbx | 7 | located |
| 30 | `MOZ_DOM_JSCALL_DETAIL_NATIVE` | csv | — | jscall | `0x189f4794a` | `0x18563e519` | direct | 7 | located |
| 31 | `MOZ_DOM_JSCALL_DETAIL_SCRIPT_URL` | csv | — | jscall | `0x189f400ce` | `0x18563e4e0` | direct | 7 | located |
| 32 | `MOZ_DOM_JSCALL_DURATION` | default_on | — | jscall | `0x189f3d428` | `0x18563e3ea` | direct | 7 | located |
| 33 | `MOZ_DOM_JSCALL_FUNC_STATS` | default_on | — | jscall | `0x189f31603` | `0x18563e410` | direct | 7 | located |
| 34 | `MOZ_DOM_JSCALL_LIMIT` | int | 0 | jscall | `0x189f2f28a` | `0x18563e349` | direct | 7 | located |
| 35 | `MOZ_DOM_JSCALL_MAX_VALUE_BYTES` | int | 65536 | jscall | `0x189f33b2f` | `0x18563e655` | direct | 7 | located |
| 36 | `MOZ_DOM_JSCALL_NATIVE` | bool | — | jscall | `0x189f47934` | `0x18563e5e1` | direct | 7 | located |
| 37 | `MOZ_DOM_JSCALL_OBJECT_FUNCS` | csv | — | jscall | `0x189f34892` | `0x18563e69a` | rbx | 7 | located |
| 38 | `MOZ_DOM_JSCALL_OBJECT_LIMIT` | int | 64 | jscall | `0x189f2f1d3` | `0x18563e6c3` | direct | 7 | located |
| 39 | `MOZ_DOM_JSCALL_PER_FUNC_LIMIT` | int | 0 | jscall | `0x189f2f2c8` | `0x18563e436` | direct | 7 | located |
| 40 | `MOZ_DOM_JSCALL_SCRIPT_URL` | csv | — | jscall | `0x189f400b4` | `0x18563e310` | direct | 7 | located |
| 41 | `MOZ_DOM_JSCALL_SOURCE` | enum_free | — | jscall | `0x189f4d2e0` | `0x18563e589` | direct | 7 | located |
| 42 | `MOZ_DOM_JSCALL_TRACE` | bool | — | jscall | `0x189f4d593` | `0x18065fc93` | r15 | 7 | located |
| 43 | `MOZ_DOM_JSCALL_TRACE_FILE` | path | — | jscall | `0x189f4ad7b` | `0x18065fca0` | r15 | 7 | located |
| 44 | `MOZ_DOM_COOKIE_TRACE_FILE` | path | — | 总开关与输出 | `0x189f4ad95` | `0x18065fc63` | r15 | 7 | located |
| 45 | `MOZ_DOM_EVENT_TRACE_FULL` | bool | — | 总开关与输出 | `0x189f40b5c` | `0x182ae036b` | direct | 7 | located |
| 46 | `MOZ_DOM_IDB_READ_VALUE` | bool | — | 总开关与输出 | `0x189f47f0c` | `0x180660320` | direct | 7 | located |
| 47 | `MOZ_DOM_IDB_VALUE` | bool | — | 总开关与输出 | `0x189f47f53` | `0x1806602bc` | direct | 7 | located |
| 48 | `MOZ_DOM_IDB_VALUE_MAX_BYTES` | int | 8192 | 总开关与输出 | `0x189f33adb` | `0x180660361` | direct | 7 | located |
| 49 | `MOZ_DOM_STORAGE_TRACE_FILE` | path | — | 总开关与输出 | `0x189f4adaf` | `0x18065fc72` | r15 | 7 | located |
| 50 | `MOZ_DOM_TRACE` | tristate | — | 总开关与输出 | `0x189f4d585` | `0x18065fc44` | r15 | 14 | located |
| 51 | `MOZ_DOM_TRACE_ASYNC` | default_on | — | 总开关与输出 | `0x189f57c26` | `0x182ad076d` | direct | 7 | located |
| 52 | `MOZ_DOM_TRACE_BUILTIN_CAP` | int | 64 | 总开关与输出 | `0x189f3a8d9` | `0x180660129` | direct | 7 | located |
| 53 | `MOZ_DOM_TRACE_BUILTIN_ERROR` | bool | — | 总开关与输出 | `0x189f366a5` | `0x1806600fc` | direct | 7 | located |
| 54 | `MOZ_DOM_TRACE_FILE` | path | — | 总开关与输出 | `0x189f4ad68` | `0x18065fc51` | r15 | 7 | located |
| 55 | `MOZ_DOM_TRACE_GATE` | path | — | 总开关与输出 | `0x189f48700` | `0x18065ff33` | direct | 7 | located |
| 56 | `MOZ_DOM_TRACE_GATE_POLL_MS` | int | 200 | 总开关与输出 | `0x189f32caa` | `0x18066001a` | direct | 7 | located |
| 57 | `MOZ_DOM_TRACE_INTERNAL` | bool | — | 总开关与输出 | `0x189f423a2` | `0x18065fddd` | r15 | 7 | located |
| 58 | `MOZ_DOM_TRACE_LIMIT` | int | 0 | 总开关与输出 | `0x189f2f2b4` | `0x18065fdac` | r15 | 7 | located |
| 59 | `MOZ_DOM_TRACE_MAX_STRING_CHARS` | int | 512 | 总开关与输出 | `0x189f31eec` | `0x180660283` | direct | 7 | located |
| 60 | `MOZ_DOM_TRACE_OPERATORS` | default_on | — | 总开关与输出 | `0x189f31cd4` | `0x18065fdb9` | r15 | 7 | located |
| 61 | `MOZ_DOM_TRACE_PTYPE` | enum_free | parent | 总开关与输出 | `0x189f49b82` | `0x180660a27` | direct | 7 | located |
| 62 | `MOZ_DOM_TRACE_RUN_ID` | text | — | 总开关与输出 | `0x189f5110c` | `0x18065fdcb` | r15 | 7 | located |
| 63 | `MOZ_DOM_TRACE_SITE_CAP` | int | 4096 | 总开关与输出 | `0x189f3a8f3` | `0x1806601ba` | direct | 7 | located |
| 64 | `MOZ_DOM_WASM_TRACE_FILE` | path | — | 总开关与输出 | `0x189f4ad50` | `0x18065fc81` | r15 | 7 | located |
| 65 | `MOZ_DOM_ABSENT_PROBE` | bool | — | 补环境探测 | `0x189f4d827` | `0x18065fd3d` | r15 | 7 | located |
| 66 | `MOZ_DOM_ENV_INVENTORY` | bool | — | 补环境探测 | `0x189f2768e` | `0x18065fd6d` | r15 | 7 | located |
| 67 | `MOZ_DOM_HOST_MUTATION` | bool | — | 补环境探测 | `0x189f3d204` | `0x18065fd5e` | r15 | 7 | located |
| 68 | `MOZ_DOM_IFACE_PROBE` | bool | — | 补环境探测 | `0x189f4d83c` | `0x18065fd4f` | r15 | 7 | located |
| 69 | `MOZ_DOM_RNG_TRACE_URL` | csv | — | 补环境探测 | `0x189f401cf` | `0x18564169f` | direct | 7 | located |
| 70 | `MOZ_DOM_TRACE_SNAPSHOT` | default_on | — | 补环境探测 | `0x189f2e250` | `0x182af52d5` | direct | 7 | located |
| 71 | `MOZ_DOM_TRACE_SNAPSHOT_IFACES` | csv | — | 补环境探测 | `0x189f345f5` | `0x182af52fb` | direct | 7 | located |
| 72 | `MOZ_DOM_TRACE_TIMERS` | bool | — | 补环境探测 | `0x189f31def` | `0x182af0bc3` | direct | 7 | located |
| 73 | `MOZ_DOM_TRACE_TIMER_LIMIT` | int | 16384 | 补环境探测 | `0x189f2f1ef` | `0x182af0eca` | direct | 7 | located |
| 74 | `MOZ_DOM_TRACE_UNFILTER` | csv | — | 补环境探测 | `0x189f379bb` | `0x18065fd2b` | r15 | 7 | located |

## 按组汇总

| 组 | 数量 |
| --- | ---: |
| 总开关与输出 | 21 |
| jscall | 17 |
| 补环境探测 | 10 |
| WASM | 10 |
| exception | 6 |
| API 定制 / 随机数劫持 | 5 |
| HTTP / WebSocket | 5 |

## `getenv` 调用点形态分布

| 形态 | 数量 | 说明 |
| --- | ---: | --- |
| `direct` | 174 | `call qword ptr [rip+getenv_IAT]` |
| `r15` | 6147 | `call r15`，该寄存器预先载入 `getenv` |
| `rbx` | 3730 | `call rbx`，该寄存器预先载入 `getenv` |
| `rsi` | 5192 | `call rsi`，该寄存器预先载入 `getenv` |
| `rax` | 249 | `call rax`，该寄存器预先载入 `getenv` |
| `rcx` | 161 | `call rcx`，该寄存器预先载入 `getenv` |
| `rdx` | 163 | `call rdx`，该寄存器预先载入 `getenv` |

> 未配对的 0 条：全部 74 个开关都在 `lea` 之后 16 字节内找到 `getenv` 调用。
