# 临时 TLS 租约：已验证的范围

[发布记录](release.json)将真实读回的独立 sidecar image ID `sha256:28eac74b5455256d4e20b41b7feb18c8371e9f940fee11c05d144ff771b57a22`、[归档与逐层导出验证](edge-export.json)、[原生扩展与文件读回](edge-readback.json)与[固定源码](https://github.com/Facetomyself/ruyitrace/tree/c3723ca5f71e860ed19d1fa1a4305da930dc7428/product/interactive)对齐。归档为 `ruyitrace-public-edge-tls-lease-v1-linux-amd64.docker.tar.gz`，351,919,702 字节，SHA-256 `44c1f62192a851c8e183da31a3b12beff6769ff72495b7a0144016f3f2a731dc`。它不同于[原交互镜像及其空引擎回执](../trace-interactive-r5/README.md)。

2026-11-25 在 host185 的回环地址，验证真实 Firefox → TLS → 邀请兑换 → noVNC/WSS → 另一个真实 Firefox 的桌面。客户端只信任测试 CA，合成测试页与查看者都采用仅回环网络的容器；查看者通过 Unix 字节中继走同一个实际 TLS 监听。首次没有额外输入，1280×720 非空画面已绘制；未认证的资源/授权返回 403，原邀请复用返回 403，已认证浏览器可通过干净的 URL 重连。

| 场景 | 已观测的结果 |
|---|---|
| [主动撤销](final-revoke.json) | 断开活跃桌面，CLI 停止退出 0，三个归属容器、运行目录与监听都消失。 |
| [自然到期](final-expire.json) | 实测 90 秒租约到期，不靠聊天会话触发清理。默认策略为 1200 秒；这条不是完整 20 分钟的现场计时。 |
| [监护进程 SIGKILL](final-worker-loss.json) | systemd 退出后阶段执行收尾；连接关闭，CLI 退出 0，残留为零。 |
| [启动中途失败、跨 boot 清扫](systemd-failure-recovery.json) | 指向未加载镜像时没有发邀请；已创建但未记入 ID 的旧代资源通过命名空间与归属标签收回。这是注入的旧 boot 标记，未重启主机。 |
| [验后宿主清单](final-host.json) | 公网演示保持关闭；无 QA 单元、容器、目录或临时开放规则，两个既有产品镜像 ID 不变，Docker、SSH 和既有反向隧道 active。 |

CI 读取原始回执字节、固定源文件、归档和实测容器 ID，多项必须相符。未在第二台物理机器或实际公网客户网络上进行测试；证书签发、DNS、端口映射及上游接入策略属于独立的部署条件。构建步骤与[运维手册](../../../submodules/ruyitrace/product/interactive/public-demo.md)不会自动开防火墙或发布一个外部地址。
