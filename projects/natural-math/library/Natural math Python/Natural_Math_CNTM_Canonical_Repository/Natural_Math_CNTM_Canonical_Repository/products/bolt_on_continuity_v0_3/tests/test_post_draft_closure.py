from dataclasses import replace
import json

from bolt_on.post_draft_closure import (
    FROZEN_MANIFEST,
    RELEASE_NOTES_SHA256,
    RELEASE_TITLE,
    REPOSITORY,
    TAG_NAME,
    TAG_OBJECT,
    TAG_TARGET,
    PostDraftEvidence,
    close_post_draft,
)


def good_evidence() -> PostDraftEvidence:
    return PostDraftEvidence(
        tests_passed=126,
        release_exists=True,
        release_is_draft=True,
        release_is_unpublished=True,
        release_title_matches=True,
        tag_matches=True,
        tag_target_matches=True,
        release_notes_match=True,
        uploaded_assets_absent=True,
        frozen_verifier_passed=True,
        all_frozen_passed=True,
        frozen_diff_clean=True,
        worktree_clean=True,
    )


def test_pinned_identity() -> None:
    assert REPOSITORY == "BonAcqui-LLC/cntm-natural-math-canonical-library"
    assert RELEASE_TITLE == "Bolt-On Continuity v0.3"
    assert TAG_NAME == "bolt-on-continuity-v0.3"
    assert TAG_OBJECT == "fc3e27567e38a94322b437a4285c52ee38ac8407"
    assert TAG_TARGET == "1c95a1ff8ead30675d4d26f7d77720097c5b9129"
    assert FROZEN_MANIFEST == "3ce662d9be77735a9de53086160a3b2589f1b0feabcebba1551b080702f821bb"
    assert RELEASE_NOTES_SHA256 == "cafe56a302ecc7f091762a0e90f2d404f90b48683fee9e6272e522c71e622d30"


def test_good_evidence_closes_track() -> None:
    record = close_post_draft(good_evidence())
    assert record.status == "POST_DRAFT_CLOSED"
    assert record.source_archives_expected == 2


def test_authority_remains_denied() -> None:
    record = close_post_draft(good_evidence())
    assert record.authority
    assert set(record.authority.values()) == {False}


def test_record_is_deterministic() -> None:
    assert close_post_draft(good_evidence()).canonical_bytes() == close_post_draft(good_evidence()).canonical_bytes()


def test_digest_is_present() -> None:
    body = json.loads(close_post_draft(good_evidence()).canonical_bytes())
    assert len(body["record_digest"]) == 64


def test_published_release_is_rejected() -> None:
    evidence = replace(good_evidence(), release_is_draft=False, release_is_unpublished=False)
    assert close_post_draft(evidence).status == "NOT_READY"


def test_uploaded_asset_is_rejected() -> None:
    evidence = replace(good_evidence(), uploaded_assets_absent=False)
    assert close_post_draft(evidence).status == "NOT_READY"


def test_mismatched_notes_are_rejected() -> None:
    evidence = replace(good_evidence(), release_notes_match=False)
    assert close_post_draft(evidence).status == "NOT_READY"
