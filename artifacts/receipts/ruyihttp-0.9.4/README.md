# RuyiHttp 0.9.4：H3-over-MASQUE / glibc 2.31

[产品提交 74953f7](https://github.com/Facetomyself/ruyihttp/commit/74953f70e87f5935a9ce4410c639727d26ea323e) · [五平台发行格式 wheel](https://github.com/Facetomyself/ruyihttp/actions/runs/45810139410) · [逐项回执与 SHA-256](qualification.json) · [独立 ARM64 主机复验](independent-arm-glibc235.json)。`v0.9.3` 的 GitHub Release 和旧 wheel 均未改写。

**正式发布晚于上述 CI 资格验收。** [GitHub Release v0.9.4](https://github.com/Facetomyself/ruyihttp/releases/tag/v0.9.4) 于 2026-11-26 20:10（北京时间）发布。[发布回执](publication.json)记录 8 项正式附件的匿名回读；公开 ZIP 另有分发说明，五个 wheel 和完整资格 JSON 与已验 CI 工件逐字节相同。2026-11-27 复核 GitHub 的附件 ID、字节数、摘要及本地副本；回放时可取公开附件并运行 `sha256sum -c SHA256SUMS`。

- **路径**：外层 aioquic H3 与代理建立 RFC 9298 CONNECT-UDP，内层是原生 NSS / Neqo 与实际 UDP 源站的 HTTP/3。每个 wheel 的 CPython 3.10 和 3.14 分别通过主夹具与固定版本 `masque-go / quic-go` 两个独立对端；对照客户端、源站、代理三方，核对专用 UDP 出口、正文摘要、请求次数、并发、取消、拒绝/错证书、IPv6、自定义模板和重定向。外层不被冒称为 Firefox 指纹。
- **Linux**：两种架构各自重编 14 个 ELF，最高 glibc 符号需求 `GLIBC_2.30`；`auditwheel` 和实际运行的发行下限为 **glibc 2.31**。[x86_64 原生构建](https://github.com/Facetomyself/ruyihttp/actions/runs/45793633435) / [独立最低系统](https://github.com/Facetomyself/ruyihttp/actions/runs/45796429837)；[AArch64 原生构建](https://github.com/Facetomyself/ruyihttp/actions/runs/45792538631) / [独立最低系统](https://github.com/Facetomyself/ruyihttp/actions/runs/45796424436)。最终矩阵在对应 CPU 的 Debian 11/glibc 2.31 用户态再正常安装**同一个最终 wheel**，在两个 Python 端点核对全部原生哈希/加载器、直接协议及经代理 H3，无外网运行。原 v0.9.3 wheel 的 pip 拒收与现代系统原地升级是两项不同的检验。
- **范围**：单跳、外层 HTTP/3 + QUIC DATAGRAM。HTTP/2 外层、仅 capsule 代理、CONNECT-IP 或多跳 MASQUE 均未列为该版本能力。Windows 继续使用原上游六个 DLL、macOS 保留 Intel 15.0 / ARM64 26.0 的部署下限。源站 Firefox 159/160/161 的同平台对照和旧双跳 TCP 回归另行保留。
- **直接传输趋势**：[成对运行](https://github.com/Facetomyself/ruyihttp/actions/runs/45810150980)分别从 0.9.4 产品提交和固定 v0.9.3 提交打包，是趋势参考，并非再次分发的最终 wheel。32/32 个旁路 H2 小响应完成，未消费大流的预算为 655,360 字节；1 MiB H3 上传使用正文 ABI v1。此基准并非 MASQUE 的公网吞吐测试。

本页索引对应完整交付 `qualification.json` SHA-256 `7b05ecd08a3019555367956725ab646270eda0c6546b954d21ea2db085e3f5ce`，五平台 ZIP SHA-256 `c36913a1e3c152c07bf5ad028f1a97e7a6b851bc0be7385d1aed4d1d6079b111`。链接和记录按实际 Actions run / attempt / artifact ID 固定。原始十个 ZIP 已独立按 Actions 公布的 SHA-256 复核并归档。
