# RuyiDOM · 私有源码组件

[RuyiDOM](https://github.com/Facetomyself/ruyidom) 为 Linux 提供离线 HTML/DOM 脚本执行与显式浏览器导航。`native` 在官方 Firefox 136.0 的 xpcshell 中执行；`browser` 保留同一可信脚本宿主，用 BiDi 驱动独立的内容浏览器。脚本宿主与内容引擎分别固定、分别验收，见[平台组件关系](../../docs/01-architecture.md#下游先选依赖再选证据)。

## 取用源码

| 字段 | 值 |
| --- | --- |
| 平台一级路径 | `submodules/ruyidom` |
| 上游组件仓 | [Facetomyself/ruyidom.git](https://github.com/Facetomyself/ruyidom.git)（private，读取需单独授权） |
| 维护分支 | `main` |
| 首次接入 | 沿用 runtime 已有的直接 gitlink，即正式 `v0.3.1^{commit}` = [`b57891fb9348842e22bbc9395c3db810c0c569fc`](https://github.com/Facetomyself/ruyidom/tree/b57891fb9348842e22bbc9395c3db810c0c569fc)。它是剥离附注标签后的提交，区别于标签对象或后续 `main` HEAD。 |

具备私仓读取权限后，从平台根目录按当前父仓记录取用并核对：

```bash
git -c submodule.recurse=false submodule update --init --checkout -- submodules/ruyidom
git ls-tree HEAD -- submodules/ruyidom
test "$(git -C submodules/ruyidom rev-parse HEAD)" = "$(git rev-parse HEAD:submodules/ruyidom)"
```

[源码 pin](../../PINS.md#ruyidom-source)与[接入决策](../../docs/adr/0005-ruyidom-gitlink.md)区分平台记录、runtime 同步和组件自有维护。匿名 `--public` 仍只取 RuyiHttp、ruyi-mcp、公开 RuyiJS。

## 发行、在用宿主与恢复

| 要核对什么 | 入口与边界 |
| --- | --- |
| v0.3.1 发行 | [正式标签](https://github.com/Facetomyself/ruyidom/releases/tag/v0.3.1) · [可移植性手册](https://github.com/Facetomyself/ruyidom/blob/b57891fb9348842e22bbc9395c3db810c0c569fc/docs/PORTABILITY.md) · [已入库验收回执](../../artifacts/receipts/ruyidom-source-portability-v0.3.1.json)。amd64 完整源码版 Docker 与裸 Jammy ARM64 专用包分别验收。 |
| 在用 ARM64 宿主 | [已入库宿主读回](../../artifacts/receipts/ruyijs-linux-aarch64-product-r433/independent-live.json)记录 `oracle-reverse-dev` 使用 `v0.3.0-host1` 及原 Noble 镜像；接入源码 pin 保持现用版本与 Firefox 136.0 可信脚本宿主原样。 |
| 历史恢复 | [v0.3.0 原发行](../../artifacts/receipts/ruyidom-arm64-source-v0.3.0.json)与[第二台 ARM64 冷恢复](../../artifacts/receipts/ruyidom-arm64-v0.3-cold-restore.json)各自保留；冷恢复证据只覆盖对应归档和已记录的验证范围。 |

组件仍在私仓独立维护、构建与发版。平台只记录源码指针和可公开回执；供应商框架仍为 `not-in-git`，发行制品和恢复材料仍从各自受控位置取用。详见[版本与交付说明](../../docs/14-source-handoff.md#ruyidom-独立源码交接)和[平台侧变更记录](CHANGELOG.md)。
