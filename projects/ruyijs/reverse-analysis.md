# RuyiJS 内部版反编译进度

方案：[`../../docs/06-ruyijs-inner.md`](../../docs/06-ruyijs-inner.md)
对象：`ruyijs/_runtime/dist/js.exe`，49,569,792 B

---

## 1. 契约提取（第一步）

### 1.1 operation 全集

从 19 个 `.py` 枚举 RPC 名称。**状态：未开始。**

```bash
python3 - <<'PY'
import zipfile, re, json
z = zipfile.ZipFile('artifacts/binaries/ruyijs/ruyijs-0.2.2+inner.20261101191032-py3-none-win_amd64.whl')
ops = set()
for n in z.namelist():
    if n.startswith('ruyijs/') and n.endswith('.py') and n.count('/') == 1:
        src = z.read(n).decode('utf-8')
        for m in re.finditer(r'_request\(\s*"([a-z_]+)"', src):
            ops.add(m.group(1))
json.dump(sorted(ops), open('artifacts/analysis/ruyijs/operations.json', 'w'), indent=1)
print(len(ops), '个 operation')
PY
```

### 1.2 已知来源

| 文件 | 提供什么 |
| --- | --- |
| `_context_eval.py` | `eval` / `locals` |
| `_context.py` | `load_page` / `navigate` / `set` / `expose` / `native` / `checkpoint` / `collect_garbage` |
| `_environment.py` | `configure_fingerprint` / `configure_environment` / `get_defaults` |
| `_scheduling.py` | 15 个时钟与定时器操作 |
| `_resources.py` | `put_resource` / `get_resource` / `net_log` / `export_cookies` / `cookie_header` / `resource_status` / `clear_resources` |
| `_inspector.py` | `peek_api_log` / `get_api_log` / `clear_api_log` |
| `_input.py` | `dispatch_input` / `click` / `type` / `press` |

---

## 2. 符号定位（第二步）

**状态：0/74。**

锚点工具：

```bash
python3 scripts/reverse-anchors.py \
  --pe artifacts/binaries/ruyijs/js.exe \
  --strings-file artifacts/analysis/ruyijs/operations.txt \
  --out artifacts/analysis/ruyijs/anchors.json
```

定位表（逐步填写）：

| operation | 二进制字符串 | RVA | 引用点 | handler 入口 | 状态 |
| --- | --- | --- | --- | --- | --- |
| `eval` | To be confirmed | — | — | — | 未开始 |
| `load_page` | To be confirmed | — | — | — | 未开始 |
| `advance` | To be confirmed | — | — | — | 未开始 |

---

## 3. 语义重建（第三步）

### 3.1 ground truth

`build-identity.json` 的 `source_inputs` 给了 **2038 条** `path + sha256`：

```bash
python3 - <<'PY'
import json, zipfile
z = zipfile.ZipFile('artifacts/binaries/ruyijs/ruyijs-0.2.2+inner.20261101191032-py3-none-win_amd64.whl')
bi = json.loads(z.read('ruyijs/_runtime/build-identity.json'))
paths = sorted({i['path'] for i in bi['source_inputs']})
print(f'{len(paths)} 个源文件')
from collections import Counter
top = Counter(p.split('/')[1] for p in paths if p.startswith('src/'))
for k, v in top.most_common(): print(f'  src/{k:30s} {v}')
PY
```

还原出的每个文件可以用 sha256 反查是否正确——**这是反编译里罕见的可验证性**。

### 3.2 符号命名表

| 二进制形态 | 命名 | 例 |
| --- | --- | --- |
| RPC 分发器 | `Dispatch<Layer>` | `DispatchEvaluation` |
| 单个 handler | `Handle<Operation>` | `HandleEval` |
| 值编解码 | `Encode<Type>` / `Decode<Type>` | `EncodeJSObject` |
| 管道帧 | `Frame<Direction>` | `FrameRead` |

---

## 4. 交叉验证（第四步）

**状态：0/N 断言。**

| # | 断言 | 状态 |
| --- | --- | --- |
| 1 | `Context().eval("1+1") == 2` | 待跑 |
| 2 | `eval("undefined") is UNDEFINED` | 待跑 |
| 3 | `set()` 后 `eval` 能读到 | 待跑 |
| 4 | `expose()` 的 Python 函数可从 JS 调用 | 待跑 |
| 5 | 逻辑时钟 `advance(10)` 触发 `setTimeout` | 待跑 |
| 6 | 帧长度前缀为 4 字节小端 | 待跑 |

---

## 5. 与 ff-ruyijs 的对照记录

**纪律**：每条标注「参照，未采用」或「与二进制一致，采用」。详见 `docs/06-ruyijs-inner.md` §5。

| operation | 二进制行为（实测） | ff-ruyijs 参照（`3501a90`） | 结论 |
| --- | --- | --- | --- |
| To be filled | — | — | — |
