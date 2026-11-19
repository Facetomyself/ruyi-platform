# domtrace 插桩点定位（基于官方 159.0 源码）

> 依据：[`mozilla-firefox/firefox`](https://github.com/mozilla-firefox/firefox)
> `FIREFOX_159_0_RELEASE` = `9a2dc53c369c7ae5172018b35988e1d2ffeff402`
> 的 `dom/bindings/`（3.9 MB，13 个 .cpp）。

## 一、为什么看这里

domtrace 记录的是「页面读了哪个属性的什么值」「调了哪个 API 的什么参数」。
在 Firefox 里，**所有 WebIDL 属性读写与方法调用都收敛到三个函数**：

| 函数 | 位置 | 覆盖 |
| --- | --- | --- |
| `GenericGetter` | `BindingUtils.cpp:3054` | 所有 WebIDL 属性的 `get` |
| `GenericSetter` | `BindingUtils.cpp` | 所有 WebIDL 属性的 `set` |
| `GenericMethod` | `BindingUtils.cpp` | 所有 WebIDL 方法的 `call` |

声明在 `BindingUtils.h:3167 / 3183 / 3201`。

**这是 domtrace 唯一合理的插桩位置**——挂在这三处，就覆盖了 `document.cookie`、
`navigator.webdriver`、`getComputedStyle`、`requestAnimationFrame` 等全部接口，
不需要逐个接口改。

## 二、`GenericGetter` 的完整结构

```cpp
bool GenericGetter(JSContext* cx, unsigned argc, JS::Value* vp) {
  JS::CallArgs args = JS::CallArgsFromVp(argc, vp);
  const JSJitInfo* info = FUNCTION_VALUE_TO_JITINFO(args.calleev());
  prototypes::ID protoID = static_cast<prototypes::ID>(info->protoID);
  if (!ThisPolicy::HasValidThisValue(args)) { ... }
  JS::Rooted<JSObject*> obj(cx, ThisPolicy::ExtractThisObject(args));
  JS::Rooted<JSObject*> rootSelf(cx, ThisPolicy::MaybeUnwrapThisObject(obj));
  void* self;
  { nsresult rv = ThisPolicy::UnwrapThisObject(&rootSelf, cx, self, protoID, info->depth); ... }

  MOZ_ASSERT(info->type() == JSJitInfo::Getter);
  JSJitGetterOp getter = info->getter;
  bool ok = getter(cx, obj, self, JSJitGetterCallArgs(args));
  ...
  return ExceptionPolicy::HandleException(cx, args, info, ok);
}
```

`GenericSetter` 与 `GenericMethod` 同构（同样的 `args` / `info` / `protoID` / `self` 前置）。

## 二之二、Codegen 的验证（关键）

光看 `BindingUtils.cpp` 有这三个函数还不够——要确认它们**真的被所有接口用到**。
在 `dom/bindings/Codegen.py` 里查引用：

```
GenericGetter   引用数（Codegen.py 中）  —— 见下
GenericSetter   6
GenericMethod   4
```

`Codegen.py` 生成的访问器字符串形如：

```python
"(GenericMethod<NormalThisPolicy, %s>)" % exceptionPolicy
"(GenericGetter<LenientThisPolicy, %s>)" % exceptionPolicy
```

覆盖 6 个 `ThisPolicy` 变体：

| 变体 | 用于 |
| --- | --- |
| `NormalThisPolicy` | 普通接口 |
| `MaybeGlobalThisPolicy` | Window 全局 |
| `LenientThisPolicy` | 宽松 this |
| `CrossOriginThisPolicy` | 跨源访问 |
| `MaybeCrossOriginObjectThisPolicy` | 跨源对象 |
| `MaybeCrossOriginObjectLenientThisPolicy` | 跨源 + 宽松 |

`BindingUtils.cpp` 里对应 8 处 `template bool GenericGetter<...>` 显式实例化。

**结论：在 `GenericGetter` / `GenericSetter` / `GenericMethod` 三处插桩，
即覆盖全部 WebIDL 接口的所有属性读写与方法调用。** 这是 Codegen 结构性保证的，
不是抽样推断。

## 三、插桩能拿到什么

在这三个函数里，**无需额外信息源**就能得到 domtrace 记录所需的大部分字段：

| domtrace 字段 | 来源 | 说明 |
| --- | --- | --- |
| `interface` | `info->protoID` → `prototypes::ID` 表 | 需要一张 ID→接口名映射 |
| `member` | `info` 的 getter/setter 指针 | 需反查；或由 Codegen 注入名字 |
| `thisObj` | `args.thisv()` | 直接可读 |
| `value`（get 的结果） | `args.rval()` | getter 返回后读 |
| `args`（call 的实参） | `args[i]` | 直接可读 |
| `return`（call 的返回值） | `args.rval()` | 调用后读 |
| `ok` | `getter()` 的返回值 | 直接可读 |
| `error` | `ExceptionPolicy::HandleException` 之前 | 需在抛错路径上加一次捕获 |

### 关键陷阱：`args` 必须在 `_BEFORE` 渲染

手册 1.0.6 节记录过这个坑：

> `args` 必须在 `_BEFORE` 渲染（被调方会改实参对象，`postArgs` 就是为此存在的），到
> `_AFTER` 才读；而 DOM 调用会嵌套（`insertBefore` 触发事件、处理器里又调 `addEventListener`），
> 内层调用的 `_BEFORE` 曾覆盖同一块线程局部缓冲，于是外层记录的 `args` 装的是内层那次调用的实参。

修法是**按嵌套深度索引的 8 槽栈**（`TraceDOMCallState::args[8]`），
`_BEFORE` 取槽、绑定返回时释放（RAII）。

## 四、建议的插桩形态

```cpp
// BindingUtils.cpp，GenericGetter 内，getter 调用前后
bool GenericGetter(JSContext* cx, unsigned argc, JS::Value* vp) {
  ...
  MOZ_ASSERT(info->type() == JSJitInfo::Getter);
  JSJitGetterOp getter = info->getter;

  // _BEFORE：入槽，记录实参 + this（此时 args 尚未被修改）
  domtrace::ScopedGetterCall traceScope(cx, args, info, protoID, self);

  bool ok = getter(cx, obj, self, JSJitGetterCallArgs(args));

  // _AFTER：RAII 析构时读 args.rval() 与 ok，写出一行 JSONL
  return ExceptionPolicy::HandleException(cx, args, info, ok);
}
```

`ScopedGetterCall` 的构造与析构对应手册里的 `_BEFORE` / `_AFTER`，
由 RAII 保证在**所有退出路径**（正常返回、抛错、`HandleInvalidThis`）上都写出记录。

## 五、还需要什么才能完整

| 缺什么 | 怎么补 |
| --- | --- |
| `protoID` → 接口名 | Codegen 生成的 `prototypes::ID` 表已有名字，需加一个反查 API |
| getter 指针 → 成员名 | Codegen（`Codegen.py`）里能给每个 JitInfo 附上名字 |
| 四个身份槽位（`id`/`nativeId`/`class`） | 需在 `JSObject` 上加/取 collection-stable id |
| 12 类输出写入 | 我们已有（`domtrace/trace/`） |

前两项是**重新编译时必须改 Codegen** 的地方，这是 domtrace 不是纯运行时插桩的原因。

## 六、这解决了什么

之前 `docs/05-reverse-analysis.md` 的方案 A（「去官方树找 domtrace」）已验证作废——
官方没有 domtrace。

但**官方有这三个函数**，它们是 domtrace 必须挂的地方。所以：

- ❌ 找不到 domtrace 的实现
- ✅ 找到了 domtrace 该挂的**位置**

这意味着插桩层的骨架现在有依据了，不再是猜。

## 七、复现

```bash
git clone --depth 1 --filter=blob:none --sparse \
  https://github.com/mozilla-firefox/firefox ff159
cd ff159
git fetch --depth 1 origin 9a2dc53c369c7ae5172018b35988e1d2ffeff402
git checkout 9a2dc53c369c7ae5172018b35988e1d2ffeff402
git sparse-checkout set dom/bindings

grep -n "bool GenericGetter\|bool GenericSetter\|bool GenericMethod" \
  dom/bindings/BindingUtils.cpp dom/bindings/BindingUtils.h
```
