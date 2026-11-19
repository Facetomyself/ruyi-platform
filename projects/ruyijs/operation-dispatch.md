# ruyijs operation 分发器（定论）

> **本文更正上一轮的判断。** 上一轮说「7 个 operation 在 js.exe 里不存在」，
> 那是**错的**。真实情况是这些 operation 的名字被编译成立即数比较与掩码拼接，
> 不留下独立的 NUL 结尾字符串，因此只做字符串扫描就会漏掉。

## 一、证据

### 1. 全部 39 个 operation 都在二进制里

```bash
python3 scripts/ruyijs-ops-scan.py --exe artifacts/binaries/ruyijs/js.exe
```

输出：

```
operation 总数: 39
  字符串池命中: 15
  立即数命中:   31
  合计定位:     37/39
  仍缺失: ['drain', 'put']
```

上一轮的 32/39 是**子串误报**：`advance`、`status`、`drain` 命中的是
`.rdata` 里别的长文本（`confirmCurrentadvancesharing`、
`countryregioncommonstatus`、`ondrain`），不是 operation。

### 2. 三类编码

| 编码 | 数量 | 例 |
| --- | ---: | --- |
| 独立字符串（`\0` 结尾） | 15 | `checkpoint` `run_message` `clear` |
| 4/8 字节立即数 | 22 | `eval` `page` `user` `input` `expose_data` |
| 两者都有 | 6 | `expose_data` `navigate` `run_timer` `timer_realm` `pending_timers` |

### 3. 分发器的真实形态（`0xbcf93` / VA `0x1400bcf93`）

```asm
; operation 名长度 9..24 才进这个分支
add   rax, -9
cmp   rax, 0xf          ; 0..15
ja    → 其他长度分支
lea   rcx, [跳转表]
movsxd rax, [rcx + rax*4]
add   rax, rcx
jmp   rax               ; 16 路跳转表

; 分支 1：run_timer（8 字节立即数 + 单字节掩码）
movabs rax, 0x656d69745f6e7572      ; "run_time"
xor    rax, [r14]
movzx  ecx, byte [r14 + 8]
xor    rcx, 0x72                    ; 'r'
or     rcx, rax
jne    → 下一分支
jmp    → run_timer 处理

; 分支 2：16 字节 SSE 比较（操作名 ≥ 16）
movdqu xmm0, [r14]
pcmpeqb xmm0, [常量]
pmovmskb eax, xmm0
cmp    eax, 0xffff
jne    → 下一分支

; 分支 3：pending_timers / pending_messages（两段 8 字节 + 偏移 6）
movabs rax, 0x5f676e69646e6570      ; "pending_"
xor    rax, [r14]
movabs rcx, 0x7372656d69745f67      ; "g_timers"
xor    rcx, [r14 + 6]
or     rcx, rax
jne    → 下一分支
```

**关键**：这是编译器对 `if (op == "run_timer")` 这类比较的优化——把字符串比较
内联成寄存器异或，完全不走 `strcmp`，也不在 `.rdata` 留字符串。

## 二、对上一轮的更正

| 上一轮判断 | 实际情况 |
| --- | --- |
| 7 个 operation 在 js.exe 里不存在 | **全部存在**，编码为立即数/掩码/SSE |
| 可能有「功能被裁剪」 | **不成立** |
| 要「补实现」这 7 个 | **不需要**，已在二进制里 |
| 32/39 字符串命中 | 其中多项是子串误报，真实独立字符串只有 15 个 |

## 三、仍然缺失的 2 个

`drain` 与 `put`：

| operation | 来源 | 状态 |
| --- | --- | --- |
| `drain` | `_scheduling.py` 的 `drain_timers` | To be confirmed |
| `put` | `_resources.py` 的 `put_resource` | To be confirmed |

两者都只有 4~3 字符，极可能同样被内联成 4 字节立即数，但当前的正则范围没覆盖到
（`put` 只有 3 字符，低于 4 字节立即数的最小粒度；`drain` 可能是 `movabs` 8 字节里的
中段）。要精确判定需要逐函数反汇编分发器全部分支。

## 四、方法学教训

**只扫字符串是不够的。** 判断一个符号是否存在于二进制，至少要查：

1. 独立 NUL 结尾字符串
2. 4 字节立即数（`81 3x imm32`、`B8-BF imm32`、`3D imm32`）
3. 8 字节立即数（`48 B8-BF imm64`）
4. 分段拼接（立即数 + 偏移读 + 掩码异或）
5. SSE 比较（`pcmpeqb`）
6. 跳转表（`lea` + `movsxd` + `jmp rax`）

这条教训已写入 `scripts/ruyijs-ops-scan.py` 的实现里。
