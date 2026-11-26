# 其他项目如何使用 Ruyi Platform（2026-11-24 交接）

**Trace 的独立 Linux CLI 已纳入主线。** 平台固定的是可继续开发的 Trace 源码；复现已发布的 amd64 无头 R5 原始内核输入仍使用独立标签。先选择目标：构建 CLI、重建 Firefox，或组装可选的 Electron 桌面。

## 选择交付物

| 需求 | 使用什么 | 已有证据与边界 |
| --- | --- | --- |
| 自有页面的浏览器采集 | Trace amd64 **R5 无头运行时** | 原生完整构建、Rust 归档审计、打包、镜像保存后本机重新加载并运行两档 QA；覆盖 DOM、click、脱敏 Storage、双会话及显式 script-error 档。它不是 Electron、MCP 服务或任意 producer 的保证。 |
| Linux 命令行采集 | [独立 CLI](../submodules/ruyitrace/console/cli/README.md) + 合格内核 | 与 R5 同一 amd64 实包验过双会话开关、活进程停止、异常摘要一条；[实机回执](../artifacts/receipts/trace-amd64-r5/cli-native-amd64.json)。 |
| 桌面配置和日志预览 | Trace 的可选 Electron + **对应架构**的合格内核 | 较早的 x86_64 和 ARM64 各有独立实包及虚拟 X11/Wayland 验收，[详情](13-ruyitrace-progress.md)。物理显示、更广 producer 和所有 Win64 行为的等价性另验。 |
| 校验旧版 Win64 产物 / 读取离线统计 | Trace **Win64 离线交接分支**，见下表 | 静态原件证据与合成测试，不是 Win64 私有 Firefox 的完整源树，也不是 Linux 实采证明。业务项目宜依赖有版本的输出 schema，避免把推断地址当成稳定 ABI。 |
| HTTP 客户端 | [RuyiHttp](../projects/ruyihttp/README.md)：Python API、wheel 构建与已入库原生库 | Linux amd64 在 glibc 2.39 上通过 HTTPS/TLS 1.3/h2；另有[原生 Linux ARM64 与 H1/H2/H3 验收](../artifacts/receipts/ruyihttp-native-20261124/linux-aarch64.json)。另见 [Intel macOS 原生验收](../artifacts/receipts/ruyihttp-native-20261124/darwin-x86_64.json)；这些传输证据属于 RuyiHttp，不替代 RuyiJS 联网验收。 |
| JS/DOM 运行环境 | [RuyiJS 内部仓](../projects/ruyijs/README.md)：Python、C ABI、语义重建和构建脚本 | [R355 干净重建原生包](../artifacts/receipts/ruyijs-linux-amd64-clean-r355/validation.json)：Ubuntu 24.04/glibc 2.39 从空目录编译 1,268 个私有单元、解包实跑 Python/C 13/13，另验 Worker 与 WebCrypto。[原生包运行命令](../submodules/ruyijs/docs/linux-amd64-clean.md)。pip 安装使用[R356](../submodules/ruyijs/docs/linux-amd64-clean-wheel.md)；直接明文 HTTP/1 另装可卸载的 [R357 组件](../submodules/ruyijs/docs/linux-http1.md)。[R356 安装态回执](../artifacts/receipts/ruyijs-linux-amd64-wheel-r356/validation.json) · [R357 真实回环收发回执](../artifacts/receipts/ruyijs-linux-http1-r357/validation.json)。TLS、h2、QUIC 与 RuyiJS ARM64 产品另验。 |
| 程序化管理浏览器 | [MCP / owner 交接及验收表](../projects/ruyi-mcp/MANAGEMENT-HANDOFF.md) | [AMD64 R5 生产 M2](../projects/ruyi-mcp/PRODUCTION-OWNER.md)通过排他借用、真断点、归还与重借、暂停中停止及原生关闸读回；使用从干净 GitHub 检出构建并搬到另一台主机的独立 CLI。 |
| 离线 HTML/DOM 或显式 HTTP(S) 导航脚本 | [RuyiDOM v0.3.0 独立源码交接](#ruyidom-独立源码交接) | ARM64 源码版 ESR 内容引擎已通过 Docker 验收；可信脚本宿主仍为 Firefox 136.0。v0.2.0 官方内容引擎与历史 amd64/P3 证据分开保留。 |

## 源码检出：业务项目固定 SHA，不跟随最新分支构建

平台（private）负责四个 gitlink，代码在各组件仓。[.gitmodules](../.gitmodules) 定义来源，[STATUS.yaml](../STATUS.yaml) 记录状态。下游可将平台交接标签解析为提交，写入自己的依赖锁；已有子模块的仓库勿用 `git submodule update --remote` 替代固定提交。需要私有仓读取权限，凭据由使用方的 Git 客户端管理。

```bash
git clone --branch main --recurse-submodules https://github.com/Facetomyself/ruyi-platform.git
cd ruyi-platform
git rev-parse HEAD
git ls-tree HEAD:submodules
bash scripts/verify-pins.sh  # Python 3 + PyYAML；使用已入库的开关清单或本地重新生成的清单
```

Trace 特定交付位于同一个[私有源码仓](https://github.com/Facetomyself/ruyitrace)。`main` 是 CLI 与构建工具的维护入口；R5 复现标签、早期 CLI 候选及独立证据分支保留原样。构建请用新的工作目录。

| 用途 | GitHub 引用 | 固定提交 / 用法 |
| --- | --- | --- |
| amd64 无头 R5 的冻结源码 | `source/amd64-headless-r5-20261124`（tag） | [ccc0ffa](https://github.com/Facetomyself/ruyitrace/tree/ccc0ffa1e65c291aa6cbdd68648f587eed6c0de9)，可重新导出验收时的原始输入 tar |
| R5 导出工具 | `handoff/oci-export-20261124` | [2cfa904](https://github.com/Facetomyself/ruyitrace/tree/2cfa904741da1ba07d0d31175c8124b5b2afd6f6)，用于传输验证，独立于内核输入 |
| 日常开发、独立 Linux CLI 和当前构建工具 | `main`；平台 gitlink 固定开发版本 | [c3723ca](https://github.com/Facetomyself/ruyitrace/tree/c3723ca5f71e860ed19d1fa1a4305da930dc7428)，含独立 CLI、常驻采集修复、场景技能与可选 TLS 租约；已发布交互镜像的来源仍固定于 [9f8dbb9](https://github.com/Facetomyself/ruyitrace/tree/9f8dbb9bbbd322c2e6a17b05b89fd23690067f2c)。克隆后 `bash tests/linux/check_developer_checkout.sh`。生产 M2 回执仍指 [f8eeb0e](https://github.com/Facetomyself/ruyitrace/tree/f8eeb0ee909436fbe038a9e0bff67b5f96326022)，[13fd24b](https://github.com/Facetomyself/ruyitrace/tree/13fd24bf77f1a81cc12af3939049e72f04138d53) 保留早期 CLI 证据 |
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

[RuyiDOM 私有源码仓](https://github.com/Facetomyself/ruyidom)维护 Linux 启动器、适配层、测试与构建工具；`main` 用于日常维护。RuyiDOM 单独检出，现有四个 gitlink 与各自的版本固定方式维持原样。

**ARM64 日常使用**：在 `oracle-reverse-dev` 上以 `ubuntu` 运行 `/home/ubuntu/.local/bin/ruyidom verify`，验证真实浏览器导航。本地标签 `ruyidom:arm64-use` 指向下文同一个 v0.3.0 镜像 ID；入口按需启动临时容器，默认离线，未发布端口。见[主机使用与维护说明](https://github.com/Facetomyself/ruyidom/blob/5dd1ea218d0824207069ffba443593656039274d/deploy/arm64/README.md)。

### v0.3.0：ARM64 源码版 ESR 内容引擎

新机器用有读取权限的 Git 账号检出[发布标签 `v0.3.0`](https://github.com/Facetomyself/ruyidom/releases/tag/v0.3.0)并核对完整提交：

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

镜像 8/8 项验收通过，源码版内容引擎的浏览器套件 12/12、冷启动 10/10。Ubuntu 24.04 Noble 容器内通过，裸 Ubuntu 22.04 Jammy 因动态库符号缺失启动失败。归档已在原 ARM 主机的现有 Docker 存储离线重载，镜像 ID 一致，native 冒烟和浏览器重定向/CSP 通过；维护工作区的独立副本只核验归档摘要，尚无第二台主机冷导入的验收。

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
