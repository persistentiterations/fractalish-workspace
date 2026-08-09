"""Deterministic Stage 6 incident review, replay, and in-memory export."""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from typing import Any, Mapping, Sequence

from .receipts import canonical_json_bytes

INCIDENT_ID = re.compile(r"^inc-[0-9a-f]{64}$")
CONTAINER_ID = re.compile(r"^[0-9a-f]{64}$")
CONFIGURATION_DIGEST = re.compile(r"^sha256:[0-9a-f]{64}$")
REASON_CODE = re.compile(r"^[A-Z][A-Z0-9_]{0,63}$")
HEX64 = re.compile(r"^[0-9a-f]{64}$")
DECISIONS = {"NO_ACTION", "HOLD", "RELEASE"}
ACTION_STATUSES = {
    "NOT_PROJECTED", "PROJECTED", "APPROVED", "DENIED",
    "GATEWAY_REJECTED", "DOCKER_ACCEPTED", "DOCKER_REJECTED",
}
ZERO_DIGEST = "0" * 64


class IncidentError(ValueError):
    """Stable fail-closed Stage 6 error."""


@dataclass(frozen=True)
class ReplayResult:
    decision: str
    action_status: str
    terminal_receipt_digest: str
    receipt_count: int
    chain_valid: bool

    def body(self) -> dict[str, object]:
        return {
            "action_status": self.action_status,
            "chain_valid": self.chain_valid,
            "decision": self.decision,
            "receipt_count": self.receipt_count,
            "terminal_receipt_digest": self.terminal_receipt_digest,
        }


def _validate_receipt(value: object, expected_sequence: int, previous_digest: str) -> dict[str, object]:
    if not isinstance(value, dict) or set(value) != {"sequence", "event_type", "payload", "previous_digest", "receipt_digest"}:
        raise IncidentError("MALFORMED_RECEIPT")
    sequence = value["sequence"]
    event_type = value["event_type"]
    payload = value["payload"]
    prior = value["previous_digest"]
    digest = value["receipt_digest"]
    if type(sequence) is not int or sequence != expected_sequence or sequence < 0:
        raise IncidentError("INVALID_RECEIPT_SEQUENCE")
    if not isinstance(event_type, str) or not REASON_CODE.fullmatch(event_type):
        raise IncidentError("INVALID_EVENT_TYPE")
    if not isinstance(payload, dict):
        raise IncidentError("INVALID_RECEIPT_PAYLOAD")
    if not isinstance(prior, str) or prior != previous_digest:
        raise IncidentError("RECEIPT_CHAIN_MISMATCH")
    if not isinstance(digest, str) or not HEX64.fullmatch(digest):
        raise IncidentError("INVALID_RECEIPT_DIGEST")
    base = {"event_type": event_type, "payload": payload, "previous_digest": prior, "sequence": sequence}
    expected = hashlib.sha256(canonical_json_bytes(base)).hexdigest()
    if digest != expected:
        raise IncidentError("RECEIPT_DIGEST_MISMATCH")
    return dict(value)


def validate_incident(value: object) -> dict[str, object]:
    required = {
        "incident_id", "container_id", "configuration_digest", "opened_sequence",
        "updated_sequence", "decision", "reason_code", "action_status", "receipts",
    }
    if not isinstance(value, dict) or set(value) != required:
        raise IncidentError("INCIDENT_FIELDS_MISMATCH")
    if not isinstance(value["incident_id"], str) or not INCIDENT_ID.fullmatch(value["incident_id"]):
        raise IncidentError("INVALID_INCIDENT_ID")
    if not isinstance(value["container_id"], str) or not CONTAINER_ID.fullmatch(value["container_id"]):
        raise IncidentError("INVALID_CONTAINER_ID")
    if not isinstance(value["configuration_digest"], str) or not CONFIGURATION_DIGEST.fullmatch(value["configuration_digest"]):
        raise IncidentError("INVALID_CONFIGURATION_DIGEST")
    opened = value["opened_sequence"]
    updated = value["updated_sequence"]
    if type(opened) is not int or type(updated) is not int or opened < 0 or updated < opened:
        raise IncidentError("INVALID_SEQUENCE_RANGE")
    if value["decision"] not in DECISIONS:
        raise IncidentError("INVALID_DECISION")
    if not isinstance(value["reason_code"], str) or not REASON_CODE.fullmatch(value["reason_code"]):
        raise IncidentError("INVALID_REASON_CODE")
    if value["action_status"] not in ACTION_STATUSES:
        raise IncidentError("INVALID_ACTION_STATUS")
    receipts = value["receipts"]
    if not isinstance(receipts, list) or not receipts:
        raise IncidentError("EMPTY_RECEIPTS")
    previous = ZERO_DIGEST
    normalized = []
    for index, receipt in enumerate(receipts):
        checked = _validate_receipt(receipt, opened + index, previous)
        normalized.append(checked)
        previous = checked["receipt_digest"]  # type: ignore[assignment]
    if normalized[-1]["sequence"] != updated:
        raise IncidentError("UPDATED_SEQUENCE_MISMATCH")
    result = dict(value)
    result["receipts"] = normalized
    return result


def incident_summary(value: object) -> dict[str, object]:
    incident = validate_incident(value)
    return {
        "action_status": incident["action_status"],
        "decision": incident["decision"],
        "incident_id": incident["incident_id"],
        "reason_code": incident["reason_code"],
        "updated_sequence": incident["updated_sequence"],
    }


def list_incidents(values: Sequence[object], limit: int) -> tuple[dict[str, object], ...]:
    if type(limit) is not int or not 1 <= limit <= 1000:
        raise IncidentError("INVALID_LIST_LIMIT")
    summaries = [incident_summary(value) for value in values]
    summaries.sort(key=lambda item: (-int(item["updated_sequence"]), str(item["incident_id"])))
    return tuple(summaries[:limit])


def replay_incident(value: object) -> ReplayResult:
    incident = validate_incident(value)
    receipts = incident["receipts"]
    terminal = receipts[-1]["receipt_digest"]  # type: ignore[index]
    return ReplayResult(
        decision=str(incident["decision"]),
        action_status=str(incident["action_status"]),
        terminal_receipt_digest=str(terminal),
        receipt_count=len(receipts),  # type: ignore[arg-type]
        chain_valid=True,
    )


def explain_incident(value: object) -> dict[str, object]:
    incident = validate_incident(value)
    replay = replay_incident(incident)
    return {
        "action": {
            "native_execution_evidenced": incident["action_status"] == "DOCKER_ACCEPTED",
            "status": incident["action_status"],
        },
        "decision": {"reason_code": incident["reason_code"], "value": incident["decision"]},
        "observation": {
            "container_id": incident["container_id"],
            "opened_sequence": incident["opened_sequence"],
            "updated_sequence": incident["updated_sequence"],
        },
        "receipt_chain": {"terminal_digest": replay.terminal_receipt_digest, "valid": replay.chain_valid},
        "schema_version": 1,
    }


def export_incident(value: object) -> bytes:
    incident = validate_incident(value)
    members: dict[str, bytes] = {
        "incident.json": canonical_json_bytes(incident),
        "replay.json": canonical_json_bytes(replay_incident(incident).body()),
        "summary.json": canonical_json_bytes(incident_summary(incident)),
    }
    manifest = [
        {"bytes": len(data), "name": name, "sha256": hashlib.sha256(data).hexdigest()}
        for name, data in sorted(members.items())
    ]
    package_base = {
        "manifest": manifest,
        "members": {name: data.decode("utf-8") for name, data in sorted(members.items())},
        "schema_version": 1,
    }
    digest = hashlib.sha256(canonical_json_bytes(package_base)).hexdigest()
    package = dict(package_base)
    package["package_digest"] = digest
    return canonical_json_bytes(package) + b"\n"
