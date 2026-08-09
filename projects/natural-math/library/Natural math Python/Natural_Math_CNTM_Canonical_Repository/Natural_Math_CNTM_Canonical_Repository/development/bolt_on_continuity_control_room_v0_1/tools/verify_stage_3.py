#!/usr/bin/env python3
"""Fail-closed qualification for the bounded Stage 3 transition."""
from __future__ import annotations
import argparse, ast, hashlib, os
from pathlib import Path
import shutil, subprocess, sys

ROOT=Path(__file__).resolve().parents[1]
REPOSITORY=ROOT.parents[1]
FILES=("docs/STAGE_3_CONTRACT.md","src/control_room/transition.py","src/control_room/webapp.py","src/control_room/server.py","src/control_room/__init__.py","tests/test_stage_3.py","tests/test_stage_3_docker_integration.py","tools/verify_stage_3.py")
DENIED={"start","stop","restart","pause","unpause","kill","rm","rename","create","run","exec","cp","update"}
def fail(message:str)->None: raise SystemExit(f"CONTROL ROOM v0.1 STAGE 3 VERIFICATION FAILED: {message}")
def verify_authority()->None:
    for path in (ROOT/"src/control_room/observer.py",ROOT/"src/control_room/transition.py",ROOT/"tests/test_stage_3.py",ROOT/"tests/test_stage_3_docker_integration.py"):
        tree=ast.parse(path.read_text(encoding="utf-8")); literals={n.value for n in ast.walk(tree) if isinstance(n,ast.Constant) and isinstance(n.value,str)}
        if denied:=sorted(DENIED & literals): fail(f"prohibited Docker operation literal in {path.name}: {denied}")
    tree=ast.parse((ROOT/"src/control_room/observer.py").read_text(encoding="utf-8")); calls=[n for n in ast.walk(tree) if isinstance(n,ast.Call) and isinstance(n.func,ast.Attribute) and n.func.attr=="run"]
    if len(calls)!=1: fail("Docker authority must remain one read-only subprocess.run call")
def tests(pattern:str)->int:
    env=dict(os.environ); env["PYTHONPATH"]=str(ROOT/"src")
    return subprocess.run([sys.executable,"-m","unittest","discover","-s",str(ROOT/"tests"),"-p",pattern,"-v"],env=env,check=False).returncode
def main()->int:
    parser=argparse.ArgumentParser(); parser.add_argument("--require-docker",action="store_true"); args=parser.parse_args()
    for item in FILES:
        if not (ROOT/item).is_file(): fail(f"missing required file: {item}")
    verify_authority()
    if tests("test_stage_3.py"): fail("Stage 3 fixture tests failed")
    if args.require_docker:
        if not os.environ.get("CONTROL_ROOM_DOCKER_CONTAINER") or not os.environ.get("CONTROL_ROOM_STAGE3_EVIDENCE"): fail("Docker subject and operator-confirmed Stage 3 evidence are required")
        if not shutil.which("docker"): fail("Docker CLI is required")
        if tests("test_stage_3_docker_integration.py"): fail("live Stage 3 qualification failed")
    if subprocess.run([sys.executable,str(REPOSITORY/"tools/verify_frozen.py")],cwd=REPOSITORY,check=False).returncode: fail("frozen verification failed")
    entries=[f"{item}:{hashlib.sha256((ROOT/item).read_bytes()).hexdigest()}" for item in FILES]
    print(f"Stage 3 manifest SHA-256: {hashlib.sha256(chr(10).join(entries).encode()).hexdigest()}")
    print("CONTROL ROOM v0.1 STAGE 3 VERIFICATION PASSED" if args.require_docker else "CONTROL ROOM v0.1 STAGE 3 UNIT VERIFICATION PASSED")
    return 0
if __name__=="__main__": raise SystemExit(main())
