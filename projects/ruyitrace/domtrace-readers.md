# domtrace 读取器聚类

74 个开关的 `getenv` 调用点按地址聚类，找出共享读取函数。

## 聚类结论

| 区域 | 开关数 | 估计函数起点 | 说明 |
| --- | ---: | --- | --- |
| `0x180600000` | 40 | `0x18065fbfa` | MOZ_DOM_ABSENT_PROBE, MOZ_DOM_COOKIE_TRACE_FILE, MOZ_DOM_ENV_INVENTORY … |
| `0x185600000` | 16 | `0x18563e213` | MOZ_DOM_JSCALL_BASELINE, MOZ_DOM_JSCALL_CLOSURE_MAX_BYTES, MOZ_DOM_JSCALL_CLOSURE_URL … |
| `0x182a00000` | 11 | `0x182ad0720` | MOZ_DOM_EVENT_TRACE_FULL, MOZ_DOM_EXCEPTION_FLUSH_INTERVAL, MOZ_DOM_EXCEPTION_LIMIT … |
| `0x181c00000` | 5 | `0x181c69103` | MOZ_DOM_API_CRYPTO_RANDOM_VALUES, MOZ_DOM_API_DATE_NOW, MOZ_DOM_API_MATH_RANDOM … |
| `0x180a00000` | 2 | `0x180a96290` | MOZ_DOM_HTTP_PACKET_TRACE_DIR, MOZ_DOM_WS_MAX_BYTES |

## 各聚类成员

### `0x180600000`（40 个）

| env | getenv call | 形态 |
| --- | --- | --- |
| `MOZ_DOM_ABSENT_PROBE` | `0x18065fd3d` | r15 |
| `MOZ_DOM_COOKIE_TRACE_FILE` | `0x18065fc63` | r15 |
| `MOZ_DOM_ENV_INVENTORY` | `0x18065fd6d` | r15 |
| `MOZ_DOM_EXCEPTION_TRACE` | `0x18065fe09` | r15 |
| `MOZ_DOM_EXCEPTION_TRACE_FILE` | `0x18065fe16` | r15 |
| `MOZ_DOM_HOST_MUTATION` | `0x18065fd5e` | r15 |
| `MOZ_DOM_HTTP_PACKET_TRACE` | `0x18065fdef` | r15 |
| `MOZ_DOM_IDB_READ_VALUE` | `0x180660320` | direct |
| `MOZ_DOM_IDB_VALUE` | `0x1806602bc` | direct |
| `MOZ_DOM_IDB_VALUE_MAX_BYTES` | `0x180660361` | direct |
| `MOZ_DOM_IFACE_PROBE` | `0x18065fd4f` | r15 |
| `MOZ_DOM_JSCALL_TRACE` | `0x18065fc93` | r15 |
| `MOZ_DOM_JSCALL_TRACE_FILE` | `0x18065fca0` | r15 |
| `MOZ_DOM_STORAGE_TRACE_FILE` | `0x18065fc72` | r15 |
| `MOZ_DOM_TRACE` | `0x18065fc44` | r15 |
| `MOZ_DOM_TRACE_BUILTIN_CAP` | `0x180660129` | direct |
| `MOZ_DOM_TRACE_BUILTIN_ERROR` | `0x1806600fc` | direct |
| `MOZ_DOM_TRACE_FILE` | `0x18065fc51` | r15 |
| `MOZ_DOM_TRACE_GATE` | `0x18065ff33` | direct |
| `MOZ_DOM_TRACE_GATE_POLL_MS` | `0x18066001a` | direct |
| `MOZ_DOM_TRACE_INTERNAL` | `0x18065fddd` | r15 |
| `MOZ_DOM_TRACE_LIMIT` | `0x18065fdac` | r15 |
| `MOZ_DOM_TRACE_MAX_STRING_CHARS` | `0x180660283` | direct |
| `MOZ_DOM_TRACE_OPERATORS` | `0x18065fdb9` | r15 |
| `MOZ_DOM_TRACE_PTYPE` | `0x180660a27` | direct |
| `MOZ_DOM_TRACE_RUN_ID` | `0x18065fdcb` | r15 |
| `MOZ_DOM_TRACE_SITE_CAP` | `0x1806601ba` | direct |
| `MOZ_DOM_TRACE_UNFILTER` | `0x18065fd2b` | r15 |
| `MOZ_DOM_WASM_CALL` | `0x18065fd7c` | r15 |
| `MOZ_DOM_WASM_CALL_MAX` | `0x18065fd9a` | r15 |
| `MOZ_DOM_WASM_DUMP` | `0x18065fcb2` | r15 |
| `MOZ_DOM_WASM_DUMP_MAX` | `0x18065fcc4` | r15 |
| `MOZ_DOM_WASM_DUMP_TOTAL` | `0x18065fcd6` | r15 |
| `MOZ_DOM_WASM_INSN` | `0x18065fce8` | r15 |
| `MOZ_DOM_WASM_INSN_FUNC_INDEX` | `0x18065fcfa` | r15 |
| `MOZ_DOM_WASM_INSN_MAX_BYTES` | `0x18065fd19` | r15 |
| `MOZ_DOM_WASM_INSN_MAX_FUNCS` | `0x18065fd07` | r15 |
| `MOZ_DOM_WASM_MEM_BYTES` | `0x18065fd8b` | r15 |
| `MOZ_DOM_WASM_TRACE_FILE` | `0x18065fc81` | r15 |
| `MOZ_DOM_WS_TRACE` | `0x18065fdfc` | r15 |

### `0x185600000`（16 个）

| env | getenv call | 形态 |
| --- | --- | --- |
| `MOZ_DOM_JSCALL_BASELINE` | `0x18563e552` | direct |
| `MOZ_DOM_JSCALL_CLOSURE_MAX_BYTES` | `0x18563e799` | direct |
| `MOZ_DOM_JSCALL_CLOSURE_URL` | `0x18563e68e` | rbx |
| `MOZ_DOM_JSCALL_DETAIL_NATIVE` | `0x18563e519` | direct |
| `MOZ_DOM_JSCALL_DETAIL_SCRIPT_URL` | `0x18563e4e0` | direct |
| `MOZ_DOM_JSCALL_DURATION` | `0x18563e3ea` | direct |
| `MOZ_DOM_JSCALL_FUNC_STATS` | `0x18563e410` | direct |
| `MOZ_DOM_JSCALL_LIMIT` | `0x18563e349` | direct |
| `MOZ_DOM_JSCALL_MAX_VALUE_BYTES` | `0x18563e655` | direct |
| `MOZ_DOM_JSCALL_NATIVE` | `0x18563e5e1` | direct |
| `MOZ_DOM_JSCALL_OBJECT_FUNCS` | `0x18563e69a` | rbx |
| `MOZ_DOM_JSCALL_OBJECT_LIMIT` | `0x18563e6c3` | direct |
| `MOZ_DOM_JSCALL_PER_FUNC_LIMIT` | `0x18563e436` | direct |
| `MOZ_DOM_JSCALL_SCRIPT_URL` | `0x18563e310` | direct |
| `MOZ_DOM_JSCALL_SOURCE` | `0x18563e589` | direct |
| `MOZ_DOM_RNG_TRACE_URL` | `0x18564169f` | direct |

### `0x182a00000`（11 个）

| env | getenv call | 形态 |
| --- | --- | --- |
| `MOZ_DOM_EVENT_TRACE_FULL` | `0x182ae036b` | direct |
| `MOZ_DOM_EXCEPTION_FLUSH_INTERVAL` | `0x182ae928d` | direct |
| `MOZ_DOM_EXCEPTION_LIMIT` | `0x182ae925e` | direct |
| `MOZ_DOM_EXCEPTION_MAX_STRING_CHARS` | `0x182ae92fb` | direct |
| `MOZ_DOM_EXCEPTION_STACK_FRAMES` | `0x182ae92c3` | direct |
| `MOZ_DOM_TRACE_ASYNC` | `0x182ad076d` | direct |
| `MOZ_DOM_TRACE_SNAPSHOT` | `0x182af52d5` | direct |
| `MOZ_DOM_TRACE_SNAPSHOT_IFACES` | `0x182af52fb` | direct |
| `MOZ_DOM_TRACE_TIMERS` | `0x182af0bc3` | direct |
| `MOZ_DOM_TRACE_TIMER_LIMIT` | `0x182af0eca` | direct |
| `MOZ_DOM_WS_ASYNC` | `0x182af8f7d` | direct |

### `0x181c00000`（5 个）

| env | getenv call | 形态 |
| --- | --- | --- |
| `MOZ_DOM_API_CRYPTO_RANDOM_VALUES` | `0x181c6920b` | rbx |
| `MOZ_DOM_API_DATE_NOW` | `0x181c691b7` | rbx |
| `MOZ_DOM_API_MATH_RANDOM` | `0x181c691ed` | rbx |
| `MOZ_DOM_API_OVERRIDE` | `0x181c69188` | direct |
| `MOZ_DOM_API_PERFORMANCE_NOW` | `0x181c691d2` | rbx |

### `0x180a00000`（2 个）

| env | getenv call | 形态 |
| --- | --- | --- |
| `MOZ_DOM_HTTP_PACKET_TRACE_DIR` | `0x180a96328` | direct |
| `MOZ_DOM_WS_MAX_BYTES` | `0x180a9629b` | direct |

