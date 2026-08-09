#!/usr/bin/env python3
"""Run all frozen-release verification tools."""

from __future__ import annotations

from pathlib import Path
import subprocess
import sys


def run(path: Path) -> int:
    completed = subprocess.run([sys.executable, str(path)], check=False)
    return completed.returncode


def main() -> int:
    tools = Path(__file__).resolve().parent
    checks = (
        tools / "verify_frozen.py",
        tools / "verify_bolt_on_v0_1.py",
    )

    for check in checks:
        if not check.is_file():
            print(f"MISSING VERIFIER: {check}")
            return 1
        if run(check) != 0:
            return 1

    print()
    print("ALL FROZEN RELEASE VERIFICATIONS PASSED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
