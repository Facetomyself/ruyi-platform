# artifacts — 发布物与反编译产物

## 规则

| 目录 | 入库 | 内容 |
| --- | --- | --- |
| `manifests/` | ✅ | 每个发布物的 yaml 记录（hash、来源、溯源三元组） |
| `binaries/` | ❌ gitignore | 本地存放待分析的二进制（wheel / zip / exe / dll） |
| `analysis/` | ❌ gitignore | 反编译中间产物（锚点 json、dump、反汇编片段） |

**二进制不入 git**（例外：submodule 里的原生库，见 `conventions.md` §5）。

## manifests 一览

| 文件 | 对象 |
| --- | --- |
| `ruyijs-inner-492ee47.yaml` | wheel `0.2.2+inner.492ee47`（含 Engine） |
| `ruyijs-inner-1011.yaml` | wheel `0.2.2+inner.20261101191032`（RuyiTrace 自带） |
| `ruyitrace-3.5.0-win64.yaml` | RuyiTrace 3.5.0 包 |

## 本地放置约定

```bash
# 待分析的二进制放这里（gitignore）
mkdir -p artifacts/binaries/{ruyijs,ruyitrace}
cp /path/to/ruyijs.whl        artifacts/binaries/ruyijs/
cp /path/to/RuyiTrace-3.5.0-win64.zip artifacts/binaries/ruyitrace/

# 反编译输出也放这里（gitignore）
mkdir -p artifacts/analysis/{ruyijs,domtrace}
```

校验：

```bash
python3 scripts/verify-manifests.py
```
