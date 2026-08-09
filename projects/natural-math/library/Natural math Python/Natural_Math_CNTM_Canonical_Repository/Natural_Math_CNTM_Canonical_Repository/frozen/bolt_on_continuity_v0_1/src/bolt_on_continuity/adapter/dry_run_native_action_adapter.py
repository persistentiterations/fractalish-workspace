from __future__ import annotations
import hashlib
import json
from typing import Any

SCHEMA_VERSION = "1"
ZERO_DIGEST = "sha256:" + "0" * 64
ALLOWED_ACTIONS = {"HOLD", "RELEASE"}
ALLOWED_OPERATIONS = {"pause", "unpause"}

class AdapterRejected(ValueError):
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

class DryRunNativeActionAdapter:
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
            "docker_binary",
            "max_decision_age_seconds",
            "dry_run_required",
        }
        if set(policy) != required:
            raise ValueError("policy fields differ")
        if policy["policy_version"] != "1":
            raise ValueError("unsupported policy version")
        if policy["docker_binary"] != "docker":
            raise ValueError("docker binary must be exact")
        if type(policy["max_decision_age_seconds"]) is not int or policy["max_decision_age_seconds"] <= 0:
            raise ValueError("max_decision_age_seconds must be positive integer")
        if policy["dry_run_required"] is not True:
            raise ValueError("dry_run_required must be true")

        self.container_id = container_id.lower()
        self.configuration_digest = configuration_digest
        self.policy = json.loads(json.dumps(policy))
        self.policy_digest = digest(self.policy)
        self._last_adapter_sequence = -1
        self._last_gateway_sequence = -1
        self._last_plan_digest = ZERO_DIGEST

    @property
    def state(self) -> dict[str, Any]:
        return {
            "last_adapter_sequence": self._last_adapter_sequence,
            "last_gateway_sequence": self._last_gateway_sequence,
            "last_plan_digest": self._last_plan_digest,
        }

    def plan(self, gateway_decision: dict[str, Any], *, adapter_sequence: int, created_at_epoch: int) -> dict[str, Any]:
        if type(adapter_sequence) is not int or adapter_sequence < 0:
            raise AdapterRejected("MALFORMED_REQUEST", "adapter sequence invalid")
        if type(created_at_epoch) is not int or created_at_epoch < 0:
            raise AdapterRejected("MALFORMED_REQUEST", "creation time invalid")

        self._validate_gateway_decision(gateway_decision)

        if adapter_sequence <= self._last_adapter_sequence:
            raise AdapterRejected("ADAPTER_SEQUENCE_REGRESSION", "adapter sequence did not advance")
        if gateway_decision["gateway_sequence"] <= self._last_gateway_sequence:
            raise AdapterRejected("GATEWAY_REPLAY", "gateway sequence replayed")
        if created_at_epoch < gateway_decision["decided_at_epoch"]:
            raise AdapterRejected("TIME_REVERSED", "plan predates gateway decision")
        if created_at_epoch - gateway_decision["decided_at_epoch"] > self.policy["max_decision_age_seconds"]:
            raise AdapterRejected("DECISION_TOO_OLD", "gateway decision too old")

        if gateway_decision["decision"] == "NO_ACTION":
            result = self._no_plan(gateway_decision, adapter_sequence, created_at_epoch, "NO_ACTION_DECISION")
        elif gateway_decision["decision"] == "DENY":
            result = self._no_plan(gateway_decision, adapter_sequence, created_at_epoch, "DENIED_BY_GATEWAY")
        elif gateway_decision["decision"] == "APPROVE":
            action = gateway_decision["projected_action"]
            if action not in ALLOWED_ACTIONS:
                raise AdapterRejected("UNSUPPORTED_ACTION", "approved action unsupported")
            operation = "pause" if action == "HOLD" else "unpause"
            body = {
                "schema_version": SCHEMA_VERSION,
                "incident_id": gateway_decision["incident_id"],
                "container_id": self.container_id,
                "configuration_digest": self.configuration_digest,
                "gateway_decision_digest": gateway_decision["gateway_decision_digest"],
                "gateway_sequence": gateway_decision["gateway_sequence"],
                "projected_action": action,
                "native_operation": operation,
                "argument_vector": ["docker", operation, self.container_id],
                "adapter_policy_digest": self.policy_digest,
                "adapter_sequence": adapter_sequence,
                "created_at_epoch": created_at_epoch,
                "dry_run": True,
                "plan_status": "PLANNED",
                "reason_code": "APPROVED_MAPPING",
                "previous_plan_digest": self._last_plan_digest,
            }
            result = {**body, "plan_digest": digest(body)}
        else:
            raise AdapterRejected("MALFORMED_DECISION", "gateway decision invalid")

        self._last_adapter_sequence = adapter_sequence
        self._last_gateway_sequence = gateway_decision["gateway_sequence"]
        self._last_plan_digest = result["plan_digest"]
        return result

    def _no_plan(self, decision: dict[str, Any], adapter_sequence: int,
                 created_at_epoch: int, reason_code: str) -> dict[str, Any]:
        body = {
            "schema_version": SCHEMA_VERSION,
            "incident_id": decision["incident_id"],
            "container_id": self.container_id,
            "configuration_digest": self.configuration_digest,
            "gateway_decision_digest": decision["gateway_decision_digest"],
            "gateway_sequence": decision["gateway_sequence"],
            "projected_action": decision["projected_action"],
            "native_operation": None,
            "argument_vector": [],
            "adapter_policy_digest": self.policy_digest,
            "adapter_sequence": adapter_sequence,
            "created_at_epoch": created_at_epoch,
            "dry_run": True,
            "plan_status": "NO_PLAN",
            "reason_code": reason_code,
            "previous_plan_digest": self._last_plan_digest,
        }
        return {**body, "plan_digest": digest(body)}

    def _validate_gateway_decision(self, record: dict[str, Any]) -> None:
        if not isinstance(record, dict):
            raise AdapterRejected("TAMPERED_DECISION", "gateway decision must be object")
        required = {
            "schema_version","incident_id","container_id","configuration_digest",
            "projection_digest","projection_sequence","projected_action",
            "gateway_policy_digest","gateway_sequence",
            "previous_gateway_decision_digest","decided_at_epoch","decision",
            "reason_code","gateway_decision_digest"
        }
        if set(record) != required:
            raise AdapterRejected("TAMPERED_DECISION", "gateway decision fields differ")

        body = dict(record)
        claimed = body.pop("gateway_decision_digest")
        if digest(body) != claimed:
            raise AdapterRejected("TAMPERED_DECISION", "gateway decision digest differs")
        if record["container_id"] != self.container_id:
            raise AdapterRejected("SUBJECT_MISMATCH", "gateway subject differs")
        if record["configuration_digest"] != self.configuration_digest:
            raise AdapterRejected("CONFIGURATION_MISMATCH", "gateway configuration differs")
        if record["decision"] not in {"APPROVE", "DENY", "NO_ACTION"}:
            raise AdapterRejected("MALFORMED_DECISION", "gateway decision invalid")
        if record["projected_action"] not in {"HOLD", "RELEASE", "NO_ACTION"}:
            raise AdapterRejected("UNSUPPORTED_ACTION", "projected action invalid")
        if type(record["gateway_sequence"]) is not int or record["gateway_sequence"] < 0:
            raise AdapterRejected("TAMPERED_DECISION", "gateway sequence invalid")
        if type(record["decided_at_epoch"]) is not int or record["decided_at_epoch"] < 0:
            raise AdapterRejected("TAMPERED_DECISION", "gateway decision time invalid")
        for field in ("projection_digest", "gateway_policy_digest", "previous_gateway_decision_digest"):
            if not valid_digest(record[field]):
                raise AdapterRejected("TAMPERED_DECISION", f"{field} invalid")

    @staticmethod
    def verify_plan(record: dict[str, Any]) -> dict[str, Any]:
        if not isinstance(record, dict):
            raise AdapterRejected("MALFORMED_PLAN", "plan must be object")
        required = {
            "schema_version","incident_id","container_id","configuration_digest",
            "gateway_decision_digest","gateway_sequence","projected_action",
            "native_operation","argument_vector","adapter_policy_digest",
            "adapter_sequence","created_at_epoch","dry_run","plan_status",
            "reason_code","previous_plan_digest","plan_digest"
        }
        if set(record) != required:
            raise AdapterRejected("MALFORMED_PLAN", "plan fields differ")
        body = dict(record)
        claimed = body.pop("plan_digest")
        if digest(body) != claimed:
            raise AdapterRejected("TAMPERED_PLAN", "plan digest differs")
        if record["dry_run"] is not True:
            raise AdapterRejected("MALFORMED_PLAN", "dry-run flag invalid")
        if record["plan_status"] == "PLANNED":
            if record["native_operation"] not in ALLOWED_OPERATIONS:
                raise AdapterRejected("MALFORMED_PLAN", "native operation invalid")
            expected = ["docker", record["native_operation"], record["container_id"]]
            if record["argument_vector"] != expected:
                raise AdapterRejected("MALFORMED_PLAN", "argument vector differs")
        elif record["plan_status"] == "NO_PLAN":
            if record["native_operation"] is not None or record["argument_vector"] != []:
                raise AdapterRejected("MALFORMED_PLAN", "no-plan contains operation")
        else:
            raise AdapterRejected("MALFORMED_PLAN", "plan status invalid")

        return {
            "verification_pass": True,
            "plan_status": record["plan_status"],
            "native_operation": record["native_operation"],
            "plan_digest": claimed,
        }
