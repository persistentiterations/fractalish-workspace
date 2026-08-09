#!/usr/bin/env python3
"""Verify the frozen Bolt-On Demonstrator v0.3 release."""
from __future__ import annotations
from pathlib import Path
import hashlib
import json

EXPECTED_RC_RECORD_SHA256 = "179e5f1cae244df123de3e5edf1000ab1ae186be20c6041d24141560b963f2b2"
EXPECTED_DEVELOPMENT_MANIFEST_SHA256 = "aac2512cc908609ef73c8a94ccd86c74a18b22e004c80a722c391de7cabd3ddc"
EXPECTED_ENTRIES = 20

def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()

def canonical_digest(value: object) -> str:
    payload = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return hashlib.sha256(payload.encode("ascii")).hexdigest()

def main() -> int:
    repository_root = Path(__file__).resolve().parents[1]
    root = repository_root / "frozen" / "bolt_on" / "v0.3"
    manifest = root / "RELEASE_MANIFEST_SHA256.txt"
    if not root.is_dir() or not manifest.is_file():
        print("MISSING v0.3 frozen release")
        return 1
    expected: dict[str, str] = {}
    for line_number, line in enumerate(manifest.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        parts = line.split("  ", 1)
        if (
            len(parts) != 2
            or len(parts[0]) != 64
            or any(character not in "0123456789abcdef" for character in parts[0])
            or not parts[1]
            or parts[1] in expected
        ):
            print(f"INVALID MANIFEST LINE {line_number}: {line}")
            return 1
        expected[parts[1]] = parts[0]
    actual = {
        path.relative_to(root).as_posix()
        for path in root.rglob("*")
        if path.is_file()
        and path != manifest
        and "__pycache__" not in path.parts
        and path.suffix not in {".pyc", ".pyo"}
    }
    failed = False
    for relative in sorted(set(expected) - actual):
        print("MISSING ", relative)
        failed = True
    for relative in sorted(actual - set(expected)):
        print("EXTRA   ", relative)
        failed = True
    for relative in sorted(set(expected) & actual):
        if sha256_file(root / relative) != expected[relative]:
            print("CHANGED ", relative)
            failed = True
    if len(expected) != EXPECTED_ENTRIES:
        print(f"ENTRY COUNT MISMATCH: expected {EXPECTED_ENTRIES}, observed {len(expected)}")
        failed = True
    receipt_path = root / "FREEZE_RECEIPT.json"
    try:
        envelope = json.loads(receipt_path.read_text(encoding="utf-8"))
        record = envelope["record"]
        record_digest = envelope["record_sha256"]
    except Exception as error:
        print(f"INVALID FREEZE RECEIPT: {error}")
        return 1
    if canonical_digest(record) != record_digest:
        print("FREEZE RECEIPT DIGEST MISMATCH")
        failed = True
    if record.get("release") != "v0.3" or record.get("status") != "FROZEN":
        print("FREEZE RECEIPT RELEASE STATUS MISMATCH")
        failed = True
    if record.get("rc_record_sha256") != EXPECTED_RC_RECORD_SHA256:
        print("FREEZE RECEIPT RC BINDING MISMATCH")
        failed = True
    if record.get("development_manifest_sha256") != EXPECTED_DEVELOPMENT_MANIFEST_SHA256:
        print("FREEZE RECEIPT DEVELOPMENT BINDING MISMATCH")
        failed = True
    if failed:
        print("BOLT-ON v0.3 FROZEN VERIFICATION FAILED")
        return 1
    print(f"BOLT-ON v0.3 FROZEN VERIFICATION PASSED: {len(expected)} files")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
