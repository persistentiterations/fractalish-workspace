import json

from bolt_on.recovery_stage8 import RequestEvidence, SubjectEvidence, classify_recovery

CID = "a" * 64
OTHER = "b" * 64
REQ = "req-" + "c" * 64
DIGEST = "sha256:" + "d" * 64


def test_matched_subject_resumes_observation_only():
    report = classify_recovery(CID, "demo", [SubjectEvidence(CID, "demo", "running")], "STORE_HEALTHY")
    assert report.disposition == "RESUME_OBSERVATION_ONLY"
    assert report.body()["native_execution_authorized"] is False


def test_same_name_different_id_requires_reenrollment():
    report = classify_recovery(CID, "demo", [SubjectEvidence(OTHER, "demo", "running")], "STORE_HEALTHY")
    assert report.subject_classification == "SUBJECT_REPLACED"
    assert report.disposition == "REQUIRE_REENROLLMENT"


def test_stopped_and_missing_subjects_are_unavailable():
    stopped = classify_recovery(CID, "demo", [SubjectEvidence(CID, "demo", "exited")], "STORE_HEALTHY")
    missing = classify_recovery(CID, "demo", [], "STORE_HEALTHY")
    assert stopped.disposition == "REPORT_SUBJECT_UNAVAILABLE"
    assert missing.disposition == "REPORT_SUBJECT_UNAVAILABLE"


def test_unhealthy_store_fails_closed():
    report = classify_recovery(CID, "demo", [SubjectEvidence(CID, "demo", "running")], "STORE_CORRUPT")
    assert report.disposition == "FAIL_CLOSED_STORE"


def test_terminal_request_is_suppressed():
    prior = [RequestEvidence(REQ, DIGEST, "DOCKER_ACCEPTED")]
    report = classify_recovery(CID, "demo", [SubjectEvidence(CID, "demo", "running")], "STORE_HEALTHY", prior)
    assert report.disposition == "SUPPRESS_DUPLICATE"
    assert report.terminal_request_suppressed is True


def test_unresolved_or_conflicting_request_fails_closed():
    projected = [RequestEvidence(REQ, DIGEST, "APPROVED")]
    conflict = [RequestEvidence(REQ, DIGEST, "DENIED"), RequestEvidence(REQ, "sha256:" + "e" * 64, "DENIED")]
    assert classify_recovery(CID, "demo", [SubjectEvidence(CID, "demo", "running")], "STORE_HEALTHY", projected).disposition == "FAIL_CLOSED_UNCERTAIN"
    report = classify_recovery(CID, "demo", [SubjectEvidence(CID, "demo", "running")], "STORE_HEALTHY", conflict)
    assert report.disposition == "FAIL_CLOSED_UNCERTAIN"
    assert json.loads(report.canonical_json())["gateway_enabled"] is False
