# 三个 Firefox commit 的真实归属（2026-11-19 实地核查）

> 本文更正 `PINS.md` 的基线选择。此前把 `39bfd14c` 定为唯一基线，理由是
> 「domtrace 只在这棵树上验证过」。核查后发现这个理由站不住——**那个 commit 在官方仓库里不存在**。

## 一、核查方法

在 `oracle-reverse-dev`（Ubuntu 24.04 / aarch64）上 sparse clone
`https://github.com/mozilla-firefox/firefox`，然后：

```bash
git ls-remote --tags origin | grep FIREFOX_159
git fetch --depth 1 origin <commit>
git cat-file -t <commit>
```

## 二、结果

| commit | 出处 | 在官方仓库存在? | 是什么 |
| --- | --- | --- | --- |
| `9a2dc53c369c7ae5172018b35988e1d2ffeff402` | ruyijs 内部 wheel `SOURCE_NOTICE.md` | ✅ | **`FIREFOX_159_0_RELEASE`** 官方 tag |
| `2887d9de1f69c0e9776413da80e7ba0d1225dd9b` | ff-ruyijs `.gitmodules` 子模块 pin | ✅ | 官方 `release` 分支上的普通 commit，2026-11-04，「No Bug - Update configs after merge day operations a=release」 |
| `39bfd14cb45c` | RuyiTrace `kernel/application.ini` 的 `SourceStamp` | ❌ **不存在** | 私有 fork 上的 commit（或被改写的值） |

### 官方仓库里 159 相关的 tag

```
FIREFOX_159_0_RELEASE     9a2dc53c369c7ae5172018b35988e1d2ffeff402
FIREFOX_159_0_BUILD1      9a2dc53c369c7ae5172018b35988e1d2ffeff402
FIREFOX_159_0_1_RELEASE   6181e6b5f28a8fbae1d5c3ef6f6626b5a2180213
FIREFOX_159_0_1_BUILD1    6181e6b5f28a8fbae1d5c3ef6f6626b5a2180213
```

`9a2dc53c` 与 `9a2dc53c369c…` 是同一个 commit 的短/长形式。

## 三、这意味着什么

### 1. ruyijs 内部版的溯源是干净的

`SOURCE_NOTICE.md` 写的是 `9a2dc53c`，就是官方 159.0 release。**这一处可信。**

### 2. ff-ruyijs 的 pin 是官方 release 分支上的正常 commit

`2887d9de`（2026-11-04）不是 159，是 `release` 分支上的最新 commit 之一。
ff-ruyijs 跟的是「最新 release 分支」，不是某个固定版本。

### 3. RuyiTrace 的 `39bfd14c` 无法在官方验证

两种可能：

| 可能 | 说明 |
| --- | --- |
| A. 私有 fork | 作者在官方 159 基础上改（加 domtrace 插桩）后建的仓，commit 只在私有仓里 |
| B. 值被改写 | `application.ini` 的 `SourceStamp` 被手动填了一个不对的值 |

无论哪种，**`39bfd14c` 都不能当「官方基线」用**——它指向的东西在公开世界里无法获取。

### 4. domtrace 是私有修改，不是官方功能

官方 `dom/bindings/` 有 323 个文件，grep `domtrace` **零命中**。
官方仓库里没有任何 domtrace 相关目录或文件。

**结论**：domtrace 的 74 个 `MOZ_DOM_*` 开关完全来自私有 fork，官方源码里没有可参照的实现。
这解释了为什么 `docs/05-reverse-analysis.md` 的方案 A（「去官方树找 domtrace」）必然失败。

## 四、对基线的修正建议

`PINS.md` 当前写「以 `39bfd14cb45c` 为唯一基线」。这个决策需要改：

| 用途 | 应该用哪个 commit | 理由 |
| --- | --- | --- |
| **源码分析的基线** | `9a2dc53c`（FIREFOX_159_0_RELEASE） | 官方可取、可验证、是真正的 159.0 |
| 复现 RuyiTrace 内核 | `39bfd14c` | 但它不可获取 → **只能靠反编译** |
| 跟 ff-ruyijs | `2887d9de` | 官方 release 分支上的点，可验证 |

**核心矛盾**：RuyiTrace 的内核基于一个公开世界拿不到的 fork。要做「与 RuyiTrace 一致」的
Linux 版，只能：

1. 从官方 `9a2dc53c` 起，自己实现 domtrace 插桩（等价重建），或
2. 从私有 fork 拿到 patch（需作者提供）

## 五、对 `docs/05-reverse-analysis.md` 方案 A 的结论

方案 A 原文：「取官方源码树找 domtrace，先验证存在性，10 分钟」。

**已验证：不存在。** 方案 A 作废。剩余只有方案 B（反编译）与方案 C（问上游要）。

## 六、复现本文的核查

```bash
# 在任意有网的机器上
git clone --depth 1 --filter=blob:none --sparse \
  https://github.com/mozilla-firefox/firefox ffprobe
cd ffprobe

# 1. 官方 159 tag
git ls-remote --tags origin | grep FIREFOX_159

# 2. 三个 commit 的存在性
for c in 9a2dc53c369c7ae5172018b35988e1d2ffeff402 \
         2887d9de1f69c0e9776413da80e7ba0d1225dd9b \
         39bfd14cb45c; do
  printf '%-42s ' "$c"
  git fetch --depth 1 origin "$c" >/dev/null 2>&1 && echo "存在" || echo "不存在"
done

# 3. domtrace 是否在官方树
git sparse-checkout set dom/bindings
git ls-tree -r --name-only HEAD | grep -ci domtrace   # → 0
```
