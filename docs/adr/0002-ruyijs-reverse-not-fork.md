# ADR 0002 · ruyijs 内部版走反编译还原，不基于 ff-ruyijs fork

- 状态：已接受
- 日期：2026-11-19
- 决策者：项目主体维护者

## 背景

内部 wheel `ruyijs 0.2.2+inner.*` 的 Python 层（19 文件，1605 行）是明文，但原生壳 `dist/js.exe`（49.5 MB）只有二进制。

`Facetomyself/ff-ruyijs` 是公开 fork，其 `python/ruyijs/` 恰好**已经支持 macOS arm64 与 Linux x86_64**（`_pipe.py` 208 行含 AF_UNIX 分支等）。

于是产生一个诱人选项：直接用 fork 的代码当内部版基线。

## 候选方案

### A. 以 ff-ruyijs 为基重建（否决）

把 fork 的 `python/ruyijs/` 4 个跨平台文件覆盖进内部 wheel。

### B. 独立反编译还原（选中）

内部产物自成一个还原目标，fork 只作语义对照。

## 决策

**选 B。**

## 理由

| # | 理由 |
| --- | --- |
| 1 | fork 是 **public**，内部功能不得进入。用它当基线会把内部差异混进公开仓库 |
| 2 | 两者 firefox commit 不同：内部 `9a2dc53c`，fork 子模块 `2887d9de`，行为会漂移 |
| 3 | 内部 wheel 的 `build-identity.json` 记录 `working_tree_changes: true`，说明有未提交改动，fork 里没有 |
| 4 | 内部版删了 `Engine`、删了 26 个 examples、加了 `ruyijs_client.dll`，与 fork 结构不同 |
| 5 | 直接覆盖会让人误以为「内部版 = 上游 0.4.1 + 补丁」，掩盖反编译的必要性 |

## 后果

### 正面

- 内部版与公开版边界清晰，PR 回流路径干净
- 反编译产出可验证（2038 条源文件 sha256 作 ground truth）
- 内部功能不会因为「同步上游」被意外泄露

### 负面

- 反编译 `js.exe` 是本项目最重的两块工作之一（另一块是 domtrace）
- 短期内 Linux 上跑不起来内部版

### 缓解

- 优先级收敛到 P0–P2（eval / set / expose / load_page / navigate + 管道协议 + 指纹配置）
- fork 作参照可显著降低「不知道该怎么实现」的成本
- 对照结论必须标注「参照，未采用」或「与二进制一致，采用」

## 硬规则（写入 docs/06-ruyijs-inner.md §0）

| 规则 | 内容 |
| --- | --- |
| R1 | `ff-ruyijs` 不承载内部功能 |
| R2 | `ruyijs-inner` 代码来自反编译，不从 fork 复制 |
| R3 | 对照结论必须标注采用与否 |
| R4 | 能力回流上游走 PR 单向流出，不回灌 |

## 关联

- `docs/06-ruyijs-inner.md`
- `docs/03-linux-port.md` L2
- `PINS.md` §3
