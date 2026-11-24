# 其他项目如何使用 Ruyi Platform（2026-11-24 交接）

**Trace 的 Linux 运行时按已验收范围收尾，常规工作转向管理面。** 对于新项目，“拉取平台”“复建发行浏览器”“开发控制台”是三种不同操作；平台默认 Trace gitlink 并非最新 amd64 无头包的构建输入。

## 选择交付物

| 需求 | 使用什么 | 已有证据与边界 |
| --- | --- | --- |
| 自有页面的浏览器采集 | Trace amd64 **R5 无头运行时** | 原生完整构建、Rust 归档审计、打包、镜像保存后本机重新加载并运行两档 QA；覆盖 DOM、click、脱敏 Storage、双会话及显式 script-error 档。它不是 Electron、MCP 服务或任意 producer 的保证。 |
| 桌面配置和日志预览 | Trace 默认源码中的 Electron + **对应架构**的合格内核 | 较早的 x86_64 和 ARM64 各有独立实包及虚拟 X11/Wayland 验收，[详情](13-ruyitrace-progress.md)。物理显示、更广 producer 和所有 Win64 行为的等价性另验。 |
| 校验旧版 Win64 产物 / 读取离线统计 | Trace **Win64 离线交接分支**，见下表 | 静态原件证据与合成测试，不是 Win64 私有 Firefox 的完整源树，也不是 Linux 实采证明。业务项目宜依赖有版本的输出 schema，避免把推断地址当成稳定 ABI。 |
| HTTP 客户端 | [RuyiHttp](../projects/ruyihttp/README.md)：Python API、wheel 构建与已入库原生库 | 三平台既有库可重打包；Linux amd64 在 glibc 2.39 上通过 HTTPS/TLS 1.3/h2。Linux ARM64、macOS x86_64 新原生库及 H3/代理联验独立；重打 wheel 不等于从 C++/Rust 重建底层库。 |
| JS/DOM 运行环境 | [RuyiJS 内部仓](../projects/ruyijs/README.md)：Python、C ABI、语义重建和构建脚本 | Linux 客户端、donor 与若干部件已有验收。以本交接基线 `ab060a5` 所对应 R344 回执为准，产品链接仍失败，未形成合格的内部 Linux `dist/js`/wheel。pixman 仍在编译阶段受阻于 include 形状，且该修复不等于下一次整链已过。 |
| 程序化管理浏览器 | [MCP / owner 交接及验收表](../projects/ruyi-mcp/MANAGEMENT-HANDOFF.md) | [AMD64 真机验收](../projects/ruyi-mcp/README.md#amd64-容器与-trace-制品)通过 MCP 自启、下载和 19 项 RDP；与 Trace 自身实采分开。候选 CLI 已从 GitHub 干净副本按锁文件构建出应用目录，但生产借用、RDP 暂停恢复、归还与最终 flush 的整链尚待验收。 |

## 源码检出：业务项目固定 SHA，不跟随最新分支构建

平台（private）负责四个 gitlink，代码在各组件仓。[.gitmodules](../.gitmodules) 定义来源，[STATUS.yaml](../STATUS.yaml) 记录状态。下游可将平台交接标签解析为提交，写入自己的依赖锁；已有子模块的仓库勿用 `git submodule update --remote` 替代固定提交。需要私有仓读取权限，凭据由使用方的 Git 客户端管理。

```bash
git clone --branch handoff/platform-source-20261124 --recurse-submodules https://github.com/Facetomyself/ruyi-platform.git
cd ruyi-platform
git rev-parse HEAD
git ls-tree HEAD:submodules
bash scripts/verify-pins.sh  # Python 3 + PyYAML；使用已入库的开关清单或本地重新生成的清单
```

Trace 特定交付位于同一个[私有源码仓](https://github.com/Facetomyself/ruyitrace)。保留原始提交身份：正式源码用标签，候选用独立分支，均与产品默认主线分开。构建请用新的工作目录。

| 用途 | GitHub 引用 | 固定提交 / 用法 |
| --- | --- | --- |
| amd64 无头 R5 的冻结源码 | `source/amd64-headless-r5-20261124`（tag） | [ccc0ffa](https://github.com/Facetomyself/ruyitrace/tree/ccc0ffa1e65c291aa6cbdd68648f587eed6c0de9)，可重新导出验收时的原始输入 tar |
| R5 导出工具 | `handoff/oci-export-20261124` | [2cfa904](https://github.com/Facetomyself/ruyitrace/tree/2cfa904741da1ba07d0d31175c8124b5b2afd6f6)，用于传输验证，独立于内核输入 |
| 管理 CLI 及应用组装候选 | `handoff/management-cli-20261124` | [1452154](https://github.com/Facetomyself/ruyitrace/tree/1452154c64437b00494c005cbd54a5003c77def3)，CLI/组装各 8 项合成测试；干净构建 6 个 renderer 路由、77 个应用文件，含可执行 `bin/ruyitrace`，不含 Electron/Firefox |
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

- **内核**：R5 标签提供 `domtrace/`、补丁与 `tests/linux/run_audited_build.sh`，不是整棵 Firefox 源树。另备官方 Firefox `9a2dc53c369c7ae5172018b35988e1d2ffeff402`、原生 amd64 Linux、足够空间、Clang 19、Rust 1.100.0、cbindgen 0.29.4、已校验的 WASI sysroot 与独立 objdir。以标签内[构建脚本](https://github.com/Facetomyself/ruyitrace/blob/ccc0ffa1e65c291aa6cbdd68648f587eed6c0de9/tests/linux/run_audited_build.sh)为准；R5 使用 `RUYITRACE_AMD64_WINDOW_ERROR_RELEASE=1` 并保留原版 Rust 网络归档审计，再打包验收。脚本会采样构建时间，本交接证明**输入可还原**，不承诺下一次 Firefox 二进制逐字节一致。
- **镜像**：取同一包和 runtime receipt，按标签中的[离线 OCI 流程](https://github.com/Facetomyself/ruyitrace/blob/ccc0ffa1e65c291aa6cbdd68648f587eed6c0de9/tests/linux/headless-oci.md)组装、跑两档 QA；基底是已预装的 Ubuntu 24.04 本地镜像/config ID，不是可直接从注册表拉取的 manifest digest。
- **管理应用**：在上述 CLI 候选的独立副本，Node ≥22.12；`npm --prefix console/tooling ci --ignore-scripts --no-audit --no-fund`，再 `node console/tooling/build-linux.mjs /absolute/new/app`。完整桌面发行还需匹配架构的 Electron 45.4.1 ZIP、审计内核与资格回执。`run --gate auto` 的重复开闸嫌疑及真实 CLI 会话验收是待办；已有应用构建和 stub 测试不代替这一步。

## 以后如何维护

组件改动先在所属仓提交并推送，记录测试范围；再在平台更新对应 gitlink 和 `STATUS.yaml` 的完整提交，跑 `scripts/verify-pins.sh`。已有发布标签保留原位；新发行另打标签、生成新的锁和回执。将包、镜像、工具链缓存和浏览器 profile 与源码分开保管。`git status` 中其他开发者的工作或某台机器的缓存不构成可构建版本。
