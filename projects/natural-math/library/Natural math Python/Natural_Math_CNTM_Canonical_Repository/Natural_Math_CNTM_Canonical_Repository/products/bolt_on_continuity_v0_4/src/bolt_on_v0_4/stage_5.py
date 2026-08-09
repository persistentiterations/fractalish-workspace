"""Deterministic Stage 5 observation-only lifecycle planning."""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
from typing import Mapping

from .stage_4 import ConfigurationError, canonical_bytes, validate_configuration

PRODUCT = "Bolt-On Continuity v0.4"
STAGE = 5
SCHEMA_VERSION = 1
QUALIFIED_STAGE_4_HEAD = "9e05306ebbbd235beb2af8cf91c2b4c4d96c9ddc"
STAGE_4_QUALIFICATION_RECORD_SHA256 = "8ac44c29c207f6bf047f5291abc16b99394d1bfc139a15e57c35d0a37e2cebe9"
STAGE_4_VERIFIER_MANIFEST_SHA256 = "3628499eacbb59d457ccfd8333adb0ebcbfa4b0542891d4a26b24fdc2079ef8f"
COMMANDS = frozenset({"config-check", "status", "start", "stop"})
STATES = frozenset({"NOT_STARTED", "OBSERVATION_PLAN_READY", "STOP_PLAN_READY"})

SAFETY = {
    "autonomous_actions": False,
    "container_mutated": False,
    "execution_performed": False,
    "gateway_enabled": False,
    "native_execution_authorized": False,
    "observation_only": True,
}

AUTHORITY = {
    "stage_4_configuration_consumption": True,
    "configuration_validation": True,
    "lifecycle_plan_construction": True,
    "docker_contact": False,
    "docker_mutation": False,
    "container_enumeration": False,
    "container_inspection": False,
    "container_start_stop_restart": False,
    "container_exec": False,
    "container_create_remove": False,
    "filesystem_read": False,
    "filesystem_mutation": False,
    "process_inspection": False,
    "subprocess_execution": False,
    "installer_execution": False,
    "background_service": False,
    "thread_creation": False,
    "network_contact": False,
    "automatic_recovery": False,
    "gateway_action": False,
    "hold_release_projection": False,
    "attach_or_distribute_packages": False,
    "publish_release": False,
    "production_claims": False,
}


def sha256(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


@dataclass(frozen=True)
class LifecycleResult:
    body_value: Mapping[str, object]

    def body(self) -> dict[str, object]:
        return dict(self.body_value)

    def canonical_bytes(self) -> bytes:
        return canonical_bytes(self.body())

    def canonical_json(self) -> str:
        return self.canonical_bytes().decode("utf-8")

    @property
    def result_digest(self) -> str:
        return str(self.body_value["result_digest"])


def _build_result(command: str, *, accepted: bool, reason_code: str, lifecycle_state: str, configuration_digest: str | None, subject_container_id: str | None, plan: Mapping[str, object] | None) -> LifecycleResult:
    if lifecycle_state not in STATES:
        raise ValueError("unsupported lifecycle state")
    base: dict[str, object] = {
        "accepted": accepted,
        "authority": dict(AUTHORITY),
        "command": command,
        "configuration_digest": configuration_digest,
        "lifecycle_state": lifecycle_state,
        "plan": dict(plan) if plan is not None else None,
        "product": PRODUCT,
        "qualified_stage_4_head": QUALIFIED_STAGE_4_HEAD,
        "reason_code": reason_code,
        "safety": dict(SAFETY),
        "schema_version": SCHEMA_VERSION,
        "stage": STAGE,
        "stage_4_qualification_record_sha256": STAGE_4_QUALIFICATION_RECORD_SHA256,
        "stage_4_verifier_manifest_sha256": STAGE_4_VERIFIER_MANIFEST_SHA256,
        "subject_container_id": subject_container_id,
    }
    return LifecycleResult({**base, "result_digest": sha256(canonical_bytes(base))})


def execute(command: str, configuration_bytes: bytes) -> LifecycleResult:
    if command not in COMMANDS:
        return _build_result(command, accepted=False, reason_code="UNKNOWN_COMMAND", lifecycle_state="NOT_STARTED", configuration_digest=None, subject_container_id=None, plan=None)
    try:
        raw = json.loads(configuration_bytes.decode("utf-8"))
        configuration = validate_configuration(raw)
    except (UnicodeDecodeError, json.JSONDecodeError, ConfigurationError, TypeError, ValueError):
        return _build_result(command, accepted=False, reason_code="CONFIGURATION_INVALID", lifecycle_state="NOT_STARTED", configuration_digest=None, subject_container_id=None, plan=None)

    body = configuration.body()
    digest = str(body["configuration_digest"])
    subject_id = str(body["subject"]["container_id"])
    state = "NOT_STARTED"
    reason = "CONFIGURATION_VALID"
    plan: dict[str, object] | None = None
    if command == "status":
        reason = "RUNTIME_NOT_STARTED"
    elif command == "start":
        state = "OBSERVATION_PLAN_READY"
        reason = "OBSERVATION_PLAN_CREATED"
        plan = {"components": ["observer", "receipt_store", "explanation_export"], "container_mutated": False, "execution_performed": False, "persistence_performed": False}
    elif command == "stop":
        state = "STOP_PLAN_READY"
        reason = "STOP_PLAN_CREATED"
        plan = {"container_mutated": False, "execution_performed": False, "monitored_container_remains_independently_operable": True, "runtime_was_running": False}
    return _build_result(command, accepted=True, reason_code=reason, lifecycle_state=state, configuration_digest=digest, subject_container_id=subject_id, plan=plan)


def render_human(result: LifecycleResult) -> str:
    body = result.body()
    lines = [
        f"PASS stage4.binding: {body['qualified_stage_4_head']}",
        f"PASS command: {body['command']}",
        f"PASS accepted: {str(body['accepted']).upper()}",
        f"PASS lifecycle.state: {body['lifecycle_state']}",
        "PASS execution.performed: FALSE",
        "PASS container.mutated: FALSE",
        "PASS docker.contact: DENIED",
        "STAGE_5_PLAN_READY" if body["accepted"] else "STAGE_5_REJECTED",
        f"RESULT SHA-256 {body['result_digest']}",
    ]
    return "\n".join(lines)
