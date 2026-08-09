"""Verify deterministic RC1 preparation without granting release authority."""

from __future__ import annotations

import ast
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
sys.path.insert(0, str(SRC))

from bolt_on.rc1_preparation import (
    QUALIFIED_SOURCE_COMMIT,
    RCPreparationEvidence,
    STAGE_MANIFESTS,
    prepare_rc1,
)
from bolt_on.receipts import canonical_json_bytes

AUTHORITY_FILES = (
    "docs/RC1_PREPARATION_CONTRACT.md",
    "src/bolt_on/rc1_preparation.py",
    "tests/test_rc1_preparation.py",
    "tools/verify_rc1_preparation.py",
)
FORBIDDEN_IMPORTS = {"docker", "subprocess", "socket", "os", "shutil"}
EXPECTED_SOURCE = "6ef5595f4d0d86074fbb53e4a37a9c04d4a62f78"


def fail(message: str) -> None:
    raise SystemExit(f"RC1 PREPARATION VERIFICATION FAILED: {message}")


def verify_files() -> None:
    missing = [relative for relative in AUTHORITY_FILES if not (ROOT / relative).is_file()]
    if missing:
        fail(f"missing files: {missing}")


def verify_source_boundary() -> None:
    path = ROOT / "src/bolt_on/rc1_preparation.py"
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
    if QUALIFIED_SOURCE_COMMIT != EXPECTED_SOURCE:
        fail("qualified source mismatch")
    if set(STAGE_MANIFESTS) != {f"stage_{index}" for index in range(11)}:
        fail("stage manifest set mismatch")


def verify_record() -> str:
    evidence = RCPreparationEvidence(66, True, True, True)
    first = prepare_rc1(evidence).canonical_bytes()
    second = prepare_rc1(evidence).canonical_bytes()
    if first != second:
        fail("record is not deterministic")
    if not first.endswith(b"\n") or first.endswith(b"\n\n"):
        fail("canonical newline mismatch")
    body = json.loads(first)
    if body.get("status") != "READY_FOR_RC_REVIEW":
        fail("readiness status mismatch")
    if set(body.get("authority", {}).values()) != {False}:
        fail("release authority expanded")
    digest = body.pop("record_digest", None)
    expected = hashlib.sha256(canonical_json_bytes(body)).hexdigest()
    if digest != expected:
        fail("record digest mismatch")
    return digest


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
    record_digest = verify_record()
    print(f"RC1 RECORD SHA256 {record_digest}")
    print(f"RC1 PREPARATION MANIFEST SHA256 {manifest_digest()}")
    print("BOLT-ON CONTINUITY V0.3 RC1 PREPARATION VERIFICATION PASSED")


if __name__ == "__main__":
    run()
