# RuyiHttp 目录与维护职责

```text
submodules/ruyihttp/
├── ruyihttp/                          Python API 与运行时配置
│   ├── sessions.py、api.py             会话与 Requests 风格接口
│   ├── _transport.py、_connect.py      连接池、拨号竞速、期限与 Alt-Svc
│   ├── _http2.py、_http3.py            协议状态、上传/下载与复用
│   ├── _retry.py、_socks.py            重试语义与 SOCKS 协商
│   ├── _nss.py、_trust.py              NSS 绑定、只读 CA 缓存与逐连接校验
│   ├── _native_buffer.py              有长度边界的原生缓冲区读取
│   ├── _firefox.py、_tls_profiles.py   请求配置和站点判定
│   └── runtime-manifest.json          原生文件、版本与四份数据文件的哈希
├── native/                            每个目标一套库、SHA256SUMS 和来源记录
│   └── patches/                       固定 donor 上的 H3 数据及观测补丁
├── ci/                                目标机安装、协议、负例及旧版本升级验收
├── tests/                             单元、契约与 opt-in 原生网络测试
├── benchmarks/                        独立回环源站、性能采样和趋势报表
├── tools/                             原生预检、导入、构建追溯及准入
├── docs/                              平台、构建、H2 流控、性能与分发说明
├── setup.py、pyproject.toml            平台标签、打包与项目元数据
└── dist-v0.9.0-legacy/                 历史发布物，仅供溯源
```

[项目入口](README.md)记录当前适用范围和历史验收。平台版本、源提交及工件哈希见[固定版本](../../PINS.md)。wheel 安装后的 `ruyihttp/native-provenance.json` 对应当前包中的原生文件，不是其他目标的来源记录。
