# 04 · 已知缺口、矛盾点与待决策项

## 当前交付缺口

**2026-11-24，RuyiJS 条目已更新至 R376；各项目保持各自的交付回执。** 已经通过的两道门先从待办移走：AMD64 R5 的 Trace CLI 与 MCP 生产同会话有真实回执；RuyiJS 私有 Linux amd64 壳已链接并从离线归档实跑。剩余工作按**会阻塞哪种下游交付**排列，不用单一“完成百分比”。依赖类型见[架构关系表](01-architecture.md#下游先选依赖再选证据)，版本检出见[交接手册](14-source-handoff.md)。

| 优先级 / 责任组件 | 目前可以依赖 | 还挡住什么；怎样才算通过 |
|---|---|---|
| **已验 · 原生 Linux ARM64 私有产品（R432）** | [全量安装回执](../artifacts/receipts/ruyijs-linux-aarch64-product-r432/validation.json)：1,268 TU、18 库、13 项功能门、C、安装态默认 Context/Worker/WebCrypto、JS HTTPS 及导航外部脚本均在 ARM 真机运行。 | 认证范围为 Ubuntu 24.04 / glibc 2.39、CPython 3.12.3；musl、其它发行版与 32 位 ARM 仍各自待验。 |
| **已验 · ARM64 原生 HTTP/3 互操作** | [正反对照](../artifacts/receipts/ruyijs-linux-aarch64-h3-r432/validation.json)：调用方核验服务器 DER 后由真实 QUIC ABI 完成 ngtcp2 H3 请求/响应；错误 pin 和错误 CA 均在发送 HTTP 之前终止。 | JS 默认 HTTP/3、WebTransport、公网证书策略仍未接通；另一测试对端 aioquic 0.9.25 有 ALPN 解码差异。 |
| **已验 · Linux x86-64 QUIC 组件（R431）** | [宿主原生回执](../artifacts/receipts/ruyijs-linux-quic-component-r431/validation.json)：真实 ELF 加载，固定 NSS 映射，创建/驱动/关闭会话，回环收到 QUIC v1 Initial。 | 下一道门是对真实 h3 服务端完成带身份校验的握手并读回响应体，再接已安装 wheel 的 JS 路由。本项未覆盖这两道门。 |
| **已验 · RuyiJS amd64 离线发行** | [R356 wheel](../artifacts/receipts/ruyijs-linux-amd64-wheel-r356/validation.json) 使用 R355 干净原生构建的确切字节。新装及从 R354 升级均通过 13 组安装态测试及真实 Worker/WebCrypto，显式回退后的文件清单完全恢复。 | 依照[固定版本的安装命令](../submodules/ruyijs/docs/linux-amd64-clean-wheel.md)使用；公共索引、跨发行版认证、联网与 ARM64 不继承本项证明。 |
| **P1 · Trace / MCP 发布与管理面** | [M2 标准与暂停中停止](../artifacts/receipts/trace-amd64-r5/m2-delivery.json)用 Trace `f8eeb0e` + MCP `8f3839b` + R5；MCP 当前 pin `b5e204a` 又验过[自然到期、错范围无页面动作及实际归还](../artifacts/receipts/trace-amd64-r5/borrowed-behaviors-b5e204a.json)。 | **挡扩大支持矩阵，不挡已验的原生 AMD64 CLI 组合。** 发布新 CLI/MCP 组合时固定双方 SHA 与同一浏览器摘要，重跑正常归还及暂停中停止两档；另测 Firefox 进程意外丢失，核对租约、descriptor、profile 及输出。生产 ARM64、Electron 充当 owner、跨执行机 SSH stdio 分开签收。[执行入口](../projects/ruyi-mcp/PRODUCTION-OWNER.md) |
| **已复核 · distrust 截止** | [R389](../artifacts/receipts/ruyijs-linux-cutoff-recheck-r389/validation.json)：新探针重跑 R388 两项声明，结论一致。 | 复核不改变缺口清单；OCSP/CRL 与默认根库仍未做。 |
| **已验 · distrust 截止（实机）** | [R388](../artifacts/receipts/ruyijs-linux-cutoff-r388/validation.json)：过去 cutoff 拒绝、未来放行，拒绝理由明确；R387 的 `NameError` 缺陷已修。 | 仅覆盖调用方声明的 cutoff；默认 Mozilla 根与 OCSP/CRL 仍未做。 |
| **部分已验 · distrust 截止（R387 已被取代）** | [R387](../artifacts/receipts/ruyijs-linux-cutoff-offline-r387/validation.json)：解析、绑定与执行逻辑离线全通过；实机未验，且当时存在未定位的 `SEC_ERROR_EXTENSION_NOT_FOUND`。 | 实机截止执行未签收；该 NSS 报错待查。这一行不能当作"已在线上生效"。 |
| **已验 · PEM 锚点包** | [R386](../artifacts/receipts/ruyijs-linux-pem-anchors-r386/validation.json)：可消费 121 张证书的 Mozilla 包，端到端拒绝未签发叶子。 | 未默认启用 Mozilla 根、未实现 distrust-after 截止与 PKIX 名称约束——与原始 Windows 实现仍有差距。 |
| **已验 · 构建期提交校验** | [R385](../artifacts/receipts/ruyijs-linux-commit-guard-r385/validation.json)：锁定源必须与 `HEAD` 一致；非检出目录需显式 opt-out，否则拒绝构建。 | 依赖 git 可用；归档分发场景必须显式声明 opt-out。 |
| **已验 · TLS profile 计数边界** | [R384](../artifacts/receipts/ruyijs-linux-profile-bounds-r384/validation.json)：四类计数均设上限，超界在调用 NSS 前拒绝；真实 profile 仍可握手。 | profile 接口尚未被 JS 路径使用；客户端证书未接通。 |
| **已验 · h2 拒绝（实机）** | [R397](../artifacts/receipts/ruyijs-linux-h2-refusal-r397/validation.json)：选 h2 的对端被拒且未收到任何 HTTP 字节。 | h2 **帧与多路复用**仍未实现。 |
| **已补 · ALPN 守卫测试** | [R396](../artifacts/receipts/ruyijs-linux-alpn-coverage-r396/validation.json)：`h2` 拒绝逻辑抽为纯函数并覆盖；变异可检出。 | h2 **帧与多路复用**仍未实现；端到端 h2 用例本轮未在主机执行。 |
| **已验 · h2 端到端（R430）** | [R430](../artifacts/receipts/ruyijs-linux-h2-e2e-r430/validation.json)：ALPN h2 协商成功，vendored 帧化完成请求，200+body。 | 多路复用、server push、JS 层标志、QUIC/h3、ARM64 仍未签收。 |
| **已验 · 默认 Mozilla 根库（R423）** | [R423](../artifacts/receipts/ruyijs-linux-default-roots-r423/validation.json)：121 根 + cutoff 随 wheel 分发，pin 文件 opt-in，测试 CA 被拒（-8079）。 | OCSP/CRL、PKIX、h2、QUIC、ARM64 仍未签收。 |
| **已验 · 含 ABI 修复的 wheel** | [R393](../artifacts/receipts/ruyijs-linux-wheel-r393/validation.json)：安装后 19 个离线 + 3 个端到端测试全绿，`declare_adapter` 在打包产物中确认存在。 | brotli/OCSP/h2/QUIC/ARM64 仍未做。 |
| **已补 · 端到端握手测试** | [R394](../artifacts/receipts/ruyijs-linux-e2e-tests-r394/validation.json)：3 个用例通过，并暴露 `exchange()` 对调用方传入库未声明 ABI 的缺陷（已修）。 | wheel 尚未包含该修复；brotli/OCSP/h2/QUIC/ARM64 仍未做。 |
| **已补 · TLS 模块仓库内测试** | [R392](../artifacts/receipts/ruyijs-linux-tls-tests-r392/validation.json)：18 个测试覆盖解析、链、主机名、锚点、cutoff；两处变异均被检出。 | 测试是离线的，不含真实握手；端到端仍需主机。 |
| **已缓解 · 压缩编码覆盖** | [R391](../artifacts/receipts/ruyijs-linux-content-negotiation-r391/validation.json)：请求只声明 `gzip, deflate`，服务端不会再回 `br`/`zstd`。 | brotli/zstd **解码**仍未实现；若服务端无视协商仍返回 br，会明确拒绝而非误解码。 |
| **未交付 · OCSP（R420 结论）** | [R420](../artifacts/receipts/ruyijs-linux-ocsp-conclusion-r420/validation.json)：响应被缓存且判定执行（stage 21），但 revoked 仍判 good。需 NSS 认可的签名者，属夹具工程。 | 三轮已排除编码、符号、模式、接线、缓存拒绝。**不再投入**。 |
| **有阻碍 · OCSP（R418）** | [R418](../artifacts/receipts/ruyijs-linux-ocsp-attempt-r418/validation.json)：已接线并构建，但 revoked 响应未被采信，三者都返回 0。疑似签名者信任未建立。 | **未交付**。需先解决 NSS 对响应签名者的接受条件。 |
| **已探明 · 吊销机制范围（R416）** | [R416](../artifacts/receipts/ruyijs-linux-revocation-scope-r416/validation.json)：OCSP 可链接（`CERT_CheckOCSPStatus`），CRL 声明在头文件但未导出。 | **未实施吊销判定**；OCSP 需在线响应器，工作量大于解码路径。CRL 需重编 NSS。 |
| **已验 · 炸弹经 TLS 链路（R415）** | [R415](../artifacts/receipts/ruyijs-linux-bomb-e2e-r415/validation.json)：真实服务端发炸弹，br 与 zstd 都在链路上以准确理由拒绝。 | 剩余缺口是 CA 信任、吊销、PKIX、h2、QUIC、ARM64。 |
| **已验 · 炸弹边界（R414）** | [R414](../artifacts/receipts/ruyijs-linux-bomb-bounds-r414/validation.json)：br 与 zstd 均拒绝 50 MiB 炸弹且理由准确；修掉 brotli 误报"无效"的问题。 | 链路层炸弹未验；OCSP/CRL、默认根库、PKIX、h2、QUIC、ARM64 仍未签收。 |
| **已验 · zstd 端到端（R410）** | [R410](../artifacts/receipts/ruyijs-linux-zstd-e2e-r410/validation.json)：进入 wheel，按协商返回并解出原文，200。 | 压缩编码这块（gzip/deflate/br/zstd）**已完成**。剩余缺口是 CA 信任、吊销、PKIX、h2、QUIC、ARM64。 | [R409](../artifacts/receipts/ruyijs-linux-zstd-decode-r409/validation.json)：树内源码可编出并解出独立编码器数据，`-DZSTD_DISABLE_ASM` 必需。 | **完全未接入产品**：不进 `tls.py`、不进 wheel、协商未变。与 brotli 的差距就在这里。 |
| **已验 · brotli 端到端（R408）** | [R408](../artifacts/receipts/ruyijs-linux-br-e2e-r408/validation.json)：真实服务端按协商返回 brotli，JS `fetch()` 解出原文，200。 | zstd 未做；OCSP/CRL、默认根库、PKIX、h2、QUIC、ARM64 仍未签收。 |
| **已验 · brotli 已打包（R407）** | [R407](../artifacts/receipts/ruyijs-linux-brotli-packaged-r407/validation.json)：库进入 wheel，声明 `br`，经**包内 API** 解出独立编码器数据。 | 真实 `br` 响应经 TLS 端到端未验；zstd 未做。 | [R406](../artifacts/receipts/ruyijs-linux-brotli-wiring-r406/validation.json)：`tls.py` 与打包映射已改好，27 个测试通过；wheel 构建因 brotli 源码不在密封 SDK 中而失败。 | 需把 `modules/brotli` 放进构建可见位置；`br` 端到端仍未验。 |
| **已验 · brotli 解码库（R405）** | [R405](../artifacts/receipts/ruyijs-linux-brotli-decode-r405/validation.json)：独立编码器压缩的数据被树内源码编出的解码器正确解出，逐字节断言通过。 | **仅覆盖解码库**；接入 `tls.py`、打包、真实 `br` 响应端到端、zstd 均未做。 | [R404](../artifacts/receipts/ruyijs-linux-brotli-roundtrip-r404/validation.json)：改用后台作业突破长命令限制；找到根因——头文件是符号链接，`cp -r` 复制了链接。`cp -L` 修复已备好。 | decode 仍未证明；同类问题 R358 曾遇过。 | [R403](../artifacts/receipts/ruyijs-linux-brotli-roundtrip-r403/validation.json)：拆成最短步骤后，单挂载仅 `ls` 可返回，**编译仍每次超时**；本机 aarch64 无法代验。状态已就绪，只差一次能撑住的编译。 | 阻塞是链路时长，非产品缺陷。 | [R402](../artifacts/receipts/ruyijs-linux-brotli-roundtrip-r402/validation.json)：库已编出、测试与数据就绪；阻塞是**链路无法维持长命令**（短命令 12/20 可达），非产品缺陷。 | 待链路可用即可执行，无需重建。 | [R400](../artifacts/receipts/ruyijs-linux-brotli-roundtrip-r400/validation.json) / [R401](../artifacts/receipts/ruyijs-linux-brotli-roundtrip-r401/validation.json)：库已编出但解码未证明；R401 把报错来源定位到**宿主机** `/usr/bin/sh` 缺失而非镜像。 | 下一步应先确认宿主机 shell 布局，再用当初编库成功的那条命令形态运行。 | [R400](../artifacts/receipts/ruyijs-linux-brotli-roundtrip-r400/validation.json)：库已编出（187,456 字节）但**未证明能解码**；工具链镜像的 clang 路径在 `--entrypoint` 下无法解析，取证物已备好待续。 | 这是当前最接近可交付的一项，只差一次成功的编译-运行；源码、测试数据、脚本均已就位。 |
| **未做 · 压缩编码覆盖（已被 R391 缓解）** | 当前只解 gzip 与 deflate；`Content-Encoding: br` 与 `zstd` 会被明确拒绝而不是静默返回错误内容。 | 真实服务端常返回 `br`，缺失意味着部分站点不可用。**R398/R399 实测**：固定构建未编译解码器（`modules/brotli/` 只有 5 个编码器 `.o`，`dist/` 内 brotli 文件 0 个），**但解码器源码随树存在**（`dec/` 6 个 `.c`、`common/` 6 个 `.c`）。R399 用这些源码成功编出 `libbrotlidec.so`（187,456 字节）。所以先前"需引入完整源码"的判断也不准确——源码就在树内，正确说法是**未编译、未接入打包**。 |
| **已验 · 解压安全** | [R383](../artifacts/receipts/ruyijs-linux-decode-r383/validation.json)：压缩流后多余字节、双成员、deflate+垃圾均拒绝；100 MiB 压缩炸弹被 8 MiB 上限拦住。 | 只覆盖 gzip/deflate；brotli、zstd 未实现。 |
| **已验 · 证书链元素校验** | [R382](../artifacts/receipts/ruyijs-linux-chain-elements-r382/validation.json)：每个元素都验 DER 标签与长度，11 项畸形矩阵 0 不符；名字解析与摘要解析对畸形数据结论一致。 | 只覆盖结构合法性，不涉及 RFC 5280 路径语义（该引擎在本构建缺失）。 |
| **已验 · 主机名匹配加固** | [R381](../artifacts/receipts/ruyijs-linux-hostname-hardening-r381/validation.json)：修复星号字面量匹配、通配符空标签、畸形分隔符三个缺陷；18 项单元矩阵 0 不符。 | 覆盖 DNS/IP 名称匹配；未涉及 IDNA 国际化域名的完整 UTS-46 处理。 |
| **已验 · 累积回归** | [R380](../artifacts/receipts/ruyijs-linux-regression-r380/validation.json)：六项正向与四项负向在同一 wheel 上同时通过，明文路径未被 TLS 相关改动破坏。 | 回归集覆盖 HTTP/1.1 与证书路径；h2、QUIC、ARM64 无对应实现可回归。 |
| **已验 · NSS 生命周期范围** | [R379](../artifacts/receipts/ruyijs-linux-nss-lifetime-r379/validation.json)：锚点在单进程内累积；4 次连续带锚点请求各自正确。 | 复用长命 helper 时的按主机隔离未实现，需要时应改为每主机独立进程。 |
| **已验 · JS 路径链校验** | [R378](../artifacts/receipts/ruyijs-linux-js-anchor-r378/validation.json)：JS `fetch()` 与 Python API 走同一校验；错误锚点拒绝，锚点被替换亦拒绝（摘要校验）。 | OCSP/CRL 与公共 CA 根库仍缺。 |
| **已验 · 锚点接入 HTTPS 路径** | [R376](../artifacts/receipts/ruyijs-linux-anchor-r376/validation.json)：声明锚点时在握手钩子内做链校验；错误 CA 与非 CA 锚点均拒绝且 0 请求。 | 未做 OCSP/CRL 与公共 CA 根库，故仍不等于通用公网信任。 |
| **部分已验 · 到 CA 链校验（独立工具，已被 R376 取代）** | [R375](../artifacts/receipts/ruyijs-linux-chain-legacy-r375/validation.json)：旧校验器可完成叶子→CA 校验；修复了非 CA 锚点被信任的缺陷。 | 尚未接入适配层与 JS 路径；OCSP/CRL 吊销不可用；PKIX 仍不可用。 |
| **未完成 · PKIX 引擎** | [R374](../artifacts/receipts/ruyijs-linux-chain-r374/validation.json)：固定 NSS 3.131 构建的 `CERT_PKIXVerifyCert` 返回 `PR_NOT_IMPLEMENTED`，两种初始化方式均如此。 | 这是**信任模型的真实缺口**：当前只有叶子固定值、有效期与主机名匹配，没有 RFC 5280 路径校验与吊销检查。需要重编 NSS 或自行实现。 |
| **已验 · 代理失败关闭** | [R373](../artifacts/receipts/ruyijs-linux-proxy-r373/validation.json)：配置代理时明文与 HTTPS 均拒绝、对端 0 连接、无直连泄漏。 | 这是拒绝而非支持：CONNECT、SOCKS5、PAC 均未实现，代理场景不可用。 |
| **已验 · 传输一致性** | [R372](../artifacts/receipts/ruyijs-linux-parity-r372/validation.json)：明文与 TLS 在九个 framing 用例上结果一致；修复前无长度响应只在明文侧被接受。 | 一致性只覆盖 HTTP/1.1 framing；h2 与 QUIC 无对应实现可对照。 |
| **已验 · 并发隔离** | [R371](../artifacts/receipts/ruyijs-linux-concurrency-r371/validation.json)：12 并发全部正确，混合失败场景其余 8 个不受影响，峰值 RSS 约 11 MB。 | 无连接复用与稳态负载压测；h2 多路复用未实现。 |
| **已验 · 资源边界** | [R370](../artifacts/receipts/ruyijs-linux-bounds-r370/validation.json)：响应/请求头块上限 64 KiB，body 上限 8 MiB，超限均给具体原因；修复前 80 KB 响应头会被接受。 | 未做并发连接数上限与整体内存预算的压测。 |
| **已验 · ALPN 守卫** | [R369](../artifacts/receipts/ruyijs-linux-alpn-r369/validation.json)：对端选中 h2 时在任何字节前拒绝且 0 请求；ALPN 空或 http/1.1 时正常。缺陷是**潜在**的，出厂路径 `http2=False` 时不可达。 | 真正的 HTTP/2 帧与多路复用未实现，h2 站点仍不可用。 |
| **已验 · HTTPS 重定向** | [R368](../artifacts/receipts/ruyijs-linux-redirect-r368/validation.json)：同源 302 被跟随且 URL 更新；指向未固定主机的 302 被拒，目标 0 次 HTTP。同时修复了 IP SAN 不可见的 DER 解析缺陷。 | 跨协议跳转链（http→https）、h2 与 QUIC 下的重定向语义未验。 |
| **已验 · 主机名校验** | [R367](../artifacts/receipts/ruyijs-linux-hostname-r367/validation.json)：SAN 解析后按 RFC 6125 匹配；同一叶子固定到两个名称时，错误名称在握手中被拒、HTTP 0 次。修复前该场景是放行的。 | 仍未做 RFC 5280 到根路径校验与吊销检查，故"主机名正确"不等于"证书受信任"。 |
| **已验 · 证书固定粒度与有效期** | [R366](../artifacts/receipts/ruyijs-linux-pin-scope-r366/validation.json)：固定值只比对叶子证书，有效期由 DER 解析后按系统时钟校验；错误叶子被拒。 | 未做 RFC 5280 到根路径校验、OCSP/CRL 吊销、外部 CA 信任。这两者是信任模型的真实缺口，不能由"已验"字样掩盖。 |
| **已验 · navigate() 走 HTTPS** | [R365](../artifacts/receipts/ruyijs-linux-navigate-https-r365/validation.json)：文档与外部脚本经 TLS 加载并执行；错误固定值时 0 字节 HTTP、文档为空。 | 未覆盖外部 CA、公网来源、跨协议跳转链、h2 与 QUIC。 |
| **已验 · 组件生命周期与回退** | [R364](../artifacts/receipts/ruyijs-linux-companion-lifecycle-r364/validation.json)：252 → 285 文件（新增 33），基础文件零改写；卸载后逐字节还原基础树并回到离线行为。 | 未覆盖在既有业务数据上的升级路径、并发安装与 `--user` 安装形态。 |
| **已验 · 可安装的 RuyiJS HTTPS** | [R361](../artifacts/receipts/ruyijs-linux-installed-js-https-r361/validation.json)：两个 wheel 纯 pip 安装后，JS `fetch("https://…")` 拿到服务端生成的 body，`net_log` 200；组件自带完整 10 库 NSS 闭包。 | 外部 CA 信任、公网来源、h2 语义、QUIC/h3、`navigate()` 的 HTTPS 与 ARM64 仍单列。 |
| **已验 · RuyiJS JS 层固定证书 HTTPS（手工布局）** | [R360](../artifacts/receipts/ruyijs-linux-js-https-r360/validation.json)：安装态 R356 壳的 `fetch()` 走 `https:` 后，独立 TLS 服务端记录到 `GET /direct`，返回体与 JS 读回逐字节一致。错误固定值时 JS 得 `TypeError`，服务端接受 1 次 TCP 但收到 0 字节 HTTP。根因是缺少 bundled-interpreter 启动器，补上即通。 | 外部 CA 信任链、公网 HTTPS、h2 语义、QUIC/h3、`navigate()` 的 HTTPS 与 ARM64 均未签收。 |
| **部分已验 · RuyiJS TLS 原生层** | [R358](../artifacts/receipts/ruyijs-linux-tls-r358/validation.json)：固定 NSS 3.131 的 TLS 1.3 握手、ALPN 协商、不受信任证书拒绝，以及基于 DER 证书固定值的 HTTPS 客户端往返均已实测；未配置固定值直接拒连；固定值不匹配在 TLS 握手中止，不发送 HTTP 请求字节。 | 仍需 JS `fetch()`/`navigate()` 的 HTTPS 端到端与外部 CA 信任；h2 语义、QUIC 与 ARM64 另验。 |
| **部分已验 · RuyiJS 明文 HTTP/1** | [R357 组件](../artifacts/receipts/ruyijs-linux-http1-r357/validation.json)在 R356 安装态上真实收发：JS 读到回环服务新生成的挑战，GET/POST/HEAD/404、二进制体、参数、gzip/deflate/chunked、导航及外部脚本均经服务端核对；独立 C 程序也取得新响应。卸载该组件恢复 R356 原文件树。 | 该项只覆盖 libc 上的私有明文 HTTP/1。HTTPS 另有条目（R358 适配层、R360/R361 安装态、R376 锚点链校验）。**仍需** h2、QUIC/h3、OCSP/CRL、公共 CA 根库与代理支持各自实测；未列出者不得据本项推断。 |
| **P2 · 架构与宿主** | Trace 有独立 ARM64 浏览器及虚拟桌面证据；MCP 有双架构 core；Http 已核验 Linux ARM64 和 Intel macOS 原生库。 | RuyiJS ARM64、Trace 生产 ARM64 共会话、物理显示分别建包验收；仅在要承诺更低 glibc 时做相应目标发行版测试。Trace 托管检查曾因计费未获 runner，应在 runner 可用后重跑；已有本地源码通过记录与 hosted CI 分开。 |
| **使用 RuyiDOM 时 · 独立仓与制品维护者** | ARM64 源码版镜像已在 Noble 容器内通过真实浏览器验收，归档在原 Docker 存储回载后复测；见[v0.3.0 发行回执](../artifacts/receipts/ruyidom-arm64-source-v0.3.0.json)和[主机操作入口](14-source-handoff.md#ruyidom-独立源码交接)。 | 第二台 ARM64 主机的空存储冷导入仍未验证。裸 Jammy 的动态库版本不足，优先使用已验收的 Noble 镜像；`native` 的 HTTP 导航受限属已知边界，真实导航选择 `browser`。 |

**另有一条不能合并的发布线。** [常驻采集 CLI2 产品标签](https://github.com/Facetomyself/ruyitrace/blob/f3f45baaee75a700ed4d41fdc5e4e70d977df1b6/product/release-lock.json)锁定实际 CLI 输入 `29a1111`，复用 R5 内核。它验过 256 个开关代际、512 条原生边界与同一宿主的空 Docker 引擎加载。Trace 主线的常驻修复 `61a4c15`、平台 Trace pin、CLI2 产品镜像是不同对象；CLI2 证据不自动继承生产 M2。若下游需要“一份镜像兼有常驻配额与 MCP 借用”，先合成一个明确版本，再在**同一镜像摘要**上同时通过这两组测试。第二物理宿主、严格内容进程过滤证据仍应单列。

下列 A/B/C/D 条目保留原始调查和纠错过程。编号数量不是当前未完成项计数；例如 B3 的 backports 与 D2 的六项 Windows 假设在 [HTTP 状态账本](../STATUS.yaml) 已列为关闭。

---

## A 级：会阻断 Linux 适配

### ~~A1 · `_pipe.py` 是 Windows 独占~~ → **已降级为 B 级**

**初版误判**。复查 `ff-ruyijs` 0.4.1 源码后发现：

```bash
cd /var/lib/dsh/Ruyi/RuyiJS/upstream-ff-ruyijs
head -5 python/ruyijs/_pipe.py
# """Bounded local frame transport.
#  Windows keeps the overlapped named pipe. macOS uses a Unix socket with the
#  same 4-byte little-endian length prefix and 16 MiB frame cap."""
grep -c 'AF_UNIX' python/ruyijs/_pipe.py    # ≥1 → 已实现
```

上游 `_pipe.py` **208 行，已含非 Windows 的 AF_UNIX 分支**；`_runtime_paths.py`（59 行）、`_context.py`（495 行）同样已平台化。

**真正的问题改成**：内部 wheel `0.2.2+inner.*` 是上游 0.4.1 之前的快照，没合这些代码。

- **影响**：只需覆盖 4 个 `.py`（约 2 小时），不是重写
- **改法**：见 `03-linux-port.md` L2
- **验证**：`diff -rq RuyiJS/upstream-ff-ruyijs/python/ruyijs RuyiJS/source/_wheel/ruyijs` 只剩 `_runtime`/`examples` 差异

### A2 · `libnecko_core.so` 要求 glibc 2.38

```bash
objdump -T RuyiHttp/repo/native/linux_x86_64/libnecko_core.so \
  | grep -o 'GLIBC_[0-9.]*' | sort -uV | tail -1     # → GLIBC_2.38
ldd --version | head -1                              # 本机 → 2.35
```

本机 `dlopen` 报 `cannot open shared object file`（`DT_NEEDED` 齐但符号版本不满足）。

- **影响**：Ubuntu 22.04 / Debian 12 及更旧系统直接用不了
- **选项**：
  1. 目标机升级到 Ubuntu 24.04+（wheel tag 已是 `manylinux_2_39`）
  2. 降 `--target-glibc` 重编（`docs/build-native.md` 说支持 `RUYIHTTP_GLIBC`）
- **决策**：待定，倾向选项 1

### A3 · ruyijs 内部版原生壳无源码，需反编译

```bash
# 内部 wheel 只有二进制壳
unzip -l '/tmp/ruyijs_whl/ruyijs.whl' | grep '_runtime/dist'
# → dist/js.exe 50,256,896 B / mozglue.dll / CRT
```

Python 层 19 文件是明文，但 `dist/js.exe`（49.5 MB，含 38 个浏览器子系统与管道 IPC 服务端）只有二进制。

- **影响**：`ruyijs-inner` 无法在 Linux 上产出，除非还原出可编译源码
- **减压因素**：`build-identity.json` 给出 2038 个源文件的**路径 + sha256**，是罕见 ground truth
- **方案**：见 `06-ruyijs-inner.md`，P0–P2 优先
- **决策**：反编译先行；P0–P2 完成即可覆盖主要用途

### A4 · RuyiTrace 内核 domtrace 源码缺失

```bash
grep -r 'domtrace' RuyiTrace/app-3.5.0/resources/kernel/ --include='*.py' --include='*.c' -l | head
# → 无输出
find RuyiTrace/app-3.5.0/resources/kernel/moz-src -type d -name domtrace   # → 无输出
```

`kernel/moz-src/` 只有 572 文件 / 12 MB，是被删减的片段，不含 `dom/bindings/domtrace`。`ff-ruyijs` 仓库 grep `domtrace` 也是零命中。

- **影响**：Linux 上复现 domtrace 等于从零实现 74 个开关的插桩
- **选项**：见 `02-source-recovery.md` §4.3 方案 A/B/C
- **决策**：**建议先跑方案 A（10 分钟验证存在性），失败立刻并行 C（问上游）+ B（反推）**

---

## B 级：会拖慢维护

### B1 · `necko` Python 层被 fork 成两份

| 位置 | 版本 | `_transport.py` |
| --- | --- | --- |
| `RuyiHttp/repo/ruyihttp/` | `0.9.0` | 1260 行 |
| ruyijs wheel `vendor/.../necko/` | `0.8.2` | 1337 行 |

`__init__.py` 只有 1 行差异（版本号），`_http3.py` 差 220 行，`_transport.py` 差 362 行。

- **后果**：每个 Linux bug 要修两次，且两边会渐行渐远
- **建议**：合流成一个外部包（例如 `ruyinecko`），两边都当依赖引用
- **验证**：`diff -r RuyiHttp/repo/ruyihttp /tmp/necko_from_ruyijs | wc -l` → 约 1100 行差异

### B2 · 三份 `necko_posix` 源码副本

| 副本 | 来源 |
| --- | --- |
| `ff-ruyijs/native/necko_posix/` | 上游 |
| `RuyiHttp/repo/native/linux_x86_64/` | 二进制，源码未纳入 |
| ruyijs wheel `vendor/necko-derived/` | Python 层，原生库为 dll |

- **建议**：抽成 submodule，三处共享
- **验证**：`git ls-tree -r HEAD native/necko_posix/src/ | wc -l` → 8 个源文件

### B3 · `backports` 依赖写错

```bash
cd RuyiHttp/repo && python3 -c "import ruyihttp"
# → ModuleNotFoundError: No module named 'cryptography.x509.verification'（旧 cryptography）
# → ModuleNotFoundError: No module named 'publicsuffixlist'
# → ModuleNotFoundError: No module named 'backports'
```

`_nss.py:34` 是 `from backports import zstd`（无条件），而 `pyproject.toml` 写 `backports.zstd>=1.0; python_version < '3.14'`。PyPI 包名 `backports.zstd` 的导入名是 `backports.zstd`，`from backports import zstd` 依赖隐式命名空间包行为，Python 3.10 上会失败。

- **改法**：`try: import zstd / except ImportError: from backports import zstd`
- **验证**：干净 venv 里 `pip install -e .` 后 `import ruyihttp` 无异常
- **注意**：上游 ruyijs 的 `vendor/.../necko/_nss.py` 有同样写法，**合流时要一起修**

### ~~B4 · `dist/` 两个 wheel 与 `native/` 脱钩~~ → **已解决**（2026-11-19）

已归档到 `submodules/ruyihttp/dist-v0.9.0-legacy/`，三个平台重新构建并通过
hash 校验（26 个原生文件全匹配）。详见该目录的 `VERIFICATION.md`。

| wheel | 问题 |
| --- | --- |
| `ruyihttp-0.9.0-py3-none-win_amd64.whl` | manifest 是旧结构（`platform` + 扁平 `sha256`），文件在包根 |
| `ruyihttp-0.9.0-py3-none-macosx_26_0_arm64.whl` | dylib 哈希与 `native/darwin_arm64/provenance.json` **全部不符**，**缺 `libnecko_quic.dylib`** |
| linux | **不存在** |

- **建议**：`git mv dist/ dist-v0.9.0-legacy/`，重新构建三平台
- **验证**：新的 linux wheel 里 `unzip -l` 应含 14 个 `.so`

---

## C 级：文档与实现不一致

### C1 · domtrace 开关数量三处不一致

| 来源 | 数量 |
| --- | --- |
| `README-cheatsheet.md` 开头 | 69 |
| `switches.js` 注释 | 67（+1 废弃） |
| `switches.js` 实际数组 | **74** |
| `xul.dll` strings | **74** |

```bash
# 复现
cd RuyiTrace/app-3.5.0/resources
python3 -c "
import re
t=open('../unpacked-asar/src/shared/switches.js',encoding='utf-8').read()
print('switches.js:', len(re.findall(r\"env: '([A-Z0-9_]+)'\", t)))
"
strings -a kernel/xul.dll | grep -oE 'MOZ_DOM_[A-Z0-9_]+' | sort -u | wc -l
```

- **结论**：**74 是正确的**，文档陈旧
- **建议**：以 `switches.js` 做单一真相源，自动生成 cheatsheet，别手写

### C2 · `MOZ_DOM_HTTP_PACKET_TRACE_MAX_PENDING` 的读取层

初版只在 DLL 搜索，误称为幽灵开关。Win64 3.5.0 随包 `HttpPacketTrace.sys.mjs` 的 `getMaxPendingWrites()` 实际读取它，合法范围 1–8192，默认 256；这是 **JS 队列参数**，不计作额外原生开关。以下命令只说明文档与原生字符串的差异。

```bash
grep -c 'HTTP_PACKET_TRACE_MAX_PENDING' RuyiTrace/app-3.5.0/resources/domtrace/README-cheatsheet.md  # ≥1
strings -a RuyiTrace/app-3.5.0/resources/kernel/xul.dll | grep -c 'HTTP_PACKET_TRACE_MAX_PENDING'   # 0
```

### C3 · ruyijs `SOURCE_NOTICE` 指向 0.3.3，版本号却是 0.2.2+inner

```bash
cat RuyiJS/source/_wheel/ruyijs/_runtime/SOURCE_NOTICE.md   # 已随解包删除，需重新解
# Package: https://pypi.org/project/ruyijs/0.3.3/
# Version: 0.2.2+inner.492ee47
```

两个内部构建：
- `+inner.492ee47`：**无** `build-identity.json`，溯源链断裂
- `+inner.20261101191032`：**有** `base_commit aa255fbb…`、`working_tree_changes: true`、`source_files_verified: 2038`

- **建议**：fork 里补 `PROVENANCE.md`，每个 wheel 必须带 `wheel → ff-ruyijs commit → firefox commit` 三元组

### C4 · `SHA256SUMS` 用 CRLF 分隔

```bash
cd RuyiJS/source/_wheel/ruyijs/_runtime
sha256sum -c SHA256SUMS                    # → 全部 "FAILED open or read"
sed 's/\r$//' SHA256SUMS > /tmp/sums.txt
sha256sum -c /tmp/sums.txt | grep -c ': OK$'   # → 1579
```

**文件本身没问题**，只是行尾 CR 让 `sha256sum` 找不到文件。文档里要写明。

### C5 · `kernel/moz-src/` 不是完整源码

```bash
find RuyiTrace/app-3.5.0/resources/kernel/moz-src -type f | wc -l   # → 572
du -sh RuyiTrace/app-3.5.0/resources/kernel/moz-src                 # → 12M
```
完整 Firefox 源码约 30 万文件 / 3 GB。这是删减片段，**只能参考不能重编**。

---

## D 级：环境与工具

### D1 · 本机 glibc 2.35 无法 live 验证 linux 原生库

见 A2。当前所有 linux 侧结论都是**静态检查**（ELF/ABI/符号/manifest），没有一条是实际发请求。

### D2 · 测试套件 6 项 Windows 假设

```bash
cd RuyiHttp/repo && /tmp/ruyivenv/bin/python -m unittest discover -s tests
# → 13 ok, 4 fail, 2 error
```

失败项：
- `test_windows_host_stays_win_amd64`（断言 `os.name=="nt"`）
- `test_default_core_names_follow_the_platform`（断言消息含 `necko_core.dll`）
- `test_windows_build_copies_native_dlls`
- `test_platform_profiles_and_user_agents`
- `test_quic_names_and_environment_override`（临时目录无 `.so`）
- `test_nss_gate_compares_packaged_version`

**这不是代码 bug，是测试的参数化缺失。** Linux 移植时必须修，否则 CI 永远红。

### D3 · RuyiJS 无测试套件

本地 `ruyijs` 包里没有任何 `tests/`。`ff-ruyijs` 有 13 个 smoke 脚本（`ci/*_check.py`），但那是对 ff-ruyijs 自己的构建，不是对内部 wheel。

- **建议**：Linux 移植后用 `ruyihttp` 的契约测试 + `ci/smoke_test.py` 当外环，内部至少补 `Context.eval` / `load_page` / `net_log` 三个冒烟。

---

### D-MCP · Linux 生产 Trace owner 同会话验收

AMD64 R5 的 Linux CLI [生产门禁](../projects/ruyi-mcp/PRODUCTION-OWNER.md)已通过。AMD64 真机租约自然到期与失效后控制权已[单独验收](../artifacts/receipts/trace-amd64-r5/borrowed-behaviors-b5e204a.json)；Electron owner、ARM64 生产、部署中的跨机器 SSH stdio，以及真实浏览器进程丢失仍为 `To be confirmed`；独立 ARM64 fixture 的回执仍只覆盖其有界范围。

## 历史决策清单（原始建议；当前选择见页首）

| # | 决策项 | 选项 | 建议 | 阻塞什么 |
| --- | --- | --- | --- | --- |
| 1 | 目标 glibc | 24.04+ / 降版本重编 | **24.04+** | A2 全部 |
| 2 | Firefox commit 基线 | `9a2dc53c` / `39bfd14c` / `2887d9de` | 原建议 `39bfd14c` 仅能标识 Win64 私有内核；Linux Trace/R353 用官方 `9a2dc53c`，见 [PINS](../PINS.md) | 旧建议已替代 |
| 3 | domtrace 源码 | A 官方树 / B 反推 / C 问上游 | **A 先验证 10 分钟，C 并行** | 阶段 4（占 70% 工作量） |
| 4 | `necko` Python 层 | 两份独立 / 合流成一个包 | **合流** | B1，长期维护成本 |
| 5 | `necko_posix` 源码 | 三份副本 / submodule | **submodule** | B2 |
| 6 | ruyijs 内部版路线 | 以上游 0.4.1 为基 / **反编译还原** | **反编译还原**；上游只作对照（`ff-ruyijs` 不得承载内部功能） | A3、B1、B2 |
| 8 | ruyijs 反编译范围 | 全量 / P0–P2 | **P0–P2**（eval/set/expose/load_page/navigate + 管道 + 指纹配置） | A3 |
| 7 | RuyiTrace Linux 形态 | 完整移植 / 只做 CLI 复现 | **先做 CLI**（跳过 Electron，直接照 `firefox-environment.cjs` 拼 env 拉 firefox） | L3 |


---

## 附：本文的更正记录

| 轮次 | 更正内容 |
| --- | --- |
| 2026-11-26 · RuyiDOM | [v0.1.0](../artifacts/receipts/ruyidom-source-v0.1.0.json)的「ARM64 Docker 待验」是历史结论。[v0.3.0](../artifacts/receipts/ruyidom-arm64-source-v0.3.0.json)已关闭这项缺口；第二台主机冷导入另列，不因同机回载通过而关闭。 |
| 初版 | A1 判定「`_pipe.py` 需整文件重写 127 行」 |
| **更正** | 上游 ff-ruyijs 0.4.1 `python/ruyijs/_pipe.py` 已 208 行且含 AF_UNIX 分支；内部 wheel 只是旧快照。降级为「覆盖 4 个文件」。 |
| 初版 | 预估 RuyiJS Linux 适配为「中（重编 js 壳）」 |
| 二次更正 | 曾判定「Python 层覆盖上游 4 个文件即可」。**再更正**：`ff-ruyijs` 是 public fork，只作 PR 目标与反编译对照，**不作内部基线**。内部版 `js.exe` 需反编译还原，见 `06-ruyijs-inner.md`。 |
| **定论** | Python 层改动小（19 文件仅 5 处差异）；**真正成本在 `js.exe` 反编译**（49.5 MB C++）。Linux 适配的成败取决于原生壳能否还原。 |
