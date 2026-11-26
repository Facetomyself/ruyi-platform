# Candidate D — Linux Electron owner evidence review

**Result:** `bounded_electron_owner_d_evidence_verified_pending_strict_external_review`. Five preregistered cases were independently reviewed per native architecture. The [machine receipt](candidate-d-review.json) records `product_qualified: false` and `human_signoff: false`. This receipt concerns the installed, headful Electron main process owning one Firefox and one BiDi session in an isolated loopback namespace. It grants no physical display, system IME, WebSocket, public-site, or general release credit.

## Observations by architecture

| Preregistered case | Linux ARM64 | Linux AMD64 | Falsification checked |
|---|---|---|---|
| `borrow_return_reborrow` (Xvfb) | Two ordered, authorized fixture clicks; same Firefox and one BiDi session | Same | Borrowed quit releases the lease; next borrower observes the previous page state. Native title effects 1 and 2 occur between writer start/stop. |
| `exclusive_and_stale` (Xvfb) | One authorized effect after negative requests | Same | Competing attach is lease-busy and its click denied; stale, expired and wrong-mode admin requests denied. Original borrower still reads count 0 at that point, then legitimately advances to count 1. The fixture runner also asserts unauthenticated-control denial. |
| `paused_owner_stop` (Weston-headless) | Stop acknowledged 2,089 ms after native RDP pause | Stop acknowledged 2,056 ms after native RDP pause | Native breakpoint at fixture line 5; two ordered `pause-pending` and `resumed` title effects before the writer closes; flush and exactly one BiDi-end acknowledgement. The stopped borrower is denied, within the 30-second watchdog window. |
| `borrower_lost` (Xvfb) | Reborrow acknowledged 121,996 ms after borrower exit observed | Reborrow acknowledged 121,675 ms after borrower exit observed | Borrower SIGKILL, early lease-busy response, production 120-second expiry counter, later attach and unchanged page in the original Firefox/session. This is kill-to-observed-recovery evidence, not an estimate of the exact instant the lease expired. |
| `browser_lost` (Xvfb) | Descriptor revocation observed 156 ms after Firefox SIGKILL | Descriptor revocation observed 76 ms after Firefox SIGKILL | Signal targets the observed Firefox instance; stale query denied; exit 137 and explicit `unclean`, with neither a BiDi-end acknowledgement nor a clean native flush. A JSONL ending on a newline is not a sealed writer. |

The QA runner samples `/proc` for exact Firefox ancestry/start, live namespace isolation and Electron renderer seccomp/no-new-privileges. Timed MCP exchanges record synthetic fixture responses, not page credentials or raw tokens. Separate retained readback binds original state, product result and native writer hashes, plus the byte hashes of each selected raw boundary/effect line. The verifier compares those readbacks to the exact corresponding timed run, rejects historical Candidate C and preliminary D rows, and recomputes the assertions without trusting intake’s `eligible_for_manual_review` as a product verdict.

## Custody

- Product source [`724ef8e147dc1c688601346cb4d25cb3f26a8942`](https://github.com/Facetomyself/ruyitrace/tree/724ef8e147dc1c688601346cb4d25cb3f26a8942); MCP pin `b5e204a76dc3974abadf1fe355392815ddddd6b7`. [Build receipt](custody/build-receipt.json) and [repeat receipt](custody/repeat-build-receipt.json) match byte-for-byte at SHA-256 `f7914d94b77947000e176771d934a28ae2f381c3df3944d5a5de78167e331481`. [Source/readback map](custody/source-inputs.json) records 13 product/build inputs and independently rehashed 91-file inventories of both clean app trees.
- [ARM64 bundle receipt](custody/arm64-bundle-receipt.json) SHA-256 `7cf94a281832de9331cb03d22210993b34f5e1d32d1a47859c434594ba89c131`; [native archive proof](custody/arm64-archive-proof.json), 235,142,912 bytes, SHA-256 `727c9d600721aba58a562b9a8ba55dc303aeb067b70982ec2344e9542aa1db76`.
- [AMD64 bundle receipt](custody/amd64-bundle-receipt.json) SHA-256 `e35f4f879a1fe08125bcc9af68daf10a4a11a3cc805daca064c4feff8a6f495c`; [native archive proof](custody/amd64-archive-proof.json), 239,522,229 bytes, SHA-256 `791e4b0c2fe8b0fa08478b610e8503d0a5fae1a188d494eca44282a864c22829`.
- [Structural contract](custody/contract.json) and [authoritative original/readback hash list](custody/SHA256SUMS) cover the final timed D runs only. The [platform evidence index](evidence-index.json) pins 30 bounded members, including compact, scrubbed renderings of each exact QA receipt and separate native-host readback. Index SHA-256: `5fe4cbf294b5503ed03bd841f18e63fd0002577ecedb9571c41d7c989b341ea0`. Neither predecessor nor candidate-002 evidence supplies any row here.

## Reproduce the independent review

From the platform checkout:

```sh
python3 -B artifacts/receipts/trace-linux-gap-closure-v1/electron-owner/verify_candidate_d.py
python3 -B -m unittest discover -s tests -p 'test_trace_electron_owner_d.py' -v
```

The [offline verifier](verify_candidate_d.py) requires only the standard library and these checked-in evidence files. `--original-runs /path/to/intake` additionally retries the join with exact upstream timed receipts and original readback projections. For a reviewer with approved access to the retained raw bytes, adding `--raw-runs /path/to/raw-runs` rehashes exact product results and writer files; use `<arch>-<case>/result.json` and `<arch>-<case>/domtrace/trace_process_<namespace-pid>.jsonl` under that directory. Keep the raw directories outside Git. No raw descriptor, capability, profile, local namespace PID, private capture path, or binary archive is part of the platform bundle.

The native-host collectors retained the raw records and archive bytes; the default offline review authenticates their recorded SHA commitments against the authoritative manifest and verifies the bounded relationships, rather than locally rehashing the native-host files or acting as a separate live observer. The MCP and process observations share a controlled QA environment. Product provenance, independent hardware/IME witnesses, human external sign-off and formal product signing remain distinct.
