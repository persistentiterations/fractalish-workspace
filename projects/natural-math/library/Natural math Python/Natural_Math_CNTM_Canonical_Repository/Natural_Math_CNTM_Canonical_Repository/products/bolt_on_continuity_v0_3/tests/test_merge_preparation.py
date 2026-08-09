import json

import pytest

from bolt_on.merge_preparation import (
    AHEAD_BY,
    BEHIND_BY,
    FROZEN_BRANCH_HEAD,
    FROZEN_MANIFEST,
    RC2_REVIEW_SHA256,
    TARGET_BRANCH,
    TARGET_HEAD,
    MergePreparationError,
    MergePreparationEvidence,
    prepare_merge,
)


def evidence(**changes):
    values = {
        "tests_passed": 90,
        "frozen_verification_passed": True,
        "fast_forward_only": True,
        "frozen_diff_clean": True,
        "working_tree_clean": True,
    }
    values.update(changes)
    return MergePreparationEvidence(**values)


def test_record_is_deterministic_and_pins_boundaries():
    first = prepare_merge(evidence()).canonical_bytes()
    second = prepare_merge(evidence()).canonical_bytes()
    assert first == second
    body = json.loads(first)
    assert body["status"] == "READY_FOR_MERGE_DECISION"
    assert body["merge"] == {
        "ahead_by": AHEAD_BY,
        "behind_by": BEHIND_BY,
        "candidate_head": FROZEN_BRANCH_HEAD,
        "target_branch": TARGET_BRANCH,
        "target_head": TARGET_HEAD,
    }
    assert body["release"]["frozen_manifest"] == FROZEN_MANIFEST
    assert body["release"]["rc2_review_sha256"] == RC2_REVIEW_SHA256


def test_authority_remains_denied():
    body = json.loads(prepare_merge(evidence()).canonical_bytes())
    assert set(body["authority"].values()) == {False}


@pytest.mark.parametrize(
    ("field", "value", "code"),
    [
        ("tests_passed", 89, "TEST_EVIDENCE_MISMATCH"),
        ("frozen_verification_passed", False, "FROZEN_VERIFICATION_NOT_PROVEN"),
        ("fast_forward_only", False, "FAST_FORWARD_NOT_PROVEN"),
        ("frozen_diff_clean", False, "FROZEN_DIFF_NOT_CLEAN"),
        ("working_tree_clean", False, "WORKING_TREE_NOT_CLEAN"),
    ],
)
def test_invalid_evidence_fails_closed(field, value, code):
    with pytest.raises(MergePreparationError, match=code):
        prepare_merge(evidence(**{field: value}))


def test_canonical_record_has_one_newline():
    payload = prepare_merge(evidence()).canonical_bytes()
    assert payload.endswith(b"\n")
    assert not payload.endswith(b"\n\n")
