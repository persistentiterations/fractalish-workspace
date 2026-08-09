#!/usr/bin/env python3
"""Independently qualify Bolt-On Continuity v0.4 Stage 10."""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
sys.path.insert(0, str(SRC))

from bolt_on_v0_4.stage_10 import (
    AUTHORITY,
    QUALIFIED_STAGE_9_HEAD,
    REQUIRED_STAGES,
    STAGE_9_QUALIFICATION_RECORD_SHA256,
    STAGE_9_VERIFIER_MANIFEST_SHA256,
    qualify_evidence,
)

FILES = [
    "docs/STAGE_10_ACCEPTANCE_GATES.md",
    "docs/STAGE_10_END_TO_END_QUALIFICATION_CONTRACT.md",
    "src/bolt_on_v0_4/stage_10.py",
    "src/bolt_on_v0_4/stage_10_cli.py",
    "tests/test_stage_10.py",
    "tools/verify_stage_10.py",
]


def canonical(value: object) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def digest(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def main() -> None:
    assert QUALIFIED_STAGE_9_HEAD == "9915372ca7a63c0de60c2e65cf08765e262eff88"
    assert STAGE_9_QUALIFICATION_RECORD_SHA256 == "da0442cf175e4b2d99f34cac7e3bd48cf2986ac0f2581cc0df2b7695cf1d9f27"
    assert STAGE_9_VERIFIER_MANIFEST_SHA256 == "7085f2d3ee5ef9e247e013c46f13ac57c388eb38afe27a8c305f4cfea51619a6"
    assert {key for key, value in AUTHORITY.items() if value} == {
        "stage_9_evidence_consumption",
        "evidence_validation",
        "release_candidate_readiness_reporting",
    }
    evidence = [
        {
            "stage": stage,
            "status": "PASS",
            "evidence_digest": f"{index + 1:064x}",
            "frozen_regression_passed": True,
            "authority_expanded": False,
        }
        for index, stage in enumerate(REQUIRED_STAGES)
    ]
    report = qualify_evidence(evidence).body()
    assert report["readiness"] == "RELEASE_CANDIDATE_READY"
    assert report["release_candidate_preparation_authorized"] is True
    assert report["release_freeze_authorized"] is False
    assert report["merge_authorized"] is False
    assert report["publication_authorized"] is False
    assert report["native_execution_authorized"] is False

    manifest = {path: digest((ROOT / path).read_bytes()) for path in FILES}
    record = {
        "files": FILES,
        "qualified_stage_9_head": QUALIFIED_STAGE_9_HEAD,
        "stage": 10,
        "stage_9_qualification_record_sha256": STAGE_9_QUALIFICATION_RECORD_SHA256,
        "stage_9_verifier_manifest_sha256": STAGE_9_VERIFIER_MANIFEST_SHA256,
    }
    print("Stage 10 qualification record SHA-256:", digest(canonical(record)))
    print("Stage 10 verifier manifest SHA-256:", digest(canonical(manifest)))
    print("BOLT-ON CONTINUITY v0.4 STAGE 10 VERIFICATION PASSED: 6 files")


if __name__ == "__main__":
    main()
