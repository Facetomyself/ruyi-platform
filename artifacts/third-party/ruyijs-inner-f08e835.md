# 第三方构建的 ruyijs Linux wheel（对照用，非本仓产物）

由外部构建者提供，2026-11-20 收到。**与我们的 RuyiTrace domtrace 路线无关**，
仅作 ruyijs Linux 运行时的参考样本。

| 项 | 值 |
| --- | --- |
| 文件名 | `ruyijs-0.2.2+inner.f08e835-py3-none-manylinux_2_39_x86_64.whl` |
| 字节 | 63,984,101 |
| sha256 | `8de31db4911f77b544b44f1827cb3cb32ea2335eb3361f9011ea5b9998549ab4` |
| 文件数 | 2072 |
| `dist/js` | 58,303,185 B（SpiderMonkey **160**） |
| WebCrypto | OpenSSL |
| glibc | 2.39 |
| 编译器 | clang 21.1.8 / GCC 13.3.0 |

## 关键结论：**不含 domtrace**

```
nm -C js | grep -ci domtrace   → 0
strings js | grep -c MOZ_DOM   → 0
```

这是标准 ruyijs 的 Linux 构建，不是 RuyiTrace 的内核。

## 与我们的构建对比

| 项 | 这个 wheel | 我们正在构建的 |
| --- | --- | --- |
| SpiderMonkey | 160 | 159（`9a2dc53c`） |
| domtrace | ❌ | ✅ |
| 用途 | ruyijs 运行时 | RuyiTrace 内核 |

## 价值

证明 ruyijs 的 Linux + glibc 2.39 + necko 派生路线是可行的，
可作为将来对齐内部版 Linux 版的参照。

## 样本本体

样本现保存在本工作区的 `artifacts/binaries/ruyijs/ruyijs-0.2.2+inner.f08e835-py3-none-manylinux_2_39_x86_64.whl`，由仓库的忽略规则排除，不进入 Git，也不进入私有版发布产物。

2026-11-22 用 [只读校验脚本](../../scripts/verify-reference-wheel.py) 实际复核：外层 SHA-256 与登记值一致；2,072 个 ZIP 成员都在顶层 `RECORD`，其余 2,071 个成员的 SHA-256 和长度全部匹配。`dist/js` 为原生 x86_64 ELF，SHA-256 `260caccaf87d89b3646f2184d65ea827b08ce7d1231b7fe3daf18cb55441a588`。脚本不解包、不安装、不执行样本。归档校验只证明与入库的参考字节一致，不代表重建或运行验收。

```sh
python3 -B scripts/verify-reference-wheel.py
```

在已有合法副本的其他工作区可传入 wheel 路径，脚本使用相同固定摘要。
