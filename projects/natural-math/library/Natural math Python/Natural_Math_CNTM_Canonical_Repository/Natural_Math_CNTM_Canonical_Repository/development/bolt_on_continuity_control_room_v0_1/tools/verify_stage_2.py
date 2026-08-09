#!/usr/bin/env python3
"""Qualify the bounded Stage 2 continuity slice."""
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
FILES = ("src/control_room/__init__.py", "src/control_room/retention.py", "src/control_room/comparison.py", "src/control_room/webapp.py", "src/control_room/server.py", "web/index.html", "tests/test_stage_2.py", "tests/test_stage_2_docker_integration.py", "tools/verify_stage_2.py")
DENIED_DOCKER_OPERATIONS = {"start", "stop", "restart", "pause", "unpause", "kill", "rm", "rename", "create", "run", "exec", "cp", "update"}

def fail(message: str) -> None:
    raise SystemExit(f"CONTROL ROOM v0.1 STAGE 2 VERIFICATION FAILED: {message}")

def inspect_docker_authority() -> None:
    tree = ast.parse((ROOT / "src/control_room/observer.py").read_text(encoding="utf-8"))
    literals = {node.value for node in ast.walk(tree) if isinstance(node, ast.Constant) and isinstance(node.value, str)}
    if denied := sorted(DENIED_DOCKER_OPERATIONS & literals): fail(f"denied Docker operation literal: {denied}")
    calls = [node for node in ast.walk(tree) if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and node.func.attr == "run"]
    if len(calls) != 1: fail("Docker authority must remain one subprocess.run call")

def run_tests(pattern: str) -> int:
    environment = dict(os.environ); environment["PYTHONPATH"] = str(ROOT / "src")
    return subprocess.run([sys.executable, "-m", "unittest", "discover", "-s", str(ROOT / "tests"), "-p", pattern, "-v"], env=environment, check=False).returncode

def main() -> int:
    parser = argparse.ArgumentParser(); parser.add_argument("--require-docker", action="store_true"); args = parser.parse_args()
    for relative in FILES:
        if not (ROOT / relative).is_file(): fail(f"missing required file: {relative}")
    inspect_docker_authority()
    if run_tests("test_stage_2.py"): fail("Stage 2 unit tests failed")
    if args.require_docker:
        if not os.environ.get("CONTROL_ROOM_DOCKER_CONTAINER"): fail("CONTROL_ROOM_DOCKER_CONTAINER is required")
        if not shutil.which("docker"): fail("Docker CLI is required and was not found")
        if run_tests("test_stage_2_docker_integration.py"): fail("live Stage 2 Docker qualification failed")
    frozen = subprocess.run([sys.executable, str(REPOSITORY / "tools/verify_frozen.py")], cwd=REPOSITORY, check=False)
    if frozen.returncode: fail("frozen verification failed")
    entries = [f"{relative}:{hashlib.sha256((ROOT / relative).read_bytes()).hexdigest()}" for relative in FILES]
    print(f"Stage 2 files: {len(entries)}")
    print(f"Stage 2 manifest SHA-256: {hashlib.sha256(chr(10).join(entries).encode()).hexdigest()}")
    print("Live Docker qualification: PASSED" if args.require_docker else "Live Docker qualification: NOT RUN")
    print("CONTROL ROOM v0.1 STAGE 2 VERIFICATION PASSED" if args.require_docker else "CONTROL ROOM v0.1 STAGE 2 UNIT VERIFICATION PASSED")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
