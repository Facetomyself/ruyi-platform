#!/usr/bin/env python3
"""Check that every RuyiJS ledger block points at real, matching evidence.

The ledger is the only place that records what was delivered, so a broken link
or a stale hash there silently converts a verified claim into an unverifiable
one. This script is the check that claim implies.
"""
import hashlib
import sys
from pathlib import Path

import yaml

PLATFORM = Path(__file__).resolve().parents[1]
ROOT = PLATFORM.parents[1]          # /var/lib/dsh/Ruyi
SECTION = ("projects", "ruyijs", "verified",
           "private_linux_x86_donor_source", "guarded_build")


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def blocks():
    data = yaml.safe_load((PLATFORM / "STATUS.yaml").read_text())
    scope = data
    for key in SECTION:
        scope = scope[key]
    return {k: v for k, v in scope.items() if isinstance(v, dict)}


def main():
    failures = []
    total = 0
    for name, block in blocks().items():
        total += 1
        evidence = block.get("evidence")
        if not evidence:
            failures.append(f"{name}: no evidence field")
            continue
        path = ROOT / evidence
        if not path.is_file():
            failures.append(f"{name}: evidence missing at {evidence}")
            continue
        recorded = block.get("evidence_sha256")
        if not recorded:
            failures.append(f"{name}: no evidence_sha256")
        elif digest(path) != recorded:
            failures.append(f"{name}: evidence hash differs from the record")
        receipt = block.get("repository_receipt")
        if receipt:
            copy = PLATFORM / receipt
            if not copy.is_file():
                failures.append(f"{name}: receipt missing at {receipt}")
            elif copy.read_bytes() != path.read_bytes():
                failures.append(f"{name}: receipt is not a copy of the evidence")
    print(f"blocks checked: {total}")
    if failures:
        for item in failures:
            print(f"  FAIL {item}")
        print(f"failures: {len(failures)}")
        return 1
    print("all evidence present, hashes match, receipts identical")
    return 0


if __name__ == "__main__":
    sys.exit(main())
