import json

import pytest

from bolt_on.qualification_stage10 import QualificationError, REQUIRED_STAGES, qualify


def evidence():
    return {
        stage: {
            "stage": stage,
            "status": "PASS",
            "evidence_digest": f"{index + 1:064x}",
            "frozen_regression_passed": True,
            "authority_expanded": False,
        }
        for index, stage in enumerate(REQUIRED_STAGES)
    }


def test_qualification_is_deterministic_across_mapping_order():
    one = qualify(evidence())
    reversed_evidence = dict(reversed(list(evidence().items())))
    two = qualify(reversed_evidence)
    assert one.canonical_bytes() == two.canonical_bytes()
    assert one.canonical_bytes().endswith(b"\n")


def test_ready_report_keeps_all_execution_and_release_authority_disabled():
    body = json.loads(qualify(evidence()).canonical_bytes())
    assert body["readiness"] == "RELEASE_CANDIDATE_READY"
    assert body["authority_boundary_intact"] is True
    assert body["frozen_regression_passed"] is True
    assert all(value is False for key, value in body["safety"].items() if key != "observation_only")
    assert body["safety"]["observation_only"] is True


def test_missing_or_extra_stage_fails_closed():
    missing = evidence()
    missing.pop(REQUIRED_STAGES[-1])
    with pytest.raises(QualificationError, match="STAGE_EVIDENCE_SET_MISMATCH"):
        qualify(missing)
    extra = evidence()
    extra["stage_10_extra"] = extra[REQUIRED_STAGES[0]]
    with pytest.raises(QualificationError, match="STAGE_EVIDENCE_SET_MISMATCH"):
        qualify(extra)


def test_failed_or_mismatched_stage_fails_closed():
    value = evidence()
    value[REQUIRED_STAGES[2]]["status"] = "FAIL"
    with pytest.raises(QualificationError, match="FAILED_OR_CONFLICTING_STAGE_EVIDENCE"):
        qualify(value)
    value = evidence()
    value[REQUIRED_STAGES[2]]["stage"] = "wrong"
    with pytest.raises(QualificationError, match="FAILED_OR_CONFLICTING_STAGE_EVIDENCE"):
        qualify(value)


def test_bad_digest_or_regression_failure_fails_closed():
    value = evidence()
    value[REQUIRED_STAGES[4]]["evidence_digest"] = "ABC"
    with pytest.raises(QualificationError, match="INVALID_EVIDENCE_DIGEST"):
        qualify(value)
    value = evidence()
    value[REQUIRED_STAGES[4]]["frozen_regression_passed"] = False
    with pytest.raises(QualificationError, match="FROZEN_REGRESSION_NOT_PROVEN"):
        qualify(value)


def test_authority_expansion_or_extra_record_field_fails_closed():
    value = evidence()
    value[REQUIRED_STAGES[6]]["authority_expanded"] = True
    with pytest.raises(QualificationError, match="AUTHORITY_EXPANSION_DETECTED"):
        qualify(value)
    value = evidence()
    value[REQUIRED_STAGES[6]]["command"] = "docker pause"
    with pytest.raises(QualificationError, match="MALFORMED_STAGE_EVIDENCE"):
        qualify(value)
