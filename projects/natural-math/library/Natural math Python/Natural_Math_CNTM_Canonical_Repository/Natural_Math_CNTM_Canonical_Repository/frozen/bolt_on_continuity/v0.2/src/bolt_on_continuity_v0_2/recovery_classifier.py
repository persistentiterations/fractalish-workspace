from __future__ import annotations

import hashlib
import json
import re
from typing import Any, Mapping, Sequence

CONTAINER_ID_RE = re.compile(r"^[0-9a-f]{64}$")
STORE_STATES = {
    "STORE_HEALTHY", "STORE_MISSING", "STORE_PERMISSION_DENIED",
    "STORE_PARTIAL_WRITE", "STORE_CORRUPT", "STORE_DISK_FULL", "STORE_AMBIGUOUS",
}
TERMINAL_RESULTS = {"GATEWAY_REJECTED", "DOCKER_ACCEPTED", "DOCKER_REJECTED"}


class RecoveryError(ValueError):
    pass


def _canonical_bytes(value: Mapping[str, Any]) -> bytes:
    return (json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False) + "\n").encode("utf-8")


def _digest(value: Mapping[str, Any]) -> str:
    return "sha256:" + hashlib.sha256(_canonical_bytes(value)).hexdigest()


def _validate_id(value: Any, field: str) -> str:
    if not isinstance(value, str) or CONTAINER_ID_RE.fullmatch(value) is None:
        raise RecoveryError(f"invalid {field}")
    return value


def _classify_subject(enrolled_id: str, enrolled_name: str, current: Sequence[Mapping[str, Any]]) -> str:
    exact: list[Mapping[str, Any]] = []
    same_name_other: list[Mapping[str, Any]] = []
    seen_ids: set[str] = set()
    for item in current:
        if not isinstance(item, Mapping) or set(item) != {"container_id", "display_name", "state"}:
            return "SUBJECT_AMBIGUOUS"
        cid = item.get("container_id")
        name = item.get("display_name")
        state = item.get("state")
        if not isinstance(cid, str) or CONTAINER_ID_RE.fullmatch(cid) is None or cid in seen_ids:
            return "SUBJECT_AMBIGUOUS"
        seen_ids.add(cid)
        if not isinstance(name, str) or not name or state not in {"running", "paused", "created", "exited", "dead"}:
            return "SUBJECT_AMBIGUOUS"
        if cid == enrolled_id:
            exact.append(item)
        elif name == enrolled_name:
            same_name_other.append(item)
    if len(exact) > 1:
        return "SUBJECT_AMBIGUOUS"
    if exact:
        return "SUBJECT_STOPPED" if exact[0]["state"] in {"exited", "dead"} else "SUBJECT_MATCHED"
    if same_name_other:
        return "SUBJECT_REPLACED"
    return "SUBJECT_MISSING"


def classify_recovery(
    *,
    enrolled_container_id: str,
    enrolled_display_name: str,
    current_subjects: Sequence[Mapping[str, Any]],
    store_state: str,
    request_id: str | None = None,
    request_digest: str | None = None,
    prior_records: Sequence[Mapping[str, Any]] = (),
) -> dict[str, Any]:
    enrolled_id = _validate_id(enrolled_container_id, "enrolled container ID")
    if not isinstance(enrolled_display_name, str) or not enrolled_display_name:
        raise RecoveryError("invalid enrolled display name")
    if store_state not in STORE_STATES:
        raise RecoveryError("unsupported store state")
    if (request_id is None) != (request_digest is None):
        raise RecoveryError("request identity incomplete")
    if request_id is not None:
        if not isinstance(request_id, str) or not request_id or not isinstance(request_digest, str) or not request_digest.startswith("sha256:") or len(request_digest) != 71:
            raise RecoveryError("invalid request identity")

    subject_status = _classify_subject(enrolled_id, enrolled_display_name, current_subjects)
    disposition = "FAIL_CLOSED_UNCERTAIN"
    reason = "UNRESOLVED_EVIDENCE"

    if store_state != "STORE_HEALTHY":
        disposition, reason = "FAIL_CLOSED_STORE", store_state
    elif subject_status == "SUBJECT_REPLACED":
        disposition, reason = "REQUIRE_REENROLLMENT", subject_status
    elif subject_status in {"SUBJECT_MISSING", "SUBJECT_STOPPED"}:
        disposition, reason = "REPORT_SUBJECT_UNAVAILABLE", subject_status
    elif subject_status == "SUBJECT_AMBIGUOUS":
        disposition, reason = "FAIL_CLOSED_UNCERTAIN", subject_status
    else:
        matching: list[Mapping[str, Any]] = []
        conflicting = False
        for record in prior_records:
            if not isinstance(record, Mapping):
                conflicting = True
                break
            rid = record.get("request_id")
            digest = record.get("request_digest")
            result = record.get("terminal_result")
            if rid == request_id:
                if digest != request_digest:
                    conflicting = True
                    break
                matching.append(record)
                if result not in TERMINAL_RESULTS:
                    conflicting = True
                    break
        if conflicting:
            disposition, reason = "FAIL_CLOSED_UNCERTAIN", "REQUEST_HISTORY_CONFLICT"
        elif request_id is not None and matching:
            disposition, reason = "SUPPRESS_DUPLICATE", "TERMINAL_REQUEST_ALREADY_RECORDED"
        else:
            disposition, reason = "RESUME_OBSERVATION_ONLY", "SAFE_RESTART_BASELINE"

    report: dict[str, Any] = {
        "disposition": disposition,
        "enrolled_container_id": enrolled_id,
        "gateway_enabled": False,
        "native_execution_authorized": False,
        "observation_only": True,
        "reason": reason,
        "schema_version": "1",
        "store_state": store_state,
        "subject_status": subject_status,
    }
    if request_id is not None:
        report["request_digest"] = request_digest
        report["request_id"] = request_id
    report["report_digest"] = _digest(report)
    return report


def serialize_recovery_report(report: Mapping[str, Any]) -> bytes:
    expected = _digest({k: v for k, v in report.items() if k != "report_digest"})
    if report.get("report_digest") != expected:
        raise RecoveryError("recovery report digest mismatch")
    if report.get("observation_only") is not True or report.get("gateway_enabled") is not False or report.get("native_execution_authorized") is not False:
        raise RecoveryError("unsafe recovery report")
    return _canonical_bytes(report)
