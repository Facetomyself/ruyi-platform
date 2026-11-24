# RuyiJS（内部版）

仓库：`Facetomyself/ruyijs-inner`（private，**已存在**：2026-11-04 创建，7.4 MB，默认分支 `main`）
挂载：`submodules/ruyijs`
上游参考：`Facetomyself/ff-ruyijs`（public fork，**只作 PR 与对照，不作基线**）

## 是什么

Firefox 159 的 SpiderMonkey + 38 个浏览器子系统的 Python 可编程封装。跑在独立进程里，通过本地帧传输与 Python 通信。

## 三层结构

| 层 | 体积 | 源码状态 |
| --- | --- | --- |
| Python 绑定 `ruyijs/*.py` | 60 KB / 19 文件 | ✅ 明文 |
| `necko` 适配器 `vendor/.../necko/` | 200 KB / 13 文件 | ✅ 明文 |
| 原生壳 `dist/js.exe` | 49.5 MB | ❌ 需反编译 |
| 内嵌 CPython 3.14 | ~15 MB | ✅ 官方产物 |

## 两个已有构建

| 版本 | 大小 | Engine | examples | client.dll |
| --- | --- | --- | --- | --- |
| `0.2.2+inner.492ee47` | 46.0 MB | ✅ | 26 个 | ❌ |
| `0.2.2+inner.20261101191032` | 46.6 MB | ❌ | 0 | ✅ |

记录：`artifacts/manifests/ruyijs-inner-*.yaml`

## 期望目录（ruyijs-inner 建库后）

```
ruyijs-inner/
├── src/                      反编译还原的 C++（2069 文件，按 build-identity 的 2038 条路径）
├── python/ruyijs/            19 个 .py（明文，从 wheel 取）
├── native/                   necko C/C++/Rust
│   ├── necko_tls/            Windows：necko_tls.c 863 / necko_exchange.c 823
│   ├── necko_posix/          Linux：tls.cpp 148 / http1.cpp 144 / socket.cpp 125
│   └── necko_quic/           两平台：lib.rs 1007
├── tests/                    契约断言（见 docs/06 §4）
├── tools/                    构建脚本
└── docs/                     本项目文档
```

## 反编译方案

见 [`../../docs/06-ruyijs-inner.md`](../../docs/06-ruyijs-inner.md)。

**优先级**：P0（eval/set/expose/load_page/navigate）→ P1（管道协议）→ P2（指纹配置）→ P3–P6。

## 当前状态

**语义重建进行中**（不是从 0 开始）。

| 分类 | 数量 |
| --- | ---: |
| identity 总数 | 2038 |
| eol-insensitive 对齐 0.2.1 | 1792 |
| hash_diff | 237（56 条 identity 命中） |
| inner_only | 9（全部语义化） |

最大缺口：`page_storage` / `browsing_context` / `draw` / `css_color_resolve`。

详细进度见 [`reverse-analysis.md`](reverse-analysis.md)。

### Linux x86_64 私有 donor

**当前联网组件（R357）：独立安装的 `ruyijs-http1 0.1.0+inner.r357` 为 R356 壳补齐明文 HTTP/1 helper。** [安装与实测说明](../../submodules/ruyijs/docs/linux-http1.md) · [R357 回执](../../artifacts/receipts/ruyijs-linux-http1-r357/validation.json) · [运行与归属检查](../../artifacts/receipts/ruyijs-linux-http1-r357/runtime-gates.json)。

- 组件 wheel 37,532 字节，SHA-256 `66121abc2983a51bbd859b2f894169a04186e5bb0bc48453b7fb4e4f124a4b9b`；私有 C 源、8 个锁定输入和 16 个导出符号固定，直接构建与源码包再构建字节一致。它不替换或修改 R356 的基础 wheel。
- 在 R356 安装态、UID 1000、仅回环网络的真实环境中，服务端观察到 JS 发出的 GET、二进制 POST、HEAD 与 404 请求，返回在服务端新生成的挑战，JS 逐字节读回；导航文件和外部脚本亦分别核对。每笔交换的客户端套接字属于载入该组件的 helper 进程。
- `gzip`、`deflate`、分块传输均解码正确，截断的定长响应成为 `TypeError`，畸形/断开后可重试；显式代理和 HTTPS 都没有产生越界连接。独立 C 程序和 IPv6 回环也取得新响应。卸载组件后，R356 的文件树、13 组离线测试与 Worker/WebCrypto 全部恢复通过。
- 边界：**这不是 Mozilla Necko/NSS**，无 TLS、h2、h3/QUIC、代理或外网验收。匹配真实 Necko/NSS 的 helper 与协议族、Linux ARM64 产品仍分别待办。

**可安装的 HTTPS 组件（R363）：`ruyijs-http1 0.2.2+inner.r363` 让纯 pip 安装的 JS `fetch()` 走 HTTPS，并支持分块、gzip 与 deflate 响应。** [R361 安装回执](../../artifacts/receipts/ruyijs-linux-installed-js-https-r361/validation.json) · [R363 编码回执](../../artifacts/receipts/ruyijs-linux-js-https-framing-r363/validation.json)

- 组件 wheel 5,255,218 字节，SHA-256 `bcadfcace6714d043e6a454702e2a9f65364b4ac507a987455da7366f148196a`。内含固定 NSS 适配库 `libruyijs_tls.so`、完整 10 个 NSS 库闭包、`tls.py` 与启动器；基础 R356 wheel 不变。
- 在一个新建 venv 里只装这两个 wheel（无手工拷贝），JS `fetch("https://…")` 得到服务端新生成的 body 且逐字节一致，`net_log` 记录 200。私有 DER 证书固定模型，未配置或错误固定值仍拒绝。
- **R363：** 分块、gzip、deflate 三种 HTTPS 响应在安装后的 JS 中均解码为同样的 5120 字节（校验和 652800）。同时修复一个真实安全缺陷：NSS 会话恢复会让后续握手跳过证书校验，现在每次交换使用独立 peer id 强制完整握手并校验。
- 打包流程现在会在构建期校验 NSS 闭包完整性并拒绝不完整集合。本轮据此发现并修复了缺失的 `libmozsqlite3.so`（`libsoftokn3` 的加载期依赖）以及构建路径符号链接导致的悬空头文件。

**ALPN 守卫（R369）：修掉一个静默降级——对端选中 h2 时曾把 HTTP/1.1 请求行写进 h2 通道。** [回执](../../artifacts/receipts/ruyijs-linux-alpn-r369/validation.json)

- 修复前：服务端 ALPN 选中 `h2`，客户端仍写出 `GET /alpn HTTP/1.1`，服务端按 HTTP/1.1 解析并回了 200，JS 看到"成功"——错误被完全掩盖。
- 修复后：只在 ALPN 为空或 `http/1.1` 时发送 HTTP/1.1 请求；对端选中 `h2` 直接报 `peer selected h2; this helper implements HTTP/1.1 only`，服务端读到的是连接关闭、**0 个**请求。
- 明确一点：ALPN 未协商时回退 HTTP/1.1 是 RFC 7301 的既定行为，不算降级；只有"已选中 h2 却退回去"才是问题。

**重定向与 IP SAN（R368）：同源 HTTPS 重定向正常跟随，未固定的异地主机被拒。** [回执](../../artifacts/receipts/ruyijs-linux-redirect-r368/validation.json)

- 正向：`302 → /final` 被跟随，`response.url` 更新为最终地址，body 与最终响应一致；服务端记录 `/start`、`/final` 两次请求，均经 TLS。
- 负向：302 指向 `https://localhost:<port>/final`（该主机未配置固定值），JS 得到 `TypeError`，`net_log` 明确记录 `no pinned certificate for localhost:…`，目标主机 **0 次** HTTP。
- 同时修掉 DER 解析缺陷：subject 偏移算错一位，导致扩展块从未被扫描、`iPAddress` 类型的 SAN 完全不可见——带 `IP:127.0.0.1` 的合法证书会被误判为主机名不符。

**主机名校验（R367）：修掉一个真实缺陷——证书属于别的主机名时曾会被接受。** [回执](../../artifacts/receipts/ruyijs-linux-hostname-r367/validation.json)

- 修复前：自定义校验钩子只比对固定值与有效期，完全不看主机名。实测 `wrong.example` 去连一张 `CN=localhost` 的证书，握手成功并写出了 HTTP 请求——这是可被利用的身份冒充缺口。
- 修复后：从 DER 解析 `subjectAltName` 的 `dNSName` 与 `iPAddress`；只有在证书完全没有 SAN 时才回退到 `commonName`；通配符仅匹配一个左侧标签。
- 实测隔离性：同一张叶子证书同时被 `localhost` 与 `other.example` 固定，`localhost` 成功取回 body，`other.example` 以 `name mismatch` 在握手阶段被拒，HTTP 请求 0 次。
- **仍未做**：到可信根的 RFC 5280 路径构建、OCSP/CRL 吊销、外部 CA 信任。

**证书固定收紧（R366）：只认叶子证书，并校验有效期。** [回执](../../artifacts/receipts/ruyijs-linux-pin-scope-r366/validation.json)

- 之前固定值只要匹配**链中任意一张**证书即通过——一个无关的中间证书就能满足另一张服务器证书的固定值。现在只比对**叶子证书**。
- 叶子证书的 DER 有效期被解析并与系统时钟核对，过期或尚未生效都在写出任何 HTTP 字节前拒绝。
- 实测：叶子固定值命中时返回对端 body；换成另一张有效证书的固定值被拒（`peer leaf certificate does not match any pinned digest`，服务端 `bad_certificate`）。
- **仍未做**：到根的完整 RFC 5280 路径校验、OCSP/CRL 吊销、外部 CA 信任。

**导航走 HTTPS（R365）：`Context.navigate()` 与外部脚本均经 TLS 加载，错误固定值不加载任何内容。** [回执](../../artifacts/receipts/ruyijs-linux-navigate-https-r365/validation.json)

- 正向：`navigate("https://…")` 提交文档后，`document.title`、`h1`、`location.href` 均与所供页面一致；页面引用的外部脚本经 TLS 取回并执行（`asset-ok`）；`net_log` 两条记录均为 200。
- 负向：固定值错误时导航**未传输任何 HTTP 字节**（TCP 1 次、HTTP 0 次），服务端在握手中以 `bad_certificate` 中止，文档标题与正文均为空。

**组件生命周期（R364）：安装与卸载都经过实测，卸载后精确还原基础树。** [回执](../../artifacts/receipts/ruyijs-linux-companion-lifecycle-r364/validation.json)

- 基础 R356 单独安装为 **252** 个文件；再装 `ruyijs-http1 0.2.2+inner.r363` 后为 **285** 个，新增 33 个，且没有任何基础文件被改写。
- 组件在位时，JS `fetch("http://…")` 得到服务端新生成的 body，服务端只看到 **1 次** GET。
- `pip uninstall ruyijs-http1` 后 helper、启动器与 vendor 子树全部移除，文件树与安装前逐字节一致（252 个文件全等）；此后基础运行时回到其文档所述离线行为，服务端 **0 次**连接。

**TLS 适配层（R358）：固定 Firefox 159 的 NSS 3.131 已原生编译并通过真实握手。** [回执](../../artifacts/receipts/ruyijs-linux-tls-r358/validation.json)

- `native/necko_tls/necko_tls.c` 用封存的 195 个头文件和固定 Firefox 构建的 NSS/NSPR 共享库编译为 `libruyijs_tls.so`（35,800 字节，SHA-256 `d5238c84…3c1a9e`），15 个导出符号与源码一致；依赖仅 `libnss3/ssl3/nssutil3/nspr4/plc4/plds4/libc`。
- 在仅回环网络的原生容器中完成三次 TLS 1.3 握手：显式 `http/1.1` ALPN、显式 `h2` ALPN、不协商 ALPN；均由独立 Python/OpenSSL 服务端核对版本、密码套件 `TLS_AES_256_GCM_SHA384` 和应用数据往返。
- 不受信任证书以 `SSL_ERROR_BAD_CERTIFICATE` 终止，服务端收到 `bad certificate` 告警。构建中发现的真实问题已记录：dist 头目录的符号链接指向 `/build/ff159/...`，单独绑定目录会全部悬空。
- **固定证书的 HTTPS 客户端（同批）：** `deliverables/linux-ruyijs-tls-r358/release/python/tls.py`（SHA-256 `8944de5e…2dfb6e`）通过该适配层完成一次真实请求/响应往返。信任模型是调用方提供 DER 证书的 SHA-256 固定值：未配置固定值的域名直接拒连；固定值不匹配时 TCP 连接会建立，但 TLS 握手以 `bad_certificate` 告警中止，不写入任何 HTTP 请求字节；空固定值集合视为配置错误。这不是公共 CA 信任库。
- **边界：** 上述仍是原生层与独立客户端验收，不是 RuyiJS JS 层 HTTPS。`Context.fetch()`/`navigate()` 走 HTTPS、外部 CA 信任、真实 Necko socket 进程、h2 多路复用语义、QUIC/h3、ARM64 与 wheel 发行均未在本次签收。

**基础 pip 交付（R356）：R355 干净重建的原生文件已封装为独立版本 `0.2.2+inner.20261101191032.r356`。** [安装、升级与回退命令](../../submodules/ruyijs/docs/linux-amd64-clean-wheel.md) · [R356 回执](../../artifacts/receipts/ruyijs-linux-amd64-wheel-r356/validation.json) · [同一虚拟环境的迁移记录](../../artifacts/receipts/ruyijs-linux-amd64-wheel-r356/lifecycle.json)。

- 新 wheel 为 `py3-none-linux_x86_64`，29,749,981 字节，SHA-256 `cec72669fdfed34ea39c02f8c04125e90535fc1bf06bff12e8ac11acf7285bd6`。20 个原生文件、4 份构建证据与 R355 归档逐字节一致；18 个 Python 模块仅变更版本常量。未上传公共索引，也未改写 R354。
- 真实下载件在 Ubuntu 24.04/glibc 2.39/CPython 3.12.3 断网安装。13/13 组、95 项断言通过；主进程和真实 Worker 各自加载包内的 18 个库，WebCrypto 结果及进程回收均核对。由安装后的头文件编译的 C 调用程序，在无编译器、无 Python 的 Ubuntu 镜像中取得 `42` 和 `ruyi40`。
- 同一 venv 完成 R354 → R356 → R354。错误哈希的升级请求保留原 221 个已安装文件；显式回退后连同安装元数据在内的整体哈希与升级前一致，卸载后恢复初始清单。R356 仍是离线版本：回环服务可用，页面读取预置资源返回 203；未命中资源时记录 `Necko worker startup failed`，服务端没有收到该请求。真实网络、Linux ARM64 产品另验。

**当前原生交付（R355，2026-11-24）：固定私有提交从空对象目录重建的 amd64 运行时，已解包实跑。** [交付回执](../../artifacts/receipts/ruyijs-linux-amd64-clean-r355/validation.json) · [编译覆盖](../../artifacts/receipts/ruyijs-linux-amd64-clean-r355/coverage-summary.json) · [产品测试](../../artifacts/receipts/ruyijs-linux-amd64-clean-r355/runtime-gates.json) · [构建与运行方式](../../submodules/ruyijs/docs/linux-amd64-clean.md)。

- `ab68b3c` 的 Git 归档有 2,949 个文件。20 个分片共 1,268 次原生编译，得到 1,268 个不同私有单元；链接前逐个重读 ELF、DWARF 源路径和散列。严格链接退出 0、0 项未定义和 0 条 LLD 警告；错误源码、替换对象以及只给 63 个对象的反例均在对应环节失败。
- 交付归档 `ruyijs-linux-amd64-clean-r355.tar.gz`，29,855,046 字节，SHA-256 `764e295727518b2927de7fca901cd60b4390cea8e58762c8437c7236f03b03a9`。下载后校验 218 个文件，再送回 amd64 断网环境解包，13/13 组、83 项断言通过。单独的 Worker 实测读到了运行同一壳的子进程并验证终止回收；WebCrypto 对 `abc` 的 SHA-256 与独立实现相同。无 Python、无编译器的 Ubuntu 24.04 也从这份归档通过 C ABI 得到 `42`、`ruyi40`。
- 这里的“干净”指私有代码从固定提交重建；仍使用事先配置的 Firefox 159 对象和已校验的上游图形依赖。R355 是独立 tar 包；当前 R356 wheel 封装这套原生文件，历史 R354 保留用于回退。真实 Necko/NSS/QUIC、ARM64 产品和全量 Windows 行为对齐各自单验。

**历史回退版本（R354）：旧私有 Linux amd64 wheel 已在干净 venv 安装并实跑。** [wheel 验收](../../artifacts/receipts/ruyijs-linux-amd64-wheel-r354/validation.json) · [安装态运行检查](../../artifacts/receipts/ruyijs-linux-amd64-wheel-r354/runtime-gates.json) · [安装与复建说明](../../submodules/ruyijs/docs/linux-amd64-wheel.md)。

- 文件：`ruyijs-0.2.2+inner.20261101191032-py3-none-linux_x86_64.whl`，29,378,755 字节；SHA-256 `9135568cd48ec931d094853763e37ae576e581e3c5f4fb1c810fc9f12ee575db`。本地交付目录 `deliverables/linux-ruyijs-wheel-r354/`。原生壳、C 客户端及 18 个库的内容与 R353 完全相同；三次 `pip wheel` 输出同一散列。
- 安装后无需源码目录、`RUYIJS_SHELL` 或 `LD_LIBRARY_PATH`。在 Ubuntu 24.04/glibc 2.39、CPython 3.12.3、UID 1000、断网环境，零参数 `Context()` 使用包内 `dist/js` 返回 `42`。13/13 组、95 项断言通过；再次普通 `pip install` 后卸载，虚拟环境包清单恢复原样。包内非 glibc 依赖通过 `ldd -r`；从只读安装目录单独挂载到原生基础镜像的 C 客户端两次取得 `42`、`ruyi40`。
- 范围：这是私有 `linux_x86_64` 离线 wheel，未上传公共索引，不作 manylinux 声明。R354 之上另有 R355 私有源码干净重建的归档，未替换该 wheel；真实网络辅助进程及 ARM64 产品仍需独立验收。

**R353 原生基线：私有 Linux amd64 离线运行时已严格链接、打包、解压并实跑。** [交付回执](../../artifacts/receipts/ruyijs-linux-amd64-r353/validation.json) · [运行检查](../../artifacts/receipts/ruyijs-linux-amd64-r353/runtime-gates.json) · [链接回执](../../artifacts/receipts/ruyijs-linux-amd64-r353/link-report.json) · [使用说明](../../submodules/ruyijs/docs/linux-amd64-candidate.md)。

- **产品而非 donor：** 1,268 个 Linux 私有翻译单元逐一定位；31 组同源缓存由源文件身份消歧。严格链接保留重复定义与未解析库的报错，退出 0，未定义符号及警告均为 0。图形使用同一固定 Firefox 159 的对象族，Skia 的 76 个成员均先通过旧清单校验，其中 1 个按实际 HarfBuzz 共享库头重编。URLPattern 与 zlib-rs 在同一个 Rust 根归档内；AVIF 的 109 个对象提供真正的 dav1d 解码和缩放。
- **交付件：** 工作区 `deliverables/linux-ruyijs-integration-r353/ruyijs-linux-amd64-r353.tar.gz`，29,488,216 字节，SHA-256 `c3dfd2bed28b6119c7258e09b13ff0f8176393be5475541ed8b9c7b3438c936f`。含 `dist/js`、7 个导出的 C 客户端、18 个版本化运行库、Python 绑定、头文件及校验清单。使用归档内 `README.md` 的 `PYTHONPATH` 和 `RUYIJS_SHELL` 示例即可执行本地页面。
- **执行门槛：** 包从零解压到带空格的新路径，UID 1000、断网、无 `LD_LIBRARY_PATH`。Python 和真实 C 客户端 13/13 组、83 项断言通过；另用无构建工具的 Ubuntu 24.04 基础镜像复跑 CLI 和 C 接口，分别读回 `42` 和持久上下文中的 `ruyi40`。初次实跑揭示的 WebP 间接依赖及 debug 模式查询日志缺项已经修复，初始失败回执保留。
- **R353 当时的边界：** tar 包本身未证明 wheel 安装；该项随后由 R354 单独验收。全树干净重建、真实 Necko 网络联验、Linux ARM64 产品及全量 Windows 行为对齐仍需单列。

**历史基线（R352）：私有壳链接退出 1。** [验收回执](../../artifacts/receipts/ruyijs-linux-amd64-r352/validation.json)与[完整符号清单](../../artifacts/receipts/ruyijs-linux-amd64-r352/link-report.json)已随仓入库。

- **纠正计数。** R351 达到 LLD 的 20 条报错上限。保持同一批对象和库，仅改变输出路径并启用 `--error-limit=0`，得到 347 个不同的未定义符号（68 个 hidden）。修复后的整链为 **129 个**：104 个普通引用，25 个 hidden。早期截断日志里某个名字消失，并非已解决的证据。早期“额外 include 根使样式对象为空”的断言也应撤回：两次 `nm` 在新容器读取前一容器的 `/tmp`，没有检验到同一个文件。
- **图形与字体实跑。** Firefox 159 的 amd64 Pixman 0.46.4 清单是 34 个单元，排除其他架构的加速实现，同时保留运行时分派。4 线程分别在默认分派与禁用 MMX/SSE2/SSSE3 的条件下各比对 4,096 次像素；两次均通过。重编后的几何对象共 33 个 HarfBuzz 导入均为 `DEFAULT UND`，子集适配器返回的空集与实际共享库的单例同址，引用和销毁也经实跑。
- **压缩与 Rust。** 原来的二层归档被 LLD 跳过；展开为 ELF 对象后，又实证未修改的 `libjsrust.a` 把分配器等符号内联／局部化，单加扁平库仍会失败。按 donor 记录的 Rust 根编译命令将 zlib-rs 在 LTO 前纳入同一归档，以它**替换**原归档。检查的 331 个原有外部非修饰函数名全部保留。私有 C++ 适配器的 zlib、raw deflate、gzip 和 Brotli 各完成 65,537 字节的逐字节往返；使用相同归档的原版 C++ shell 报 `JavaScript-C159.0`，求值、Promise 和 WebAssembly 分别返回 `42`、`[7]`、`35`。这是 donor 对照执行，不是私有 `Context.eval`。
- **下一步。** 按 Firefox 的 Linux 配置和对象身份核对 Skia、字体胶合层和 Cairo 合成器；将 URLPattern 的 13 个入口接入同一个 Rust 归档，核对 8 个 AVIF 入口。保留每次链接的真实退出码、完整 argv 和按完整函数签名去重的诊断。私有 shell、真实 C ABI 和 wheel 须分别验收。

以下为各阶段的历史记录。

2026-11-22 在 `host185` 通过 Trace 让行和资源检查后，以 0.5 CPU、2 GiB 内存运行单独的离线快照。借用的 Firefox Git 对象库是 partial clone，实际 `checkout` 因缺少 blob 返回失败；其私有目录和日志保留，未启动 standalone 编译，容器 `OOMKilled=false`。

主机已从 Mozilla 官方仓库核对 `FIREFOX_159_0_RELEASE` 对应 `9a2dc53c369c7ae5172018b35988e1d2ffeff402`。同额度的独立源码容器在 `/home/ruyijs-donor-isolated-moz159/firefox` 浅取该 tag，没有 Trace 挂载，实际 `official_source_ready 0`。联网仅用于取官方源码。证据位于工作区 `deliverables/linux-ruyijs-donor-r66/source-stage.json`。

同机原生 amd64 断网预检以只读方式挂官方源码，Clang 21、`JS_STANDALONE=1`、`JS_SHARED_LIBRARY=1`、x86_64 目标和 247 个生成后端文件均确认。首次仅头文件步骤误从子目录调用，保留 `headers 2`；`959de74` 改用顶层两个确切目标，生成 `js-config.h` 与 `js-confdefs.h` 后 `configured_only 0`。配置及头文件复验均无 OOM，证据 `deliverables/linux-ruyijs-donor-r67/native-configure.json`。新增 2 项配置回归与 21 项隔离回归通过；仍无 `dist/bin/js` 或私有产品 `Context.eval` 结果。

`fb4d68f` 加入 cgroup v1 单作业看门狗：从实际在用内存中扣除有界的非活跃文件缓存，工作量连续三次达到 3,750,000,000 字节即停止本次进程组；每 30 秒保留数值。主机 `/home/ruyijs-donor-isolated-moz159/full-r68` 使用配置的独立副本，在原生 amd64 容器内以只读源码、无网络、2 CPU／4 GiB（无额外 swap）启动 `make -j1`。06:37 +08:00 已生成 JIT 构建输入，OOM 为零；原预检保持原样。两项看门狗回归通过。阶段性证据 `deliverables/linux-ruyijs-donor-r68/native-build-start.json`。候选只有链接后通过 ELF／对象清单、版本和本地 JavaScript／Promise 才算源 donor 通过，且与私有产品行为验收分开。

随后同一任务生成中间 `libjsrust.a`（65,114,854 字节），继续编译 `js/src/builtin/Unified_cpp_js_src_builtin4.o`，阶段性实证为 `deliverables/linux-ruyijs-donor-r68/native-cxx-stage.json`。

07:15 +08:00 已确认 `standalone_donor_verified 0`：候选链接的原生 x86_64 `dist/bin/js` 为 288,896,464 字节，SHA-256 `edd591e42f99ed3436e6f8112b2939a0a74b458fa09de261cc45214733bead80`，28 个 shell 对象齐备，实际 `--version` 为 `JavaScript-C159.0`，断网执行的求值与 Promise 回执 `{eval:42,promise:[7]}`。内存看门狗采样工作量峰值 2,795,630,592 字节、未触发停止，Docker `OOMKilled=false`，原预检副本仍未链接。回执 `deliverables/linux-ruyijs-donor-r68/standalone-verified.json`。这是原版 Mozilla donor，和私有版验收分开。

07:30 +08:00，`23409f7` 在独立断网容器按真实构建记录重放原始链接，只改变输出路径。28 个原对象和三个静态库通过只读挂载；产物和原版 `dist/bin/js` **逐字节一致**（同为 288,896,464 字节、SHA-256 `edd591e42f99ed3436e6f8112b2939a0a74b458fa09de261cc45214733bead80`），重链 ELF 也实跑得到 `JavaScript-C159.0` 和 `{eval:42,promise:[7]}`。重复或变更链接命令会失败，两项新增回归通过。证据 `deliverables/linux-ruyijs-donor-r72/exact-relink.json`。该回执仅用于未修改对象的链接对照。

随后 `12e33c7` 以已提交的私有生成器及头文件，从真实 Mozilla donor 生成私有 `js.cpp`、统一单元与 codec 头。100 项原始编译参数经摘要固定，只更改输出、依赖文件和输入的路径并新增私有 include。断网原生编译生成 x86_64 ET_REL `shell0.o`：6,958,728 字节，SHA-256 `82f7bb61f0a9509e56e3e09c67a5fc6a21d13546f16e96e0c2968dd1a308e2a8`；检查到 `Arguments::Prepare`、`Run`、`RunWorker` 与两类异常处理的五个待链接钩子。原 donor 对象摘要不变，容器退出 0、未 OOM，继续保留在独立目录 `/home/ruyijs-donor-isolated-moz159/private-shell0-r73`。见 `deliverables/linux-ruyijs-private-shell0-r73/compile-evidence.json`。该轮只生成待链接对象。

`94436d5` 核对、提交 POSIX 参数分支，实际 C++ 回归覆盖 UTF-8 路径和原始 argv 字节、二进制读取、`{pid}` 展开与显式路径优先。`host185` 从同一真实 donor 的编译配置断网编译 `arguments`、`exception_capture`、`runtime`、`worker_mode` 四个私有单元，再用 `ld.lld -r` 与上一轮 `shell0.o` 合并。回执 `native_hooks_verified 0`，含 **五个原始钩子定义**，对应引用均闭合；合并后的 x86_64 ET_REL 是 8,237,552 字节，SHA-256 `dda86055255d47912212dd17af9c14e9c8e611f228e3b6ba01533e82d60ed965`。没有 OOM；仍有 **229 条其他私有未解析符号**。列表及四个原始对象摘要在 `deliverables/linux-ruyijs-native-hooks-r74/hook-link-evidence.json`。`Context.eval` 仍待实际运行。

`deae44b` 复验并纳入 POSIX `Pipe` 实现，本机 AF_UNIX 试验通过同步／异步、16 MiB 帧、背压与关闭清理。再在 `host185` 用已有只读 donor 和私有输入编译 17 个实际单元，生成 11,250,344 字节的 x86_64 ET_REL（SHA-256 `951edd890376963f5987dbe961441a91602eb3d650d1816f5a4a38a3255c4345`）。按 ELF 原始符号身份而不是相似名称，上一轮 229 条私有引用消除 30 条（包含 `Pipe::ConnectAsync`），新增 68 条，**当前 267 条**。容器退出 0 且无 OOM，前版对象摘要不变。实证在 `deliverables/linux-ruyijs-native-batch-r75/symbol-delta.json`。符号继续闭合，尚无私有可执行文件。

`bca6c12` 在同一原生 x86_64 donor 旁使用 `scheduling-v1` 分批编译整个执行调度域。49 个已提交单元逐一通过，6 个模型单元启用异常处理；部分链接所得 x86_64 ET_REL 为 19,266,376 字节，SHA-256 `71e106976ac290d6c6d643e538dd46182d443f0939d11852bccd2714f7811edf`。上一轮 267 条引用解决 20 条（均属于调度域），新增 7 条，剩 254 条，其中 `execution_scheduling` 引用为 **0**。前版对象摘要保持原样；容器退出 0、无 OOM。实证 `deliverables/linux-ruyijs-native-sched-r76/scheduling-symbol-delta.json`；仅为部分链接，调度的产品运行验收与完整 `Context.eval` 仍待实跑。

`c7e6eaa` 使用已提交的环境配置生成 `firefox_environment_profile.h`，然后原生断网编译全部 64 个 `browser_environment` 单元（3 个模型单元沿用异常策略）。新 x86_64 ET_REL 为 44,501,600 字节，SHA-256 `26591bd914028753f73dfc481a7e7d26112c49f1d9cfe5084cbcca729a71d572`；上一轮 254 条引用消除 26 条，新增 14 条，剩 242 条，其中 `browser_environment` 引用为 **0**。前版对象、配置来源和生成头均复核摘要一致，容器退出 0、无 OOM。宿主 locale 等平台语义仍需产品实跑；此处仅验收链接。证据 `deliverables/linux-ruyijs-native-env-r77/environment-symbol-delta.json`。

`ce0247e` 将交互和消息域放入同一原生批次，按域保存对象，避免不同目录内的 `realm.cpp` 等同名文件碰撞。主机启动器先核对同架构只读 donor、配置提交、容器隔离和资源上限，实际编译逐一运行，并保留新旧符号身份。

`host185` 已实跑 `native_interaction_verified 0`：82 个交互单元和 5 个消息单元全部编译通过，新 ET_REL 60,678,392 字节、SHA-256 `e2430213b921e9df8ab2bb83f89bb996460e76631df57f7a72f611cf15634c15`。交互 15 条和消息 10 条上一轮引用全部闭合，新增 2 条其他引用，未解析总数 **242 → 219**。容器退出 0、无 OOM，前一批摘要不变。本机 5 项批次与隔离回归通过；回执 `deliverables/linux-ruyijs-native-interact-r78/interaction-symbol-delta.json`。该部分链接没有运行交互或消息功能，完整私有版仍待构建和运行验收。

`e477bf3` 将 Linux Necko helper 移植落入私有源码：使用 POSIX 进程、描述符和原有小端帧，保留旧 Windows 路径。原生 aarch64 本机通过实际回环 HTTP，150,000 字节二进制 POST 完整回返，计时字段、帧内错误后的 session 复用、子进程关闭／回收也通过。对端是 `http.client` 试件；非浏览器 Necko/NSS、非真实 QUIC 握手。x86_64 原生 7 个受限编译单元的部分链接另得 SHA-256 `feb197e098fda4d17449d4bb8712846ec18c47c2c775721fb4aea7bd67901b70`，消除 `AsyncHttp::Wait` 与 `PrewarmNeckoSessions` 两条旧引用，新增 9 条，**219 → 226**；前一批摘要不变、无 OOM。回执 `deliverables/linux-ruyijs-native-carrier-r79/carrier-symbol-delta.json`。其余 AsyncHttp／Abort／资源域实现仍需继续编译和实跑。

`aa029f7` 启动单作业 `resource-network-v1`，包含 177 个已提交资源单元中剩余的 168 个（排除两个 Windows 专用和上批七个），17 个模型文件保持异常策略。`host185` 在 09:25 +08:00 的实际样本为 **80/168** 个已成功编译，断网、2 CPU／4 GiB，未发生 OOM，尚未完成部分链接。证据 `deliverables/linux-ruyijs-native-net-r80/compile-sample.json`；该样本只是阶段性进度。

资源网络随后 `native_resource_network_verified 0`：168/168 单元成功，ET_REL 109,858,816 字节、SHA-256 `ca4f1e6ff50e950d902db1fb146c54d35a5b1e62c67872d26bd30d9d0752e378`；消除 39 条旧引用、引入 10 条新引用，**226 → 197**，`resource_network` 归零。证据在 `deliverables/linux-ruyijs-native-net-r80/resource-symbol-delta.json`。没有 OOM，真实 Necko/NSS 与 QUIC 行为仍未验收。

`72b50b9` 的 Linux Worker POSIX 进程适配通过本机协议试件，真实测试覆盖 dedicated/shared/service 子进程、关闭继承描述符、提前退出、最后一帧及进程组清理；并未执行 JS Worker realm。另以该对象接入原生 x86_64 20 单元 `workers-v1`：`native_workers_verified 0`，消除全部 12 条 Worker 引用且未新增私有未解析引用，**197 → 185**。产物仍是 ET_REL（114,077,432 字节），前一批对象摘要不变，无 OOM。证据 `deliverables/linux-ruyijs-native-workers-r81/worker-symbol-delta.json`。私有可执行文件和 `Context.eval` 仍待实际验收。

`76a6ea3` 启动完整 `document-v1`：248 个已提交文档单元，60 个模型文件沿用异常策略，使用固定 Mozilla Sanitizer 源和事件表生成头文件。本机 AArch64 的 C++ 数据检查通过，固定表为 121 个默认元素、58 个默认属性、147 个事件属性；`script`、`onclick` 排除在默认允许表，`onclick` 位于移除表。记录 `deliverables/linux-ruyijs-native-doc-r82/sanitizer-data-check.json`，仅覆盖生成表，无页面 Sanitizer 准入结论。

09:55 +08:00，`native-doc-r82` 断网单作业已编译 38 个单元，`document_metadata.cpp` 因 Windows-only `localtime_s` 失败，OOM 为零，批次仍使用原提交继续。`bbca26b` 保留 Windows 接口并用 POSIX `localtime_r`，本机实跑校验固定日期、闰日及跨午夜时区，格式保持 `MM/DD/YYYY HH:MM:SS`。旧日志保留。早期采样 `deliverables/linux-ruyijs-native-doc-r82/compile-sample.json`。

首批终态 `native_batch 1`：247 个成功、仅 `document_metadata` 失败、未发生 OOM，保留实际部分对象与终态回执 `deliverables/linux-ruyijs-native-doc-r82/original-terminal.json`。`a9f237f` 逐项比较新旧整个私有源树，只准两个日期文件变动；核对 247 个旧对象与其依赖记录、Sanitizer 输入及旧聚合摘要后，仅重编 `document_metadata.cpp` 并重新部分链接。`native_document_repair_verified 0` 产物 202,261,184 字节，SHA-256 `efd8bb5bf88f4cf6b39cdc29b016c1ebe04395ad91abc5d9e9cbaca67cf86925`；相对 Worker 基线消除 10 条旧引用、新增 15 条，总数 **185 → 190**，`document_model` 引用为 0。无 OOM，首批旧对象保持原样。证据 `deliverables/linux-ruyijs-native-docfix-r83/document-repair-symbol-delta.json`。这里只验收文档域 ET_REL；产品链接、完整页面行为和 `Context.eval` 尚待实跑。

`72d124d` 为对象 URL 的 UUID 保留 Windows BCrypt 路径，Linux 使用内核 `getrandom`，并保留原有前缀及版本／变体位。本机 AArch64 C++ helper 真运行通过；`host185` 的 3.10 内核及此次断网容器也实际返回了随机字节（未输出内容）。该小型测试未运行对象 URL 的完整 JS 创建或撤销语义。

原生 `web-platform-v1`（53 个 Web 平台单元＋共用 `WebKit`）终态 `native_batch 1`，51/54 编译成功，无 OOM。Brotli 和 zlib 单元缺本次归档遗漏的**已跟踪 vendor 头**；URLPattern 正则单元是手写 SpiderMonkey 前置声明与 GCC hidden pragma 下的公开可见性不一致。部分 ET_REL 实测消除 30 条旧引用、引入 10 条、**190 → 170**，`WebKit` 的 15 条旧引用全部闭合，但 Web 平台仍有 9 条引用。回执 `deliverables/linux-ruyijs-native-webplat-r84/partial-web-platform.json` 保留原始编译错误。`1208a11` 改用 donor 的 `js/TypeDecls.h`；后续须带上固定 Brotli/zlib 头、重编三个失败单元及此头的旧依赖者，再确认完整批次。没有私有可执行文件或对象 URL 产品行为结论。

`a1a98c2` 按真实依赖清单选出三个失败单元及依赖改动头的 `url_pattern.cpp`，核对剩余 50 个旧对象。带上 8 个固定 vendor 头后，第一轮复验的 Brotli 已通过，zlib 曝出旧断言 `112 == 88`；`d058a5e` 保留 Windows x64 `uLong=4/z_stream=88`，新增 Linux LP64 `8/112` 校验，原私有 zlib-rs 符号前缀保持原样。原生 AArch64 的实际适配器编译及头布局测试通过，未链接 Rust runtime。

最终 `native_web_platform_repair_verified 0`：4 个重编单元与 50 个已核对复用对象重新部分链接，54/54 无错误，ET_REL 213,252,296 字节、SHA-256 `5d74f088a91a904b759492bf1a1b189dcc8a67bc3ab4e65a1db0a8fbdfc8e707`。相对修复前文档基线消除 30 条、引入 1 条，**190 → 161**，`web_platform` 归零；无 OOM，首次失败和旧聚合对象保持原样。回执 `deliverables/linux-ruyijs-native-webabi-r85/web-repair-symbol-delta.json`。此处未运行压缩、URLPattern 或私有 `Context.eval`。

`d57a927` 在断网原生 x86_64 容器实际构建并链接私有 codec：181 个固定文件按摘要检查，沿用 donor Rust 1.100.0，核对六个 `RUYIJS_CS_Z_*` 导出，并编译 35 个 Brotli C 单元。真实 C++ 适配器以小块往返 65,537 字节二进制数据，zlib／raw deflate／gzip／Brotli 压缩长度分别为 2,985／2,979／2,997／1,871，解压逐字节一致，`native_codecs_verified 0`、无 OOM。证据 `deliverables/linux-ruyijs-native-codecs-r86/native-roundtrip.json`。独立探针的 Rust staticlib 包含 std，不能混进最终 SpiderMonkey；产品的 JS CompressionStream、URLPattern 和 `Context.eval` 仍待运行验收。

`35e8197` 为私有主程序配置 `runtime-rest-v1`：90 个已提交 runtime 单元中，精确排除前序已链接的实现和 Windows 专用管道，保留其余 63 个。断网编译使用已提交的 Firefox 绑定顺序头及前序 donor 配置；该批次检查链接依赖，不运行页面导航或消息行为。

`native-runtime-r87` 终态 `native_batch 1`，实际编译 62/63 个单元、无 OOM。唯一错误是 `worker_nested.cpp` 首先引入手写 `JSContext` 声明，与 donor API 的可见性冲突。`8cbeac3` 在该单元最前引入规范 `js/TypeDecls.h`，保留共享头，避免改变已经编译的依赖者；原生重编仍待完成。实际 62 单元部分 ET_REL（SHA-256 `e3a40ea6bdbaab90fd02f62663440cd732f612d9d9f711bf4aab7690e9c2f9d9`）消除 68 条旧引用，暴露 139 条新依赖，剩 232 条。回执 `deliverables/linux-ruyijs-native-runtime-r87/runtime-partial.json`。失败日志和前序对象保留；尚无私有可执行文件。

`f7bb5f8` 复验已 `native_runtime_repair_verified 0`：核对完整私有源树、绑定表、62 个复用对象和依赖记录，只重编修正后的 `worker_nested.cpp` 再部分链接。相对前序基线消除 70 条，暴露 139 条，**余 230 条**；实证是原生 x86_64 ET_REL，SHA-256 `582aed88bedafcb67717252b4971cb4b715f6c39c8e2367f855fcfe94cbab112`。无 OOM，旧部分对象保持原样。证据 `deliverables/linux-ruyijs-native-runtimefix-r88/runtime-repair-symbol-delta.json`。私有可执行文件与真实 JS 行为仍待验收。

样式域首批同时独立编译桥接和 CSS 实现，真实 native `ld.lld` 拦截重复定义；六个展开单元另报告 no-exceptions 失败。原日志独立保留在 `deliverables/linux-ruyijs-native-styling-r91/original-failure.json`。源清单复核发现 52 个 CSS 实现已由三个桥接单元唯一包含，独立编译仅需 `css_color_space.cpp` 加 55 个桥接单元。`b4040ec` 将所有权纳入校验，并以原生 AArch64 最新源码实跑纯 C++ 逻辑：CSS 声明重要性覆盖、margin 简写及选择器优先级通过；这不是 SpiderMonkey 页面行为验收。

修正后的 `native-stylefix-r91` 在同一只读前序 native x86_64 ET_REL 上编译 56 个唯一拥有者，`native_styling_verified 0`、无 OOM。ET_REL SHA-256 `368563a2ccfa06073820a4220a25093512e0d3eef91be27c323456f3484e138f`。消除 26 条桥接和 15 条 CSS 实现引用，未引入私有未解析引用，**230 → 189**。前序摘要不变。回执 `deliverables/linux-ruyijs-native-styling-r91/styling-symbol-delta.json`；全部 10 项批次回归通过，完整产品与页面样式运行仍待验证。

`057ce17` 将 59 个几何单元分成 41 个可移植单元与 18 个字体／字形／SVG 原生后端单元，后者保留待移植，不以空实现填充。原生 AArch64 的独立 C++ 试验通过矩阵平移与二维判定、SVG 相对控制点和无效输入检查；无浏览器 DOM 或原生描边验收。11 项批次回归通过。

`native-geometry-r92` 原生 x86_64 断网单作业 `native_geometry_portable_verified 0`：41 个单元编译与部分链接均通过，消除 20 条旧引用并新增 8 条，总数 **189 → 177**。目前仍有 12 条几何后端引用（主要是字体配置、度量和 SVG 描边），待使用合适的原生 Linux 后端，不代表完整几何域通过。ET_REL SHA-256 `a884d0cd88125485af75062a1b7ea0653d647eb387c2630672da7e56274e7ff7`，前序对象摘要不变、无 OOM。回执 `deliverables/linux-ruyijs-native-geometry-r92/geometry-symbol-delta.json`，产品可执行文件与 `Context.eval` 仍待验。

`f0cf666` 将 `font_config` 与 `font_preferences` 的可移植逻辑从 DirectWrite 后端分开，Linux 共享严格 Unicode 标量转换。本机原生 C++ 验证非 BMP、错误／截断／过长序列原子拒绝。原生 x86_64 使用固定 HarfBuzz 头和已提交字体表，2 个单元 `native_font_profile_verified 0`，消除 6 条、不新增私有引用，**177 → 171**，剩 6 条几何符号主要是 `SystemFonts` 和 `SvgPathBounds`。新 ET_REL SHA-256 `c4b324cbbf9ae034d06bfcdc725c0d880e405001a746c20e126ab371b78240f9`、前序对象不变、无 OOM。

`a915eef` 的独立运行探针直接用这两个真实对象，链接同一 donor 中实际提供 `moz_xmalloc` 与 `gMozCrashReason` 的对象（之前两次失败保留）。断网实跑 `en-US → serif`，`ja-JP`／`zh-CN → sans-serif`，DPR=1／2 的自动文本优化阈值 20／10。这只验证配置与决策，不选择已安装字体、不进行度量或绘制。见 `deliverables/linux-ruyijs-native-fontprofile-r93/font-profile-validation.json`。

`69946ae` 为 Linux `SvgPathBounds` 接入 Cairo，Windows 保留 Direct2D。实现覆盖直线、二次／三次曲线、旋转 SVG 椭圆弧及平头斜接描边，并限制 Cairo 固定点坐标范围；越界返回失败且保留原输出。使用 Ubuntu `libcairo2-dev` 头、实际 AArch64 Cairo 1.16.0 库原生链接并运行 17 个用例，UBSan 检查与矩阵／SVG 解析回归通过。Linux 最终链接需要 Cairo 开发头及 `-lcairo`；这一阶段只实跑独立后端。回执 `deliverables/linux-ruyijs-svg-path-r94/svg-native-validation.json`。

随后 `c95d91b` 在 x86_64 donor 配方下解决两层实际失败：Firefox 自带头要求生成的 `cairo-platform.h`，改用签名 Ubuntu Noble 索引核对的公开开发头；donor 默认隐藏符号会阻止链接真实 Cairo 动态库，故只把这些 C 声明恢复为默认可见。`native_svg_path_relocation_verified 0` 闭合 `SvgPathBounds`，私有引用 **171 → 170**（余 5 条几何引用均在 `SystemFonts`），前序 ET_REL 不变。精确复用该批次的 `svg_path.o`，单独链接并以 UID 1000 断网实跑 Ubuntu 24.04 Cairo 1.18.0 的全部 17 项用例，实查 17 个 Cairo 导入可见性和加载，未发生 OOM。回执 `deliverables/linux-ruyijs-svg-abi-r95/svg-abi-validation.json`。其余私有产品的完整链接和页面 `getBBox()` 仍待验收。

`c500b3c` 给 Linux `SystemFonts` 接入 Fontconfig 选字与 FreeType 行高、SVG `ex/ch/ic/cap` 度量；Windows 继续使用原 DirectWrite 实现。Linux 使用系统配置排序，在打开字体前调用字体配置过滤器，按 CSS app unit 舍入；此批仅处理可缩放字体。原生 AArch64 在仅有 DejaVu Sans/Serif 的隔离字体目录实跑，验证 16px 行高 18.633333、`ex=8.75`、`ch=10.183333`、`ic=16`、`cap=11.666667`，覆盖尺寸缩放、候选过滤、无可选字体和无效输入。用系统真实 Fontconfig 2.13.1、FreeType 2.11.1 通过 UBSan；生产适配层通过独立编译检查。最终 Linux 链接需 Fontconfig/FreeType 的开发头与动态库。这份 ARM64 回执未改变 x86_64 聚合符号计数。回执 `deliverables/linux-ruyijs-font-metrics-r96/font-metrics-validation.json`。

`1ae925d` 用签名 Ubuntu Noble 开发包固定的 58 个头编译 `system_font` 与 `font_metrics_linux`，`native_font_metrics_relocation_verified 0` 闭合 4 条私有引用（构造、析构、行高、SVG 字体单位），**170 → 166**，未引入新的私有引用；实查 23 个默认可见的外部 Fontconfig/FreeType 导入。用这两个真实对象与已有 CSS、字体配置和 donor 分配器对象链接独立探针，原二进制 6,623,096 字节，首次仅超过输出回收上限，核对摘要后直接重放同一 ELF。UID 1000、断网、两种 DejaVu 独立字体；直接调用 `SystemFonts` 验证 16px 与 32px 度量、非法或零尺寸、默认字体路径，未发生 OOM。回执 `deliverables/linux-ruyijs-native-fontmetrics-r97/font-metrics-abi-validation.json`。该 x86_64 聚合对象的几何域只剩 `SystemFonts::Measure`。

`9a8ae1f` 实现 Linux `SystemFonts::Measure` 的水平 SVG 文本后端：沿用 Fontconfig 候选与字体可见性过滤，用 FreeType 打开可缩放 SFNT 字型，HarfBuzz 塑形、FriBidi 计算双向嵌入等级，按逻辑 UTF-16 索引回填字簇，并投影仿射边界。原生 AArch64 用隔离 DejaVu 字体和真实库通过 `ffi`、组合符、代理对、希伯来文混排、阿拉伯文 lam-alif、回退、输入校验及 UBSan，实测 16px `ffi=15.4667px`、阿拉伯样例 `32.8500px`。Fontconfig/FreeType 行高回归及 11 项批次回归通过，生产适配层通过编译检查。回执 `deliverables/linux-ruyijs-svg-text-r98/svg-text-validation.json`。这份 ARM64 回执未改变 x86_64 聚合符号计数。

`13954bf` 的独立 x86_64 重建从前字体阶段基线（177 条）重编六单元，闭合几何域全部 12 条，余 165 条私有引用；相对已公示的行高批次 **166 → 165**，唯一差异是 `SystemFonts::Measure`。第一版保留的实际 ET_REL 仍含两个 `HIDDEN` 的旧 HarfBuzz 导入；修复后全聚合中 69 个系统几何导入均为 `DEFAULT`，已验 `SvgPathBounds` 对象仍逐字节相同。用同一批次对象运行 137,440 字节独立探针，断网 UID 1000，真实 HarfBuzz 8.3.0／FriBidi 1.0.13：行高和 SVG 单位回归通过；`ffi=15.4667px`、阿拉伯样例 `32.8500px`、希伯来与拉丁混排 `75.6167px`，UTF-16 字簇和仿射变换通过。无 OOM，12 项批次回归通过。回执 `deliverables/linux-ruyijs-geometry-abi-r99/geometry-abi-validation.json`。Canvas 栅格、页面／完整产品和更广的 SVG 文字布局仍待验收。

`a74bd1e` 将 18 个 Web API 域的 116 个翻译单元接到已经核验的几何基线；按域区分同名对象，异常开启仅限两个 IndexedDB 模型单元。原生 x86_64 `native_web_services_verified 0`，116 个均通过编译及 ET_REL，消除 102 条原引用、新增 2 条，**165 → 65**，新依赖为 `web_crypto::ComputeDigest` 与 `web_geometry::LocalFontFamilyInstalled`；其余未闭合来自 Audio、Canvas、Crypto、GPU、Graphics、Media 和 RTC。回执 `deliverables/linux-ruyijs-webservices-r100/web-services-validation.json`。编译与部分链接暂无完整 Web API 或页面验收结论。

真实 IndexedDB 模型复现了 `2^53+1` 被舍入的旧错误；修复后最后可用的自动键 `2^53` 仅生成一次，耗尽标记随写事务提交，回滚恢复生成器。原生 AArch64 UBSan 测试与 x86_64 同批精确对象的独立探针均验证提交、回滚、唯一索引、源隔离、版本升级回滚与生成器耗尽。ARM64 原始失败保留在 `deliverables/linux-ruyijs-indexeddb-r100/`；13 项批次回归通过、无远端 OOM。该模型运行不等同于 JS IndexedDB 页面或持久化验收。

`f138943` 给 Linux `local()` 接入真实 Fontconfig 全名／PostScript 名查找：精确匹配忽略大小写，查询不走替代字体，按字体 profile 过滤，拒绝 NUL 和无效宽字符；Windows 路径保持原样。验证闭合该字体查询，以及 30 个 WebAudio、23 个 WebRTC 单元；54 个全部原生编译及部分链接，**65 → 46**，消除 19 条旧引用、零新增，余 Canvas 13、Crypto 6、GPU 4、Graphics 6、Media 17。71 个系统几何导入保持默认可见，未发生 OOM。

ARM64 UBSan 与同对象 x86_64 探针实际通过 Fontconfig 两字体的全名／PostScript、隐藏和替代名过滤，也实跑 48kHz 的 1kHz PCM，两个 128 帧量子与 256 帧连续运行逐样本一致，另过方波和参数限幅／实例隔离。x86_64 断网 UID 1000，使用真实 profile 对象。14 项批次回归通过。证据 `deliverables/linux-ruyijs-audiortc-r101/audio-rtc-font-validation.json` 与 `deliverables/linux-ruyijs-audio-font-r101/audio-font-validation.json`；WebRTC 当前只验证部分链接，JS 页面、音频设备、RTC 媒体传输及完整私有程序仍待验收。

在完全干净的 Git 源快照中，WebGPU 模型的旧实现允许负限制值。`75cf2bc` 修复非有限及负限制值，初始化改用 RAII，功能集直接使用底层聚合状态而不维护副本。ARM64 原生 UBSan 实际运行软件 GLSL 与 MSAA、能力子集回滚和 64 位限制值；实得 RGBA `[255,127,0,255]`、抽样覆盖 `[4,2,0]`。原始失败与修复验证位于 `deliverables/linux-ruyijs-graphics-r102/graphics-software-validation.json`。两处既有本地 WebGL 修改未纳入快照；此回执不覆盖页面、驱动或硬件 GPU。

原生 x86_64 `native_graphics_gpu_verified 0`：33 个 Web Graphics 和 17 个 WebGPU 单元全部通过 ET_REL，消除 10 条旧引用、未引入新私有引用，**46 → 36**，余 Canvas 13、Crypto 6、Media 17。用同批五个精确对象与 donor 分配器构建断网探针，顶点 `[0.5,-1,0,1]`、颜色 `[255,127,0,255]`、MSAA 覆盖 `[4,2,0]` 与 ARM64 结果一致，4 GiB 数值、非法限制拒绝和能力回滚均通过。无 OOM，15 项批次回归通过。见 `deliverables/linux-ruyijs-graphicsgpu-r102/graphics-gpu-abi-validation.json`；仍无真实网页、GPU 设备或完整私有程序验收。

`99796e9` 将 Media 的 APNG／WebP 动画接口与 WIC 解耦，Linux 静态和帧补丁分别以 libpng／libwebp 真实解码，再做预乘 BGRA 合成和缩放。Windows 继续走 WIC。Linux 校验源、目标及累计帧像素预算，动画重建还检查累计编码字节；无效整图解码保留原结果。AArch64 独立 C++ 探针在仅 lo 的命名空间用系统 libpng 1.6.37／libwebp 1.2.2 通过 UBSan、静态图像、两帧 APNG／WebP、缩放像素、流中前缀和截断 EOF 区分。支持查询仅报 PNG／WebP；JPEG、GIF、AVIF、BMP、ICO、ICC 色彩转换、x86_64 私有聚合和浏览器 ImageDecoder 待验。这份 ARM64 记录未重测当时的 x86_64 私有余量。运行记录 `deliverables/linux-ruyijs-imagecodec-r103/image-codec-validation.json`。

`b00a758` 从已核验 Graphics/GPU 基线构建 65 个 Media 单元，排除未移植的 `image_avif`、`image_color` 和 `image_gif`，并锁定签名 Ubuntu Noble 包的 9 个开发头。原生 x86_64 `native_media_png_webp_verified 0`，**36 → 19**，消除 Media 的全部 17 条旧私有引用，零新增；剩 Canvas 13、Crypto 6。聚合 ELF 实查 32 个 libpng／WebP 导入均为默认可见。使用同批六个精确对象和真实 Noble 动态库，在断网 UID 1000 原生重跑静态 PNG／WebP、两帧 APNG／WebP、预乘 BGRA、缩放、截断 EOF 与损坏输入，均复现 ARM64 结果。无 OOM，16 项批次回归通过。回执 `deliverables/linux-ruyijs-media-r105/media-png-webp-validation.json`。Media 私有符号闭合只覆盖该已编译范围；剩余格式、ICC 和浏览器页面仍待验证。

`6356385` 纳入已审阅的 Linux OpenSSL 字节后端，系统 libcrypto 声明保持默认可见，Windows CNG 单元原样保留。新增固定原版 Windows PE 在 Wine 9 的 29 个合成向量：摘要、HMAC、CBC、GCM；在 21 组 GCM 中兼容原件的 5 组接受和 16 组拒绝。ARM64 UBSan 与 AMD64 同批精确对象实跑均逐项匹配，另验证三条 EC 曲线及失败解密保留调用者输出。原生 x86_64 `native_crypto_openssl_verified 0`：19 个 Crypto 单元（排除两份 Windows 后端），135 个签名 OpenSSL 公共开发头、58 个默认可见导入；闭合全部 6 条旧引用、零新增，**19 → 13**，均为 Canvas。AMD64 断网 UID 1000，libcrypto 3.0.13，未发生 OOM，17 项批次回归通过。[固定 PE 向量](../../submodules/ruyijs/ci/fixtures/openssl-windows-pe-contract.json)；运行回执 `deliverables/linux-ruyijs-crypto-r106/crypto-openssl-abi-validation.json`、`deliverables/linux-ruyijs-crypto-arm64-r106/crypto-openssl-validation.json`。第三方 Linux wheel 继续只作对照；WebCrypto Promise／WebIDL、产品构建接线和完整 `dist/js` 仍待验收。

`b2830b8` 在 Crypto 基线上编译 63 个可移植 Canvas 单元，暂时排除仍依赖平台字形与 Skia 后端的 `skia_target` 与 `skia_subset_stubs`，不以空实现顶替。原生 x86_64 `native_canvas_portable_verified 0`：13 条旧私有引用全部闭合、零新增，余 12 条（`skia_target` 8 条、字体几何 4 条）。同时修复一个真实缺陷：`raster_fill.cpp` 原先在把坐标转成 `int` 之后才检查范围，ARM64 UBSan 在 `-1e+20` 上直接报越界；改为逐点在舍入与转换之前检查有限性与既有 ±8191 边界，正常像素逐字节不变，并把 `EncodePNG`／`Base64`／`PngMetadataHex` 的声明从 SpiderMonkey 头迁到 `png_codec.h`。同批对象在断网环境实跑 8×6 RGBA 栅格与 PNG 回环，独立 CRC、zlib 和 Sub 滤波器反推逐像素核对 48 个像素（28 透明／16 红／4 蓝），94 字节 PNG 摘要固定；ARM64 先复现后修复。无 OOM。回执 `deliverables/linux-ruyijs-canvas-r107/canvas-portable-validation.json`、`deliverables/linux-ruyijs-canvas-raster-r107/raster-bounds-validation.json`、图片 `deliverables/linux-ruyijs-canvas-r107/canvas.png`。这里没有 Skia 目标、字体栅格或浏览器 Canvas。

`804b6ef` 把 Canvas 剩余的 Skia 后端第一次接到固定 Firefox 原点真实的原生 Skia 产物上。先只读审计：要求 Firefox 提交与基线完全一致、`gfx/skia` 工作区无改动，实查 x86_64 objdir 中 **76 个**原生 ET_REL（76,498,176 字节）、`backend.mk` 含 `MOZ_SKIA` 与 `TRIMMED=1`，并要求 `SkSurfaces::WrapPixels` 与 `SkCanvas::drawRect` 是真定义而不只是重定位。第一次链接失败给出确切的第一个阻塞点：`/usr/bin/ld: hidden symbol 'hb_face_destroy' isn't defined`。原因是探针只带 Skia 与 mozalloc／mfbt，没带 Firefox 自己的 HarfBuzz；该 provider 不在 `gfx/harfbuzz` 目录，而是 `gfx/harfbuzz/src` 下的单个统一对象 `Unified_cpp_gfx_harfbuzz_src0.o`（38 MB，定义 28,044 个 `hb_` 符号，链接可见性为 `HIDDEN`）。补上该真实对象后，符号闭合剩余 222 条，其中 176 条由镜像内真实共享库（libc／libm／libstdc++／libgcc_s／libexpat／libz）提供，46 条只被 `--gc-sections` 回收掉的 subsetter 与 typeface 段引用（29 条 FreeType、9 条 Mozilla FreeType 胶水、3 条 `MOZ_Z_`、2 条 `PrintfTarget`）。

这一轮还暴露一个与代码无关的真实运行条件：探针镜像给 `/tmp` 挂的是 `noexec`，所以二进制虽然成功生成（7,010,232 字节）却根本起不来，前两次运行据此写出空结果。第三次显式使用可执行 tmpfs 后，`skia_cpu_probe_draw 0`：4×4 `kBGRA_8888` 预乘 CPU surface，`SkSurfaces::WrapPixels` 后 `drawRect` 落在 (1,1)-(3,3)，得到 4 个不透明红、12 个透明，`bgra.json` 逐像素断言通过。容器为 network none、只读根、1 CPU、2 GiB RAM+swap，`OOMKilled=false`、退出码 0。回执 `deliverables/linux-ruyijs-skia-cpu-r112/skia-cpu-probe-validation.json`。这次通过只说明该 CPU 光栅与绘制路径可用；Canvas 文字字形、度量与掩码、私有 `CanvasSkiaTarget` 集成、`dist/js`、浏览器渲染与 PDF subset API 都还没验收。

`39607d9` 把 Canvas 文字第一次真正接到固定 Firefox 的 Skia 上，结论是**链接通了、绘制没通**，而且失败点被精确定位到 `main` 之前。可复用的技术事实有四条。第一，固定 Skia 产物里**只有** `SkFontHost_cairo.o` 一个从 FT_Face 造 typeface 的入口，`SkFontHost_FreeType_common.o` 一个 `SkTypeface`/`SkFontMgr` 工厂都不定义。第二，这个 Cairo 端口把传入的 context 原样保存，并在每个字形上回调 `mozilla_*SharedFTFace`，所以传 `nullptr` 必然在 `mozilla_LockSharedFTFace` 解引用空指针——换成真实 `SharedFTFace` 后该崩溃消失。第三，用 WebRender 的真实 Rust 导出满足 `mozilla_glyphslot_embolden_less` 是对的：整个 `libgkrust.a` 里该符号所在 CGU 是 1.47 GB 单体，2 GiB 容器直接 OOMKilled；只取 `wr_glyph_rasterizer` 那个 7.7 MB 成员即可，因为该导出自带独立 text 段、只调用 `FT_MulFix`/`FT_Outline_Embolden`/`FT_GlyphSlot_Embolden`。第四，FreeType 的间接依赖（libpng/libbz2/libbrotlidec/libz）不在编译镜像里，`DT_RUNPATH` 只覆盖二进制自身的直接依赖，必须给运行期搜索路径。

最终可执行文件 8,413,304 字节、链接成功（`link_rc=0`），运行以 `SIGSEGV` 退出，且 `stderr` 只有 `stage:ctor` 一行、`rip 0x0`、`advance anchor 0x0`——说明故障发生在本探针构造函数之后、`main` 写入任何阶段标记之前，是某个静态初始化通过空函数指针发起调用。这一轮没有画出任何字形、没有比较任何像素，所以**不构成 Canvas 文字验收**。回执 `deliverables/linux-ruyijs-skia-text-r138/skia-text-attempt-validation.json`。定位这个静态初始化需要初始器级别的追踪，而不是继续加阶段标记。

这一轮的**方法本身**给出了可复用的结论，值得单独记下来：用一个什么都不做的 `main`（只写一行 `main reached`）逐级叠加真实 donor 对象，就能把「静态初始化是否干净」和「业务代码是否正确」彻底分开。阶梯十步全部打印 `main reached`：`mozalloc+mfbt` → 76 个 Skia → HarfBuzz 统一对象 → gfx/2d 与运行时 FreeType → XPCOM string → libpref → XPCOM base0 → base1 → threads0 → 真实 `libnspr4.so`。

这同时**纠正了上一轮的错误判断**。上一轮把「加入 `xpcom/base2` 就崩」读成「base2 不安全」，实际是 base2 恰好是第一个需要 `mozilla::Mutex` 的步骤，而定义 `BlockingResourceBase` 的对象此时还没进链接，于是 mutex 在未构造状态下被使用。base0、base1、threads0 各自单独都能通过，它们才是 `BlockingResourceBase` 的真正定义者。回执 `deliverables/linux-ruyijs-ctor-bisect-r144/ctor-ladder-validation.json`。

剩下的问题收敛得很具体：即使 base0/base1/threads0 和 `libnspr4` 都已链接、且 `libnspr4.so` 已实测是 `NEEDED` 项，文字探针仍在 `SharedFTFace` 构造内部以 `rip 0x0` 结束——mutex 构造函数里还有一处间接调用解析到地址 0。这条路径要真正打通，需要在探针里提供 XPCOM 的静态初始化入口，而不是继续逐个对象试链。此前所有文字相关结论保持为「未验收」。

这一轮找到了剩余 12 条私有引用里那 4 条字体几何引用的**真正根因**，并且是工程缺陷而不是缺依赖：私有 `src/web_geometry/font_backend.h` 无条件 `#include <windows.h>`、`<dwrite.h>`、`<wrl/client.h>`，所以四个 Canvas 文字 owner（`MeasureCanvas`、`BuildCanvasGlyphMasks`、`CanvasGlyphRuns`、`ReleaseCanvasGlyphRuns`）在非 Windows 上**根本无法编译**，Linux 分支自然一行实现都没有。

按上游树早已采用的同一约定修好：Windows 路径保持逐字节不变，非 Windows 提供 owner 实际用到的 DirectWrite 值类型与接口面（`DWRITE_FONT_METRICS`、`DWRITE_GLYPH_METRICS`、`DWRITE_GLYPH_OFFSET`、`DWRITE_GLYPH_RUN`、`DWRITE_MAKE_OPENTYPE_TAG`、`SUCCEEDED`/`FAILED`、`ComPtr`、`IDWriteFontFace`），Darwin 继续走 `font_face_mac.cpp`。

新增 `src/web_geometry/font_face_linux.cpp` 用真实 FreeType 实现这层接口，数值语义按 DirectWrite 而不是 FreeType 的默认：度量取 design unit、`advanceWidth` 无符号、侧边距有符号、`verticalOriginY` 取 y 向下墨迹顶、`TryGetFontTable` 返回带所有权释放上下文的缓冲、tag 字节序按 owner 既有假设。编译过程暴露三个真实错误：`const void*` 到 `FT_Face` 的 `static_cast` 掉限定符且无法用那种形式的 `const_cast` 恢复；`TT_OS2` **根本没有下划线字段**，下划线数据在 post 表里、FreeType 直接挂在 face 上。

结果：原生 AMD64 `compile_rc 0`，12 个接口方法（含两个构造、析构、`GetMetrics`、`GetGlyphIndices`、`GetDesignGlyphMetrics`、`GetGdiCompatibleGlyphMetrics`、`TryGetFontTable`、`ReleaseFontTable`、`AddRef`、`Release`、`CoreFont`）逐一在目标文件里确认为已定义，对象 SHA-256 `49252f2b…`。**这只是编译**：没有打开任何字体、没有查任何字形、没有比对任何度量。`GetGlyphRunOutline` 属于独立的描边接口、Linux 侧仍未实现，那 4 个 `SystemFonts` 方法也还没有函数体。回执 `deliverables/linux-ruyijs-font-face-r155/font-face-compile-validation.json`。

平台拆分之后立刻得到两个真实结论，一个好消息、一个坏消息，都必须分开记。

**好消息：`canvas_text` 与 `glyph_runs` 第一次在 Linux 上编译通过。** 原生 AMD64，对象 SHA-256 分别是 `53b3dbdc…`、`1dea82aa…`。而剩余 4 条私有引用——`MeasureCanvas`、`BuildCanvasGlyphMasks`、`CanvasGlyphRuns`、`ReleaseCanvasGlyphRuns`——**全部定义在这两个文件里**，不在别处。所以之前认为「还要另找实现」的判断是错的，实现一直都在，只是编译不了。过程中还纠正了第二个真缺陷：`IDWriteFontFace` 原先被我放进命名空间，而 `glyph_mask.h` 按 Windows 头的习惯在**全局**前向声明它，于是报“member access into incomplete type”——把它移回全局作用域后 `glyph_runs` 立即通过。

**坏消息：能编译不等于能链接。** 逐个查这两个对象未定义的私有符号，得到的清单是：`canvas_text` 需要 `CanvasFontBaselines`、`FontCollection::Initialize`、`FontCollection::Select`、`MissingFontRun`、`ShapeFont`；`glyph_runs` 需要 `FontCollection::Initialize`、`FontCollection::Select`、`GlyphColorMask`、`GlyphMask`、`ShapeFont`。这些符号的**定义方本身仍然只在 Windows 上可编译**：`glyph_mask`／`glyph_color`／`glyph_palette`／`glyph_style` 分别要 `dwrite_2.h` 的 rendering params、COLR 接口和 palette 接口，`canvas_text_path` 要 `d2d1.h` 的 Direct2D 几何 sink，`GetGlyphRunOutline` 更是整个缺失。

所以真实的剩余工作量不是「补 4 个函数」，而是「把 mask／colour／palette／style／outline 五个 owner 从 DirectWrite 专有接口上剥下来」。这一轮把这句话从推测变成了有清单的实测。回执 `deliverables/linux-ruyijs-canvastext-r156/canvas-text-compile-validation.json`。没有链接、没有打开字体、没有查字形、没有任何度量或像素比对。

这一轮把「字体选择」这一层真正打通了。`FontCollection::Initialize` 与 `Select` 原本只有 DirectWrite 实现，现在有了 Linux 版：用 Fontconfig 解析同一个 `FontInput`（家族列表、引号、generic 替换、`-moz-default`），再用 FreeType 打开选中文件，交给上层的 `SelectedFont` 与 Windows 完全同形——所以四个 Canvas owner 这一层不需要任何平台分支。`LineMetrics`／`SvgLengthMetrics` 用的 Fontconfig/FreeType 度量集合也挂在同一个对象上，不再走第二条路径。

四个单元连同真实依赖一起编译通过（原生 AMD64）：

| 单元 | 对象 SHA-256 |
|---|---|
| `font_face_linux` | `404e9154…` |
| `font_collection_linux` | `dbc87472…` |
| `canvas_text` | `28a21287…` |
| `glyph_runs` | `827872df…` |

**关键进展在未定义符号清单上**：`font_collection_linux` 现在剩下的私有依赖全是**可移植代码**——`CssSplit`／`CssTrim`／`CssLower`、`DefaultGenericFamily`、`GenericFamilyOverride`、`FontFamilyVisible`、`LinuxResolveFonts`。这些在 Linux 上都已能编译，不再是 Windows 专有接口。也就是说字体选择这条链已经解决。

真正还剩的是上层：`ShapeFont`、`CanvasFontBaselines`、`MissingFontRun` 在 `font_shaping.cpp`／`font_missing.cpp`，`GlyphMask`／`GlyphColorMask` 在 `glyph_mask.cpp`／`glyph_color.cpp`，它们仍然要 `dwrite_2.h`。这一轮如实把缺口缩小成这两组，而不是笼统说「Canvas 文字还没好」。回执 `deliverables/linux-ruyijs-lincollect-r158/lin-collection-validation.json`。仍然没有链接、没有打开字体、没有查字形、没有任何度量或像素比对。

这一轮把缺口又缩小了一格，并且把一个「看起来只是路径问题」的坑判成了设计耦合。

**打通：`font_shaping` 编译通过**（对象 SHA-256 `d99f83bb…`）。它正好定义 `ShapeFont` 与 `CanvasFontBaselines`——上一轮清单里五个 Windows 专有符号中的两个，现在有了能在 Linux 上编译的真实实现。

**卡住：`font_missing`（`MissingFontRun`）。** 它从 Mozilla 只借了一个二元属性 `Default_Ignorable_Code_Point`，但那个头文件 `mozilla/intl/UnicodeProperties.h` 会连带拉进整棵树，且每修一处就露出更深一层：

```
UnicodeProperties.h  →  mfbt (需 XP_UNIX，否则 UniquePtrExtensions 报 "Unsupported OS?")
                     →  nsError.h  →  ErrorList.h（objdir 生成文件）
                     →  nsISupportsImpl.h  →  prthread.h（NSPR）
                     →  prtypes.h  →  obsolete/protypes.h
```

我一开始把它当成挂载路径没配全，逐个补了 `XP_UNIX`、objdir 根、NSPR include——每补一个就前进一层，但这一层背后永远还有一层。到 `obsolete/protypes.h` 时判定：这已经不是路径问题，而是**为一个布尔值把 mfbt／XPCOM／NSPR 整条头文件链和运行时都绑进私有树**的权衡问题。

**这是一个需要决策的分叉，不是继续试错能解决的**：要么把真实 Mozilla 头文件链及其运行时接进来，只为这一个判断；要么在私有树里自己实现 `Default_Ignorable_Code_Point`。注意 HarfBuzz 只暴露 general category，**没有**这个二元属性，而用 category 近似会把集合里的 `Lo` 与 `Mn` 成员判错，所以不能拿 category 糊弄过去。

回执 `deliverables/linux-ruyijs-shaping-r160/shaping-compile-validation.json`。仍然没有链接、没有打开字体、没有查字形、没有任何度量或像素比对。

上一轮那个「为一个布尔值拉进整条 Mozilla 头文件链」的分叉，这一轮选了第二条路：**在私有树里自己实现 `Default_Ignorable_Code_Point`**，不再依赖 `mozilla/intl`。

关键是不能凭印象写。第一版我就是凭记忆列了一小张表，**整个 Cf 与 White_Space 部分全漏了**——如果只抽样测几个码点，这个错误完全测不出来。所以做法是从规范定义出发：`Other_Default_Ignorable_Code_Point + Cf + Variation_Selector + White_Space` 减去列明的例外，用 Unicode 数据算出完整集合，压缩成 **23 个连续区间、4204 个码点**。

然后用**全集合比对**验证，而不是抽样：

| 项 | 值 |
|---|---|
| 目标 Unicode 版本 | 13.0.0 |
| 独立基准（Python `unicodedata`） | 4204 |
| 私有实现输出 | 4204 |
| 缺失 | 无 |
| 多余 | 无 |

比对过程还暴露了一个容易误判的地方：host185 镜像里的 Python 是 **Unicode 9.0**，拿它当基准会把 `0x13439–0x1343f`（Unicode 14 才分配的埃及象形文字格式控制符）报成“缺失”。在 13.0 与 9.0 之间做比对，差异来自版本而不是表。所以现在基准**锁定 13.0**，版本不符时明确报 `inconclusive`，而不是报 mismatch。

这里要记清一条判断依据：**HarfBuzz 只暴露 general category，没有这个二元属性**；而这个属性既不是“Cf”也不是“White_Space”——它会加上变体选择符、又会减掉两者的成员，用近似集合会判错真实码点。

回执 `deliverables/linux-ruyijs-unicode-r161/unicode-ignorable-validation.json`。`font_missing` 还没链接、没打开字体、没查字形。

这一轮做了一件此前一直没有做过的事：**真正执行了 Linux 字体路径**，而不只是编译。用的单元是自足的 `font_metrics_linux` 与 `font_shape_linux`——`font_config` 把 fonts 配置组和 SpiderMonkey 绑定写在同一个文件里，属于完整产品链接，不该为探针拆开，所以 `MeasureCanvas` 这一轮没跑。

真实运行 12 项全部通过，且数字与历史基准**逐项一致**：

| 指标 | 本轮 x86_64 | r99 x86_64 exact-probe | 结论 |
|---|---|---|---|
| `line` | 18.6333 | 18.6333 | 一致 |
| `ex` | 8.75 | 8.75 | 一致 |
| `ch` | 10.1833 | 10.1833 | 一致 |

`ic=16.0000`、`cap=11.6667`，32px 时各项**翻倍**，0.001px 的尺寸**向下取整为零且不报错**，HarfBuzz／FriBidi 塑形 `Hamburgefonstiv` 得到 `length=138.0667`、每个字符都有盒子、盒子有高度。

过程中暴露了真实的依赖闭包，这是之前从未测到的：Fontconfig 需要配置文件与字体目录（否则**一个字体都选不到**），而完整运行时闭包是 `libfreetype`、`libfontconfig`、`libharfbuzz`、`libfribidi`、`libexpat`、`libglib-2.0`、`libpcre2-8`、`libgraphite2`、`libpng16`、`libbz2`、`libbrotlidec`、`libz`——每缺一个就在加载期失败，逐个才补齐。

一个细节值得记：只读运行时下 Fontconfig 会打印 `No writable cache directories`，那是**缓存警告而不是查找失败**，所有度量都正常解析。

回执 `deliverables/linux-ruyijs-font-measure-r163/font-measure-validation.json`。

这一轮把上一轮刻意没跑的 `MeasureCanvas` 真正链接并执行了：13 个单元编译、链接成功，**10 项检查通过 9 项**。为此先做了一次按职责的重构——`font_config.cpp` 原来把配置值、读访问器和 SpiderMonkey 写入入口塞在一个文件里，导致「只读配置」的单元也要 `jsapi` 才能编译。把配置状态与三个读访问器拆到 `font_config_state.cpp`（只依赖标准库），JS 写入侧留在原处；Windows 两个单元都链接，行为不变。

按单元实测的边界现在是：`font_preferences`、`font_config_state`、`font_shaping`、`canvas_text`、`system_font`、`css_components`、`unicode_default_ignorable` 全部独立成立，只有 `font_config.cpp` 需要 SpiderMonkey——因为它是 JS 入口，这个划分是对的。

链接过程中还补上了两处真实的平台缺口，而不是绕过：

- `FrameMaxDescent` 整个落在 `_WIN32` 分支里，但它的算法只是对字体度量做算术，唯一平台耦合点是 `BadUnderlineFamily`。把函数移到平台块之外共用，并为 Linux 用 SFNT `name` 表实现同一张 CJK 家族名单的判定。
- `BadUnderlineFamily` 因此在头文件里有了跨平台声明，Windows 定义也要离开匿名命名空间以匹配——**函数体一字未改**。

**通过 9 项**：单字推进为正、单字有墨迹、墨迹在字体盒内、alphabetic baseline 为零、ascent/descent 为正、两字推进大于一字、两字等于一字的 2 倍、空格有推进、双倍尺寸双倍推进。实测 `width16=8.0000`、`width32=16.0000`、`ascent=15.0000`、`descent=4.0000`。

**失败 1 项，是个真实语义问题**：`spaces report no ink`。三个空格报告的墨迹框是 `left=0.7969 top=-14.1094 right=27.9969 bottom=4.7188`——纵向与单字 `H` 完全一致。原因是 `font_shaping.cpp` 处理空格推进后**继续走通用墨迹累积**，把按推进算出的框并进了 run ink。这不是移植引入的：`font_shaping.cpp` 是共享单元，Windows 走同一条路径。而 r99 的探针从未测过空格，所以此前没有任何回执覆盖到它。

修它会同时改变两个平台的生产行为，因此**这一轮不改**——那是一个应当单独决定的问题，不该夹在移植探针里顺手做掉。回执 `deliverables/linux-ruyijs-measure-canvas-r163/measure-canvas-validation.json`。

上一轮我把 `spaces report no ink` 的失败判成「共享代码的既有行为」，理由是 `font_shaping.cpp` 是共享单元。**这个判断是错的**，错在我没有验证输入。这一轮直接测了每个码点的真实设计度量：

```
space  gid=3  adv=651  lsb=0  rsb=651  advH=2048  voy=0  ink_w=0  ink_h=2048
```

问题一眼就出来了：**`ink_h=2048`**。所有者读这些字段时是把它们当一个墨迹矩形用的——高度 = `advanceHeight - tsb - bsb`、顶 = `tsb - voy`。而我写的 `GetDesignGlyphMetrics` 把 `advanceHeight` 取了 FreeType 的 `vertAdvance`（字体无 vmtx 时返回 em 高度），`topSideBearing` 又来自**水平**方位。于是每个字形都报成 em 高，宽度为零的空格也就有了盒子。

按 Mac 实现的语义修正后：

| 码点 | 修正前 `ink_h` | 修正后 `ink_h` |
|---|---|---|
| `H` | 2048 | 1493 |
| `space` | 2048 | **0** |
| `0` | 2048 | 1549（墨迹底 −29） |

`0` 的 −29 是真实的：DejaVu Sans 的零确实下沉 29/2048 em 做视觉对齐。修正后的数值经得起核对，修正前只是把一切都抹成 em 高。

对 `MeasureCanvas` 的效果：`H` 的墨迹盒从 `[-14.1094, 4.7188]` 变成 `[-11.2812, 2.8281]`——这才是真实的 ink 盒。

**但空格仍然报墨迹**，而根因已经查到底：`font_shaping.cpp` 用 `InkBox ink{0, -ascent, 0, descent}` 起手，这个框本身就有高度，随后 `ink.right = max(ink.right, advance)` 又把它撑到整个推进。算术核对完全吻合（ascent 900、descent 240、推进 1440 app units）。这一段**这一轮没改**：它与 Windows 共享，而 r99 的基准数字又出自同一份代码，改它会同时移动生产行为和参照值——那是应当单独决定的事。

回执 `deliverables/linux-ruyijs-glyphmetrics-r179/glyph-metrics-validation.json`。

`MeasureCanvas` 现在**十项全过**（`failures: 0`）。这个结果不是靠调整预期得来的——是修掉三个真缺陷之后自然成立的。

**缺陷一：tag 被交换了两次（最关键）。** `TryGetFontTable` 的调用方传入的是 DirectWrite tag，也就是四字符 tag 的字节反转读法：HarfBuzz 要 `'cmap'`，共享的 `ReadTable` 先做一次 `_byteswap_ulong` 再交下来。我却又按数值高位重建了一遍，等于换回原样再翻转，于是每次查表实际问的是 `'pamc'`。后果是**所有表都取不到**，`ShapeFont` 对任何字符都返回 glyph 0——`H` 和空格都必须用 `.notdef` 的度量。

这一点是靠直接调用 `ShapeFont` 打印 run 才看见的：修之前 `glyph ids: 0`，修之后 `43`（H）与 `3`（space）。

**缺陷二：`Select` 每次调用都新建 face。** Canvas owner 用**指针比较**来切分 run，指针永不相等就意味着每个字符各自成一个 run。改为在 collection 内按文件与索引缓存。

**缺陷三：缓存交给 `ComPtr` 时用了 `Attach`。** `Attach` 把裸指针交给一个新的 `shared_ptr`，于是同一对象有两个主人，探针直接以 SIGABRT 退出。新增 `Share` 复制所有权。

修复后的实测值经得起对账：

| 项 | 值 | 对账 |
|---|---|---|
| `width16` | 12.0333 | 与 HarfBuzz 设计推进 12.0312 一致 |
| `width32` | 24.0667 | 正好翻倍 |
| `ShapeFont("H")` | 722 app / glyph 43 | 正确字形 |
| `ShapeFont(" ")` | 305 app / glyph 3 / **ink 为空** | 空格无墨迹 |

同时纠正了前两轮的判断：把空格报墨迹说成「共享代码既有行为」是错的，根因在本移植的度量与 tag 处理。`font_shaping` 的 run ink 初值也改为空——`ProjectInk` 本身会合并字体盒，SVG 结果不受影响，这个等价关系先用算术验证过，再用十项全过的 canvas 结果确认。

回执 `deliverables/linux-ruyijs-measure-pass-r190/measure-pass-validation.json`。

字形掩码（`GlyphMask`）现在也在 Linux 上真正跑通了：**13 项全过**。

实现方式和 `MeasureCanvas` 那条链不同——掩码不需要绕 XPCOM，直接交给 FreeType：把 face 设成设备 em，把 `linear` 矩阵作为轮廓变换传进去，亚像素偏移折进 `FT_Set_Transform`（y 轴翻转），渲染普通灰阶位图，最后用**同一张 Skia mask 表**做校正。这样它的输出语义与 DirectWrite 那条路一致，而实现只依赖 FreeType。

实测 `H` 在 32px 下：

| 项 | 值 |
|---|---|
| glyph | 43 |
| box | `[3, -23, 18×23]` |
| 覆盖像素 | 214 / 414 |
| 最暗值 | 0（纯黑） |

这些数字互相自洽：18 像素宽对应约 0.56 em，23 像素高对应约 0.72 em，起点在笔位右 3px、基线之上 23px——正是一个 `H` 该有的位置。检查项还包括双倍尺寸把宽高都翻倍、亚像素偏移不改变位图尺寸、以及**空格产出空掩码而不是失败**（空格有推进、没有轮廓，空掩码就是正确答案）。

过程中做了一次必要的职责重划：`glyph_style.cpp` 是 DirectWrite 的**渲染模式选择器**，它读渲染参数、比较 `DWRITE_RENDERING_MODE` 常量，Linux 上根本没有这个概念。于是整个单元归为 Windows-only，由 Linux 掩码单元自己回答 `GlyphStyle`、`SystemTextGamma`、`SystemTextContrast`——canvas 要的只有灰阶一种模式。

上一轮那个 `LINK_FAIL` 的真实原因也记下来了：探针的编译单元列表漏了 `glyph_style`，而 `SystemTextGamma` 定义在那里。补上之后才暴露出更根本的问题——那个单元本身不该在 Linux 编译。

回执 `deliverables/linux-ruyijs-glyphmask-r191/glyph-mask-validation.json`。

彩色字形的第一层——**调色板解析**——在 Linux 上通了。`GlyphPalette` 原本走 `IDWriteFontFace2::GetPaletteEntries`，Linux 版直接解析 CPAL 表；`GlyphColorMask` 里 `sampled` 分支用的 `IDWriteFontFace1` head 盒也改成读 SFNT `head` 表（xMin/yMin/xMax/yMax 在 36/38/40/42，y 向上，所以盒顶是 yMax、盒底是 yMin）。

验证用了两款**真实**字体，不是构造数据：

| 字体 | 结果 |
|---|---|
| `TwemojiMozilla.ttf`（带 COLR+CPAL） | 1063 个 entry，首个为 `0x0e000000` |
| `DejaVuSans.ttf`（纯文本） | 无调色板 |

`0x0e000000` 与我用 Python 独立解析同一张 CPAL 表算出的值**完全一致**——这是交叉验证，不是自证。

过程中查出一个真实字体怪癖，值得单记：**TwemojiMozilla 把 entry 数量写在了第一个 color record index 的位置**，于是那个索引指向数组末尾之外一个 entry。按规范应当拒绝，但 Firefox 的 table reader 是容错的、而且能正常渲染这个字体——拒绝它等于丢掉一个浏览器能显示的彩色字体。所以按真实行为容错：仅当从 0 起算记录能放下时才接受（`8 + 1063×4 = 4260 ≤ 4266`）。同时纠正了一处偏移错误：记录数组起点是「6 + 每调色板 2 字节」，不是 12。

这也是为什么先用「malformed」预期跑出 `ok` 反而说明问题——那个 `ok` 掩盖了解析器根本没读到颜色。改成真正验证成功路径后才暴露。

回执 `deliverables/linux-ruyijs-glyphcolour-r195/glyph-palette-validation.json`。

彩色字形的第二层——**COLR 图层路径**——也通了。用真实的 `TwemojiMozilla.ttf` 里第一个 base glyph（`0x0f`，两层）：

| 项 | 值 |
|---|---|
| 图层数 | 2（表中就是 2） |
| 图层盒 | `[0,-28,32×32]`、`[7,-23,16×22]` |
| 图层颜色 | `rgba(225,255,0,170)` |

颜色与独立 Python 解析的 palette entry 658（`BGRA 0,255,225,170` → `rgba 225,255,0,170`）**逐字节一致**。纯文本字体则干净地报告“无图层”，而不是空成功。

## 两个探针自身的错误，都被数据纠正了

**一是传了空变换。** 探针给 `GlyphColorMask` 传 `linear = nullptr`，而 `sampled=false` 路径会解引用它，于是 SIGSEGV。真实调用方永远会传矩阵，是探针错了。

**二是断言写反了。** 我断言“两层颜色应当不同”，实测两层都是 `225,255,0,170`。查真实表才发现：**两层确实共用 palette index 658**，所以相同颜色才是正确答案。断言改成检查“是否为表中命名的那个 entry”，而不是“是否互不相同”。

这两处都说明同一件事：**断言要跟着数据走，不能跟着直觉走**。如果第一次就把“颜色不同”当成 bug 去改代码，会把正确的实现改坏。

顺带解除最后一处平台耦合：`glyph_color.cpp` 在非 Windows 下不再包含 `dwrite_2.h`——COLR 表读取和 head 盒都不需要它。

回执 `deliverables/linux-ruyijs-colr-r195/colr-validation.json`。

字形轮廓（`BuildCanvasTextPath`）也在 Linux 上打通了，**14 项全过**。原来那套走 Direct2D 几何 sink，非 Windows 没有对应物；Linux 版改用 FreeType 的 outline 分解，把同一批 `CanvasTextPath` verbs 发出去——合成斜体在设计空间里施加，每个字形从 run 的笔位落笔。

实测 `H` 在 32px 下：`move=1 line=12 close=1`、26 个点、`extent x=[3.14, 20.92] y=[-23.33, 0]`。

关键对账：**宽 17.78px 恰好等于 `1138/2048×32`**（设计度量表里的值），所以这不是“看起来合理”，而是数值正确。

## 过程中修掉三个真实缺陷

| # | 缺陷 | 症状 |
|---|---|---|
| 1 | 设计单位→CSS 的系数**又除了一次 60** | 32px 的 `H` 只有 0.30 宽，应为 17.78 |
| 2 | FreeType 的 y 向上、canvas 的 y 向下，**没有翻转** | 字形跨 `0..23.33`，应跨 `-23.33..0` |
| 3 | **轮廓从未闭合** | 缺 `close` verb，与 Windows 的 `EndFigure` 不一致 |

外加一处**探针自己的错误**：我断言 `H` 的轮廓里有二次曲线，但 `H` 全是直线。曲线检查改到 `O` 上做——`O` 确实有 quad，而 `H` 断言为 0 条，两个方向都验证到了。

这三个产品缺陷有一个共同点：**都是我写的映射/换算出错，不是 FreeType 的问题**。而且每一个都是靠“与独立算出的数值对账”发现的，不是靠“看着像不像”。

回执 `deliverables/linux-ruyijs-textpath-r202/text-path-validation.json`。

最后一层 `sampled` 颜色快照也通过了。这条路径按字体的 **head bbox** 决定 2× 快照画布，而不是按字形，所以验证必须对着表算：`TwemojiMozilla` 的 bbox 是 `(-27,-91)-(541,477)`、512 upem，32px 下取整得到 `[-2,-30,36×36]`——**与实测逐值一致**。

## Canvas 文字在 Linux 上的完整状态

五层全部有实际执行结果：

| 层 | 结果 | 验证方式 |
|---|---|---|
| 度量 `MeasureCanvas` | 10/10 | `width16=12.0333` 对上 HarfBuzz 设计推进 |
| 掩码 `GlyphMask` | 13/13 | `H` 的 18×23 盒、214 覆盖点尺寸自洽 |
| 调色板 `GlyphPalette` | 3/3 | 首项与独立 Python 解析一致 |
| COLR 图层 | 7/7 | 两层颜色对上 palette entry 658 |
| 轮廓 `BuildCanvasTextPath` | 14/14 | 宽 17.78px 对上 `1138/2048×32` |
| 快照 `sampled` | 11/11 | 盒 `[-2,-30,36×36]` 对上 head bbox |

这些数字的价值在于**每一条都对得上一个独立算出的值**，而不是「跑通了就算过」。途中修掉的每一个缺陷——度量语义、tag 双重交换、face 身份、缩放系数、y 轴方向、轮廓闭合——也全部是靠这种对账发现的。

## 仍然缺失的

这里的边界必须说清楚：**以上都是单元级执行，没有一条经过产品链接**。缺的仍然是 `dist/js`、真实页面 canvas、浏览器渲染。这不等于 Canvas 在私有产品里可用，只等于它的每一层在 Linux 上各自算对了。

回执 `deliverables/linux-ruyijs-sampled-r205/sampled-validation.json`。

## `skia_target` 打通了：Linux 上真正画出了文字

`FillText` 通过从 FreeType face 构造的 Skia typeface 在 CPU 面布上画出一个 32px 的 `H`：**6 项全过**，`inked=222`，墨迹盒 `x=11..28`、`y=20..43`。起点在 (8,44)、基线之上——17px 宽、23px 高，几何正确。

## 根因：一个从未被链接的 mutex 实现

真正的修复只有一行——**链接 `mozglue/misc/Mutex_posix.o`**。

链条是：`SharedFTFace` 持有 `mozilla::Mutex` → 继承 `OffTheBooksMutex` → 继承 `detail::MutexImpl`（声明在 `mozglue/misc/PlatformMutex.h`）→ **实现只在 `Mutex_posix.o` 里**。之前所有链接都没带它，于是 `Mutex::Lock()` 内联的那个调用没有实现可解析，运行时跳到地址 0。

**验证方式是隔离实验**：一个不链接 Skia、只开字体并调 `SkiaFaceContext()` 的探针，加上 `Mutex_posix.o` 之前崩在构造函数里，加上之后立刻输出 `context=0x...`、`lock=1`，五个钩子全通过。这把故障与 Skia 彻底分开。

## 前两轮的归因都不对，需要记下来

| 轮次 | 当时的结论 | 实际 |
|---|---|---|
| 第 128 轮 | `PR_CallOnce` 被 section GC 删除 | 错：`PR_CallOnce` 只在 NSS 目标文件里 |
| 第 129 轮 | `BlockingResourceBase` 是空壳 | 也不算对：空壳对非 debug 构建是**正常的**，缺的是 `MutexImpl` |

这两次都是**看起来很有解释力、但没验证到根**的结论。真正的定位靠的是把故障范围缩到一个不含 Skia 的最小探针，然后逐个补齐它调用的实现。

## 一处探针自身的缺陷

修好 mutex 后第一次运行报 `FillText` 成功但 `inked=0`——因为 `Pattern` 默认颜色 alpha 为 0。canvas 永远会设颜色，是探针漏了。

回执 `deliverables/linux-ruyijs-skia-draw-r225/skia-draw-validation.json`。

## `skia_target` 接回批次：13 → 6，而且剩下的 6 条全都已实现

把 `skia_target` 从延后清单里移出，在 host185 上真跑完整 Canvas 批次：**64 个单元全部编译，部分链接通过**，`native_canvas_portable_verified 0`。

符号演进：

| 项 | 值 |
|---|---|
| 原有私有引用 | 13 |
| 闭合 | **13（全部）** |
| 新增 | 6 |
| 剩余 | **6** |

**最有价值的是这 6 条是什么**——不是新缺口，而是这几轮已经逐一实现并验证过的函数：

- `SystemFonts::MeasureCanvas`（10/10 通过）
- `SystemFonts::BuildCanvasGlyphMasks` / `CanvasGlyphRuns` / `ReleaseCanvasGlyphRuns`（经 `GlyphMask` 13/13）
- `SystemTextGamma` / `SystemTextContrast`（在 `glyph_mask_linux.cpp`，掩码与绘制两次验证）

它们仍然显示为「未解析」，原因很简单：**批次编译了 `canvas_text` 和 `glyph_runs`，却没有编译定义这些函数体的那些 Linux 单元**。也就是说缺口已经从「没有实现」变成了「没有接进批次」。

## 过程中修掉三处真实的接线错误

1. **延后清单**：`skia_target` 已能编译绘制，不该继续延后；同时保留 ownership guard 要求它存在，防止文件被改名后悄悄离开批次
2. **预期计数**：host 启动器里硬写的 63 要改成 64
3. **头文件路径**：`skia_target` 包含 `font_backend.h` 需要 HarfBuzz 头，而 Canvas 批次不挂 `font-include`；改用 donor 源码树 `/source/gfx/harfbuzz/src`（那里本来就有）

第 3 点我试错了两次：第一次用了不存在的 `/private/font-include`，第二次才发现 `include` 变量在这个批次里是 `null`。两次都是「以为环境里有，其实没有」。

回执 `deliverables/linux-ruyijs-canvas-r229/canvas-batch-validation.json`。

## Canvas 文字层接进批次：13 → 6，剩余是它的下一层

把 `canvas_text`、`glyph_runs`、`glyph_mask_linux` 三个单元加进批次后：**67 个单元全部编译，链接通过**，`native_canvas_portable_verified 0`，ET_REL 369,052,368 字节。

| 项 | 值 |
|---|---|
| 原有私有引用 | 13 |
| 闭合 | **13** |
| 新增 | 6 |
| 剩余 | **6** |

**这 6 条是文字层自己的下层依赖**：`ShapeFont`、`CanvasFontBaselines`、`FontCollection::Initialize`/`Select`、`MissingFontRun`、`GlyphColorMask`。它们每一个都有此前验证过的 Linux 实现，只是这批还没编译 `font_shaping`、`font_missing`、`font_collection_linux`、`glyph_color`。

## 这一轮的教训：加单元不是越多越好

我最初一次加了 10 个单元 + `css_components`，结果链接报**重复定义**——其中 **7 个单元和 `css_components` 早就在前序对象 `runtime-batch.o` 里**。

于是改法：**只加真正定义那 6 个未解析符号的单元**（3 个），让下一轮的 delta 告诉我下面还有哪一层。先 75 个单元（重复），再 68 个（仍重复），最后 67 个（干净通过）——两次重复都是因为没有先查基线里已有什么。

另外修了三处真实接线：延后清单、启动器硬写计数、以及 FreeType/Fontconfig 头文件的挂载路径（`/private` 本身只读，嵌套挂载点建不出来，改挂 `/font-include`）。

回执 `deliverables/linux-ruyijs-canvas-r238/canvas-layer-validation.json`。

## Canvas 批次：13 → 1

四次实测，每次只加「定义当前未解析符号」的单元：

| 轮次 | 单元数 | 剩余 |
|---|---|---|
| 起点 | 67 | 6 |
| 加 shaping/missing/collection/color | 71 | 3 |
| 加 unicode/palette | 73 | **1** |

`73 个单元全部编译、链接通过`，`native_canvas_portable_verified 0`，ET_REL 370,188,864 字节。

## 最后一条：`FrameMaxDescent`，而且它是真的卡住

它定义在 `system_font.cpp`，但**整个单元已经在基线对象里**，再加一次会把 `SystemFonts` 的所有成员定义两遍，链接器直接报重复。

我试着把该函数抽成独立单元，结果破坏了 `system_font.cpp` 的平台分支结构（`#if _WIN32` / `#elif __linux__` 各自闭合命名空间），于是**回退**，没有硬塞。

下一步只有两条路：只编译这一个函数，或把它从基线单元集里摘掉。

## 又学了一次同样的教训

这轮我又踩了同样的坑：加 `system_font` 前只查了 `FrameMaxDescent` 不在基线，**没查整个单元**——而基线里 `SystemFonts::MeasureCanvas`、`LineMetrics`、`CanvasGlyphRuns` 全都在。上一轮刚记过这个教训，这轮又犯了一次。

正确的排查方式是：**按单元查，不是按符号查**。`nm | grep 'SystemFonts::'` 一条就能看出来。

回执 `deliverables/linux-ruyijs-canvas-r241/canvas-residual-validation.json`。

## Canvas 批次：13 → 0，私有引用全闭合

| 步骤 | 单元数 | 剩余 |
|---|---|---|
| 起点 | 67 | 6 |
| + shaping / missing / collection / color | 71 | 3 |
| + unicode / palette | 73 | 1 |
| + `system_font` 共享段 | **74** | **0** |

`74 个单元全部编译、链接通过`，`resolved 13 / introduced 0 / remaining 0`，ET_REL 370,219,344 字节。

`web_canvas` 这一层在 Linux 上**已无任何未解析的私有符号**，13 条全部闭合。

## 最后一条怎么解开的

`FrameMaxDescent` 卡了两轮，原因是 `system_font.cpp` 的 `SystemFonts` 成员已在前序对象里，整单元重编会重复定义。

**解法**：给平台实现加守卫 `RUYIJS_SYSTEM_FONT_SHARED_ONLY`，让该单元**只贡献共享段**。

然后又踩一个坑：共享段失去了平台分支提供的类型声明，报 `unknown type name 'IDWriteFontFace'`——补上 `font_backend.h` 才过。

上一轮我试着把函数抽成独立文件，结果破坏了 `#if` / `#elif` 分支结构；这一轮的守卫法**不改文件结构**，只控制编译范围，才是对的。

## 这证明了什么，不证明什么

**证明**：canvas 表面需要的每个私有符号，都有 Linux 实现被批次编译并链接。

**不证明**：产品已链接，或浏览器能画出东西。产品链接、`dist/js`、真实页面 canvas、浏览器仍是空的。

回执 `deliverables/linux-ruyijs-canvas-closed-r243/canvas-closure-validation.json`。

## 产品 transport 库在 Linux 上构建成功

`src/client` 一直是产品 shell 的入口，有完整的 `CMakeLists.txt`，却**从未在隔离环境里构建过**。这一轮把它跑通：**`exported_abi_verified 0`**。

| 项 | 结果 |
|---|---|
| 编译 | `api`、`transport`、`lifecycle_linux` 全过（`-Wall -Wextra -Werror`） |
| 链接 | `--no-undefined` + version script |
| 导出 ABI | **精确等于** script 的 7 个符号 |
| 未定义符号 | 全部是带版本的运行时导入 |

导出的七个 C 入口：`ruyijs_alloc`、`ruyijs_call`、`ruyijs_close`、`ruyijs_create`、`ruyijs_create_mode`、`ruyijs_free`、`ruyijs_set_callback`。

## 查出四个真实缺陷

1. **`SO_NOSIGPIPE` 是 BSD 专有**——`transport.cpp` 在 Linux 上根本编译不过。改用 `accept4` + `MSG_NOSIGNAL`
2. **`ChildExited` 的声明和定义都没提交**——`transport.cpp` 引用了它，头文件里没有
3. **`lifecycle_linux.cpp` 和 `CMakeLists.txt` 是未跟踪文件**——任何导出的树都构建不出这个库
4. **我的未定义符号检查把 `_Unwind_Resume@GCC_3.0` 判成失败**——它是正常的 libgcc 导入

前三个说明一件事：**Linux 移植工作在树里放了一堆未提交文件**，所以之前每一轮 `git archive` 导出的都是编译不过的旧版。

## 一处流程漏洞

我的密钥检查命中后只打印 `HIT`，**没有中止提交**。两次命中的都是变量名 `token`（`getentropy` 填充的 16 字节随机数），内容无害，但门禁应当阻断而不是提示。

回执 `deliverables/linux-ruyijs-client-r249/client-build-validation.json`。

## 客户端 C ABI 端到端跑通

上一轮只证明库能构建，这一轮**真的跑起来了**：**`client_abi_verified 0`，9 项全过**。

| 步骤 | 结果 |
|---|---|
| `ruyijs_create` | 启动 shell 并连上它的 listener |
| `ruyijs_call` | 写帧、读帧，载荷原样回传 |
| 第二次 `ruyijs_call` | 同一上下文仍可用 |
| `ruyijs_close` | 正常返回 |
| `ruyijs_alloc` / `ruyijs_free` | 分配释放配对 |

实际回复：

```
{"mode":"default","echo":"{"op":"echo","value":42}"}
```

帧格式是**小端 u32 长度 + 载荷**，走真实 unix socket，`--ruyijs-rpc` 与 `--ruyijs-mode` 两个参数原样传到子进程。

## 这一步证明什么，不证明什么

**证明**：transport 层、进程生命周期适配器、C ABI 封装，在 Linux 上端到端可用。

**不证明**：JavaScript 执行。因为 shell 是**为测试写的 echo 程序**，不是 RuyiJS 运行时。真实的运行时 shell 需要 `dist/js`，那还没做。

这个区别很重要：ABI 通了不代表能跑脚本，中间还隔着整个运行时。

回执 `deliverables/linux-ruyijs-client-abi-r250/client-abi-validation.json`。

## 真实 SpiderMonkey 运行时跑起来了，但它还不是 RuyiJS

**`runtime_shell_verified 0`**：容器里 `JavaScript-C159.0` 正常启动，脚本算出 `{"sum":385,...}`。这是 RuyiJS 依赖的**同一个引擎**（`FIREFOX_159_0_RELEASE`）。

它必须在容器里跑，因为它需要 **glibc 2.27/2.29 和 GLIBCXX 3.4.32**，宿主机 CentOS 7 都没有，而 Ubuntu 24.04 镜像有。

## 但它不认识 RuyiJS

```
js --help | grep -c ruyijs   →   0
```

这是纯上游 shell，**没有任何 ruyijs 选项**。所以上一轮那个 ABI 测试只能用 echo 替身——真实的运行时现在接不上客户端。

## `dist/js` 到底是什么

`tools/generate.py` 把 RuyiJS 的选项和运行时调用**注入 donor 的 `js.cpp`**：

- `--ruyijs-rpc` / `--ruyijs-mode` / `--ruyijs-runtime` / `--ruyijs-worker` 四个选项
- `ruyijs::Run(cx, op, RunShellJobs)` 替换默认的 `ProcessArgs`
- 异常捕获和 Promise 拒绝追踪挂钩
- `runtime_assets.h` 嵌入 codec 源码

生成后重新链接，才是真正的产品 shell。

## 可行性判据

已通过的 `donor_relink_control` 证明：**28 个对象 + 3 个归档能做到字节级一致的重链，且不含任何私有 shell 对象**。所以把生成的 shell 单元加进同一条链接命令是可行的。

第 128 轮的 OOM 来自**单个 1.47 GB 编译单元**，不是这个形态。这两件事必须分开看。

## 现状

`linux_donor.py` 只有 `--prepare`（生成源码，状态 `generated-only`）和 `--relink-control`（重建 donor），**没有“链接私有 shell”的入口**。那一步还没实现。

回执 `deliverables/linux-ruyijs-runtime-r251/runtime-shell-validation.json`。

## 产品 shell 生成器在 Linux 上跑通了

**`shell_generate_verified 0`**：`tools/linux_donor.py --prepare` 产出 7 个文件，注入全部到位。

| 项 | 值 |
|---|---|
| 状态 | `generated-only` |
| 生成文件 | `js.cpp`、`Unified_cpp_js_src_shell0.cpp`、`runtime_assets.h` + 4 个配置头 |
| 候选单元 | **1275** 个 |
| `ruyijs-rpc` 选项 | 出现 3 次 |
| `ruyijs::Run` 调用 | 1 次 |
| codec 嵌入 | 3481 字节 |

Firefox HEAD 与固定参照一致。

## 清掉三个阻塞

1. **`tools/donor.py` 直接拒绝 Linux**，所有调用停在 `donor OS_ARCH is not supported`
2. **`tools/product_sources.py` 没有 `target_platform` 参数**，生成器在源清单调用处失败
3. **`config.status.json` 记录的是 `/source` 和 `/work`**，必须在容器里挂到这些路径，而不是翻译路径

## 第四次同样的坑

前两个工具的改动**都是未提交的工作区修改**。这是这棵树上第四次 Linux 工作因为没提交而对导出的构建不可见。

第 135 轮记过一次，第 137 轮又遇到，这一轮连撞两次。**这不是偶发，是这个工作流的系统性缺陷**。

## 新增的链接入口

`tools/linux_donor.py --link-product` 已实现：把 donor argv 里的 `shell0.o` 换成生成的单元，拒绝缺失单元、拒绝残留 donor shell、拒绝覆盖已有产物。三个测试覆盖替换、缺失和失败清理。

**但还没对真实的 1275 个单元用过。**

## 边界

`generated-only` 意味着**只证明生成了源码**，不证明这些单元能编译能链接。1275 个单元是源码清单，不是编译通过的证明。

回执 `deliverables/linux-ruyijs-generate-r258/shell-generate-validation.json`。

## 生成后的 shell 单元编译成功

**`shell0_compile_verified 0`**：6,955,912 字节的对象文件，**3 个产品钩子引用**全部在符号表里。

| 钩子 | 状态 |
|---|---|
| `ruyijs::Arguments::Prepare(` | 引用 |
| `ruyijs::Run(` | 引用 |
| `ruyijs::RunWorker(` | 引用 |

这说明**注入的源码对 donor 头文件是合法的 C++**，而且编译器保留了三个产品钩子——**这是个真实的产品 shell 对象，不是空壳**。

## 编译命令是 donor 自己的

没有自己拼 flags，而是从 donor 的 `build.log` 里**原样取出**当年编译 `shell0.o` 的那条命令。这样 flags、include、宏定义都与已被字节级验证的重链所用的对象一致。

只改写五个操作数：

1. 输出对象 → `/tmp`
2. 依赖文件 → `/tmp`（原目录不存在）
3. 源文件 → 生成的单元
4. 加 `-I/private/src`（产品头文件在这里）
5. 生成单元内嵌的绝对路径 → 按它声明的位置挂载

## 这一轮踩的五个坑，全是环境而非代码

1. 提取器文件名写错
2. `git archive` 不保留可执行位，得用 `python3` 调用
3. 生成单元内嵌了产出时的绝对路径 `/genparent/generated/js.cpp`
4. donor 命令里没有私有 include 根
5. donor 命令把 `.deps` 写到不存在的目录

每一个都是“以为环境是这样，其实不是”。这已经是这个项目反复出现的模式。

## 边界

**只证明这一个单元能编译，不证明能链接。** 1275 个候选单元里的其余 1274 个、以及运行时对象都还没编译，`--link-product` 也还没对真实对象用过。

回执 `deliverables/linux-ruyijs-shell0-r265/shell0-compile-validation.json`。

## 产品链接跑起来了，缺口变成一份具体清单

**`product_link 1`** —— 但这一轮的进展在过程里：

| 项 | 结果 |
|---|---|
| 运行时单元编译 | **4/4 全过**，1,219,608 字节 |
| 五个 `ruyijs::` 符号 | **全部有定义** |
| `link_product` 替换 | 正常，donor argv 一路跑到链接器 |
| 链接结果 | 20 个未定义符号 |

**关键**：`libjs_static.a`、`libjsrust.a`、28 个 donor 对象全都参与了链接，没有 OOM，没有替换错误。

## 缺口从「不知道」变成「知道」

```
ruyijs::interaction::Realm::Install / InstallWorkerDerived
ruyijs::execution_scheduling::Realm::~Realm
ruyijs::Pipe::ConnectAsync
ruyijs::CreatePage
ruyijs::Frames / TopLevel / BrowsingContext
ruyijs::DescribeException / EncodeReply
ruyijs::domain::styling::CssSetInitialFontFamily
```

这 20 个符号**分组后全部落在此前批次已验证过的层**：`interaction-v1`、`workers-v1`、`network-carrier-v1`、`styling-v1`。也就是说这一层已经有了，只是没接进产品链接。

## 一个我自己造成的错

编译出的 shell 对象原本躺在 `/tmp` 这个 tmpfs 里，容器退出就没了，导致第一次链接无对象可用。已改为保存到输出目录。

## 边界

**这不是一个能跑的产品 shell。** 20 个未定义符号意味着链接没有完成，`dist/js` 仍然不存在。

但下一轮的工作不再是探索——是**按清单把已验证的层接进来**。

回执 `deliverables/linux-ruyijs-product-link-r268/product-link-validation.json`。

## 缺口移动了，但没消失：0 未定义，20 重复

把 `interaction-v1` 批次的对象加进链接后：

| 阶段 | 结果 |
|---|---|
| 上一轮 | 20 个**未定义**符号 |
| 加入 `runtime-batch.o` | **0 未定义**，20 个**重复定义** |

**这说明那个批次对象确实补齐了所有缺口**，但它同时**带着 donor 的 `js::shell`**，而生成单元已经定义了这些。

## 组成是量出来的

`runtime-batch.o`：60,678,392 字节、7298 个定义、**143 个 `js::shell`**、**2131 个 `ruyijs::`**。

## 剥离行不通，而且是硬性失败

我试了 `objcopy` 移除 114 个 `js::shell` section，失败：

```
symbol `_ZN2js5shell19AutoReportExceptionD2Ev' required but not present
objcopy: no symbols
```

**原因是 donor shell 的符号互相调用，且被保留下来的 section 引用。**移除它们不是得到更小的对象，而是得到悬空引用。objcopy 直接拒绝写坏对象——这个行为是对的。

## 我这一轮走过的弯路

1. 先以为「批次对象能整体复用」→ 撞上 143 个重复定义
2. 再想「剥掉 donor 部分」→ section 名漏了前导点，第一次剥离没生效
3. 修正后仍有 143 个 → 发现剥离本身不可行

第 1 步的思路是错的：**那个合并对象方便，但携带了产品链接绝不能包含的单元**。

## 正确方向

把那一层**按单元对象构建**，而不是合并成一个 relocatable。这样 shell 单元自然不存在，不需要剥离。

## 边界

链接仍未完成，`dist/js` 不存在，产品 shell 跑不起来。

回执 `deliverables/linux-ruyijs-strip-r271/strip-validation.json`。

## 重复定义清了，剩下的是缺单元

上一轮我说「按单元对象构建」。这一轮发现**批次目录里本来就保留了 87 个独立单元对象**，直接拿来用即可。

| 项 | 上一轮 | 这一轮 |
|---|---|---|
| 重复定义 | 20 | **0** |
| 未定义符号 | 0 | 20 |
| 链接中的私有单元 | 1 个合并对象 | **87 个独立对象** |

**关键验证**：这 87 个单元里，`js::shell` 定义数 = **0**。所以冲突不是靠剥离解决的，而是根本不该用那个合并对象。

## 剩余的 20 个按层分组

| 层 | 符号数 |
|---|---|
| `BrowsingContext` | 4 |
| `resource_network` | 4 |
| `Frames` / `TopLevel` | 2 + 2 |
| `CreatePage` / `DescribeException` / `EncodeReply` | 各 1 |
| 其余 5 个单例 | 5 |

这些属于 **document 和 network 层**。它们的批次只保留了合并的可重定位对象（或仅 1 个对象），所以拿不到独立单元。

## 又一次同样的错误

`glob('*/*.o')` 匹配不到 `<domain>/<name>/<name>.o` 的三层结构，第一次跑报「no unit objects」。而且第一次的 glob 还把 `relocatable/` 里的合并对象一起捞了进来——**正是这次要避免的那个**。

两处都是想当然：以为层级是两层、以为排除条件不需要显式写。

## 边界

链接仍未完成，`dist/js` 不存在。

回执 `deliverables/linux-ruyijs-units-r274/units-validation.json`。

## 每解决一层，下面就还有一层

| 项 | 上一轮 | 这一轮 |
|---|---|---|
| 运行时单元 | 4 | **9** |
| 交互单元 | 87 | 87 |
| 重复定义 | 0 | 0 |
| 未定义符号 | 20 | **20（换了一批）** |

**关键：上一轮那 20 个符号已经全部解析**，现在报的 20 个是**更深一层的新集合**：

```
resource_network 4 · browser_environment 3 · document_model 2
CreatePage · DecodeTyped · DescribeException · Pipe::Read
ToUTF8 · UnbindUserActivation · domain · execution_scheduling
web_geometry · web_observers · web_security
```

## 这一轮能做到的

**新增 5 个单元全部编译成功**（1,736,144 字节）：`browsing_context`、`host_reply`、`protocol`、`environment_control`、`top_level`。

其中 `protocol.cpp` 依赖生成的 codec 头 `runtime_assets.h`，我为此加了 include 路径和空值保护，**编译路径现在适用于 `src/runtime` 下任意单元**。

## 这一轮的判断

这不是「还有 20 个」而是「又一层 20 个」。**每一层运行时代码会拉出下一层**，所以这不是一份固定清单，而是一条链。

诚实地说：这一轮在推进，但离 `dist/js` 还有若干层的距离，而且每层都还有各自的下一层。我在做的是**逐层逼近**，不是即将收尾。

## 边界

链接仍未完成，`dist/js` 不存在，产品 shell 跑不起来。

回执 `deliverables/linux-ruyijs-deeper-r276/deeper-validation.json`。

## runtime 目录整层关闭了

上一轮是「每解决一层还有一层」。这一轮换了做法：**不再猜哪些单元，直接把 `src/runtime` 全部 90 个单元一次编译**。

| 项 | 结果 |
|---|---|
| 总单元 | 90 |
| 编译成功 | **85** |
| 失败 | 5 |
| 重复定义 | **0** |
| 未定义符号 | 20 |

**那 5 个失败是预期行为**：它们是 Windows 的 pipe 单元，而 `product_sources` 早就声明 Linux 用 `pipe_linux.cpp` 替换它们——替换版编译成功了。

## 一个必须用对规则的细节

16 个单元用了 `try`/`throw`，而 donor 命令带 `-fno-exceptions`。产品里**已有** `needs_exceptions` 分类器，我直接调它，而不是另立一份清单。

如果我自己列清单，就会漏掉 `api_monitor` 这种通过 `domain/shared/entity.h` 间接用 `throw` 的单元。

## 缺口现在的分布

```
web_workers 6 · document_model 5 · web_broadcast 3 · web_styling 2
browser_environment 1 · resource_network 1 · web_platform 1 · web_security 1
```

**`src/runtime` 里已经一个都不缺了。** 剩下的是别的目录。

## 规模必须说清楚

私有树共 **1355 个单元**，这一轮覆盖 90 个。最大的剩余目录：`document_model` **248** 个、`resource_network` **177** 个。

按这个比例，把 1355 个全部编译并链接，是**几十轮的量级**，不是几步的事。

## 边界

链接仍未完成，`dist/js` 不存在。

回执 `deliverables/linux-ruyijs-allruntime-r280/allruntime-validation.json`。

## 整目录一次编译：document_model 248 个全过

上一轮确认了「整目录一次编译」可行，这一轮拿最大的目录验证。

| 项 | 值 |
|---|---|
| 单元数 | **248** |
| 编译成功 | **248** |
| 失败 | **0** |
| 耗时 | **943 秒** |

**吞吐量测出来了：每单元约 3.8 秒。**

按这个速率，全树 1355 个单元约需 **86 分钟**编译。这是**分几次有界批次**的量，不是一次能跑完的。

## document_model 的符号全部解析

上一轮那 5 个 `document_model::Realm::*` 符号**全部解析成功**，说明整目录编译是对的。

剩余 20 个现在集中在：

```
web_workers 6 · browser_environment 4 · resource_network 2
web_broadcast 2 · web_geometry 2 · web_styling 2 · web_platform 1 · web_security 1
```

## 这一轮没有新踩坑

编译一次通过，链接零重复。和第 140-143 轮反复撞墙相比，**说明前几轮把机制修对了**：异常分类器、生成头路径、对象前缀分离，现在都能稳定工作。

## 边界

链接仍未完成，`dist/js` 不存在。剩余约 1100 个单元待编译。

回执 `deliverables/linux-ruyijs-docmodel-r282/docmodel-validation.json`。

## 批量推进：一次 447 个单元

有了 3.8 秒/单元的吞吐数据，这一轮一次性把**符号所在的全部 8 个目录**（447 个单元）跑完。

| 项 | 值 |
|---|---|
| 单元总数 | 447 |
| 编译成功 | **420** |
| 失败 | 27 |
| 耗时 | **1553 秒** |

**累计已产出 764 个对象**，占全树 1355 个的 **56%**。

## 失败的 27 个分两类，没有一类是真正的代码缺陷

**一、预期替换项**：`necko_helper`、`necko_pipe`、`process`、`process_start`、`font_face_mac`、`canvas_text_path_linux`——`product_sources` 已声明 Linux 用别的单元替换它们。

**二、缺第三方头文件根**：HarfBuzz、FreeType、Fontconfig、Cairo、vendored brotli。这些是**路径问题，不是代码问题**。

补上 `-I` 后重跑 `web_geometry`：**24 个失败降到 11 个**，剩余 11 个的根因也已查明（FreeType/Cairo 头），路径已补。

## 这一轮的教训

我把「编译失败」和「代码有问题」在最初混在一起了。实际上 27 个失败里**没有一个需要改代码**，全是：
- 该被替换的 Windows 单元
- 没给对头文件路径

**先分类再动手**，比看到失败就改代码更省时间。

## 边界

链接仍未完成，`dist/js` 不存在。剩余约 590 个单元，另有 11 个几何单元待用新路径重跑。

回执 `deliverables/linux-ruyijs-rest-r284/rest-validation.json`。

## 第二轮批量：累计 891 个对象，占全树 66%

| 项 | 值 |
|---|---|
| 本轮单元 | 488 |
| 编译成功 | **460** |
| 失败 | 28 |
| 耗时 | **1436 秒** |
| **累计对象** | **891 / 1355（66%）** |

## 28 个失败分类

| 类别 | 数量 | 说明 |
|---|---|---|
| 预期 Linux 替换项 | **15** | `necko_*`、`worker_*`、`cng_backend`、`digest_backend` |
| 缺第三方头 | **11** | OpenSSL、libpng、Skia、Cairo |
| 其他 | **2** | 见下 |

## 一个有价值的发现：异常分类器看不见 include 链

`styling` 的 6 个单元报 `cannot use 'throw' with exceptions disabled`，但 `needs_exceptions` 判定它们不需要。

原因：`entity.h` 里的 `throw` 是**经 `stylesheet.h` → `aggregate_root.h` 间接引入**的，而分类器只查源文件本身。

**我的修法是让编译器当判据**：如果日志里出现这句，就加 `-fexceptions` 重试一次。这比再写一份清单可靠——编译器知道真实情况，清单不会。

## 边界

链接仍未完成，`dist/js` 不存在。剩余 464 个单元 + 若干头文件根待补。

回执 `deliverables/linux-ruyijs-bulk2-r285/bulk2-validation.json`。

## 异常重试生效了，剩余失败有了明确归属

| 项 | 上一轮 | 这一轮 |
|---|---|---|
| 本轮通过 | 460 | **468** |
| 失败 | 28 | **20** |
| 全树对象 | 891 | **1242** |

**`styling` 那 6 个单元解决了**：用编译器消息当判据、失败后加 `-fexceptions` 重试，是对的做法。

## 剩余 20 个的归属

| 类别 | 数量 | 性质 |
|---|---|---|
| `transport` 层 | **14** | Windows 专用，Linux 无对应实现 |
| `web_crypto` 的 `cng`/`digest` | 2 | Windows 专用后端 |
| 头文件路径还差一层 | 4 | OpenSSL、Skia、libpng |

## `transport` 这个发现值得单独说

`src/transport` 有 17 个单元，其中 5 个直接包含 `windows.h`，其余经头文件间接引入。

而 `resource_network` 有 `necko_linux.cpp` 作为 Linux 对应实现，**`transport` 目录里没有**。

**结论：`transport` 是 Windows 层，Linux 对应实现不在树里。** 那 14 个失败是**范围事实，不是缺陷**。

这个区分很重要：如果我把它当成“要修的 bug”，就会去改那些 Windows 专有代码——那是错的。

## 边界

链接仍未完成，`dist/js` 不存在。剩余是 4 个头文件路径细节 + 16 个不该在 Linux 编译的单元。

回执 `deliverables/linux-ruyijs-bulk3-r286/bulk3-validation.json`。

## 未定义符号归零了

用宿主机上全部累积对象（1179 个参与链接）做了一次完整链接：

| 项 | 值 |
|---|---|
| 链接的私有对象 | **1179** |
| **未定义符号** | **0** |
| 重复定义 | 20 |

**这是第一次未定义符号归零。**产品 shell 需要的每一个私有符号，现在都由某个已编译对象提供。

## 剩下的是记账问题，不是缺代码

20 个重复来自两处，都已查明：

**一、`web_styling` 用 `#include` 聚合了 52 个 `domain/styling` 实现**——那些单元单独编译就会把同一批符号定义两遍。已加规则：被别的单元 `#include` 的单元跳过。

**二、跨批次重叠**——`web_messaging` 在旧批次和本轮都有，旧对象与新对象冲突。已加规则：新一轮已有同名单元则不加入旧对象。

## 这个里程碑的性质

**缺口性质变了**：不再是「缺代码」「缺头文件」，而是「哪个对象供应哪个单元」的记账问题。

这类问题可以机械解决，不需要新的分析。

## 边界

链接仍未完成（20 个重复），`dist/js` 不存在，产品 shell 跑不起来。

回执 `deliverables/linux-ruyijs-linkall-r289/linkall-validation.json`。

## 一个二选一的困境，和一个我自己造成的错误

上一轮未定义归零但剩 20 个重复。这一轮想去掉重复，结果发现了真实约束：

| 状态 | 未定义 | 重复 |
|---|---|---|
| 全部旧对象都加入 | 0 | 20 |
| 按单元名跳过旧对象 | **20** | 0 |

**跳过是错的。** 因为同名的新编译对象**可能定义更少的符号**——跳过 `realm.o` 直接丢掉了整个 `interaction::Realm`。

**根因**：这个重叠不是「同一份代码编译两次」，而是**批次的单元和树里的单元同名但内容不同**。

## 决定：不猜哪份完整，两份都留

改用 `-Wl,--allow-multiple-definition`：所有定义都可用，由链接器选一个。这比「猜哪份更完整」可靠。

## 我这一轮错了两处

1. **`Path(o).stem` 包了一层 `Path`**，导致集合里存的是 `PosixPath` 对象，永远不等于字符串，去重从未生效
2. **改对后又跳过了必需的符号**，直接把未定义从 0 变成 20

两次都是「以为逻辑对，没验证实际值」。第 1 个错误跑了三次链接才发现。

## 边界

链接仍未完成，`dist/js` 不存在。

回执 `deliverables/linux-ruyijs-link-tradeoff-r292/tradeoff-validation.json`。

## 重复定义清零，暴露了真正的缺口

| 项 | 上一轮 | 这一轮 |
|---|---|---|
| 重复定义 | 20 | **0** |
| 未定义符号 | 0 | 20（**换了新的一批**） |
| 旧批次对象 | 按名跳过 | **87 个全部加入** |

重叠问题解决了。新的 20 个未定义**全部来自之前编译失败的单元**：

| 来源 | 数量 |
|---|---|
| `web_crypto`（AesCbc、EcdsaSign 等） | 9 |
| `web_canvas::skia`（ClearRect、DrawImage 等） | 8 |
| `web_geometry::LocalFontFamilyInstalled` | 1 |
| `getentropy`、`hb_set_get_empty` | 2 |

**为什么现在才出现**：重复没解决时，链接器先报重复就停了，不会走到列举未定义那一步。

## 我这一轮又错了两处

1. **把标志加进了 `relink_control`**——那是 donor 控制链接，必须保持原样；产品链接根本没看到这个标志
2. **加了标志却没撤掉按名跳过**——结果又丢了只有旧对象才有的符号

第 1 个错误很典型：两个函数都在同一个文件、都构造链接命令，我没确认**哪个函数真的被调用**就改了。

## 边界

链接仍未完成，`dist/js` 不存在。但这 20 个缺口的来源已经明确：**编译那些头文件根刚补好的单元**。

回执 `deliverables/linux-ruyijs-dupfix-r295/dupfix-validation.json`。

## 加密和画布单元编译出来了

上一轮那 20 个未定义的来源，这一轮解决了主要部分：

| 项 | 结果 |
|---|---|
| `web_crypto` 通过 | **140** |
| `web_geometry` 重跑通过 | **61** |
| **`openssl_backend.o`** | **360,480 字节** ← 供给了 9 个 crypto 符号 |
| **`glyph_mask_linux.o`** | 已产出 |

`geometry` 失败从 13 降到 6（挂上 FreeType 头之后）。

## 剩余 6 个的性质

| 单元 | 性质 |
|---|---|
| `font_face_mac` | **macOS**，要 CoreText |
| `font_aliases` | **Windows**，用 IDWriteFontCollection 和 HKEY |
| `font_collection` | **Windows** 实现，已被 `font_collection_linux` 替换 |
| `glyph_mask` | **Windows** 实现，已被 `glyph_mask_linux` 替换 |
| `svg_path` | 缺 `cairo/cairo.h`，**include 根已修正待重跑** |
| `font_shape_linux` | 原因未查 |

**四个是别的平台的单元**，Linux 上本就不该编译。真正待办的只有 `svg_path`（路径已修）和 `font_shape_linux`（原因未知）。

## 边界

链接仍未完成，`dist/js` 不存在。

回执 `deliverables/linux-ruyijs-crypto-geo-r298/cryptogeo-validation.json`。

## `font_shape_linux` 解决了，`svg_path` 推进一层

| 项 | 上一轮 | 这一轮 |
|---|---|---|
| geometry 通过 | 61 | **62** |
| 失败 | 6 | **5** |

**上一轮「原因未知」的 `font_shape_linux` 现在通过了**：它缺 `fribidi.h`，而那个头在 **`fontshape-r99`** 的 staged 树里，不在 `fontmetrics-r97` 那份（只有 fontconfig 和 freetype2）。

## 剩余 5 个

| 单元 | 性质 |
|---|---|
| `font_aliases` / `font_collection` / `glyph_mask` | **Windows** 实现 |
| `font_face_mac` | **macOS** 实现 |
| `svg_path` | 越过了 Cairo，现在缺 `prcpucfg.h` |

**4 个是别的平台**，Linux 上不该编译。真正待办只剩 `svg_path`。

## 两个路径教训

1. **staged 树的批次不同内容也不同**——`fontmetrics` 只暂了 fontconfig+freetype2，`fontshape` 才有 fribidi+harfbuzz
2. **符号链接活不过 bind mount**——`/tmp/cairoinc/cairo` 指向宿主机绝对路径，容器内看不见。改成复制真实目录才行

## 边界

链接仍未完成，`dist/js` 不存在。

回执 `deliverables/linux-ruyijs-geo-r302/geo-validation.json`。

## `svg_path` 编译出来了，`web_geometry` 移植完成

| 项 | 上一轮 | 这一轮 |
|---|---|---|
| geometry 通过 | 62 | **63** |
| 失败 | 5 | **4** |
| `svg_path.o` | 无 | **89,976 字节** |

剩余 4 个全是其他平台的单元：`font_aliases`、`font_collection`、`glyph_mask` 是 Windows，`font_face_mac` 是 macOS。

**`web_geometry` 里没有待移植的单元了。**

## `svg_path` 花了三轮头文件

1. `cairo/cairo.h`：得让 include 根持有**真实的 `cairo/` 目录**
2. `prcpucfg.h`：在 `config/external/nspr`
3. `md/_linux.cfg`：在 `nsprpub/pr/include`

每次修好一个就冒出下一个。这三个是**真实的依赖链**，不是我在原地打转——错误信息每次都变了。

## 一个质变的信号

链接的 20 个未定义符号**不再来自项目代码**：

| 来源 | 数量 |
|---|---|
| `hb_*`（HarfBuzz 入口） | **19** |
| `getentropy`（libc） | 1 |

**没有一个 `ruyijs::` 符号缺失了。**这意味着下一步是**链接 `libharfbuzz.so.0`**，属于共享库输入问题，不再是编译问题。

## 边界

链接仍未完成，`dist/js` 不存在。

回执 `deliverables/linux-ruyijs-svg-r305/svg-validation.json`。

## HarfBuzz 解决了，只剩 6 个符号

把 `libharfbuzz.so.0` 加进链接后：

| 项 | 上一轮 | 这一轮 |
|---|---|---|
| 未定义符号 | 20 | **6** |
| 重复定义 | 0 | 0 |

**19 个 HarfBuzz 入口全部消失。**

## 剩余 6 个的性质

| 符号 | 来源 |
|---|---|
| `RUYIJS_CS_Z_deflateInit2_` / `deflateEnd` / `inflate` / `inflateEnd` / `inflateInit2_` | 产品**自己重命名的 zlib** |
| `getentropy` | libc（glibc 2.39 有） |

**没有一个 `ruyijs::` 项目符号缺失。**

## 为什么有重命名

`src/web_platform/compression_zlib.cpp` 用 `RUYIJS_CS_Z_` 前缀声明 zlib 入口，避免与系统 zlib 符号冲突。**定义必须来自同样带前缀的 zlib**。

现有 `libz.so.1` 是标准符号名，对不上。需要：
- 用该前缀构建的 zlib，或
- 一个把标准名别名过去的小对象

`getentropy` 在 glibc 2.39 里存在，链接时加 `-lc` 即可（当前显式列了库列表，可能漏了它）。

## 边界

链接仍未完成，`dist/js` 不存在。

回执 `deliverables/linux-ruyijs-hb-r306/hb-validation.json`。

## 上一轮判断错了：工具链一直在

上一轮我写下「没有 Rust 工具链」。**这是错的。**

`rustc` 和 `cargo` 就在**编译镜像里**：`/opt/ruyijs-rust/bin/`。它们不在宿主机 PATH 里，但不需要安装。

## zlib-rs 构建成功，前缀 56 个符号

照 `tools/compression_native.py` 的方式，用**两次 rustc 调用**（不用 cargo）：

| 步骤 | 结果 |
|---|---|
| `zlib-rs` → rlib | **OK** |
| `libz-rs-sys` → rlib（`--extern` 接上一步） | **OK** |
| 归档 `libruyijs_cs_zlib.a` | **3,766,804 字节** |
| **`RUYIJS_CS_Z_` 定义** | **56 个** |

## 为什么 cargo 不行

`cargo build --offline` 报 `no matching package named libc`——**依赖没有 vendored**。产品脚本因此直接用 `rustc` 加 `--extern`，绕开解析。

## 一个差点误导我的现象

对外层归档运行 `llvm-nm`，前缀符号计数是 **0**。差点当成失败。

**原因是 Rust 的 rlib 是嵌套归档**——外层只能看到 rlib 成员，看不到其中目标文件的符号。解包后 10 个目标文件里有 56 个前缀定义。

## 边界

链接仍未完成，`dist/js` 不存在。下一步把 `libruyijs_cs_zlib.a` 交给产品链接。

回执 `deliverables/linux-ruyijs-zlibrs-r311/zlibrs-build-validation.json`。

## zlib 解决了，缺的是 Skia

把 `libruyijs_cs_zlib.a` 加入链接后：

| 项 | 结果 |
|---|---|
| `RUYIJS_CS_Z_*` | **全部解决** |
| HarfBuzz | 保持解决 |
| 重复定义 | 0 |
| 未定义 | 20（**新的一批**） |

## 新的 20 个分两类

| 类别 | 数量 | 性质 |
|---|---|---|
| **Skia**（`SkCanvas`、`SkPaint`…） | **18** | **真实缺口** |
| `getentropy` / `hb_set_get_empty` | 2 | **只是接线** |

后两个我用 `nm -D` 验证过：`hb_set_get_empty` 在 staged 的 libharfbuzz 里，`getentropy` 在镜像的 glibc 2.39 里——**它们有提供者**。

## Skia 为什么是真实缺口

donor 的 objdir 是 **JS-only standalone 构建，没有任何 gfx 目标文件**。宿主机上不存在 Skia 归档。

要过这一关，得**构建或暂存 Skia 本身**——这比前面补头文件路径的工作量大一个数量级。

## 边界

链接仍未完成，`dist/js` 不存在。18 个 Skia 符号是当前唯一的真实阻塞。

回执 `deliverables/linux-ruyijs-zlink-r312/zlink-validation.json`。

## Skia 真能编译：232 个单元通过

上一轮说 Skia 是大工程。这一轮先做**单文件验证**——一个 `SkGraphics.cpp` 加上 donor 的 Mozilla 头就编译通过了。这改变了判断：可以试全量。

| 项 | 结果 |
|---|---|
| 编译范围 | `src/core` + `src/ports` + `src/opts`（249 文件） |
| **通过** | **232** |
| 失败 | 17 |
| 耗时 | 312 秒 |
| 产物 | 8.8 MB |

## 17 个失败分三类

| 类别 | 数量 | 说明 |
|---|---|---|
| 其他平台 | **10** | Android、Fuchsia、NDK、CG、WIC、fontations |
| **缺头文件** | **5** | `SkMemory_mozalloc`、`SkFontHost_FreeType`、`SkFontMgr_fontconfig`、`SkFontHost_cairo` 等 |
| 其他 | 2 | — |

**关键的那 5 个只是缺头**：`prenv.h` 在 `nsprpub/pr/include`，`ft2build.h` 和 `fontconfig.h` 在 staged 的 font-include 树里。**三个根已补上**。

## 方法上的收获

上一轮我凭“249 个文件”就判断这是大工程、没敢试。这一轮**先编译一个文件**，15 秒就证明路径可行。

**先做最小验证，再谈规模**——这比凭文件数估算可靠。

## 边界

链接仍未完成，`dist/js` 不存在。Skia 对象还没接进链接。

回执 `deliverables/linux-ruyijs-skia-r313/skia-validation.json`。

## 239 个 Skia 对象进链接，缺口从 18 变 16

| 项 | 值 |
|---|---|
| 编译的 Skia 对象 | **239** |
| 链接前未定义 | 18 |
| 链接后未定义 | **16** |

**缺口移动了，不是消失了。**这 16 个来自 `src/effects`（40 文件）和 `src/image`（15 文件），不在我编译的 core/ports/opts 里。

## 这一轮清掉的

- 7 个缺头文件的 Skia 单元里 **6 个通过**（`SkFontHost_FreeType`、`SkFontMgr_fontconfig`、`SkFontHost_cairo`、`SkFontConfigInterface_direct` 及 `_factory`）
- `SkMemory_mozalloc` 在补了 `config/external/nspr` 后也通过

## 一个反复出现的模式

`prcpucfg.h` 这次是从 **`prtypes.h`** 引出来的——同一类修复我在 `svg_path` 上做过一次。

**这说明缺的不是某个特殊头，而是一组标准 include 根**：NSPR、FreeType、Fontconfig、Skia、Cairo。它们应该一开始就都在。

## 边界

链接仍未完成，`dist/js` 不存在。剩 16 个 Skia 符号 + 2 个接线符号。

回执 `deliverables/linux-ruyijs-skia-link-r316/skialink-validation.json`。

## Skia 覆盖到 322 个对象，零编译失败

| 目录 | 结果 |
|---|---|
| core / ports / opts（前一轮） | 239 |
| effects / image | 已编译 |
| **shaders / codec** | **零失败** |
| **累计对象** | **322** |

**这一轮清掉的符号**：`SkImage::*`、`SkImageFilters::Blur`、`SkDashPathEffect::Make`、`SkSurfaces::Raster/WrapPixels`——全部解决。

## 剩 3 个 Skia 符号，和一个我没解开的矛盾

```
SkShaders::LinearGradient
SkShaders::SweepGradient
SkShaders::TwoPointConicalGradient
```

**矛盾点**：`nm` 显示 `sk_SkLinearGradient.o` **明确定义了** `SkShaders::LinearGradient`，链接也报了 `adding 300 skia`，但链接日志里**找不到这个对象路径**。

我列了三种可能（日志截断、符号 visibility、对象在链接开始后才构建），但**都还没验证**。这一轮跑了很多次容器，不再靠猜继续试。

**下一步应该读真实的链接 argv**，而不是日志片段——这是唯一能定论的做法。

## 边界

链接仍未完成，`dist/js` 不存在。

回执 `deliverables/linux-ruyijs-skia300-r320/skia300-validation.json`。

## 一个计数错误：不是 20 个，是 5 个

前几轮我一直报「20 个未定义符号」。这轮读 argv 时发现：**那是 grep 计数的行数，不是唯一符号名**。

真实缺口是 **5 个**：

```
getentropy · getrandom
hb_set_get_empty · hb_unicode_combining_class · hb_unicode_funcs_get_default
```

这个错误让缺口看起来比实际大三倍，也影响了我对进度的判断。

## SkShaders 的谜团解开了

上一轮那个「对象定义了但链接说没有」的矛盾：**是快照时机问题**。`shaders` 目录编译完后这一轮就消失了。

写下 argv（63KB）这件事本身有价值——它证明 322 个 Skia 对象**全部在链接命令里**，排除了「对象没进去」这个猜测。

## 这一轮试了四种修法，都没成

1. 记录 argv → 证明对象都在
2. 加 `-lc` → 被文件存在检查拦下（`-lc` 不是路径）
3. 修那个检查 → 通过了
4. 加 `--no-as-needed` → 无效

**5 个符号仍在。它们都是动态库导出过的符号**，所以问题在静态对象如何绑定带版本的共享符号——`getrandom` 是弱符号，这点尤其棘手。

**我停在这里，不试第五种猜测。** 下一次应该完整读链接器对这 5 个名字的输出，而不是截断的摘要。

## 边界

链接仍未完成，`dist/js` 不存在。

回执 `deliverables/linux-ruyijs-final4-r323/final4-validation.json`。

## 找到根因了：符号可见性，不是库

前几轮我试了加 `-lc`、`--no-as-needed`、换真实 harfbuzz 文件。都无效。

这一轮完整读链接器输出的第一行，看到关键词：**`undefined hidden symbol`**。

| 检查 | 结果 |
|---|---|
| 我编译的对象 | `GLOBAL HIDDEN UND getentropy` |
| donor 的对象 | 无 `GLOBAL HIDDEN UND` |

## 为什么是 hidden

donor 的编译命令带 `-include config/gcc_hidden.h`，而那个头**只有一行**：

```c
#pragma GCC visibility push(hidden)
```

**没有 pop。**所以整个翻译单元里所有声明——**包括系统头里的**——都是 hidden。

**hidden 的未定义引用永远不能被共享库解析**。这就是为什么库明明在、符号明明有，就是绑不上。

## donor 为什么没踩到

donor 的对象里**没有任何 `GLOBAL HIDDEN UND`**——Mozilla 通过 wrapper 访问 C 库，不直接调，所以那个配方从没产出这种形态。

而 Linux 移植版**直接调用系统函数**，就必须说明这些入口点的可见性。

## 修复后验证

```
GLOBAL DEFAULT UND getentropy
```

可见性变了，符号可以绑定了。

## 这条教训

我前几轮在**库层面**找原因（有没有链接、顺序对不对、要不要 as-needed），而问题在**符号层面**。

**`undefined hidden symbol` 和 `undefined symbol` 是两回事**，我读日志时把后者当成了前者。

## 边界

链接仍未完成。canvas 和 font 单元里的 harfbuzz 引用可能需要同样处理。

回执 `deliverables/linux-ruyijs-visibility-r324/visibility-validation.json`。

## 从 5 个降到 4 个，两个都是新一类问题

| 项 | 结果 |
|---|---|
| `hb_set_get_empty` | **已解决** |
| 上一轮 5 个里的 4 个 | **已解决** |
| 剩余 | **4 个**（`getrandom` + 3 个 styling） |

## 两个修复的关键点

**一、harfbuzz 自己的依赖**

测试发现 libharfbuzz 需要 `libfreetype`、`libglib`、`libgraphite2`。缺 `-rpath-link` 时，链接器报的是**从 harfbuzz 内部冒出来的** `undefined reference to 'gr_face_destroy'`。

加 `-Wl,-rpath-link,/harfbuzz -Wl,--allow-shlib-undefined` 解决。

**二、`hb_set_get_empty` 本该是 stub 自己的对象**

`skia_subset_stubs.cpp` 是产品为「无 subsetter 的 HarfBuzz」写的替代实现，但它**把 `hb_set_get_empty` 声明成外部符号**，等于去问一个不提供它的库要。

改成 stub 自己拥有一个空集就对了。

## 剩余的 4 个

| 符号 | 性质 |
|---|---|
| `getrandom` | **仍 hidden**——保护头文件不够，后面有系统头重新声明了它 |
| `CssColorSpaceToSrgb` 等 3 个 | **项目符号**，但所在单元被我「跳过被包含单元」的规则跳过了 |

第 2 类是我自己规则造成的副作用，需要调整而不是新增编译。

## 边界

链接仍未完成，`dist/js` 不存在。

回执 `deliverables/linux-ruyijs-link2-r327/link2-validation.json`。

## 三个 styling 符号：查清了定义，但没解决编译

## 已经确认的

| 事实 | 结果 |
|---|---|
| 符号定义位置 | `css_color_space.cpp` 第 164 行起 |
| `css_color_resolve.cpp` | 只是**调用**，定义不在那里 |
| 它被包含吗 | 是，被 `model_css_rules.cpp` 包含，所以跳过规则**正确** |
| `css_color_space.cpp` 被包含吗 | **没有**，跳过规则不该作用于它 |

## 没解决的

两次编译都没有产出任何 `domain/styling` 对象，**失败列表却是空的**；这说明循环什么都没做，而不是失败了。

最后一次探针没能打印输出，容器内的路径**仍未确认**。

## 排除掉的

符号是**项目符号**，不是库入口；定义单元是普通的无条件编译的 `.cpp`；没有任何 hidden 或版本化因素。

## 下一步

从容器内部确认挂载解析正常、`find` 能看到该文件，然后**按名字单独编译那一个单元**；这比修循环更直接。

## 边界

链接仍未完成，`dist/js` 不存在。剩余 4 个符号。

回执 `deliverables/linux-ruyijs-styling-r329/styling-validation.json`。

## 三个 styling 符号清掉了，`getrandom` 也清了

| 项 | 结果 |
|---|---|
| `domain::styling` 三个符号 | **已解决** |
| `getrandom` | **已解决** |
| 剩余 | **11 个**（10 个 `_moz_cairo_*` + `hb_set_get_empty`） |

## 上一轮"编译了但没产出"的真相

不是被跳过，也不是失败——**产出的是空对象**。

| 编译方式 | 对象大小 | 符号数 |
|---|---|---|
| 批次的完整 include 集 | 28,488 | **0** |
| 最小 include 集 | 28,488 | **137** |

**同样大小，符号数却是 0 对 137。**某个额外的 include 根改变了编译结果，但没有报错。

这是最难查的一类：**成功退出、大小正常、内容为空**。

## 本轮修复

直接按最小 include 集单独编译 `css_color_space.cpp`，把它放进输出目录。

## 新的缺口

10 个 `_moz_cairo_*`——它们是 **Cairo 函数的重命名**（`cairo-rename.h`），不是缺失的第三方库。

只需编译 vendored 的 155 个 Cairo 翻译单元，让重命名头生效。

## 边界

链接仍未完成，`dist/js` 不存在。

回执 `deliverables/linux-ruyijs-styling2-r330/styling2-validation.json`。

## Cairo 编进来了，只剩 1 个符号

| 项 | 结果 |
|---|---|
| Cairo 单元 | 155 个，**120 个通过** |
| 耗时 | **25 秒** |
| `_moz_cairo_*` 定义 | **284 个** |
| 之前缺的 10 个 | **全部覆盖** |
| 剩余未定义 | **1 个** |

失败的 35 个是 xlib、xcb、quartz、pdf、svg、png 和测试合成器——**Linux 上的 canvas 一个都不需要**。

## 一个关键细节

`cairo-rename.h` 是一组 `#define`，**必须强制包含**。不包含的话，编译出的对象只带无前缀的原始名，链接器就找不到 `_moz_cairo_*`。

## 最后那个符号：修复没生效是因为对象是旧的

`hb_set_get_empty` 我在两轮前就修好了源码——让 stub 自己拥有空集。

但**输出目录里的对象是修复前编译的**。链接器读的是对象，不是源码。

重新编译后，`hb_set_get_empty` 有了 1 个定义。

**教训：改完源码不等于修复生效，得重新编译。**

## 边界

链接仍未完成（需要重链接），`dist/js` 不存在。

回执 `deliverables/linux-ruyijs-cairolink-r335/cairolink-validation.json`。

## 未定义的**性质**变了

这一轮最重要的不是数量，是**符号类型**：

| 之前 | 现在 |
|---|---|
| `undefined **hidden** symbol` | `undefined symbol` |

**可见性问题结束了。**现在的未定义是普通符号，意味着缺的是**对象本身**，不是绑定方式。

## 清掉的

**OpenSSL 的 20 个符号**——加 `libcrypto.so.3` 后全部解决。

## 剩余的 14 个分两组

| 组 | 数量 | 原因 |
|---|---|---|
| Skia `src/base` | 4 | `SkArenaAlloc`、`SkDebugf`、`SkBezierCubic/Quad` 在这个目录，之前没编译过 |
| pixman | 10 | **Cairo 的图像后端靠 pixman 合成**，而 pixman 从没编译过 |

`src/base` 已编译，**零失败**。

pixman 第一次编译 40 个失败，因为它要求 Mozilla 头文件（`pixman-private.h` 直接 `#error`）。头文件已补。

## 边界

链接仍未完成，`dist/js` 不存在。

回执 `deliverables/linux-ruyijs-ossl-r337/ossl-validation.json`。

## Seed 关系（重要）## Seed 关系（重要）

`ruyijs-inner` 的 seed 是 `ff-ruyijs` **0.2.1**（`c69875b5`），不是当前的 0.4.1（`3501a90`）。

**0.2.1 没有跨平台代码**——`python/ruyijs/_pipe.py` 仍是 Windows 独占的 127 行。0.4.1 的 AF_UNIX 分支（208 行）是后出现的能力，只能作可行性证据，不能作内部版现状依据。

## 与其他项目的关系

- 与 **RuyiHttp** 共享 31 个 C 符号的 necko ABI（见 `docs/01-architecture.md` §1.2）
- 与 **RuyiTrace** 构成 trace 对账闭环：`trace_diff.py` 比对两者行为差异
- 与 [ruyi-mcp](../../docs/01-architecture.md#5-ruyi-mcp-控制面与组件边界) 的关系是浏览器行为对照。
