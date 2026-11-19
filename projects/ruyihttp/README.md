# RuyiHttp

仓库：`Facetomyself/ruyihttp`（private）
挂载：`submodules/ruyihttp`

## 是什么

Firefox Necko/NSS 的 Requests 风格 HTTP 客户端。不启动浏览器，TLS ClientHello / H2 SETTINGS / H3 优先级按 Firefox 100–159 的正式版发送。

## 期望目录

```
submodules/ruyihttp/
├── ruyihttp/            13 个 .py，3932 行
├── native/
│   ├── win_amd64/       6 文件，7.2 MB（NSS 3.131 / Neqo 0.32.0）
│   ├── darwin_arm64/    6 文件，8.2 MB（NSS 3.132 / Neqo 0.33.0）
│   ├── linux_x86_64/   14 文件，8.4 MB（NSS 3.132 / Neqo 0.33.0）
│   ├── darwin_x86_64/   空（build-required）
│   └── linux_aarch64/   空（build-required）
├── tools/               build_native.py / verify_runtime.py
├── tests/               test_runtime.py（19 契约测试）
├── ci/smoke_local.py
└── docs/                build-native / licensing / platform-support
```

## 为什么原生库入库

24 MB 三平台合计，换 wheel 可离线构建。规则见 `conventions.md` §5：每平台只留一份，换代整目录替换并更新 `PINS.md`。

## 当前状态

- 源码：complete
- 原生哈希：26 文件全部匹配
- 契约测试：13/19（6 项 Windows 假设）
- Linux live：未验证（本机 glibc 2.35 < 2.38）

## 待办

1. 修 `backports` 导入（`_nss.py:34`）
2. 参数化 6 个 Windows 断言测试
3. `dist/` 归档为 `dist-v0.9.0-legacy/`
4. 在 glibc ≥ 2.38 主机上跑 live smoke
