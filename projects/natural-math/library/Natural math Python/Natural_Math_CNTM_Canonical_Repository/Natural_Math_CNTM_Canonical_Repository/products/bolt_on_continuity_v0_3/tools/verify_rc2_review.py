"""Verify formal RC2 review without granting release authority."""

from __future__ import annotations

import ast
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
sys.path.insert(0, str(SRC))

from bolt_on.rc2_review import (
    CORRECTED_SOURCE_COMMIT,
    CORRECTED_TREE_FILES,
    CORRECTED_TREE_SHA256,
    RC2_PREPARATION_HEAD,
    RC2_PREPARATION_MANIFEST_SHA256,
    RC2_RECORD_SHA256,
    RC2ReviewEvidence,
    review_rc2,
)
from bolt_on.receipts import canonical_json_bytes

AUTHORITY_FILES = (
    "docs/RC2_FORMAL_REVIEW_CONTRACT.md",
    "src/bolt_on/rc2_review.py",
    "tests/test_rc2_review.py",
    "tools/verify_rc2_review.py",
)
FORBIDDEN_IMPORTS = {"docker", "subprocess", "socket", "os", "shutil"}
EXPECTED = {
    "corrected_source": "67e0da7e41e96870d8dbeafa8031e4de694bb03f",
    "corrected_tree_files": 76,
    "corrected_tree_sha256": "203d43b5e3f7330c47f7cc72916540b887dccb67d039e1348989a6a8a2ea2376",
    "rc2_preparation_head": "59bddbbeac43914633782be45d01e90f3d97b7c0",
    "rc2_record_sha256": "3075d810faf9ae1cf0b201e94b81f0287894149479eba341b66a6ac6cfd8a051",
    "rc2_preparation_manifest_sha256": "cf36118ccdeb9642509f96fc986a7c7711976a09a91bdc3f68acb54de3c11f6d",
}


def fail(message: str) -> None:
    raise SystemExit(f"RC2 FORMAL REVIEW VERIFICATION FAILED: {message}")


def verify_files() -> None:
    missing = [relative for relative in AUTHORITY_FILES if not (ROOT / relative).is_file()]
    if missing:
        fail(f"missing files: {missing}")


def verify_source_boundary() -> None:
    path = ROOT / "src/bolt_on/rc2_review.py"
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
    actual = {
        "corrected_source": CORRECTED_SOURCE_COMMIT,
        "corrected_tree_files": CORRECTED_TREE_FILES,
        "corrected_tree_sha256": CORRECTED_TREE_SHA256,
        "rc2_preparation_head": RC2_PREPARATION_HEAD,
        "rc2_record_sha256": RC2_RECORD_SHA256,
        "rc2_preparation_manifest_sha256": RC2_PREPARATION_MANIFEST_SHA256,
    }
    if actual != EXPECTED:
        fail("review boundary mismatch")


def verify_record() -> str:
    evidence = RC2ReviewEvidence(84, True, True, True, True, True, True)
    first = review_rc2(evidence).canonical_bytes()
    second = review_rc2(evidence).canonical_bytes()
    if first != second:
        fail("review record is not deterministic")
    if not first.endswith(b"\n") or first.endswith(b"\n\n"):
        fail("canonical newline mismatch")
    body = json.loads(first)
    if body.get("status") != "READY_FOR_FREEZE_DECISION":
        fail("review status mismatch")
    if set(body.get("authority", {}).values()) != {False}:
        fail("release authority expanded")
    if body.get("findings") != {
        "complete_tree_coverage": "CORRECTED",
        "new_product_behavior": "NONE",
        "readme_scope": "CORRECTED",
    }:
        fail("review findings mismatch")
    digest = body.pop("review_digest", None)
    expected = hashlib.sha256(canonical_json_bytes(body)).hexdigest()
    if digest != expected:
        fail("review digest mismatch")
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
    review_digest = verify_record()
    print(f"RC2 FORMAL REVIEW SHA256 {review_digest}")
    print(f"RC2 FORMAL REVIEW MANIFEST SHA256 {manifest_digest()}")
    print("RC2 STATUS READY_FOR_FREEZE_DECISION")
    print("BOLT-ON CONTINUITY V0.3 RC2 FORMAL REVIEW VERIFICATION PASSED")


if __name__ == "__main__":
    run()
