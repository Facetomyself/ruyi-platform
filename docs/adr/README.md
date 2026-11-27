# ADR 索引

| 编号 | 标题 | 状态 |
| --- | --- | --- |
| [0001](0001-repo-topology.md) | 原始仓库拓扑：单主体仓 + 三 submodule + 上游不挂载 | 已接受；公开 fork 不挂载一项由 [0004](0004-open-ruyijs-gitlink.md) 覆盖 |
| [0002](0002-ruyijs-reverse-not-fork.md) | ruyijs 内部版走反编译还原，不基于 ff-ruyijs fork | 已接受 |
| [0003](0003-public-catalog-private-gitlinks.md) | 现有平台父仓公开，组件仓权限分别保留 | 已接受 |
| [0004](0004-open-ruyijs-gitlink.md) | 公开 RuyiJS fork 作为独立一级 gitlink 接入 | 已接受 |

## 写 ADR 的规则

1. 一个决定一个文件，编号递增。
2. 必须有「候选方案」与「否决理由」，不能只写结论。
3. 状态只能是：`提议` / `已接受` / `已废弃` / `已被 ADR-XXXX 取代`。
4. 决定被推翻时**不删除**，改状态并写「取代关系」。
