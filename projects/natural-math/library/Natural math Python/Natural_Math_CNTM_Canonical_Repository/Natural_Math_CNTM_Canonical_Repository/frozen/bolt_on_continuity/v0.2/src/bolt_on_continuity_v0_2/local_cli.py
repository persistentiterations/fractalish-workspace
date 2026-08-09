from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

from .product_configuration import ConfigurationError, validate_configuration

CLI_SCHEMA_VERSION = "1"
CLI_CONTRACT_VERSION = "5"
PRODUCT_VERSION = "0.2"
ALLOWED_COMMANDS = frozenset({"version", "config-check", "status", "start", "stop"})
ALLOWED_STATES = frozenset({"NOT_STARTED", "OBSERVATION_PLAN_READY", "STOP_PLAN_READY"})


@dataclass(frozen=True)
class CliResult:
    payload: dict[str, Any]

    def canonical_bytes(self) -> bytes:
        return (
            json.dumps(self.payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
            + "\n"
        ).encode("utf-8")


def _safety() -> dict[str, bool]:
    return {
        "autonomous_actions": False,
        "gateway_enabled": False,
        "native_execution_authorized": False,
        "observation_only": True,
    }


def _base(command: str, accepted: bool, reason_code: str) -> dict[str, Any]:
    return {
        "accepted": accepted,
        "cli_contract_version": CLI_CONTRACT_VERSION,
        "command": command,
        "product_version": PRODUCT_VERSION,
        "reason_code": reason_code,
        "safety": _safety(),
        "schema_version": CLI_SCHEMA_VERSION,
    }


def _rejected(command: str, reason_code: str) -> CliResult:
    payload = _base(command, False, reason_code)
    payload["lifecycle_state"] = "NOT_STARTED"
    return CliResult(payload)


def _validated_config(config_bytes: bytes) -> dict[str, Any]:
    if not isinstance(config_bytes, bytes):
        raise ConfigurationError("configuration input must be bytes")
    try:
        decoded = config_bytes.decode("utf-8")
        parsed = json.loads(decoded)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ConfigurationError("configuration encoding rejected") from exc
    if not isinstance(parsed, dict):
        raise ConfigurationError("configuration must be an object")
    return validate_configuration(parsed)


def run_command(command: str, config_bytes: bytes | None = None) -> CliResult:
    if not isinstance(command, str) or command not in ALLOWED_COMMANDS:
        return _rejected(str(command), "UNKNOWN_COMMAND")

    if command == "version":
        payload = _base(command, True, "VERSION_REPORTED")
        payload["lifecycle_state"] = "NOT_STARTED"
        return CliResult(payload)

    if config_bytes is None:
        return _rejected(command, "CONFIGURATION_REQUIRED")

    try:
        configuration = _validated_config(config_bytes)
    except (ConfigurationError, ValueError, TypeError, KeyError):
        return _rejected(command, "CONFIGURATION_REJECTED")

    digest = configuration.get("configuration_digest")
    subject = configuration.get("subject", {})
    container_id = subject.get("container_id") if isinstance(subject, dict) else None
    if not isinstance(digest, str) or not isinstance(container_id, str):
        return _rejected(command, "CONFIGURATION_REJECTED")

    payload = _base(command, True, "CONFIGURATION_VALID")
    payload["configuration_digest"] = digest
    payload["subject_container_id"] = container_id

    if command == "config-check":
        payload["lifecycle_state"] = "NOT_STARTED"
    elif command == "status":
        payload["lifecycle_state"] = "NOT_STARTED"
        payload["reason_code"] = "NO_RUNTIME_STATE_STORE"
    elif command == "start":
        payload["lifecycle_state"] = "OBSERVATION_PLAN_READY"
        payload["reason_code"] = "START_PLAN_CREATED"
        payload["plan"] = {
            "execution_performed": False,
            "gateway_activation_requested": False,
            "mode": "OBSERVATION_ONLY",
            "native_action_requested": False,
        }
    elif command == "stop":
        payload["lifecycle_state"] = "STOP_PLAN_READY"
        payload["reason_code"] = "STOP_PLAN_CREATED"
        payload["plan"] = {
            "container_mutation_requested": False,
            "execution_performed": False,
            "monitored_container_remains_independently_operable": True,
        }

    if payload["lifecycle_state"] not in ALLOWED_STATES:
        return _rejected(command, "INTERNAL_STATE_REJECTED")
    return CliResult(payload)
