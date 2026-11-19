# 构建主机与运行时来源（2026-11-19）

> **本文经过更正。** 初版写成「需要在服务器上编 SpiderMonkey」，那是多余的一步——
> Linux 版运行时在 ff-ruyijs v0.4.1 的 wheel 里已经有构建好的产物。

## 一、先看现成的

### ff-ruyijs 的 release 资产

`cutetailbud/ff-ruyijs` 每个版本都发布三平台 wheel：

| 版本 | win_amd64 | macosx_26_0_arm64 | **manylinux_2_39_x86_64** |
| --- | --- | --- | --- |
| v0.4.1 | ✓ | ✓ | ✓ |
| v0.4.0 | ✓ | ✓ | ✓ |
| v0.3.7 | ✓ | ✓ | ✓ |

`runtime.json` 只给了 Windows 与 macOS 的 runtime 压缩包，**没有 linux 段**——
但这不代表没有 linux 产物，而是 linux 版**只以 wheel 形式发布**（运行时内嵌在 wheel 里）。

### linux wheel 里到底有什么

实测 `ruyijs-0.4.1-py3-none-manylinux_2_39_x86_64.whl`（73,961,754 B，
sha256 `f80de6b2…908d37`，与 `ruyihttp/native/linux_x86_64/provenance.json`
记录的 wheel hash 一致）：

```
66,272,193  ruyijs/_runtime/dist/js                    ← SpiderMonkey 壳
    35,033  ruyijs/_runtime/dist/libruyijs_client.so
     2,283  ruyijs/_runtime/dist/ruyijs.h
   321,934  ruyijs/_runtime/runtime.json
            ruyijs/_runtime/lib/*.so  （26 个依赖库，见下）
```

**构建产物是完整的**，不需要自己编。

### linux 运行时配置（`_runtime/runtime.json`）

| 项 | 值 |
| --- | --- |
| `platform` | `linux_x86_64` |
| `engine` | **SpiderMonkey 160** |
| `transport` | standalone-necko+nss |
| `webcrypto` | **OpenSSL** |
| `graphics` | Firefox 160 Skia 149 raster |
| `build_glibc` | **glibc 2.39** |

26 个依赖库：`libcrypto.so.3` `libssl.so.3` `libpython3.14.so.1.0` `libharfbuzz.so.0`
`libfreetype.so.6` `libzstd.so.1` `libwebp.so.7` `libpcre2-8.so.0` 等。

## 二、与 Windows 内部版的关键差异

| 维度 | Windows 内部版 | Linux 官方 wheel |
| --- | --- | --- |
| JS 引擎 | SpiderMonkey **159**（Firefox 159 `9a2dc53c`） | SpiderMonkey **160** |
| WebCrypto | NSS | **OpenSSL** |
| 图形 | Skia（Firefox 159） | Skia 149（Firefox 160） |
| glibc | 不适用 | **2.39** |
| neqo | 0.32/0.33 | 见 `runtime.json` |

**这不是同一套构建。** 内部版的 `js.exe` 基于 159，官方 linux wheel 是 160。

含义：**Linux 侧用官方 wheel 能立刻跑起来，但与内部版不是同一个引擎版本**。
要做「与内部版一致的 Linux 版」，最终仍需按内部版的 pin 重建。

## 三、因此的正确顺序

| 步骤 | 用途 | 需要什么 |
| --- | --- | --- |
| **1. 用官方 linux wheel 跑通** | 验证链路、拿行为基线 | 只需一台 glibc ≥ 2.39 的 x86_64 主机 |
| 2. 对齐到内部版 pin | 与 Windows 内部版行为一致 | 需按内部版的 Firefox commit 重建 |
| 3. `ruyihttp` 的 `linux_aarch64` | 补 build-required 空位 | aarch64 主机 |

**第 1 步不需要编译任何东西。** 这是本轮最大的认知更正。

## 四、现有 fleet 的能力（实测）

| 主机 | 架构 | 发行版 | glibc | CPU | 内存可用 | 磁盘可用 | 能做什么 |
| --- | --- | --- | --- | ---: | ---: | ---: | --- |
| `oracle-dsh` | aarch64 | 22.04 | 2.35 | 1 核 | 5 G | 9.8 G | 本机；glibc 不足 |
| `oracle-proxy` | aarch64 | 20.04 | 2.31 | 1 核 | 11 G | 20 G | 架构不符 |
| `oracle-gateway` | **x86_64** | 20.04 | 2.31 | 2 核 | **563 M** | 34 G | 架构对但内存不足、glibc 过低 |
| `oracle-mail` | aarch64 | 8.10 | 2.28 | 1 核 | 5 G | 15 G | 架构不符 |
| `oracle-artex` | aarch64 | 24.04 | 2.39 | 2 核 | 11 G | 18 G | glibc 够，架构不符 |
| `oracle-reverse-dev` | aarch64 | 24.04 | 2.39 | 2 核 | 10 G | 73 G | glibc 够 + 盘大，架构不符 |

**结论**：现有 fleet 里**没有一台是 x86_64 且 glibc ≥ 2.39**。
官方 linux wheel 要跑起来，需要一台新的 x86_64 实例（或 grok-bot）。

## 五、需要外部构建时该产出什么

如果要在 grok-bot 或其他 x86_64 环境构建，最有价值的产出**不是**重新编 SpiderMonkey
（官方已有），而是：

| 产出 | 为什么有价值 |
| --- | --- |
| **按内部版 pin 构建的 linux `js`** | 官方 wheel 是 SP160，内部版是 SP159，要对齐只能重建 |
| `ruyihttp` 的 `linux_x86_64` 原生库重编（可选） | 现有的来自 ruyijs 0.4.1，已验证 hash |
| `ruyihttp` 的 `linux_aarch64` 原生库 | 这是真正的 build-required 空位 |

第 1 项与第 3 项才是现有资产里缺的。第 2 项已经有且验证过。

## 六、本仓不做的事

| 不做 | 理由 |
| --- | --- |
| 在 fleet 里找机器编 SpiderMonkey | 官方已有 linux 构建，重复劳动 |
| 在 `oracle-gateway` 上构建 | 952 MB 内存，必然 OOM |
| 交叉编译到 Windows | 官方有 win wheel，且内部版已有 `js.exe` |
| 用 swap 硬扛 2 核构建 | 会把小时级变成天级 |
