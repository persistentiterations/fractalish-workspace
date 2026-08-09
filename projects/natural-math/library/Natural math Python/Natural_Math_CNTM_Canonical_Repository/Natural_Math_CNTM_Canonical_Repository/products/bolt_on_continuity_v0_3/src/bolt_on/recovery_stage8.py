"""Deterministic data-only recovery classification."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Mapping, Sequence

from .receipts import canonical_json_bytes

CID = re.compile(r"^[0-9a-f]{64}$")
DIGEST = re.compile(r"^sha256:[0-9a-f]{64}$")
REQUEST_ID = re.compile(r"^req-[0-9a-f]{64}$")
SUBJECT_STATES = {"running", "created", "paused", "restarting", "exited", "dead", "stopped"}
STORE_STATES = {
    "STORE_HEALTHY",
    "STORE_MISSING",
    "STORE_PERMISSION_DENIED",
    "STORE_PARTIAL_WRITE",
    "STORE_CORRUPT",
    "STORE_DISK_FULL",
    "STORE_AMBIGUOUS",
}
TERMINAL_ACTION_STATUSES = {"DENIED", "GATEWAY_REJECTED", "DOCKER_ACCEPTED", "DOCKER_REJECTED"}


class RecoveryError(ValueError):
    """Stable fail-closed Stage 8 error."""


@dataclass(frozen=True)
class SubjectEvidence:
    container_id: str
    display_name: str
    state: str


@dataclass(frozen=True)
class RequestEvidence:
    request_id: str
    request_digest: str
    action_status: str


@dataclass(frozen=True)
class RecoveryReport:
    subject_classification: str
    store_classification: str
    disposition: str
    reason_code: str
    terminal_request_suppressed: bool

    def body(self) -> dict[str, object]:
        return {
            "disposition": self.disposition,
            "gateway_enabled": False,
            "native_execution_authorized": False,
            "observation_only": True,
            "reason_code": self.reason_code,
            "schema_version": 1,
            "store_classification": self.store_classification,
            "subject_classification": self.subject_classification,
            "terminal_request_suppressed": self.terminal_request_suppressed,
        }

    def canonical_json(self) -> str:
        return canonical_json_bytes(self.body()).decode("utf-8")


def _validate_subject(item: SubjectEvidence) -> None:
    if not CID.fullmatch(item.container_id):
        raise RecoveryError("MALFORMED_SUBJECT_EVIDENCE")
    if not isinstance(item.display_name, str) or not item.display_name or len(item.display_name) > 256:
        raise RecoveryError("MALFORMED_SUBJECT_EVIDENCE")
    if item.state not in SUBJECT_STATES:
        raise RecoveryError("MALFORMED_SUBJECT_EVIDENCE")


def classify_subject(enrolled_id: str, enrolled_name: str, current: Sequence[SubjectEvidence]) -> str:
    if not CID.fullmatch(enrolled_id) or not isinstance(enrolled_name, str) or not enrolled_name:
        return "SUBJECT_AMBIGUOUS"
    try:
        for item in current:
            _validate_subject(item)
    except RecoveryError:
        return "SUBJECT_AMBIGUOUS"
    ids = [item.container_id for item in current]
    if len(ids) != len(set(ids)):
        return "SUBJECT_AMBIGUOUS"
    exact = [item for item in current if item.container_id == enrolled_id]
    if len(exact) > 1:
        return "SUBJECT_AMBIGUOUS"
    if exact:
        return "SUBJECT_STOPPED" if exact[0].state in {"exited", "dead", "stopped"} else "SUBJECT_MATCHED"
    replacements = [item for item in current if item.display_name == enrolled_name]
    if len(replacements) == 1:
        return "SUBJECT_REPLACED"
    if len(replacements) > 1:
        return "SUBJECT_AMBIGUOUS"
    return "SUBJECT_MISSING"


def _request_state(prior: Sequence[RequestEvidence]) -> tuple[bool, bool]:
    seen: dict[str, RequestEvidence] = {}
    terminal_duplicate = False
    uncertain = False
    for item in prior:
        if not REQUEST_ID.fullmatch(item.request_id) or not DIGEST.fullmatch(item.request_digest):
            uncertain = True
            continue
        previous = seen.get(item.request_id)
        if previous is not None:
            if previous.request_digest != item.request_digest:
                uncertain = True
            elif previous.action_status != item.action_status:
                uncertain = True
        seen[item.request_id] = item
        if item.action_status in TERMINAL_ACTION_STATUSES:
            terminal_duplicate = True
        elif item.action_status in {"PROJECTED", "APPROVED"}:
            uncertain = True
        elif item.action_status != "NOT_PROJECTED":
            uncertain = True
    return terminal_duplicate, uncertain


def classify_recovery(
    enrolled_id: str,
    enrolled_name: str,
    current: Sequence[SubjectEvidence],
    store_classification: str,
    prior_requests: Sequence[RequestEvidence] = (),
) -> RecoveryReport:
    subject = classify_subject(enrolled_id, enrolled_name, current)
    if store_classification not in STORE_STATES:
        store_classification = "STORE_AMBIGUOUS"
    terminal_duplicate, uncertain = _request_state(prior_requests)

    if subject == "SUBJECT_AMBIGUOUS":
        return RecoveryReport(subject, store_classification, "FAIL_CLOSED_UNCERTAIN", "AMBIGUOUS_SUBJECT_EVIDENCE", False)
    if store_classification != "STORE_HEALTHY":
        return RecoveryReport(subject, store_classification, "FAIL_CLOSED_STORE", "STORE_NOT_HEALTHY", False)
    if uncertain:
        return RecoveryReport(subject, store_classification, "FAIL_CLOSED_UNCERTAIN", "UNRESOLVED_ACTION_EVIDENCE", False)
    if terminal_duplicate:
        return RecoveryReport(subject, store_classification, "SUPPRESS_DUPLICATE", "TERMINAL_REQUEST_ALREADY_RECORDED", True)
    if subject == "SUBJECT_REPLACED":
        return RecoveryReport(subject, store_classification, "REQUIRE_REENROLLMENT", "SUBJECT_ID_CHANGED", False)
    if subject in {"SUBJECT_MISSING", "SUBJECT_STOPPED"}:
        return RecoveryReport(subject, store_classification, "REPORT_SUBJECT_UNAVAILABLE", subject, False)
    return RecoveryReport(subject, store_classification, "RESUME_OBSERVATION_ONLY", "RECOVERY_SAFE", False)
