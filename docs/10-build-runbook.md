# 构建机到位后的执行清单

前提：有了一台 **x86_64 + 16 GB 内存 + 60 GB 磁盘 + glibc 2.38+** 的机器。
本文是拿到机器后的完整步骤，每步都有验证点。

> 本文未在真实环境跑过。步骤依据是官方 159 源码与 ff-ruyijs 的构建脚本，
> 但**没有一次完整的端到端执行记录**。执行时按验证点逐段确认。

---

## 阶段 0 · 环境准备（约 30 分钟）

### 0.1 装依赖

```bash
sudo apt-get update
sudo apt-get install -y \
  build-essential libx11-xcb-dev libdbus-glib-1-dev libgtk-3-dev \
  libpango1.0-dev libxt-dev libasound2-dev libcurl4-openssl-dev \
  python3-dev python3-pip python3-venv libssl-dev zlib1g-dev \
  autoconf2.13 clang llvm libclang-dev \
  git curl wget cmake ninja-build
```

Rust（Neqo 需要）：

```bash
curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh -s -- -y
source "$HOME/.cargo/env"
```

**验证点**：
```bash
clang --version    # ≥ 16
rustc --version    # ≥ 1.75
python3 --version  # ≥ 3.10
ldd --version | head -1   # ≥ 2.38
nproc && free -g | head -2 && df -h /  # 16核/16G/60G+
```

---

## 阶段 1 · 拉源码（约 20 分钟，8 GB）

```bash
mkdir -p ~/build && cd ~/build
git clone --depth 1 --filter=blob:none --sparse \
  https://github.com/mozilla-firefox/firefox ff159
cd ff159
git fetch --depth 1 origin 9a2dc53c369c7ae5172018b35988e1d2ffeff402
git checkout 9a2dc53c369c7ae5172018b35988e1d2ffeff402
git sparse-checkout set --no-cone \
  '/*' '!/testing' '!/js/src/tests' '!/dom/media/test'
```

**验证点**：
```bash
git log -1 --format=%H    # 9a2dc53c369c7ae5172018b35988e1d2ffeff402
du -sh .                   # 约 8 GB
```

> 若 sparse 范围导致 `mach build` 缺文件，回到完整 clone：
> `git sparse-checkout disable`

---

## 阶段 2 · 应用 domtrace 补丁（约 10 分钟）

```bash
cd ~/build/ff159

# 五个补丁，严格按序
P=/path/to/ruyi-platform/submodules/ruyitrace/domtrace/patches
for f in 0001-codegen-prototype-name \
         0002-codegen-jitinfo-name-table \
         0004-codegen-member-name-table \
         0005-codegen-member-range-table \
         0003-bindingutils-instrument; do
  git apply --check "$P/$f.patch" || { echo "FAILED: $f"; exit 1; }
  git apply "$P/$f.patch"
done

# domtrace 运行时实现放进源码树
cp -r /path/to/ruyi-platform/submodules/ruyitrace/domtrace dom/domtrace
cp dom/domtrace/binding/DOMTraceJitInfoNames.h dom/bindings/
```

**验证点**：
```bash
git diff --stat
#  dom/bindings/BindingUtils.cpp | 15 +++++++++++
#  dom/bindings/Codegen.py       | 69 +++++++++++++++++++++++++++++++++++++++++++
#  2 files changed, 84 insertions(+)

python3 -c "import ast; ast.parse(open('dom/bindings/Codegen.py').read())"
# 无输出 = 语法 OK
```

---

## 阶段 3 · configure（约 20 分钟）

```bash
cd ~/build/ff159
./mach bootstrap --no-system-changes    # 只装 Python 包，不动系统
./mach configure
```

若 `bootstrap` 失败，按它提示的包名手动 `apt-get install` 后重试。

**验证点**：
```bash
ls obj-*/config.status && echo "configure OK"
```

---

## 阶段 4 · 只编 dom/bindings（约 40 分钟，最有价值的快速验证）

**这一步是性价比最高的**：`dom/bindings` 会跑一遍 `Codegen.py`，
能立刻暴露补丁的语法/逻辑错误，不需要等到全量编完。

```bash
cd ~/build/ff159
./mach build dom/bindings --allow-subdirectory-build 2>&1 | tee /tmp/build-bindings.log
```

**验证点**：

| 现象 | 含义 |
| --- | --- |
| 编到 `dom/bindings` 结束无错 | Codegen 补丁正确 |
| `error: use of undeclared identifier 'domtrace'` | 0003 的 include 缺失 |
| `error: 'kMemberRanges' was not declared` | 0005 生成的表没被 include |
| Python traceback in Codegen | 补丁破坏了 Codegen 逻辑 |

生成的绑定文件里应能看到 domtrace 痕迹：

```bash
grep -rl "DOMTRACE_JITINFO_NAME" obj-*/dom/bindings/ | head -5
```

---

## 阶段 5 · 全量构建（约 3–6 小时）

```bash
cd ~/build/ff159
nice -n 10 ./mach build 2>&1 | tee /tmp/build-full.log
```

**验证点**：
```bash
tail -20 /tmp/build-full.log          # 应有 "Build complete"
ls obj-*/dist/bin/firefox             # 二进制存在
```

---

## 阶段 6 · 跑 domtrace（约 30 分钟）

```bash
mkdir -p /tmp/trace

MOZ_DOM_TRACE=1 \
MOZ_DOM_TRACE_FILE=/tmp/trace/run.jsonl \
  ~/build/ff159/obj-*/dist/bin/firefox \
    --new-instance -no-remote -profile /tmp/trace-profile \
    "data:text/html,<script>document.cookie='a=1';navigator.userAgent</script>"
```

**验证点**：

```bash
# 1. 文件生成
find /tmp/trace -name '*.jsonl' | head

# 2. 内容是合法 JSON
python3 -c "
import json, glob
for f in glob.glob('/tmp/trace/**/*.jsonl', recursive=True):
    n = sum(1 for line in open(f) if line.strip() and json.loads(line))
    print(f, n, 'lines OK')
"

# 3. 关键断言：interface 与 member 不是数字/占位符
python3 -c "
import json, glob
for f in glob.glob('/tmp/trace/**/trace_process_*.jsonl', recursive=True):
    for line in open(f):
        d = json.loads(line)
        if d.get('type') in ('get','call','set'):
            assert isinstance(d.get('interface'), str), d
            assert isinstance(d.get('member'), str), d
            print('OK', d['type'], d['interface'], d['member'])
            break
"
```

**若 interface/member 是 `<unknown>`**：说明 0001/0004/0005 的索引链没走通，
回阶段 4 检查生成的绑定文件。

---

## 阶段 7 · 与我们已还原的 `ruyitrace/domtrace/trace/` 对接

补丁只做了「采集 + 名字反查」，**没有接我们已写好的 13 类记录写入器**。
对接需要：

1. 把 `domtrace/trace/*.cpp` 加进构建（`dom/domtrace/moz.build`）
2. 在 `ScopedAccessCall` 的析构里调用 `SerializeRecord` + `SinkSession::WriteLine`
3. `SinkSession` 由 `TraceConfig` + `PlanSinks` 初始化

这部分的代码已存在（18 项测试覆盖），但**没有在 Firefox 里编译过**。

---

## 每阶段的预计耗时与产出

| 阶段 | 耗时 | 产出 | 验证方式 |
| --- | ---: | --- | --- |
| 0 环境 | 30 min | 工具链 | 版本检查 |
| 1 源码 | 20 min | 8 GB | `git log` |
| 2 补丁 | 10 min | 84 行改动 | `git diff --stat` |
| 3 configure | 20 min | config.status | 文件存在 |
| **4 编 dom/bindings** | **40 min** | **补丁正确性证明** | **无编译错误** |
| 5 全量 | 3-6 h | firefox 二进制 | Build complete |
| 6 跑 trace | 30 min | jsonl | interface/member 是名字 |
| 7 对接写入器 | 未定 | 13 类输出 | 文件内容合法 |

**关键节点是阶段 4**：40 分钟就能知道五个补丁对不对，不用等 6 小时。

---

## 失败时的排查顺序

| 阶段 | 失败现象 | 先查什么 |
| --- | --- | --- |
| 2 | `patch does not apply` | 源码 commit 是否是 `9a2dc53c` |
| 3 | `configure` 缺依赖 | `./mach bootstrap` 的输出 |
| 4 | Codegen Python 报错 | `git diff dom/bindings/Codegen.py` 逐行看 |
| 4 | C++ 找不到 `domtrace` | 是否 `cp -r domtrace dom/` |
| 5 | 链接错误 | 是否是 OOM（看 `dmesg`) |
| 6 | 无 jsonl 生成 | `MOZ_DOM_TRACE` 是否在启动前设好 |
| 6 | interface 是数字 | 0001/0004/0005 是否都应用了 |

---

## 当前不具备的条件

| 条件 | 现状 |
| --- | --- |
| x86_64 | fleet 里只有 `oracle-gateway`（952 MB 内存） |
| 内存 16 GB | 同上，差 16 倍 |
| 磁盘 60 GB | `oracle-reverse-dev` 有 73 GB，但是 aarch64 |
| glibc 2.38+ | `oracle-artex` / `oracle-reverse-dev` 满足，但都是 aarch64 |

**结论：需要一台新机器。** 现有六台没有一个能同时满足架构、内存、磁盘、glibc。
