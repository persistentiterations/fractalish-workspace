from __future__ import annotations
import hashlib
import json
from typing import Any

SCHEMA_VERSION = "1"
CONTRACT_VERSION = "BONACQUI_BOLT_ON_CONTINUITY_DOCKER_PRODUCT_CONTRACT_0_1_STAGE_0"
ACTIONS = {"HOLD", "RELEASE", "NO_ACTION"}
REASONS = {
    "UNHEALTHY_RUNNING",
    "HEALTHY_PAUSED_APPROVED",
    "NO_MATCH",
    "INCIDENT_CLOSED",
    "STALE_INCIDENT",
    "EXPIRED_POLICY",
    "TAMPERED_INCIDENT",
    "SUBJECT_MISMATCH",
    "CONFIGURATION_MISMATCH",
    "UNSUPPORTED_STATE",
    "AMBIGUOUS_EVIDENCE",
}

class ProjectionRejected(ValueError):
    def __init__(self, reason_code: str, message: str):
        super().__init__(message)
        self.reason_code = reason_code

def _reject_floats(value: Any) -> None:
    if isinstance(value, float):
        raise TypeError("floating-point values are not canonical")
    if isinstance(value, dict):
        for item in value.values():
            _reject_floats(item)
    elif isinstance(value, (list, tuple)):
        for item in value:
            _reject_floats(item)

def canonical_json(value: Any) -> bytes:
    _reject_floats(value)
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")

def digest(value: Any) -> str:
    return "sha256:" + hashlib.sha256(canonical_json(value)).hexdigest()

def valid_digest(value: str) -> bool:
    return (
        isinstance(value, str)
        and len(value) == 71
        and value.startswith("sha256:")
        and all(ch in "0123456789abcdef" for ch in value[7:])
    )

class BoundedActionProjector:
    def __init__(self, container_id: str, configuration_digest: str, policy: dict[str, Any]):
        if not isinstance(container_id, str) or not 12 <= len(container_id) <= 128:
            raise ValueError("container_id invalid")
        if any(ch not in "0123456789abcdefABCDEF" for ch in container_id):
            raise ValueError("container_id must be hexadecimal")
        if not valid_digest(configuration_digest):
            raise ValueError("configuration_digest invalid")
        if not isinstance(policy, dict):
            raise ValueError("policy must be object")
        required = {
            "policy_version",
            "max_incident_age_seconds",
            "request_ttl_seconds",
            "release_requires_approval",
        }
        if set(policy) != required:
            raise ValueError("policy fields differ")
        if policy["policy_version"] != "1":
            raise ValueError("unsupported policy version")
        for field in ("max_incident_age_seconds", "request_ttl_seconds"):
            if type(policy[field]) is not int or policy[field] <= 0:
                raise ValueError(f"{field} must be positive integer")
        if type(policy["release_requires_approval"]) is not bool:
            raise ValueError("release_requires_approval must be boolean")
        self.container_id = container_id.lower()
        self.configuration_digest = configuration_digest
        self.policy = json.loads(json.dumps(policy))
        self.policy_digest = digest(self.policy)

    def project(
        self,
        *,
        incident_export: dict[str, Any],
        observed_state: str,
        health_state: str,
        recovery_approved: bool,
        projection_sequence: int,
        issued_at_epoch: int,
        latest_evidence_epoch: int,
    ) -> dict[str, Any]:
        if type(recovery_approved) is not bool:
            raise ProjectionRejected("AMBIGUOUS_EVIDENCE", "recovery approval must be boolean")
        for name, value in {
            "projection_sequence": projection_sequence,
            "issued_at_epoch": issued_at_epoch,
            "latest_evidence_epoch": latest_evidence_epoch,
        }.items():
            if type(value) is not int or value < 0:
                raise ProjectionRejected("AMBIGUOUS_EVIDENCE", f"{name} invalid")

        incident_digest = self._validate_incident(incident_export)
        if issued_at_epoch - latest_evidence_epoch > self.policy["max_incident_age_seconds"]:
            return self._record(
                incident_export, incident_digest, "NO_ACTION", "STALE_INCIDENT",
                observed_state, projection_sequence, issued_at_epoch
            )
        if latest_evidence_epoch > issued_at_epoch:
            return self._record(
                incident_export, incident_digest, "NO_ACTION", "AMBIGUOUS_EVIDENCE",
                observed_state, projection_sequence, issued_at_epoch
            )
        if incident_export["closed"]:
            return self._record(
                incident_export, incident_digest, "NO_ACTION", "INCIDENT_CLOSED",
                observed_state, projection_sequence, issued_at_epoch
            )

        if observed_state not in {"RUNNING", "PAUSED", "EXITED", "RESTARTING", "UNAVAILABLE", "UNKNOWN"}:
            return self._record(
                incident_export, incident_digest, "NO_ACTION", "UNSUPPORTED_STATE",
                observed_state, projection_sequence, issued_at_epoch
            )
        if health_state not in {"HEALTHY", "UNHEALTHY", "STARTING", "NOT_CONFIGURED", "UNKNOWN"}:
            return self._record(
                incident_export, incident_digest, "NO_ACTION", "AMBIGUOUS_EVIDENCE",
                observed_state, projection_sequence, issued_at_epoch
            )

        if observed_state == "RUNNING" and health_state == "UNHEALTHY":
            return self._record(
                incident_export, incident_digest, "HOLD", "UNHEALTHY_RUNNING",
                "RUNNING", projection_sequence, issued_at_epoch
            )

        release_allowed = (
            observed_state == "PAUSED"
            and health_state == "HEALTHY"
            and (
                recovery_approved
                or self.policy["release_requires_approval"] is False
            )
        )
        if release_allowed:
            return self._record(
                incident_export, incident_digest, "RELEASE", "HEALTHY_PAUSED_APPROVED",
                "PAUSED", projection_sequence, issued_at_epoch
            )

        return self._record(
            incident_export, incident_digest, "NO_ACTION", "NO_MATCH",
            observed_state, projection_sequence, issued_at_epoch
        )

    def _validate_incident(self, incident_export: dict[str, Any]) -> str:
        if not isinstance(incident_export, dict):
            raise ProjectionRejected("TAMPERED_INCIDENT", "incident export must be object")
        required = {
            "schema_version","incident_id","container_id","configuration_digest",
            "entry_count","closed","entries","terminal_entry_digest","export_digest"
        }
        if set(incident_export) != required:
            raise ProjectionRejected("TAMPERED_INCIDENT", "incident fields differ")
        body = dict(incident_export)
        claimed = body.pop("export_digest")
        if digest(body) != claimed:
            raise ProjectionRejected("TAMPERED_INCIDENT", "incident digest differs")
        if incident_export["container_id"] != self.container_id:
            raise ProjectionRejected("SUBJECT_MISMATCH", "incident subject differs")
        if incident_export["configuration_digest"] != self.configuration_digest:
            raise ProjectionRejected("CONFIGURATION_MISMATCH", "incident configuration differs")
        if not valid_digest(claimed):
            raise ProjectionRejected("TAMPERED_INCIDENT", "incident digest invalid")
        return claimed

    def _record(
        self,
        incident_export: dict[str, Any],
        incident_digest: str,
        action: str,
        reason_code: str,
        expected_state: str,
        projection_sequence: int,
        issued_at_epoch: int,
    ) -> dict[str, Any]:
        if action not in ACTIONS or reason_code not in REASONS:
            raise RuntimeError("internal projection result invalid")
        expires_at_epoch = issued_at_epoch + self.policy["request_ttl_seconds"]
        body = {
            "schema_version": SCHEMA_VERSION,
            "contract_version": CONTRACT_VERSION,
            "incident_id": incident_export["incident_id"],
            "container_id": self.container_id,
            "configuration_digest": self.configuration_digest,
            "incident_export_digest": incident_digest,
            "policy_digest": self.policy_digest,
            "projected_action": action,
            "expected_state": expected_state,
            "reason_code": reason_code,
            "projection_sequence": projection_sequence,
            "issued_at_epoch": issued_at_epoch,
            "expires_at_epoch": expires_at_epoch,
        }
        return {**body, "projection_digest": digest(body)}

    @staticmethod
    def verify_projection(record: dict[str, Any]) -> dict[str, Any]:
        if not isinstance(record, dict):
            raise ProjectionRejected("AMBIGUOUS_EVIDENCE", "projection must be object")
        required = {
            "schema_version","contract_version","incident_id","container_id",
            "configuration_digest","incident_export_digest","policy_digest",
            "projected_action","expected_state","reason_code","projection_sequence",
            "issued_at_epoch","expires_at_epoch","projection_digest"
        }
        if set(record) != required:
            raise ProjectionRejected("AMBIGUOUS_EVIDENCE", "projection fields differ")
        body = dict(record)
        claimed = body.pop("projection_digest")
        if digest(body) != claimed:
            raise ProjectionRejected("AMBIGUOUS_EVIDENCE", "projection digest differs")
        if record["projected_action"] not in ACTIONS:
            raise ProjectionRejected("AMBIGUOUS_EVIDENCE", "projection action invalid")
        if record["reason_code"] not in REASONS:
            raise ProjectionRejected("AMBIGUOUS_EVIDENCE", "projection reason invalid")
        if record["expires_at_epoch"] <= record["issued_at_epoch"]:
            raise ProjectionRejected("AMBIGUOUS_EVIDENCE", "projection expiry invalid")
        return {
            "verification_pass": True,
            "projection_digest": claimed,
            "projected_action": record["projected_action"],
            "reason_code": record["reason_code"],
        }
