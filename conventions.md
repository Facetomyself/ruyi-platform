# 文档规范（conventions）

适用本仓全部 `.md` / `.yaml`。

---

## 1. 唯一权威原则

一条结论只能写在**一个**文件里。

| 结论类型 | 唯一位置 |
| --- | --- |
| 跨项目架构、关联、ABI | `docs/01-architecture.md` |
| 源码从哪来 | `docs/02-source-recovery.md` |
| 平台移植步骤 | `docs/03-linux-port.md` |
| 缺口、矛盾、待决策 | `docs/04-risks-and-gaps.md` |
| 反编译方法 | `docs/05-reverse-analysis.md` |
| 单项目结构 / 构建 / 测试 | `projects/<name>/` |
| 版本号、hash | `PINS.md` |
| 状态机 | `STATUS.yaml` |

其他文件需要这些内容时，**写链接，不复制**。

---

## 2. 每条结论必须可复现

写数字、写版本、写「可用」「不可用」，必须紧跟一条能跑的命令。

```markdown
`libnecko_core.so` 要求 glibc 2.38。

    objdump -T native/linux_x86_64/libnecko_core.so | grep -o 'GLIBC_[0-9.]*' | sort -uV | tail -1
```

反例（禁止）：

```markdown
`libnecko_core.so` 要求较新的 glibc。      ← 没有具体值，没有命令
```

---

## 3. 未知项必须显式标记

三档，不许留空，不许猜：

| 标记 | 含义 | 何时用 |
| --- | --- | --- |
| `Unknown` | 不知道，也没计划马上查 | 外部信息缺失 |
| `To be confirmed` | 有线索，待验证 | 反编译中、待实测 |
| `Not yet documented` | 已确认存在，但还没写 | 有实物没整理 |

反编译进行中的模块**必须**标 `To be confirmed` 并附进度（例如「3/74 开关定位完成」）。

---

## 4. 三元组可追溯

任何二进制、任何构建产物，必须能回答三个问题：

1. **Firefox commit** 是什么
2. **ff-ruyijs commit** 是什么
3. **产物 sha256** 是什么

缺一个就是不可追溯，必须标 `Unknown` 并列入 `docs/04-risks-and-gaps.md`。

已知实例：

| 产物 | Firefox | ff-ruyijs | sha256 |
| --- | --- | --- | --- |
| `+inner.492ee47` | `9a2dc53c`（SOURCE_NOTICE） | Unknown | `a7be9c4a…` |
| `+inner.20261101191032` | Unknown | `aa255fbb`（base_commit，但 working_tree 不干净） | `e3243d9b…` |

---

## 5. 二进制不入 git

| 类型 | 入库 | 例外条件 |
| --- | --- | --- |
| 原生库 `.so/.dll/.dylib` | ✅ | 唯一例外，见下 |
| wheel / zip / 安装包 | ❌ | 无 |
| 反编译产物（`.idb`、dump、`.asm`） | ❌ | 无，可再生 |
| Firefox 源码 | ❌ | 无，靠 submodule |
| 测试样本（真实 trace 的 jsonl） | ❌ | 脱敏后且 < 100 KB 可考虑 |

### 原生库入库的额外规则

1. 每个平台目录**只允许一份**，不允许 `libnecko_core.so.131` / `.132` 并存。
2. 换代必须**整目录替换**，并同时更新 `PINS.md` 与 `STATUS.yaml`。
3. 库里必须带 `SHA256SUMS` 与 `provenance.json`（记录来源 wheel 的 sha256）。
4. 新增平台前先在 `docs/03-linux-port.md` 记录必要性，不得先斩后奏。

---

## 6. 修正必须留痕

被推翻的判断**不删除**，改为：

```markdown
### ~~A1 · 原判断~~ → 已降级为 B 级

**初版误判**。<证据>

- 原结论：...
- 更正后：...
- 原因：...
```

并在 `docs/04-risks-and-gaps.md` 末尾的「更正记录」表里加一行。

**不允许**静默修改一个已经发布的结论。

---

## 7. 路径与命令

- 文档正文里的路径用**相对仓库根**（`docs/03-linux-port.md`、`submodules/ruyihttp/native/`）。
- 只有可执行命令块里才用绝对路径（`/var/lib/dsh/Ruyi/...`），且必须能直接复制运行。
- 本地工作区约定：`/var/lib/dsh/Ruyi/` 是母目录，本仓是 `/var/lib/dsh/Ruyi/ruyi-platform/`。

---

## 8. Markdown 约定

| 元素 | 规则 |
| --- | --- |
| 文件命名 | 小写 + 连字符，数字前缀表示顺序（`01-architecture.md`） |
| 一级标题 | 每文件仅一个，与文件名语义一致 |
| 表格 | 用于矩阵、清单；不用于长段落 |
| 代码块 | 必须标语言；shell 用 `bash`，占位符用 `[占位符]` 前缀 |
| 内部链接 | 相对路径，且必须能解析（有校验脚本） |

链接校验：

```bash
python3 scripts/verify-links.py
```

---

## 9. CHANGELOG 格式

`projects/<name>/CHANGELOG.md`，新条目在最上：

```markdown
## YYYY-MM-DD — <一句话标题>

- 改了什么
- 为什么改（发现什么问题）
- 校验方式（跑了什么命令、结果如何）
```

---

## 10. STATUS.yaml 契约

机器可读状态，字段固定：

```yaml
generated_at: "YYYY-MM-DDTHH:MM:SS+08:00"
projects:
  <name>:
    source: complete | partial | missing
    build: linux | windows | macos | none
    tests: <通过数>/<总数> | none
    phase: <当前阶段>
    blocked_by: [<阻塞项 id>]
```

`blocked_by` 引用 `docs/04-risks-and-gaps.md` 的条目编号（如 `A2`、`L4`）。

---

## 11. 提交规范

```
docs(<area>): <祈使句摘要>

<为什么这文档是旧的 / 新增了什么结论>
```

`area` 取值：`architecture` / `recovery` / `linux` / `risks` / `reverse` / `pins` / `status` / `project:<name>`

示例：

```
docs(linux): 更正 ruyijs Python 层为上游已实现，工作量从重写降为合入

初版判断 _pipe.py 是 Windows 独占需重写 127 行。复查 ff-ruyijs 0.4.1
发现上游 _pipe.py 已 208 行且含 AF_UNIX 分支，内部 wheel 只是旧快照。
同步更新 01-architecture、02-source-recovery、03-linux-port、04-risks。
```

---

## 12. 提交前自检

```bash
./scripts/verify-pins.sh           # pin 一致性
python3 scripts/verify-manifests.py # 发布物 hash 与记录一致
python3 scripts/verify-links.py     # 内部链接可解析
git diff --cached | grep -Ei 'token|secret|password|BEGIN .*PRIVATE'   # 必须无输出
```

四条全过才能 commit。
