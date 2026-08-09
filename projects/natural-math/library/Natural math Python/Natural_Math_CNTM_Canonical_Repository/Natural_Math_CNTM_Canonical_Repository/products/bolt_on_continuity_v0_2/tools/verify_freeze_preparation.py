from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
QUALIFIED_REVIEW_HEAD = "3574021a3b6735696c759579651abbb2ed9f2b2c"
DESTINATION = ROOT / "frozen" / "bolt_on_continuity" / "v0.2"
ALLOWED_POST_REVIEW_PREFIXES = (
    "products/bolt_on_continuity_v0_2/release_freeze/",
    "products/bolt_on_continuity_v0_2/tools/build_frozen_v0_2.py",
    "products/bolt_on_continuity_v0_2/tools/verify_freeze_preparation.py",
    "tools/verify_bolt_on_continuity_v0_2.py",
    "tools/verify_all_frozen.py",
)


def git(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", *args],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )


def main() -> int:
    failures: list[str] = []

    if DESTINATION.exists():
        failures.append(f"frozen destination already exists: {DESTINATION}")

    status = git("status", "--porcelain")
    if status.returncode != 0:
        failures.append("unable to read Git status")
    elif status.stdout.strip():
        failures.append("working tree must be clean before freeze creation")

    ancestor = git("merge-base", "--is-ancestor", QUALIFIED_REVIEW_HEAD, "HEAD")
    if ancestor.returncode != 0:
        failures.append("qualified release-review head is not an ancestor of HEAD")

    changed = git("diff", "--name-only", f"{QUALIFIED_REVIEW_HEAD}..HEAD")
    if changed.returncode != 0:
        failures.append("unable to inspect post-review changes")
    else:
        for raw in changed.stdout.splitlines():
            path = raw.strip().replace("\\", "/")
            if path and not any(path == prefix or path.startswith(prefix) for prefix in ALLOWED_POST_REVIEW_PREFIXES):
                failures.append(f"unapproved post-review change: {path}")

    required = (
        ROOT / "products" / "bolt_on_continuity_v0_2" / "release_freeze" / "README_FREEZE.md",
        ROOT / "products" / "bolt_on_continuity_v0_2" / "tools" / "build_frozen_v0_2.py",
        ROOT / "tools" / "verify_bolt_on_continuity_v0_2.py",
    )
    for path in required:
        if not path.is_file():
            failures.append(f"missing freeze file: {path.relative_to(ROOT)}")

    if failures:
        print("BOLT-ON CONTINUITY V0.2 FREEZE PREPARATION: FAIL")
        for failure in failures:
            print(f"- {failure}")
        return 1

    print("BOLT-ON CONTINUITY V0.2 FREEZE PREPARATION: PASS")
    print(f"Qualified review head: {QUALIFIED_REVIEW_HEAD}")
    print(f"Proposed destination: {DESTINATION.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
