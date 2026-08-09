from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from typing import Any, Mapping

SCHEMA_VERSION = "1"
ALLOWED_ACTIONS = ("HOLD", "RELEASE")
ALLOWED_DECISIONS = ("APPROVE", "DENY")
ALLOWED_REASONS = ("OPERATOR_APPROVED", "OPERATOR_DENIED", "SAFETY_CONCERN", "NOT_REQUIRED")
CONTAINER_ID_RE = re.compile(r"^[0-9a-f]{64}$")
DIGEST_RE = re.compile(r"^sha256:[0-9a-f]{64}$")
REQUEST_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")


class OperatorControlError(ValueError):
    pass


def _canonical_bytes(value: Mapping[str, Any]) -> bytes:
    return (json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False) + "\n").encode("utf-8")


def _digest(value: Mapping[str, Any], digest_field: str) -> str:
    payload = dict(value)
    payload.pop(digest_field, None)
    return "sha256:" + hashlib.sha256(_canonical_bytes(payload)).hexdigest()


def _strict_positive_int(value: Any, field: str) -> int:
    if type(value) is not int or value < 0:
        raise OperatorControlError(f"invalid {field}")
    return value


def build_projected_request(
    *,
    request_id: str,
    container_id: str,
    action: str,
    incident_digest: str,
    configuration_digest: str,
    issued_sequence: int,
    expiry_sequence: int,
) -> dict[str, Any]:
    request: dict[str, Any] = {
        "action": action,
        "configuration_digest": configuration_digest,
        "container_id": container_id,
        "expiry_sequence": expiry_sequence,
        "incident_digest": incident_digest,
        "issued_sequence": issued_sequence,
        "request_id": request_id,
        "schema_version": SCHEMA_VERSION,
    }
    _validate_request_fields(request)
    request["request_digest"] = _digest(request, "request_digest")
    return request


def _validate_request_fields(request: Mapping[str, Any]) -> None:
    if request.get("schema_version") != SCHEMA_VERSION:
        raise OperatorControlError("unsupported request schema")
    request_id = request.get("request_id")
    if not isinstance(request_id, str) or REQUEST_ID_RE.fullmatch(request_id) is None:
        raise OperatorControlError("invalid request ID")
    container_id = request.get("container_id")
    if not isinstance(container_id, str) or CONTAINER_ID_RE.fullmatch(container_id) is None:
        raise OperatorControlError("invalid container ID")
    if request.get("action") not in ALLOWED_ACTIONS:
        raise OperatorControlError("unsupported action")
    for field in ("incident_digest", "configuration_digest"):
        value = request.get(field)
        if not isinstance(value, str) or DIGEST_RE.fullmatch(value) is None:
            raise OperatorControlError(f"invalid {field}")
    issued = _strict_positive_int(request.get("issued_sequence"), "issued sequence")
    expiry = _strict_positive_int(request.get("expiry_sequence"), "expiry sequence")
    if expiry <= issued:
        raise OperatorControlError("expiry must be greater than issuance")


def validate_projected_request(request: Mapping[str, Any]) -> dict[str, Any]:
    expected = {
        "action", "configuration_digest", "container_id", "expiry_sequence",
        "incident_digest", "issued_sequence", "request_digest", "request_id", "schema_version",
    }
    if not isinstance(request, Mapping) or set(request) != expected:
        raise OperatorControlError("request fields mismatch")
    _validate_request_fields(request)
    digest = request.get("request_digest")
    if not isinstance(digest, str) or digest != _digest(request, "request_digest"):
        raise OperatorControlError("request digest mismatch")
    return json.loads(_canonical_bytes(request).decode("utf-8"))


@dataclass(frozen=True)
class GatewayState:
    enabled: bool = False
    sequence: int = 0


def transition_gateway(state: GatewayState, *, enable: bool, sequence: int) -> tuple[GatewayState, dict[str, Any]]:
    sequence = _strict_positive_int(sequence, "gateway sequence")
    if sequence <= state.sequence:
        raise OperatorControlError("gateway sequence must increase")
    if enable == state.enabled:
        raise OperatorControlError("gateway state unchanged")
    record: dict[str, Any] = {
        "enabled": enable,
        "native_execution_authorized": False,
        "previous_enabled": state.enabled,
        "schema_version": SCHEMA_VERSION,
        "sequence": sequence,
    }
    record["gateway_state_digest"] = _digest(record, "gateway_state_digest")
    return GatewayState(enabled=enable, sequence=sequence), record


def create_operator_decision(
    request: Mapping[str, Any],
    *,
    gateway_state: GatewayState,
    decision: str,
    reason_code: str,
    decision_sequence: int,
) -> dict[str, Any]:
    validated = validate_projected_request(request)
    if decision not in ALLOWED_DECISIONS:
        raise OperatorControlError("unsupported operator decision")
    if reason_code not in ALLOWED_REASONS:
        raise OperatorControlError("unsupported reason code")
    sequence = _strict_positive_int(decision_sequence, "decision sequence")
    if sequence < validated["issued_sequence"] or sequence > validated["expiry_sequence"]:
        raise OperatorControlError("decision outside request validity window")
    if decision == "APPROVE" and not gateway_state.enabled:
        raise OperatorControlError("gateway disabled")
    record: dict[str, Any] = {
        "decision": decision,
        "decision_sequence": sequence,
        "gateway_enabled": gateway_state.enabled,
        "native_execution_authorized": False,
        "reason_code": reason_code,
        "request_digest": validated["request_digest"],
        "request_id": validated["request_id"],
        "schema_version": SCHEMA_VERSION,
    }
    record["decision_digest"] = _digest(record, "decision_digest")
    return record


def register_decision(
    registry: Mapping[str, Mapping[str, Any]],
    request: Mapping[str, Any],
    decision_record: Mapping[str, Any],
) -> dict[str, dict[str, Any]]:
    validated_request = validate_projected_request(request)
    request_id = validated_request["request_id"]
    if decision_record.get("request_id") != request_id or decision_record.get("request_digest") != validated_request["request_digest"]:
        raise OperatorControlError("decision request binding mismatch")
    existing = registry.get(request_id)
    if existing is not None:
        if existing.get("request_digest") != validated_request["request_digest"]:
            raise OperatorControlError("request ID reused with different digest")
        if existing.get("decision") == decision_record.get("decision"):
            raise OperatorControlError("duplicate operator decision")
        raise OperatorControlError("conflicting operator decision")
    updated = {key: dict(value) for key, value in registry.items()}
    updated[request_id] = dict(decision_record)
    return updated


def canonical_record_bytes(record: Mapping[str, Any]) -> bytes:
    return _canonical_bytes(record)
