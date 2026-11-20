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

按 `conventions.md` §5，二进制不入 git。需要时按上方 sha256 校验。
