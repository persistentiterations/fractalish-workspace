"""Verify deterministic RC2 preparation without granting release authority."""

from __future__ import annotations

import ast
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
sys.path.insert(0, str(SRC))

from bolt_on.rc2_preparation import (
    CORRECTED_SOURCE_COMMIT,
    CORRECTED_TREE_FILES,
    CORRECTED_TREE_SHA256,
    RC2PreparationEvidence,
    prepare_rc2,
)
from bolt_on.receipts import canonical_json_bytes

AUTHORITY_FILES = (
    "docs/RC2_PREPARATION_CONTRACT.md",
    "src/bolt_on/rc2_preparation.py",
    "tests/test_rc2_preparation.py",
    "tools/verify_rc2_preparation.py",
)
FORBIDDEN_IMPORTS = {"docker", "subprocess", "socket", "os", "shutil"}
EXPECTED_SOURCE = "67e0da7e41e96870d8dbeafa8031e4de694bb03f"
EXPECTED_TREE_FILES = 76
EXPECTED_TREE_SHA256 = "203d43b5e3f7330c47f7cc72916540b887dccb67d039e1348989a6a8a2ea2376"


def fail(message: str) -> None:
    raise SystemExit(f"RC2 PREPARATION VERIFICATION FAILED: {message}")


def verify_files() -> None:
    missing = [relative for relative in AUTHORITY_FILES if not (ROOT / relative).is_file()]
    if missing:
        fail(f"missing files: {missing}")


def verify_source_boundary() -> None:
    path = ROOT / "src/bolt_on/rc2_preparation.py"
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
    if CORRECTED_SOURCE_COMMIT != EXPECTED_SOURCE:
        fail("corrected source mismatch")
    if CORRECTED_TREE_FILES != EXPECTED_TREE_FILES:
        fail("corrected tree file count mismatch")
    if CORRECTED_TREE_SHA256 != EXPECTED_TREE_SHA256:
        fail("corrected tree digest mismatch")


def verify_record() -> str:
    evidence = RC2PreparationEvidence(78, True, True, True, True)
    first = prepare_rc2(evidence).canonical_bytes()
    second = prepare_rc2(evidence).canonical_bytes()
    if first != second:
        fail("record is not deterministic")
    body = json.loads(first)
    if body.get("status") != "READY_FOR_RC2_REVIEW":
        fail("readiness status mismatch")
    if set(body.get("authority", {}).values()) != {False}:
        fail("release authority expanded")
    corrected = body.get("corrected_candidate", {})
    if corrected.get("tree_files") != EXPECTED_TREE_FILES or corrected.get("tree_sha256") != EXPECTED_TREE_SHA256:
        fail("corrected tree evidence mismatch")
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
    print(f"RC2 RECORD SHA256 {record_digest}")
    print(f"RC2 PREPARATION MANIFEST SHA256 {manifest_digest()}")
    print("BOLT-ON CONTINUITY V0.3 RC2 PREPARATION VERIFICATION PASSED")


if __name__ == "__main__":
    run()
