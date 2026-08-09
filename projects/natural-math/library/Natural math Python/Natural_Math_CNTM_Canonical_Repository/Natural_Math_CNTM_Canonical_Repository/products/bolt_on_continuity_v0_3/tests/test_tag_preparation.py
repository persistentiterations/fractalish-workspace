from __future__ import annotations

import pytest

from bolt_on.tag_preparation import (
    FROZEN_MANIFEST,
    FROZEN_SOURCE_COMMIT,
    MERGED_BRANCH,
    MERGED_HEAD,
    PROPOSED_TAG,
    TagPreparationError,
    TagPreparationEvidence,
    prepare_tag,
)


def valid_evidence() -> TagPreparationEvidence:
    return TagPreparationEvidence(98, True, True, True, True)


def test_tag_preparation_is_deterministic() -> None:
    assert prepare_tag(valid_evidence()).canonical_bytes() == prepare_tag(valid_evidence()).canonical_bytes()


def test_tag_preparation_pins_release_boundary() -> None:
    body = prepare_tag(valid_evidence()).body
    assert MERGED_BRANCH == "main"
    assert MERGED_HEAD == "1c95a1ff8ead30675d4d26f7d77720097c5b9129"
    assert FROZEN_SOURCE_COMMIT == "67e0da7e41e96870d8dbeafa8031e4de694bb03f"
    assert FROZEN_MANIFEST == "3ce662d9be77735a9de53086160a3b2589f1b0feabcebba1551b080702f821bb"
    assert body["proposed_tag"]["target"] == MERGED_HEAD


def test_tag_name_is_pinned() -> None:
    body = prepare_tag(valid_evidence()).body
    assert PROPOSED_TAG == "bolt-on-continuity-v0.3"
    assert body["proposed_tag"] == {"kind": "annotated", "name": PROPOSED_TAG, "target": MERGED_HEAD}


def test_status_is_decision_only() -> None:
    assert prepare_tag(valid_evidence()).body["status"] == "READY_FOR_TAG_DECISION"


def test_authority_remains_denied() -> None:
    authority = prepare_tag(valid_evidence()).body["authority"]
    assert authority
    assert set(authority.values()) == {False}


@pytest.mark.parametrize(
    ("evidence", "message"),
    [
        (TagPreparationEvidence(97, True, True, True, True), "TEST_EVIDENCE_MISMATCH"),
        (TagPreparationEvidence(98, False, True, True, True), "MERGED_MAIN_NOT_PROVEN"),
        (TagPreparationEvidence(98, True, False, True, True), "FROZEN_REGRESSION_NOT_PROVEN"),
        (TagPreparationEvidence(98, True, True, False, True), "WORKING_TREE_NOT_CLEAN"),
        (TagPreparationEvidence(98, True, True, True, False), "TAG_ABSENCE_NOT_CHECKED"),
    ],
)
def test_missing_evidence_fails_closed(evidence: TagPreparationEvidence, message: str) -> None:
    with pytest.raises(TagPreparationError, match=message):
        prepare_tag(evidence)


def test_bool_is_not_accepted_as_test_count() -> None:
    with pytest.raises(TagPreparationError, match="TEST_EVIDENCE_MISMATCH"):
        prepare_tag(TagPreparationEvidence(True, True, True, True, True))


def test_record_contains_digest() -> None:
    digest = prepare_tag(valid_evidence()).body["record_digest"]
    assert isinstance(digest, str)
    assert len(digest) == 64
