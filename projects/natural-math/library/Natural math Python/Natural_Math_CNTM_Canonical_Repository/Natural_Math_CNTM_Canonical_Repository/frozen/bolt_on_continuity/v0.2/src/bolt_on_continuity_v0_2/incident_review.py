from __future__ import annotations

import hashlib
import json
import re
from typing import Any, Mapping, Sequence

INCIDENT_ID_RE = re.compile(r"^inc-[0-9a-f]{64}$")
CONTAINER_ID_RE = re.compile(r"^[0-9a-f]{64}$")
DIGEST_RE = re.compile(r"^sha256:[0-9a-f]{64}$")
REASON_RE = re.compile(r"^[A-Z][A-Z0-9_]{0,63}$")
DECISIONS = {"NO_ACTION", "HOLD", "RELEASE"}
ACTION_STATUSES = {
    "NOT_PROJECTED", "PROJECTED", "APPROVED", "DENIED",
    "GATEWAY_REJECTED", "DOCKER_ACCEPTED", "DOCKER_REJECTED",
}
INCIDENT_FIELDS = {
    "incident_id", "container_id", "configuration_digest", "opened_sequence",
    "updated_sequence", "decision", "reason_code", "action_status", "receipts",
}
RECEIPT_FIELDS = {"sequence", "event_type", "payload", "previous_digest", "receipt_digest"}


class IncidentReviewError(ValueError):
    pass


def _canonical_bytes(value: Any) -> bytes:
    return (json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False) + "\n").encode("utf-8")


def _sha256(data: bytes) -> str:
    return "sha256:" + hashlib.sha256(data).hexdigest()


def _receipt_payload(receipt: Mapping[str, Any]) -> dict[str, Any]:
    return {key: receipt[key] for key in sorted(RECEIPT_FIELDS - {"receipt_digest"})}


def validate_receipt(receipt: Mapping[str, Any]) -> dict[str, Any]:
    if not isinstance(receipt, Mapping) or set(receipt) != RECEIPT_FIELDS:
        raise IncidentReviewError("receipt fields mismatch")
    if type(receipt["sequence"]) is not int or receipt["sequence"] < 0:
        raise IncidentReviewError("invalid receipt sequence")
    if not isinstance(receipt["event_type"], str) or REASON_RE.fullmatch(receipt["event_type"]) is None:
        raise IncidentReviewError("invalid receipt event type")
    if not isinstance(receipt["payload"], Mapping):
        raise IncidentReviewError("invalid receipt payload")
    previous = receipt["previous_digest"]
    if previous is not None and (not isinstance(previous, str) or DIGEST_RE.fullmatch(previous) is None):
        raise IncidentReviewError("invalid previous digest")
    digest = receipt["receipt_digest"]
    if not isinstance(digest, str) or DIGEST_RE.fullmatch(digest) is None:
        raise IncidentReviewError("invalid receipt digest")
    expected = _sha256(_canonical_bytes(_receipt_payload(receipt)))
    if digest != expected:
        raise IncidentReviewError("receipt digest mismatch")
    return json.loads(_canonical_bytes(receipt).decode("utf-8"))


def validate_incident(incident: Mapping[str, Any]) -> dict[str, Any]:
    if not isinstance(incident, Mapping) or set(incident) != INCIDENT_FIELDS:
        raise IncidentReviewError("incident fields mismatch")
    if not isinstance(incident["incident_id"], str) or INCIDENT_ID_RE.fullmatch(incident["incident_id"]) is None:
        raise IncidentReviewError("invalid incident ID")
    if not isinstance(incident["container_id"], str) or CONTAINER_ID_RE.fullmatch(incident["container_id"]) is None:
        raise IncidentReviewError("invalid container ID")
    if not isinstance(incident["configuration_digest"], str) or DIGEST_RE.fullmatch(incident["configuration_digest"]) is None:
        raise IncidentReviewError("invalid configuration digest")
    opened = incident["opened_sequence"]
    updated = incident["updated_sequence"]
    if type(opened) is not int or type(updated) is not int or opened < 0 or updated < opened:
        raise IncidentReviewError("invalid incident sequence range")
    if incident["decision"] not in DECISIONS:
        raise IncidentReviewError("invalid decision")
    if not isinstance(incident["reason_code"], str) or REASON_RE.fullmatch(incident["reason_code"]) is None:
        raise IncidentReviewError("invalid reason code")
    if incident["action_status"] not in ACTION_STATUSES:
        raise IncidentReviewError("invalid action status")
    receipts = incident["receipts"]
    if not isinstance(receipts, Sequence) or isinstance(receipts, (str, bytes)) or not receipts:
        raise IncidentReviewError("receipts must be a nonempty list")
    normalized_receipts = [validate_receipt(item) for item in receipts]
    normalized = dict(incident)
    normalized["receipts"] = normalized_receipts
    return json.loads(_canonical_bytes(normalized).decode("utf-8"))


def replay_incident(incident: Mapping[str, Any]) -> dict[str, Any]:
    normalized = validate_incident(incident)
    previous: str | None = None
    expected_sequence = normalized["opened_sequence"]
    for receipt in normalized["receipts"]:
        if receipt["sequence"] != expected_sequence:
            raise IncidentReviewError("receipt sequence mismatch")
        if receipt["previous_digest"] != previous:
            raise IncidentReviewError("receipt chain mismatch")
        previous = receipt["receipt_digest"]
        expected_sequence += 1
    if normalized["receipts"][-1]["sequence"] != normalized["updated_sequence"]:
        raise IncidentReviewError("terminal sequence mismatch")
    return {
        "action_status": normalized["action_status"],
        "chain_valid": True,
        "decision": normalized["decision"],
        "incident_id": normalized["incident_id"],
        "receipt_count": len(normalized["receipts"]),
        "terminal_receipt_digest": previous,
    }


def list_incidents(incidents: Sequence[Mapping[str, Any]], *, limit: int = 100) -> list[dict[str, Any]]:
    if type(limit) is not int or limit <= 0 or limit > 1000:
        raise IncidentReviewError("invalid incident limit")
    normalized = [validate_incident(item) for item in incidents]
    normalized.sort(key=lambda item: (-item["updated_sequence"], item["incident_id"]))
    return [
        {
            "action_status": item["action_status"],
            "decision": item["decision"],
            "incident_id": item["incident_id"],
            "reason_code": item["reason_code"],
            "updated_sequence": item["updated_sequence"],
        }
        for item in normalized[:limit]
    ]


def explain_incident(incident: Mapping[str, Any]) -> dict[str, Any]:
    normalized = validate_incident(incident)
    replay = replay_incident(normalized)
    return {
        "action_status": normalized["action_status"],
        "chain_valid": replay["chain_valid"],
        "container_id": normalized["container_id"],
        "decision": normalized["decision"],
        "incident_id": normalized["incident_id"],
        "native_execution_evidenced": normalized["action_status"] == "DOCKER_ACCEPTED",
        "opened_sequence": normalized["opened_sequence"],
        "projected_is_execution": False,
        "reason_code": normalized["reason_code"],
        "updated_sequence": normalized["updated_sequence"],
    }


def create_export_package(incident: Mapping[str, Any]) -> dict[str, Any]:
    normalized = validate_incident(incident)
    replay = replay_incident(normalized)
    summary = explain_incident(normalized)
    members = {
        "incident.json": _canonical_bytes(normalized),
        "replay.json": _canonical_bytes(replay),
        "summary.json": _canonical_bytes(summary),
    }
    manifest = {
        "members": [
            {"byte_count": len(data), "name": name, "sha256": _sha256(data)}
            for name, data in sorted(members.items())
        ],
        "schema_version": "1",
    }
    manifest_bytes = _canonical_bytes(manifest)
    package_digest = _sha256(manifest_bytes)
    return {
        "manifest": manifest,
        "manifest_bytes": manifest_bytes,
        "members": members,
        "package_digest": package_digest,
    }


def verify_export_package(package: Mapping[str, Any]) -> bool:
    if not isinstance(package, Mapping) or set(package) != {"manifest", "manifest_bytes", "members", "package_digest"}:
        return False
    try:
        if package["manifest_bytes"] != _canonical_bytes(package["manifest"]):
            return False
        if package["package_digest"] != _sha256(package["manifest_bytes"]):
            return False
        members = package["members"]
        if not isinstance(members, Mapping):
            return False
        expected = {
            item["name"]: (item["byte_count"], item["sha256"])
            for item in package["manifest"]["members"]
        }
        if set(members) != set(expected):
            return False
        for name, data in members.items():
            byte_count, digest = expected[name]
            if not isinstance(data, bytes) or len(data) != byte_count or _sha256(data) != digest:
                return False
        return True
    except (KeyError, TypeError, ValueError):
        return False
