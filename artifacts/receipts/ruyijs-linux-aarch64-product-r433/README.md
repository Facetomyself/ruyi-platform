# R433 已正式发布并切换生产

[私有 GitHub Release：linux-arm64-product-r433](https://github.com/Facetomyself/ruyijs-inner/releases/tag/linux-arm64-product-r433) 于 2026-11-26 19:31:32（上海时间）发布，状态为正式发行。独立生产读回时间为当日 19:36:24。应用提交是 `10b6e5a5f2486f7b7d7ec83e3ec9707a8f8d1bb1`，发布 tag 指向打包和部署配方提交 `1ee61b9e368c53da6cb4d37ac8edf4e79001df93`。

| Linux ARM64 wheel | 版本 | 字节数 | SHA-256 |
|---|---|---:|---|
| [ruyijs](https://github.com/Facetomyself/ruyijs-inner/releases/download/linux-arm64-product-r433/ruyijs-0.2.2%2Binner.20261101191032.r433-py3-none-linux_aarch64.whl) | `0.2.2+inner.20261101191032.r433` | 143,356,091 | `43f9bdc7ee7cea17747d1d08fd8f0d275fca5d5ac685af6d98e11834292ba218` |
| [ruyijs-http1](https://github.com/Facetomyself/ruyijs-inner/releases/download/linux-arm64-product-r433/ruyijs_http1-0.2.39%2Binner.r433-py3-none-linux_aarch64.whl) | `0.2.39+inner.r433` | 2,587,660 | `0104110889fa3317e02b308824b8e53a28f79e5723c1ca279a7a078b6a2803cf` |

网络组件精确依赖同批基座，应成对升级。三次原生打包生成相同字节；正式发布后的 11 个资产全部重新下载并匹配校验和。下载的 wheel 在 Ubuntu 24.04 ARM64 / glibc 2.39 / CPython 3.12.3 上再次进行全新基座安装、全新组合安装、从可工作的 R432 升级和卸载 companion 后的基座复验。用的是 wheel 安装的原生 shell，不是宿主挂载的候选文件。

## 正式入口和恢复点

| 角色 | 版本 | 不可变镜像 ID |
|---|---|---|
| 当前完整版 | `r433-host1` | `sha256:5661a38cdf25d80b0df12119ea8e2e8c6881d84f4790e5dd62b57614f9c6d821` |
| 上一完整版 | `r432-host1` | `sha256:82dcd7b11350ccf90dc38805b5c1d10df9e89c59c2c4a67c5b1b2cfedd28602c` |
| 本版纯基座选项 | `r433-base-host1` | `sha256:9476cafeb33264ea9948d8f351db710e0bd8a93d794e2e9a5f16142870a3f2b5` |

```bash
ssh oracle-reverse-dev '/home/ubuntu/.local/bin/ruyijs --version'
ssh oracle-reverse-dev '/home/ubuntu/.local/bin/ruyijs check'
ssh oracle-reverse-dev '/home/ubuntu/.local/bin/ruyijs verify'
```

实际执行了 **R433 → R432 完整版 → R433**，每次均经正式 CLI 校验包版本、镜像 ID、默认 Context 和健康状态。最终 `previous` 为 `r432-host1`。运行保持默认离线、只读根、UID 10001、2 CPU、2 GiB 内存和 192 PIDs，部署切换前后的 13 个监听端点一致，RuyiDOM 入口与别名保持原样。

权限对照通过 **15/15**，Blob/File 快速对照 **8/8**，Window 与独立 Worker 各 **58/58**。13 组原生功能、9 组网络组件检查、HTTPS 正确 pin 返回 200、错误 pin 时对端收到 0 个 HTTP 字节，均在安装态通过。独立 QUIC C ABI 另有三种 H3 身份校验对照；这与 JS 默认路由是两回事。

双镜像归档同主机重载后两种镜像均重新验证；维护机另存的加密副本已解密核对为相同的 525,262,159 字节原始归档。全新空主机冷恢复未在本次演练。参见[安装和回滚手册](https://github.com/Facetomyself/ruyijs-inner/blob/linux-arm64-product-r433/docs/linux-arm64-r433.md)与[部署回执](validation.json)。
