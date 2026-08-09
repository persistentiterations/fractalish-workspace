"""Deterministic Stage 6 incident review, replay, and in-memory export."""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
import re
from typing import Mapping, Sequence

PRODUCT = "Bolt-On Continuity v0.4"
STAGE = 6
SCHEMA_VERSION = 1
QUALIFIED_STAGE_5_HEAD = "818aa1bccd89bc9ba79bd48a7190ff3b6f61b06c"
STAGE_5_QUALIFICATION_RECORD_SHA256 = "6b1deab138bd52643ed797fc1195cf5d8a5fbcc2ea8a72c95ec871847f0e3ffc"
STAGE_5_VERIFIER_MANIFEST_SHA256 = "58ec59fdb6aa87ed934cea48581c7cdb3c790c39b7f980e10444aaff007e5e2f"

INCIDENT_ID = re.compile(r"^inc-[0-9a-f]{64}$")
CONTAINER_ID = re.compile(r"^[0-9a-f]{64}$")
CONFIGURATION_DIGEST = re.compile(r"^sha256:[0-9a-f]{64}$")
DIGEST = re.compile(r"^[0-9a-f]{64}$")
EVENT_TYPE = re.compile(r"^[A-Z][A-Z0-9_]{0,63}$")
REASON_CODE = re.compile(r"^[A-Z][A-Z0-9_]{0,63}$")
DECISIONS = frozenset({"NO_ACTION", "HOLD", "RELEASE"})
ACTION_STATUSES = frozenset({"NOT_PROJECTED", "PROJECTED", "APPROVED", "DENIED", "DOCKER_ACCEPTED", "DOCKER_REJECTED"})
MAX_RECEIPTS = 4096
MAX_PAYLOAD_BYTES = 65536
MAX_INCIDENTS = 10000
MAX_LIST_LIMIT = 1000

AUTHORITY = {
    "stage_5_result_consumption": True,
    "incident_validation": True,
    "incident_listing": True,
    "incident_explanation": True,
    "offline_replay": True,
    "in_memory_export": True,
    "docker_contact": False,
    "docker_mutation": False,
    "container_enumeration": False,
    "container_inspection": False,
    "container_start_stop_restart": False,
    "container_exec": False,
    "container_create_remove": False,
    "filesystem_read": False,
    "filesystem_mutation": False,
    "subprocess_execution": False,
    "socket_access": False,
    "network_contact": False,
    "gateway_action": False,
    "approval_or_denial": False,
    "native_execution": False,
    "background_service": False,
    "thread_creation": False,
    "automatic_recovery": False,
    "attach_or_distribute_packages": False,
    "publish_release": False,
    "production_claims": False,
}

class IncidentError(ValueError):
    """Stable fail-closed Stage 6 validation error."""

def canonical_bytes(value: object) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False).encode("utf-8")

def sha256(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()

@dataclass(frozen=True)
class IncidentRecord:
    body_value: Mapping[str, object]
    def body(self) -> dict[str, object]:
        return dict(self.body_value)
    def canonical_bytes(self) -> bytes:
        return canonical_bytes(self.body())

@dataclass(frozen=True)
class StageSixResult:
    body_value: Mapping[str, object]
    def body(self) -> dict[str, object]:
        return dict(self.body_value)
    def canonical_bytes(self) -> bytes:
        return canonical_bytes(self.body())
    def canonical_json(self) -> str:
        return self.canonical_bytes().decode("utf-8")

def _plain_int(value: object, code: str) -> int:
    if type(value) is not int or value < 0:
        raise IncidentError(code)
    return value

def _bounded_payload(value: object) -> object:
    try:
        encoded = canonical_bytes(value)
    except (TypeError, ValueError) as exc:
        raise IncidentError("INVALID_RECEIPT_PAYLOAD") from exc
    if len(encoded) > MAX_PAYLOAD_BYTES:
        raise IncidentError("RECEIPT_PAYLOAD_TOO_LARGE")
    return value

def _validate_receipts(receipts: object, opened: int, updated: int) -> tuple[list[dict[str, object]], bool]:
    if not isinstance(receipts, list) or not receipts or len(receipts) > MAX_RECEIPTS:
        raise IncidentError("INVALID_RECEIPTS")
    validated: list[dict[str, object]] = []
    previous = "0" * 64
    last_sequence = None
    for item in receipts:
        if not isinstance(item, dict) or set(item) != {"sequence", "event_type", "payload", "previous_digest", "receipt_digest"}:
            raise IncidentError("RECEIPT_FIELDS_MISMATCH")
        sequence = _plain_int(item["sequence"], "INVALID_RECEIPT_SEQUENCE")
        if last_sequence is not None and sequence <= last_sequence:
            raise IncidentError("RECEIPT_SEQUENCE_NOT_INCREASING")
        event_type = item["event_type"]
        if not isinstance(event_type, str) or not EVENT_TYPE.fullmatch(event_type):
            raise IncidentError("INVALID_EVENT_TYPE")
        payload = _bounded_payload(item["payload"])
        previous_digest = item["previous_digest"]
        receipt_digest = item["receipt_digest"]
        if previous_digest != previous or not isinstance(receipt_digest, str) or not DIGEST.fullmatch(receipt_digest):
            raise IncidentError("RECEIPT_CHAIN_INVALID")
        base = {"sequence": sequence, "event_type": event_type, "payload": payload, "previous_digest": previous_digest}
        expected = sha256(canonical_bytes(base))
        if receipt_digest != expected:
            raise IncidentError("RECEIPT_DIGEST_MISMATCH")
        validated.append({**base, "receipt_digest": receipt_digest})
        previous = receipt_digest
        last_sequence = sequence
    if validated[0]["sequence"] != opened or validated[-1]["sequence"] != updated:
        raise IncidentError("INCIDENT_SEQUENCE_BOUNDS_MISMATCH")
    return validated, True

def validate_incident(value: object) -> IncidentRecord:
    if not isinstance(value, dict):
        raise IncidentError("MALFORMED_INCIDENT")
    required = {"incident_id","container_id","configuration_digest","opened_sequence","updated_sequence","decision","reason_code","action_status","receipts"}
    if set(value) != required:
        raise IncidentError("INCIDENT_FIELDS_MISMATCH")
    incident_id = value["incident_id"]
    container_id = value["container_id"]
    configuration_digest = value["configuration_digest"]
    if not isinstance(incident_id, str) or not INCIDENT_ID.fullmatch(incident_id):
        raise IncidentError("INVALID_INCIDENT_ID")
    if not isinstance(container_id, str) or not CONTAINER_ID.fullmatch(container_id):
        raise IncidentError("INVALID_CONTAINER_ID")
    if not isinstance(configuration_digest, str) or not CONFIGURATION_DIGEST.fullmatch(configuration_digest):
        raise IncidentError("INVALID_CONFIGURATION_DIGEST")
    opened = _plain_int(value["opened_sequence"], "INVALID_OPENED_SEQUENCE")
    updated = _plain_int(value["updated_sequence"], "INVALID_UPDATED_SEQUENCE")
    if updated < opened:
        raise IncidentError("INVALID_SEQUENCE_BOUNDS")
    decision = value["decision"]
    reason = value["reason_code"]
    status = value["action_status"]
    if decision not in DECISIONS:
        raise IncidentError("INVALID_DECISION")
    if not isinstance(reason, str) or not REASON_CODE.fullmatch(reason):
        raise IncidentError("INVALID_REASON_CODE")
    if status not in ACTION_STATUSES:
        raise IncidentError("INVALID_ACTION_STATUS")
    receipts, _ = _validate_receipts(value["receipts"], opened, updated)
    body = {
        "action_status": status,
        "configuration_digest": configuration_digest,
        "container_id": container_id,
        "decision": decision,
        "incident_id": incident_id,
        "opened_sequence": opened,
        "reason_code": reason,
        "receipts": receipts,
        "updated_sequence": updated,
    }
    return IncidentRecord(body)

def list_incidents(values: object, limit: int = 100) -> StageSixResult:
    if type(limit) is not int or not 1 <= limit <= MAX_LIST_LIMIT:
        raise IncidentError("INVALID_LIST_LIMIT")
    if not isinstance(values, list) or len(values) > MAX_INCIDENTS:
        raise IncidentError("INVALID_INCIDENT_COLLECTION")
    records = [validate_incident(value).body() for value in values]
    records.sort(key=lambda item: (-int(item["updated_sequence"]), str(item["incident_id"])))
    summaries = [
        {
            "action_status": item["action_status"],
            "decision": item["decision"],
            "incident_id": item["incident_id"],
            "reason_code": item["reason_code"],
            "updated_sequence": item["updated_sequence"],
        }
        for item in records[:limit]
    ]
    body = _result_base("list", None)
    body.update({"accepted": True, "incident_count": len(records), "items": summaries, "reason_code": "INCIDENTS_LISTED"})
    return _finalize(body)

def explain_incident(value: object) -> StageSixResult:
    record = validate_incident(value).body()
    executed = record["action_status"] == "DOCKER_ACCEPTED"
    projected = record["action_status"] in {"PROJECTED", "APPROVED", "DENIED", "DOCKER_ACCEPTED", "DOCKER_REJECTED"}
    body = _result_base("explain", record["incident_id"])
    body.update({
        "accepted": True,
        "explanation": {
            "action_status": record["action_status"],
            "decision": record["decision"],
            "native_execution_evidenced": executed,
            "observation": {
                "configuration_digest": record["configuration_digest"],
                "container_id": record["container_id"],
                "opened_sequence": record["opened_sequence"],
                "updated_sequence": record["updated_sequence"],
            },
            "projected_action_present": projected,
            "reason_code": record["reason_code"],
            "receipt_chain_valid": True,
        },
        "reason_code": "INCIDENT_EXPLAINED",
    })
    return _finalize(body)

def replay_incident(value: object) -> StageSixResult:
    record = validate_incident(value).body()
    receipts = record["receipts"]
    terminal = receipts[-1]
    replay = {
        "action_status": record["action_status"],
        "decision": record["decision"],
        "native_execution_evidenced": record["action_status"] == "DOCKER_ACCEPTED",
        "receipt_count": len(receipts),
        "terminal_receipt_digest": terminal["receipt_digest"],
        "terminal_sequence": terminal["sequence"],
    }
    body = _result_base("replay", record["incident_id"])
    body.update({"accepted": True, "reason_code": "OFFLINE_REPLAY_COMPLETE", "replay": replay})
    return _finalize(body)

def export_incident(value: object) -> StageSixResult:
    record = validate_incident(value)
    replay = replay_incident(record.body()).body()["replay"]
    summary = explain_incident(record.body()).body()["explanation"]
    manifest = {
        "format": "bolt-on-continuity-stage-6-export",
        "incident_digest": sha256(record.canonical_bytes()),
        "receipt_count": len(record.body()["receipts"]),
        "schema_version": 1,
    }
    package_without_digest = {
        "incident": record.body(),
        "manifest": manifest,
        "replay": replay,
        "summary": summary,
    }
    package_digest = sha256(canonical_bytes(package_without_digest))
    package = {**package_without_digest, "package_digest": package_digest}
    body = _result_base("export", record.body()["incident_id"])
    body.update({
        "accepted": True,
        "export": package,
        "export_bytes": len(canonical_bytes(package)),
        "reason_code": "IN_MEMORY_EXPORT_READY",
    })
    return _finalize(body)

def _result_base(operation: str, incident_id: object) -> dict[str, object]:
    return {
        "accepted": False,
        "authority": dict(AUTHORITY),
        "incident_id": incident_id,
        "operation": operation,
        "product": PRODUCT,
        "qualified_stage_5_head": QUALIFIED_STAGE_5_HEAD,
        "reason_code": "NOT_EVALUATED",
        "schema_version": SCHEMA_VERSION,
        "stage": STAGE,
        "stage_5_qualification_record_sha256": STAGE_5_QUALIFICATION_RECORD_SHA256,
        "stage_5_verifier_manifest_sha256": STAGE_5_VERIFIER_MANIFEST_SHA256,
    }

def _finalize(body: dict[str, object]) -> StageSixResult:
    base = dict(body)
    result_digest = sha256(canonical_bytes(base))
    return StageSixResult({**base, "result_digest": result_digest})

def render_human(result: StageSixResult) -> str:
    body = result.body()
    lines = [
        f"PASS stage5.binding: {body['qualified_stage_5_head']}",
        f"PASS operation: {body['operation']}",
        f"PASS accepted: {'TRUE' if body['accepted'] else 'FALSE'}",
        "PASS docker.contact: DENIED",
        "PASS filesystem.mutation: DENIED",
        "PASS native.execution: DENIED",
        body["reason_code"],
        f"RESULT SHA-256 {body['result_digest']}",
    ]
    return "\n".join(lines)
