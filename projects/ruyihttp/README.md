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
| `linux_x86_64` | ready（未 live 验证） | 159.0 / 3.132 / 0.33.0 | `py3-none-manylinux_2_39_x86_64` |
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
| Linux live | **未验证** | 需 x86_64 + glibc ≥ 2.38 |
| 仓库可见性 | public | — |

### 已完成的历史待办

以下四项曾登记为待办，现已全部闭合：

1. `backports` 导入 —— 已改为三级 fallback（`compression.zstd` → `backports.zstd` → `backports.zstd.zstd`），见 `ruyihttp/_nss.py`。
2. 6 项 Windows 断言 —— 已用 `driven_host()` 按真实宿主分支，19/19 全绿。
3. `dist/` 归档 —— 已移到 `dist-v0.9.0-legacy/` 并附 `VERIFICATION.md`。
4. 三平台重新构建 —— 已完成，26 个原生文件 hash 全匹配。

## 剩余缺口

| 项 | 卡在哪 |
| --- | --- |
| Linux live 验证 | 需 x86_64 且 glibc ≥ 2.38 的主机。本机是 aarch64 + glibc 2.35 |
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
