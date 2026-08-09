import hashlib
import json

import pytest

from bolt_on.rc2_preparation import (
    CORRECTED_SOURCE_COMMIT,
    CORRECTED_TREE_FILES,
    CORRECTED_TREE_SHA256,
    RC2PreparationError,
    RC2PreparationEvidence,
    prepare_rc2,
)
from bolt_on.receipts import canonical_json_bytes


def evidence(**changes):
    values = {
        "tests_passed": 78,
        "rc1_review_passed": True,
        "frozen_regression_passed": True,
        "frozen_diff_clean": True,
        "working_tree_clean": True,
    }
    values.update(changes)
    return RC2PreparationEvidence(**values)


def test_rc2_record_is_deterministic_and_newline_terminated():
    first = prepare_rc2(evidence()).canonical_bytes()
    second = prepare_rc2(evidence()).canonical_bytes()
    assert first == second
    assert first.endswith(b"\n") and not first.endswith(b"\n\n")


def test_rc2_pins_corrected_complete_tree():
    body = json.loads(prepare_rc2(evidence()).canonical_bytes())
    assert body["corrected_candidate"] == {
        "source_commit": CORRECTED_SOURCE_COMMIT,
        "tree_files": CORRECTED_TREE_FILES,
        "tree_sha256": CORRECTED_TREE_SHA256,
    }


def test_rc1_is_superseded_without_being_rewritten():
    body = json.loads(prepare_rc2(evidence()).canonical_bytes())
    assert body["prior_candidate"] == {"candidate_id": "v0.3-rc1", "disposition": "NEEDS_CORRECTION"}
    assert body["candidate_id"] == "v0.3-rc2"


def test_record_digest_covers_every_field_except_itself():
    body = json.loads(prepare_rc2(evidence()).canonical_bytes())
    digest = body.pop("record_digest")
    assert digest == hashlib.sha256(canonical_json_bytes(body)).hexdigest()


def test_authority_remains_disabled():
    body = json.loads(prepare_rc2(evidence()).canonical_bytes())
    assert body["status"] == "READY_FOR_RC2_REVIEW"
    assert set(body["authority"].values()) == {False}


def test_incomplete_evidence_fails_closed():
    cases = (
        (evidence(tests_passed=77), "TEST_EVIDENCE_MISMATCH"),
        (evidence(rc1_review_passed=False), "RC1_REVIEW_NOT_PROVEN"),
        (evidence(frozen_regression_passed=False), "FROZEN_REGRESSION_NOT_PROVEN"),
        (evidence(frozen_diff_clean=False), "FROZEN_DIFF_NOT_CLEAN"),
        (evidence(working_tree_clean=False), "WORKING_TREE_NOT_CLEAN"),
    )
    for item, code in cases:
        with pytest.raises(RC2PreparationError, match=code):
            prepare_rc2(item)
