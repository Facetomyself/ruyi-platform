# RuyiJS Linux 适配 · 交接摘要

给接手者的一页纸。完整证据在 `STATUS.yaml` 的 `guarded_build` 段与
`artifacts/receipts/`；本文只回答"做到哪了、凭什么相信、还差什么"。

统计时间：**2026-11-25 04:05 +08:00**，对应 156 个台账块，全部带证据哈希。

## 1. 交付了什么

一条**私有、离线、必须显式配置信任**的 Linux x86-64 HTTPS 组件，以 wheel 形式交付。

- 基础轮子 `ruyijs 0.2.2+inner...r356`（对应 Firefox 159 内核产物）+ 伴随轮子 `ruyijs_http1`
- 最新伴随轮子：`0.2.30+inner.r421`
- 走的是**固定 NSS 3.131 的 TLS 1.3**，不是 OpenSSL

能力清单（每项都有端到端回执，不是单元测试推断）：

| 能力 | 回执 |
| --- | --- |
| TLS 1.3 握手、ALPN 协商 | R358 |
| JS `fetch()` 走固定证书 HTTPS | R360 / R361 |
| `navigate()` 走 HTTPS | R365 |
| 叶子 DER 固定值 + 有效期 + SAN 主机名 | R366 / R367 |
| 到调用方锚点的链校验 | R375 / R376 |
| 每根 distrust 截止 | R387 / R388 |
| gzip / deflate | R383 |
| **brotli** | R405 → R407 → R408 |
| **zstd** | R409 → R410 |
| 解压炸弹拒绝（两种新编码） | R414 / R415 |
| h2 被拒绝（不会误发 HTTP/1.1 请求行） | R397 |

## 2. 凭什么相信

三条规矩，缺一条结论就不成立：

1. **每个结论都有仓库内回执**，带证据文件哈希。156/156 块有 `evidence_sha256`，0 处不符，0 个孤儿回执。这一条现在由 `scripts/verify-ledger.py` 强制检查，不再只是声明。
2. **端到端优先于单元测试**。压缩、握手、炸弹都做到了"真实服务端 + 真实链路"，而不只是调用函数。
3. **变异验证**。关键测试都反向检查过：故意破坏一处，确认测试会失败（如把 `h2` 加入可接受列表、放宽 `_LABEL` 规则）。

回归入口：

```
ci/test_linux_tls.py            33 个离线测试
ci/test_linux_tls_handshake.py   4 个端到端测试（需 x86-64 NSS 工具链）
```

## 2.5 现在有两个自检脚本

声明本身也要能被检查，否则它只是文字：

| 脚本 | 检查什么 |
| --- | --- |
| `scripts/verify-ledger.py` | 156 个块的证据存在、哈希相符、仓库副本逐字节一致；70 处次级哈希可追溯；形状非法的摘要直接报错而非跳过 |
| `scripts/verify-claims.py` | 13 项关键能力仍存在于当前源码（解码器、wheel 映射调用、ALPN 守卫、截止、锚点、提交守卫、CRL 未被调用） |

两个都做过变异验证：故意破坏一处，确认会报错。误报也修过——`trust_anchors` 一度被断言在 `tls.py`，实际在 C 层。

`scripts/verify-pins.sh` 串起 18 个脚本，是提交前的门禁。

## 3. 没做什么（不要误读为"做了"）

按影响排序，均已在缺口表登记：

| 缺口 | 状态 |
| --- | --- |
| **默认 Mozilla 根库** | 未启用。信任模型仍是"调用方显式给锚点"，这是产品决策，未擅自更改 |
| **OCSP 吊销** | **已尝试三次，未交付**。响应能被缓存、检查会执行，但 NSS 把 revoked 判成 good，需要被认可的响应签名者。R421 已确认这次尝试没有影响普通链校验 |
| **CRL 吊销** | 本构建 `CERT_CheckCRL` **声明在头文件但未导出**，无法链接 |
| **PKIX / RFC 5280 路径语义** | `CERT_PKIXVerifyCert` 在本构建返回 `PR_NOT_IMPLEMENTED`，用的是 legacy `CERT_VerifyCertNow` |
| **h2 帧与多路复用** | 只有"干净拒绝"，没有 h2 能力 |
| **QUIC / h3** | 未做 |
| **ARM64** | 未做，只有 x86-64 |
| **代理（CONNECT/SOCKS5/PAC）** | 未做 |
| **客户端证书** | 未接线 |

## 4. 接手前必须知道的三个坑

都是我这轮次里真实踩过的，重复率极高：

1. **`dist/include/*` 全是悬空符号链接**，指向 `/build/...`。要用头文件必须去源码树
   （`security/nss/lib`、`modules/brotli/include`、`third_party/zstd/lib`）。
2. **长命令在 `host185` 上跑不完**。构建/测试必须用 `nohup ... &` 后台作业 + 短 SSH 读日志。
   单次 SSH 里的长命令会因链路中断失败，且报错会伪装成别的原因。
3. **头文件声明不等于可链接符号**。`CERT_CheckCRL` 就是例子：头文件写得很清楚，`nm -D` 找不到定义。

## 4.5 收尾状态（2026-11-25 04:10 +08:00）

三个克隆均已推送、工作树干净：

| 仓库 | HEAD |
| --- | --- |
| `ruyijs-inner`（私有源） | `7038dd5` |
| `ruyi-platform`（台账+回执） | `1b368fb` |
| `openclaw-infra`（主机记录） | `e18d1ee` |

收尾时的四项实测：

- `scripts/verify-ledger.py` — 156 块，0 处不符
- `scripts/verify-claims.py` — 13 项能力检查通过
- `scripts/verify-pins.sh` — 18 个脚本，退出码 0
- `ci/test_linux_tls.py` — 33 个离线测试通过（1 个因缺解码库跳过）

**目标未完成。** 压缩编码这条线（gzip/deflate/br/zstd）已完整闭环，但"完整 Linux 适配"仍缺默认根库、OCSP/CRL、PKIX、h2 帧、QUIC、ARM64。按台账实测：`quic_http3` 仍有 51 块排除、`ocsp_crl_revocation` 42 块、`http2_framing` 26 块、`arm64_product` 25 块。

这个结论不会因为轮次用尽而改变。

## 5. 如果要继续

优先级建议：

1. **决定默认根库**（产品决策，卡着"能否访问公网 HTTPS"这一大类能力）
2. OCSP 需要专用响应签名者（带 `id-kp-OCSPSigning`）才能验证通过，属夹具工程
3. h2 帧是下一个最大的功能缺口
4. ARM64 需要另一套工具链，工作量独立

新增回执前请先读 `docs/09-evidence-ledger.md` 的「验证纪律」一节，那里记着两次真实事故的教训。
