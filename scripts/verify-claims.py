#!/usr/bin/env python3
"""Check that the capabilities the ledger claims still exist in the source.

The ledger records what was delivered. The source can drift away from it — a
function renamed, a builder dropped from the wheel map — and every receipt would
still verify, because receipts describe the past. This script compares a small
set of load-bearing claims against the tree as it stands now.
"""
import re
import sys
from pathlib import Path

PLATFORM = Path(__file__).resolve().parents[1]
ROOT = PLATFORM.parents[1]
REPO = ROOT / "acceptance" / "r354-ruyijs"
TLS = REPO / "linux_http1" / "ruyijs_necko" / "tls.py"
BACKEND = REPO / "linux_http1" / "build_backend.py"
CHAIN = REPO / "linux_http1" / "native_tls_chain_verify.c"

# (file, needle, what the ledger says this provides)
REQUIRED = [
    (TLS, "def _decode_brotli", "brotli decoding"),
    (TLS, "def _decode_zstd", "zstd decoding"),
    (TLS, "def _offerable_encodings", "advertising only decodable codings"),
    (TLS, "def _accepted_alpn", "refusing a peer that selects h2"),
    (TLS, "def _enforce_cutoff", "per-root distrust cutoffs"),
    (CHAIN, "static int trust_anchors", "caller-supplied anchors are imported and trusted"),
    (BACKEND, "def compile_brotli", "brotli built from in-tree sources"),
    (BACKEND, "def compile_zstd", "zstd built from in-tree sources"),
    (BACKEND, "compile_brotli(sdk_root())", "brotli wired into the wheel", True),
    (BACKEND, "compile_zstd(sdk_root())", "zstd wired into the wheel", True),
    (BACKEND, "check_committed", "build refuses uncommitted sources"),
    (CHAIN, "int chain_verify_ocsp", "the OCSP entry point is defined"),
]

# Things the ledger says are NOT delivered. Their absence is the claim.
ABSENT_CALLS = [
    (CHAIN, "CERT_CheckCRL(", "CRL is not used (declared upstream, not exported)"),
]


def main():
    failures = []
    checked = 0
    for entry in REQUIRED:
        path, needle, claim = entry[0], entry[1], entry[2]
        literal = len(entry) > 3 and entry[3]
        checked += 1
        if not path.is_file():
            failures.append(f"{path.name} is missing, so '{claim}' cannot hold")
            continue
        text = path.read_text(errors="replace")
        # Match the definition itself, not a longer name that starts the same
        # way: "def _decode_brotli" is a prefix of "def _decode_brotli_GONE",
        # which a mutation test used to slip past a plain substring check.
        pattern = re.escape(needle) if literal else re.escape(needle) + r"\("
        if not re.search(pattern, text):
            failures.append(f"{path.name} lacks {needle!r}: '{claim}' is no longer true")
    for path, needle, claim in ABSENT_CALLS:
        checked += 1
        if path.is_file() and needle in path.read_text(errors="replace"):
            failures.append(f"{path.name} calls {needle!r} although '{claim}'")
    print(f"claims checked: {checked}")
    if failures:
        for item in failures:
            print(f"  FAIL {item}")
        print(f"failures: {len(failures)}")
        return 1
    print("source still matches every claim listed above")
    return 0


if __name__ == "__main__":
    sys.exit(main())
