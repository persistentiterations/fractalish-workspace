from copy import deepcopy
from bolt_on_v0_4.rc1 import AUTHORITY, QUALIFIED_STAGE_10_HEAD, prepare_rc1, qualified_evidence


def test_complete_chain_is_review_ready():
    body = prepare_rc1(qualified_evidence(), QUALIFIED_STAGE_10_HEAD).body()
    assert body["accepted"] is True
    assert body["reason_code"] == "RC1_REVIEW_READY"
    assert body["evidence_count"] == 11
    assert body["release_review_authorized"] is True


def test_source_head_mismatch_fails_closed():
    body = prepare_rc1(qualified_evidence(), "0" * 40).body()
    assert body["accepted"] is False
    assert body["reason_code"] == "SOURCE_HEAD_MISMATCH"


def test_missing_evidence_fails_closed():
    body = prepare_rc1(qualified_evidence()[:-1], QUALIFIED_STAGE_10_HEAD).body()
    assert body["accepted"] is False
    assert body["reason_code"] == "INCOMPLETE_EVIDENCE_CHAIN"


def test_extra_evidence_fails_closed():
    evidence = qualified_evidence() + [qualified_evidence()[0]]
    assert prepare_rc1(evidence, QUALIFIED_STAGE_10_HEAD).body()["accepted"] is False


def test_reordered_evidence_fails_closed():
    evidence = qualified_evidence()
    evidence[0], evidence[1] = evidence[1], evidence[0]
    body = prepare_rc1(evidence, QUALIFIED_STAGE_10_HEAD).body()
    assert body["reason_code"] == "EVIDENCE_CHAIN_MISMATCH"


def test_record_digest_mismatch_fails_closed():
    evidence = qualified_evidence()
    evidence[4]["qualification_record_sha256"] = "0" * 64
    assert prepare_rc1(evidence, QUALIFIED_STAGE_10_HEAD).body()["accepted"] is False


def test_manifest_digest_mismatch_fails_closed():
    evidence = qualified_evidence()
    evidence[4]["verifier_manifest_sha256"] = "0" * 64
    assert prepare_rc1(evidence, QUALIFIED_STAGE_10_HEAD).body()["accepted"] is False


def test_authority_expansion_fails_closed():
    evidence = qualified_evidence()
    evidence[8]["authority_expanded"] = True
    body = prepare_rc1(evidence, QUALIFIED_STAGE_10_HEAD).body()
    assert body["reason_code"] == "AUTHORITY_EXPANSION_DETECTED"


def test_extra_field_fails_closed():
    evidence = qualified_evidence()
    evidence[3]["extra"] = True
    assert prepare_rc1(evidence, QUALIFIED_STAGE_10_HEAD).body()["reason_code"] == "MALFORMED_EVIDENCE"


def test_non_list_fails_closed():
    assert prepare_rc1({}, QUALIFIED_STAGE_10_HEAD).body()["reason_code"] == "MALFORMED_EVIDENCE"


def test_deterministic_report():
    first = prepare_rc1(qualified_evidence(), QUALIFIED_STAGE_10_HEAD).canonical_json()
    second = prepare_rc1(qualified_evidence(), QUALIFIED_STAGE_10_HEAD).canonical_json()
    assert first == second


def test_input_not_mutated():
    evidence = qualified_evidence()
    before = deepcopy(evidence)
    prepare_rc1(evidence, QUALIFIED_STAGE_10_HEAD)
    assert evidence == before


def test_non_authority_is_explicit():
    body = prepare_rc1(qualified_evidence(), QUALIFIED_STAGE_10_HEAD).body()
    assert body["release_freeze_authorized"] is False
    assert body["merge_authorized"] is False
    assert body["tag_creation_authorized"] is False
    assert body["publication_authorized"] is False
    assert body["installation_authorized"] is False
    assert body["distribution_authorized"] is False
    assert body["native_execution_authorized"] is False
    assert body["container_mutation_authorized"] is False
    assert body["production_readiness_claim_authorized"] is False


def test_authority_true_set_is_exact():
    assert {key for key, value in AUTHORITY.items() if value} == {
        "qualified_chain_consumption",
        "rc_manifest_construction",
        "release_review_reporting",
    }


def test_digests_are_lowercase_hex():
    body = prepare_rc1(qualified_evidence(), QUALIFIED_STAGE_10_HEAD).body()
    assert len(body["rc_manifest_digest"]) == 64
    assert len(body["report_digest"]) == 64
    assert body["rc_manifest_digest"] == body["rc_manifest_digest"].lower()
    assert body["report_digest"] == body["report_digest"].lower()
