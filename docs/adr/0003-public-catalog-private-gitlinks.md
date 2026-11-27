# ADR 0003 · 公开目录与私有组件的权限边界

- 状态：已接受。2026-11-27 09:44（北京时间），现有 `Facetomyself/ruyi-platform` 原地由 private 改为 public；四个 gitlink 与各组件仓权限保持原样。
- 核对：切换后，GitHub 管理接口与匿名接口均返回父仓 `public`。两个公开组件匿名返回 200；两个私有子模块及独立的 RuyiDOM 匿名返回 404，管理接口仍标记为 `private`。

## 公开父仓可以挂私有子仓吗？

可以。父仓树中模式为 `160000` 的条目是 **子仓的固定提交号**。[模块配置](../../.gitmodules)提供路径和获取地址。两者都随父仓可见，但子仓有自己的 Git 对象、提交历史和访问控制。知道 SHA 或能克隆父仓的人，仍需对子仓单独具备读取权限才可取得该提交。[Git 子模块规范](https://git-scm.com/docs/gitsubmodules#_description)

| 使用者 | 能读什么 | 在克隆好的父仓中怎么做 |
|---|---|---|
| 只读目录的人 | 父仓文件、可见历史、模块路径、URL 和 SHA | 普通 clone 后运行 `bash scripts/verify-pins.sh --catalog`，无需拉子仓 |
| 只用公开组件的人 | 上述内容，以及公开的 HTTP 与 MCP 源码 | `git submodule update --init --checkout -- submodules/ruyihttp submodules/ruyi-mcp` |
| 内部维护者 | 权限覆盖的私仓内容；内部原件仍单独分发 | `git submodule update --init --recursive`，再按[复现手册](../../REPRODUCE.md)运行仓内或完整验收 |

`ruyi-platform` 可匿名普通 clone。公开读者可继续检出 RuyiHttp 和 ruyi-mcp；对全部子模块使用 `--recurse-submodules` 会在需要私仓权限的步骤返回失败。RuyiJS 内部版与 RuyiTrace 仍是私有子模块，RuyiDOM 仍是独立私仓。

## 候选方案与取舍

| 方案 | 适用条件 | 对本项目的结论 |
|---|---|---|
| 将当前平台仓原地转 public | 父仓文件、可见历史和已登记的组件元数据一起公开 | **已采用。** 保留原有仓名与历史，子仓权限未变。切换前登记的旧制品领取入口查无有效记录。 |
| 新建干净历史的公开目录；保留内部平台仓 | 希望只公开选定文件，并隐藏原有父仓历史或私有组件的名称和版本节奏 | 09:18 提议曾推荐此方案；维护者随后选定原地公开，未新建镜像仓。 |

CI 也按受众分开：公开贡献运行目录校验与公开组件的测试；从受保护分支或私有 CI 获取完整子仓，读取凭据限已选仓库、只读、短时。公开 PR 提供的代码不得在持有私仓访问权限的作业中执行。不要把私仓源码、构建目录或内部回执上传为公开产物。[GitHub Actions 跨仓检出说明](https://github.com/actions/checkout)

## 本次变更与复核

1. 2026-11-27 切换前复核了远端 4 个分支和 1 个标签的可达历史；对提交内容和其中可解读的归档做凭据特征筛查，无高置信命中。父仓当时没有 issue、PR、Release、Actions 运行或 Actions 制品。这是切换时的观察，而非对未来提交的保证。[GitHub 可见性说明](https://docs.github.com/en/repositories/managing-your-repositorys-settings-and-features/managing-repository-settings/setting-repository-visibility)
2. 切换后，在无 Git 凭据的空目录中，从 GitHub 通过 HTTPS 实际克隆父仓。`bash scripts/verify-pins.sh --catalog` 通过；按路径初始化 HTTP、MCP 后，两者均停在登记的提交，私有子模块保持未初始化。
3. 后续提交按公开材料审查。私仓源码、内部原件、有效领取码和访问凭据只放在各自受限的位置；GitHub 上的父仓权限与私仓权限分别管理。

只读查看当前父仓确实跟踪什么：

```bash
git ls-tree HEAD:submodules
git config --file .gitmodules --get-regexp '^submodule\..*\.(path|url)$'
git ls-files -- artifacts/receipts artifacts/manifests
```
