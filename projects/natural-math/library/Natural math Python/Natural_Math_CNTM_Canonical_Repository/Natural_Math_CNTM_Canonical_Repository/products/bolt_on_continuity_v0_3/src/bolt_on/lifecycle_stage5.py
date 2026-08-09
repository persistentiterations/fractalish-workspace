"""Stage 5 observation-only lifecycle planning."""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Mapping

from .configuration_stage4 import ConfigurationError, validate_configuration
from .receipts import canonical_json_bytes
from .version import __version__

COMMANDS = {"config-check", "status", "start", "stop"}
STATES = {"NOT_STARTED", "OBSERVATION_PLAN_READY", "STOP_PLAN_READY"}
SAFETY = {
    "autonomous_actions": False,
    "gateway_enabled": False,
    "native_execution_authorized": False,
    "observation_only": True,
}


@dataclass(frozen=True)
class LifecycleResult:
    body: Mapping[str, Any]

    def canonical_json(self) -> str:
        return canonical_json_bytes(dict(self.body)).decode("utf-8")


def _rejected(command: str, reason: str) -> LifecycleResult:
    return LifecycleResult({
        "accepted": False,
        "command": command,
        "configuration_digest": None,
        "lifecycle_state": "NOT_STARTED",
        "plan": None,
        "product_version": __version__,
        "reason_code": reason,
        "safety": dict(SAFETY),
        "schema_version": 1,
        "subject_container_id": None,
    })


def execute(command: str, configuration_bytes: bytes) -> LifecycleResult:
    if command not in COMMANDS:
        return _rejected(command, "UNKNOWN_COMMAND")
    try:
        raw = json.loads(configuration_bytes.decode("utf-8"))
        validated = validate_configuration(raw)
    except (UnicodeDecodeError, json.JSONDecodeError, ConfigurationError, TypeError, ValueError):
        return _rejected(command, "CONFIGURATION_INVALID")

    config = dict(validated.body)
    state = "NOT_STARTED"
    plan: dict[str, object] | None = None
    reason = "CONFIGURATION_VALID"
    if command == "status":
        reason = "RUNTIME_NOT_STARTED"
    elif command == "start":
        state = "OBSERVATION_PLAN_READY"
        reason = "OBSERVATION_PLAN_CREATED"
        plan = {
            "components": ["observer", "receipt_store", "explanation_export"],
            "execution_performed": False,
        }
    elif command == "stop":
        state = "STOP_PLAN_READY"
        reason = "STOP_PLAN_CREATED"
        plan = {
            "container_mutated": False,
            "execution_performed": False,
            "monitored_container_remains_independently_operable": True,
        }

    return LifecycleResult({
        "accepted": True,
        "command": command,
        "configuration_digest": config["configuration_digest"],
        "lifecycle_state": state,
        "plan": plan,
        "product_version": __version__,
        "reason_code": reason,
        "safety": dict(SAFETY),
        "schema_version": 1,
        "subject_container_id": config["subject"]["container_id"],
    })
