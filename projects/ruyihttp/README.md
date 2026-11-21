# RuyiHttp

| 项 | 值 |
| --- | --- |
| 仓库 | `Facetomyself/ruyihttp`（**public**，2026-11-20 起） |
| 挂载 | `submodules/ruyihttp` |
| 版本 | `0.9.0` |
| 许可 | MPL-2.0 |

## 是什么

Firefox Necko/NSS 的 Requests 风格 HTTP 客户端。不启动浏览器，TLS ClientHello / H2 SETTINGS / H3 优先级按 Firefox 100–159 的正式版发送。

它不是 browser fact，也不替代 RuyiTrace、RuyiDOM 或 ruyipage。

与 [ruyi-mcp](../../docs/01-architecture.md#5-ruyi-mcp-控制面与组件边界) 的关系是 HTTP 行为对照，两者各自运行。

## 目录

```
submodules/ruyihttp/
├── ruyihttp/            13 个 .py，约 3900 行
├── native/
│   ├── win_amd64/       6 文件，7.2 MB（NSS 3.131 / Neqo 0.32.0）
│   ├── darwin_arm64/    6 文件，8.2 MB（NSS 3.132 / Neqo 0.33.0）
│   ├── linux_x86_64/   14 文件，8.4 MB（NSS 3.132 / Neqo 0.33.0）
│   ├── darwin_x86_64/   空（build-required，仅 README）
│   └── linux_aarch64/   空（build-required，仅 README）
├── tools/               build_native.py / verify_runtime.py
├── tests/               test_runtime.py（19 项契约测试）
├── ci/smoke_local.py
├── docs/                build-native / licensing / platform-support
├── dist-v0.9.0-legacy/  脱钩旧 wheel 归档 + VERIFICATION.md
└── setup.py             平台选择与原生库打包
```

结构细节见 [`structure.md`](structure.md)。

## 平台矩阵

| 平台 | 状态 | Firefox / NSS / Neqo | wheel tag |
| --- | --- | --- | --- |
| `win_amd64` | ready | 159.0 / 3.131 / 0.32.0 | `py3-none-win_amd64` |
| `darwin_arm64` | ready | 159.0 / 3.132 / 0.33.0 | `py3-none-macosx_26_0_arm64` |
| `linux_x86_64` | ready（Ubuntu 24.04 容器已通过 HTTPS 验收） | 159.0 / 3.132 / 0.33.0 | `py3-none-manylinux_2_39_x86_64` |
| `darwin_x86_64` | build-required | 159.0 / 3.132 / 0.33.0 | `py3-none-macosx_11_0_x86_64` |
| `linux_aarch64` | build-required | 159.0 / 3.132 / 0.33.0 | `py3-none-manylinux_2_39_aarch64` |

两个 `build-required` 平台已有代码路径与 manifest 槽位，没有二进制。构建时 `setup.py` 明确抛
`native runtime missing`，不会静默打包其他平台的二进制：

```bash
cd submodules/ruyihttp
RUYIHTTP_PLATFORM=linux_aarch64 python -m pip wheel --no-build-isolation --no-deps -w /tmp/x .
```

## 为什么原生库入库

24 MB 三平台合计，换 wheel 可离线构建。规则见 `conventions.md` §5：每平台只留一份，换代整目录替换并更新 `PINS.md`。

## 当前状态（2026-11-20 实测）

| 项 | 状态 | 验证命令 |
| --- | --- | --- |
| 源码 | complete | — |
| 原生哈希 | **26/26 匹配** | `python3 tools/verify_runtime.py` |
| ABI 导出符号 | pass（3 个 ready 平台） | 同上 |
| 契约测试 | **19/19 通过** | `python -m unittest discover -s tests` |
| wheel 重建 | 3 平台成功，hash 全匹配 | 见 `dist-v0.9.0-legacy/VERIFICATION.md` |
| `build-required` 行为 | 2 平台按预期抛错 | 见上方命令 |
| Linux live | **通过**（2026-11-20） | `RUYIHTTP_LIVE=1 python ci/smoke_local.py`；环境见下 |
| 仓库可见性 | public | — |

### 已完成的历史待办

以下四项曾登记为待办，现已全部闭合：

1. `backports` 导入 —— 已改为三级 fallback（`compression.zstd` → `backports.zstd` → `backports.zstd.zstd`），见 `ruyihttp/_nss.py`。
2. 6 项 Windows 断言 —— 已用 `driven_host()` 按真实宿主分支，19/19 全绿。
3. `dist/` 归档 —— 已移到 `dist-v0.9.0-legacy/` 并附 `VERIFICATION.md`。
4. 三平台重新构建 —— 已完成，26 个原生文件 hash 全匹配。

### Linux x86_64 验收记录

2026-11-20 23:37（UTC+8），`oracle-gateway` 原生 x86_64 CPU，宿主 glibc 2.31；无模拟器。使用 Ubuntu 24.04 amd64 容器（glibc 2.39、Python 3.12.3），镜像 `ubuntu@sha256:9c7f200c07e3d4a03e7249d2c16bf66a51120fb876aa2242cf31451412543289`。

- 对象：`ruyihttp-0.9.0-py3-none-manylinux_2_39_x86_64.whl`，SHA-256 `da6a8800f33c0232b2705bc9c93f70d57a5971c29b7638380f7c33373fa2ab77`。Python 文件与子模块 `b4cc7b2` 一致；在干净 venv 安装后 `pip check` 通过，包内 14 个 `.so` 哈希匹配清单。
- 加载：进程映射确认 Necko core、QUIC、NSS 来自已安装的 wheel；原生接口返回 NSS 3.132 / NSPR 4.40。
- 请求：本地 HTTP 返回 200 且正文一致；`https://example.com/` 返回 200，Firefox 159 profile，TLS 1.3、ALPN `h2`、cipher `0x1301`。
- 范围：QUIC 仅验证加载。未验收 HTTP/3 握手、代理和宿主 glibc 2.31 裸机运行。`cryptography 50.0.2` 读取根证书时对非正序列号发出弃用警告，本次握手成功；升级依赖时应复测。

复验时将该 wheel 与 `ci/smoke_local.py` 放入匹配的 amd64 容器，在源码树之外运行：

```bash
python3 -m venv env
env/bin/python -m pip install ./ruyihttp-0.9.0-py3-none-manylinux_2_39_x86_64.whl
env/bin/python -m pip check
RUYIHTTP_LIVE=1 env/bin/python smoke_local.py
```

## 剩余缺口

| 项 | 卡在哪 |
| --- | --- |
| Linux HTTP/3 | QUIC 库已加载，尚无端到端 HTTP/3 请求证据 |
| `darwin_x86_64` / `linux_aarch64` 二进制 | 对应平台构建，评估见 `docs/11-aarch64-assessment.md`（决策：不做） |
| 原生库 C/C++/Rust 源码 | 不在树内，来源为 `ff-ruyijs` 0.4.1 wheel，见 `docs/02-source-recovery.md` |

## 构建

```bash
cd submodules/ruyihttp

# 本机平台
python -m pip wheel --no-build-isolation --no-deps -w dist .

# 交叉构建
RUYIHTTP_PLATFORM=win_amd64    python -m pip wheel --no-build-isolation --no-deps -w dist .
RUYIHTTP_PLATFORM=darwin_arm64 python -m pip wheel --no-build-isolation --no-deps -w dist .
RUYIHTTP_PLATFORM=linux_x86_64 RUYIHTTP_GLIBC=2.39 \
  python -m pip wheel --no-build-isolation --no-deps -w dist .
```

**构建环境要求 `setuptools >= 77`**。低于该版本时 `pyproject.toml` 的 `[project]` 段不被识别，
会静默产出 `UNKNOWN-0.0.0` 的 wheel 并以成功码退出。先升级：

```bash
python -m pip install -U 'setuptools>=77' wheel
```

## 许可

`ruyihttp/` 保留 Mozilla Public License 2.0 声明。macOS / Linux 原生库来自
`ff-ruyijs` 0.4.1。详见仓库内 `docs/licensing.md` 与 `THIRD_PARTY_NOTICES.md`。
