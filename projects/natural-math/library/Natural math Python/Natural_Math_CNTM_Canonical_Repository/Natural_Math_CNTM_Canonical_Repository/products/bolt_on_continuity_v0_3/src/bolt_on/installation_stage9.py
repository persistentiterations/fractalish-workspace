"""Deterministic data-only installation and uninstall planning."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from typing import Any, Mapping

from .configuration_stage4 import CanonicalConfiguration, validate_configuration
from .receipts import canonical_json_bytes

INSTALLATION_STATES = {"ABSENT", "INSTALLED", "PARTIAL", "CONFLICT"}
UNINSTALL_CHOICES = {"RETAIN_DATA", "DELETE_DATA"}
DELETE_CONFIRMATION = "DELETE RECEIPT DATA"


class InstallationPlanError(ValueError):
    """Stable fail-closed Stage 9 error."""


@dataclass(frozen=True)
class LifecyclePlan:
    body: Mapping[str, Any]

    def canonical_bytes(self) -> bytes:
        return canonical_json_bytes(dict(self.body)) + b"\n"


def _validated(configuration: object) -> CanonicalConfiguration:
    if isinstance(configuration, CanonicalConfiguration):
        return validate_configuration(dict(configuration.body))
    return validate_configuration(configuration)


def _base(configuration: CanonicalConfiguration, operation: str, outcome: str, targets: list[str]) -> dict[str, object]:
    subject = configuration.body["subject"]
    storage = configuration.body["storage"]
    data_directory = storage["data_directory"]
    return {
        "schema_version": 1,
        "contract": "bolt-on-continuity-v0.3-stage-9",
        "operation": operation,
        "outcome": outcome,
        "configuration_digest": configuration.body["configuration_digest"],
        "protected_subject": {"container_id": subject["container_id"]},
        "product_owned_paths": targets,
        "observation_only": True,
        "gateway_enabled": False,
        "native_execution_authorized": False,
        "container_mutation_authorized": False,
        "execution_performed": False,
        "data_directory": data_directory,
    }


def _finish(base: dict[str, object]) -> LifecyclePlan:
    digest = hashlib.sha256(canonical_json_bytes(base)).hexdigest()
    body = dict(base)
    body["plan_digest"] = "sha256:" + digest
    return LifecyclePlan(body)


def plan_install(configuration: object, installation_state: str) -> LifecyclePlan:
    config = _validated(configuration)
    if installation_state not in INSTALLATION_STATES:
        raise InstallationPlanError("INVALID_INSTALLATION_STATE")
    outcomes = {
        "ABSENT": "PLAN_INSTALL",
        "INSTALLED": "ALREADY_INSTALLED",
        "PARTIAL": "FAIL_CLOSED_PARTIAL",
        "CONFLICT": "FAIL_CLOSED_CONFLICT",
    }
    data_directory = config.body["storage"]["data_directory"]
    targets = [f"{data_directory}/configuration.json", f"{data_directory}/receipts"] if installation_state == "ABSENT" else []
    return _finish(_base(config, "INSTALL", outcomes[installation_state], targets))


def plan_uninstall(
    configuration: object,
    installation_state: str,
    retention_choice: str = "RETAIN_DATA",
    confirmation_token: str = "",
) -> LifecyclePlan:
    config = _validated(configuration)
    if installation_state not in INSTALLATION_STATES:
        raise InstallationPlanError("INVALID_INSTALLATION_STATE")
    if retention_choice not in UNINSTALL_CHOICES:
        raise InstallationPlanError("INVALID_RETENTION_CHOICE")
    if installation_state == "PARTIAL":
        outcome = "FAIL_CLOSED_PARTIAL"
    elif installation_state == "CONFLICT":
        outcome = "FAIL_CLOSED_CONFLICT"
    elif installation_state == "ABSENT":
        outcome = "ALREADY_ABSENT"
    elif retention_choice == "DELETE_DATA" and confirmation_token != DELETE_CONFIRMATION:
        outcome = "FAIL_CLOSED_CONFIRMATION"
    elif retention_choice == "DELETE_DATA":
        outcome = "PLAN_UNINSTALL_DELETE_DATA"
    else:
        outcome = "PLAN_UNINSTALL_RETAIN_DATA"
    data_directory = config.body["storage"]["data_directory"]
    targets: list[str] = []
    if outcome == "PLAN_UNINSTALL_RETAIN_DATA":
        targets = [f"{data_directory}/configuration.json"]
    elif outcome == "PLAN_UNINSTALL_DELETE_DATA":
        targets = [f"{data_directory}/configuration.json", f"{data_directory}/receipts"]
    base = _base(config, "UNINSTALL", outcome, targets)
    base["retention_choice"] = retention_choice
    base["deletion_confirmed"] = retention_choice == "DELETE_DATA" and confirmation_token == DELETE_CONFIRMATION
    base["deletion_performed"] = False
    return _finish(base)
