import hashlib
import json

import pytest

from bolt_on.rc2_review import (
    CORRECTED_SOURCE_COMMIT,
    CORRECTED_TREE_FILES,
    CORRECTED_TREE_SHA256,
    RC2_PREPARATION_HEAD,
    RC2_PREPARATION_MANIFEST_SHA256,
    RC2_RECORD_SHA256,
    RC2ReviewError,
    RC2ReviewEvidence,
    review_rc2,
)
from bolt_on.receipts import canonical_json_bytes


def evidence(**changes):
    values = {
        "tests_passed": 84,
        "rc2_preparation_passed": True,
        "rc1_findings_corrected": True,
        "preparation_delta_only": True,
        "frozen_regression_passed": True,
        "frozen_diff_clean": True,
        "working_tree_clean": True,
    }
    values.update(changes)
    return RC2ReviewEvidence(**values)


def test_review_record_is_deterministic_and_newline_terminated():
    first = review_rc2(evidence()).canonical_bytes()
    second = review_rc2(evidence()).canonical_bytes()
    assert first == second
    assert first.endswith(b"\n") and not first.endswith(b"\n\n")


def test_review_pins_corrected_candidate_and_rc2_preparation():
    body = json.loads(review_rc2(evidence()).canonical_bytes())
    assert body["corrected_candidate"] == {
        "source_commit": CORRECTED_SOURCE_COMMIT,
        "tree_files": CORRECTED_TREE_FILES,
        "tree_sha256": CORRECTED_TREE_SHA256,
    }
    assert body["rc2_preparation"] == {
        "head": RC2_PREPARATION_HEAD,
        "manifest_sha256": RC2_PREPARATION_MANIFEST_SHA256,
        "record_sha256": RC2_RECORD_SHA256,
    }


def test_review_digest_covers_every_field_except_itself():
    body = json.loads(review_rc2(evidence()).canonical_bytes())
    digest = body.pop("review_digest")
    assert digest == hashlib.sha256(canonical_json_bytes(body)).hexdigest()


def test_findings_are_corrected_and_no_new_behavior_is_claimed():
    body = json.loads(review_rc2(evidence()).canonical_bytes())
    assert body["findings"] == {
        "complete_tree_coverage": "CORRECTED",
        "new_product_behavior": "NONE",
        "readme_scope": "CORRECTED",
    }
    assert body["status"] == "READY_FOR_FREEZE_DECISION"


def test_authority_remains_explicitly_disabled():
    body = json.loads(review_rc2(evidence()).canonical_bytes())
    assert set(body["authority"].values()) == {False}


def test_failed_or_incomplete_evidence_fails_closed():
    cases = (
        (evidence(tests_passed=83), "TEST_EVIDENCE_MISMATCH"),
        (evidence(rc2_preparation_passed=False), "RC2_PREPARATION_NOT_PROVEN"),
        (evidence(rc1_findings_corrected=False), "RC1_FINDINGS_NOT_CORRECTED"),
        (evidence(preparation_delta_only=False), "PREPARATION_DELTA_NOT_PROVEN"),
        (evidence(frozen_regression_passed=False), "FROZEN_REGRESSION_NOT_PROVEN"),
        (evidence(frozen_diff_clean=False), "FROZEN_DIFF_NOT_CLEAN"),
        (evidence(working_tree_clean=False), "WORKING_TREE_NOT_CLEAN"),
    )
    for item, code in cases:
        with pytest.raises(RC2ReviewError, match=code):
            review_rc2(item)
