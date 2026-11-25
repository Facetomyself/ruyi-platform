# RuyiTrace ARM64 独立目标

[预检索引](preflight/stage.json)是构建过程的一份**历史截面**，不是最终 ARM 发行回执。它绑定原始文件 SHA-256、目标机、精确构建输入与当时仍在执行的 attempt。正式签收需要另外记录同一归档的 Rust 网络审计、native CLI doctor、真实 noVNC 私有/公网访问和收尾，再发布 ARM 镜像 ID。已发布的 amd64 镜像和回执保持独立。

- **机器实测**：[OCI](preflight/oci-shape-and-network.json) 与 [guest](preflight/site-health.json) 对齐：`oracle-reverse-dev` 是现有 4 OCPU、24 GB、200 GiB A1.Flex，原生 aarch64。没有额外开一台同名 VM。R5 attempt 为 `attempt.j1mT36SL`，源码基线 `c3723ca5…`，构建配置报告 BuildID `20261125162841`。`20261121211603` 是历史 ARM 包，不能代替本轮。
- **独立公网接入**：[专用 DNS](preflight/dns.json)、[续期演练](preflight/renewal.json)及三个外部传输层结果：[oracle-dsh](preflight/oracle-dsh.json)、[香港中继](preflight/hk-relay.json)、[host185 查看器用户态](preflight/host185.json)。系统 CA、域名和叶摘要验证均开启；目标固定响应 200，未服务路径 404，常规 Caddy 没有接管站点，短时服务随后关闭。host185 的旧离线浏览器用户态缺省没有 Python CA 包，测试显式提供该外部主机的操作系统公共根，未将服务端叶证书作为根。
- **浏览器层增量**：2026-11-25 17:21 UTC，[独立的 ARM 版 Mozilla Firefox 159](public-health-browser/oracle-dsh-native-firefox.json)在 `oracle-dsh` 的只读用户态，通过真实公网出口看到固定 HTTPS 页面，域名/证书验证全程开启。IP 字面值的负对照是服务端 TLS/SNI 告警，未把它写成证书域名错误。host185 的浏览器直连曾导航超时，其协议层 200 不代表该出口一定流畅。这个测试没有发邀请，也没有启动桌面。见[夹具版本和摘要](public-health-browser/provenance.json)。
- **构建可信度**：[Gecko 补丁与上游审计文件](preflight/reviewed-gecko-inputs.json)在全新对象目录单独核对。当前[固定构建、检查点与离线导出驱动](https://github.com/Facetomyself/ruyitrace/tree/934c67f0cc71f403663e455deb18585e7ee822b5/product/arm64)仅允许正式核对通过后消费本轮包。
