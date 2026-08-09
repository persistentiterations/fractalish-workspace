#!/usr/bin/env python3
"""Independently qualify Bolt-On Continuity v0.4 RC1 preparation."""
from __future__ import annotations
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
sys.path.insert(0, str(SRC))

from bolt_on_v0_4.rc1 import AUTHORITY, QUALIFIED_STAGE_10_HEAD, prepare_rc1, qualified_evidence

FILES = [
    "docs/RC1_PREPARATION_CONTRACT.md",
    "docs/RC1_REVIEW_CHECKLIST.md",
    "src/bolt_on_v0_4/rc1.py",
    "src/bolt_on_v0_4/rc1_cli.py",
    "tests/test_rc1.py",
    "tools/verify_rc1.py",
]


def canonical(value: object) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def digest(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def main() -> None:
    assert QUALIFIED_STAGE_10_HEAD == "6e3843eed394cad1bc3ed00b4d148cdcaa2fbba9"
    assert {key for key, value in AUTHORITY.items() if value} == {
        "qualified_chain_consumption",
        "rc_manifest_construction",
        "release_review_reporting",
    }
    report = prepare_rc1(qualified_evidence(), QUALIFIED_STAGE_10_HEAD).body()
    assert report["accepted"] is True
    assert report["reason_code"] == "RC1_REVIEW_READY"
    assert report["evidence_count"] == 11
    assert report["release_review_authorized"] is True
    assert report["release_freeze_authorized"] is False
    assert report["merge_authorized"] is False
    assert report["tag_creation_authorized"] is False
    assert report["publication_authorized"] is False
    assert report["native_execution_authorized"] is False

    manifest = {path: digest((ROOT / path).read_bytes()) for path in FILES}
    record = {
        "files": FILES,
        "qualified_stage_10_head": QUALIFIED_STAGE_10_HEAD,
        "release_candidate": "RC1",
        "stage_10_qualification_record_sha256": "39cdb080b6710b147e369e4b28b2414c04d7f8a34acf1cf1f7c1538b4bfbe943",
        "stage_10_verifier_manifest_sha256": "f22e0dd0931982ebd38f346bee0a4326d5ce2cc1f85b3d6a01d5c16e949df46b",
    }
    print("RC1 qualification record SHA-256:", digest(canonical(record)))
    print("RC1 verifier manifest SHA-256:", digest(canonical(manifest)))
    print("BOLT-ON CONTINUITY v0.4 RC1 PREPARATION VERIFICATION PASSED: 6 files")


if __name__ == "__main__":
    main()
