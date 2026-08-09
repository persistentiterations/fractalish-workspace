#!/usr/bin/env python3
"""Qualify the Control Room v0.1 Stage 0 boundary without product execution."""
from __future__ import annotations
import hashlib
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
REPOSITORY = ROOT.parents[1]
EXPECTED_BRANCH = "agent/bolt-on-continuity-control-room-v0.1"
FOUNDATION_TAG = "bolt-on-continuity-v0.4"
FOUNDATION_COMMIT = "4cc817441d3447e54303550090eaf8b95c451a83"
REQUIRED_FILES = ("README.md", "docs/STAGE_0_SCOPE.md", "tests/test_stage_0.py", "tools/verify_stage_0.py")
FORBIDDEN_SUFFIXES = (".html", ".css", ".js", ".ts", ".tsx")
FORBIDDEN_NAMES = ("Dockerfile", "compose.yaml", "docker-compose.yaml")

def fail(message: str) -> None:
    raise SystemExit(f"CONTROL ROOM v0.1 STAGE 0 VERIFICATION FAILED: {message}")

def git(*arguments: str, check: bool = True) -> subprocess.CompletedProcess[str]:
    return subprocess.run(["git", "-c", f"safe.directory={REPOSITORY.as_posix()}", "-C", str(REPOSITORY), *arguments], check=check, capture_output=True, text=True)

def main() -> int:
    for relative in REQUIRED_FILES:
        if not (ROOT / relative).is_file():
            fail(f"missing required file: {relative}")
    branch = git("branch", "--show-current").stdout.strip()
    if branch != EXPECTED_BRANCH:
        fail(f"branch is {branch!r}, expected {EXPECTED_BRANCH!r}")
    target = git("rev-parse", f"{FOUNDATION_TAG}^{{commit}}").stdout.strip()
    if target != FOUNDATION_COMMIT:
        fail(f"foundation tag resolves to {target}")
    if git("merge-base", "--is-ancestor", FOUNDATION_COMMIT, "HEAD", check=False).returncode != 0:
        fail("current HEAD does not descend from the foundation commit")
    forbidden = [path.relative_to(ROOT).as_posix() for path in ROOT.rglob("*") if path.is_file() and (path.suffix.lower() in FORBIDDEN_SUFFIXES or path.name in FORBIDDEN_NAMES)]
    if forbidden:
        fail(f"product implementation exists in Stage 0 tree: {forbidden}")
    tests = subprocess.run([sys.executable, "-m", "unittest", "discover", "-s", str(ROOT / "tests"), "-p", "test_*.py", "-v"], check=False)
    if tests.returncode != 0:
        fail("Stage 0 tests failed")
    frozen = subprocess.run([sys.executable, str(REPOSITORY / "tools" / "verify_frozen.py")], cwd=REPOSITORY, check=False)
    if frozen.returncode != 0:
        fail("frozen verification failed")
    entries = []
    for relative in REQUIRED_FILES:
        data = (ROOT / relative).read_bytes()
        entries.append(f"{relative}:{len(data)}:{hashlib.sha256(data).hexdigest()}")
    manifest = hashlib.sha256("\n".join(entries).encode("utf-8")).hexdigest()
    print(f"Branch: {branch}")
    print(f"Foundation: {FOUNDATION_TAG} -> {target}")
    print(f"Stage 0 files: {len(entries)}")
    print(f"Stage 0 manifest SHA-256: {manifest}")
    print("CONTROL ROOM v0.1 STAGE 0 VERIFICATION PASSED")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
