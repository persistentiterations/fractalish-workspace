"""Deterministic Stage 5 verifier."""

from __future__ import annotations

import ast
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
sys.path.insert(0, str(SRC))

from bolt_on.configuration_stage4 import build_configuration
from bolt_on.discovery import EnrollmentRecord
from bolt_on.lifecycle_stage5 import COMMANDS, SAFETY, STATES, execute
from bolt_on.receipts import canonical_json_bytes

AUTHORITY_FILES = (
    "docs/STAGE_5_CONTRACT.md",
    "docs/STAGE_5_GATES.md",
    "src/bolt_on/lifecycle_stage5.py",
    "src/bolt_on/cli/main.py",
    "tests/test_stage_5.py",
    "tools/verify_stage_5.py",
)
FORBIDDEN_IMPORTS = {"docker", "subprocess", "socket", "threading", "multiprocessing"}
CID = "a" * 64


def fail(message: str) -> None:
    raise SystemExit(f"STAGE 5 VERIFICATION FAILED: {message}")


def verify_files() -> None:
    missing = [relative for relative in AUTHORITY_FILES if not (ROOT / relative).is_file()]
    if missing:
        fail(f"missing files: {missing}")


def verify_source_boundary() -> None:
    path = ROOT / "src/bolt_on/lifecycle_stage5.py"
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            names = {alias.name.split(".")[0] for alias in node.names}
        elif isinstance(node, ast.ImportFrom) and node.module:
            names = {node.module.split(".")[0]}
        else:
            continue
        forbidden = names & FORBIDDEN_IMPORTS
        if forbidden:
            fail(f"forbidden import {sorted(forbidden)}")
    if COMMANDS != {"config-check", "status", "start", "stop"}:
        fail("command contract mismatch")
    if STATES != {"NOT_STARTED", "OBSERVATION_PLAN_READY", "STOP_PLAN_READY"}:
        fail("lifecycle state contract mismatch")
    if SAFETY != {
        "autonomous_actions": False,
        "gateway_enabled": False,
        "native_execution_authorized": False,
        "observation_only": True,
    }:
        fail("safety contract mismatch")


def configuration_bytes() -> bytes:
    base = {
        "container_id": CID,
        "contract": "bolt-on-continuity-v0.3-stage-3",
        "display_name": "demo",
        "gateway_enabled": False,
        "image": "example:1",
        "observation_only": True,
        "observed_state": "running",
        "schema_version": 1,
    }
    digest = hashlib.sha256(canonical_json_bytes(base)).hexdigest()
    return build_configuration(EnrollmentRecord(CID, "demo", "example:1", "running", digest)).canonical_bytes()


def verify_vectors() -> None:
    payload = configuration_bytes()
    expected = {
        "config-check": ("NOT_STARTED", "CONFIGURATION_VALID"),
        "status": ("NOT_STARTED", "RUNTIME_NOT_STARTED"),
        "start": ("OBSERVATION_PLAN_READY", "OBSERVATION_PLAN_CREATED"),
        "stop": ("STOP_PLAN_READY", "STOP_PLAN_CREATED"),
    }
    for command, vector in expected.items():
        result = execute(command, payload)
        if result.body["accepted"] is not True:
            fail(f"{command} unexpectedly rejected")
        if (result.body["lifecycle_state"], result.body["reason_code"]) != vector:
            fail(f"{command} vector mismatch")
        if json.loads(result.canonical_json()) != result.body:
            fail(f"{command} canonical serialization mismatch")
    if execute("start", b"{}").body["reason_code"] != "CONFIGURATION_INVALID":
        fail("invalid configuration did not fail closed")
    stop_plan = execute("stop", payload).body["plan"]
    if stop_plan["container_mutated"] is not False or stop_plan["execution_performed"] is not False:
        fail("stop plan implies execution")


def manifest_digest() -> str:
    entries = []
    for relative in AUTHORITY_FILES:
        data = (ROOT / relative).read_bytes()
        entries.append({"path": relative, "bytes": len(data), "sha256": hashlib.sha256(data).hexdigest()})
    payload = json.dumps(entries, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def run() -> None:
    verify_files()
    verify_source_boundary()
    verify_vectors()
    print(f"STAGE 5 MANIFEST SHA256 {manifest_digest()}")
    print("BOLT-ON CONTINUITY V0.3 STAGE 5 VERIFICATION PASSED")


if __name__ == "__main__":
    run()
