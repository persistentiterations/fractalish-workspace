from __future__ import annotations
import copy
from bolt_on_v0_4.release_review import AUTHORITY, NOT_READY, PROPOSED_DESTINATION, QUALIFIED_RC1_HEAD, READY, build_manifest, review_release


def files():
    return {"README.md": b"candidate\n", "src/module.py": b"pass\n"}


def valid_input():
    return {
        "source_head": QUALIFIED_RC1_HEAD,
        "manifest": build_manifest(files()),
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


def test_ready():
    result = review_release(valid_input()).body()
    assert result["accepted"] is True and result["outcome"] == READY


def test_manifest_deterministic():
    assert build_manifest(files()) == build_manifest({"src/module.py": b"pass\n", "README.md": b"candidate\n"})


def test_wrong_head_fails():
    value = valid_input(); value["source_head"] = "0" * 40
    assert review_release(value).body()["outcome"] == NOT_READY


def test_tampered_manifest_fails():
    value = valid_input(); value["manifest"]["entries"][0]["byte_count"] = 99
    assert review_release(value).body()["reason_code"] == "MANIFEST_DIGEST_MISMATCH"


def test_wrong_destination_fails():
    value = valid_input(); manifest = copy.deepcopy(value["manifest"]); manifest["proposed_destination"] = "frozen/wrong"
    from bolt_on_v0_4.release_review import digest
    base = dict(manifest); base.pop("manifest_digest")
    manifest["manifest_digest"] = digest(base); value["manifest"] = manifest
    assert review_release(value).body()["reason_code"] == "MANIFEST_IDENTITY_MISMATCH"


def test_wrong_test_count_fails():
    value = valid_input(); value["test_count"] = 233
    assert review_release(value).body()["reason_code"] == "QUALIFICATION_EVIDENCE_MISMATCH"


def test_dirty_tree_fails():
    value = valid_input(); value["working_tree_clean"] = False
    assert review_release(value).body()["reason_code"] == "REPOSITORY_SAFETY_EVIDENCE_MISMATCH"


def test_frozen_diff_fails():
    value = valid_input(); value["frozen_diff_empty"] = False
    assert review_release(value).body()["outcome"] == NOT_READY


def test_boundary_missing_fails():
    value = valid_input(); value["authority_boundary_approved"] = False
    assert review_release(value).body()["reason_code"] == "BOUNDARY_APPROVAL_MISSING"


def test_prohibited_claim_fails():
    value = valid_input(); value["claims"] = ["production ready"]
    assert review_release(value).body()["reason_code"] == "PROHIBITED_CLAIM_DETECTED"


def test_safe_authority_exact():
    assert {key for key, enabled in AUTHORITY.items() if enabled} == {"release_review_reporting", "proposed_snapshot_manifest_construction", "rc1_evidence_consumption"}


def test_result_digest_deterministic():
    assert review_release(valid_input()).body()["review_digest"] == review_release(valid_input()).body()["review_digest"]


def test_ready_preserves_non_authority():
    result = review_release(valid_input()).body()
    assert result["proposed_destination"] == PROPOSED_DESTINATION
    assert result["release_freeze_authorized"] is False
    assert result["merge_authorized"] is False
    assert result["tag_creation_authorized"] is False
    assert result["publication_authorized"] is False
    assert result["native_execution_authorized"] is False
