# Patched Gecko WebSocket V2 — independent Linux/AMD64 acceptance

**Qualified: Linux/AMD64, 22/22** on `sha256:a0cec2d71681234165f6e22d9b8f52f993fdbb6723106152ec74a513b97f8e64`: five WebSocket cases and 17 Wasm, JSCall, and HTTP regressions rerun on these new bytes. The peer and native writer agreed on all eight frames in the positive case; the page separately saw message lengths 5 and 8. The upgrade-only case recorded two closes. Skip, disabled, and wrong-origin cases had complete zero-drop seals; the stock `unsupported` control earned no credit. The [AMD64 case verdict](amd64-review.json) and [full-byte verdict](amd64-full-byte-review.json) are independent of the pinned [ARM64 case verdict](arm64-review.json) and [ARM64 full-byte verdict](arm64-full-byte-review.json). The [two-architecture review](two-architecture-review.json) joins exact digests only: **44 distinct runs, eight gate/architecture cells, 10 WebSocket cases, and 34 regressions**. Scope is approved synthetic loopback on these exact images.

The [AMD64 verifier](verify_amd64.py) consumes the complete native `qualify_patched.py` handoff, both candidate archives, and the original AMD64 Docker baseline. Sources, receipts and native builds remain separate by architecture.

## Native package delta, independently explained

The native AMD64 Firefox TAR.XZ is `25017b78ddd69c0beaac895b93a26ab8d0fcbb597ad5add20a5ae0e1ad2f9982` (81,716,568 bytes). Of 56 original TAR members, **54 are unchanged**. `firefox/libxul.so` is the C++ relink and `firefox/omni.ja` differs for a separate packaging reason. The [native omni review](amd64-native-omni-review.json) independently reads the original root bundle from the exact stock CLI2 Docker archive and the candidate bundle from the actual native TAR.XZ. Of 2,674 ZIP members, 2,673 have identical contents, including all 1,645 JS/MJS and all three Wasm entries. There are no added or removed entries or changed entry order or ZIP entry attributes. The sole payload delta is the exact 36-byte configure-option insertion ` MOZBUILD_STATE_PATH=/root/.mozbuild` in the generated `chrome/toolkit/content/global/buildconfig.html`. [The comparator](verify_amd64_omni.py) reconstructs the entire candidate ZIP byte-for-byte using only that insertion and the corresponding CRC, length, and offset fields. This is build-information text, separate from the app overlay. The full verifier separately reads the installed root omni, libxul, and package JSON from the Docker layer. It requires that overlay to preserve the native build-information HTML and change only the known startup actor hook plus seven exact added modules.

## Required originals

| Input | Expected layout or identity |
|---|---|
| `--qualified` | Completed native producer directory: `identity.json`, `summary.json`, `integrated/summary.json` and all 22 case bundles, `scope/index.json`, `scope/qa-snapshot.tar` and all 22 scope-config/marker pairs, `export/{archive-proof,installed-package,controller}.json`, `offhost/offhost-archive.json`, and four `intake-<gate>/` trees with their candidate, intake result and original observer data. |
| `--kernel-dir` | AMD64 native `lineage.json`, `independent-package.json`, `member-delta.json`; under `logs/`: `candidate-package.json`, `candidate-gecko-websocket-effective.diff`, `candidate-archive-audit.json`, `relinked-libxul-elf.txt`, `candidate.log`, `phases.log`. The baseline is a separate file passed as `--baseline`. |
| `--kernel-tar` | Actual Firefox TAR.XZ named `firefox-159.0.en-US.linux-x86_64.tar.xz`. Upstream BuildID `20261123161729`; x86_64 GNU ELF machine 62. The verifier reads all members and the actual ELF and INI stamps. |
| `--operator-tar` | Actual escrowed Docker TAR.GZ at the filename in the producer export proof. The verifier checks gzip CRC and rehashes the full archive, selected untagged config, and all layer diff IDs. Those identities must agree with the installed image and scope/run originals. |
| `--baseline-docker` | Actual original `ruyitrace-r5-cli2-linux-amd64.docker.tar.gz`, image `sha256:eb73d165ea9adc15864aeb054bc90a78670618c5c0606827997d357f1cae05c6` and archive SHA-256 `8f08567095d752cea64d121a759433eee5c1eb694a10d3e4fe495f058c2b1cd7`. Recomputes the three-way root omni chain. |
| `--image-receipt`, `--patch`, `--native-work`, `--runtime-source` | Original AMD64 installed `image.json`; exact platform-shared V2 C++ patch; the native build helper used to invoke the upstream networking audit; directory containing the ten original runtime source files from commit `f177682d8dc4e028ad450a00f2d78acc4063e321`. The patch SHA-256 is pinned at `3cecbf0b086ff1b630f79ce493d2c4f64782bdf96feb05a9d0a9db57fff3e45b`. |
| `--stock-control`, `--stock-smoke` | Existing AMD64 workload-only `control-amd64.json` and AMD64 `runtime/amd64/smoke-009/`. Historical stock evidence is used to reject substitution, never credited as a patched regression. |

The independently frozen [AMD64 review pins](amd64-review-pins.json) have SHA-256 `55663f92213e105a82f40d3fc18080996e1a75323ca8d2b4c96665d2e7905135`. A separately acquired candidate needs a fresh `ruyitrace.patched-amd64-review-pins.v1` review **after** its actual inputs arrive. The AMD-only omni exception binds this exact native XZ; a different native artifact needs a new independent ZIP comparison and an explicit verifier update. Record:

- `schema` and `platform` (`linux/amd64`), `runtime_source` (fixed above), and runtime `source_set_sha256` (the same admitted ten-file set as ARM).
- `image_id` (`sha256:` form), `kernel_sha256` and `kernel_bytes`, packaged `libxul_sha256` and GNU `elf_build_id`, `operator_sha256` and `operator_bytes`; check these against the actual AMD64 artifacts and independent package/export custody.
- `export_proof_sha256`, `image_receipt_sha256`, `native_omni_review_sha256` (the digest of the independently reconstructed, checked native ZIP report), and `evidence_index_sha256`. The candidate index command reads only the allowlisted originals and prints a digest; it awards no acceptance. Before freezing the digest, review the original set against the expected architecture and handoff.
- `capture_day_utc` (actual `YYYY-MM-DD` UTC day of the complete 22-case lane). Carry the SHA-256 of the **original** reviewer pins file via a separate trusted channel or a reviewed revision; pass that SHA to the verifier. The producer's own summary is checked as a cross-reference, not treated as a release pin or a substitute for any artifact or witness.

```bash
# Run from this receipt directory. Set the named paths from the real AMD64 handoff.
: "${QUALIFIED:?}" "${AMD_KERNEL_DIR:?}" "${RUNTIME_IMAGE_RECEIPT:?}" \
  "${REVIEWER_PINS:?}" "${REVIEWER_PINS_SHA256:?}" "${AMD_KERNEL_TAR:?}" "${AMD_OPERATOR_TAR:?}"
R=/var/lib/dsh/Ruyi/deliverables/ruyitrace-gap-closure.WPnuhkfh
BASE=/var/lib/dsh/Ruyi/deliverables/ruyitrace-resident-cli2.weNViGFr/ruyitrace-r5-cli2-linux-amd64.docker.tar.gz
SRC=/var/lib/dsh/Ruyi/acceptance/trace-linux-gap-closure-v1/product/native-events
INPUTS=(--qualified "$QUALIFIED" --kernel-dir "$AMD_KERNEL_DIR"
        --image-receipt "$RUNTIME_IMAGE_RECEIPT" --baseline "$R/kernel/amd-baseline-archive-readback.json"
        --patch "$SRC/net/gecko159-websocket-metadata-v2.patch" --native-work "$SRC/kernel/native-work.sh"
        --runtime-source "$SRC" --stock-control "$R/control-amd64.json" --stock-smoke "$R/runtime/amd64/smoke-009")
python3 -B verify_amd64.py "${INPUTS[@]}" --index-only
python3 -B verify_amd64.py "${INPUTS[@]}" --pins "$REVIEWER_PINS" --pins-sha256 "$REVIEWER_PINS_SHA256" \
  --kernel-tar "$AMD_KERNEL_TAR" --operator-tar "$AMD_OPERATOR_TAR" --baseline-docker "$BASE"
```

The final command emits one AMD64 review only after release/source identity, exact 22 originals, four intake packets, native build and application/peer/frame witnesses, and full-byte artifact readbacks all pass. A partial directory, stock kernel, ARM64 artifact, mismatched source, or absent archive yields no AMD64 verdict. No network, host mutation, build, polling, Git commit, or product binary is part of this verifier.

## Replay the frozen machine verdicts

[AMD64 originals ZIP](amd64-originals.zip) contains 419 byte-preserved originals (314,749 bytes; SHA-256 `43e2ed51cd7568ed139cff10f6bce799e0d71490af130caa6b4905c0b3bb59ab`). Its pinned per-member size/SHA-256 index is `f9436d2d97abc65794406fd1e4d31ccf50bcab4d2961c8c61cc9d95ff5ebbac4`. Neither the evidence ZIP nor the product binaries need to enter Git.

```bash
# Run from this receipt directory.
PINS=55663f92213e105a82f40d3fc18080996e1a75323ca8d2b4c96665d2e7905135
python3 -B verify_amd64.py --zip amd64-originals.zip --pins amd64-review-pins.json \
  --pins-sha256 "$PINS" --receipt-replay amd64-native-omni-review.json
# The receipt-only replay returns accepted_case_receipts=22 and artifacts_reopened=false.
# With actual binaries, repeat full acceptance from the same ZIP instead of all source paths:
python3 -B verify_amd64.py --zip amd64-originals.zip --pins amd64-review-pins.json --pins-sha256 "$PINS" \
  --kernel-tar "$AMD_KERNEL_TAR" --operator-tar "$AMD_OPERATOR_TAR" --baseline-docker "$BASE"
set -o pipefail
python3 -B join_reviews.py | cmp - two-architecture-review.json
```

Rebuild the originals ZIP with `--pack-originals amd64-originals.zip` in place of `--index-only`, adding `--pins amd64-review-pins.json --pins-sha256 "$PINS"` to the original input command. The case verdict SHA-256 is `b6f269eaa52b32c3b064347750a24825b0dacec5a85c39ed6d1f1fd1cb470494`; the full-byte verdict is `33ffe0f3dd12291d1e4f45585d5ece952c8b86493bf1284619a052b35f1db7e5`. The AMD64 operator archive itself is 508,204,336 bytes, SHA-256 `9e01fc527e4d1c1c123159899797e0f17d670548aff83ebb3c9084caabe56489`.

## Separate operator controls

The [AMD64 operator route/quota capsule readback](amd64-operator-control.json) is outside the 22 registered cases and the originals ZIP. The same installed image delivered 5- and 9-byte text frames on the selected and unselected same-origin routes, respectively; native rows show only the selected 5-byte frame and its closes. An independently witnessed 65,537-byte delivery reached the page, while its native metadata result had two close frames, `drops.limit=1`, `status=partial`, and `complete=false`. The capsule has SHA-256 `3225616bfc6d0df4b4ba61013bb4916b9a01725ece2bb4b781f52869728c5d2b`.

A separate operator-supplement summary (SHA-256 `472ebbc5c9e5881f00ac72399efdf582c4609fb3550c723cb991f2b0c2418bb2`) records opt-in HTTP, redirect and JSCall selections on both final images. Its wrong-document witness lacked IPC-ready and a complete measurement; that is distinct from the registered wrong-origin cases with complete zero-row seals. Supplemental controls add no counts to the two-architecture review.
