"""Deterministic Stage 6 verifier."""

from __future__ import annotations

import ast
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
sys.path.insert(0, str(SRC))

from bolt_on.incident_stage6 import explain_incident, export_incident, replay_incident, validate_incident
from bolt_on.receipts import canonical_json_bytes

AUTHORITY_FILES = (
    "docs/STAGE_6_CONTRACT.md",
    "docs/STAGE_6_GATES.md",
    "src/bolt_on/incident_stage6.py",
    "tests/test_stage_6.py",
    "tools/verify_stage_6.py",
)
FORBIDDEN_IMPORTS = {"docker", "subprocess", "socket", "os", "threading", "multiprocessing"}
CID = "a" * 64


def fail(message: str) -> None:
    raise SystemExit(f"STAGE 6 VERIFICATION FAILED: {message}")


def verify_files() -> None:
    missing = [relative for relative in AUTHORITY_FILES if not (ROOT / relative).is_file()]
    if missing:
        fail(f"missing files: {missing}")


def verify_source_boundary() -> None:
    path = ROOT / "src/bolt_on/incident_stage6.py"
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


def make_receipt(sequence: int, event_type: str, payload: dict, previous: str) -> dict:
    base = {"event_type": event_type, "payload": payload, "previous_digest": previous, "sequence": sequence}
    return dict(base, receipt_digest=hashlib.sha256(canonical_json_bytes(base)).hexdigest())


def incident() -> dict:
    first = make_receipt(0, "OBSERVED", {"state": "running"}, "0" * 64)
    second = make_receipt(1, "DECIDED", {"decision": "HOLD"}, first["receipt_digest"])
    return {
        "incident_id": "inc-" + "c" * 64,
        "container_id": CID,
        "configuration_digest": "sha256:" + "b" * 64,
        "opened_sequence": 0,
        "updated_sequence": 1,
        "decision": "HOLD",
        "reason_code": "BOUNDARY_REACHED",
        "action_status": "PROJECTED",
        "receipts": [first, second],
    }


def verify_vectors() -> None:
    value = incident()
    validated = validate_incident(value)
    replay = replay_incident(validated)
    if replay.body() != {
        "action_status": "PROJECTED",
        "chain_valid": True,
        "decision": "HOLD",
        "receipt_count": 2,
        "terminal_receipt_digest": value["receipts"][-1]["receipt_digest"],
    }:
        fail("replay vector mismatch")
    explanation = explain_incident(validated)
    if explanation["action"] != {"native_execution_evidenced": False, "status": "PROJECTED"}:
        fail("execution evidence boundary mismatch")
    package = export_incident(validated)
    parsed = json.loads(package)
    base = dict(parsed)
    digest = base.pop("package_digest")
    if digest != hashlib.sha256(canonical_json_bytes(base)).hexdigest():
        fail("package digest mismatch")
    if not package.endswith(b"\n") or package.endswith(b"\n\n"):
        fail("package newline mismatch")


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
    print(f"STAGE 6 MANIFEST SHA256 {manifest_digest()}")
    print("BOLT-ON CONTINUITY V0.3 STAGE 6 VERIFICATION PASSED")


if __name__ == "__main__":
    run()
