from dataclasses import replace
import json

from bolt_on_v0_4.stage_0 import AcceptanceEvidence, qualify_stage_zero


def good_evidence() -> AcceptanceEvidence:
    return AcceptanceEvidence(True, True, True, True, True)


def test_good_evidence_qualifies() -> None:
    assert qualify_stage_zero(good_evidence()).status == "STAGE_0_QUALIFIED"


def test_authority_remains_denied() -> None:
    assert set(qualify_stage_zero(good_evidence()).authority.values()) == {False}


def test_record_is_deterministic() -> None:
    assert qualify_stage_zero(good_evidence()).canonical_bytes() == qualify_stage_zero(good_evidence()).canonical_bytes()


def test_digest_is_present() -> None:
    body = json.loads(qualify_stage_zero(good_evidence()).canonical_bytes())
    assert len(body["record_digest"]) == 64


def test_missing_scope_is_rejected() -> None:
    assert qualify_stage_zero(replace(good_evidence(), scope_defined=False)).status == "NOT_READY"


def test_missing_authority_boundary_is_rejected() -> None:
    assert qualify_stage_zero(replace(good_evidence(), authority_denied=False)).status == "NOT_READY"
