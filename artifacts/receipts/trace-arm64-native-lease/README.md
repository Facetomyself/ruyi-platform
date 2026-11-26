# RuyiTrace ARM64 独立目标

**正式发行证据与最终宿主收尾均已通过平台校验。** [确认索引](release/confirmation.json)绑定 33 份原始回执与九道验证关卡，覆盖 `oracle-reverse-dev` 原生 `linux/arm64`、attempt `attempt.j1mT36SL`、Firefox BuildID `20261125162841`。[预检索引](preflight/stage.json)仍是构建中的历史截面；`--preflight` 只核验当时的输入、环境和公网健康页。已发布的 amd64 镜像与回执保持独立。

[GitHub 私有发行 `arm64-r5-cli2-lease-v1`](https://github.com/Facetomyself/ruyitrace/releases/tag/arm64-r5-cli2-lease-v1)已发布，源码与标签均为 `f1253a6ddf03dffa178d349231facc61866e686b`。六个附件已通过正式发布端点重新下载并计算 SHA-256，包含三镜像 Docker 归档、独立 Firefox、可携带的 CLI 技能、两个清单及校验和。[发布端回读](github-release.json)与产品验收索引分别记录，前者不替代后者。

## 正式回执（UTC）

- **原生构建和归档**：[同包内核审计](release/kernel-release-summary.json)、[CLI doctor](release/cli-doctor.json)和[构建终态](release/post-kernel-result.json)连接到同一发行。2026-11-25 23:55:45，归档生产完成。[归档回读](release/archive-verified.json)记录 `381640590` 字节、SHA-256 `1de33f49c6ceac4cfd1686b42203bddb1255882c67cad80b4b617247c1c267cb`、三个 Docker config ID 与 CLI → 私有桌面 → TLS edge 的 `4 → 5 → 6` 层前缀关系；[本机生产登记回读](release/production-verified-release.json)匹配其镜像 ID 与清单。
- **私有桌面及空引擎**：[原生私有 noVNC](release/private-native.json)覆盖真实键鼠、重连、三次点击、采集开关与 owner 退出。[独立空引擎](release/empty-engine.json)从零镜像开始，在隔离的原生 Docker 29.1.3 中载入同一归档，执行 CLI、私有 Unix socket 查看器和原生 edge 回读，并验证独立引擎关闭、宿主 daemon 身份保持原样。真实 loopback Firefox 分别验证[自然到期](release/loopback-expire.json)、[主动撤销](release/loopback-revoke.json)和 [worker 丢失](release/loopback-worker-loss.json)后的连接断开与清理。
- **公网桌面及收尾**：2026-11-26 00:16:11，独立 `oracle-dsh` 上的 [ARM Mozilla Firefox](release/external-desktop.json)经真实公共 DNS、系统/浏览器信任链与 443/WSS 看到非空 `1280×720` 桌面，确认已用邀请被拒、现有会话可重连、撤销后 WSS 关闭。相同会话的目标 vNIC 实测中，原生 CLI 的 Python 校验错误为 `64`，Firefox 为 `SSL_ERROR_BAD_CERT_DOMAIN`。00:28:02 的[最终收尾](release/post-cleanup.json)确认 80/443 已无监听，租约容器、运行目录和 QA 单元文件计数为零，且 `loaded_qa_units` 为空。临时 QA 私钥已清理，原有主机及 OCI 准入规则摘要一致，SSH、Docker、Certbot timer 和生产清扫 timer 仍在运行。

运行[平台验证器](../../../scripts/verify-trace-arm64.py)的默认模式或 `--release`，即可按[收集契约](receipt-paths.json)复验原始字节与索引。传 `--archive /绝对路径/归档` 会再读实际 gzip，核对字节数、SHA-256、配置 JSON 与层字节。正式索引创建前已完成这项校验；成品核对同时通过了 `archive_bytes_checked: true` 的复验。源仓库带有对应的本地 Git 对象即可，`--trace-source /绝对路径/Trace仓库` 可显式指定其位置。

## 历史预检

- **机器实测**：[OCI](preflight/oci-shape-and-network.json) 与 [guest](preflight/site-health.json) 对齐：`oracle-reverse-dev` 是现有 4 OCPU、24 GB、200 GiB A1.Flex，原生 aarch64。没有额外开一台同名 VM。R5 attempt 为 `attempt.j1mT36SL`，源码基线 `c3723ca5…`，构建配置报告 BuildID `20261125162841`。`20261121211603` 是历史 ARM 包，不能代替本轮。
- **独立公网接入**：[专用 DNS](preflight/dns.json)、[续期演练](preflight/renewal.json)及三个外部传输层结果：[oracle-dsh](preflight/oracle-dsh.json)、[香港中继](preflight/hk-relay.json)、[host185 查看器用户态](preflight/host185.json)。系统 CA、域名和叶摘要验证均开启；目标固定响应 200，未服务路径 404，常规 Caddy 没有接管站点，短时服务随后关闭。host185 的旧离线浏览器用户态缺省没有 Python CA 包，测试显式提供该外部主机的操作系统公共根，未将服务端叶证书作为根。
- **浏览器层增量**：2026-11-25 17:21 UTC，[独立的 ARM 版 Mozilla Firefox 159](public-health-browser/oracle-dsh-native-firefox.json)在 `oracle-dsh` 的只读用户态，通过真实公网出口看到固定 HTTPS 页面，域名/证书验证全程开启。IP 字面值的负对照是服务端 TLS/SNI 告警，未把它写成证书域名错误。host185 的浏览器直连曾导航超时，其协议层 200 不代表该出口一定流畅。这个测试没有发邀请，也没有启动桌面。见[夹具版本和摘要](public-health-browser/provenance.json)。
- **构建可信度**：[Gecko 补丁与上游审计文件](preflight/reviewed-gecko-inputs.json)在全新对象目录单独核对。当前[固定构建、检查点与离线导出驱动](https://github.com/Facetomyself/ruyitrace/tree/934c67f0cc71f403663e455deb18585e7ee822b5/product/arm64)仅允许正式核对通过后消费本轮包。

## 失败与复验说明

1. [原始私有 QA 失败](release/private-first-failure.json)发生在重连后：画面已显示第二阶段，但输入坐标命中 noVNC 过渡层，第三次点击未送达。保留原始失败字节。随后只改 [QA peer 与回归测试](https://github.com/Facetomyself/ruyitrace/commit/3c8ec093ba22b714ab57d4685229505182c52d56)，原始 Docker 生产者、镜像 config ID 和公共 Firefox 夹具保持原样；[恢复操作](https://github.com/Facetomyself/ruyitrace/commit/00297cf14b534aeb8a0b06fc67cbf9650e3ef163)重新调用原始组装器。23:54:29 的[恢复回执](release/private-readiness-recovery.json)与[原始组装检查点](release/private-qa-checkpoint.json)绑定新的通过报告，证明画布已可接收输入、真实第三次点击完成。之后才重启生产流程并完成归档。
2. 较早的私有租约准备遇到 `/run` 的 `noexec`，该轮未创建邀请或租约；[修订](https://github.com/Facetomyself/ruyitrace/commit/45d6e657b24f5c90ab8e5f4c34d518d67e0c5344)调整临时单元的可执行文件放置，保留了宿主挂载策略。早期空引擎 shell 另有 `started: unbound variable`，其退出与后续 VFS 冷创建诊断均仅属排查。正式[空引擎回执](release/empty-engine.json)源于[修订后的 shell](https://github.com/Facetomyself/ruyitrace/commit/138664569a835965835cf4abf157dd52092264ba)在新目录完成的完整空引擎试验；修订将 VFS 冷创建与进程启动分开计时并记录实际退出阶段，Python 验证器 SHA-256 仍为 `00d2569eab996585fd9ecd8804d9fea54a5e761e4ecd2bbe9739001c4359bed5`。
3. 00:16:54 的初次收尾只统计 QA 单元文件。随后发现这三次 QA 用例留下了一个已加载的空隐式 systemd slice；经确认其进程计数、cgroup `populated` 值均为零，且无依赖后，停止该 slice 并验证对应 cgroup 消失。00:28:02 的[追加宿主回读](release/post-cleanup.json)同时核对单元文件与已加载的 QA 单元，以其原始字节重建索引后再次通过归档完整校验。
