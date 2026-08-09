"""Deterministic data-only approval and gateway boundary."""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from typing import Mapping, Sequence

from .receipts import canonical_json_bytes

CID = re.compile(r"^[0-9a-f]{64}$")
DIGEST = re.compile(r"^sha256:[0-9a-f]{64}$")
REQUEST_ID = re.compile(r"^req-[0-9a-f]{64}$")
REASON = re.compile(r"^[A-Z][A-Z0-9_]{0,63}$")
ACTIONS = {"HOLD", "RELEASE"}
DECISIONS = {"APPROVE", "DENY"}
GATEWAY_STATES = {"DISABLED", "ENABLED"}


class ApprovalError(ValueError):
    """Stable fail-closed Stage 7 error."""


def _sha(body: Mapping[str, object]) -> str:
    return "sha256:" + hashlib.sha256(canonical_json_bytes(body)).hexdigest()


@dataclass(frozen=True)
class ProjectedRequest:
    request_id: str
    container_id: str
    action: str
    incident_digest: str
    configuration_digest: str
    issued_sequence: int
    expiry_sequence: int
    request_digest: str

    def base(self) -> dict[str, object]:
        return {
            "action": self.action,
            "configuration_digest": self.configuration_digest,
            "container_id": self.container_id,
            "expiry_sequence": self.expiry_sequence,
            "incident_digest": self.incident_digest,
            "issued_sequence": self.issued_sequence,
            "request_id": self.request_id,
            "schema_version": 1,
        }

    def body(self) -> dict[str, object]:
        return {**self.base(), "request_digest": self.request_digest}


@dataclass(frozen=True)
class GatewayState:
    state: str = "DISABLED"
    sequence: int = 0


@dataclass(frozen=True)
class DecisionRecord:
    request_id: str
    request_digest: str
    decision: str
    reason_code: str
    decision_sequence: int
    decision_digest: str

    def body(self) -> dict[str, object]:
        return {
            "decision": self.decision,
            "decision_digest": self.decision_digest,
            "decision_sequence": self.decision_sequence,
            "native_execution_authorized": False,
            "reason_code": self.reason_code,
            "request_digest": self.request_digest,
            "request_id": self.request_id,
            "schema_version": 1,
        }


def create_request(request_id: str, container_id: str, action: str, incident_digest: str, configuration_digest: str, issued_sequence: int, expiry_sequence: int) -> ProjectedRequest:
    probe = ProjectedRequest(request_id, container_id, action, incident_digest, configuration_digest, issued_sequence, expiry_sequence, "")
    _validate_request_fields(probe)
    return ProjectedRequest(
        request_id,
        container_id,
        action,
        incident_digest,
        configuration_digest,
        issued_sequence,
        expiry_sequence,
        _sha(probe.base()),
    )


def _validate_request_fields(request: ProjectedRequest) -> None:
    if not REQUEST_ID.fullmatch(request.request_id) or not CID.fullmatch(request.container_id):
        raise ApprovalError("INVALID_REQUEST_IDENTITY")
    if request.action not in ACTIONS:
        raise ApprovalError("INVALID_ACTION")
    if not DIGEST.fullmatch(request.incident_digest) or not DIGEST.fullmatch(request.configuration_digest):
        raise ApprovalError("INVALID_DIGEST")
    if type(request.issued_sequence) is not int or type(request.expiry_sequence) is not int or request.issued_sequence < 0 or request.expiry_sequence <= request.issued_sequence:
        raise ApprovalError("INVALID_SEQUENCE_WINDOW")


def validate_request(request: ProjectedRequest) -> None:
    _validate_request_fields(request)
    if request.request_digest != _sha(request.base()):
        raise ApprovalError("REQUEST_DIGEST_MISMATCH")


def transition_gateway(current: GatewayState, target: str, sequence: int) -> GatewayState:
    if current.state not in GATEWAY_STATES or target not in GATEWAY_STATES:
        raise ApprovalError("INVALID_GATEWAY_STATE")
    if type(sequence) is not int or sequence <= current.sequence:
        raise ApprovalError("INVALID_GATEWAY_SEQUENCE")
    if target == current.state:
        raise ApprovalError("NO_GATEWAY_TRANSITION")
    return GatewayState(target, sequence)


def decide(request: ProjectedRequest, gateway: GatewayState, decision: str, reason_code: str, decision_sequence: int, prior: Sequence[DecisionRecord] = ()) -> DecisionRecord:
    validate_request(request)
    if decision not in DECISIONS:
        raise ApprovalError("INVALID_DECISION")
    if not REASON.fullmatch(reason_code):
        raise ApprovalError("INVALID_REASON_CODE")
    if type(decision_sequence) is not int or not request.issued_sequence <= decision_sequence <= request.expiry_sequence:
        raise ApprovalError("DECISION_OUTSIDE_WINDOW")
    if decision == "APPROVE" and (gateway.state != "ENABLED" or gateway.sequence > decision_sequence):
        raise ApprovalError("GATEWAY_NOT_ENABLED")
    for record in prior:
        if record.request_id != request.request_id:
            continue
        if record.request_digest != request.request_digest:
            raise ApprovalError("REQUEST_IDENTIFIER_REUSE")
        if record.decision == decision and record.reason_code == reason_code and record.decision_sequence == decision_sequence:
            raise ApprovalError("DUPLICATE_DECISION")
        raise ApprovalError("CONFLICTING_DECISION")
    base = {
        "decision": decision,
        "decision_sequence": decision_sequence,
        "reason_code": reason_code,
        "request_digest": request.request_digest,
        "request_id": request.request_id,
        "schema_version": 1,
    }
    return DecisionRecord(request.request_id, request.request_digest, decision, reason_code, decision_sequence, _sha(base))
