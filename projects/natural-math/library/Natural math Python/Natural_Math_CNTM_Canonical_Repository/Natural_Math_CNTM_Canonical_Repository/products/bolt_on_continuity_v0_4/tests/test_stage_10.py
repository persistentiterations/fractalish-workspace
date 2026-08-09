import pytest
from bolt_on_v0_4.stage_10 import AUTHORITY, REQUIRED_STAGES, canonical_bytes, qualify_evidence, sha256


def evidence():
    return [
        {
            "stage": stage,
            "status": "PASS",
            "evidence_digest": f"{index + 1:064x}",
            "frozen_regression_passed": True,
            "authority_expanded": False,
        }
        for index, stage in enumerate(REQUIRED_STAGES)
    ]


def test_ready_report():
    body = qualify_evidence(evidence()).body()
    assert body["accepted"] is True
    assert body["readiness"] == "RELEASE_CANDIDATE_READY"
    assert body["release_candidate_preparation_authorized"] is True


def test_deterministic_order():
    values = list(reversed(evidence()))
    body = qualify_evidence(values).body()
    assert [item["stage"] for item in body["evidence"]] == list(REQUIRED_STAGES)


def test_missing_fails_closed():
    body = qualify_evidence(evidence()[:-1]).body()
    assert body["readiness"] == "FAIL_CLOSED_NOT_READY"
    assert body["reason_code"] == "MISSING_STAGE_EVIDENCE"


def test_duplicate_fails_closed():
    values = evidence(); values.append(dict(values[0]))
    assert qualify_evidence(values).body()["reason_code"] == "DUPLICATE_STAGE_EVIDENCE"


@pytest.mark.parametrize(
    "field,value,reason",
    [
        ("status", "FAIL", "STAGE_EVIDENCE_NOT_PASSING"),
        ("evidence_digest", "bad", "INVALID_EVIDENCE_DIGEST"),
        ("frozen_regression_passed", False, "FROZEN_REGRESSION_NOT_PROVEN"),
        ("authority_expanded", True, "AUTHORITY_EXPANSION_DETECTED"),
        ("stage", "stage_99_unknown", "UNKNOWN_STAGE_EVIDENCE"),
    ],
)
def test_invalid_evidence(field, value, reason):
    values = evidence(); values[0][field] = value
    assert qualify_evidence(values).body()["reason_code"] == reason


def test_extra_field_fails_closed():
    values = evidence(); values[0]["extra"] = True
    assert qualify_evidence(values).body()["reason_code"] == "EVIDENCE_FIELDS_MISMATCH"


def test_non_list_fails_closed():
    assert qualify_evidence({}).body()["reason_code"] == "MALFORMED_EVIDENCE_COLLECTION"


def test_report_digest():
    body = qualify_evidence(evidence()).body()
    base = dict(body); digest = base.pop("report_digest")
    assert digest == sha256(canonical_bytes(base))


def test_repeat_is_identical():
    assert qualify_evidence(evidence()).canonical_bytes() == qualify_evidence(evidence()).canonical_bytes()


def test_safety_flags():
    body = qualify_evidence(evidence()).body()
    assert body["observation_only"] is True
    assert body["native_execution_authorized"] is False
    assert body["container_mutation_authorized"] is False
    assert body["release_freeze_authorized"] is False
    assert body["merge_authorized"] is False
    assert body["publication_authorized"] is False
    assert body["tag_creation_authorized"] is False
    assert body["production_readiness_claim_authorized"] is False


def test_authority_exact_enabled_set():
    assert {key for key, value in AUTHORITY.items() if value} == {
        "stage_9_evidence_consumption",
        "evidence_validation",
        "release_candidate_readiness_reporting",
    }


def test_capability_counts():
    body = qualify_evidence(evidence()).body()
    assert len(body["bounded_capabilities"]) == 9
    assert "native_execution" in body["excluded_capabilities"]
