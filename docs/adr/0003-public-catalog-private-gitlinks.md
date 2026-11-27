# ADR 0003 · 公开目录与私有组件的权限边界

- 状态：提议；本次维护仅更新文档与本地校验，现有仓库维持原可见性。
- 核对：2026-11-27 09:18（Asia/Shanghai），以 GitHub 仓库接口及匿名读取对照为准。

## 公开父仓可以挂私有子仓吗？

可以。父仓树中模式为 `160000` 的条目是 **子仓的固定提交号**。[模块配置](../../.gitmodules)提供路径和获取地址。两者都随父仓可见，但子仓有自己的 Git 对象、提交历史和访问控制。知道 SHA 或能克隆父仓的人，仍需对子仓单独具备读取权限才可取得该提交。[Git 子模块规范](https://git-scm.com/docs/gitsubmodules#_description)

| 使用者 | 能读什么 | 在克隆好的父仓中怎么做 |
|---|---|---|
| 只读目录的人 | 父仓文件、可见历史、模块路径、URL 和 SHA | 普通 clone 后运行 `bash scripts/verify-pins.sh --catalog`，无需拉子仓 |
| 只用公开组件的人 | 上述内容，以及公开的 HTTP 与 MCP 源码 | `git submodule update --init --checkout -- submodules/ruyihttp submodules/ruyi-mcp` |
| 内部维护者 | 权限覆盖的私仓内容；内部原件仍单独分发 | `git submodule update --init --recursive`，再按[复现手册](../../REPRODUCE.md)运行仓内或完整验收 |

从公开父仓直接用 `--recurse-submodules` 会尝试私仓；缺权限时子模块步骤返回失败，这不影响已取得的父仓，也不会把私仓变为公开。当前 `ruyi-platform` 本身是私有的，外部使用者今天可直接克隆两个公开组件。RuyiDOM 是独立私仓，未挂平台 gitlink。

## 候选方案与取舍

| 方案 | 适用条件 | 对本项目的结论 |
|---|---|---|
| 将当前平台仓原地转 public | 父仓的全部可见历史、附件、记录和组件元数据都允许对外分发 | 暂缓。本仓除指针外还跟踪原始验收回执、主机/部署细节、逆向分析及带参数的历史制品下载入口；仅清理最新文件不会清除旧提交。 |
| 新建干净历史的公开目录；保留内部平台仓 | 希望公开组件关系、使用文档和公开制品，也希望保留内部证据与研发历史 | **建议。** 仅从许可公开的文件清单发布；公开目录先列 HTTP、MCP 及正式公开 Release。私仓名称、URL 与更新到哪个提交都允许披露时才加入其 gitlink；若名称或版本节奏本身需保密，对应映射只放内部平台仓。 |

CI 也按受众分开：公开贡献运行目录校验与公开组件的测试；从受保护分支或私有 CI 获取完整子仓，读取凭据限已选仓库、只读、短时。公开 PR 提供的代码不得在持有私仓访问权限的作业中执行。不要把私仓源码、构建目录或内部回执上传为公开产物。[GitHub Actions 跨仓检出说明](https://github.com/actions/checkout)

## 预备公开时如何验收

1. 私有父仓内先选定允许分发的文档、模块名称、地址、版本和成品。原始日志、主机清单、内部源码摘录和私有工件入口留在私仓；带访问码的旧链接如仍有效，先撤销或轮换。新仓使用独立历史，勿镜像推送旧 refs。
2. 若坚持原地变更，先审查可见分支/标签及其历史、Release 附件、issue/PR 及其附件，以及 Actions 日志/制品。GitHub 说明转公开后 **Actions 历史和日志也会公开**；再次设回私有也无法收回已产生的外部副本。[GitHub 可见性说明](https://docs.github.com/en/repositories/managing-your-repositorys-settings-and-features/managing-repository-settings/setting-repository-visibility)
3. 发布验证分三次：匿名普通 clone 并验父仓目录；匿名按路径拉公开组件、验证私组件仍受限；内部只读身份单独在干净目录检出全部固定提交。清单校验成功只说明指针一致，不等于组件构建、完整原件验收或公开审批。

只读查看当前父仓确实跟踪什么：

```bash
git ls-tree HEAD:submodules
git config --file .gitmodules --get-regexp '^submodule\..*\.(path|url)$'
git ls-files -- artifacts/receipts artifacts/manifests
```
