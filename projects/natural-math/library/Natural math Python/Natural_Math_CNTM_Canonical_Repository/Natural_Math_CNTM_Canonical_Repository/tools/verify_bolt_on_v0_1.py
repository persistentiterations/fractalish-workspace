#!/usr/bin/env python3
"""Verify the frozen Bolt-On Demonstrator v0.1 release."""

from __future__ import annotations

import hashlib
from pathlib import Path
import sys


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def main() -> int:
    repo_root = Path(__file__).resolve().parents[1]
    release_root = repo_root / "frozen" / "bolt_on" / "v0.1"
    manifest_path = release_root / "RELEASE_MANIFEST_SHA256.txt"

    if not release_root.is_dir():
        print(f"MISSING  {release_root}")
        return 1
    if not manifest_path.is_file():
        print(f"MISSING  {manifest_path}")
        return 1

    expected: dict[str, str] = {}
    for line_number, raw_line in enumerate(
        manifest_path.read_text(encoding="utf-8").splitlines(), start=1
    ):
        line = raw_line.strip()
        if not line:
            continue
        parts = line.split("  ", 1)
        if len(parts) != 2:
            print(f"INVALID MANIFEST LINE {line_number}: {raw_line}")
            return 1
        digest, relative = parts
        if len(digest) != 64 or relative in expected:
            print(f"INVALID MANIFEST ENTRY {line_number}: {raw_line}")
            return 1
        expected[relative] = digest.lower()

    actual_files = {
        path.relative_to(release_root).as_posix()
        for path in release_root.rglob("*")
        if path.is_file() and path != manifest_path
    }

    expected_files = set(expected)
    missing = sorted(expected_files - actual_files)
    extra = sorted(actual_files - expected_files)

    failed = False

    for relative in missing:
        print(f"MISSING  {relative}")
        failed = True

    for relative in extra:
        print(f"EXTRA    {relative}")
        failed = True

    for relative in sorted(expected_files & actual_files):
        path = release_root / Path(relative)
        actual_digest = sha256(path)
        if actual_digest == expected[relative]:
            print(f"OK       frozen/bolt_on/v0.1/{relative}")
        else:
            print(f"CHANGED  frozen/bolt_on/v0.1/{relative}")
            print(f"         expected: {expected[relative]}")
            print(f"         actual:   {actual_digest}")
            failed = True

    if failed:
        print()
        print("BOLT-ON v0.1 FROZEN VERIFICATION FAILED")
        return 1

    print()
    print(
        f"BOLT-ON v0.1 FROZEN VERIFICATION PASSED: "
        f"{len(expected_files)} files"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
