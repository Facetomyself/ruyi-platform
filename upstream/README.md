# upstream — 只读参考（gitignore）

本目录的代码**不入本仓历史**，只记录 pin。

## 用途

| 目录 | 用途 |
| --- | --- |
| `ff-ruyijs/` | ① 向 `cutetailbud/ff-ruyijs` 提 PR；② 反编译内部版时的**语义对照物** |
| `firefox/` | Firefox 159 源码树（数十 GB），只在需要重编内核时拉 |

## 纪律

**`ff-ruyijs` 不是内部基线。** 见 `docs/06-ruyijs-inner.md` §0 与 `docs/adr/0002`。

| 允许 | 禁止 |
| --- | --- |
| 读它的 `src/` 形成反编译假设 | 把它的代码拷进 `ruyijs-inner` |
| 读它的 `native/` 理解 necko ABI 实现 | 因为「上游这么写」就认定内部版也这么写 |
| 向上游提 PR | 把内部改动提交到 fork |

## 拉取

```bash
cd upstream
git clone https://github.com/Facetomyself/ff-ruyijs ff-ruyijs
cd ff-ruyijs
git checkout 3501a90          # 见 PINS.md §3

# firefox 子模块（数十 GB，按需）
git submodule update --init --depth 1 firefox
```

## 版本

以 `PINS.md` §1、§3 为准。本目录的 commit 与 `PINS.md` 不符时，以 `PINS.md` 为准并更新 README。
