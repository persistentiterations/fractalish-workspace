"""Deterministic Stage 8 verifier."""

from __future__ import annotations

import ast
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
sys.path.insert(0, str(SRC))

from bolt_on.recovery_stage8 import RequestEvidence, SubjectEvidence, classify_recovery

AUTHORITY_FILES = (
    "docs/STAGE_8_CONTRACT.md",
    "docs/STAGE_8_GATES.md",
    "src/bolt_on/recovery_stage8.py",
    "tests/test_stage_8.py",
    "tools/verify_stage_8.py",
)
FORBIDDEN_IMPORTS = {"docker", "subprocess", "socket", "os", "pathlib", "threading", "multiprocessing"}
CID = "a" * 64
REQ = "req-" + "b" * 64
DIGEST = "sha256:" + "c" * 64


def fail(message: str) -> None:
    raise SystemExit(f"STAGE 8 VERIFICATION FAILED: {message}")


def verify_files() -> None:
    missing = [relative for relative in AUTHORITY_FILES if not (ROOT / relative).is_file()]
    if missing:
        fail(f"missing files: {missing}")


def verify_source_boundary() -> None:
    path = ROOT / "src/bolt_on/recovery_stage8.py"
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
    current = [SubjectEvidence(CID, "demo", "running")]
    report = classify_recovery(CID, "demo", current, "STORE_HEALTHY")
    expected = {
        "disposition": "RESUME_OBSERVATION_ONLY",
        "gateway_enabled": False,
        "native_execution_authorized": False,
        "observation_only": True,
        "reason_code": "RECOVERY_SAFE",
        "schema_version": 1,
        "store_classification": "STORE_HEALTHY",
        "subject_classification": "SUBJECT_MATCHED",
        "terminal_request_suppressed": False,
    }
    if report.body() != expected:
        fail("safe recovery vector mismatch")
    if report.canonical_json() != json.dumps(expected, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False):
        fail("canonical recovery serialization mismatch")

    terminal = classify_recovery(
        CID,
        "demo",
        current,
        "STORE_HEALTHY",
        [RequestEvidence(REQ, DIGEST, "DOCKER_ACCEPTED")],
    )
    if terminal.disposition != "SUPPRESS_DUPLICATE" or not terminal.terminal_request_suppressed:
        fail("terminal duplicate vector mismatch")


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
    print(f"STAGE 8 MANIFEST SHA256 {manifest_digest()}")
    print("BOLT-ON CONTINUITY V0.3 STAGE 8 VERIFICATION PASSED")


if __name__ == "__main__":
    run()
