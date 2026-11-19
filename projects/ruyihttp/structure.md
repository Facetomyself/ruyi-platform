# RuyiHttp 现有结构

```
submodules/ruyihttp/
├── ruyihttp/                       3932 行 / 13 文件
│   ├── _transport.py               1260   exchange 抽象 / 重试 / 缓存
│   ├── _http2.py                    566   自实现 HTTP/2
│   ├── _http3.py                    530   QUIC
│   ├── _firefox.py                  481   header 顺序 / UA / cookie
│   ├── _nss.py                      474   ctypes 绑定
│   ├── _tls_profiles.py             169   100–159 profile 表
│   ├── _connect.py                  109   TCP / 代理
│   ├── sessions.py                   89   Session 子类
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
│   └── linux_aarch64/   仅 README（build-required）
├── tools/             build_native.py / verify_runtime.py
├── tests/             test_runtime.py
├── ci/                smoke_local.py
├── docs/              build-native / licensing / platform-support
├── setup.py           114 行
├── pyproject.toml
└── dist-v0.9.0-legacy/   2 个旧 wheel 归档 + VERIFICATION.md
```

## 缺失

| 项 | 现状 | 补法 |
| --- | --- | --- |
| 原生库 C/C++/Rust 源码 | ❌ 不在树内 | 参照 `ff-ruyijs/native/`（见 `docs/02-source-recovery.md` §1） |
| `darwin_x86_64` / `linux_aarch64` 二进制 | ❌ 空位 | 对应平台构建 |
| linux wheel | ✅ 可重建（未 live 验证） | `RUYIHTTP_PLATFORM=linux_x86_64 RUYIHTTP_GLIBC=2.39 pip wheel ...` |
