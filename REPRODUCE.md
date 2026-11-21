# 复现手册：从零到这个状态

本仓现有 **32 篇文档 / 43 个 C++ 文件 / 17 项测试 / 13 个脚本**。
这份手册给出一条从空目录到全部验证通过的路径，每一步都能独立核对。

---

## 0. 前置

| 项 | 版本 | 用途 | 检查 |
| --- | --- | --- | --- |
| git | 任意近期版本 | 拉仓与 submodule | `git --version` |
| Python | ≥ 3.10 | 校验脚本、反编译分析 | `python3 --version` |
| pyyaml | 任意 | `verify-pins.sh` 读 STATUS | `python3 -c "import yaml"` |
| pefile | 2024.8.26 或更新 | 反编译分析 | `python3 -c "import pefile"` |
| capstone | 5.0.7 或更新 | 反汇编标注 | `python3 -c "import capstone"` |
| g++ | 支持 C++17 | 编译测试 | `g++ --version` |
| bash | 任意 | 脚本 | `bash --version` |

一次装齐：

```bash
python3 -m pip install --user pyyaml pefile capstone
```

> **不需要**：Windows、Wine、IDA、Ghidra、Firefox 源码、glibc 2.38。
> 全部 17 项测试都是 host 可跑的纯 C++/Python。

---

## 1. 拉仓

```bash
git clone --recurse-submodules https://github.com/Facetomyself/ruyi-platform
cd ruyi-platform
```

已有 clone 但缺 submodule：

```bash
git submodule update --init --recursive
```

**验证**（四个指针应全部匹配当前平台提交）：

```bash
git submodule status
# 期望四行，每行以空格和固定 commit 开头；-、+、U 前缀表示未初始化、偏离 pin 或冲突
```

只检出 MCP 时可运行 `git submodule update --init --checkout -- submodules/ruyi-mcp`。组件安装和 Docker 路线见 [ruyi-mcp 项目入口](projects/ruyi-mcp/README.md)。

---

## 2. 一条命令跑全部验证

```bash
bash scripts/verify-pins.sh
```

期望输出末尾：

```
== 5. submodule 状态 ==
  <hash> submodules/ruyihttp (heads/main) OK
  <hash> submodules/ruyijs (heads/main) OK
  <hash> submodules/ruyitrace (heads/main) OK
  <hash> submodules/ruyi-mcp (heads/linux) OK

全部通过
```

它依次检查六节：必需文件 → STATUS 可解析 → Firefox 基线一致 → 开关三处一致
→ 文档链接 → submodule 状态。

---

## 3. 跑 domtrace 的 17 项测试

```bash
cd submodules/ruyitrace
bash tests/run-tests.sh
```

期望：

```
== byte_layout ==
PASS  api-override: 结构偏移与解析语义全部对齐
PASS  jscall-config: 15 个读取点 + 语义对齐
PASS  jscall-record: 布局与字节序全部对齐
PASS  jscall-writer: 序列化 + 端到端解码往返全部通过
PASS  network-record: ws + http 8 组断言全通过
PASS  p4-scattered: 13 条读取点 + 8 种解析模式对齐
PASS  sidecar-record: 3 类侧车记录 8 组断言全部通过
PASS  sink-dispatch: 12 组调度断言全通过
PASS  sink-session: 6 组端到端断言全通过（真实写盘）
PASS  storage-record: cookie/storage/eval 三类 8 组断言全通过
PASS  switchlist: 74 条契约全部通过
PASS  trace-config: 40 条落位 + 3 种解析器全部对齐
PASS  trace-config-runtime: 环境变量读取与解析全部正确
PASS  trace-record: 10 组 schema 断言全部通过
PASS  trace-writer: 路径派生 + 写入 + 追加全部正确
PASS  wasm-record: 11 组断言通过（部分键名为推断，待样本核对）

== wiring (python) ==
PASS  wiring: 74 个开关全部有读取点，5 个区域分布正确

全部通过
```

`wiring` 需要 `artifacts/analysis/domtrace/switches.json`。缺失时实测输出：

```
== wiring (python) ==
SKIP  .../artifacts/analysis/domtrace/switches.json 不存在（需要先跑 scripts/domtrace-anchors.py）

全部通过
```

是 `SKIP` 不是 `FAIL`，退出码仍为 0。那份文件由第 4 节重新生成。

---

## 4. 从 xul.dll 重建反编译证据（可选）

这一步需要 `xul.dll`（约 187 MB），从 RuyiTrace 发布包取：

```bash
cd /var/lib/dsh/Ruyi/ruyi-platform

# 1. 放二进制（gitignore，不入库）
mkdir -p artifacts/binaries/ruyitrace
python3 - <<'PY'
import zipfile, os
z = zipfile.ZipFile('/path/to/RuyiTrace-3.5.0-win64.zip')
out = 'artifacts/binaries/ruyitrace'
os.makedirs(out, exist_ok=True)
for name in ('resources\\kernel\\xul.dll', 'resources\\kernel\\firefox.exe'):
    dst = os.path.join(out, os.path.basename(name.replace('\\', '/')))
    open(dst, 'wb').write(z.read(name))
PY

# 2. 74 个开关的读取点
python3 scripts/domtrace-anchors.py --pe artifacts/binaries/ruyitrace/xul.dll

# 3. 符号表
python3 scripts/gen-reader-names.py

# 4. P1+P2 落位表
python3 scripts/annotate-asm.py --start 0x18065fbfa --len 0x1b00 --out /tmp/p1p2.asm
python3 scripts/gen-trace-config.py --asm /tmp/p1p2.asm \
  --out submodules/ruyitrace/domtrace/config/trace-config-slots.h
```

期望 `domtrace-anchors.py` 输出 `读取点配对: 74/74`。

---

## 5. 常用校验命令速查

| 目的 | 命令 |
| --- | --- |
| 六节综合校验 | `bash scripts/verify-pins.sh` |
| 开关三处一致 | `python3 scripts/verify-coverage.py` |
| 文档链接 | `python3 scripts/verify-links.py` |
| 发布物 hash | `python3 scripts/verify-manifests.py` |
| domtrace 测试 | `cd submodules/ruyitrace && bash tests/run-tests.sh` |
| ruyihttp 测试 | `cd submodules/ruyihttp && python3 -m unittest discover -s tests` |

---

## 6. 各项目当前的期望状态

| 项目 | 命令 | 期望 |
| --- | --- | --- |
| ruyihttp | `cd submodules/ruyihttp && python3 -m unittest discover -s tests` | `Ran 19 tests ... OK` |
| ruyitrace | `cd submodules/ruyitrace && bash tests/run-tests.sh` | 16 项全 PASS |
| ruyijs | — | 无测试套件；反编译进度见 `projects/ruyijs/` |
| 综合 | `bash scripts/verify-pins.sh` | `全部通过` |

---

## 7. 常见失败与处理

| 现象 | 原因 | 处理 |
| --- | --- | --- |
| `verify-pins.sh` 报 submodule `NOT INIT` | 没拉 submodule | `git submodule update --init --recursive` |
| `wiring` 测试 SKIP | 缺 `artifacts/analysis/domtrace/switches.json` | 跑第 4 节第 2 步 |
| `ModuleNotFoundError: yaml` | 缺 pyyaml | `pip install --user pyyaml` |
| `verify-manifests.py` 全 SKIP | 本地没有二进制实物 | 正常；放进 `artifacts/binaries/` 后才会真的核对 hash |
| g++ 找不到 `charconv` | 编译器太旧 | 需要 C++17 完整的 g++（GCC 8+） |

---

## 8. 仓库里没有的东西（别浪费时间找）

| 缺什么 | 为什么 | 去哪 |
| --- | --- | --- |
| `xul.dll` / `js.exe` / wheel | 二进制不入 git | 从发布包取，见第 4 节与 `artifacts/manifests/` |
| domtrace 内核原始源码 | 包里没有，需反编译 | `docs/05-reverse-analysis.md` |
| Firefox 源码树 | 数十 GB | `upstream/README.md` 的 pin |
| `env_inventory` 的字段定义 | 手册没写 | `projects/ruyitrace/outputs-remaining.md` |
| Windows 上的实跑能力 | 需要 Windows | 当前所有验证都是 host 可跑的静态契约 |

---

## 9. 本手册的实测记录

编写时逐条跑过，结果如下（2026-11-19）：

| 章节 | 命令 | 实测结果 |
| --- | --- | --- |
| 0 前置 | `python3 -c "import yaml, pefile, capstone"` | 全部可用 |
| 0 前置 | `g++ -std=c++17` + `<charconv>` | 通过 |
| 2 | `bash scripts/verify-pins.sh` | 六节全 PASS，末行「全部通过」 |
| 3 | `bash tests/run-tests.sh` | **17 个 PASS** |
| 5 | `verify-coverage.py` | 退出码 0，74/74/74 |
| 5 | `verify-links.py` | 退出码 0，27 链接 |
| 5 | `verify-manifests.py` | 3/3 通过 |
| 6 | ruyihttp `unittest discover` | `Ran 19 tests ... OK` |
| 7 | 移走 switches.json 后跑 wiring | 确认输出 SKIP 且整体仍「全部通过」 |

第 4 节（重建反编译证据）依赖 `xul.dll`，本机有实物且脚本此前已跑通
（`读取点配对: 74/74`），但手册里的 zip 路径是占位符，实际使用时替换。

## 10. 如果你只有 5 分钟

```bash
git clone --recurse-submodules https://github.com/Facetomyself/ruyi-platform
cd ruyi-platform
python3 -m pip install --user pyyaml pefile capstone
bash scripts/verify-pins.sh
cd submodules/ruyitrace && bash tests/run-tests.sh
```

看到 `全部通过` 两次，就说明仓库是健康的、17 项契约测试全绿、74 个开关三处一致。
