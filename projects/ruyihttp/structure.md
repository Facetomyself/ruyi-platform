# RuyiHttp 现有结构

```
submodules/ruyihttp/
├── ruyihttp/                       Python 客户端和平台清单
│   ├── _transport.py    exchange 抽象 / 重试 / 缓存
│   ├── _http2.py    自实现 HTTP/2
│   ├── _http3.py    QUIC
│   ├── _firefox.py    header 顺序 / UA / cookie
│   ├── _nss.py    ctypes 绑定
│   ├── _tls_profiles.py    100–159 profile 表
│   ├── _connect.py    TCP / 代理
│   ├── sessions.py    Session 子类
│   ├── _socks.py                     57
│   ├── _retry.py                     47
│   ├── api.py                        40
│   ├── adapters.py                    9
│   └── __init__.py                  101
├── native/
│   ├── linux_x86_64/   14 文件  8.4 MB
│   ├── darwin_arm64/    6 文件  8.2 MB
│   ├── win_amd64/       6 文件  7.2 MB
│   ├── darwin_x86_64/   仅 README（build-required）
│   └── linux_aarch64/   14 个 AArch64 ELF、哈希与构建来源
├── tools/             build_native.py / verify_runtime.py
├── tests/             契约、原生清单、H3 集成测试
├── ci/                安装后的 HTTP、双跳代理、H2 EOF 与原生平台验收
├── docs/              build-native / licensing / platform-support
├── setup.py    行
├── pyproject.toml
└── dist-v0.9.0-legacy/   2 个旧 wheel 归档 + VERIFICATION.md
```

## 缺失

| 项 | 现状 | 补法 |
| --- | --- | --- |
| 原生库 C/C++/Rust 源码 | ❌ 不在树内 | 参照 `ff-ruyijs/native/`（见 `docs/02-source-recovery.md` §1） |
| 两个新原生平台 | 架构、原生库存及协议验证分开记录 | 见[平台矩阵](README.md#平台矩阵) |
| Linux wheel | amd64、aarch64 均可从仓内原生文件重建 | [构建与验收](README.md) |
