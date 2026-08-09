#!/usr/bin/env python3
"""Qualify the Stage 2 definition without executing or implementing Stage 2."""
from __future__ import annotations
import hashlib
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
REPOSITORY = ROOT.parents[1]
EXPECTED_BRANCH = "agent/bolt-on-continuity-control-room-v0.1"
STAGE_1_COMMIT = "51dffe72c43a2c5f98c20cc9d9ea4ae1b336f225"
FILES = ("docs/STAGE_2_SCOPE.md", "tests/test_stage_2_scope.py", "tools/verify_stage_2_scope.py")
PROHIBITED_STAGE_2_PRODUCT_FILES = (
    "src/control_room/retention.py",
    "src/control_room/comparison.py",
    "src/control_room/stage_2.py",
    "tests/test_stage_2.py",
    "tests/test_stage_2_docker_integration.py",
    "tools/verify_stage_2.py",
)

def fail(message: str) -> None:
    raise SystemExit(f"CONTROL ROOM v0.1 STAGE 2 SCOPE VERIFICATION FAILED: {message}")

def git(*arguments: str, check: bool = True) -> subprocess.CompletedProcess[str]:
    return subprocess.run(["git", "-c", f"safe.directory={REPOSITORY.as_posix()}", "-C", str(REPOSITORY), *arguments], check=check, capture_output=True, text=True)

def main() -> int:
    for relative in FILES:
        if not (ROOT / relative).is_file(): fail(f"missing scope file: {relative}")
    branch = git("branch", "--show-current").stdout.strip()
    if branch != EXPECTED_BRANCH: fail(f"unexpected branch: {branch!r}")
    if git("merge-base", "--is-ancestor", STAGE_1_COMMIT, "HEAD", check=False).returncode:
        fail("current head does not descend from the qualified Stage 1 commit")
    prohibited = [relative for relative in PROHIBITED_STAGE_2_PRODUCT_FILES if (ROOT / relative).exists()]
    if prohibited: fail(f"Stage 2 product code exists before scope qualification: {prohibited}")
    tests = subprocess.run([sys.executable, "-m", "unittest", "discover", "-s", str(ROOT / "tests"), "-p", "test_stage_2_scope.py", "-v"], check=False)
    if tests.returncode: fail("scope tests failed")
    frozen = subprocess.run([sys.executable, str(REPOSITORY / "tools" / "verify_frozen.py")], cwd=REPOSITORY, check=False)
    if frozen.returncode: fail("frozen verification failed")
    entries = [f"{relative}:{hashlib.sha256((ROOT / relative).read_bytes()).hexdigest()}" for relative in FILES]
    digest = hashlib.sha256("\n".join(entries).encode("utf-8")).hexdigest()
    print(f"Branch: {branch}")
    print(f"Qualified Stage 1 ancestor: {STAGE_1_COMMIT}")
    print(f"Stage 2 scope files: {len(FILES)}")
    print(f"Stage 2 scope manifest SHA-256: {digest}")
    print("CONTROL ROOM v0.1 STAGE 2 SCOPE VERIFICATION PASSED")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
