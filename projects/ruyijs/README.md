# RuyiJS（内部版）

仓库：`Facetomyself/ruyijs-inner`（private，**已存在**：2026-11-04 创建，7.4 MB，默认分支 `main`）
挂载：`submodules/ruyijs`
上游参考：`Facetomyself/ff-ruyijs`（public fork，**只作 PR 与对照，不作基线**）

## 是什么

Firefox 159 的 SpiderMonkey + 38 个浏览器子系统的 Python 可编程封装。跑在独立进程里，通过本地帧传输与 Python 通信。

## 三层结构

| 层 | 体积 | 源码状态 |
| --- | --- | --- |
| Python 绑定 `ruyijs/*.py` | 60 KB / 19 文件 | ✅ 明文 |
| `necko` 适配器 `vendor/.../necko/` | 200 KB / 13 文件 | ✅ 明文 |
| 原生壳 `dist/js.exe` | 49.5 MB | ❌ 需反编译 |
| 内嵌 CPython 3.14 | ~15 MB | ✅ 官方产物 |

## 两个已有构建

| 版本 | 大小 | Engine | examples | client.dll |
| --- | --- | --- | --- | --- |
| `0.2.2+inner.492ee47` | 46.0 MB | ✅ | 26 个 | ❌ |
| `0.2.2+inner.20261101191032` | 46.6 MB | ❌ | 0 | ✅ |

记录：`artifacts/manifests/ruyijs-inner-*.yaml`

## 期望目录（ruyijs-inner 建库后）

```
ruyijs-inner/
├── src/                      反编译还原的 C++（2069 文件，按 build-identity 的 2038 条路径）
├── python/ruyijs/            19 个 .py（明文，从 wheel 取）
├── native/                   necko C/C++/Rust
│   ├── necko_tls/            Windows：necko_tls.c 863 / necko_exchange.c 823
│   ├── necko_posix/          Linux：tls.cpp 148 / http1.cpp 144 / socket.cpp 125
│   └── necko_quic/           两平台：lib.rs 1007
├── tests/                    契约断言（见 docs/06 §4）
├── tools/                    构建脚本
└── docs/                     本项目文档
```

## 反编译方案

见 [`../../docs/06-ruyijs-inner.md`](../../docs/06-ruyijs-inner.md)。

**优先级**：P0（eval/set/expose/load_page/navigate）→ P1（管道协议）→ P2（指纹配置）→ P3–P6。

## 当前状态

**语义重建进行中**（不是从 0 开始）。

| 分类 | 数量 |
| --- | ---: |
| identity 总数 | 2038 |
| eol-insensitive 对齐 0.2.1 | 1792 |
| hash_diff | 237（56 条 identity 命中） |
| inner_only | 9（全部语义化） |

最大缺口：`page_storage` / `browsing_context` / `draw` / `css_color_resolve`。

详细进度见 [`reverse-analysis.md`](reverse-analysis.md)。

## Seed 关系（重要）

`ruyijs-inner` 的 seed 是 `ff-ruyijs` **0.2.1**（`c69875b5`），不是当前的 0.4.1（`3501a90`）。

**0.2.1 没有跨平台代码**——`python/ruyijs/_pipe.py` 仍是 Windows 独占的 127 行。0.4.1 的 AF_UNIX 分支（208 行）是后出现的能力，只能作可行性证据，不能作内部版现状依据。

## 与其他项目的关系

- 与 **RuyiHttp** 共享 31 个 C 符号的 necko ABI（见 `docs/01-architecture.md` §1.2）
- 与 **RuyiTrace** 构成 trace 对账闭环：`trace_diff.py` 比对两者行为差异
