# RuyiHttp

| 项 | 值 |
| --- | --- |
| 仓库 | `Facetomyself/ruyihttp`（**public**，2026-11-20 起） |
| 挂载 | `submodules/ruyihttp` |
| 版本 | `0.9.2`（独立维护，从上游 0.9.0 起步并选择性跟进 [0.11.0](https://pypi.org/project/ruyihttp/0.11.0/)） |
| 许可 | MPL-2.0 |

## 是什么

Firefox Necko/NSS 的 Requests 风格 HTTP 客户端。不启动浏览器，支持 Firefox 100–161 配置，默认 159；TLS/H2/H3 的具体观察和差异见[官方浏览器对照](../../submodules/ruyihttp/docs/firefox-profile-wire.md)。

它不是 browser fact，也不替代 RuyiTrace、RuyiDOM 或 ruyipage。

与 [ruyi-mcp](../../docs/01-architecture.md#5-ruyi-mcp-控制面与组件边界) 的关系是 HTTP 行为对照，两者各自运行。

## 目录

```
submodules/ruyihttp/
├── ruyihttp/            Python 客户端、只读信任缓存、原生缓冲读取及平台清单
├── native/
│   ├── win_amd64/       6 个上游 Windows DLL（NSS 3.133 / Neqo 0.34.0）
│   ├── darwin_arm64/    6 个 Apple Silicon 源码构建 dylib，正文 ABI v1
│   ├── linux_x86_64/   14 个 Linux x86_64 源码构建 ELF，正文 ABI v1
│   ├── darwin_x86_64/   6 个 x86_64 dylib 和固定源码构建来源
│   └── linux_aarch64/   14 个 AArch64 ELF 和固定源码构建来源
├── tools/               build_native.py / verify_runtime.py / check_linux_candidate.py
├── tests/               契约、原生预检和 opt-in HTTP/3 集成测试
├── ci/                  安装后 HTTP、H2 EOF、H3 和双跳代理验收
├── benchmarks/          真实回环源站、冷/热连接性能与并发隔离趋势
├── docs/                构建、平台、H2 流控与性能策略
├── dist-v0.9.0-legacy/  脱钩旧 wheel 归档 + VERIFICATION.md
└── setup.py             平台选择与原生库打包
```

结构细节见 [`structure.md`](structure.md)。

## 平台矩阵

| 平台 | 状态 | Firefox / NSS / Neqo | wheel tag |
| --- | --- | --- | --- |
| `win_amd64` | ready | 161.0 / 3.133 / 0.34.0 | `py3-none-win_amd64` |
| `darwin_arm64` | ready | 161.0 / 3.133 / 0.34.0 | `py3-none-macosx_26_0_arm64` |
| `linux_x86_64` | ready（Ubuntu 24.04 容器已通过 HTTPS 验收） | 161.0 / 3.133 / 0.34.0 | `py3-none-manylinux_2_39_x86_64` |
| `darwin_x86_64` | ready（Intel macOS 15.7.9 安装及 H1/H2/H3） | 161.0 / 3.133 / 0.34.0 | `py3-none-macosx_15_0_x86_64` |
| `linux_aarch64` | ready（原生 ARM64 编译、安装及 H1/H2/H3） | 161.0 / 3.133 / 0.34.0 | `py3-none-manylinux_2_39_aarch64` |

打包器要求状态为 `ready`，且平台目录的文件集合及 SHA-256 与清单完全一致；单独放入一个同名库不会生成目标 wheel。Linux 槽位的最低 glibc 标签为 2.39，即使跨打包宿主更旧也不能把标签降到 2.31。

### 2026-11-26：0.9.2 选择性同步

先同步并独立核验 118 张 TLS server-trusted 根、一个签发截止约束与 10,463 条 PSL 规则，再添加显式 160/161、升级 Windows 6 DLL、从 Firefox 161 正式版源码重编四个 POSIX 套件。保留本仓 POST 重放限制、H2 流控、H3 STOP 与 POSIX 正文 ABI v1。两个 Python 端点都检查上代 0.9.0 和直接前代 fork 0.9.1 的原地升级。见[五平台最终实测](https://github.com/Facetomyself/ruyihttp/actions/runs/45747144872)及[精确提交与工件哈希](../../artifacts/receipts/ruyihttp-0.9.2/qualification.json)。

### Linux 原生候选静态预检

`fd3d4f3` 增加只读 `check_linux_candidate.py DIR --arch aarch64`，核对完整 14 库的 ELF 架构、31 个核心和 2 个 QUIC 函数的**已定义动态导出**、依赖库名称、同级 loader 路径及至多 `GLIBC_2.39` 的符号需求。它既不加载库，也不写运行时清单。这是 2026-11-22 的静态检查范围。实际 ARM64 运行时和协议验收已于 2026-11-24 单独完成，见下文。

走 `--reference` 实测历史 amd64 14 库和全部导出匹配，最高动态版本需求 `GLIBC_2.38`（发行 wheel 仍声明 2.39）。旧库的继承搜索路径超出同级，默认候选检查会拦截；未复制或改写这些库。实际证据 `deliverables/linux-ruyihttp-preflight-r70/historical-amd64-abi.json`。ARM64 测试在本机编译非产品 ELF，覆盖错误架构、漏导出和引用未定义，21 项回归通过；非 ARM64 runtime 发行证据。

`2903c12` 还加入只读 `build_native.py --inspect-wheel`：先限制 ZIP 中央目录，再仅展开声明的原生库，拒绝重复 basename、链接、非本架构 Linux ELF 或检查期间变动的 wheel。历史 Win64 的六个成员通过；旧 macOS 包缺 `libnecko_quic.dylib`，按预期失败。用现有 Linux 14 库构造的布局试件与 runtime manifest 逐项相符。26 项回归通过，既有库和运行时清单保持原样。

## 为什么原生库入库

平台目录存放已验证的整套原生库，使 wheel 可以离线封装。规则见 `conventions.md` §5：每平台只留一份，换代整目录替换并更新 `PINS.md`。

## 历史基线（2026-11-20 实测）

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

### 2026-11-24：HTTP/3 与代理链端到端验收

在 x86_64 Linux 上从已安装 wheel 建立真正的 QUIC 连接。独立 UDP 服务端记录 TLS 1.3、ALPN `h3`、流 0 与 4；关闭所有 TCP 监听后，IPv4 和 IPv6 都经 `Session` 完成端口型 Alt-Svc 升级。256 KiB GET/POST、流重置/超时后复用以及三种证书反例均有专门断言。修复前 IPv6 地址丢失方括号导致升级失败。见[已安装 wheel 回归](https://github.com/Facetomyself/ruyihttp/actions/runs/45334742501)。

HTTP CONNECT、HTTPS CONNECT、SOCKS5h 三种入口经第二跳 CONNECT 到达受控 TLS 源站；三端分别记录请求，校验临时响应值和代理认证头隔离。第二跳断开时零源站请求；错误域名证书分别在 HTTPS 入口或源站阻止请求。共 [10 项通过](https://github.com/Facetomyself/ruyihttp/actions/runs/45333462315)。结论限于服务端联链的 TCP 代理路径，未验收 CONNECT-UDP/MASQUE。

### 2026-11-24：Linux ARM64 原生构建与目标机网络验证

[固定源码原生构建](https://github.com/Facetomyself/ruyihttp/actions/runs/45335744015)产出完整的 14 个 AArch64 ELF（NSS 3.132、NSPR 4.40、Neqo 0.33.0）。[从入库字节重新打包](https://github.com/Facetomyself/ruyihttp/actions/runs/45336869695)并在干净 ARM64 venv 校验 wheel 哈希、加载路径、HTTP/1、H2、H3 和 peer EOF。标签 `manylinux_2_39_aarch64` 经 auditwheel 核实。[原生回执](../../artifacts/receipts/ruyihttp-native-20261124/linux-aarch64.json)。

独立 Oracle ARM64 主机的回环证据包括真实 IPv4/IPv6 UDP H3、TLS 正反例和双跳代理。[H3 客户端/服务端回执](../../artifacts/receipts/ruyihttp-native-20261124/h3.txt)及[代理逐跳记录](../../artifacts/receipts/ruyihttp-native-20261124/proxy.json)给出了 x86_64 侧的独立对照。公网双栈单独验收：在 IPv6 优先而 IPv6 出口超时的同一主机，旧库对 example.com、PyPI 均在 TLS 前超时。`3df80a3` 在总连接时限内错开两种地址族尝试，保留原始 SNI、证书校验及代理侧 DNS。安装[主分支 wheel](https://github.com/Facetomyself/ruyihttp/actions/runs/45339943378)后两个原 URL 均返回 200/NSS TLS 1.3/h2；受控错误域名仍在发送 HTTP 前失败。

### 2026-11-24：Intel macOS 原生运行时

在原生 Intel runner 上编译 6 个 x86_64 dylib。最低部署版本从 Mach-O load commands 读取为 15.0，实际安装机为 macOS 15.7.9。第一版 H3 已经传输成功但 `tls=null`，未提升为正式运行时。修复 donor QUIC 桥后，从 Neqo 会话取回 TLS 版本、ALPN、cipher、恢复状态；实际选择的 Firefox 版本随请求传入。新的[严格验收](https://github.com/Facetomyself/ruyihttp/actions/runs/45341302623)通过 6 项 H3、10 项两跳代理与 H2 EOF 正反对照。[目标机回执及工件身份](../../artifacts/receipts/ruyihttp-native-20261124/darwin-x86_64.json)。

### 2026-11-25：请求异常路径与信任边界

| 场景 | 旧基线 `846f8ff` | 修复后的验收判据 |
| --- | --- | --- |
| 已发送 POST，复用连接时回执丢失 | 一次调用被服务器读完两次 | 默认只送达一次，向调用方报告结果未知的连接错误；安全 GET、协议明确未处理及调用方显式允许的重试仍可用 |
| IPv4 跨站 fetch | 末两段相同的不同 IPv4 被当作同站，附带目标的 Strict Cookie | 使用完整规范化 IP；Cookie 与 `Sec-Fetch-Site` 一致，保留同 IP 不同端口及 DNS 注册域的合法同站行为 |
| 跨源 H2 连接复用与 DNS | 调用线程阻塞，拨号获得新的时间预算 | 按一次连接尝试的绝对期限分配池等待、DNS 与拨号；过期时归还租约，证书不匹配仍拒绝复用 |
| H2 上传中提前收到完整 413 和 `RST_STREAM(NO_ERROR)` | 调用方只拿到连接错误 | 保存状态、头和完整正文，获知停止上传后不再拉取下一块；截断、错误长度和 `CANCEL` 仍失败 |

复验：在源码树外，以安装了目标 wheel 和 PySocks 的 Python 环境执行 `bash /path/to/checkout/ci/verify_request_boundaries.sh`。以上 TCP、TLS、HTTP/2 对端均为回环监听器，Cookie 用例检查实际准备好的请求。[分平台回执](../../artifacts/receipts/ruyihttp-request-boundaries-20261125.json)。

### 2026-11-26：0.9.1 传输性能、协议完整性与升级验收

- H3 处理对端正常停止上传后结束源数据消费，保留有效最终响应并继续区分取消、截断。UDP 持续不可用时可以复用已验证的同源 TCP；短预算跳过无谓竞速。Alt-Svc 和 QUIC 恢复信息具有 TTL、容量及相应字节限制。
- 降低 ctypes 读取的分配成本；可复用 H2 连接按流容量租出，大流和慢读者保留受限窗口。只缓存内容寻址的只读 CA/约束，轮换后新握手重新验证。两种 Linux 和两种 macOS 均由固定源码构建 H3 正文 ABI v1；Windows 保留原始 DLL 与 JSON 正文兼容路径。
- 五份 wheel 分别在 CPython 3.10、3.14 安装，对协议及新旧版本升级作独立检查。单次低时延基准、同连接流隔离、native 读写计数及 Windows 旧桥字段各有自己的证据，不能彼此替代。详见[验收回执](../../artifacts/receipts/ruyihttp-0.9.1/qualification.json)与[成对性能摘要](../../artifacts/receipts/ruyihttp-0.9.1/performance.md)。

复验：在产品仓运行 `python tools/build_native.py --check`，并按[性能文档](../../submodules/ruyihttp/docs/performance.md)在源码树外运行已安装工件基准。每周趋势任务以真实报文/哈希作为功能门禁，普通共享 runner 上的耗时只作趋势参考。

## 剩余缺口

| 项 | 卡在哪 |
| --- | --- |
| HTTP/3 经代理 | 普通 TCP 代理和直连 H3 已分别验收；这两种能力并不构成 CONNECT-UDP/MASQUE 验收 |
| 旧系统兼容性 | Intel Mac 15.0 是二进制部署下限，目标机验收版本为 15.7.9；未宣称在 macOS 11–14 或 Linux glibc < 2.39 上可用 |
| 原生来源 | Windows 固定历史 wheel；POSIX 固定 donor、Firefox 源提交和本地补丁。安装包内的 `native-provenance.json` 给出对应目标的逐文件来源 |

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
固定的 `ff-ruyijs` / Firefox 来源和补丁。详见仓库内 `docs/licensing.md` 与 `THIRD_PARTY_NOTICES.md`。
