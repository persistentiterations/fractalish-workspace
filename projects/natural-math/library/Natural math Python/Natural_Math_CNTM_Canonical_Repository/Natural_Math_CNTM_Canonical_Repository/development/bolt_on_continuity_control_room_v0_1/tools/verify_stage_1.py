#!/usr/bin/env python3
"""Verify Stage 1; require an actual Docker observation in qualification mode."""
from __future__ import annotations
import argparse
import ast
import hashlib
import os
from pathlib import Path
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
REPOSITORY = ROOT.parents[1]
FILES = ("docs/STAGE_1_CONTRACT.md", "src/control_room/__init__.py", "src/control_room/observation.py", "src/control_room/observer.py", "src/control_room/receipt.py", "src/control_room/server.py", "src/control_room/webapp.py", "tests/fixtures/docker_inspect_one.json", "tests/test_stage_1.py", "tests/test_stage_1_docker_integration.py", "tools/verify_stage_1.py", "web/index.html")
DENIED_DOCKER_OPERATIONS = {"start", "stop", "restart", "pause", "unpause", "kill", "rm", "rename", "create", "run", "exec", "cp", "update"}

def fail(message: str) -> None: raise SystemExit(f"CONTROL ROOM v0.1 STAGE 1 VERIFICATION FAILED: {message}")
def inspect_observer_source() -> None:
    path = ROOT / "src/control_room/observer.py"; tree = ast.parse(path.read_text(encoding="utf-8"))
    literals = {node.value for node in ast.walk(tree) if isinstance(node, ast.Constant) and isinstance(node.value, str)}
    present = sorted(DENIED_DOCKER_OPERATIONS & literals)
    if present: fail(f"denied Docker operation literal in adapter: {present}")
    calls = [node for node in ast.walk(tree) if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and node.func.attr == "run"]
    if len(calls) != 1: fail("adapter must contain exactly one subprocess.run call")
def run_tests(pattern: str) -> subprocess.CompletedProcess[str]:
    environment = dict(os.environ); environment["PYTHONPATH"] = str(ROOT / "src")
    return subprocess.run([sys.executable, "-m", "unittest", "discover", "-s", str(ROOT / "tests"), "-p", pattern, "-v"], env=environment, check=False)
def main() -> int:
    parser = argparse.ArgumentParser(); parser.add_argument("--require-docker", action="store_true"); args = parser.parse_args()
    for relative in FILES:
        if not (ROOT / relative).is_file(): fail(f"missing required file: {relative}")
    inspect_observer_source()
    if run_tests("test_stage_1.py").returncode: fail("unit tests failed")
    if args.require_docker:
        if not os.environ.get("CONTROL_ROOM_DOCKER_CONTAINER"): fail("CONTROL_ROOM_DOCKER_CONTAINER is required")
        if not shutil.which("docker"): fail("Docker CLI is required and was not found")
        if run_tests("test_stage_1_docker_integration.py").returncode: fail("live Docker integration failed")
    frozen = subprocess.run([sys.executable, str(REPOSITORY / "tools/verify_frozen.py")], cwd=REPOSITORY, check=False)
    if frozen.returncode: fail("frozen verification failed")
    entries = [f"{relative}:{hashlib.sha256((ROOT / relative).read_bytes()).hexdigest()}" for relative in FILES]
    print(f"Stage 1 files: {len(entries)}"); print(f"Stage 1 manifest SHA-256: {hashlib.sha256(chr(10).join(entries).encode()).hexdigest()}")
    print("Live Docker integration: PASSED" if args.require_docker else "Live Docker integration: NOT RUN (qualification incomplete)")
    print("CONTROL ROOM v0.1 STAGE 1 VERIFICATION PASSED" if args.require_docker else "CONTROL ROOM v0.1 STAGE 1 UNIT VERIFICATION PASSED")
    return 0
if __name__ == "__main__": raise SystemExit(main())
