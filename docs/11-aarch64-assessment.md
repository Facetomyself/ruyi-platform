# linux_aarch64 原生库：可行性评估

> **2026-11-24 更新：Linux ARM64 运行时现已入库，并已通过原生安装及协议验收。** 新的验收需求触发了本文原定的重议条件。固定源码在托管 ARM64 runner 构建，独立 Oracle ARM64 主机复测；当前状态与证据以 [RuyiHttp 项目记录](../projects/ruyihttp/README.md) 为准。以下保留 2026-11-19 对当时主机资源与优先级的评估，并非当前交付状态。

## 一、需要什么

`ruyihttp/native/linux_aarch64/` 现在是空位（`build-required`），需要 14 个 `.so`：

```
libnecko_core.so  libnecko_quic.so
libnss3.so  libnssutil3.so  libssl3.so
libnspr4.so  libplc4.so  libplds4.so
libsoftokn3.so  libfreebl3.so  libfreeblpriv3.so
libsqlite3.so  libnssckbi.so  libnsssysinit.so
```

## 二、构建路径（来自 `tools/build_necko_linux.py` 实读）

| 步骤 | 命令 | 依赖 |
| --- | --- | --- |
| 1. 建 venv | `python -m venv vendor/necko-derived/python` | **Python 3.14+** |
| 2. 装依赖 | `pip install gyp-next==0.21.0` + DEPENDENCIES | 网络 |
| 3. 拷源码 | `security/nss` + `nsprpub` 从 Firefox 树 | Firefox 源码 |
| 4. 编 NSS | `bash build.sh -o --clang --disable-tests -j N --dist=...` | clang、NSS 工具链 |
| 5. 拷 .so | NSS 的 `dist/Release/lib/*.so` → `necko/` | — |
| 6. 编 Brotli | `clang -std=c11 -fPIC -O2` 编 47 个 `.c` | clang |
| 7. 编 necko | `clang++ -std=c++20 -shared` 编 8 个 `.cpp` | clang++、NSS 头文件 |
| 8. 编 Neqo | `tools/build_neqo_linux.py --http3` | Rust、cargo |
| 9. 自检 | `_load_library()` 打印 NSS/NSPR 版本 | 能 dlopen |

## 三、现有环境的差距

`oracle-reverse-dev`（aarch64 / Ubuntu 24.04 / glibc 2.39 / 2 核 / 10 G / 72 G）实测：

| 需求 | 现状 | 差距 |
| --- | --- | --- |
| **Python 3.14+** | **3.12.3** | ❌ **脚本硬性拒绝**（`sys.version_info < (3, 14)` 直接 `parser.error`） |
| clang | **未装** | 需 `apt install clang` |
| Rust / cargo | **未装** | 需 rustup |
| Firefox 源码 | 有 sparse clone（1.4 G），但**缺 `security/nss` 与 `nsprpub`** | 需补 sparse 范围 |
| 磁盘 | 72 G 可用 | ✅ 够 |
| 内存 | 10 G | 🟡 NSS 编译峰值约 2-4 G，够 |

### Python 3.14 是硬门槛

脚本第 132 行：

```python
if not sys.platform.startswith("linux") or sys.version_info < (3, 14):
    parser.error("Linux, Python 3.14+ and a positive jobs count are required")
```

Ubuntu 24.04 官方源没有 3.14（`apt-cache policy python3.14` 空）。三条路：

| 路 | 成本 | 风险 |
| --- | --- | --- |
| deadsnakes PPA | 5 分钟 | PPA 可能未提供 aarch64 的 3.14 |
| 从源码编译 CPython 3.14 | 20 分钟 | 需要 `libssl-dev` 等，编译后还要 `--enable-shared` |
| 改脚本放宽版本要求 | 1 分钟 | **可能编不过**——3.14 的内嵌运行时是 wheel 的一部分，版本不一致会 ABI 不匹配 |

第三条看着最省事，但**不安全**：产物要进 `ruyihttp` 的 wheel，运行时会用 `libpython3.14.so`。
用 3.12 编出来的 `necko_core.so` 与 3.14 的 CPython ABI 不兼容。

## 四、成本估算

| 项 | 时间 |
| --- | ---: |
| 装 clang + rust + Python 3.14 | 30 min |
| 补 Firefox 源码的 `security/nss` + `nsprpub` | 10 min |
| 编 NSS 3.132（2 核 aarch64） | 60–90 min |
| 编 Brotli + necko_posix | 15 min |
| 编 Neqo（Rust） | 30 min |
| 调试失败 | 60–120 min（保守估计） |
| **合计** | **3.5–5 小时** |

## 五、收益评估

| 项 | 判断 |
| --- | --- |
| `linux_aarch64` 的用户基数 | **未知**——没有数据说明有多少人需要 |
| 当前 `build-required` 状态是否阻碍使用 | 否：`setup.py` 会明确报错，不会静默装错 |
| 与 `linux_x86_64` 的差别 | 仅架构，代码路径相同 |
| 补上后的验证成本 | 还需在 aarch64 上跑 live smoke |

**结论：这是「在等外部条件时可以做的填充工作」，不是「有明确价值的推进」。**

## 六、更值得先做的

在花 4 小时编 aarch64 库之前，有三件事成本更低、价值更明确：

| 优先级 | 事项 | 成本 |
| --- | --- | --- |
| 1 | 等 x86_64 构建机，跑 `docs/10-build-runbook.md` 阶段 4 | 40 min（机器到位后） |
| 2 | 拿一次真机 `env_inventory` 样本，补最后一个记录结构 | 需 Windows |
| 3 | `linux_aarch64` 原生库 | 3.5–5 h |

第 1 项能验证 5 个补丁 + 84 行改动，是整个仓库最关键的一步。
第 3 项只是把一个 `build-required` 变成 `ready`，没有验证任何新东西。

## 七、如果决定要做

按这个顺序：

```bash
# 1. Python 3.14（从源码编，deadsnakes 未必有 aarch64）
cd /tmp && wget https://www.python.org/ftp/python/3.14.0/Python-3.14.0.tgz
tar xf Python-3.14.0.tgz && cd Python-3.14.0
./configure --enable-shared --prefix=/opt/python314
make -j2 && sudo make install
sudo ldconfig

# 2. clang + rust
sudo apt-get install -y clang lld
curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh -s -- -y

# 3. 补 Firefox 源码
cd /tmp/ffprobe
git sparse-checkout add security/nss nsprpub

# 4. 编
cd /path/to/ff-ruyijs
/opt/python314/bin/python3 tools/build_necko_linux.py \
  --firefox-source /tmp/ffprobe --jobs 2 --http3

# 5. 拷进 ruyihttp
cp native/necko_posix/*.so /path/to/ruyihttp/native/linux_aarch64/
cd /path/to/ruyihttp
python tools/build_native.py --check
```

第 5 步之后需要更新 `runtime-manifest.json` 与 `provenance.json`，
否则 `verify_runtime.py` 会报 hash 不匹配。

## 八、当前决策

**不做。** 理由：

1. 需要 3.5–5 小时，且 Python 3.14 在 aarch64 上的获取路径不确定
2. 收益是「补一个可能无人使用的平台」
3. 同一时间可以做更有价值的事

若后续确认 `linux_aarch64` 有实际需求，按 §七 执行。
