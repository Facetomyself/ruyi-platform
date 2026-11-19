# Codegen 改名机制：domtrace 必须改的三处

> 依据：官方 `FIREFOX_159_0_RELEASE` = `9a2dc53c` 的 `dom/bindings/Codegen.py`
> 与 `js/public/experimental/JitInfo.h`，实读源码。

## 一、问题陈述

上一轮定位到插桩点（`GenericGetter/Setter/Method`），但那里只能拿到
`info->protoID` 与 `info->getter`。**拿不到接口名与成员名。**

原因在 `JSJitInfo` 的结构（`js/public/experimental/JitInfo.h:132`）：

```cpp
static_assert(sizeof(JSJitInfo) == (sizeof(void*) + 2 * sizeof(uint32_t)), ...);
```

**16 字节，全部位已分配**：

| 字段 | 大小 | 位置 |
| --- | --- | --- |
| `union { getter / setter / method / staticMethod / ... }` | 8 | 偏移 0 |
| `protoID` | uint16 | union 内 |
| `depth` | uint16 | union 内 |
| `nativeOp` | uint16 | union 内 |
| `type_` / `aliasSet_` / `returnType_` / 9 个标志位 / `slotIndex` | 4 | 偏移 8 |
| 填充 | 4 | 偏移 12 |

**没有存名字的空间。**

## 二、三个必须改的点

### 改动 1：`CGPrototypeTraitsClass` — 补接口名

**位置**：`Codegen.py:14691`

现状：只生成 `Depth`。

```python
class CGPrototypeTraitsClass(CGClass):
    def __init__(self, descriptor, indent=""):
        templateArgs = [Argument("prototypes::ID", "PrototypeID")]
        templateSpecialization = ["prototypes::id::" + descriptor.name]
        enums = [ClassEnum("", ["Depth"], [descriptor.interface.inheritanceDepth()])]
```

改成同时生成名字：

```python
        enums = [ClassEnum("", ["Depth"], [descriptor.interface.inheritanceDepth()])]
        # domtrace: 接口名
        members = [ClassMember("InterfaceName", "const char*",
                               f'"{descriptor.name}"')]
```

产出：

```cpp
struct PrototypeTraits<prototypes::id::Document> {
  enum { Depth = 1 };
  static const char* InterfaceName;   // "Document"
};
```

这样 `prototypes::ID` → 接口名就有了编译期表，`GenericGetter` 里可以：

```cpp
const char* iface = PrototypeTraitsFirst<protoID>::InterfaceName;
```

（需要一个小模板做 ID→Traits 的分派，或用 Codegen 生成一个
`const char* const kPrototypeNames[prototypes::id::Count]` 数组——后者更简单。）

### 改动 2：`CGMemberJITInfo` — 补成员名

**位置**：`Codegen.py:12100` 附近的 `jitInfoInitializer`

Codegen **本来就知道成员名**，只是没写进 JitInfo：

```python
# Codegen.py:5084 已经用到
name=self.member.identifier.name,
# Codegen.py:12189
getterinfo = "%s_getterinfo" % IDLToCIdentifier(self.member.identifier.name)
```

两种产出方式：

| 方式 | 做法 | 优点 |
| --- | --- | --- |
| **A. sidetable 数组** | Codegen 生成 `const char* const kMemberNames_<Interface>[]`，索引是 `slotIndex` 或成员序号 | 不动 `JSJitInfo` 布局，风险最低 |
| B. 放宽 JSJitInfo | 加 `const char* memberName`（16 → 24 字节） | 改动 JS 层公共头，影响 JIT 代码生成 |

**建议 A。** `JSJitInfo` 的 `static_assert` 卡死在 16 字节，改它要动
`js/src/jit/` 下的所有使用者，风险远大于收益。

**sidetable 的反查键必须选对。** 实测 `JSJitInfo` 的两个 union：

```cpp
union {
  uint16_t protoID;
  js::jit::InlinableNative inlinableNative;
  js::jit::TrampolineNative trampolineNative;
};

union {
  uint16_t depth;
  uint16_t nativeOp;     // "Additional opcode for some InlinableNative functions."
};
```

`nativeOp` **与 `depth` 共用存储**，而 getter/setter 路径正需要 `depth`
（`ThisPolicy::UnwrapThisObject(..., protoID, info->depth)`），
**所以 `nativeOp` 在 getter/setter 场景下不空闲，不能用它存成员序号**。

可行的反查键：

| 键 | 可用性 |
| --- | --- |
| `info` 指针本身 | ✅ 最直接——sidetable 直接以 `const JSJitInfo*` 为键做二分/哈希 |
| `protoID` + `slotIndex` | 🟡 `slotIndex` 只在 `isAlwaysInSlot`/`isLazilyCachedInSlot` 时有效 |
| `nativeOp` | ❌ 与 `depth` 共用，getter/setter 路径要用 |

**建议用 `info` 指针为键**：Codegen 生成一张按地址排序的
`{const JSJitInfo*, const char* memberName, const char* interfaceName}` 表，
`GenericGetter` 里二分查找。表是编译期常量，无运行时分配。

### 改动 3：插桩点接上名字

**位置**：`BindingUtils.cpp:3054` 的 `GenericGetter`（`Setter`/`Method` 同构）

```cpp
bool GenericGetter(JSContext* cx, unsigned argc, JS::Value* vp) {
  ...
  const JSJitInfo* info = FUNCTION_VALUE_TO_JITINFO(args.calleev());
  prototypes::ID protoID = static_cast<prototypes::ID>(info->protoID);
  ...
  JSJitGetterOp getter = info->getter;

  // domtrace: 名字从 sidetable 取
  const char* interfaceName = domtrace::PrototypeName(protoID);
  const char* memberName = domtrace::MemberName(protoID, info);

  domtrace::ScopedGetterCall traceScope(cx, args, interfaceName, memberName, self);
  bool ok = getter(cx, obj, self, JSJitGetterCallArgs(args));
  return ExceptionPolicy::HandleException(cx, args, info, ok);
}
```

## 三、为什么这三处改动是必须的

| 不改 Codegen 会怎样 | 后果 |
| --- | --- |
| 只有 `protoID` | 记录里 `interface` 是数字，无法读 |
| 只有 getter 指针 | 记录里 `member` 缺失，无法知道读了什么属性 |
| 两者都缺 | domtrace 记录只剩 `thisObj` 与值，失去溯源价值 |

**这就是 domtrace 必须修改 Codegen 并重编、不能做成运行时插件的原因。**

## 四、验证 Codegen 确实知道这些信息

```bash
# 成员名在 Codegen 里的使用
grep -n "self.member.identifier.name" dom/bindings/Codegen.py
#  5084:  name=self.member.identifier.name,
# 12189:  getterinfo = "%s_getterinfo" % IDLToCIdentifier(self.member.identifier.name)
# 12264:  self.member.identifier.name
# 12269:  self.member.identifier.name

# 接口名在 CGPrototypeTraitsClass 里
grep -n "templateSpecialization = \[\"prototypes::id::\"" dom/bindings/Codegen.py
```

两者都是现成的，只是没写进最终产物。

## 五、改动量估算

| 改动 | 文件 | 行数 |
| --- | --- | --- |
| `CGPrototypeTraitsClass` | `Codegen.py` | +10 |
| `CGMemberJITInfo` sidetable | `Codegen.py` | +20 |
| `PrototypeName()` / `MemberName()` | 新增 `domtrace/` 头文件 | +40 |
| `GenericGetter/Setter/Method` 插桩 | `BindingUtils.cpp` | +15 |
| **合计** | | **~85 行** |

**这是整个 domtrace 重编里最小的部分**——大量工作已在 `ruyitrace/domtrace/trace/`
（13 类记录 + sink 调度）与 `domtrace/config/`（74 开关）做好了。

## 六、复现

```bash
git clone --depth 1 --filter=blob:none --sparse \
  https://github.com/mozilla-firefox/firefox ff159
cd ff159
git fetch --depth 1 origin 9a2dc53c369c7ae5172018b35988e1d2ffeff402
git checkout 9a2dc53c369c7ae5172018b35988e1d2ffeff402
git sparse-checkout set dom/bindings js/public js/src/jit

sed -n '14691,14715p' dom/bindings/Codegen.py    # CGPrototypeTraitsClass
sed -n '12100,12130p' dom/bindings/Codegen.py    # jitInfoInitializer
sed -n '132,240p' js/public/experimental/JitInfo.h  # JSJitInfo 只有 16 字节
```
