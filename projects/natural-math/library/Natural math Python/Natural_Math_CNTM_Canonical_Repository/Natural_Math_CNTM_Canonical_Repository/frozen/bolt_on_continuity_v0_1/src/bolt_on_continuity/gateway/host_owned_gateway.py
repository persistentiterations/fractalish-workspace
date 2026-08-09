from __future__ import annotations
import hashlib
import json
from typing import Any

SCHEMA_VERSION = "1"
DECISIONS = {"APPROVE", "DENY", "NO_ACTION"}
ACTIONS = {"HOLD", "RELEASE", "NO_ACTION"}
ZERO_DIGEST = "sha256:" + "0" * 64

class GatewayRejected(ValueError):
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

class HostOwnedGateway:
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
            "hold_enabled",
            "release_enabled",
            "max_projection_age_seconds",
        }
        if set(policy) != required:
            raise ValueError("policy fields differ")
        if policy["policy_version"] != "1":
            raise ValueError("unsupported policy version")
        if type(policy["hold_enabled"]) is not bool or type(policy["release_enabled"]) is not bool:
            raise ValueError("action enablement must be boolean")
        if type(policy["max_projection_age_seconds"]) is not int or policy["max_projection_age_seconds"] <= 0:
            raise ValueError("max_projection_age_seconds must be positive integer")

        self.container_id = container_id.lower()
        self.configuration_digest = configuration_digest
        self.policy = json.loads(json.dumps(policy))
        self.policy_digest = digest(self.policy)
        self._last_gateway_sequence = -1
        self._last_projection_sequence = -1
        self._last_decision_digest = ZERO_DIGEST

    @property
    def state(self) -> dict[str, Any]:
        return {
            "last_gateway_sequence": self._last_gateway_sequence,
            "last_projection_sequence": self._last_projection_sequence,
            "last_decision_digest": self._last_decision_digest,
        }

    def decide(self, projection: dict[str, Any], *, gateway_sequence: int, decided_at_epoch: int) -> dict[str, Any]:
        if type(gateway_sequence) is not int or gateway_sequence < 0:
            raise GatewayRejected("MALFORMED_REQUEST", "gateway sequence invalid")
        if type(decided_at_epoch) is not int or decided_at_epoch < 0:
            raise GatewayRejected("MALFORMED_REQUEST", "decision time invalid")

        validation = self._validate_projection(projection)

        if gateway_sequence <= self._last_gateway_sequence:
            decision, reason = "DENY", "GATEWAY_SEQUENCE_REGRESSION"
        elif projection["projection_sequence"] <= self._last_projection_sequence:
            decision, reason = "DENY", "PROJECTION_REPLAY"
        elif decided_at_epoch > projection["expires_at_epoch"]:
            decision, reason = "DENY", "PROJECTION_EXPIRED"
        elif decided_at_epoch < projection["issued_at_epoch"]:
            decision, reason = "DENY", "DECISION_TIME_PRECEDES_PROJECTION"
        elif decided_at_epoch - projection["issued_at_epoch"] > self.policy["max_projection_age_seconds"]:
            decision, reason = "DENY", "PROJECTION_TOO_OLD"
        elif projection["projected_action"] == "NO_ACTION":
            decision, reason = "NO_ACTION", "NO_ACTION_PROJECTED"
        elif projection["projected_action"] == "HOLD":
            if self.policy["hold_enabled"]:
                decision, reason = "APPROVE", "HOLD_ALLOWED"
            else:
                decision, reason = "DENY", "HOLD_DISABLED"
        elif projection["projected_action"] == "RELEASE":
            if self.policy["release_enabled"]:
                decision, reason = "APPROVE", "RELEASE_ALLOWED"
            else:
                decision, reason = "DENY", "RELEASE_DISABLED"
        else:
            decision, reason = "DENY", "UNSUPPORTED_ACTION"

        record = self._record(
            projection=projection,
            gateway_sequence=gateway_sequence,
            decided_at_epoch=decided_at_epoch,
            decision=decision,
            reason_code=reason,
        )

        self._last_gateway_sequence = max(self._last_gateway_sequence, gateway_sequence)
        self._last_projection_sequence = max(self._last_projection_sequence, projection["projection_sequence"])
        self._last_decision_digest = record["gateway_decision_digest"]
        return record

    def _validate_projection(self, projection: dict[str, Any]) -> dict[str, Any]:
        if not isinstance(projection, dict):
            raise GatewayRejected("TAMPERED_PROJECTION", "projection must be object")
        required = {
            "schema_version","contract_version","incident_id","container_id",
            "configuration_digest","incident_export_digest","policy_digest",
            "projected_action","expected_state","reason_code","projection_sequence",
            "issued_at_epoch","expires_at_epoch","projection_digest"
        }
        if set(projection) != required:
            raise GatewayRejected("TAMPERED_PROJECTION", "projection fields differ")
        body = dict(projection)
        claimed = body.pop("projection_digest")
        if digest(body) != claimed:
            raise GatewayRejected("TAMPERED_PROJECTION", "projection digest differs")
        if projection["container_id"] != self.container_id:
            raise GatewayRejected("SUBJECT_MISMATCH", "projection subject differs")
        if projection["configuration_digest"] != self.configuration_digest:
            raise GatewayRejected("CONFIGURATION_MISMATCH", "projection configuration differs")
        if projection["projected_action"] not in ACTIONS:
            raise GatewayRejected("UNSUPPORTED_ACTION", "projection action invalid")
        if not valid_digest(projection["incident_export_digest"]):
            raise GatewayRejected("TAMPERED_PROJECTION", "incident digest invalid")
        if not valid_digest(projection["policy_digest"]):
            raise GatewayRejected("TAMPERED_PROJECTION", "projection policy digest invalid")
        if type(projection["projection_sequence"]) is not int or projection["projection_sequence"] < 0:
            raise GatewayRejected("TAMPERED_PROJECTION", "projection sequence invalid")
        if type(projection["issued_at_epoch"]) is not int or type(projection["expires_at_epoch"]) is not int:
            raise GatewayRejected("TAMPERED_PROJECTION", "projection time invalid")
        if projection["expires_at_epoch"] <= projection["issued_at_epoch"]:
            raise GatewayRejected("TAMPERED_PROJECTION", "projection expiry invalid")
        return {"projection_digest": claimed}

    def _record(
        self,
        *,
        projection: dict[str, Any],
        gateway_sequence: int,
        decided_at_epoch: int,
        decision: str,
        reason_code: str,
    ) -> dict[str, Any]:
        if decision not in DECISIONS:
            raise RuntimeError("internal gateway decision invalid")
        body = {
            "schema_version": SCHEMA_VERSION,
            "incident_id": projection["incident_id"],
            "container_id": self.container_id,
            "configuration_digest": self.configuration_digest,
            "projection_digest": projection["projection_digest"],
            "projection_sequence": projection["projection_sequence"],
            "projected_action": projection["projected_action"],
            "gateway_policy_digest": self.policy_digest,
            "gateway_sequence": gateway_sequence,
            "previous_gateway_decision_digest": self._last_decision_digest,
            "decided_at_epoch": decided_at_epoch,
            "decision": decision,
            "reason_code": reason_code,
        }
        return {**body, "gateway_decision_digest": digest(body)}

    @staticmethod
    def verify_decision(record: dict[str, Any]) -> dict[str, Any]:
        if not isinstance(record, dict):
            raise GatewayRejected("MALFORMED_DECISION", "decision must be object")
        required = {
            "schema_version","incident_id","container_id","configuration_digest",
            "projection_digest","projection_sequence","projected_action",
            "gateway_policy_digest","gateway_sequence",
            "previous_gateway_decision_digest","decided_at_epoch","decision",
            "reason_code","gateway_decision_digest"
        }
        if set(record) != required:
            raise GatewayRejected("MALFORMED_DECISION", "decision fields differ")
        body = dict(record)
        claimed = body.pop("gateway_decision_digest")
        if digest(body) != claimed:
            raise GatewayRejected("TAMPERED_DECISION", "decision digest differs")
        if record["decision"] not in DECISIONS:
            raise GatewayRejected("MALFORMED_DECISION", "decision invalid")
        if record["projected_action"] not in ACTIONS:
            raise GatewayRejected("MALFORMED_DECISION", "action invalid")
        return {
            "verification_pass": True,
            "decision": record["decision"],
            "reason_code": record["reason_code"],
            "gateway_decision_digest": claimed,
        }
