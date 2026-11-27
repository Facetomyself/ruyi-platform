# upstream — 只读参考（gitignore）

**现行公开 RuyiJS 在 `submodules/ff-ruyijs`。** [项目入口](../projects/ff-ruyijs/README.md)与[开发 pin](../PINS.md#open-ruyijs)记录公开 fork 的开发、上游 PR 和构建。`upstream/` 仅保留历史说明，不是开发检出目录。

## 用途

| 历史目录 | 记录 |
| --- | --- |
| `upstream/ff-ruyijs/` | 过去的只读对照检出；样本身份见 [PINS §3](../PINS.md) |
| `upstream/firefox/` | 过去的独立 Firefox 参考目录；各组件构建按各自手册取固定输入 |

## 纪律

**`ff-ruyijs` 不是内部基线。** 见[内部来源纪律](../docs/06-ruyijs-inner.md#0-三层边界先立规矩)与 [ADR 0002](../docs/adr/0002-ruyijs-reverse-not-fork.md)。

| 允许 | 禁止 |
| --- | --- |
| 读它的 `src/` 形成反编译假设 | 把它的代码拷进 `ruyijs-inner` |
| 读它的 `native/` 理解 necko ABI 实现 | 因为「上游这么写」就认定内部版也这么写 |
| 向上游提 PR | 把内部改动提交到 fork |

## 拉取

从普通 clone 的平台父仓根目录，只检出公开 fork 的一级 gitlink：

```bash
git -c submodule.recurse=false submodule update --init --checkout -- submodules/ff-ruyijs
```

只有需要构建公开 RuyiJS 时，再按 [fork 自己的构建手册入口](../projects/ff-ruyijs/README.md)处理嵌套 Firefox。

## 版本

早期只读镜像（包括旧 `3501a90` 对照样本）、固定 donor、Firefox 构建输入及发行工件各看 [PINS 对应条目](../PINS.md)，不可用[当前公开开发 pin](../PINS.md#open-ruyijs)替换。旧「手动克隆公开 fork 到 `upstream/`」入门流程已由 [ADR 0004](../docs/adr/0004-open-ruyijs-gitlink.md) 覆盖。
