from __future__ import annotations

import hashlib
import json

from bolt_on.receipts import canonical_json_bytes
from bolt_on.release_preparation import (
    FROZEN_MANIFEST,
    RELEASE_NOTES,
    RELEASE_TITLE,
    REPOSITORY,
    TAG_NAME,
    TAG_OBJECT,
    TAG_TARGET,
    ReleasePreparationEvidence,
    prepare_release,
)


def qualified() -> ReleasePreparationEvidence:
    return ReleasePreparationEvidence(110, True, True, True, True, True, True)


def test_release_identity_is_pinned() -> None:
    assert REPOSITORY == "BonAcqui-LLC/cntm-natural-math-canonical-library"
    assert TAG_NAME == "bolt-on-continuity-v0.3"
    assert TAG_OBJECT == "fc3e27567e38a94322b437a4285c52ee38ac8407"
    assert TAG_TARGET == "1c95a1ff8ead30675d4d26f7d77720097c5b9129"
    assert FROZEN_MANIFEST == "3ce662d9be77735a9de53086160a3b2589f1b0feabcebba1551b080702f821bb"
    assert RELEASE_TITLE == "Bolt-On Continuity v0.3"


def test_qualified_status_is_ready_for_decision() -> None:
    record = prepare_release(qualified())
    assert record.status == "READY_FOR_RELEASE_DECISION"
    assert record.draft is True
    assert record.prerelease is True
    assert record.assets == ()


def test_authority_remains_false() -> None:
    record = prepare_release(qualified())
    assert set(record.authority.values()) == {False}


def test_record_is_deterministic() -> None:
    assert prepare_release(qualified()).canonical_bytes() == prepare_release(qualified()).canonical_bytes()


def test_record_digest_is_valid() -> None:
    body = json.loads(prepare_release(qualified()).canonical_bytes())
    digest = body.pop("record_digest")
    assert digest == hashlib.sha256(canonical_json_bytes(body)).hexdigest()


def test_notes_preserve_observation_boundary() -> None:
    lowered = RELEASE_NOTES.lower()
    assert "observation-only" in lowered
    assert "does not" in lowered
    assert "mutate containers" in lowered
    assert "production readiness" in lowered
    assert "release assets: none" in lowered


def test_missing_evidence_is_not_ready() -> None:
    fields = [
        ReleasePreparationEvidence(109, True, True, True, True, True, True),
        ReleasePreparationEvidence(110, False, True, True, True, True, True),
        ReleasePreparationEvidence(110, True, False, True, True, True, True),
        ReleasePreparationEvidence(110, True, True, False, True, True, True),
        ReleasePreparationEvidence(110, True, True, True, False, True, True),
        ReleasePreparationEvidence(110, True, True, True, True, False, True),
        ReleasePreparationEvidence(110, True, True, True, True, True, False),
    ]
    assert all(prepare_release(item).status == "NOT_READY" for item in fields)


def test_notes_digest_is_pinned_in_record() -> None:
    record = prepare_release(qualified())
    assert record.release_notes_sha256 == hashlib.sha256(RELEASE_NOTES.encode("utf-8")).hexdigest()
