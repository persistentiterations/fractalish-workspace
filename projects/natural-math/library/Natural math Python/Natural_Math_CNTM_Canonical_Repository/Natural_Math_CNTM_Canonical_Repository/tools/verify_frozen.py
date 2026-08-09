#!/usr/bin/env python3
from __future__ import annotations

import hashlib
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "manifests" / "SHA256SUMS.txt"


def digest(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def main() -> int:
    errors: list[str] = []
    checked = 0
    for raw in MANIFEST.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        expected, relative = line.split("  ", 1)
        path = ROOT / relative
        if not path.is_file():
            errors.append(f"MISSING  {relative}")
            continue
        actual = digest(path)
        checked += 1
        if actual != expected:
            errors.append(f"CHANGED  {relative}\n  expected {expected}\n  actual   {actual}")
        else:
            print(f"OK       {relative}")

    if errors:
        print("\nFROZEN VERIFICATION FAILED", file=sys.stderr)
        for error in errors:
            print(error, file=sys.stderr)
        return 1
    print(f"\nFROZEN VERIFICATION PASSED: {checked} files")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
