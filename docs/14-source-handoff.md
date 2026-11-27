# 其他项目如何使用 Ruyi Platform

**先区分平台开发 pin、发布工件和主机在用版本。** [PINS](../PINS.md) 与 [STATUS](../STATUS.yaml) 记录五个一级组件的开发固定提交；复现 amd64 无头 R5 的冻结输入仍用独立标签，Trace 的原生事件 Beta 与 Electron owner Alpha 各有交付标签，RuyiDOM 则单独检出。

## 选择交付物

| 需求 | 使用什么 | 已有证据与边界 |
| --- | --- | --- |
| 自有页面的浏览器采集 | Trace amd64 **R5 无头运行时** | 原生完整构建、Rust 归档审计、打包、镜像保存后本机重新加载并运行两档 QA；覆盖 DOM、click、脱敏 Storage、双会话及显式 script-error 档。它不是 Electron、MCP 服务或任意 producer 的保证。 |
| Linux 命令行采集 | [独立 CLI](../submodules/ruyitrace/console/cli/README.md) + 对应架构内核 | [amd64 R5 CLI 原件](../artifacts/receipts/trace-amd64-r5/cli-native-amd64.json)和 [ARM64 R5 CLI2 正式发行](../artifacts/receipts/trace-arm64-native-lease/README.md)分开验收；ARM64 稳定站点使用 site2、回退 site1；浏览器和桌面按需运行，见[站点手册](../submodules/ruyitrace/product/arm64/site/README.md)。 |
| Wasm、JSCall、HTTP、WebSocket 原生事件 | [Trace 原生事件 Beta 1](https://github.com/Facetomyself/ruyitrace/releases/tag/native-events-v0.2.0-beta.1)，独立非默认交付 | 双架构各 22 案，限对应工件和受控合成回环页面；[双架构原始审核](../artifacts/receipts/trace-linux-gap-closure-v1/patched-websocket/two-architecture-review.json) · [发布下载读回](../artifacts/receipts/trace-linux-gap-closure-v1/patched-websocket/beta-published.json)。 |
| Electron 桌面配置、预览或持有会话 | [Electron owner Alpha 1](https://github.com/Facetomyself/ruyitrace/releases/tag/linux-electron-owner-v0.1.0-alpha.1) + 对应架构内核 | [每架构五项持有者生命周期](../artifacts/receipts/trace-linux-gap-closure-v1/electron-owner/README.md)和[原启动器复跑](../projects/ruyi-mcp/LIVE-MATRIX.md#独立-electron-发行线)均使用虚拟席位；[实体显示与本地人工 IME](../artifacts/receipts/trace-linux-gap-closure-v1/desktop-seat/desktop-seat-review.json)仍待现场见证。 |
| 校验旧版 Win64 产物 / 读取离线统计 | Trace **Win64 离线交接分支**，见下表 | 静态原件证据与合成测试，不是 Win64 私有 Firefox 的完整源树，也不是 Linux 实采证明。业务项目宜依赖有版本的输出 schema，避免把推断地址当成稳定 ABI。 |
| HTTP 客户端 | [RuyiHttp 0.9.4](https://github.com/Facetomyself/ruyihttp/releases/tag/v0.9.4)：Python API、wheel、已入库原生库 | [精确 wheel 验收](../artifacts/receipts/ruyihttp-0.9.4/README.md)：Linux amd64 / ARM64 在 glibc 2.31 实装并通过直连 H1/H2/H3、双跳 TCP 和单跳 CONNECT-UDP 内层原生 H3；Windows 和两种 macOS 各验同平台工件。 |
| 公开 JS/DOM 开发与上游贡献 | [公开 RuyiJS 项目入口](../projects/ff-ruyijs/README.md)；开发检出按 [gitlink](../PINS.md#open-ruyijs) | `Facetomyself/ff-ruyijs` 的 `main` 用于公开源码维护，复现以 gitlink 为准；公开性能与 macOS/Linux 兼容改动提交上游，保留 Windows 共用主干的既有行为。公开发行、历史 donor 和内部 wheel 各自固定。 |
| 私有 JS/DOM 运行环境 | [RuyiJS 内部仓](../projects/ruyijs/README.md)：Python、C ABI、语义重建和构建脚本 | ARM64 选 [R433 双 wheel](../artifacts/receipts/ruyijs-linux-aarch64-product-r433/README.md)，正式下载实装及 `r433-host1`／完整 `r432-host1` 切换见[安装与回滚](../submodules/ruyijs/docs/linux-arm64-r433.md)。amd64 可用 [R355 原生包回执](../artifacts/receipts/ruyijs-linux-amd64-clean-r355/validation.json)和 [R356 wheel 安装](../submodules/ruyijs/docs/linux-amd64-clean-wheel.md)；[R357 明文 HTTP/1](../submodules/ruyijs/docs/linux-http1.md)可独立卸载。分项能力见[当前交付缺口](04-risks-and-gaps.md#当前交付缺口)。 |
| 程序化管理浏览器 | [MCP / owner 交接](../projects/ruyi-mcp/MANAGEMENT-HANDOFF.md) | [生产矩阵](../projects/ruyi-mcp/LIVE-MATRIX.md)涵盖双架构 CLI 同镜像、跨机 SSH stdio 和仅 ARM64 的意外退出恢复；早期 [amd64 R5 生产 M2](../projects/ruyi-mcp/PRODUCTION-OWNER.md)仍是独立证据。 |
| 离线 HTML/DOM 或显式 HTTP(S) 导航脚本 | [RuyiDOM 独立源码交接](#ruyidom-独立源码交接) | v0.3.1 交付 amd64 源码版 Docker 和裸 Jammy ARM64 专用包；现用 ARM64 宿主沿用 v0.3.0 Noble 镜像，可信脚本宿主仍是 Firefox 136.0。 |

## 源码检出：业务项目固定 SHA，不跟随最新分支构建

平台父仓公开，可匿名普通 clone；[.gitmodules](../.gitmodules) 登记五个独立组件的来源，[STATUS](../STATUS.yaml) 记录状态。按父仓提交与其一级 gitlink 复现；`git submodule update --remote` 获取的是组件分支头。公开组件的路径与 CI 权限见[访问边界](adr/0003-public-catalog-private-gitlinks.md)。

```bash
git clone https://github.com/Facetomyself/ruyi-platform.git
cd ruyi-platform
git rev-parse HEAD
git ls-tree HEAD:submodules
bash scripts/verify-pins.sh --catalog
```

仅取公开源码时，可列出全部三个公开路径，或只列当前所需路径：

```bash
git -c submodule.recurse=false submodule update --init --checkout -- \
  submodules/ruyihttp submodules/ruyi-mcp submodules/ff-ruyijs
```

具备两个私有子仓的读取权限时，可检出全部一级组件并核对仓内证据：

```bash
git -c submodule.recurse=false submodule update --init --checkout
bash scripts/verify-pins.sh --repo
```

仅在需要构建公开 RuyiJS 时，按 [fork 自己的构建手册入口](../projects/ff-ruyijs/README.md)取得其嵌套 Firefox。这个构建输入与 Trace Firefox、历史 donor、固定发布物及宿主现用版本均独立。

Trace 特定交付位于同一个[私有源码仓](https://github.com/Facetomyself/ruyitrace)。`main` 是 CLI 与构建工具的维护入口；R5 复现标签、早期 CLI 候选及独立证据分支保留原样。构建请用新的工作目录。

| 用途 | GitHub 引用 | 固定提交 / 用法 |
| --- | --- | --- |
| amd64 无头 R5 的冻结源码 | `source/amd64-headless-r5-20261124`（tag） | [ccc0ffa](https://github.com/Facetomyself/ruyitrace/tree/ccc0ffa1e65c291aa6cbdd68648f587eed6c0de9)，可重新导出验收时的原始输入 tar |
| R5 导出工具 | `handoff/oci-export-20261124` | [2cfa904](https://github.com/Facetomyself/ruyitrace/tree/2cfa904741da1ba07d0d31175c8124b5b2afd6f6)，用于传输验证，独立于内核输入 |
| 平台开发检出与生产 CLI/MCP 矩阵 | Trace `main`、MCP `linux` 为维护分支；复现按 gitlink | Trace [51852ce](https://github.com/Facetomyself/ruyitrace/tree/51852ce98804390a11ae326bd1205a5abf1a3eb6) 与 MCP [df0db85](https://github.com/Facetomyself/ruyi-mcp/tree/df0db8545a3f75461627a3f45c5bca8668211ea7) 是[生产矩阵](../projects/ruyi-mcp/LIVE-MATRIX.md)的 `corrected` 组合。开发检出可执行 `bash tests/linux/check_developer_checkout.sh`（在 Trace 仓根）。 |
| ARM64 R5 CLI2 发行、站点和较早 CLI | 独立标签与历史回执 | [f1253a6](https://github.com/Facetomyself/ruyitrace/tree/f1253a6ddf03dffa178d349231facc61866e686b) 固定 [ARM64 R5 租约发行](https://github.com/Facetomyself/ruyitrace/releases/tag/arm64-r5-cli2-lease-v1)，站点另用 [站点运维锁](../PINS.md#arm64-主机运维版本独立于原生内核发行)。amd64 交互镜像 [9f8dbb9](https://github.com/Facetomyself/ruyitrace/tree/9f8dbb9bbbd322c2e6a17b05b89fd23690067f2c)、旧生产 M2 [f8eeb0e](https://github.com/Facetomyself/ruyitrace/tree/f8eeb0ee909436fbe038a9e0bff67b5f96326022)、早期 CLI [13fd24b](https://github.com/Facetomyself/ruyitrace/tree/13fd24bf77f1a81cc12af3939049e72f04138d53) 各自保留。 |
| Trace 独立预发行 | 原生事件 Beta 1 与 Electron owner Alpha 1 | [独立发行固定值](../PINS.md#linux-原生事件私有候选不改默认子模块或站点)区分交付标签与实际运行时源码；两条预发行均未替换开发 gitlink 或稳定站点。 |
| ARM64 owner 受控 fixture | `handoff/owner-arm64-fixture-20261124` | [b4ba3a8](https://github.com/Facetomyself/ruyitrace/tree/b4ba3a876479f4fcfc68428051f2a1d9c5f78d31)，生命周期与基础 DOM 对照；不是生产管理面 |
| Win64 离线分析和测试 | `handoff/win64-offline-20261124` | [c3e0937 交接说明](https://github.com/Facetomyself/ruyitrace/blob/c3e0937cc455fac6b45f2725185dc5735e927785/docs/win64-offline-handoff.md)；115 份静态回执。检出后运行 `python3 -B tools/win64_offline_verify.py --tests`；原 DLL、随包 JS 和真实采集不随交接增量提交 |

## 无需编译，先验证 R5 源码确实可取

从平台根执行（目录名需是新路径）：

```bash
git clone --depth 1 --branch source/amd64-headless-r5-20261124 \
  https://github.com/Facetomyself/ruyitrace.git ../trace-amd64-r5
python3 scripts/verify-trace-release.py --source ../trace-amd64-r5
git -C ../trace-amd64-r5 archive --format=tar HEAD domtrace tests/linux > ../trace-r5-inputs.tar
python3 scripts/verify-trace-release.py --source ../trace-amd64-r5 --inputs ../trace-r5-inputs.tar
```

该入口核对 [R5 源码锁](../artifacts/receipts/trace-amd64-r5/source-lock.json) 中 **199 个源码文件**、冻结 tar 的 SHA-256，以及五份小型回执的身份链。在交接时从 GitHub 重新检出并执行过此项；原始 tar 与新导出 tar 的 SHA-256 均为 `e9450c2dd0bc3691f4dc15c82a4d50296c66589f947d53cb1ed868061e9feaf6`。原发布说明曾写父提交 `c52549f`；它的 staging 脚本与归档不符，准确提交以 **`ccc0ffa`** 为准。

若已取得离线制品（不在 Git 内），可加 `--package /path/to/candidate.tar.xz --docker-save /path/to/ruyitrace-headless-amd64.docker.tar`。包身份和发布 BuildID 见[运行时回执](../artifacts/receipts/trace-amd64-r5/runtime-identity.json)，镜像身份和归档摘要见[Docker-save 回执](../artifacts/receipts/trace-amd64-r5/docker-save-readback.json)。本机交接时同时重算过两份制品的哈希；重载后通过的[基线](../artifacts/receipts/trace-amd64-r5/oci-reloaded-baseline.json)和[script-error](../artifacts/receipts/trace-amd64-r5/oci-reloaded-script-error.json)是此前运行留存的证据。没有向镜像注册表上传制品。

## 真正重建时还需要什么

- **CLI**：在 Trace 根目录运行 `bash tests/linux/check_developer_checkout.sh`（Node ≥22.12、npm、Python ≥3.10、C++17）。独立交付用 `node console/tooling/build-cli.mjs /absolute/new/cli`；运行时需要目标机器的 Linux Node 和独立 Trace Firefox。Electron 应用仍可用 `node console/tooling/build-linux.mjs /absolute/new/app` 构建。本轮从 GitHub 干净检出跑通检查；新增的 [GitHub Actions 运行](https://github.com/Facetomyself/ruyitrace/actions/runs/45310452143) 因账户计费限制未启动 runner，不能视为 CI 通过。
- **Firefox 内核**：按[跨机器构建手册](../submodules/ruyitrace/docs/linux-build-from-source.md)准备官方 Firefox `9a2dc53c369c7ae5172018b35988e1d2ffeff402`、Clang 19.1.1、Rust 1.100.0、cbindgen 0.29.4、固定 WASI sysroot 与独立 objdir。主线包含可执行的洁净构建、原版 Rust 归档审计、打包及两档页面验收流程；R5 标签仅用于重现历史输入。重新编译会生成新的 BuildID，并须进行新包验收。
- **镜像**：取同一审计包和 runtime receipt，按[主线离线 Docker 流程](../submodules/ruyitrace/tests/linux/headless-oci.md)组装、跑两档 QA。已验收镜像可以 `docker load`，无需源码编译；同一检查脚本需要其固定 Ubuntu 24.04 本地基底 config ID。

## RuyiDOM 独立源码交接

[RuyiDOM 私有源码仓](https://github.com/Facetomyself/ruyidom)维护 Linux 启动器、适配层、测试与构建工具；`main` 用于日常维护。RuyiDOM 是第六个相关项目，仍单独检出，未纳入平台的五个一级 gitlink。

[RuyiDOM 实现与维护手册](https://github.com/Facetomyself/ruyidom/blob/1bfbd7c69e6ce4044510afd5ee9d04e774fb13c1/docs/architecture/README.md)涵盖 `native`／`browser` 双后端、RPC 与 BiDi 协议、句柄生命周期和优化复验，并说明如何编辑 Archify 图的 JSON 图源并再生成 SVG／HTML。这是知识手册入口，发布与运行证明仍以下文发行回执和实测记录为准。

**ARM64 日常使用**：在 `oracle-reverse-dev` 上以 `ubuntu` 运行 `~/.local/bin/ruyidom verify`，验证真实浏览器导航。2026-11-26 11:36 UTC 的[宿主读回](../artifacts/receipts/ruyijs-linux-aarch64-product-r433/independent-live.json)分别核对启动器目标 `v0.3.0-host1` 与本地标签 `ruyidom:arm64-use`；它仍指向下文的 Noble 镜像，和 v0.3.1 源码发行分开。入口按需启动临时容器，默认离线，未发布端口。见[主机使用与维护说明](https://github.com/Facetomyself/ruyidom/blob/5dd1ea218d0824207069ffba443593656039274d/deploy/arm64/README.md)。

**验收机空间维护**：正式归档、校验清单、原始回执和已配置的运行依赖留存；只回收已结束的 QA 展开树及校验相同的临时副本。具体分类和复验方法见[项目空间回收手册](https://github.com/Facetomyself/ruyidom/blob/6ffb604b5771ff9646c765d03db13cfdf0a5fe38/docs/DEVELOPMENT.md#验收机空间回收)。

### v0.3.1：源码版 ESR 的 amd64 与裸 Jammy ARM64 验收

检出[发布标签 `v0.3.1`](https://github.com/Facetomyself/ruyidom/releases/tag/v0.3.1)并核对完整提交；真实运行所需的受控工件、部署与复验命令见[可移植性手册](https://github.com/Facetomyself/ruyidom/blob/b57891fb9348842e22bbc9395c3db810c0c569fc/docs/PORTABILITY.md)和[发行回执](../artifacts/receipts/ruyidom-source-portability-v0.3.1.json)。

```bash
set -eu
sha=b57891fb9348842e22bbc9395c3db810c0c569fc
repo=https://github.com/Facetomyself/ruyidom.git
git clone --branch v0.3.1 "$repo" ruyidom
test "$(git -C ruyidom rev-parse HEAD)" = "$sha"
make -C ruyidom check
```

- **amd64**：在 `host185` 原生完成 Firefox `153.8.0esr` 的完整源码编译和打包（Build ID `20261126091201`）。用新包构建的 `linux/amd64` 镜像通过 8/8 项、12/12 组浏览器测试、10/10 次冷启动。私有镜像归档在 `host185` 的现有 Docker 存储回载，按同一镜像 ID 复测 native 冒烟、浏览器重定向及 CSP。这与 v0.2.0 的只读叠加验证、历史 P3 和第二台 ARM64 主机空存储验证均不同。
- **ARM64 裸 Jammy**：专用 Firefox `153.8.0esr` 包（Build ID `20261126091202`）在 `oracle-dsh` 的裸 Ubuntu 22.04.5 ARM64 / glibc 2.35 通过 10/10 条命令、12/12 组浏览器测试、10/10 次冷启动和 10 次回环请求。全部 30 个 ELF 通过 ABI 审计；实际导航核对外链脚本随机值与 CSP，进程映射按 inode 验证系统动态加载器、libc、libstdc++ 和该包的 `libxul.so`。原 v0.3.0 Noble 包在裸 Jammy 的启动失败仍是负对照。

| v0.3.1 工件 | 字节数 | SHA-256 |
| --- | ---: | --- |
| amd64 Firefox 包 | 80,205,228 | `31944ed2290c63643662500896540b3268b9942f3e05884c42d9fdd19274a6e9` |
| amd64 Docker 归档 | 407,591,801 | `0b0132a0dc3c604b19b44688f52ed114c7507f63ddbf9cca7e5a348f107c34bc` |
| 裸 Jammy ARM64 Firefox 包 | 72,862,192 | `d8d64b1628d6cbf2056c5edd9a2c53e11b0e2ab68288eb5f04b01346aeefa70e` |

保留的 amd64 镜像 ID：`sha256:1f0347fd3b575c141b2856a590c83dbdb131403b6ce06a162694fc67bf05faac`。日常 `ruyidom:arm64-use` 继续使用已部署的 v0.3.0 Noble 镜像，可信脚本宿主仍为官方 Firefox 136.0。

### v0.3.0：ARM64 Noble 源码版 ESR 内容引擎

需要复现原发行时，检出[发布标签 `v0.3.0`](https://github.com/Facetomyself/ruyidom/releases/tag/v0.3.0)并核对完整提交：

```bash
set -eu
sha=790cc23e6c049bbcb2d186656fa5545d1ef7bac6
repo=https://github.com/Facetomyself/ruyidom.git
git clone --branch v0.3.0 "$repo" ruyidom
test "$(git -C ruyidom rev-parse HEAD)" = "$sha"
make -C ruyidom check
```

[源码构建与验收流程](https://github.com/Facetomyself/ruyidom/blob/790cc23e6c049bbcb2d186656fa5545d1ef7bac6/source-build/README.md)记录原生 ARM64 上从 Mozilla Firefox `153.8.0esr` 源码完整编译的路径。本次在 `oracle-reverse-dev` 完成 `mach configure`（109 秒）、`mach build`（15,183 秒）和 `mach package`（163 秒）；SourceStamp 为 `44242c0bf7eef0918a458568730d8e36022e0743`，自建 Build ID 为 `20261125161200`。`v0.3.0` 维护独立内容引擎配置 `153.8.0esr-source-20261125161200`。已验收镜像以 `v0.2.0` 源码为基线，加上源码版引擎配置的叠加层装配，见[实测回执](https://github.com/Facetomyself/ruyidom/blob/790cc23e6c049bbcb2d186656fa5545d1ef7bac6/docs/releases/arm64-source-v0.3.json)。可信脚本宿主仍是官方 Firefox 136.0；本次范围仅为 ARM64 内容引擎。

[部署、换机与回滚说明](https://github.com/Facetomyself/ruyidom/blob/790cc23e6c049bbcb2d186656fa5545d1ef7bac6/docs/ARM64-SOURCE-RELEASE.md)提供受控存储取用、校验和 `docker load` 命令。自建 Firefox 包与含私有框架的 Docker 归档是不同工件；镜像未推送到注册表。

| 工件 | 字节数 | SHA-256 |
| --- | ---: | --- |
| `firefox-153.8.0.en-US.linux-aarch64.tar.xz` | 72,307,796 | `9fbaa767a9d0eedd740378d945f7d9dacb8043df3cf93364f5cdec26b85d60d0` |
| `ruyidom-arm64-source-20261125161200-648b02c0896e1cae.docker.tar.gz` | 386,773,602 | `7824494c3f3ce30f1e8df4086dc3ce7eade69e7b2f5a6a7f8c2556657b0a8e34` |

2026-11-25 23:32:36 UTC 在 `oracle-reverse-dev` 只读核对保留标签 `ruyidom:arm64-source-20261125161200-648b02c0896e1cae` 为 `linux/arm64`，镜像 ID 为 `sha256:f9d740cf768f3c5048e8850f55e4355946abb1a64f054c054673f00b8a2fd23d`：

```bash
ssh oracle-reverse-dev 'docker image inspect --format "{{.Id}} {{.Os}}/{{.Architecture}}" ruyidom:arm64-source-20261125161200-648b02c0896e1cae'
```

**v0.3.0 发行时的验收**：镜像 8/8 项通过，源码版内容引擎的浏览器套件 12/12、冷启动 10/10。Ubuntu 24.04 Noble 容器内通过，裸 Ubuntu 22.04 Jammy 因动态库符号缺失启动失败。归档在原 ARM 主机的现有 Docker 存储离线重载后，镜像 ID 一致，native 冒烟和浏览器重定向/CSP 通过；当时第二台主机只核对了归档摘要。

**第二台 ARM64 主机冷恢复**：2026-11-26 10:04 UTC，在 `oracle-dsh` 原生 ARM64 上，把同一份 v0.3.0 归档导入本机新建的隔离 Docker/containerd 空存储。导入前镜像、容器、内容记录、快照及物理 blob 计数均为零；导入后核对原镜像配置摘要、manifest 及 7 层摘要。Docker 29 的 containerd 存储显示的是 manifest 摘要，与旧存储显示的配置摘要是两个不同标识。复验见[换机步骤](https://github.com/Facetomyself/ruyidom/blob/1344fec24407b5d525ea5b47e0ba6522c8522279/docs/ARM64-SOURCE-RELEASE.md#2-在另一台-arm64-机器部署)和[独立冷恢复回执](../artifacts/receipts/ruyidom-arm64-v0.3-cold-restore.json)。

Firefox 136 native 序列化 10/10；真实浏览器完成 `GET /start` → `/page` → `/external.js`，验过外链 nonce、两项 CSP 内联阻断和清理。较早一次默认 15 秒用例超时，本次冷恢复后的默认 15 秒和单独的 75 秒用例均通过。补跑原八项命令通过 7/8：整套 `browser-nav` 达到 270 秒上限、5 秒终止宽限后退出 137；第二台主机没有完整组数或冷启动计数。独立存储已清理。成功范围是使用镜像内 Noble 用户态的冷恢复与真实导航；它与 v0.3.1 的裸 Jammy 和 amd64 源码验收分别记账。

### v0.2.0：官方内容引擎基线与历史 AMD64 P3

需要复现旧基线时，检出[附注标签 `v0.2.0`](https://github.com/Facetomyself/ruyidom/tree/v0.2.0)并核对完整提交：

```bash
set -eu
sha=1a1421051ebb0de38c7f194983fd2503d777db51
repo=https://github.com/Facetomyself/ruyidom.git
git clone --branch v0.2.0 --single-branch "$repo" ruyidom
test "$(git -C ruyidom rev-parse HEAD)" = "$sha"
make -C ruyidom check
```

`make check` 校验维护源码；真实运行和镜像构建另按[输入恢复说明](https://github.com/Facetomyself/ruyidom/blob/1a1421051ebb0de38c7f194983fd2503d777db51/docs/INPUTS.md)准备供应商框架和固定的公开依赖，供应商框架仍为 `not-in-git`。

[v0.2.0 变更](https://github.com/Facetomyself/ruyidom/blob/1a1421051ebb0de38c7f194983fd2503d777db51/CHANGELOG.md#v020--2026-11-25)经定向回归验证：完整 RPC 回复帧超 8 MiB 时返回 `result_too_large`，原页、兄弟页和新页仍可用；native 序列化保留调用方沙箱全局属性；导航超时分别覆盖主文档响应前和解析阻塞脚本阶段。恢复运行输入后，执行 `make -C ruyidom regression-fixes` 复测。

[双引擎实测回执](https://github.com/Facetomyself/ruyidom/blob/1a1421051ebb0de38c7f194983fd2503d777db51/docs/releases/dual-engines-v0.2.json)对应冻结运行提交 `de30443e1d1530176b4321412e7f05945123cfa1`，与上面的发布标签提交分开记录。Firefox 136.0 继续作为可信脚本和 native DOM 宿主；Firefox `153.8.0esr` 仅供显式选择浏览器内容进程，136.0 也是可用的内容引擎。

- **ARM64 Docker**：在 `oracle-reverse-dev` 上从零无缓存构建；两个内容引擎浏览器套件各 12/12，通过 [ARM64 构建及验收流程](https://github.com/Facetomyself/ruyidom/blob/1a1421051ebb0de38c7f194983fd2503d777db51/docs/FIREFOX-MATRIX.md#复现与切换)可复测。保留标签 `ruyidom:arm64-de30443-dual-r2zidw5j` 仅在该主机本地，未导出或推送到注册表。2026-11-25 15:44:33 UTC 只读核对为 `linux/arm64`，镜像 ID 为 `sha256:9fa4311f1d136cb5032ed5df5f985e1e33297a98752966629e9e9bb38626c9bc`：

  ```bash
  ssh oracle-reverse-dev 'docker image inspect --format "{{.Id}} {{.Os}}/{{.Architecture}}" ruyidom:arm64-de30443-dual-r2zidw5j'
  ```

- **amd64**：在 host185 的现有 P3 容器中只读挂载冻结源码与单独校验的 ESR 安装树，两个内容引擎浏览器套件各 12/12；此次只验证运行兼容，未重新构建 amd64 镜像。
- **v0.2.0 构建边界**：此次 Docker 验收使用 Mozilla 官方已编译的 Firefox，当时未运行完整上游 Gecko `mach build`；源码编译是上面的独立 v0.3.0 交付。

[v0.1.0 源码交接回执](../artifacts/receipts/ruyidom-source-v0.1.0.json)仍记录当时的干净 ARM64 原生恢复、amd64 便携镜像测试，以及未运行的 ARM64 Docker 门禁；[v0.1.0 发布页](https://github.com/Facetomyself/ruyidom/releases/tag/v0.1.0)仍提供离线源码 Git bundle 和 `SHA256SUMS`。[host185 工件取用与校验](https://github.com/Facetomyself/openclaw-infra/blob/main/hosts/self-server/projects/ruyidom-browser-candidate.md#10-common-tasks)记录私有框架最小包与**历史 AMD64 P3 Docker 归档**的取用方法。该 P3 归档在源码导入 Git 前已验收，与各版本源码标签及 v0.2.0、v0.3.0 的 ARM64 镜像是不同工件。

## 以后如何维护

组件改动先在所属仓提交并推送，记录测试范围。已由 gitlink 接入的平台组件再更新相应 gitlink 和 `STATUS.yaml`，跑 `scripts/verify-pins.sh`；RuyiDOM 在独立仓发布，在这里更新交接引用。已有发布标签保留原位；新发行另打标签、生成新的锁和回执。将包、镜像、工具链缓存和浏览器 profile 与源码分开保管。`git status` 中其他开发者的工作或某台机器的缓存不构成可构建版本。
