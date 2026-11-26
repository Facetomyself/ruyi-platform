# Patched Gecko WebSocket V2 — independent Linux/ARM64 acceptance

**Qualified: Linux/ARM64, 22/22** on installed image `sha256:ecb43c4ef8f448d41bce4213954bb202d308287fc21826ad38952b52e331c8ab`. This is five WebSocket cases plus **17 regressions rerun on those same new bytes**: six Wasm, five JSCall and six HTTP. This ARM-specific proof was not used to qualify a different architecture: [AMD64 has its own 22/22 independent verification](AMD64.md) and a separate full-byte verdict. The [joined report](two-architecture-review.json) checks all 44 distinct run identities. These receipts cover only the approved, operator-selected loopback synthetic workloads.

## What was observed

| Gate | Original cases | Finding |
|---|---:|---|
| WebSocket | 5 | Real fragmentation and control frames; upgrade/close-only; sealed skip, disabled, and other-origin zeros |
| Wasm | 6 | Three exact export entry/return pairs, one entry/trap pair, four sealed zeros |
| JSCall | 5 | Three exact `fixedAdd` entry/return pairs, one entry/throw pair, three sealed zeros |
| HTTP | 6 | Fetch 200, linked redirect 302/200, one cache transaction with independent prewarm and no measured GET, three sealed zeros |

The independent peer decoded `C→S` text **5**, pong **1**, close **2** and `S→C` text **5**, non-FIN text **4**, ping **1**, FIN continuation **4**, close **2**. The native JSONL has one opaque connection ID and this chronological sequence: TX text 5 → RX text 5 → RX non-FIN text 4 → RX ping 1 → TX pong 1 → RX FIN continuation 4 → TX close 2 → RX close 2. The browser page separately saw two application messages, lengths **5 and 8**. That page result is a message-layer control, not a frame transcript. Upgrade-only yielded one close per direction and zero data frames; skipped had no upgrade or frames; disabled and wrong-origin cases had real peer upgrades and eight peer frames but zero native rows. The historical stock-kernel smoke had `status=unsupported`, `complete=false`, and lacked an armed receipt: it is **not** a sealed zero and earns no product credit.

The complete writer receipts agree on run, mode, exact loopback origin and admitted document, writer/content PID, browsing context, and inner window. Each case joins the scope config and control marker readback, host attempt and layer chain, writer OS provenance, workload/peer witnesses, intact JSONL, seal, and the original SHA-256s in the intake packet. Whole output enumeration excludes additional native files and `.pending` output. Every qualified seal is `ok`, `complete=true`, with all five drop buckets zero and child sent/seen equal; positive counts were recomputed from original rows. Structural intake reports remain `eligible_for_manual_review`; the independent verdict is [arm64-review.json](arm64-review.json), not an intake status promotion.

## Source, native package, and transport

- Runtime source is `f177682d8dc4e028ad450a00f2d78acc4063e321`, source-set SHA-256 `d97edbcbb9e3d9849518d8b00f1ac24ff7b0b5ba6266ce436c69b9b46472baf5`. Ten source files and the seven installed module hashes join the export and installed image manifests.
- Gecko source is `9a2dc53c369c7ae5172018b35988e1d2ffeff402`, tree `7a8dd864f3e99cc350dbb47dcaf123fe60218c51`, V2 patch SHA-256 `3cecbf0b086ff1b630f79ce493d2c4f64782bdf96feb05a9d0a9db57fff3e45b`. Compile, link, package, and readback records join the applied source diff and ELF. The native package changes **only `firefox/libxul.so`**, with 55 unchanged members. The app image overlay separately updates the top-level `omni.ja`. Firefox 159.0 retains upstream BuildID `20261125162841`; the packaged/relinked GNU ELF Build ID is `8c6ec61b11b671e14bdcefbca4c9a79b23a357cf`. The original upstream `mozbuild.action.check_binary --networking` audit passed on the unchanged Rust archive before/after audit.
- The parent-only V2 listener receives a scoped channel plus the serial, direction, opcode, FIN, and length; no payload, mask, protocol, or URL string crosses the frame callback. Rows contain only the documented scalar fields and a scope-local opaque connection ID. The 128-frame / eight-connection / 65,536-byte-length native budget is enforced by code, with diagnostics bounded at 65,535. Native stop atomically disables collection and combines queued callbacks, incomplete sends, and failures; the overlay folds rejected budget work into `drops.limit` and native failures/pending into `drops.protocol`. A complete zero-drop seal thus certifies the aggregate, not separate persisted pending counters. The independent [synthetic tests](../../../../tests/test_trace_native_ws_v2.py) reject loss, IO/limit/protocol drops, pending artifacts, frame synthesis, mixed identity and forged unsupported zeros.
- The measured default socket process stayed **enabled and launched**; `network.http.network_access_on_socket_process.enabled=false`, and `MOZ_FORCE_USE_SOCKET_PROCESS` was absent. This keeps the selected WebSocket on the supported parent transport; it is **not** a sandbox or socket-process disable. These original seals attest the default configuration, not support for delegated transport or every possible browser configuration.

Two separately collected operator controls on the same image corroborate the boundaries but are **outside the 22-case verdict and ZIP**. The exact-route control delivered text frames of 5 and 9 bytes to the page on two same-origin routes; native output includes only the selected route's 5-byte RX and its two close frames. The quota control delivered one 65,537-byte text frame to the page intact; native output has only its two close frames, with `drops.limit=1`, `status=partial`, and `complete=false`. The [separate off-host operator-control readback](arm64-operator-control.json) binds these results. The ARM64 operator-control capsule has SHA-256 `c95d3ca7042877703512b0ae35cfc688e55fc47fba429acb3218f0bb36c59b30`.

## Offline reproduction

[verify.py](verify.py) uses only Python's standard library. [pack_arm64.py](pack_arm64.py) maps named originals to their source paths and writes a ZIP only when the index hash matches. The optional evidence-only archive [arm64-originals.zip](arm64-originals.zip) is 298,346 bytes, SHA-256 `030749d53b246e7151687fd70994bde8ad440421d70ecbee00384d699caf7ee3`. Its 417 originals are indexed by original length and SHA-256; index SHA-256 `185aac65ddd85fd0b8973e18981fe37ba6c7b1edba3bc85473ad5a4b6cac71f3`. The checked-in ZIP is the allowlisted small evidence capsule; executable product archives remain outside Git. It can be regenerated from the specified originals. It contains textual evidence, exact QA sources, and framed copies of original receipts, without product executables, credentials, profiles, or captured payloads.

```bash
PLATFORM=/var/lib/dsh/Ruyi/acceptance/platform-trace-gap-closure-v1
D="$PLATFORM/artifacts/receipts/trace-linux-gap-closure-v1/patched-websocket"
R=/var/lib/dsh/Ruyi/deliverables/ruyitrace-gap-closure.WPnuhkfh

# If the original-byte ZIP has not been supplied, regenerate it from the allowlisted receipts.
python3 -B "$D/pack_arm64.py" "$R" \
  /var/lib/dsh/Ruyi/acceptance/trace-linux-gap-closure-v1/product/native-events "$D/arm64-originals.zip"

set -o pipefail
python3 -B "$D/verify.py" | cmp - "$D/arm64-review.json"
python3 -B -m unittest discover -s "$PLATFORM/tests" -p test_trace_native_ws_v2.py -v

# Optional: repeat the full-byte, read-only check against escrowed binaries.
python3 -B "$D/verify.py" --artifact-report \
  --kernel-tar "$R/kernel/aarch64/firefox-159.0.en-US.linux-aarch64.tar.xz" \
  --operator-tar "$R/offhost-arm64-kernelv2-01/ruyitrace-native-arm64-ecb43c4ef8f448d4.docker.tar.gz" \
  | cmp - "$D/arm64-full-byte-review.json"
```

[arm64-full-byte-review.json](arm64-full-byte-review.json) independently rehashes the actual native Firefox TAR.XZ and all 56 members, reads its ELF machine and Build ID notes and both INI stamps, and rehashes the complete operator Docker TAR.GZ, including gzip CRC, selected config ID and all five layer diff IDs. The native Firefox archive is `53747262e3af06ec0e4b98806efed38225b51b3c83b8b8d877eba133e4c9eacf` (74,812,416 bytes); the operator archive is `10d940ce5a502fe7652ae7685534e16c7fdeb03579ea48d730453597e458ee33` (494,839,061 bytes). Neither product archive belongs in Git.
