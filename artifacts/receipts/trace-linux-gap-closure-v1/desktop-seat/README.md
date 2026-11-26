# Desktop seat: clean D evidence with four gates held

**Disposition:** `technical_evidence_verified_physical_display_and_system_ime_held`. Linux ARM64 and AMD64 each have an actual clean D virtual-seat run, but neither architecture has formal approval for physical display or system IME. The [machine receipt](desktop-seat-review.json) reports `formal_approvals: 0`, `human_signoff: false` and `product_qualified: false`. This receipt does not alter the separately frozen Electron owner, native events, or WebSocket reviews.

| Evidence | Linux ARM64 | Linux AMD64 |
|---|---:|---:|
| Actual clean D field receipts | 4/4 | 4/4 |
| Accepted stock GTK callbacks | 164: 153 in round windows + 11 outside | 144: 137 in round windows + 7 outside |
| Detected sequencing gaps / rejected callbacks / overflow | 0 / 0 / 0 | 0 / 0 / 0 |
| Strict product checks under the virtual fixture | Equal paste control only | Equal paste control only |
| Formal physical display / system IME approval | Held / held | Held / held |

## What the observations establish

- **IME selection:** Stock IBus Pinyin showed visible lookup, rank 2 and one equal stock GTK commit. The clean product matched final text, yet recorded one untrusted event in aggregate, one other input, and zero matching trusted ends. Equality alone does not satisfy the browser IME gate.
- **Cancel:** Native side recorded zero GTK commits and the field ended empty. The clean product still had an untrusted event and no trusted composition end. The select and cancel controls remain technically held.
- **Paste:** Equal fixture text through one paste event and one paste input, zero composition and zero stock GTK commits or visible lookup. This is a passing negative control, not a passing IME claim.
- **Active focus change:** The second field received focus during composition. The first field remained nonempty, the second remained empty, and the clean product recorded one untrusted event in aggregate and zero trusted matching delayed ends. The stock GTK observer saw zero commits inside this round's bounded window; it was bound to the exact product peer, not mapped to individual DOM fields or post-window activity.
- **Dirty ARM diagnostic:** The separate diagnostic artifact compared wrapped and unwrapped stock GTK. Rank-2 selection, Escape and pointer focus each produced one **untrusted `compositionend`**, zero trusted ends, before the Record click. The diagnostic had different app, fixture and bundle hashes. It characterizes those diagnostic runs and **does not assign an event type to the clean D untrusted aggregate**.
- **Display:** The native ARM64 XCB fixture differentiated one real pixmap-copy completion from one `NotifyMSC` timer completion and rejected the wrong owner before arming. In a different clean D Xvfb window, three resizes were observed and restored; **zero Present completion notifications in a completed 6.006-second window**. This is an exact-window observation, not evidence of missing paint, final scanout, or the renderer's internal backend. Both architecture-specific Xvfb window controls were viewable and sandboxed yet lacked an active physical output or seat witness. Native Present calibration ran on ARM64 only.
- **Earlier ARM64 observer:** Its 108 native callbacks and three linked product field rounds established a technical precursor. It is preserved separately from the final four-round data and supplies no missing fourth round or AMD64 approval.

## Byte custody and offline replay

The [evidence index](evidence-index.json) pins 19 files to SHA-256 `bca250f5ea50ffbecc6cfd4529d42128fef3b2c88cfbd628cfa201e2125f669f`. It preserves exact SHA-bound clean and diagnostic counts, summaries and source manifests. PID-, run-ID- or path-bearing capture artifacts are represented by narrow projections with both source and projection SHA commitments; the original receipts stay in the protected lab evidence root. No binary kits, archives, raw profiles, typed fixture values, or live session data are in the platform receipt.

Authoritative sources: [clean D reconciliation](</var/lib/dsh/Ruyi/deliverables/ruyitrace-gap-closure.WPnuhkfh/seat-reconciliation/REPORT.md>), [ARM64 Present calibration](</var/lib/dsh/Ruyi/deliverables/ruyitrace-gap-closure.WPnuhkfh/present-observer/RESULT.json>), [earlier native observer](</var/lib/dsh/Ruyi/deliverables/ruyitrace-gap-closure.WPnuhkfh/seat-observer/RESULT.json>), and [private release download readback](<evidence/desktop-alpha/github-release-proof.json>). The final actual-run projections are [ARM64](<evidence/seat-reconciliation/arm64-clean-D-fixture-selection.json>) and [AMD64](<evidence/seat-reconciliation/amd64-clean-D-fixture-selection.json>).

From the platform checkout:

```sh
python3 -B artifacts/receipts/trace-linux-gap-closure-v1/desktop-seat/verify_desktop_seat.py
python3 -B -m unittest discover -s tests -p 'test_trace_desktop_seat_held.py' -v
```

The [verifier](verify_desktop_seat.py) recomputes the bounded checks and has no human-pass path. `--originals-root /path/to/evidence-root` additionally rehashes exact upstream files, reproduces the scrubbed projections, and rehashes separately held tool archives. It does not relaunch Electron, IBus, or X11, and does not act as an independent in-person witness.

## Published operator handoff

Use the private [desktop alpha release](https://github.com/Facetomyself/ruyitrace/releases/tag/linux-electron-owner-v0.1.0-alpha.1), [operator guide](https://github.com/Facetomyself/ruyitrace/releases/download/linux-electron-owner-v0.1.0-alpha.1/DESKTOP-ALPHA-ZH.md) and [published seat operator kit v1](https://github.com/Facetomyself/ruyitrace/releases/download/linux-electron-owner-v0.1.0-alpha.1/seat-operator-kit-v1.tar.gz) with the pinned clean software source `724ef8e147dc1c688601346cb4d25cb3f26a8942`. The independently rehashed v1 kit is `bd6ddaa4c2c0fcb0e80361db196aeb5a46588df1c4e0981b18132fbb603f0d8c`. The separate [native observer v2](</var/lib/dsh/Ruyi/deliverables/ruyitrace-gap-closure.WPnuhkfh/seat-observer/seat-observer-kit-v2.tar.gz>) (`59ac75105b0ebe6db296f1223b09d5baa9621c6a58554fe02197f80be732e5e1`) and [technical QA supplement](</var/lib/dsh/Ruyi/deliverables/ruyitrace-gap-closure.WPnuhkfh/seat-reconciliation/seat-technical-qa-kit-v1.tar.gz>) (`0650dd6d5f5ef22695c4c269a27c2d5f1cf03c524636a00670844633eae8488a`) are technical companions, not changes to the released software, operator kit, or pass criteria.

Per architecture, formal display still needs an enrolled bare-metal local Linux Xorg seat, an active physical connector/mode, and an independent in-person panel witness who returns both ordered fresh challenges before comparison. Formal IME still needs an actual local operator on the appropriate clean build, four complete native and product rounds with the established trust/commit/focus checks, and independent review. A future run should preserve an observed failure instead of replacing the active-focus case with an Escape-first workaround.
