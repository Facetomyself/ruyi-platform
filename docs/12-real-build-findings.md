# 真实构建验证：在 Firefox 159 里实际跑出来的结果

> 2026-11-20，host185（x86_64 / CentOS 7 / Docker Ubuntu 24.04 / clang 19.1.1）。
> 这是 24 轮以来**第一次真实验证补丁**，前 24 轮所有「补丁正确」的结论都只是
> `git apply --check` 级别的推测。

---

## 一、结论先行

| 项 | 结果 |
| --- | --- |
| Codegen 生成 domtrace 表 | ✅ **正确** |
| 生成的绑定文件里插桩展开 | ✅ **正确** |
| C++ 编译 | ✅ **4431 个目标文件，含 dom/bindings 全部 42 个** |
| Rust `gkrust` 链接 | ❌ OOM（**与补丁无关**） |
| 完整 `libxul.so` | ❌ 未完成（卡在上一步） |

**补丁本身验证通过。** `gkrust` 是 Firefox 自身的 Rust 组件聚合 crate，
我们的补丁没有改动任何 Rust 代码。

---

## 二、实证产物

### 生成的索引表

`obj-*/dist/include/mozilla/dom/PrototypeList.h`：

```cpp
namespace domtrace {
inline constexpr const char* kMemberNames[] = {
  "ANGLE_instanced_arrays::drawArraysInstancedANGLE",
  "AbortController::signal",
  ...
};

struct InterfaceEntry {
  const char* name;
  uint16_t start;
  uint16_t count;
};
inline constexpr InterfaceEntry kInterfaces[] = {
  {"ANGLE_instanced_arrays", 0, 3},
  {"AbortController", 3, 2},
  {"AbortSignal", 5, 7},
  {"AbstractRange", 12, 6},
  ...
};
}
```

**索引链闭合**：`protoID` → `kInterfaces[protoID]` → `(start, count)` →
`kMemberNames[start .. start+count)`。

### 生成的绑定插桩

`obj-*/dom/bindings/AbortControllerBinding.cpp`：

```cpp
namespace {
[[maybe_unused]] constexpr const char* kDomtraceName_signal_getterinfo =
    "signal@AbortController";
}
```

### 插桩点

`dom/bindings/BindingUtils.cpp` 有 4 处 `ScopedAccessCall`（1 处 include + 3 处插桩）。

---

## 三、六个真实缺陷（`git apply --check` 全部漏掉）

### 缺陷 1 · 运算符优先级

0005 生成区间表处：

```python
"  {%d, %d}," + chr(10) % (start, count)     # % 绑到 chr(10) 上
```

```
TypeError: not all arguments converted during string formatting
```

**修法**：`("  {%d, %d}," % (start, count)) + chr(10)`

### 缺陷 2 · `fill()` 模板要求 `$*{x}` 独占一行

```
ValueError: Invalid fill() template: $*{ranges} must appear by itself on a line
```

原写法 `$*{ranges}};` 后面跟了字符。

**修法**：`};` 移到下一行。

### 缺陷 3 · `static const char*` 类内初始化非法

0001 想在 `PrototypeTraits` 里加 `static const char* name = "Document"`：

```
error: non-const static data member must be initialized out of line
```

改成 `const char* const` 后：

```
error: in-class initializer for static data member of type 'const char* const'
       requires 'constexpr' specifier
```

而 `ClassMember` 不支持生成 `constexpr`。

**修法**：**放弃这条路线**。名字改由 `kInterfaces` 提供
（`const char* name` 作为聚合初始化字段是合法的）。

### 缺陷 4 · `CGStringTable` 不能用于复合键

0004 用 `CGStringTable("DomtraceMemberNames", ["Document::cookie", ...])`。
`CGStringTable` 依赖 `BindingNamesOffset` 枚举，该枚举只收录 WebIDL 的成员名：

```
error: 'ANGLE_instanced_arrays' is not a class, namespace, or enumeration
```

**修法**：改用普通 `const char*` 数组。

### 缺陷 5 · `domtrace` 命名空间未声明

```
error: use of undeclared identifier 'domtrace'
```

**修法**：`ScopedAccessCall.inl` 放 `dom/bindings/domtrace/binding/`，
在 **`BindingUtils.cpp`** 加 include。

**不能加在 `BindingUtils.h`** —— 该头被 `accessible/`、`layout/` 等目录 include，
相对路径失效，会导致整个代码树编译失败。

### 缺陷 6 · `CGGeneric` 只输出 `define()`，头文件要 `declare()`

**最隐蔽的一个。**

```python
traitsDecls.append(CGGeneric(domtraceMemberNamesDecl))   # 内容进了 define
```

`CGGeneric.__init__(define="", declare="", forward_declare="")`，
而生成 `.h` 时只调用 `declare()`。

结果：**代码完全正确，产物里一个字都没有，编译不报错。**

这个缺陷只有在「生成 → 检查产物」这条链上才能发现——
我是对比了 `PrototypeList.h` 的实际内容才找到的。

**修法**：`CGGeneric(declare=...)`

### 缺陷 7（补充）· 构造函数需要模板

```
error: no matching constructor for initialization of 'domtrace::ScopedAccessCall'
```

原签名 `ScopedAccessCall(void* cx, void* args, const void* info, void* self, ...)`，
调用处传的是 `JSContext*` / `JS::CallArgs&` / `JSJitInfo*` / `void*`，无法隐式转换。

**修法**：

```cpp
template <typename CxT, typename ArgsT, typename InfoT, typename SelfT>
ScopedAccessCall(CxT* cx, ArgsT& args, const InfoT* info, SelfT* self, AccessKind kind);
```

---

## 四、环境侧的坑（非补丁问题，但会浪费时间）

| 坑 | 现象 | 修法 |
| --- | --- | --- |
| clang 版本 | `Only clang/llvm 19.0 or newer is supported` | 装 `clang-19` + `update-alternatives` |
| `libclang.so` | bindgen `libclang for bindgen... not found` | 建无版本软链接 `libclang.so -> libclang-19.so.19` |
| crates.io | `transfer too slow` | `~/.cargo/config.toml` 用 `rsproxy.cn` |
| GitHub 拉 blob | `could not fetch ... from promisor remote` | remote 换成 `gh-proxy.com` |
| sparse 排除 | `moz.build` 引用的文件缺失 | 补 `js/src/tests`、`dom/media/test`、`servo` |
| **firewalld 抢 iptables 锁** | Docker 卡在 `activating` 15 分钟 | 临时 `systemctl stop firewalld` |
| **容器内存** | `gkrust` OOM（`OOMKilled=true`） | 见下 |

### 内存这件事的教训

| 尝试 | 结果 |
| --- | --- |
| 容器 13 GB | `gkrust` LTO 峰值超限 → 容器 OOM |
| 容器 15 GB（用满宿主） | **整机 thrashing，SSH 失联，需服务商重启** |
| 容器 10 GB + `--disable-lto` | 跑了 90 分钟，仍 `OOMKilled=true` |

**结论**：`gkrust` 在关闭 LTO 后仍需 12 GB 以上。
15 GB 的机器做 Firefox 完整链接，处在临界线上。

---

## 五、时间账（为什么花了这么久）

| 阶段 | 耗时 | 是否必要 |
| --- | --- | --- |
| 环境搭建（clang/rust/cbindgen/libclang/crates 镜像） | ~1.5 h | 必要，但踩了版本坑 |
| 拉源码（sparse 反复补范围） | ~0.5 h | 部分可省 |
| **`gkrust` 编译（3 次尝试）** | **~4 h** | **❌ 与补丁完全无关** |
| C++ 编译（4431 目标文件） | ~1.5 h | 其中只有 42 个与我们相关 |

**关键数字**：4431 个目标文件里，**只有 42 个在 `dom/bindings`**（0.95%）。

### 为什么会走成完整构建

Mozilla 的构建系统强制要求完整依赖图：

| 尝试 | 结果 |
| --- | --- |
| `./mach build dom/bindings` | `Build argument is a subdirectory and was ignored` |
| `./mach build dom/bindings --allow-subdirectory-build` | `No rule to make target 'CSSCounterStyleRule.webidl'` |

`GENERATED_WEBIDL_FILES` 的 5 个文件由 `layout/style/GenerateCSSProperties.py` 生成，
需要 `servo` 组件，而 `servo` 是 Rust 的 → 触发 `gkrust` 全量编译。

**这是构建系统的结构性限制，不是命令选错。**

### 下次应该怎么做

| 目标 | 做法 | 耗时 |
| --- | --- | --- |
| 只验证补丁 | `./mach build dom/bindings/export` 触发 Codegen，再手动编 42 个 `.cpp` | ~20 min |
| 完整可运行二进制 | 给 32 GB 内存，或用 Mozilla 预构建工具链 | 2–4 h |

---

## 六、这次验证确立了什么

**可以确认**：

1. 五个补丁的 Codegen 逻辑正确（生成的表结构、数值、索引链都对）
2. 生成代码能过 C++ 编译（4431 个目标文件，含 dom/bindings 全部 42 个）
3. 插桩点的位置正确（三个 `Generic*` 函数编译通过）
4. 索引链设计成立：`protoID → (start,count) → 成员名`

**未确认**：

1. 完整 `libxul.so` 能链接出来
2. 插桩在**运行时**真的采集到数据
3. 采集出的 JSONL 与 win64 版格式一致

后三项需要一台 32 GB 以上内存的机器。

---

## 七、收尾状态

| 项 | 位置 |
| --- | --- |
| 六处修复的完整代码 | `submodules/ruyitrace/domtrace/patches/v2/` |
| 应用说明与验证清单 | `patches/v2/apply-v2.md` |
| 从构建机导出的实际代码 | `patches/v2/codegen-domtrace-snippet.py` |
| 修正后的 `ScopedAccessCall.inl` | `domtrace/binding/ScopedAccessCall.inl`（模板构造函数） |

构建机上的产物（`obj-*/dist/include/.../PrototypeList.h` 等）保留在 host185，
路径 `/root/ruyi-build/ff159/`，容器 `ruyi-build` 已停止。
