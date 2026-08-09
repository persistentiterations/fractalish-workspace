"""Deterministic Stage 7 verifier."""

from __future__ import annotations

import ast
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
sys.path.insert(0, str(SRC))

from bolt_on.approval_stage7 import GatewayState, create_request, decide, transition_gateway
from bolt_on.receipts import canonical_json_bytes

AUTHORITY_FILES = (
    "docs/STAGE_7_CONTRACT.md",
    "docs/STAGE_7_GATES.md",
    "src/bolt_on/approval_stage7.py",
    "tests/test_stage_7.py",
    "tools/verify_stage_7.py",
)
FORBIDDEN_IMPORTS = {"docker", "subprocess", "socket", "os", "threading", "pathlib"}
CID = "a" * 64
RID = "req-" + "b" * 64
DIGEST = "sha256:" + "c" * 64


def fail(message: str) -> None:
    raise SystemExit(f"STAGE 7 VERIFICATION FAILED: {message}")


def verify_files() -> None:
    missing = [relative for relative in AUTHORITY_FILES if not (ROOT / relative).is_file()]
    if missing:
        fail(f"missing files: {missing}")


def verify_source_boundary() -> None:
    path = ROOT / "src/bolt_on/approval_stage7.py"
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


def verify_vectors() -> None:
    request = create_request(RID, CID, "HOLD", DIGEST, DIGEST, 10, 20)
    expected_request = {
        "action": "HOLD",
        "configuration_digest": DIGEST,
        "container_id": CID,
        "expiry_sequence": 20,
        "incident_digest": DIGEST,
        "issued_sequence": 10,
        "request_id": RID,
        "schema_version": 1,
    }
    expected_request_digest = "sha256:" + hashlib.sha256(canonical_json_bytes(expected_request)).hexdigest()
    if request.request_digest != expected_request_digest:
        fail("request digest mismatch")

    gateway = transition_gateway(GatewayState(), "ENABLED", 11)
    decision = decide(request, gateway, "APPROVE", "OPERATOR_CONFIRMED", 12)
    expected_decision = {
        "decision": "APPROVE",
        "decision_sequence": 12,
        "reason_code": "OPERATOR_CONFIRMED",
        "request_digest": expected_request_digest,
        "request_id": RID,
        "schema_version": 1,
    }
    expected_decision_digest = "sha256:" + hashlib.sha256(canonical_json_bytes(expected_decision)).hexdigest()
    if decision.decision_digest != expected_decision_digest:
        fail("decision digest mismatch")
    if decision.body()["native_execution_authorized"] is not False:
        fail("native execution boundary mismatch")


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
    print(f"STAGE 7 MANIFEST SHA256 {manifest_digest()}")
    print("BOLT-ON CONTINUITY V0.3 STAGE 7 VERIFICATION PASSED")


if __name__ == "__main__":
    run()
