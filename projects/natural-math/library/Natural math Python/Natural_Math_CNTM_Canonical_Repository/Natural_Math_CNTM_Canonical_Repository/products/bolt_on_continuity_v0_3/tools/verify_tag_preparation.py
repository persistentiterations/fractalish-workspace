"""Verify deterministic tag preparation without granting tag authority."""

from __future__ import annotations

import ast
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
sys.path.insert(0, str(SRC))

from bolt_on.receipts import canonical_json_bytes
from bolt_on.tag_preparation import (
    FROZEN_MANIFEST,
    FROZEN_SOURCE_COMMIT,
    MERGED_BRANCH,
    MERGED_HEAD,
    PROPOSED_TAG,
    TagPreparationEvidence,
    prepare_tag,
)

AUTHORITY_FILES = (
    "docs/TAG_PREPARATION_CONTRACT.md",
    "src/bolt_on/tag_preparation.py",
    "tests/test_tag_preparation.py",
    "tools/verify_tag_preparation.py",
)
FORBIDDEN_IMPORTS = {"docker", "subprocess", "socket", "shutil"}


def fail(message: str) -> None:
    raise SystemExit(f"TAG PREPARATION VERIFICATION FAILED: {message}")


def verify_files() -> None:
    missing = [relative for relative in AUTHORITY_FILES if not (ROOT / relative).is_file()]
    if missing:
        fail(f"missing files: {missing}")


def verify_source_boundary() -> None:
    path = ROOT / "src/bolt_on/tag_preparation.py"
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
    if MERGED_BRANCH != "main":
        fail("merged branch mismatch")
    if MERGED_HEAD != "1c95a1ff8ead30675d4d26f7d77720097c5b9129":
        fail("merged head mismatch")
    if FROZEN_SOURCE_COMMIT != "67e0da7e41e96870d8dbeafa8031e4de694bb03f":
        fail("frozen source mismatch")
    if FROZEN_MANIFEST != "3ce662d9be77735a9de53086160a3b2589f1b0feabcebba1551b080702f821bb":
        fail("frozen manifest mismatch")
    if PROPOSED_TAG != "bolt-on-continuity-v0.3":
        fail("proposed tag mismatch")


def verify_record() -> str:
    evidence = TagPreparationEvidence(98, True, True, True, True)
    first = prepare_tag(evidence).canonical_bytes()
    second = prepare_tag(evidence).canonical_bytes()
    if first != second:
        fail("record is not deterministic")
    body = json.loads(first)
    if body.get("status") != "READY_FOR_TAG_DECISION":
        fail("status mismatch")
    if set(body.get("authority", {}).values()) != {False}:
        fail("authority expanded")
    proposed = body.get("proposed_tag", {})
    if proposed != {"kind": "annotated", "name": PROPOSED_TAG, "target": MERGED_HEAD}:
        fail("tag specification mismatch")
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
    print(f"TAG PREPARATION RECORD SHA256 {record_digest}")
    print(f"TAG PREPARATION MANIFEST SHA256 {manifest_digest()}")
    print(f"PROPOSED TAG {PROPOSED_TAG}")
    print(f"TAG TARGET {MERGED_HEAD}")
    print("TAG STATUS READY_FOR_TAG_DECISION")
    print("BOLT-ON CONTINUITY V0.3 TAG PREPARATION VERIFICATION PASSED")


if __name__ == "__main__":
    run()
