# RuyiTrace 整体进度评估（更新于 2026-11-21）

> 编译只是验证手段。本文回答：**RuyiTrace 这个项目实际完成了多少。**

---

## 当前验收：x86_64 开发版已采到真实页面；发行版另验

`attempt.iqWqH54h`（产品输入 `d3371b7`）整机构建 `complete 0`，最终上游 Rust 网络审计通过。发行身份检查因 INI 缺少 SourceStamp 而停止；旧 tar 及失败回执原样保留。另在 UID 1000、仅 lo、seccomp=2、NoNewPrivs=1、零 capabilities 环境实跑了 45 个文件逐项核验的只读浏览器副本。OFF 页面执行成功且无文件。ON 页面回执确认活跃 Web 内容 PID 341，该 PID 文件 667 字节（SHA-256 `9c1f11baf7685271e6b9ee10f7c93525599727308ef0e8dba11f5bd84304fc78`）。控制台实际预览代码读出同轮 marker 的 `set Document.title`、`get Document.title` 和 `call Document.createElement("div")`、`ok=true`，三条顺序正确。**这是基础采集实证，不是全套 producer、Window 上下文或发行包验收。**

### 带源码标识的正式候选：打包通过，页面采集失败

`attempt.H5K1EqGg`（输入 `4eed287`）已 `complete 0`，最终原版 Rust 审计 rc=0，BuildID `20261121023929`，完整基线 `9a2dc53c369c7ae5172018b35988e1d2ffeff402`。上游 tar.xz 81,711,500 字节，SHA-256 `ff24a6b43e8357e6df0eea4835fe4ebca9ed36120bcca932a579defbfff21ebf`；包及安装副本身份校验通过。正式交付却以 `run_page 1` 结束：OFF 零文件；ON 页面 marker、PNG 和进程退出正常，实测内容 PID 290 在首次打开 core 时记录 `open_failed: Permission denied`，无事件输出。不能把上一个开发版的三条记录移作这个包的证明。

13:43 +08:00 前对同一包做隔离复测：无预建子目录时 PID 267、预建本用户 0700 `domtrace` 子目录时 PID 607 均出现相同打开错误，均零文件；新版失败摘要又关联到了 PID 311 的同类错误。只证明首次打开失败，不能由 errno 反推具体受限系统调用。未改 Firefox 沙箱、宿主目录权限、Docker seccomp 或两个 SSH 隧道。下一项工程重点是受限的父进程写入：以窗口 actor 自身的 principal/WindowID 和内容进程身份确定落点，只接收明确类型、长度和限额内的事件；不接受子进程提供的路径、PID 或原始 JSON。修复后重跑原 OFF/ON 窗口验收。

`e3939b3` 给 Linux 控制台受控启动增加资格检查：只有经完整 DOM/click/双会话原始数据复核的本地交付可签发小型能力记录，启动前重新核实七个关键文件；缺凭据、同尺寸改包、配置变化和取消均在启动前停止。无论文件名或构建版本都不能代替这份验收；这也不是解决上述写盘故障的修复。尚未给任何产品包发放真实闸门资格。

### 父进程写入候选 `86d4352`

在 `PWindowGlobal` 增加有界的类型化 DOM/click 上报。父进程从当前窗口 actor 确认来源、窗口和内容进程，并按自己配置打开私有文件。消息不携带路径、文件句柄、PID、来源或 JSON。要求明确选定单一 HTTP(S) origin；设闸门时保持停采，直至父进程可确认会话边界。原生父子进程模型通过 OFF、错误来源、非法 payload、PID 实例冲突、共享上限及 DOM/click 正例；21 项控制台组合回归通过。

host185 上两次独立生成 261 个 IPDL 输入，真实编译发送方、接收方、协议生成物和运行时共 16 个对象，`ld -r` 无未解析的本项目符号。上一次失败包原样保留。新工作区 `/var/tmp/ruyi-ff159-window-actor` 已通过干净检出和四项补丁检查。15:43 +08:00，`attempt.6D26B4Jt` 开始配置。一次性顺序协调器随后执行全量构建、独立审计、打包及 `--parent-window-transport` 离线验收；前一阶段失败即停止。13:43 的旧包失败结论不变；新候选尚未取得成品页面输出。

### 后续源码增量：DOM 类型和五项只读属性（尚未发布）

`810c3e2` 依据 Firefox 159 的 WebIDL 声明接入 `Document.compatMode/contentType`、`Element.tagName/localName`、`Node.nodeName`。成功 `createElement` 的返回值用原生 DOM JSClass 名渲染，例如 `[Object HTMLDivElement]`，不读取页面的 `constructor` 或 `toString`；不据此生成对象关联 ID。新增 `--require-dom-shape` 档要求在同一页面窗口顺序识别八条值与类型都正确的记录。

实测分层：宿主筛选/序列化和八事件判定反例通过；新绑定头在候选原配置下编译得到 489,936 字节 x86_64 ELF 对象（SHA-256 `d4ec73d4ab8528070e2916ffa1dce123b4b26ad11cc2786300e79c5a206abb9b`）。旧开发版在仅回环环境能正确执行扩展后的页面、OFF/ON 均正常退出，基础事件仍可读；严格八事件检查按预期失败。没有改动正在构建的 `4eed287`，八事件浏览器正例仍待后续集成。

### 后续源码增量：Linux click 派发的独立 JSONL（待集成浏览器正例）

`cfdf3e5` 接入 Firefox 159 `EventDispatcher::Dispatch` 真正派发分支，只处理目标为 HTTP(S) 内容 Window 的 `ePointerClick`，不记录按键、坐标、节点正文或 listener 数据。按 PID 延迟创建独占私有 event 文件，时间、WindowID/origin、递增事件 ID 和窗口序号用于核对。不同 sink 各自停止 I/O 故障写入，Linux 实现共同遵守进程记录上限。该切片不等于 Win64 全部事件、异步队列或完整执行上下文关联。

原生测试已覆盖 OFF、仅 event 不建 core、两类记录一起写、跨 sink 限流和旁路故障后 core 保持可用。真实 Gecko 的 BindingUtils、EventDispatcher 与七个运行时单元已独立串行编译并成功部分链接。受控页面执行两次 `click()`、一次非 click，监听器计数及最后 title 读回正确才发回执；已在旧 x86 开发版实跑，基础采集仍成功，新的 `--require-click-dispatch` 判定按预期未通过。带此钩子的浏览器仍待后续集成；当前 `4eed287` 候选不含该增量。

### 后续源码增量：Linux 受控采集会话

`4dbbe6c` 接通 `MOZ_DOM_TRACE_GATE` 与轮询间隔：默认无标记时暂停，观察到开闸后先同步写 `session_started` 再发布会话号，关闸写 `session_stopped`。core/click 提交前都重新核对入口会话，避免跨窗口调用串入新会话；限额跨会话累计。Linux 控制台只发布/移除已保存 profile 内自己格式的 `trace.on`，不会截断或移除外部标记；界面表达的是控制文件状态而非推断采集成功。

在 ARM64 和 host185 的 x86_64 原生测试进程观察两轮开关、空闲边沿、旧调用拒收、跨会话上限、fork/exec 和可中断退出。16 项控制台组合回归通过；真实 Gecko 两个钩子和八个运行时单元部分链接无未解析的 domtrace 符号。闸门与各 producer 的完整浏览器沙箱内联调仍待集成；本轮未改变 `attempt.H5K1EqGg` 的输入。

`bc0ec4c` 补上浏览器级闸门验收协议：同一页面五个阶段，核对同一活跃内容 PID 的两对实际落盘边界、同一 WindowID/origin 内的 DOM 与点击及三个暂停值缺席。原生 writer 配合回环 HTTP 与模拟页面正例通过，八组错误记录被判失败。真实 x86_64 对照中，旧插桩版在第一次开闸前写出了暂停值；stock 因从未写出开启边界而失败。两者都正常退出并有截图，说明退出和截图不是闸门行为证明。未来含相应实现的发行候选可选 `--extended-producers`，须通过八事件、点击和双会话页才签发扩展验收。现有 `4eed287` 仍走先前窗口验收档位，未变更其输入或在途交付。

## 历史过程：从宿主 writer 到首个受控页面

上一版实验内核已链接 libxul 并进入 headless，采集目录为空；其 networking 构建审计曾被跳过，不作为发布构建。后续接入尝试缺父级 DIRS，导致链接找不到运行时符号。现在已有 Linux 父构建补丁及本机验证的 core 写入路径：20 项宿主测试通过，其中新增并发落盘和限流测试。这一步验证的是独立写入器。

2026-11-21：已在固定 Firefox 159 的 `GenericGetter/Setter/Method` 接入最小页面验收范围：`Document.title` 的字符串读写和 `Document.createElement` 的单字符串调用。host185 上用 Gecko clangd 编译命令（局部验证覆盖优化/调试级别），串行编译真实 BindingUtils 和六个核心源文件；绑定对象确实引用写入函数，合并后的可重定位对象没有未解析的 domtrace 符号。顺带修复了 Gecko Clang 拒绝在 constexpr 中调用 strlen 的错误。方法名来自函数内部标识，接口名来自 Gecko 原有的 proto 表；生成名字区间表不是此链路的前提。

当时仅有局部链接证据；本页顶部现已记录后续取得的真实采集。该阶段的下一步是保留上游网络审计、用正常沙箱加载受控页面。验收要求同一 PID 按顺序出现唯一标记的 set/get 和参数为 `div` 的成功调用；关闭开关换新目录应零输出。[复现步骤与页面验收](../submodules/ruyitrace/tests/linux/README.md)。

### 2026-11-21：页面负对照与构建审计

未插桩的 ARM64 Firefox 159.0 在仅回环网络命名空间作为普通用户运行。两次新 profile 分别关闭、开启采集开关，均在页面成功 set/get/call 后返回本轮随机 marker，浏览器退出码 0，PNG 有效，trace 文件数 0。再按**产品**标准运行同一浏览器，ON 轮具备页面回执却没有事件，验收按预期失败（rc=1）。这证明空目录不会冒充采集成功，而非证明带补丁的 x86_64 浏览器已经出数。环境报告 PID namespace 创建 EPERM，未关闭沙箱，也不据此认证其全部隔离层。

host185 先复验现存 `libgkrust.a`：1,525,171,928 字节，SHA-256 `86987fa36c842b9e90902b9342b8bc7c50e656309d896a43ab05c8e9fee26a8d`。固定版本上游的 `check_binary --networking` 返回 1（`recv,send`）；在聚合对象的可执行节中定位到 24 处匹配的 ELF 重定位，包括 `nix::sys::socket`、`socket2::sys` 和 Rust 标准库接口。这是静态引用证据，尚无页面可达性或实际网络流量证据。历史“纯误报”判断撤回。只将构建树的 `config/makefiles/rust.mk` 恢复至上游（blob `60fa082aa4d2f471b3410a45b24f8fdcb3f5df2b`）；未移除构建产物、未启动全编。下次应使用受控资源的干净配置复验归档审计，通过后才进入最终链接和产品 ON/OFF 验收。此次实测源码卷位于根分区（可用 22 GiB）；`/home` 的 961 GiB 空闲不是当前 `/build` 的可用容量。

### 2026-11-21 01:47 +08:00：隔离的审计构建已开跑

`host185` 容器中另建 `/var/tmp/ruyi-ff159-core-audited`，新 worktree 和 objdir 均位于大卷，不覆盖旧实验构建。保留上游审计和两类沙箱；容器 9 GiB RAM / 13 GiB 含 swap、两核两路。`configure` 实读 2502 个 moz.build；`configured.json` 确认了 Linux core 后端、Rust 优化等级 1、无额外调试符号、gkrust LTO 审计条件与六类 WASI 库沙箱。第一次预检误读 export 阶段才生成的头文件，改为读取配置输出后，干净目标通过，旧目标被正确拒绝。

`attempt.wtTaYr4i` 已进入编译。这是阶段观测，不是产物验收；下一轮先读回执，不重复启动。独立 WASI C 样例链接成功，但当前 Ubuntu WASI C++ 标准库样例有未解析的异常运行时符号。若工程触发同类错误，核对该 commit 的 Mozilla WASI SDK 34 工具链配方，保留现有沙箱。最终必须用归档审计回执和真实页面 get/set/call 结果判定。

### 2026-11-21 02:02 +08:00：Linux 日志目录的组件联调通过

修复前渲染层把 `/tmp/采集 01/` 生成为 `/tmp/采集 01\trace.jsonl`。现在主进程的默认日志目录位于 `userData`，渲染层按宿主平台生成锚点，原生路径推导和目录创建在 POSIX 上保留字面反斜杠。实际用 Node 生成环境、启动 C++ 合成生产者，在含中文、空格、单引号与反斜杠的指定目录只得到一个 PID 文件、7 行可解析的 `Document` 记录；Windows 盘符、UNC 路径及显式覆盖仍过测试。这是控制台函数至原生写入器的联调，不是 Electron 可视界面或带补丁浏览器采集验收。

已有 `attempt.wtTaYr4i` 继续运行，本次没有修改它的输入或资源限额；本轮路径修复需要在后续集成中纳入。复核时日志已到编译约 18 分 44 秒，尚无构建退出回执。

### 2026-11-21 02:23 +08:00：控制台主进程启动链已单独验证

Linux 打包态按 `resources/kernel/firefox` 与 `libxul.so` 识别内核，不再回退到 Windows 开发路径；未附带内核时保留显式选择。默认 profile 放用户数据目录，显式 Linux profile 保留大小写。用 Electron 事件注册替身执行真实 `app:kernel` / `cfg:get` / `ff:launch`，在仅回环网络中以普通用户启动已有的 ARM64 Firefox 159.0；`about:blank` 截图 PNG 验证通过，浏览器返回 0。五项测试全过。这是主进程启动验证，不是 Electron 窗口验证，也不是带插桩 x86_64 内核的页面采集。

同一审计构建在 `dom/clients/manager` 编译中，容器占用 4.336 / 9 GiB，尚无最终回执；未调整资源或重跑构建。

### 2026-11-21 02:39 +08:00：日志内容到渲染层已单独验证

Linux 日志页可按 PID 只读预览 get/set/call，展示接口、成员、参数、值及调用结果，并区分读取上限、坏行和未完成末行。主进程只接受 PID，只读当前配置根目录下的 core 文件。实际编译 Vue 日志组件并在 jsdom 挂载：C++ 写入器生成 12 条合成事件，经真实主进程和 preload 的方法交给界面，逐行对照文件验证展示。Node 组合测试 8/8。未启动 Electron 窗口；这些记录不是页面采集数据。

同一审计构建 `attempt.wtTaYr4i` 日志到 `dom/media/doctor`，容器 4.358 / 9 GiB，仍无最终构建回执。后续需用通过上游审计的 x86_64 产物跑 ON/OFF 页面测试，再将真实 trace 交给此预览。

### 2026-11-21 03:12 +08:00：已在 Firefox 实际沙箱目标上定位并修复 WASI 链接问题

从该 Firefox 提交的 Mozilla CI Clang 19 基线任务 `FovSmFqBRB2BN1EcgwlFeA` 的 `MOZ_FETCHES` 找到生产任务 `CJd0ctZnQzSu4Erw4ZByrA`（run 0）。归档 10,187,126 字节，SHA-256 `ced4ad66408022397388863bf5c1c3f0cea250c7445d4a5e2ab884c5a4e71660` 与上游元数据一致；解包后逐文件核对。固定的是实际 CI 消费者的依赖，不是按日期猜选或使用 `latest`。

在独立目录重放真实 `rlboxsoundtouch.wasm` 构建规则（16 个 C/C++ 单元、同一 Clang 19.1.1），只改变 `--sysroot`。系统 `/usr` 的最终链接报 `__cxa_allocate_exception` 与 `__cxa_throw`；使用上述 sysroot 成功，得到 359,701 字节 WASM，SHA-256 `1972108e3f54298706b0607cab9e09aed8073e4572921a133492fdde4159d6dd`。已由 WebAssembly 引擎验证模块格式和四个 SoundTouch API 导出，未执行音频处理。构建驱动后续要求该 sysroot，预检拒绝不匹配归档、改写过的头文件或额外文件。[复现步骤](../submodules/ruyitrace/tests/linux/README.md)。

同一整机 `attempt.wtTaYr4i` 仍使用旧 `/usr` 配置，日志至 `gfx/gl`、尚无退出回执，容器 4.303 / 9 GiB。未切换运行中输入或启动第二份全编。上述成功只涵盖独立沙箱目标，不代表完整 Rust 归档审计、最终链接或浏览器采集验收。

### 2026-11-21 03:39 +08:00：Linux core 日志文件生命周期

核心写入器现在通过目录描述符逐段打开路径，以独占方式创建 `0600` 的 PID 文件，新建目录权限上限为 `0700`。同 PID 重用旧路径时保留旧记录；出现符号链接、硬链接、FIFO、可被其他用户写入的最终目录或 `..` 等情况时跳过该 core sink。整行写入后刷新用户态缓冲，父进程测试在生产者 `_Exit` 之前已读到完整记录；这是读者可见性，不是断电持久化。fork 后禁止复用父进程的 writer，exec 后各 PID 独立落盘。适用于 Linux core，不将结论外推到所有 sidecar 或 Firefox 的内容进程沙箱。

在 host185 临时目录用该 Firefox 配置的真实编译命令对本次改动的两个单元生成了 ELF 对象；20 项宿主套件及 8 项控制台组合测试通过。正在进行的原构建未包含本轮改动，03:39 仍在 `layout/generic`，没有最终回执或真实浏览器 trace。

### 2026-11-21 04:00 +08:00：修正版候选就绪，仍只有一份全编

原 `attempt.wtTaYr4i`（产品输入 `17c8e21`）仍在编译 `third_party/libwebrtc`，尚无退出回执。以 `d3371b7` 归档产品输入，在同一容器的 `/var/tmp/ruyi-ff159-core-wasi159` 独立检出 Firefox `9a2dc53c`，核验全部 CI sysroot 文件并检查父构建补丁与绑定补丁都能应用。新工作区无 `latest-attempt`：尚未开始配置或编译。

一次性交接器 `3a9c667` 等待旧驱动的文件锁；实际观测旧 `build.lock` 与新 `handoff.lock` 分别由驱动和交接器持有，`handoff.json` 为 `waiting_for_predecessor`。只有旧任务以已知的 SoundTouch/WASI 系统库错误结束才自动交给候选构建。旧任务成功则保留其结果，审计/资源/其他错误则留待分析。分类用例和真实文件锁的互斥测试已过。该步骤不代替候选 Rust 归档审计、最终链接或受控页面验收。

### 2026-11-21 07:29 +08:00：旧尝试结束，候选开始真实构建

旧 `/usr` sysroot 尝试在 162 分 34 秒后以 `build 2` 结束：SoundTouch 和 `security/rlbox` 的组合 WASM 均因系统 libc++ 异常处理符号无法链接。旧尝试的 Rust 静态库已生成，160,069,128 字节，SHA-256 `9e3404f9497555a570e763e6c067c39114244a8ae6641ecadf2459497aa6d1fd`；保持所有上游检查完整，独立运行 `check_binary --networking` 得到退出码 0。这是这个新归档的实测，并非对早期失败归档的豁免。

自动交接器因检测到额外目标而停下。人工复核时，组合模块用相同构建参数和固定 Mozilla sysroot 重放 53 个实际编译单元，产出 4,459,037 字节 WASM；五类库各一项函数导出获确认。加上前次 16 单元 SoundTouch 复验，两个已观察失败目标都已有隔离链接结果，不等同于浏览器运行结果。

保留旧日志及交接器原始决定后，人工复核回执放行 `attempt.iqWqH54h`（产品输入 `d3371b7`）。实查 configure 已完成、预检确认正确 sysroot 摘要、原版审计、Linux 与 WASI 沙箱；目前阶段为 `build`。仍为单任务、两核两路、9 GiB RAM / 13 GiB 合计。下一步看候选自己的归档审计与受控页面 ON/OFF 结果。

### 2026-11-21 07:49 +08:00：采集验收增加页面内容进程归属

修正了“文件名含数字就当作本次内容进程”的盲点。回环页面交回随机 marker 时暂缓响应，记录本次浏览器的活跃 Web 内容子进程树及命名空间 PID；结束后只在这些 PID 对应的文件里接受同一 marker 的 set/get/call。实测 Firefox 159 的 forkserver 子进程已重写 argv，仅看末项 `tab` 会漏判；现在也核实 forkserver 父子关系和 Gecko Web 进程角色。PID 复用、命名空间内编号冲突及其他进程角色有独立反例测试。

ARM64 未插桩 Firefox 的 OFF、ON 均确认页面完成、截图有效、进程归属可识别、trace 为零；同一浏览器跑产品模式， ON 轮按预期因缺三条记录而失败，离线复核也失败。真实 x86_64 采集仍未验收。候选 `attempt.iqWqH54h` 07:49 在编译，无最终回执；本轮没有更改其输入和限额。

### 2026-11-21 08:08 +08:00：验收结果绑定到实际运行的发行包

候选的产品模式现在区分开发树、未插桩对照和带审计的分发包。分发包需要同一次完整成功回执、实际 Rust 归档通过上游审计、objdir 与打包后内核的 ELF Build ID 匹配。页面测试前后核实 7 个关键文件的长度和 SHA-256；独立记录整包 SHA-256。

在 oracle-reverse-dev 上，真实 Firefox 159 ARM64 tar 与已安装的 7 个关键文件逐字节摘要一致（BuildID `20261022150525`）。普通用户在仅回环网络内用这份回执运行 OFF/ON，均正常退出，有截图、页面回执及内容进程证据，零 trace。五项合成单测覆盖混包、架构、归档、回执和 Build ID 异常；产品正例仍须在 x86_64 候选上运行。同一候选 `attempt.iqWqH54h` 此时编译到 `dom/canvas`、尚无退出回执。

### 2026-11-21 08:31 +08:00：核心 Window 上下文与事件序号增量

为现有 `Document.title` 和 `Document.createElement` 探针接入 Gecko 执行 realm 的 HTTP(S) 内容窗口：通过当前原生全局、inner WindowID、BrowsingContext 及 principal 的 web-exposed origin 区分 top/iframe，跳过不可判定的来源。每线程按 `(WindowID,type,interface,member)` 对成功写出的记录编号；键数上限 1024，饱和后保留已有序列。此切片不宣称 Worker、扩展或其他协议的支持。

宿主实测 1,027 条合成 Window 行，跨线程、窗口、操作独立计数；`--require-window-context` 的判定器拒绝串窗口、错误来源/层级与无效序号。host185 对此版本真实编译 BindingUtils 和六个核心单元，`ld -r` 无未解析 domtrace 引用。尚无含此增量的浏览器级记录。原候选 `attempt.iqWqH54h` 仍基于 `d3371b7`、编译至 `dom/media/mp4`，原候选输入未改；保留原候选验收与后续增量验收的区别。

### 2026-11-21 08:40 +08:00：候选结束后的一次性打包已接入

打包器 `efa0277` 在独立目录等待现有候选锁，不与全编并行。候选须以 `complete 0` 结束、自己的 Rust 归档通过原版审计，且配置/工具链与回执相符，才运行上游 `mach package`。实际包须通过包名指针、tar 与 staging 内容、ELF 和 Rust 归档身份校验才生成成功回执。四项互斥与故障测试、五项身份测试均在本机和构建容器通过。

实查 `attempt.iqWqH54h` 阶段为 `build`；`package-review/phases.jsonl` 仅有 `waiting_for_build`，无打包命令日志及包身份回执。无第二份编译。此处既不表示已有产品包，也不表示通过页面采集。该容器不允许 `unshare -n`，后续普通用户隔离页面验收仍须使用单独合适环境，不放宽构建容器权限。

### 2026-11-21 08:54 +08:00：同机 x86_64 离线浏览器负对照已实跑

在 host185 单独准备 Ubuntu 24.04 运行镜像，不把构建容器改为特权模式。官方 Firefox 159.0 amd64 的发行归档经 Mozilla SHA512SUMS 核验，实际 90,055,416 字节，SHA-256 `54536fcd120af484d4c56272a5a1cf4af57b9c713d1a3b1e775da192dd541fcd`。和未来候选使用相同入口：UID 1000、只读根、只读输入、有效 capabilities 为 0、NoNewPrivs=1、seccomp=2、网络接口仅 lo。OFF 和 ON 均有页面 marker、PNG、有效 Web 内容 PID 和退出码 0，产物为空；同一浏览器跑采集诊断，准确因缺少三条记录而失败。stock 回执冒充候选的测试在浏览器启动前即失败。

旧内核中 Firefox 报用户命名空间创建 `EPERM`；记录真实限制，不降低默认隔离设置，不当作完整浏览器沙箱认证。完成后烟测容器退出。候选 `attempt.iqWqH54h` 仍处于 build（`dom/workers/sharedworkers`），打包仍等待；这次验收的是运行环境和负对照，不是 RuyiTrace 的真实采集正例。

### 2026-11-21 09:07 +08:00：从打包结果到候选页面验收的一次性交付已接入

在 host185 验证了真实官方 x86_64 tar 经 UID 1000 离线容器独立解出 51 项（340,865,762 字节），复制前后身份一致。用该安装目录只读启动新的 OFF/ON 和缺采集负对照均符合预期。首次执行暴露脚本对 UID 1000 不可读，改为 root 所有的只读检查脚本后在全新目录实跑通过；不放开浏览器、宿主或构建目录写权限。另测摘要/身份冲突、路径越界和链接条目均停止。

一次性交付器 `daffb7d` 对指定构建用 inotify 等待打包结果；只在同次构建、Rust 审计、包身份与指针一致时，才复制候选、复核、普通用户解包，再运行真实页面。实查 `attempt.iqWqH54h` 仍在 `gfx/vr`，打包 `waiting_for_build`，交付 `waiting_for_package`，尚无候选 tar 或正例回执。基础验收与后续窗口上下文/其他 producer 验收仍有区别。

### 2026-11-21 09:21 +08:00：本次候选的 Rust 静态库通过构建中独立审计，日志预览可续读

`attempt.iqWqH54h` 的 `libgkrust.a` 已生成：160,069,256 字节，SHA-256 `2c81bdb3cac5f6efd90e44cf24c0defd74b7df7710f4f184bcc37b900de00042`。09:20:58 在该候选自己的 objdir 中，确认固定源码、配置与 sysroot 后，用其 Python 环境只读执行上游 `check_binary --networking`，rc=0；设备/inode、长度、mtime/ctime 在审计前后相同。这是对上述摘要的中途实测，不是驱动的最终归档回执。候选此时仍编译 `js/src/vm`，最终 libxul 尚无，打包和页面交付继续等待。

控制台 Linux JSONL 预览 `1e98ca7` 支持下一页和手动查看追加记录。每次最多 64 KiB/20 条，真实写入器输出 32 条合成事件，挂载 Vue 页面经真实 preload/main IPC 分 20+12 条核对行号与内容；12 项组合回归通过。另测 UTF-8 截断、超长行跨页跳过、PID/目录绑定、文件缩短/替换和续读标识失效。此验证不是原生 Electron 窗口验收或 Linux 浏览器采集证据。

### 2026-11-21 09:37 +08:00：有效事件才创建 core 输出，满额与 I/O 故障停收

独立增量 `1a326df` 改为首次通过验证的记录才独占打开 PID 文件。开启后仅进入未匹配绑定、输入无效 Window 或刷新空 writer，都不创建输出路径。达到 `TRACE_LIMIT` 后新 scope 不做参数提取，已经进入的 scope 提交时再检查；已有文件仍可刷新。打开、写入或刷新故障会停收并输出一条不含路径和页面值的诊断，避免向已失败的流反复写入。

真实文件回归覆盖首条被过滤、同名文件保留、严格 1 行上限和并发上限、用子进程文件大小限制触发写入故障。12 项控制台组合测试通过；以候选 Gecko 实际编译参数生成 x86_64 ELF 目标文件，未改动候选 objdir。此增量不是在运行的候选输入。`attempt.iqWqH54h` 已编译至 `netwerk/sctp/datachannel`，仍无最终 `libxul.so`、打包或页面验收回执。

### 2026-11-21 10:02 +08:00：Linux Electron 成品应用目录与真实窗口日志验收

控制台 `db93c37` 从已跟踪源码和锁定依赖构建完整的六路由 renderer 及 main/preload/shared。解包目录可由本地 Electron 直接启动，不需开发服务器。Linux 改用原生窗口装饰：实测 ARM64 Electron 45.4.1 的 Ozone headless 建窗时，原先的隐藏标题栏加 overlay 组合导致 SIGSEGV，而正常窗口装饰创建成功；缺少内置 Firefox 时侧栏也不再显示内核就绪。

真实 BrowserWindow 用 `file:` 加载成品，保留 sandbox、contextIsolation 和禁用 Node 的渲染页，经真实 IPC 读取原生 C++ 测试写入器生成的 32 条合成行，页面分 20/12 逐字段与磁盘对照。确认第二页内容可见并取得 1000×615 PNG（SHA-256 `5fdfc959b6542f2ba2e5af182bd8e3f38e11d641a1716091530475bd7a1a1290`）。应用目录预览归档 354,776 字节，SHA-256 `e5145b9b61dce79fb171ab12cc7e2d47a05245b40023b02484b382c50324fc57`；不包含 Electron 运行时或 Firefox 内核。该验收是 Linux ARM64 上的实际 Electron 渲染及 IPC，不是物理显示器、全部功能页或采集浏览器本身的验收。

x86_64 候选 `attempt.iqWqH54h` 在 `widget` 编译阶段，尚无最终 `libxul.so`、包身份或受控页面正例回执。本轮未触碰候选输入。

### 2026-11-21 10:26 +08:00：真实候选已越过 WASI 失败点，识别并修复后续构建的版本标识缺项

`attempt.iqWqH54h` 的整机构建已生成 `rlboxsoundtouch.wasm`（359,701 字节，SHA-256 `1972108e3f54298706b0607cab9e09aed8073e4572921a133492fdde4159d6dd`）及 `security/rlbox/rlbox.wasm`（4,459,037 字节，`b0c69b3a6bfdcead845cbc15efbe2c6dc1677617db5bcd8af4809fdf5d1b46a0`）。两个摘要分别与此前隔离重放完全相同；对本次对象直接验证 4+5 个代表函数导出。`dist/bin/libxul.so` 已存在，为 260,808,256 字节 ELF64 x86-64 DYN，ELF Build ID `b93f7f5b7605bece329ae34e5abaf5f688fb82c4`。可识别的 ELF 不等于构建成功、包验证或页面数据。

上游默认不从 Git worktree 自动写入 SourceStamp；实际候选 `source-repo.h` 为空，生成的 `build/application.ini` 只有 BuildID `20261120232713` 而缺 SourceStamp，尚不满足分发身份要求。保持候选及已部署的严格检查原样。修复 `4eed287` 在 configure 前声明受支持的源仓及完整 SHA，核对 Git HEAD；全编前就通过上游 make 目标生成并验证两份 INI 和头文件。独立真实 configure/元数据试验得到一致的 BuildID `20261121021849` 和准确的 `9a2dc53c…`，重复生成验证通过。包检查继续拒绝缺失/错误源码戳，不以补写 INI 或旧包替代。当前候选尚在构建，打包及非 root ON/OFF 均无最终回执；本轮没有启动另一份浏览器全编。

## 此前阶段快照（以下非当前构建状态）

### 当时的结论

**分析层与实现层基本完成，运行验证层完全没开始。**

具体说：我们知道 domtrace 的全部行为（74 个开关、13 类输出、13 类 sink），
代码也写了（4852 行 C++ + 2919 行控制台），测试 19 项全绿；
但**从没在真实浏览器里跑过一次采集**。

---

## 二、分层进度

### 第 1 层：行为还原（✅ 完成）

| 项 | 目标 | 实际 | 依据 |
| --- | ---: | ---: | --- |
| `MOZ_DOM_*` 开关 | 74 | **74/74** | 反编译 `xul.dll`，每个都有读取点配对 |
| 开关解析语义 | 74 | **74/74** | 10 种解析模式，逐条对齐汇编 |
| 读取器区域 | 5 | **5/5** | 地址聚类 |
| jscall operation | 39 | **39/39** 定义，37/39 定位 | 15 独立字符串 + 31 立即数 |
| 分发器结构 | — | **完整还原** | 16 路跳转表 + movabs/SSE 三种校验 |

**这一层是实打实的。** 每一处都有反汇编依据，脚本可复现。

### 第 2 层：输出格式（✅ 完成）

13 类输出，全部有数据结构与测试：

| # | 输出 | 代码 | 测试 | 依据强度 |
| --- | --- | ---: | --- | --- |
| 1 | core jsonl | 205 行 | ✅ | 手册原文 |
| 2 | jscall bin | 228 行 | ✅ | 官方解码器互通 |
| 3 | trace-writer | 94 行 | ✅ | — |
| 4 | sidecar (exception/event/descriptor) | 158 行 | ✅ | 手册原文 |
| 5 | storage (cookie/storage/eval) | 229 行 | ✅ | 手册原文 |
| 6 | network (ws/http_packet) | 185 行 | ✅ | 手册含字段表 |
| 7 | wasm (2 类) | 224 行 | ✅ | 结构有据，键名部分推断 |
| 8 | **env_inventory** | **422 行** | ✅ | **真实样本实测** |
| 9 | sink 调度 | 299 行 | ✅ | 13/13 决策 |
| 10 | sink 会话 | 220 行 | ✅ | 端到端写盘 |

### 第 3 层：插桩（✅ 代码就绪，✅ 编译验证）

| 项 | 状态 |
| --- | --- |
| 插桩点定位 | ✅ `GenericGetter/Setter/Method`（官方源码行号） |
| Codegen 改名机制 | ✅ 索引链闭合（实测产物） |
| 补丁 | ✅ 5 个，84 行，**编译通过** |
| 8 槽嵌套栈 | ✅ 实现 + 5 组断言 |

### 第 4 层：控制台（✅ 完成，未联调）

2919 行，54 个文件，Electron 结构完整。**但没有与真实采集数据联调过。**

### 第 5 层：运行验证（❌ 未开始）

| 项 | 状态 | 卡什么 |
| --- | --- | --- |
| 完整 `libxul.so` 链接 | ❌ | `gkrust` OOM，需 32 GB 内存 |
| 实际跑 `MOZ_DOM_TRACE=1` | ❌ | 依赖上一步 |
| 采集出的 JSONL 与 win64 版一致性 | ❌ | 同上 |
| 控制台读取真实数据 | ❌ | 同上 |

---

## 三、诚实的自我评估

### 做扎实的部分

| 项 | 为什么可信 |
| --- | --- |
| 74 个开关读取点 | 反编译定位，每个都能指到具体 RVA |
| 开关解析语义 | 10 种模式，逐条对齐汇编指令 |
| jscall 二进制格式 | 用官方解码器正向验证（写入器 → 解码器 → 字节比对） |
| env_inventory 结构 | **有真实样本**，schema 是从 4 个文件反推的 |
| 索引链设计 | 生成的 `PrototypeList.h` 实测正确 |

### 依赖推断的部分

| 项 | 推断程度 |
| --- | --- |
| wasm 记录的 JSON 键名 | 结构有手册依据，**键名是推的** |
| exception/event/descriptor 的部分字段 | 同上 |
| `drain` / `put` 两个 operation | 名字太短，扫描没定位到 |

### 完全没验证的部分

**插桩在运行时到底采不采得到数据。** 这是最大的空白。

代码能编译，逻辑自洽，测试通过——但**没有一次真实采集**。

---

## 四、投入产出比

| 阶段 | 产出 | 状态 |
| --- | --- | --- |
| 反编译分析 | 74/74 开关 + 39 operation + 分发器 | 完成 |
| 输出格式还原 | 13 类，4852 行 C++ | 完成 |
| 测试 | 19 项，覆盖字节布局与端到端写盘 | 完成 |
| 插桩补丁 | 5 个，84 行 | 编译通过 |
| **真实构建** | **7 个缺陷修复** | **Codegen + C++ 通过** |
| **运行验证** | **0** | **未开始** |

**注意最后一行：运行验证是 0。**

---

## 五、下一步真正的瓶颈

不是代码，是**一台 32 GB 内存的机器**。

| 需求 | 现状 | 差距 |
| --- | --- | --- |
| 内存 | 15 GB（host185） | 需 32 GB |
| 已有产物 | 18 GB 源码 + objdir | 可复用 |
| `gkrust` 编译 | 已尝试 3 次，全部 OOM | 关 LTO 后仍需 12 GB+ |

**有了 32 GB 机器，剩下的路是清楚的**：

1. `docker update --memory=28g`
2. `mach build` → 得 `libxul.so`
3. 跑 `MOZ_DOM_TRACE=1` 采一次
4. 对比 win64 版的输出格式
5. 联调控制台

预计 4–6 小时。

---

## 六、如果一直没有机器

现有成果的**实际可用价值**：

| 用途 | 可行性 |
| --- | --- |
| 作为 domtrace 行为的**权威文档** | ✅ 完全可以，74/74 有反汇编依据 |
| 作为**重写 domtrace** 的设计参考 | ✅ 索引链、sink 调度、13 类格式都齐了 |
| 分析 win64 版采集的 trace | ✅ 解析器都能直接用（jscall、env_inventory 等） |
| 在 Linux 上跑 RuyiTrace | ❌ 需要完整构建 |

**第 3 条其实很有价值**：如果你手上有 win64 版的 trace 样本，
我们写的解析器**现在就能用**，不需要等 Linux 构建。

---

## 七、建议

| 优先级 | 事 |
| --- | --- |
| 1 | 找一台 32 GB 机器，跑完最后的链接 + 一次真实采集 |
| 2 | 或者：接受「分析已完成」这个状态，用现有解析器处理 win64 样本 |
| 3 | 不要再在 15 GB 机器上重试完整构建 |
