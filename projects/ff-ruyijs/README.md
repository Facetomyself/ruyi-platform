# ff-ruyijs · 开源 RuyiJS 维护线

[Facetomyself/ff-ruyijs](https://github.com/Facetomyself/ff-ruyijs) 是 [cutetailbud/ff-ruyijs](https://github.com/cutetailbud/ff-ruyijs) 的公开 fork。平台将它作为**独立源码组件**固定在 `submodules/ff-ruyijs`。fork 自有的产品改动限于性能优化和 macOS/Linux 跨平台兼容；同步上游时保留其现有功能和 Windows 的共用主干。私有内部版另在 `submodules/ruyijs`，有自己的源码、版本与交付；登记公开 fork 不会替换内部运行时或 RuyiHttp 历史构建的 donor。

## 取用

在平台根目录运行；这是只读使用已选源码的路径，不跟踪分支顶端，也不下载嵌套 Firefox：

```bash
git -c submodule.recurse=false submodule update --init --checkout -- submodules/ff-ruyijs
git ls-tree HEAD -- submodules/ff-ruyijs
git -C submodules/ff-ruyijs rev-parse HEAD
git -C submodules/ff-ruyijs ls-tree HEAD -- firefox
```

第一处提交号是平台承诺的 fork 版本；最后一行是该版本构建所用的 Mozilla 源码指针，不是 fork 或内部产品的提交。需要编译时才按 fork 的 [Linux](../../submodules/ff-ruyijs/docs/linux.md)／[macOS](../../submodules/ff-ruyijs/docs/macos.md) 手册准备对应运行环境。平台纳管和目录校验不等于签发 wheel、刷新 PyPI 或在目标机重做基准。

## 谁在哪里维护

实际开发使用 fork 的独立克隆；从平台固定提交取用源码与向 fork 推送分支是两种操作。首次设置并只读核对两个远端：

```bash
git clone --no-recurse-submodules https://github.com/Facetomyself/ff-ruyijs.git
cd ff-ruyijs
git remote add upstream https://github.com/cutetailbud/ff-ruyijs.git
git fetch --no-recurse-submodules upstream main
git rev-list --left-right --count origin/main...upstream/main
```

| 工作 | 归属与验收条件 |
|---|---|
| 吸收上游 | 在 fork 自己的干净克隆操作：`origin` 指自己的 fork，`upstream` 指原项目。从 `origin/main` 建 `sync/<上游SHA>` 并 merge 指定的上游提交；通过受影响平台的检查后，以 fork 内 PR 合回 `main`。 |
| 本地优化与兼容 | 使用一事一分支；性能结论需同机、同配置、固定工作负载的前后样本以及正确性对照。兼容改动记录实际 OS、CPU、运行时、构建与安装命令和结果。共用代码另外标注 Windows 信号；未跑的格子明示未跑，不借用私有版或其他架构的回执。 |
| 向上游发 PR | 从最新 `upstream/main` 另建 `upstream/<topic>`，只挑选可公开的单一补丁；推到 fork，PR 的目标是 **cutetailbud/ff-ruyijs:main**。fork 管理文件、私有来源、制品和机器配置留在各自边界。由维护者提交、上游审合。 |
| 平台升 pin | fork 的变更先合入公开 `main`；再用独立平台提交一并更新 gitlink、[PINS](../../PINS.md#open-ruyijs) 与[账本](../../STATUS.yaml)。登记已吸收上游 SHA、来源和相关 PR，并核对 fork 的内层 Firefox pin。回滚使用新的平台提交恢复上一组已验 SHA；既有发布标签不改写。 |

**经常回送 PR 时**，在 fork 对应 PR 记录上游 PR 链接及状态（待审、已合并、暂缓/关闭）。上游合入后的下一次 `sync` 核对该改动已由上游携带，再清理功能重复的 fork 补丁；上游暂缓时保留原因和兼容性证据，避免在下一次同步中重复提交。

贡献者的具体分支约定、双平台门禁、基准和 PR 模板以 fork 内的[维护规则（中文）](../../submodules/ff-ruyijs/docs/branching.zh-CN.md)／[English](../../submodules/ff-ruyijs/docs/branching.md) 为准；仅浏览 GitHub 可直接看[本次固定版本的中文规则](https://github.com/Facetomyself/ff-ruyijs/blob/f1490a564c4cf4c754e7f99af2ed04ee8b2a12ef/docs/branching.zh-CN.md)。平台项目目录只记录两仓交接，绝不从子模块的 detached HEAD 直接发布。此前把该 fork 当成只读对照的记录，仍只说明那次内部分析，见[历史与当前 pin](../../PINS.md#open-ruyijs)。
