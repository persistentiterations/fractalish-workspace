#!/usr/bin/env python3
"""Verify the authorized Bolt-On Continuity for Docker v0.3 frozen release."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RELEASE = ROOT / "frozen" / "bolt_on_continuity" / "v0.3"
EXPECTED = {
    "README.md": (1411, "af8cd834b057556b42f070b9aa5af61a240f6a641910b956433d72d67edb293a"),
    "RELEASE_RECORD.txt": (1259, "47b85e878200a756417c966541d7088b1695ba2e74efc79c1f6e8cb4b76ad9e9"),
}
EXPECTED_MANIFEST = "3ce662d9be77735a9de53086160a3b2589f1b0feabcebba1551b080702f821bb"


def fail(message: str) -> None:
    raise SystemExit(f"BOLT-ON CONTINUITY v0.3 FROZEN VERIFICATION FAILED: {message}")


def main() -> int:
    actual_names = {path.name for path in RELEASE.iterdir()} if RELEASE.is_dir() else set()
    if actual_names != set(EXPECTED):
        fail(f"file set mismatch: {sorted(actual_names)}")

    entries = []
    for name in sorted(EXPECTED):
        path = RELEASE / name
        data = path.read_bytes()
        expected_bytes, expected_sha = EXPECTED[name]
        actual_sha = hashlib.sha256(data).hexdigest()
        if len(data) != expected_bytes:
            fail(f"byte count mismatch for {name}")
        if actual_sha != expected_sha:
            fail(f"SHA-256 mismatch for {name}")
        entries.append({"path": name, "bytes": len(data), "sha256": actual_sha})
        print(f"OK       frozen/bolt_on_continuity/v0.3/{name}")

    payload = json.dumps(entries, sort_keys=True, separators=(",", ":")).encode("utf-8")
    manifest = hashlib.sha256(payload).hexdigest()
    if manifest != EXPECTED_MANIFEST:
        fail("release manifest mismatch")

    print("Source commit: 67e0da7e41e96870d8dbeafa8031e4de694bb03f")
    print(f"Release manifest SHA-256: {manifest}")
    print("BOLT-ON CONTINUITY v0.3 FROZEN VERIFICATION PASSED: 2 files")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
