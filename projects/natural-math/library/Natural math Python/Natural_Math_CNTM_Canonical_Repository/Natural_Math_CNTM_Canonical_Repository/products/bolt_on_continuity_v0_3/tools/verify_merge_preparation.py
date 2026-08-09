"""Verify deterministic merge preparation without granting merge authority."""

from __future__ import annotations

import ast
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
sys.path.insert(0, str(SRC))

from bolt_on.merge_preparation import (
    AHEAD_BY,
    BEHIND_BY,
    FROZEN_BRANCH_HEAD,
    FROZEN_MANIFEST,
    RC2_REVIEW_SHA256,
    TARGET_BRANCH,
    TARGET_HEAD,
    MergePreparationEvidence,
    prepare_merge,
)
from bolt_on.receipts import canonical_json_bytes

AUTHORITY_FILES = (
    "docs/MERGE_PREPARATION_CONTRACT.md",
    "src/bolt_on/merge_preparation.py",
    "tests/test_merge_preparation.py",
    "tools/verify_merge_preparation.py",
)
FORBIDDEN_IMPORTS = {"docker", "subprocess", "socket", "shutil"}


def fail(message: str) -> None:
    raise SystemExit(f"MERGE PREPARATION VERIFICATION FAILED: {message}")


def verify_files() -> None:
    missing = [relative for relative in AUTHORITY_FILES if not (ROOT / relative).is_file()]
    if missing:
        fail(f"missing files: {missing}")


def verify_source_boundary() -> None:
    path = ROOT / "src/bolt_on/merge_preparation.py"
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
    if TARGET_BRANCH != "main":
        fail("target branch mismatch")
    if TARGET_HEAD != "0558d3e671d854549003b729eb3879059e8658cc":
        fail("target head mismatch")
    if FROZEN_BRANCH_HEAD != "75e9cd4d7b16558702b393cf2336cffe45a18474":
        fail("candidate head mismatch")
    if (AHEAD_BY, BEHIND_BY) != (77, 0):
        fail("fast-forward relationship mismatch")
    if FROZEN_MANIFEST != "3ce662d9be77735a9de53086160a3b2589f1b0feabcebba1551b080702f821bb":
        fail("frozen manifest mismatch")
    if RC2_REVIEW_SHA256 != "5e1709214599c0bf075e04557952ee5b563461749df71a41d6fe7bbcc4e1adeb":
        fail("RC2 review mismatch")


def verify_record() -> str:
    evidence = MergePreparationEvidence(90, True, True, True, True)
    first = prepare_merge(evidence).canonical_bytes()
    second = prepare_merge(evidence).canonical_bytes()
    if first != second:
        fail("record is not deterministic")
    body = json.loads(first)
    if body.get("status") != "READY_FOR_MERGE_DECISION":
        fail("status mismatch")
    if set(body.get("authority", {}).values()) != {False}:
        fail("authority expanded")
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
    print(f"MERGE PREPARATION RECORD SHA256 {record_digest}")
    print(f"MERGE PREPARATION MANIFEST SHA256 {manifest_digest()}")
    print("MERGE STATUS READY_FOR_MERGE_DECISION")
    print("BOLT-ON CONTINUITY V0.3 MERGE PREPARATION VERIFICATION PASSED")


if __name__ == "__main__":
    run()
