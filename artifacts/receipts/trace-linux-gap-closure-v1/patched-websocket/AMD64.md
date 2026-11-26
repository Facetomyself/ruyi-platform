# AMD64 independent intake (pending native evidence)

The [AMD64 verifier](verify_amd64.py) consumes the complete native `qualify_patched.py` handoff and both actual artifacts. This file describes how to review future AMD64 evidence; it carries no AMD64 acceptance result or speculative artifact IDs. The [ARM64 verdict](arm64-review.json), [full-byte verdict](arm64-full-byte-review.json), ZIP, and pin set remain independent and unchanged.

## Required originals

| Input | Expected layout or identity |
|---|---|
| `--qualified` | Completed native producer directory: `identity.json`, `summary.json`, `integrated/summary.json` and all 22 case bundles, `scope/index.json`, `scope/qa-snapshot.tar` and all 22 scope-config/marker pairs, `export/{archive-proof,installed-package,controller}.json`, `offhost/offhost-archive.json`, and four `intake-<gate>/` trees with their candidate, intake result and original observer data. |
| `--kernel-dir` | AMD64 native `lineage.json`, `independent-package.json`, `member-delta.json`; under `logs/`: `candidate-package.json`, `candidate-gecko-websocket-effective.diff`, `candidate-archive-audit.json`, `relinked-libxul-elf.txt`, `candidate.log`, `phases.log`. The baseline is a separate file passed as `--baseline`. |
| `--kernel-tar` | Actual Firefox TAR.XZ named `firefox-159.0.en-US.linux-x86_64.tar.xz`. Upstream BuildID `20261123161729`; x86_64 GNU ELF machine 62. The verifier reads all members and the actual ELF and INI stamps. |
| `--operator-tar` | Actual escrowed Docker TAR.GZ at the filename in the producer export proof. The verifier checks gzip CRC and rehashes the full archive, selected untagged config, and all layer diff IDs. Those identities must agree with the installed image and scope/run originals. |
| `--image-receipt`, `--patch`, `--native-work`, `--runtime-source` | Original AMD64 installed `image.json`; exact platform-shared V2 C++ patch; the native build helper used to invoke the upstream networking audit; directory containing the ten original runtime source files from commit `f177682d8dc4e028ad450a00f2d78acc4063e321`. The patch SHA-256 is pinned at `3cecbf0b086ff1b630f79ce493d2c4f64782bdf96feb05a9d0a9db57fff3e45b`. |
| `--stock-control`, `--stock-smoke` | Existing AMD64 workload-only `control-amd64.json` and AMD64 `runtime/amd64/smoke-009/`. Historical stock evidence is used to reject substitution, never credited as a patched regression. |

The reviewers must freeze one `ruyitrace.patched-amd64-review-pins.v1` JSON object **after** the actual inputs arrive. Record:

- `schema` and `platform` (`linux/amd64`), `runtime_source` (fixed above), and runtime `source_set_sha256` (the same admitted ten-file set as ARM).
- `image_id` (`sha256:` form), `kernel_sha256` and `kernel_bytes`, packaged `libxul_sha256` and GNU `elf_build_id`, `operator_sha256` and `operator_bytes`; check these against the actual AMD64 artifacts and independent package/export custody.
- `export_proof_sha256`, `image_receipt_sha256`, and `evidence_index_sha256`. The candidate index command reads only the allowlisted originals and prints a digest; it awards no acceptance. Before freezing the digest, review the original set against the expected architecture and handoff.
- `capture_day_utc` (actual `YYYY-MM-DD` UTC day of the complete 22-case lane). Carry the SHA-256 of the **original** reviewer pins file via a separate trusted channel or a reviewed revision; pass that SHA to the verifier. The producer's own summary is checked as a cross-reference, not treated as a release pin or a substitute for any artifact or witness.

```bash
# Run from this receipt directory. Set the named paths from the real AMD64 handoff.
: "${QUALIFIED:?}" "${AMD_KERNEL_DIR:?}" "${RUNTIME_IMAGE_RECEIPT:?}" \
  "${REVIEWER_PINS:?}" "${REVIEWER_PINS_SHA256:?}" "${AMD_KERNEL_TAR:?}" "${AMD_OPERATOR_TAR:?}"
R=/var/lib/dsh/Ruyi/deliverables/ruyitrace-gap-closure.WPnuhkfh
SRC=/var/lib/dsh/Ruyi/acceptance/trace-linux-gap-closure-v1/product/native-events
INPUTS=(--qualified "$QUALIFIED" --kernel-dir "$AMD_KERNEL_DIR"
        --image-receipt "$RUNTIME_IMAGE_RECEIPT" --baseline "$R/kernel/amd-baseline-archive-readback.json"
        --patch "$SRC/net/gecko159-websocket-metadata-v2.patch" --native-work "$SRC/kernel/native-work.sh"
        --runtime-source "$SRC" --stock-control "$R/control-amd64.json" --stock-smoke "$R/runtime/amd64/smoke-009")
python3 -B verify_amd64.py "${INPUTS[@]}" --index-only
python3 -B verify_amd64.py "${INPUTS[@]}" --pins "$REVIEWER_PINS" --pins-sha256 "$REVIEWER_PINS_SHA256" \
  --kernel-tar "$AMD_KERNEL_TAR" --operator-tar "$AMD_OPERATOR_TAR"
```

The final command emits one AMD64 review only after release/source identity, exact 22 originals, four intake packets, native build and application/peer/frame witnesses, and full-byte artifact readbacks all pass. A partial directory, stock kernel, ARM64 artifact, mismatched source, or absent archive yields no AMD64 verdict. No network, host mutation, build, polling, Git commit, or product binary is part of this verifier.
