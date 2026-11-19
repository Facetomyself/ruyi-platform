# scripts

| 脚本 | 用途 | 依赖 |
| --- | --- | --- |
| `verify-pins.sh` | 校验 PINS.md / STATUS.yaml / submodule 一致性 | bash, python3, pyyaml |
| `verify-links.py` | 校验 Markdown 内部链接 | python3 |
| `verify-manifests.py` | 校验发布物 manifest 与实物 hash | python3, pyyaml |
| `domtrace-anchors.py` | **从 xul.dll 提取 74 个 MOZ_DOM_* 读取点** | python3, pefile |
| `reverse-anchors.py` | PE 字符串锚点通用提取 | python3, pefile |
| `sync-submodules.sh` | 初始化/更新 submodule | bash, git |

## 安装依赖

```bash
python3 -m pip install --user pefile capstone pyyaml
```

## domtrace-anchors.py

```bash
python3 scripts/domtrace-anchors.py --pe artifacts/binaries/ruyitrace/xul.dll
```

输出 `artifacts/analysis/domtrace/switches.json`，含每个开关的：
字符串 RVA、lea 引用、getenv 调用点、调用形态（direct/r15/rbx/rsi/…）、字节间隔。

实测：74 字符串 → 104 条 lea → 15816 个 getenv 调用点 → **74/74 配对**。

耗时约 40 秒（8 亿字节 .text 全扫）。
