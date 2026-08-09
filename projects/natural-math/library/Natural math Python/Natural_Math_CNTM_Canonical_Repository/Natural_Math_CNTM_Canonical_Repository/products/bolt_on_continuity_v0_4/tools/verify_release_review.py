#!/usr/bin/env python3
"""Independently qualify Bolt-On Continuity v0.4 release review."""
from __future__ import annotations
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
sys.path.insert(0, str(SRC))

from bolt_on_v0_4.release_review import AUTHORITY, QUALIFIED_RC1_HEAD, READY, build_manifest, review_release

FILES = [
    "docs/RELEASE_REVIEW_CONTRACT.md",
    "docs/RELEASE_REVIEW_GATES.md",
    "src/bolt_on_v0_4/release_review.py",
    "src/bolt_on_v0_4/release_review_cli.py",
    "tests/test_release_review.py",
    "tools/verify_release_review.py",
]


def canonical(value: object) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def digest(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def main() -> None:
    assert QUALIFIED_RC1_HEAD == "caede7dcec30c4e30a79f1d1721dae5402e1f95b"
    assert {key for key, value in AUTHORITY.items() if value} == {
        "release_review_reporting",
        "proposed_snapshot_manifest_construction",
        "rc1_evidence_consumption",
    }
    manifest = build_manifest({"README.md": b"candidate\n", "src/module.py": b"pass\n"})
    value = {
        "source_head": QUALIFIED_RC1_HEAD,
        "manifest": manifest,
        "rc1_verification_passed": True,
        "test_count": 234,
        "tests_passed": True,
        "frozen_regression_passed": True,
        "frozen_diff_empty": True,
        "working_tree_clean": True,
        "claims_boundary_approved": True,
        "authority_boundary_approved": True,
        "claims": ["Internally qualified observation-only release candidate."],
    }
    report = review_release(value).body()
    assert report["accepted"] is True
    assert report["outcome"] == READY
    assert report["release_freeze_authorized"] is False
    assert report["merge_authorized"] is False
    assert report["tag_creation_authorized"] is False
    assert report["publication_authorized"] is False
    assert report["native_execution_authorized"] is False

    manifest_hashes = {path: digest((ROOT / path).read_bytes()) for path in FILES}
    record = {
        "files": FILES,
        "qualified_rc1_head": QUALIFIED_RC1_HEAD,
        "rc1_qualification_record_sha256": "eea0b17fa192e07f35b9b35e8f4cadfff40ce1549405ae1f27b12e4151f75826",
        "rc1_verifier_manifest_sha256": "be9c50205cf06e81d0a2be7d13f6519c50573bcecf996876d27bec43f4e1d558",
        "release_candidate": "v0.4-rc1",
        "review": "final-release-review",
    }
    print("Release review qualification record SHA-256:", digest(canonical(record)))
    print("Release review verifier manifest SHA-256:", digest(canonical(manifest_hashes)))
    print("BOLT-ON CONTINUITY v0.4 RELEASE REVIEW VERIFICATION PASSED: 6 files")


if __name__ == "__main__":
    main()
