# ruyijs-inner 期望目录结构

来源依据：内部 wheel 的 `build-identity.json`（2038 条 `path + sha256`）与 `_runtime/SHA256SUMS`（1579 条）。

```
ruyijs-inner/
├── src/                              ← 反编译还原（2069 文件）
│   ├── application/
│   ├── domain/
│   ├── runtime/
│   ├── browser_environment/
│   ├── execution_scheduling/
│   ├── interaction/
│   ├── resource_network/
│   ├── document_model/
│   ├── web_canvas/
│   ├── web_graphics/
│   ├── web_geometry/
│   ├── web_media/
│   ├── web_platform/
│   ├── web_styling/
│   ├── client/
│   └── …（共 2069 文件 / 16 个一级目录）
├── python/
│   └── ruyijs/                       ← 19 个 .py（明文，从 wheel 取）
├── native/
│   ├── necko_tls/                    ← Windows C 实现
│   ├── necko_posix/                  ← Linux C++ 实现
│   └── necko_quic/                   ← 两平台 Rust
├── tests/
│   ├── contract/                     ← RPC 断言
│   └── smoke/                        ← 端到端
├── tools/
│   ├── build_linux.py
│   ├── build_windows.py
│   └── verify_structure.py           ← 用 2038 条 hash 校验还原度
└── docs/
    ├── PROVENANCE.md                 ← wheel → commit → 源码
    └── reverse-notes.md
```

## 目录来源证据

```bash
python3 - <<'PY'
import json, zipfile
from collections import Counter
z = zipfile.ZipFile('artifacts/binaries/ruyijs/ruyijs-0.2.2+inner.20261101191032-py3-none-win_amd64.whl')
bi = json.loads(z.read('ruyijs/_runtime/build-identity.json'))
paths = [i['path'] for i in bi['source_inputs']]
top = Counter(p.split('/')[1] for p in paths if p.startswith('src/'))
for k, v in sorted(top.items(), key=lambda x: -x[1]):
    print(f'{k:30s} {v}')
PY
```

## 校验方式

```bash
# 还原出文件后，用 ground truth hash 逐个比对
python3 tools/verify_structure.py \
  --identity artifacts/binaries/ruyijs/build-identity.json \
  --root src/
```

覆盖率 = 通过 hash 校验的文件数 / 2038。

## 不做的事

- 不复制 `ff-ruyijs/src/`（它是 public fork，只作对照）
- 不追求 100% 还原，按 P0–P2 范围收敛
