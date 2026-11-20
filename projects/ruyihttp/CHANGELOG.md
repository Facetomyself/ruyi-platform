# RuyiHttp 变更记录

## 2026-11-20 — Linux x86_64 wheel 真机 HTTPS 验收通过

在 Oracle x86_64 主机的 Ubuntu 24.04 容器运行发布格式 wheel，取代先前只有交叉打包和 ABI 检查的状态。见[验收记录](README.md#linux-x86_64-验收记录)。

## 2026-11-20 — 仓库转 public，文档与实测状态对齐

- `Facetomyself/ruyihttp` 可见性由 private 改为 public；四个仓库已跟踪文件与全历史均无凭据
- 重写 `projects/ruyihttp/README.md`：13/19 → **19/19**，四项历史待办标记为已闭合，
  补平台矩阵、构建环境要求与剩余缺口
- 同步 `STATUS.yaml`：新增 `visibility` / `closed_todos` / `build_required_guard`，
  刷新 `generated_at`
- 根 `README.md` 被 `STATUS.yaml` 内容覆盖的错误已修复，恢复为正式仓库说明并补齐
  `docs/12`、`docs/13`、`adr/` 索引
- `scripts/verify-manifests.py` 修复悬空符号链接导致的中断，改为按缺失处理

校验：`verify-pins.sh` 全通过、`verify-links.py` 65 个链接全解析、
`verify-timeline.py` 数字一致、`verify-manifests.py` 3/3、契约测试 19/19。

## 2026-11-19 — 建仓，完成首轮结构与状态梳理

- 新增本项目文档与结构规划
- 状态定级写入 `STATUS.yaml`
- 校验脚本落地（`scripts/verify-*`）
- 未决项登记到 `docs/04-risks-and-gaps.md`
