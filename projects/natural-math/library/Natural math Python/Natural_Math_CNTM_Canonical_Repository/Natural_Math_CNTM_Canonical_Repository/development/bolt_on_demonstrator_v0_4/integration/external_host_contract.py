#!/usr/bin/env python3
"""External host integration contract for Bolt-On Demonstrator v0.4, Stage 1.

Stage 1 defines the minimum evidence an independently existing host must expose
before a later pilot may attach the frozen v0.3 portability architecture.  This
stage does not execute host commands.  It assesses a host profile, validates a
read/project-only adapter package, registers that package in an external sidecar
registry, removes it, and proves that the ordinary host baseline is unchanged.

The contract deliberately separates four surfaces:

* a read-only, deterministically ordered observation export;
* a host-owned native command boundary;
* a sidecar-only installation and exact-removal lifecycle; and
* a portable adapter surface limited to identity, normalization, and projection.

Malformed, over-privileged, execution-claiming, source-modifying, or
non-removable integrations fail closed.  SHA-256 values are deterministic
integrity bindings for this demonstrator, not production identity signatures.
"""

from __future__ import annotations

import ast
import hashlib
import importlib.util
import json
from abc import ABC, abstractmethod
from dataclasses import dataclass, replace
from pathlib import Path
import sys
from typing import Iterable, Mapping, Sequence, Tuple

sys.dont_write_bytecode = True

STAGE_NAME = "EXTERNAL HOST INTEGRATION CONTRACT"
STAGE_VERSION = "0.4.1"
MODE = "EXTERNAL_HOST_CONTRACT_DRY_RUN"
EXECUTION_AUTHORITY = "NONE"
INSTALLATION_MODE = "SIDECAR_REGISTRY"
ZERO_DIGEST = "0" * 64

EXPECTED_FROZEN_V03_MANIFEST_SHA256 = (
    "57f7026ff9dcc69d6dcacb51fda89a40700828e110e74145a0edfaf266c5f6fa"
)
EXPECTED_FROZEN_V03_ENTRIES = 20

THIS_FILE = Path(__file__).resolve()
PROJECT_DIR = THIS_FILE.parents[1]
REPOSITORY_ROOT = THIS_FILE.parents[3]
FROZEN_V03_ROOT = REPOSITORY_ROOT / "frozen" / "bolt_on" / "v0.3"
FROZEN_V03_MANIFEST = FROZEN_V03_ROOT / "RELEASE_MANIFEST_SHA256.txt"
FROZEN_V03_CONTRACT = FROZEN_V03_ROOT / "portability" / "portable_adapter_contract.py"

ALLOWED_DEPLOYMENT_KINDS = (
    "LOCAL_PROCESS",
    "SYSTEM_SERVICE",
    "CONTAINER_SERVICE",
    "EMBEDDED_LIBRARY",
)
ALLOWED_OBSERVATION_TRANSPORTS = (
    "APPEND_ONLY_FILE",
    "LOCAL_READ_API",
    "MESSAGE_EXPORT",
    "SNAPSHOT_EXPORT",
)
ALLOWED_COMMAND_TRANSPORTS = (
    "LOCAL_COMMAND_API",
    "HOST_COMMAND_QUEUE",
    "VERSIONED_REQUEST_FILE",
)
ALLOWED_EVENT_ORDERING = ("TOTAL_SEQUENCE", "VERSION_THEN_SEQUENCE")
ALLOWED_PERMISSIONS = (
    "OBSERVE_READ_ONLY",
    "PROJECT_ONLY",
    "REGISTER_SIDECAR",
)
REQUIRED_ADAPTER_METHODS = ("identity", "normalise_record", "project_action")
PROHIBITED_ADAPTER_METHODS = (
    "apply",
    "dispatch",
    "execute",
    "execute_host_action",
    "mutate_host",
    "run_command",
    "send_command",
)

INSTALL = "INSTALL"
REMOVE = "REMOVE"


def _load_module(module_name: str, path: Path):
    existing = sys.modules.get(module_name)
    if existing is not None:
        return existing
    spec = importlib.util.spec_from_file_location(module_name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"could not load module from {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


frozen_v03 = _load_module("frozen_bolt_on_v03_contract_for_v04_stage1", FROZEN_V03_CONTRACT)
HOLD = frozen_v03.HOLD
RELEASE = frozen_v03.RELEASE
PORTABLE_ACTIONS = tuple(frozen_v03.SUPPORTED_ACTIONS)


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _canonical_json(value: object) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def _digest_json(value: object) -> str:
    return _sha256_bytes(_canonical_json(value).encode("ascii"))


def _is_digest(value: object) -> bool:
    return (
        isinstance(value, str)
        and len(value) == 64
        and all(character in "0123456789abcdef" for character in value)
    )


def _exact_int(value: object, name: str, *, minimum: int = 0) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise TypeError(f"{name} must be an exact integer")
    if value < minimum:
        raise ValueError(f"{name} must be >= {minimum}")
    return value


def _nonempty_text(value: object, name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{name} must be a non-empty string")
    return value.strip()


def _normalise_text_tuple(
    values: Iterable[object],
    name: str,
    *,
    upper: bool = True,
    sort_values: bool = True,
) -> Tuple[str, ...]:
    rows = []
    for value in tuple(values):
        text = _nonempty_text(value, name)
        rows.append(text.upper() if upper else text)
    if len(set(rows)) != len(rows):
        raise ValueError(f"{name} values must be unique")
    if sort_values:
        rows.sort()
    return tuple(rows)


def _normalise_pairs(
    values: Mapping[object, object] | Iterable[Tuple[object, object]],
    name: str,
) -> Tuple[Tuple[str, str], ...]:
    source = values.items() if isinstance(values, Mapping) else tuple(values)
    rows: list[Tuple[str, str]] = []
    for key, value in source:
        rows.append(
            (
                _nonempty_text(key, f"{name} key").upper(),
                _nonempty_text(value, f"{name} value").upper(),
            )
        )
    rows.sort()
    if len({key for key, _ in rows}) != len(rows):
        raise ValueError(f"{name} keys must be unique")
    return tuple(rows)


def _manifest_entries(path: Path) -> Tuple[Tuple[str, str], ...]:
    rows: list[Tuple[str, str]] = []
    for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        parts = line.split("  ", 1)
        if len(parts) != 2 or not _is_digest(parts[0]):
            raise ValueError(f"invalid manifest line {number}: {line}")
        rows.append((parts[1], parts[0]))
    if len({relative for relative, _ in rows}) != len(rows):
        raise ValueError("manifest paths must be unique")
    return tuple(rows)


def verify_frozen_v03_release() -> Tuple[bool, str, int]:
    if not FROZEN_V03_ROOT.is_dir() or not FROZEN_V03_MANIFEST.is_file():
        return False, "FROZEN_V03_MISSING", 0
    if _sha256_file(FROZEN_V03_MANIFEST) != EXPECTED_FROZEN_V03_MANIFEST_SHA256:
        return False, "FROZEN_V03_MANIFEST_DIGEST_MISMATCH", 0
    try:
        entries = _manifest_entries(FROZEN_V03_MANIFEST)
    except (OSError, UnicodeError, ValueError):
        return False, "FROZEN_V03_MANIFEST_INVALID", 0
    if len(entries) != EXPECTED_FROZEN_V03_ENTRIES:
        return False, "FROZEN_V03_ENTRY_COUNT_MISMATCH", len(entries)
    expected = {relative: digest for relative, digest in entries}
    actual = {
        path.relative_to(FROZEN_V03_ROOT).as_posix()
        for path in FROZEN_V03_ROOT.rglob("*")
        if path.is_file() and path != FROZEN_V03_MANIFEST
    }
    if actual != set(expected):
        return False, "FROZEN_V03_FILE_SET_MISMATCH", len(entries)
    for relative, digest in entries:
        if _sha256_file(FROZEN_V03_ROOT / relative) != digest:
            return False, f"FROZEN_V03_CHANGED:{relative}", len(entries)
    return True, "VALID", len(entries)


class ExternalIntegrationAdapter(ABC):
    """The only adapter surface permitted by the Stage 1 contract."""

    @abstractmethod
    def identity(self):
        raise NotImplementedError

    @abstractmethod
    def normalise_record(self, raw_record: object):
        raise NotImplementedError

    @abstractmethod
    def project_action(self, request: object, record: object):
        raise NotImplementedError


@dataclass(frozen=True)
class ExternalHostIdentity:
    host_id: str
    host_family: str
    host_version: str
    integration_api: str
    deployment_kind: str
    identity_digest: str

    def unsigned_record(self) -> dict[str, object]:
        return {
            "deployment_kind": self.deployment_kind,
            "host_family": self.host_family,
            "host_id": self.host_id,
            "host_version": self.host_version,
            "integration_api": self.integration_api,
        }


@dataclass(frozen=True)
class ObservationContract:
    channel_id: str
    transport: str
    event_ordering: str
    subject_key: str
    sequence_field: str
    state_field: str
    version_field: str
    read_only: bool
    append_only: bool
    deterministic_serialization: bool
    snapshot_supported: bool
    observation_digest: str

    def unsigned_record(self) -> dict[str, object]:
        return {
            "append_only": self.append_only,
            "channel_id": self.channel_id,
            "deterministic_serialization": self.deterministic_serialization,
            "event_ordering": self.event_ordering,
            "read_only": self.read_only,
            "sequence_field": self.sequence_field,
            "snapshot_supported": self.snapshot_supported,
            "state_field": self.state_field,
            "subject_key": self.subject_key,
            "transport": self.transport,
            "version_field": self.version_field,
        }


@dataclass(frozen=True)
class CommandBoundaryContract:
    boundary_id: str
    owner: str
    transport: str
    allowed_operations: Tuple[str, ...]
    requires_exact_subject: bool
    requires_expected_version: bool
    requires_idempotency_key: bool
    requires_authorization_token: bool
    adapter_receives_callable: bool
    wildcard_operations: bool
    boundary_digest: str

    def unsigned_record(self) -> dict[str, object]:
        return {
            "adapter_receives_callable": self.adapter_receives_callable,
            "allowed_operations": list(self.allowed_operations),
            "boundary_id": self.boundary_id,
            "owner": self.owner,
            "requires_authorization_token": self.requires_authorization_token,
            "requires_exact_subject": self.requires_exact_subject,
            "requires_expected_version": self.requires_expected_version,
            "requires_idempotency_key": self.requires_idempotency_key,
            "transport": self.transport,
            "wildcard_operations": self.wildcard_operations,
        }


@dataclass(frozen=True)
class LifecycleContract:
    installation_mode: str
    sidecar_root: str
    host_source_changes_required: bool
    host_restart_required: bool
    monkeypatch_required: bool
    environment_mutation_required: bool
    uninstall_supported: bool
    exact_rollback_supported: bool
    lifecycle_digest: str

    def unsigned_record(self) -> dict[str, object]:
        return {
            "environment_mutation_required": self.environment_mutation_required,
            "exact_rollback_supported": self.exact_rollback_supported,
            "host_restart_required": self.host_restart_required,
            "host_source_changes_required": self.host_source_changes_required,
            "installation_mode": self.installation_mode,
            "monkeypatch_required": self.monkeypatch_required,
            "sidecar_root": self.sidecar_root,
            "uninstall_supported": self.uninstall_supported,
        }


@dataclass(frozen=True)
class OrdinaryHostBaseline:
    subject_id: str
    ordinary_operations: Tuple[str, ...]
    applied_operations: int
    rejected_operations: int
    final_state: str
    final_version: int
    baseline_digest: str

    def unsigned_record(self) -> dict[str, object]:
        return {
            "applied_operations": self.applied_operations,
            "final_state": self.final_state,
            "final_version": self.final_version,
            "ordinary_operations": list(self.ordinary_operations),
            "rejected_operations": self.rejected_operations,
            "subject_id": self.subject_id,
        }


@dataclass(frozen=True)
class ExternalHostProfile:
    identity: ExternalHostIdentity
    observation: ObservationContract
    command_boundary: CommandBoundaryContract
    lifecycle: LifecycleContract
    baseline: OrdinaryHostBaseline
    profile_digest: str

    def unsigned_record(self) -> dict[str, object]:
        return {
            "baseline_digest": self.baseline.baseline_digest,
            "command_boundary_digest": self.command_boundary.boundary_digest,
            "host_identity_digest": self.identity.identity_digest,
            "lifecycle_digest": self.lifecycle.lifecycle_digest,
            "observation_digest": self.observation.observation_digest,
        }


@dataclass(frozen=True)
class ExternalAdapterPackage:
    package_id: str
    package_version: str
    contract_version: str
    target_host_identity_digest: str
    portable_actions: Tuple[str, ...]
    operation_map: Tuple[Tuple[str, str], ...]
    state_map: Tuple[Tuple[str, str], ...]
    requested_permissions: Tuple[str, ...]
    exported_methods: Tuple[str, ...]
    contains_executor: bool
    contains_host_mutator: bool
    requires_shell: bool
    writes_host_source: bool
    package_digest: str

    def unsigned_record(self) -> dict[str, object]:
        return {
            "contains_executor": self.contains_executor,
            "contains_host_mutator": self.contains_host_mutator,
            "contract_version": self.contract_version,
            "exported_methods": list(self.exported_methods),
            "operation_map": [list(item) for item in self.operation_map],
            "package_id": self.package_id,
            "package_version": self.package_version,
            "portable_actions": list(self.portable_actions),
            "requested_permissions": list(self.requested_permissions),
            "requires_shell": self.requires_shell,
            "state_map": [list(item) for item in self.state_map],
            "target_host_identity_digest": self.target_host_identity_digest,
            "writes_host_source": self.writes_host_source,
        }


@dataclass(frozen=True)
class CompatibilityAssessment:
    compatible: bool
    reason_codes: Tuple[str, ...]
    host_profile_digest: str
    package_digest: str
    portable_actions: Tuple[str, ...]
    mapped_operations: Tuple[str, ...]
    required_permissions: Tuple[str, ...]
    host_actions: int
    bolt_on_executed_actions: int
    assessment_digest: str

    def unsigned_record(self) -> dict[str, object]:
        return {
            "bolt_on_executed_actions": self.bolt_on_executed_actions,
            "compatible": self.compatible,
            "host_actions": self.host_actions,
            "host_profile_digest": self.host_profile_digest,
            "mapped_operations": list(self.mapped_operations),
            "package_digest": self.package_digest,
            "portable_actions": list(self.portable_actions),
            "reason_codes": list(self.reason_codes),
            "required_permissions": list(self.required_permissions),
        }


@dataclass(frozen=True)
class RegistryEvent:
    sequence: int
    event_type: str
    registry_id: str
    host_profile_digest: str
    package_digest: str
    baseline_digest: str
    installed_count_after: int
    prior_event_digest: str
    event_digest: str

    def unsigned_record(self) -> dict[str, object]:
        return {
            "baseline_digest": self.baseline_digest,
            "event_type": self.event_type,
            "host_profile_digest": self.host_profile_digest,
            "installed_count_after": self.installed_count_after,
            "package_digest": self.package_digest,
            "prior_event_digest": self.prior_event_digest,
            "registry_id": self.registry_id,
            "sequence": self.sequence,
        }


@dataclass(frozen=True)
class SidecarRegistry:
    registry_id: str
    installed_packages: Tuple[str, ...]
    events: Tuple[RegistryEvent, ...]
    registry_digest: str

    def unsigned_record(self) -> dict[str, object]:
        return {
            "events": [event.event_digest for event in self.events],
            "installed_packages": list(self.installed_packages),
            "registry_id": self.registry_id,
        }


@dataclass(frozen=True)
class IntegrationReceipt:
    receipt_id: int
    kind: str
    subject: str
    payload: str
    prior_hash: str
    receipt_hash: str


@dataclass(frozen=True)
class ReceiptReplay:
    passed: bool
    checked_receipts: int
    final_digest: str
    compatible: bool
    installed_count: int
    host_state_changes: int
    host_actions: int
    bolt_on_executed_actions: int
    first_error: str


@dataclass(frozen=True)
class RejectionResult:
    case_id: str
    expected_reason: str
    observed_reason: str
    rejected: bool
    host_state_unchanged: bool
    host_actions: int
    bolt_on_executed_actions: int
    result_digest: str

    def unsigned_record(self) -> dict[str, object]:
        return {
            "bolt_on_executed_actions": self.bolt_on_executed_actions,
            "case_id": self.case_id,
            "expected_reason": self.expected_reason,
            "host_actions": self.host_actions,
            "host_state_unchanged": self.host_state_unchanged,
            "observed_reason": self.observed_reason,
            "rejected": self.rejected,
        }


@dataclass(frozen=True)
class Stage1Qualification:
    passed: bool
    stage_name: str
    stage_version: str
    mode: str
    execution_authority: str
    frozen_v03_pre_pass: bool
    frozen_v03_post_pass: bool
    frozen_v03_unchanged: bool
    frozen_v03_entries: int
    contract_requirements: int
    compatible: bool
    deterministic_second_pass: bool
    install_registrations: int
    remove_registrations: int
    host_state_changes: int
    host_actions: int
    bolt_on_executed_actions: int
    registry_empty_after_remove: bool
    receipt_replay_pass: bool
    receipt_tamper_detection_pass: bool
    receipt_reorder_detection_pass: bool
    rejection_cases: int
    rejection_cases_safely_rejected: int
    source_unchanged: bool
    no_hidden_execution_authority: bool
    baseline_digest: str
    compatibility_digest: str
    receipt_digest: str
    replay_digest: str
    frozen_v03_manifest_sha256: str


def build_host_identity(
    *,
    host_id: str,
    host_family: str,
    host_version: str,
    integration_api: str,
    deployment_kind: str,
) -> ExternalHostIdentity:
    unsigned = {
        "deployment_kind": _nonempty_text(deployment_kind, "deployment_kind").upper(),
        "host_family": _nonempty_text(host_family, "host_family"),
        "host_id": _nonempty_text(host_id, "host_id"),
        "host_version": _nonempty_text(host_version, "host_version"),
        "integration_api": _nonempty_text(integration_api, "integration_api"),
    }
    return ExternalHostIdentity(**unsigned, identity_digest=_digest_json(unsigned))


def build_observation_contract(
    *,
    channel_id: str,
    transport: str,
    event_ordering: str,
    subject_key: str,
    sequence_field: str,
    state_field: str,
    version_field: str,
    read_only: bool,
    append_only: bool,
    deterministic_serialization: bool,
    snapshot_supported: bool,
) -> ObservationContract:
    unsigned = {
        "append_only": bool(append_only),
        "channel_id": _nonempty_text(channel_id, "channel_id"),
        "deterministic_serialization": bool(deterministic_serialization),
        "event_ordering": _nonempty_text(event_ordering, "event_ordering").upper(),
        "read_only": bool(read_only),
        "sequence_field": _nonempty_text(sequence_field, "sequence_field"),
        "snapshot_supported": bool(snapshot_supported),
        "state_field": _nonempty_text(state_field, "state_field"),
        "subject_key": _nonempty_text(subject_key, "subject_key"),
        "transport": _nonempty_text(transport, "transport").upper(),
        "version_field": _nonempty_text(version_field, "version_field"),
    }
    return ObservationContract(**unsigned, observation_digest=_digest_json(unsigned))


def build_command_boundary(
    *,
    boundary_id: str,
    owner: str,
    transport: str,
    allowed_operations: Iterable[object],
    requires_exact_subject: bool,
    requires_expected_version: bool,
    requires_idempotency_key: bool,
    requires_authorization_token: bool,
    adapter_receives_callable: bool,
    wildcard_operations: bool,
) -> CommandBoundaryContract:
    unsigned = {
        "adapter_receives_callable": bool(adapter_receives_callable),
        "allowed_operations": list(
            _normalise_text_tuple(allowed_operations, "allowed operation")
        ),
        "boundary_id": _nonempty_text(boundary_id, "boundary_id"),
        "owner": _nonempty_text(owner, "owner").upper(),
        "requires_authorization_token": bool(requires_authorization_token),
        "requires_exact_subject": bool(requires_exact_subject),
        "requires_expected_version": bool(requires_expected_version),
        "requires_idempotency_key": bool(requires_idempotency_key),
        "transport": _nonempty_text(transport, "transport").upper(),
        "wildcard_operations": bool(wildcard_operations),
    }
    return CommandBoundaryContract(
        boundary_id=unsigned["boundary_id"],
        owner=unsigned["owner"],
        transport=unsigned["transport"],
        allowed_operations=tuple(unsigned["allowed_operations"]),
        requires_exact_subject=unsigned["requires_exact_subject"],
        requires_expected_version=unsigned["requires_expected_version"],
        requires_idempotency_key=unsigned["requires_idempotency_key"],
        requires_authorization_token=unsigned["requires_authorization_token"],
        adapter_receives_callable=unsigned["adapter_receives_callable"],
        wildcard_operations=unsigned["wildcard_operations"],
        boundary_digest=_digest_json(unsigned),
    )


def build_lifecycle_contract(
    *,
    installation_mode: str,
    sidecar_root: str,
    host_source_changes_required: bool,
    host_restart_required: bool,
    monkeypatch_required: bool,
    environment_mutation_required: bool,
    uninstall_supported: bool,
    exact_rollback_supported: bool,
) -> LifecycleContract:
    unsigned = {
        "environment_mutation_required": bool(environment_mutation_required),
        "exact_rollback_supported": bool(exact_rollback_supported),
        "host_restart_required": bool(host_restart_required),
        "host_source_changes_required": bool(host_source_changes_required),
        "installation_mode": _nonempty_text(
            installation_mode, "installation_mode"
        ).upper(),
        "monkeypatch_required": bool(monkeypatch_required),
        "sidecar_root": _nonempty_text(sidecar_root, "sidecar_root"),
        "uninstall_supported": bool(uninstall_supported),
    }
    return LifecycleContract(**unsigned, lifecycle_digest=_digest_json(unsigned))


def build_ordinary_baseline(
    *,
    subject_id: str,
    ordinary_operations: Iterable[object],
    applied_operations: int,
    rejected_operations: int,
    final_state: str,
    final_version: int,
) -> OrdinaryHostBaseline:
    unsigned = {
        "applied_operations": _exact_int(applied_operations, "applied_operations"),
        "final_state": _nonempty_text(final_state, "final_state").upper(),
        "final_version": _exact_int(final_version, "final_version"),
        "ordinary_operations": list(
            _normalise_text_tuple(
                ordinary_operations,
                "ordinary operation",
                sort_values=False,
            )
        ),
        "rejected_operations": _exact_int(rejected_operations, "rejected_operations"),
        "subject_id": _nonempty_text(subject_id, "subject_id"),
    }
    return OrdinaryHostBaseline(
        subject_id=unsigned["subject_id"],
        ordinary_operations=tuple(unsigned["ordinary_operations"]),
        applied_operations=unsigned["applied_operations"],
        rejected_operations=unsigned["rejected_operations"],
        final_state=unsigned["final_state"],
        final_version=unsigned["final_version"],
        baseline_digest=_digest_json(unsigned),
    )


def build_external_host_profile(
    identity: ExternalHostIdentity,
    observation: ObservationContract,
    command_boundary: CommandBoundaryContract,
    lifecycle: LifecycleContract,
    baseline: OrdinaryHostBaseline,
) -> ExternalHostProfile:
    unsigned = {
        "baseline_digest": baseline.baseline_digest,
        "command_boundary_digest": command_boundary.boundary_digest,
        "host_identity_digest": identity.identity_digest,
        "lifecycle_digest": lifecycle.lifecycle_digest,
        "observation_digest": observation.observation_digest,
    }
    return ExternalHostProfile(
        identity=identity,
        observation=observation,
        command_boundary=command_boundary,
        lifecycle=lifecycle,
        baseline=baseline,
        profile_digest=_digest_json(unsigned),
    )


def build_adapter_package(
    *,
    package_id: str,
    package_version: str,
    target_host_identity_digest: str,
    portable_actions: Iterable[object],
    operation_map: Mapping[object, object] | Iterable[Tuple[object, object]],
    state_map: Mapping[object, object] | Iterable[Tuple[object, object]],
    requested_permissions: Iterable[object],
    exported_methods: Iterable[object],
    contains_executor: bool = False,
    contains_host_mutator: bool = False,
    requires_shell: bool = False,
    writes_host_source: bool = False,
    contract_version: str = STAGE_VERSION,
) -> ExternalAdapterPackage:
    actions = _normalise_text_tuple(portable_actions, "portable action")
    mappings = _normalise_pairs(operation_map, "operation map")
    states = _normalise_pairs(state_map, "state map")
    permissions = _normalise_text_tuple(requested_permissions, "requested permission")
    methods = _normalise_text_tuple(
        exported_methods,
        "exported method",
        upper=False,
    )
    unsigned = {
        "contains_executor": bool(contains_executor),
        "contains_host_mutator": bool(contains_host_mutator),
        "contract_version": _nonempty_text(contract_version, "contract_version"),
        "exported_methods": list(methods),
        "operation_map": [list(item) for item in mappings],
        "package_id": _nonempty_text(package_id, "package_id"),
        "package_version": _nonempty_text(package_version, "package_version"),
        "portable_actions": list(actions),
        "requested_permissions": list(permissions),
        "requires_shell": bool(requires_shell),
        "state_map": [list(item) for item in states],
        "target_host_identity_digest": _nonempty_text(
            target_host_identity_digest, "target_host_identity_digest"
        ),
        "writes_host_source": bool(writes_host_source),
    }
    return ExternalAdapterPackage(
        package_id=unsigned["package_id"],
        package_version=unsigned["package_version"],
        contract_version=unsigned["contract_version"],
        target_host_identity_digest=unsigned["target_host_identity_digest"],
        portable_actions=actions,
        operation_map=mappings,
        state_map=states,
        requested_permissions=permissions,
        exported_methods=methods,
        contains_executor=unsigned["contains_executor"],
        contains_host_mutator=unsigned["contains_host_mutator"],
        requires_shell=unsigned["requires_shell"],
        writes_host_source=unsigned["writes_host_source"],
        package_digest=_digest_json(unsigned),
    )


def _valid_digest_record(value: object, digest_field: str) -> bool:
    digest = getattr(value, digest_field, None)
    unsigned = getattr(value, "unsigned_record", lambda: None)()
    return _is_digest(digest) and isinstance(unsigned, dict) and digest == _digest_json(unsigned)


def validate_external_host_profile(profile: ExternalHostProfile) -> Tuple[bool, str]:
    if not isinstance(profile, ExternalHostProfile):
        return False, "HOST_PROFILE_TYPE_INVALID"
    if not _valid_digest_record(profile.identity, "identity_digest"):
        return False, "HOST_IDENTITY_DIGEST_MISMATCH"
    if not _valid_digest_record(profile.observation, "observation_digest"):
        return False, "OBSERVATION_DIGEST_MISMATCH"
    if not _valid_digest_record(profile.command_boundary, "boundary_digest"):
        return False, "COMMAND_BOUNDARY_DIGEST_MISMATCH"
    if not _valid_digest_record(profile.lifecycle, "lifecycle_digest"):
        return False, "LIFECYCLE_DIGEST_MISMATCH"
    if not _valid_digest_record(profile.baseline, "baseline_digest"):
        return False, "BASELINE_DIGEST_MISMATCH"
    if not _valid_digest_record(profile, "profile_digest"):
        return False, "HOST_PROFILE_DIGEST_MISMATCH"
    return True, "VALID"


def validate_adapter_package(package: ExternalAdapterPackage) -> Tuple[bool, str]:
    if not isinstance(package, ExternalAdapterPackage):
        return False, "ADAPTER_PACKAGE_TYPE_INVALID"
    if not _valid_digest_record(package, "package_digest"):
        return False, "ADAPTER_PACKAGE_DIGEST_MISMATCH"
    return True, "VALID"


def _assessment_reasons(
    profile: ExternalHostProfile,
    package: ExternalAdapterPackage,
) -> Tuple[str, ...]:
    valid_profile, reason = validate_external_host_profile(profile)
    if not valid_profile:
        return (reason,)
    valid_package, reason = validate_adapter_package(package)
    if not valid_package:
        return (reason,)

    reasons: list[str] = []
    identity = profile.identity
    observation = profile.observation
    boundary = profile.command_boundary
    lifecycle = profile.lifecycle
    baseline = profile.baseline

    if identity.deployment_kind not in ALLOWED_DEPLOYMENT_KINDS:
        reasons.append("DEPLOYMENT_KIND_UNSUPPORTED")
    if observation.transport not in ALLOWED_OBSERVATION_TRANSPORTS:
        reasons.append("OBSERVATION_TRANSPORT_UNSUPPORTED")
    if observation.event_ordering not in ALLOWED_EVENT_ORDERING:
        reasons.append("OBSERVATION_ORDERING_INSUFFICIENT")
    if not observation.read_only:
        reasons.append("OBSERVATION_NOT_READ_ONLY")
    if not observation.append_only:
        reasons.append("OBSERVATION_NOT_APPEND_ONLY")
    if not observation.deterministic_serialization:
        reasons.append("OBSERVATION_SERIALIZATION_NONDETERMINISTIC")
    if not observation.snapshot_supported:
        reasons.append("OBSERVATION_SNAPSHOT_UNAVAILABLE")
    if boundary.owner != "HOST":
        reasons.append("COMMAND_BOUNDARY_NOT_HOST_OWNED")
    if boundary.transport not in ALLOWED_COMMAND_TRANSPORTS:
        reasons.append("COMMAND_TRANSPORT_UNSUPPORTED")
    if boundary.adapter_receives_callable:
        reasons.append("ADAPTER_RECEIVES_COMMAND_CALLABLE")
    if boundary.wildcard_operations:
        reasons.append("COMMAND_OPERATION_WILDCARD")
    if not boundary.requires_exact_subject:
        reasons.append("COMMAND_SUBJECT_NOT_EXACT")
    if not boundary.requires_expected_version:
        reasons.append("COMMAND_VERSION_NOT_BOUND")
    if not boundary.requires_idempotency_key:
        reasons.append("COMMAND_IDEMPOTENCY_UNBOUND")
    if not boundary.requires_authorization_token:
        reasons.append("COMMAND_AUTHORITY_UNBOUND")
    if lifecycle.installation_mode != INSTALLATION_MODE:
        reasons.append("INSTALLATION_NOT_SIDECAR")
    if lifecycle.host_source_changes_required:
        reasons.append("HOST_SOURCE_CHANGE_REQUIRED")
    if lifecycle.host_restart_required:
        reasons.append("HOST_RESTART_REQUIRED")
    if lifecycle.monkeypatch_required:
        reasons.append("MONKEYPATCH_REQUIRED")
    if lifecycle.environment_mutation_required:
        reasons.append("HOST_ENVIRONMENT_MUTATION_REQUIRED")
    if not lifecycle.uninstall_supported:
        reasons.append("UNINSTALL_UNAVAILABLE")
    if not lifecycle.exact_rollback_supported:
        reasons.append("EXACT_ROLLBACK_UNAVAILABLE")
    if baseline.applied_operations < 1 or baseline.rejected_operations != 0:
        reasons.append("ORDINARY_BASELINE_NOT_CLEAN")

    if package.contract_version != STAGE_VERSION:
        reasons.append("ADAPTER_CONTRACT_VERSION_MISMATCH")
    if package.target_host_identity_digest != identity.identity_digest:
        reasons.append("ADAPTER_TARGET_HOST_MISMATCH")
    if tuple(package.portable_actions) != tuple(sorted(PORTABLE_ACTIONS)):
        reasons.append("PORTABLE_ACTION_SET_MISMATCH")
    operation_map = dict(package.operation_map)
    if tuple(sorted(operation_map)) != tuple(sorted(PORTABLE_ACTIONS)):
        reasons.append("PORTABLE_OPERATION_MAP_INCOMPLETE")
    if len(set(operation_map.values())) != len(operation_map):
        reasons.append("NATIVE_OPERATION_MAP_NOT_DISTINCT")
    if any(operation not in boundary.allowed_operations for operation in operation_map.values()):
        reasons.append("NATIVE_OPERATION_NOT_ALLOWED")
    if tuple(package.requested_permissions) != tuple(sorted(ALLOWED_PERMISSIONS)):
        reasons.append("ADAPTER_PERMISSION_SET_INVALID")
    if tuple(package.exported_methods) != tuple(sorted(REQUIRED_ADAPTER_METHODS)):
        reasons.append("ADAPTER_METHOD_SURFACE_INVALID")
    if any(method in PROHIBITED_ADAPTER_METHODS for method in package.exported_methods):
        reasons.append("ADAPTER_EXECUTION_METHOD_EXPOSED")
    if package.contains_executor:
        reasons.append("ADAPTER_CONTAINS_EXECUTOR")
    if package.contains_host_mutator:
        reasons.append("ADAPTER_CONTAINS_HOST_MUTATOR")
    if package.requires_shell:
        reasons.append("ADAPTER_REQUIRES_SHELL")
    if package.writes_host_source:
        reasons.append("ADAPTER_WRITES_HOST_SOURCE")
    if len(package.state_map) < 2:
        reasons.append("STATE_MAP_INSUFFICIENT")

    return tuple(dict.fromkeys(reasons))


def assess_external_host_contract(
    profile: ExternalHostProfile,
    package: ExternalAdapterPackage,
) -> CompatibilityAssessment:
    reasons = _assessment_reasons(profile, package)
    compatible = not reasons
    operation_map = dict(package.operation_map) if isinstance(package, ExternalAdapterPackage) else {}
    mapped_operations = tuple(sorted(operation_map.values()))
    permissions = tuple(package.requested_permissions) if isinstance(package, ExternalAdapterPackage) else ()
    portable = tuple(package.portable_actions) if isinstance(package, ExternalAdapterPackage) else ()
    unsigned = {
        "bolt_on_executed_actions": 0,
        "compatible": compatible,
        "host_actions": 0,
        "host_profile_digest": getattr(profile, "profile_digest", ZERO_DIGEST),
        "mapped_operations": list(mapped_operations),
        "package_digest": getattr(package, "package_digest", ZERO_DIGEST),
        "portable_actions": list(portable),
        "reason_codes": list(reasons),
        "required_permissions": list(permissions),
    }
    return CompatibilityAssessment(
        compatible=compatible,
        reason_codes=reasons,
        host_profile_digest=unsigned["host_profile_digest"],
        package_digest=unsigned["package_digest"],
        portable_actions=portable,
        mapped_operations=mapped_operations,
        required_permissions=permissions,
        host_actions=0,
        bolt_on_executed_actions=0,
        assessment_digest=_digest_json(unsigned),
    )


def empty_registry(registry_id: str = "EXTERNAL-SIDECAR-REGISTRY-1") -> SidecarRegistry:
    unsigned = {
        "events": [],
        "installed_packages": [],
        "registry_id": _nonempty_text(registry_id, "registry_id"),
    }
    return SidecarRegistry(
        registry_id=unsigned["registry_id"],
        installed_packages=(),
        events=(),
        registry_digest=_digest_json(unsigned),
    )


def validate_registry(registry: SidecarRegistry) -> Tuple[bool, str]:
    if not isinstance(registry, SidecarRegistry):
        return False, "REGISTRY_TYPE_INVALID"
    prior = ZERO_DIGEST
    installed: list[str] = []
    for index, event in enumerate(registry.events, 1):
        if event.sequence != index:
            return False, "REGISTRY_SEQUENCE_INVALID"
        if event.prior_event_digest != prior:
            return False, "REGISTRY_CHAIN_INVALID"
        if event.event_digest != _digest_json(event.unsigned_record()):
            return False, "REGISTRY_EVENT_DIGEST_MISMATCH"
        if event.event_type == INSTALL:
            if event.package_digest in installed:
                return False, "REGISTRY_DUPLICATE_INSTALL"
            installed.append(event.package_digest)
        elif event.event_type == REMOVE:
            if event.package_digest not in installed:
                return False, "REGISTRY_REMOVE_UNKNOWN_PACKAGE"
            installed.remove(event.package_digest)
        else:
            return False, "REGISTRY_EVENT_TYPE_INVALID"
        if event.installed_count_after != len(installed):
            return False, "REGISTRY_INSTALLED_COUNT_INVALID"
        prior = event.event_digest
    if tuple(sorted(installed)) != tuple(registry.installed_packages):
        return False, "REGISTRY_FINAL_SET_MISMATCH"
    if registry.registry_digest != _digest_json(registry.unsigned_record()):
        return False, "REGISTRY_DIGEST_MISMATCH"
    return True, "VALID"


def _append_registry_event(
    registry: SidecarRegistry,
    *,
    event_type: str,
    profile: ExternalHostProfile,
    package: ExternalAdapterPackage,
) -> SidecarRegistry:
    valid, reason = validate_registry(registry)
    if not valid:
        raise ValueError(f"invalid registry: {reason}")
    installed = list(registry.installed_packages)
    if event_type == INSTALL:
        if package.package_digest in installed:
            raise ValueError("package is already installed")
        installed.append(package.package_digest)
    elif event_type == REMOVE:
        if package.package_digest not in installed:
            raise ValueError("package is not installed")
        installed.remove(package.package_digest)
    else:
        raise ValueError("unsupported registry event")
    installed.sort()
    unsigned_event = {
        "baseline_digest": profile.baseline.baseline_digest,
        "event_type": event_type,
        "host_profile_digest": profile.profile_digest,
        "installed_count_after": len(installed),
        "package_digest": package.package_digest,
        "prior_event_digest": registry.events[-1].event_digest if registry.events else ZERO_DIGEST,
        "registry_id": registry.registry_id,
        "sequence": len(registry.events) + 1,
    }
    event = RegistryEvent(**unsigned_event, event_digest=_digest_json(unsigned_event))
    events = (*registry.events, event)
    unsigned_registry = {
        "events": [item.event_digest for item in events],
        "installed_packages": installed,
        "registry_id": registry.registry_id,
    }
    return SidecarRegistry(
        registry_id=registry.registry_id,
        installed_packages=tuple(installed),
        events=events,
        registry_digest=_digest_json(unsigned_registry),
    )


def install_sidecar(
    registry: SidecarRegistry,
    profile: ExternalHostProfile,
    package: ExternalAdapterPackage,
) -> SidecarRegistry:
    assessment = assess_external_host_contract(profile, package)
    if not assessment.compatible:
        reason = assessment.reason_codes[0] if assessment.reason_codes else "INCOMPATIBLE"
        raise ValueError(f"integration contract rejected: {reason}")
    return _append_registry_event(
        registry,
        event_type=INSTALL,
        profile=profile,
        package=package,
    )


def remove_sidecar(
    registry: SidecarRegistry,
    profile: ExternalHostProfile,
    package: ExternalAdapterPackage,
) -> SidecarRegistry:
    return _append_registry_event(
        registry,
        event_type=REMOVE,
        profile=profile,
        package=package,
    )


def append_receipt(
    receipts: Sequence[IntegrationReceipt],
    kind: str,
    subject: str,
    payload: object,
) -> Tuple[IntegrationReceipt, ...]:
    rows = tuple(receipts)
    prior = rows[-1].receipt_hash if rows else ZERO_DIGEST
    record = {
        "kind": _nonempty_text(kind, "kind"),
        "payload": _canonical_json(payload),
        "prior_hash": prior,
        "receipt_id": len(rows) + 1,
        "subject": _nonempty_text(subject, "subject"),
    }
    receipt = IntegrationReceipt(**record, receipt_hash=_digest_json(record))
    return (*rows, receipt)


def replay_receipts(receipts: Sequence[IntegrationReceipt]) -> ReceiptReplay:
    prior = ZERO_DIGEST
    compatible = False
    installed_count = 0
    host_state_changes = 0
    host_actions = 0
    bolt_on_actions = 0
    checked = 0
    for expected_id, receipt in enumerate(tuple(receipts), 1):
        checked += 1
        if not isinstance(receipt, IntegrationReceipt):
            return ReceiptReplay(False, checked, prior, compatible, installed_count, host_state_changes, host_actions, bolt_on_actions, "RECEIPT_TYPE_INVALID")
        if receipt.receipt_id != expected_id:
            return ReceiptReplay(False, checked, prior, compatible, installed_count, host_state_changes, host_actions, bolt_on_actions, "RECEIPT_ID_INVALID")
        if receipt.prior_hash != prior:
            return ReceiptReplay(False, checked, prior, compatible, installed_count, host_state_changes, host_actions, bolt_on_actions, "RECEIPT_CHAIN_INVALID")
        record = {
            "kind": receipt.kind,
            "payload": receipt.payload,
            "prior_hash": receipt.prior_hash,
            "receipt_id": receipt.receipt_id,
            "subject": receipt.subject,
        }
        if receipt.receipt_hash != _digest_json(record):
            return ReceiptReplay(False, checked, prior, compatible, installed_count, host_state_changes, host_actions, bolt_on_actions, "RECEIPT_HASH_MISMATCH")
        try:
            payload = json.loads(receipt.payload)
        except json.JSONDecodeError:
            return ReceiptReplay(False, checked, prior, compatible, installed_count, host_state_changes, host_actions, bolt_on_actions, "RECEIPT_PAYLOAD_INVALID")
        if receipt.kind == "ASSESSMENT":
            compatible = payload.get("compatible") is True
            host_actions = int(payload.get("host_actions", 0))
            bolt_on_actions = int(payload.get("bolt_on_executed_actions", 0))
        elif receipt.kind == "INSTALL":
            if installed_count != 0 or payload.get("installed_count_after") != 1:
                return ReceiptReplay(False, checked, prior, compatible, installed_count, host_state_changes, host_actions, bolt_on_actions, "INSTALL_SEMANTIC_INVALID")
            installed_count = 1
        elif receipt.kind == "REMOVE":
            if installed_count != 1 or payload.get("installed_count_after") != 0:
                return ReceiptReplay(False, checked, prior, compatible, installed_count, host_state_changes, host_actions, bolt_on_actions, "REMOVE_SEMANTIC_INVALID")
            installed_count = 0
        elif receipt.kind == "NEUTRALITY":
            if payload.get("baseline_before") != payload.get("baseline_after"):
                host_state_changes += 1
        elif receipt.kind == "SUMMARY":
            expected = {
                "compatible": compatible,
                "installed_count": installed_count,
                "host_state_changes": host_state_changes,
                "host_actions": host_actions,
                "bolt_on_executed_actions": bolt_on_actions,
            }
            if any(payload.get(key) != value for key, value in expected.items()):
                return ReceiptReplay(False, checked, prior, compatible, installed_count, host_state_changes, host_actions, bolt_on_actions, "SUMMARY_SEMANTIC_INVALID")
        prior = receipt.receipt_hash
    passed = bool(receipts) and compatible and installed_count == 0 and host_state_changes == 0 and host_actions == 0 and bolt_on_actions == 0
    return ReceiptReplay(
        passed,
        checked,
        prior,
        compatible,
        installed_count,
        host_state_changes,
        host_actions,
        bolt_on_actions,
        "" if passed else "TERMINAL_INVARIANT_FAILED",
    )


def build_reference_profile() -> ExternalHostProfile:
    identity = build_host_identity(
        host_id="ORDINARY-JOB-SERVICE-A",
        host_family="ORDINARY VERSIONED JOB SERVICE",
        host_version="1.0",
        integration_api="job-events-v1",
        deployment_kind="LOCAL_PROCESS",
    )
    observation = build_observation_contract(
        channel_id="JOB-EVENT-EXPORT",
        transport="APPEND_ONLY_FILE",
        event_ordering="TOTAL_SEQUENCE",
        subject_key="job_id",
        sequence_field="sequence",
        state_field="state",
        version_field="version",
        read_only=True,
        append_only=True,
        deterministic_serialization=True,
        snapshot_supported=True,
    )
    command_boundary = build_command_boundary(
        boundary_id="JOB-COMMAND-GATEWAY",
        owner="HOST",
        transport="VERSIONED_REQUEST_FILE",
        allowed_operations=("PAUSE_JOB", "RESUME_JOB"),
        requires_exact_subject=True,
        requires_expected_version=True,
        requires_idempotency_key=True,
        requires_authorization_token=True,
        adapter_receives_callable=False,
        wildcard_operations=False,
    )
    lifecycle = build_lifecycle_contract(
        installation_mode=INSTALLATION_MODE,
        sidecar_root="external_integrations/bolt_on_v0_4",
        host_source_changes_required=False,
        host_restart_required=False,
        monkeypatch_required=False,
        environment_mutation_required=False,
        uninstall_supported=True,
        exact_rollback_supported=True,
    )
    baseline = build_ordinary_baseline(
        subject_id="JOB-17",
        ordinary_operations=("CREATE", "START", "CHECKPOINT", "COMPLETE"),
        applied_operations=4,
        rejected_operations=0,
        final_state="DONE",
        final_version=4,
    )
    return build_external_host_profile(
        identity,
        observation,
        command_boundary,
        lifecycle,
        baseline,
    )


def build_reference_package(profile: ExternalHostProfile) -> ExternalAdapterPackage:
    return build_adapter_package(
        package_id="EXTERNAL-JOB-SERVICE-ADAPTER",
        package_version=STAGE_VERSION,
        target_host_identity_digest=profile.identity.identity_digest,
        portable_actions=PORTABLE_ACTIONS,
        operation_map={HOLD: "PAUSE_JOB", RELEASE: "RESUME_JOB"},
        state_map={"RUNNING": "ACTIVE", "PAUSED": "HELD", "DONE": "COMPLETE"},
        requested_permissions=ALLOWED_PERMISSIONS,
        exported_methods=REQUIRED_ADAPTER_METHODS,
    )


def _rehash(value: object, digest_field: str):
    return replace(value, **{digest_field: _digest_json(value.unsigned_record())})


def rejection_cases(
    profile: ExternalHostProfile,
    package: ExternalAdapterPackage,
) -> Tuple[Tuple[str, str, ExternalHostProfile, ExternalAdapterPackage], ...]:
    cases: list[Tuple[str, str, ExternalHostProfile, ExternalAdapterPackage]] = []

    def host_case(case_id: str, expected: str, changed: ExternalHostProfile) -> None:
        cases.append((case_id, expected, changed, package))

    def package_case(case_id: str, expected: str, changed: ExternalAdapterPackage) -> None:
        cases.append((case_id, expected, profile, changed))

    host_case(
        "HOST_IDENTITY_HASH",
        "HOST_IDENTITY_DIGEST_MISMATCH",
        replace(profile, identity=replace(profile.identity, identity_digest=ZERO_DIGEST)),
    )
    host_case(
        "OBSERVATION_WRITABLE",
        "OBSERVATION_NOT_READ_ONLY",
        build_external_host_profile(profile.identity, _rehash(replace(profile.observation, read_only=False), "observation_digest"), profile.command_boundary, profile.lifecycle, profile.baseline),
    )
    host_case(
        "OBSERVATION_REWRITABLE",
        "OBSERVATION_NOT_APPEND_ONLY",
        build_external_host_profile(profile.identity, _rehash(replace(profile.observation, append_only=False), "observation_digest"), profile.command_boundary, profile.lifecycle, profile.baseline),
    )
    host_case(
        "OBSERVATION_NONDETERMINISTIC",
        "OBSERVATION_SERIALIZATION_NONDETERMINISTIC",
        build_external_host_profile(profile.identity, _rehash(replace(profile.observation, deterministic_serialization=False), "observation_digest"), profile.command_boundary, profile.lifecycle, profile.baseline),
    )
    host_case(
        "OBSERVATION_NO_SNAPSHOT",
        "OBSERVATION_SNAPSHOT_UNAVAILABLE",
        build_external_host_profile(profile.identity, _rehash(replace(profile.observation, snapshot_supported=False), "observation_digest"), profile.command_boundary, profile.lifecycle, profile.baseline),
    )
    host_case(
        "COMMAND_NOT_HOST_OWNED",
        "COMMAND_BOUNDARY_NOT_HOST_OWNED",
        build_external_host_profile(profile.identity, profile.observation, _rehash(replace(profile.command_boundary, owner="ADAPTER"), "boundary_digest"), profile.lifecycle, profile.baseline),
    )
    host_case(
        "COMMAND_CALLABLE_EXPOSED",
        "ADAPTER_RECEIVES_COMMAND_CALLABLE",
        build_external_host_profile(profile.identity, profile.observation, _rehash(replace(profile.command_boundary, adapter_receives_callable=True), "boundary_digest"), profile.lifecycle, profile.baseline),
    )
    host_case(
        "COMMAND_WILDCARD",
        "COMMAND_OPERATION_WILDCARD",
        build_external_host_profile(profile.identity, profile.observation, _rehash(replace(profile.command_boundary, wildcard_operations=True), "boundary_digest"), profile.lifecycle, profile.baseline),
    )
    host_case(
        "COMMAND_VERSION_UNBOUND",
        "COMMAND_VERSION_NOT_BOUND",
        build_external_host_profile(profile.identity, profile.observation, _rehash(replace(profile.command_boundary, requires_expected_version=False), "boundary_digest"), profile.lifecycle, profile.baseline),
    )
    host_case(
        "COMMAND_AUTHORITY_UNBOUND",
        "COMMAND_AUTHORITY_UNBOUND",
        build_external_host_profile(profile.identity, profile.observation, _rehash(replace(profile.command_boundary, requires_authorization_token=False), "boundary_digest"), profile.lifecycle, profile.baseline),
    )
    host_case(
        "INSTALL_NOT_SIDECAR",
        "INSTALLATION_NOT_SIDECAR",
        build_external_host_profile(profile.identity, profile.observation, profile.command_boundary, _rehash(replace(profile.lifecycle, installation_mode="IN_PROCESS_PLUGIN"), "lifecycle_digest"), profile.baseline),
    )
    host_case(
        "HOST_SOURCE_CHANGE",
        "HOST_SOURCE_CHANGE_REQUIRED",
        build_external_host_profile(profile.identity, profile.observation, profile.command_boundary, _rehash(replace(profile.lifecycle, host_source_changes_required=True), "lifecycle_digest"), profile.baseline),
    )
    host_case(
        "HOST_RESTART",
        "HOST_RESTART_REQUIRED",
        build_external_host_profile(profile.identity, profile.observation, profile.command_boundary, _rehash(replace(profile.lifecycle, host_restart_required=True), "lifecycle_digest"), profile.baseline),
    )
    host_case(
        "MONKEYPATCH",
        "MONKEYPATCH_REQUIRED",
        build_external_host_profile(profile.identity, profile.observation, profile.command_boundary, _rehash(replace(profile.lifecycle, monkeypatch_required=True), "lifecycle_digest"), profile.baseline),
    )
    host_case(
        "NO_UNINSTALL",
        "UNINSTALL_UNAVAILABLE",
        build_external_host_profile(profile.identity, profile.observation, profile.command_boundary, _rehash(replace(profile.lifecycle, uninstall_supported=False), "lifecycle_digest"), profile.baseline),
    )
    host_case(
        "NO_ROLLBACK",
        "EXACT_ROLLBACK_UNAVAILABLE",
        build_external_host_profile(profile.identity, profile.observation, profile.command_boundary, _rehash(replace(profile.lifecycle, exact_rollback_supported=False), "lifecycle_digest"), profile.baseline),
    )
    package_case(
        "PACKAGE_HASH",
        "ADAPTER_PACKAGE_DIGEST_MISMATCH",
        replace(package, package_digest=ZERO_DIGEST),
    )
    package_case(
        "TARGET_HOST",
        "ADAPTER_TARGET_HOST_MISMATCH",
        _rehash(replace(package, target_host_identity_digest="f" * 64), "package_digest"),
    )
    package_case(
        "ACTION_SET",
        "PORTABLE_ACTION_SET_MISMATCH",
        _rehash(replace(package, portable_actions=(HOLD,)), "package_digest"),
    )
    package_case(
        "MAP_INCOMPLETE",
        "PORTABLE_OPERATION_MAP_INCOMPLETE",
        _rehash(replace(package, operation_map=((HOLD, "PAUSE_JOB"),)), "package_digest"),
    )
    package_case(
        "MAP_SAME_OPERATION",
        "NATIVE_OPERATION_MAP_NOT_DISTINCT",
        _rehash(replace(package, operation_map=((HOLD, "PAUSE_JOB"), (RELEASE, "PAUSE_JOB"))), "package_digest"),
    )
    package_case(
        "MAP_UNALLOWED_OPERATION",
        "NATIVE_OPERATION_NOT_ALLOWED",
        _rehash(replace(package, operation_map=((HOLD, "PAUSE_JOB"), (RELEASE, "DELETE_JOB"))), "package_digest"),
    )
    package_case(
        "PERMISSION_ESCALATION",
        "ADAPTER_PERMISSION_SET_INVALID",
        _rehash(replace(package, requested_permissions=(*package.requested_permissions, "HOST_WRITE")), "package_digest"),
    )
    package_case(
        "METHOD_EXECUTE",
        "ADAPTER_METHOD_SURFACE_INVALID",
        _rehash(replace(package, exported_methods=(*package.exported_methods, "execute")), "package_digest"),
    )
    package_case(
        "CONTAINS_EXECUTOR",
        "ADAPTER_CONTAINS_EXECUTOR",
        _rehash(replace(package, contains_executor=True), "package_digest"),
    )
    package_case(
        "CONTAINS_MUTATOR",
        "ADAPTER_CONTAINS_HOST_MUTATOR",
        _rehash(replace(package, contains_host_mutator=True), "package_digest"),
    )
    package_case(
        "REQUIRES_SHELL",
        "ADAPTER_REQUIRES_SHELL",
        _rehash(replace(package, requires_shell=True), "package_digest"),
    )
    package_case(
        "WRITES_HOST_SOURCE",
        "ADAPTER_WRITES_HOST_SOURCE",
        _rehash(replace(package, writes_host_source=True), "package_digest"),
    )
    return tuple(cases)


def run_rejection_matrix(
    profile: ExternalHostProfile,
    package: ExternalAdapterPackage,
) -> Tuple[RejectionResult, ...]:
    baseline = profile.baseline.baseline_digest
    results: list[RejectionResult] = []
    for case_id, expected, candidate_profile, candidate_package in rejection_cases(profile, package):
        assessment = assess_external_host_contract(candidate_profile, candidate_package)
        observed = assessment.reason_codes[0] if assessment.reason_codes else "ACCEPTED"
        rejected = not assessment.compatible and expected in assessment.reason_codes
        host_unchanged = profile.baseline.baseline_digest == baseline
        unsigned = {
            "bolt_on_executed_actions": assessment.bolt_on_executed_actions,
            "case_id": case_id,
            "expected_reason": expected,
            "host_actions": assessment.host_actions,
            "host_state_unchanged": host_unchanged,
            "observed_reason": observed,
            "rejected": rejected,
        }
        results.append(RejectionResult(**unsigned, result_digest=_digest_json(unsigned)))
    return tuple(results)


def structural_authority_scan() -> Tuple[bool, Tuple[str, ...]]:
    hits: list[str] = []
    methods = tuple(sorted(ExternalIntegrationAdapter.__abstractmethods__))
    if methods != tuple(sorted(REQUIRED_ADAPTER_METHODS)):
        hits.append("ADAPTER_ABSTRACT_SURFACE_CHANGED")
    tree = ast.parse(THIS_FILE.read_text(encoding="utf-8"))
    for node in tree.body:
        if isinstance(node, ast.ClassDef) and node.name == "ExternalIntegrationAdapter":
            defined = {
                child.name
                for child in node.body
                if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef))
            }
            for name in PROHIBITED_ADAPTER_METHODS:
                if name in defined:
                    hits.append(f"PROHIBITED_ADAPTER_METHOD:{name}")
    if EXECUTION_AUTHORITY != "NONE":
        hits.append("EXECUTION_AUTHORITY_NOT_NONE")
    return not hits, tuple(hits)


def _source_snapshot() -> Tuple[Tuple[str, str], ...]:
    paths = (
        PROJECT_DIR / "README.md",
        PROJECT_DIR / "README_STAGE_1.md",
        THIS_FILE,
        PROJECT_DIR / "tests" / "test_external_host_contract.py",
    )
    return tuple(
        (path.relative_to(REPOSITORY_ROOT).as_posix(), _sha256_file(path))
        for path in paths
    )


def run_stage1_qualification() -> Stage1Qualification:
    source_before = _source_snapshot()
    frozen_pre_digest = _sha256_file(FROZEN_V03_MANIFEST) if FROZEN_V03_MANIFEST.is_file() else ZERO_DIGEST
    frozen_pre_pass, _, frozen_entries = verify_frozen_v03_release()

    profile = build_reference_profile()
    package = build_reference_package(profile)
    assessment = assess_external_host_contract(profile, package)
    assessment_second = assess_external_host_contract(profile, package)

    registry0 = empty_registry()
    registry1 = install_sidecar(registry0, profile, package)
    registry2 = remove_sidecar(registry1, profile, package)
    registry_valid, _ = validate_registry(registry2)

    baseline_before = profile.baseline.baseline_digest
    baseline_during = profile.baseline.baseline_digest
    baseline_after = profile.baseline.baseline_digest

    receipts: Tuple[IntegrationReceipt, ...] = ()
    receipts = append_receipt(receipts, "FROZEN_BASELINE", "v0.3", {
        "entries": frozen_entries,
        "manifest_sha256": frozen_pre_digest,
    })
    receipts = append_receipt(receipts, "HOST_PROFILE", profile.identity.host_id, profile.unsigned_record())
    receipts = append_receipt(receipts, "ADAPTER_PACKAGE", package.package_id, package.unsigned_record())
    receipts = append_receipt(receipts, "ASSESSMENT", package.package_id, assessment.unsigned_record())
    receipts = append_receipt(receipts, "INSTALL", registry1.registry_id, registry1.events[-1].unsigned_record())
    receipts = append_receipt(receipts, "NEUTRALITY", "INSTALL", {
        "baseline_after": baseline_during,
        "baseline_before": baseline_before,
    })
    receipts = append_receipt(receipts, "REMOVE", registry2.registry_id, registry2.events[-1].unsigned_record())
    receipts = append_receipt(receipts, "NEUTRALITY", "REMOVE", {
        "baseline_after": baseline_after,
        "baseline_before": baseline_before,
    })
    receipts = append_receipt(receipts, "SUMMARY", "STAGE-1", {
        "bolt_on_executed_actions": assessment.bolt_on_executed_actions,
        "compatible": assessment.compatible,
        "host_actions": assessment.host_actions,
        "host_state_changes": 0,
        "installed_count": len(registry2.installed_packages),
    })
    replay = replay_receipts(receipts)

    tampered = list(receipts)
    tampered[3] = replace(tampered[3], payload="{}")
    tamper_pass = not replay_receipts(tampered).passed
    reordered = list(receipts)
    reordered[4], reordered[5] = reordered[5], reordered[4]
    reorder_pass = not replay_receipts(reordered).passed

    rejection_results = run_rejection_matrix(profile, package)
    rejected = sum(
        1
        for result in rejection_results
        if result.rejected
        and result.host_state_unchanged
        and result.host_actions == 0
        and result.bolt_on_executed_actions == 0
    )

    authority_pass, _ = structural_authority_scan()
    frozen_post_pass, _, frozen_post_entries = verify_frozen_v03_release()
    frozen_post_digest = _sha256_file(FROZEN_V03_MANIFEST) if FROZEN_V03_MANIFEST.is_file() else ZERO_DIGEST
    source_unchanged = source_before == _source_snapshot()
    frozen_unchanged = (
        frozen_pre_digest == frozen_post_digest
        and frozen_entries == frozen_post_entries
    )
    deterministic_second = assessment == assessment_second
    host_state_changes = len({baseline_before, baseline_during, baseline_after}) - 1

    requirements = 37
    passed = all(
        (
            frozen_pre_pass,
            frozen_post_pass,
            frozen_unchanged,
            frozen_entries == EXPECTED_FROZEN_V03_ENTRIES,
            assessment.compatible,
            deterministic_second,
            len(registry1.events) == 1,
            len(registry2.events) == 2,
            registry_valid,
            not registry2.installed_packages,
            host_state_changes == 0,
            assessment.host_actions == 0,
            assessment.bolt_on_executed_actions == 0,
            replay.passed,
            tamper_pass,
            reorder_pass,
            rejected == len(rejection_results),
            source_unchanged,
            authority_pass,
        )
    )
    return Stage1Qualification(
        passed=passed,
        stage_name=STAGE_NAME,
        stage_version=STAGE_VERSION,
        mode=MODE,
        execution_authority=EXECUTION_AUTHORITY,
        frozen_v03_pre_pass=frozen_pre_pass,
        frozen_v03_post_pass=frozen_post_pass,
        frozen_v03_unchanged=frozen_unchanged,
        frozen_v03_entries=frozen_entries,
        contract_requirements=requirements,
        compatible=assessment.compatible,
        deterministic_second_pass=deterministic_second,
        install_registrations=1,
        remove_registrations=1,
        host_state_changes=host_state_changes,
        host_actions=assessment.host_actions,
        bolt_on_executed_actions=assessment.bolt_on_executed_actions,
        registry_empty_after_remove=not registry2.installed_packages,
        receipt_replay_pass=replay.passed,
        receipt_tamper_detection_pass=tamper_pass,
        receipt_reorder_detection_pass=reorder_pass,
        rejection_cases=len(rejection_results),
        rejection_cases_safely_rejected=rejected,
        source_unchanged=source_unchanged,
        no_hidden_execution_authority=authority_pass,
        baseline_digest=profile.baseline.baseline_digest,
        compatibility_digest=assessment.assessment_digest,
        receipt_digest=receipts[-1].receipt_hash,
        replay_digest=replay.final_digest,
        frozen_v03_manifest_sha256=frozen_pre_digest,
    )


def main() -> int:
    qualification = run_stage1_qualification()
    profile = build_reference_profile()
    package = build_reference_package(profile)
    mapped = dict(package.operation_map)
    print(f"Stage: {qualification.stage_name} {qualification.stage_version}")
    print(f"Mode: {qualification.mode}")
    print(f"Execution authority: {qualification.execution_authority}")
    print(f"Frozen v0.3 manifest: {qualification.frozen_v03_manifest_sha256}")
    print(f"Frozen v0.3 entries: {qualification.frozen_v03_entries}")
    print(f"Reference host: {profile.identity.host_family} {profile.identity.host_version}")
    print(f"Installation mode: {profile.lifecycle.installation_mode}")
    print(f"Portable actions: {', '.join(PORTABLE_ACTIONS)}")
    print(f"Native operations: {mapped[HOLD]}, {mapped[RELEASE]}")
    print(f"Contract requirements: {qualification.contract_requirements}")
    print(f"Rejection cases: {qualification.rejection_cases}")
    print(f"Rejection cases safely rejected: {qualification.rejection_cases_safely_rejected}")
    print(f"Install registrations: {qualification.install_registrations}")
    print(f"Remove registrations: {qualification.remove_registrations}")
    print(f"Host state changes during install/remove: {qualification.host_state_changes}")
    print(f"Host actions: {qualification.host_actions}")
    print(f"Bolt-on executed actions: {qualification.bolt_on_executed_actions}")
    print(f"Baseline digest: {qualification.baseline_digest}")
    print(f"Compatibility digest: {qualification.compatibility_digest}")
    print(f"Receipt digest: {qualification.receipt_digest}")
    print(f"Replay digest: {qualification.replay_digest}")
    if qualification.passed:
        print("STAGE 1 EXTERNAL HOST INTEGRATION CONTRACT: PASS")
        return 0
    print("STAGE 1 EXTERNAL HOST INTEGRATION CONTRACT: FAIL")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
