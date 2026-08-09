"""Deterministic Stage 9 installation and uninstall planning."""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
from typing import Mapping

from .stage_3 import canonical_bytes
from .stage_4 import CanonicalConfiguration, ConfigurationError, validate_configuration

PRODUCT = "Bolt-On Continuity v0.4"
STAGE = 9
SCHEMA_VERSION = 1
QUALIFIED_STAGE_8_HEAD = "c31c0101e8bc97957f225f9a1892aba648a78e70"
STAGE_8_QUALIFICATION_RECORD_SHA256 = "b8c371184857f2c5d5d024562caca9e9195d16ca82115c467a774762ecb467b8"
STAGE_8_VERIFIER_MANIFEST_SHA256 = "09949caf33f16bbae695612fc4bd086f28d973a4277933f8f523c322e9bea6c0"

INSTALLATION_STATES = frozenset({"ABSENT", "INSTALLED", "PARTIAL", "CONFLICT"})
UNINSTALL_CHOICES = frozenset({"RETAIN_DATA", "DELETE_DATA"})
DELETE_CONFIRMATION = "DELETE RECEIPT DATA"

AUTHORITY = {
    "stage_4_configuration_consumption": True,
    "stage_8_record_binding": True,
    "installation_plan_construction": True,
    "uninstall_plan_construction": True,
    "retention_choice_validation": True,
    "deletion_confirmation_validation": True,
    "filesystem_read": False,
    "filesystem_mutation": False,
    "directory_creation": False,
    "package_installation": False,
    "service_registration": False,
    "environment_mutation": False,
    "docker_contact": False,
    "docker_mutation": False,
    "container_mutation": False,
    "receipt_deletion": False,
    "subprocess_execution": False,
    "network_contact": False,
    "native_execution": False,
    "background_service": False,
    "automatic_recovery": False,
    "publish_release": False,
    "production_claims": False,
}

class InstallationPlanError(ValueError):
    """Stable fail-closed Stage 9 error."""

@dataclass(frozen=True)
class LifecyclePlan:
    body_value: Mapping[str, object]

    def body(self) -> dict[str, object]:
        return dict(self.body_value)

    def canonical_bytes(self) -> bytes:
        return canonical_bytes(self.body())

    def canonical_json(self) -> str:
        return self.canonical_bytes().decode("utf-8")


def sha256(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _validated(configuration: object) -> CanonicalConfiguration:
    try:
        if isinstance(configuration, CanonicalConfiguration):
            return validate_configuration(configuration.body())
        return validate_configuration(configuration)
    except (ConfigurationError, TypeError, ValueError) as exc:
        raise InstallationPlanError("CONFIGURATION_INVALID") from exc


def _base(configuration: CanonicalConfiguration, operation: str, outcome: str, targets: list[str]) -> dict[str, object]:
    body = configuration.body()
    subject = body["subject"]
    storage = body["storage"]
    return {
        "accepted": True,
        "authority": dict(AUTHORITY),
        "configuration_digest": body["configuration_digest"],
        "container_mutation_authorized": False,
        "deletion_performed": False,
        "execution_performed": False,
        "filesystem_mutation_performed": False,
        "gateway_enabled": False,
        "native_execution_authorized": False,
        "observation_only": True,
        "operation": operation,
        "outcome": outcome,
        "product": PRODUCT,
        "product_owned_paths": targets,
        "protected_subject": {"container_id": subject["container_id"]},
        "qualified_stage_8_head": QUALIFIED_STAGE_8_HEAD,
        "schema_version": SCHEMA_VERSION,
        "stage": STAGE,
        "stage_8_qualification_record_sha256": STAGE_8_QUALIFICATION_RECORD_SHA256,
        "stage_8_verifier_manifest_sha256": STAGE_8_VERIFIER_MANIFEST_SHA256,
        "storage_data_directory": storage["data_directory"],
    }


def _finish(base: dict[str, object]) -> LifecyclePlan:
    digest = "sha256:" + sha256(canonical_bytes(base))
    return LifecyclePlan({**base, "plan_digest": digest})


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
    data_directory = config.body()["storage"]["data_directory"]
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

    data_directory = config.body()["storage"]["data_directory"]
    targets: list[str] = []
    if outcome == "PLAN_UNINSTALL_RETAIN_DATA":
        targets = [f"{data_directory}/configuration.json"]
    elif outcome == "PLAN_UNINSTALL_DELETE_DATA":
        targets = [f"{data_directory}/configuration.json", f"{data_directory}/receipts"]

    base = _base(config, "UNINSTALL", outcome, targets)
    base["retention_choice"] = retention_choice
    base["deletion_confirmed"] = retention_choice == "DELETE_DATA" and confirmation_token == DELETE_CONFIRMATION
    return _finish(base)


def render_human(plan: LifecyclePlan) -> str:
    body = plan.body()
    return "\n".join([
        f"PASS stage8.binding: {body['qualified_stage_8_head']}",
        f"PASS operation: {body['operation']}",
        f"PASS outcome: {body['outcome']}",
        "PASS filesystem.mutation.performed: FALSE",
        "PASS deletion.performed: FALSE",
        "PASS container.mutation.authorized: FALSE",
        "PASS native.execution.authorized: FALSE",
        "PASS docker.contact: DENIED",
        "STAGE_9_PLAN_READY",
        f"PLAN SHA-256 {body['plan_digest']}",
    ])
