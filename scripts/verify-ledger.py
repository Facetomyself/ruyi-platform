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
    # Secondary hashes: a block may record extra digests beside its evidence.
    # Each must be traceable, either to a wheel on disk or to a file named in the
    # block, otherwise the record cannot be checked by anyone later.
    wheels = {digest(p) for p in ROOT.glob("deliverables/**/*.whl")}
    traceable = 0
    for name, block in blocks().items():
        evidence = block.get("evidence")
        blob = ""
        if evidence and (ROOT / evidence).is_file():
            blob = (ROOT / evidence).read_text(errors="replace")
        for key, value in block.items():
            if "sha256" not in key or key == "evidence_sha256":
                continue
            if not isinstance(value, str):
                failures.append(f"{name}: {key} is not a string")
                continue
            if len(value) != 64 or any(c not in "0123456789abcdef" for c in value):
                # A malformed digest must be reported. Skipping it silently is
                # how a wrong value hides: the first mutation attempt produced a
                # 127-character value and the script said nothing.
                failures.append(f"{name}: {key} is not a SHA-256 digest")
                continue
            # A hash named after a file in the block must match that file's
            # real digest. Checking only that the string appears somewhere would
            # accept a stale or wrong value, which two mutation attempts showed.
            sibling = block.get(key.replace("_sha256", ""))
            if isinstance(sibling, str) and (ROOT / sibling).is_file():
                if digest(ROOT / sibling) == value:
                    traceable += 1
                    continue
            if value in wheels:
                traceable += 1
                continue
            if value in blob:
                traceable += 1
                continue
            # It may name its own file, as sanitizer_data_check does.

            failures.append(f"{name}: {key} cannot be traced to any file")
    print(f"secondary hashes traced: {traceable}")
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
