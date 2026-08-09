import hashlib
import json

import pytest

from bolt_on.rc1_preparation import (
    QUALIFIED_SOURCE_COMMIT,
    RCPreparationError,
    RCPreparationEvidence,
    STAGE_MANIFESTS,
    prepare_rc1,
)
from bolt_on.receipts import canonical_json_bytes


def evidence(**changes):
    values = {
        "tests_passed": 66,
        "frozen_regression_passed": True,
        "frozen_diff_clean": True,
        "working_tree_clean": True,
    }
    values.update(changes)
    return RCPreparationEvidence(**values)


def test_rc1_record_is_deterministic_and_newline_terminated():
    one = prepare_rc1(evidence()).canonical_bytes()
    two = prepare_rc1(evidence()).canonical_bytes()
    assert one == two
    assert one.endswith(b"\n") and not one.endswith(b"\n\n")


def test_record_pins_qualified_source_and_all_stage_manifests():
    body = json.loads(prepare_rc1(evidence()).canonical_bytes())
    assert body["qualified_source_commit"] == QUALIFIED_SOURCE_COMMIT
    assert body["stage_manifests"] == STAGE_MANIFESTS
    assert sorted(body["stage_manifests"], key=lambda key: int(key.removeprefix("stage_"))) == [
        f"stage_{index}" for index in range(11)
    ]


def test_record_digest_covers_every_field_except_itself():
    body = json.loads(prepare_rc1(evidence()).canonical_bytes())
    digest = body.pop("record_digest")
    assert digest == hashlib.sha256(canonical_json_bytes(body)).hexdigest()


def test_authority_remains_explicitly_disabled():
    body = json.loads(prepare_rc1(evidence()).canonical_bytes())
    assert body["status"] == "READY_FOR_RC_REVIEW"
    assert set(body["authority"].values()) == {False}


def test_failed_or_incomplete_evidence_fails_closed():
    cases = (
        (evidence(tests_passed=65), "TEST_EVIDENCE_MISMATCH"),
        (evidence(frozen_regression_passed=False), "FROZEN_REGRESSION_NOT_PROVEN"),
        (evidence(frozen_diff_clean=False), "FROZEN_DIFF_NOT_CLEAN"),
        (evidence(working_tree_clean=False), "WORKING_TREE_NOT_CLEAN"),
    )
    for item, code in cases:
        with pytest.raises(RCPreparationError, match=code):
            prepare_rc1(item)


def test_boolean_test_count_is_rejected():
    with pytest.raises(RCPreparationError, match="TEST_EVIDENCE_MISMATCH"):
        prepare_rc1(evidence(tests_passed=True))
