#!/usr/bin/env python3
"""Live host substitution for Bolt-On Demonstrator v0.3, Stage 4.

Stage 4 attaches one portable governance campaign to two materially different
live host fixtures in sequence. The bolt-on observes and projects only. Exact
one-use execution permits are consumed by separate host-owned boundary
functions:

* the lease-queue host executes native SUSPEND for portable HOLD;
* the workflow host executes native RESUME for portable RELEASE.

The source host is explicitly detached, a portable HELD checkpoint is frozen,
a substitution ticket binds that checkpoint to the prepared target host, and
the target adapter is attached before RELEASE. The target host then continues
under its own ordinary rules after the bolt-on detaches.

No adapter exposes execute/apply/dispatch/mutate_host. SHA-256 values are exact
integrity bindings for this demonstrator, not production identity signatures.
"""

from __future__ import annotations

import ast
import hashlib
import importlib.util
import json
from dataclasses import dataclass, replace
from pathlib import Path
import sys
from typing import Iterable, Sequence, Tuple

sys.dont_write_bytecode = True

STAGE_NAME = "LIVE HOST SUBSTITUTION"
STAGE_VERSION = "0.3.4"
MODE = "LIVE_HOST_SUBSTITUTION"
BOLT_ON_EXECUTION_AUTHORITY = "NONE"
EXECUTION_BOUNDARY = "HOST_BOUNDARY_ONLY"
ZERO_DIGEST = "0" * 64

QUEUE_HOST_ID = "QUEUE-HOST-A"
WORKFLOW_HOST_ID = "WORKFLOW-HOST-B"
SUBJECT_ID = "TASK-7"
PORTABLE_HELD = "HELD"

EXPECTED_STAGE1_SOURCE_SHA256 = (
    "fe8b138db0069f1ac4a7832fd0f63d5ae30021cdfd5244e2476f8b3b52a4bbb9"
)
EXPECTED_STAGE2_SOURCE_SHA256 = (
    "44801c04e6b3765387bfc4e4b7fb8d71f2ebfc3534c67cc428d778d412c8c03a"
)
EXPECTED_WORKFLOW_HOST_SOURCE_SHA256 = (
    "c940594a409fe7b159ac5c8843ea00100279f754a3db6911662dbc9553222847"
)
EXPECTED_STAGE3_SOURCE_SHA256 = (
    "4c2d4cebbaf50591386fe68a9d0da7448a0d2c8fe89c0d69851389a370eacb98"
)

THIS_FILE = Path(__file__).resolve()
PROJECT_DIR = THIS_FILE.parents[1]
REPOSITORY_ROOT = THIS_FILE.parents[3]
CONTRACT_PATH = PROJECT_DIR / "portability" / "portable_adapter_contract.py"
STAGE2_PATH = PROJECT_DIR / "portability" / "second_independent_host.py"
STAGE3_PATH = PROJECT_DIR / "portability" / "cross_host_replay.py"
WORKFLOW_HOST_PATH = PROJECT_DIR / "hosts" / "workflow_state_host.py"
QUEUE_HOST_PATH = PROJECT_DIR / "hosts" / "queue_state_host.py"
FROZEN_V02_ROOT = REPOSITORY_ROOT / "frozen" / "bolt_on" / "v0.2"


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


contract = _load_module("bolt_on_v03_stage1_contract_for_stage4", CONTRACT_PATH)
stage2 = _load_module("bolt_on_v03_stage2_for_stage4", STAGE2_PATH)
stage3 = _load_module("bolt_on_v03_stage3_for_stage4", STAGE3_PATH)
workflow_host = stage2.workflow_host
queue_host = _load_module("bolt_on_v03_live_queue_host", QUEUE_HOST_PATH)


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


def _source_snapshot() -> Tuple[Tuple[str, str], ...]:
    return tuple(
        (path.relative_to(REPOSITORY_ROOT).as_posix(), _sha256_file(path))
        for path in (
            CONTRACT_PATH,
            STAGE2_PATH,
            STAGE3_PATH,
            WORKFLOW_HOST_PATH,
            QUEUE_HOST_PATH,
            THIS_FILE,
        )
    )


@dataclass(frozen=True)
class QueueRuntime:
    commands: Tuple[object, ...]
    run: object
    consumed_permit_ids: Tuple[str, ...]


@dataclass(frozen=True)
class WorkflowRuntime:
    commands: Tuple[object, ...]
    run: object
    consumed_permit_ids: Tuple[str, ...]


@dataclass(frozen=True)
class HostExecutionPermit:
    permit_id: str
    issuer: str
    session_digest: str
    host_id: str
    adapter_identity_digest: str
    request_digest: str
    projection_digest: str
    action: str
    host_operation: str
    subject_id: str
    expected_native_state: str
    valid_epoch: int
    max_uses: int
    permit_hash: str

    def unsigned_record(self) -> dict[str, object]:
        return {
            "action": self.action,
            "adapter_identity_digest": self.adapter_identity_digest,
            "expected_native_state": self.expected_native_state,
            "host_id": self.host_id,
            "host_operation": self.host_operation,
            "issuer": self.issuer,
            "max_uses": self.max_uses,
            "permit_id": self.permit_id,
            "projection_digest": self.projection_digest,
            "request_digest": self.request_digest,
            "session_digest": self.session_digest,
            "subject_id": self.subject_id,
            "valid_epoch": self.valid_epoch,
        }

    def canonical_line(self) -> str:
        return _canonical_json({**self.unsigned_record(), "permit_hash": self.permit_hash})


@dataclass(frozen=True)
class HostExecutionOutcome:
    host_id: str
    permit_id: str
    action: str
    host_operation: str
    subject_id: str
    native_state_before: str
    native_state_after: str
    native_version_before: int
    native_version_after: int
    executed: bool
    reason_code: str
    host_run_digest: str
    outcome_digest: str

    def unsigned_record(self) -> dict[str, object]:
        return {
            "action": self.action,
            "executed": self.executed,
            "host_id": self.host_id,
            "host_operation": self.host_operation,
            "host_run_digest": self.host_run_digest,
            "native_state_after": self.native_state_after,
            "native_state_before": self.native_state_before,
            "native_version_after": self.native_version_after,
            "native_version_before": self.native_version_before,
            "permit_id": self.permit_id,
            "reason_code": self.reason_code,
            "subject_id": self.subject_id,
        }

    def canonical_line(self) -> str:
        return _canonical_json({**self.unsigned_record(), "outcome_digest": self.outcome_digest})


@dataclass(frozen=True)
class PortableCheckpoint:
    checkpoint_id: str
    session_digest: str
    subject_id: str
    portable_state: str
    source_host_id: str
    source_run_digest: str
    source_outcome_digest: str
    action_history: Tuple[str, ...]
    checkpoint_digest: str

    def unsigned_record(self) -> dict[str, object]:
        return {
            "action_history": list(self.action_history),
            "checkpoint_id": self.checkpoint_id,
            "portable_state": self.portable_state,
            "session_digest": self.session_digest,
            "source_host_id": self.source_host_id,
            "source_outcome_digest": self.source_outcome_digest,
            "source_run_digest": self.source_run_digest,
            "subject_id": self.subject_id,
        }

    def canonical_line(self) -> str:
        return _canonical_json(
            {**self.unsigned_record(), "checkpoint_digest": self.checkpoint_digest}
        )


@dataclass(frozen=True)
class SubstitutionTicket:
    ticket_id: str
    issuer: str
    session_digest: str
    subject_id: str
    source_host_id: str
    target_host_id: str
    checkpoint_digest: str
    source_detach_digest: str
    target_ready_digest: str
    valid_epoch: int
    ticket_hash: str

    def unsigned_record(self) -> dict[str, object]:
        return {
            "checkpoint_digest": self.checkpoint_digest,
            "issuer": self.issuer,
            "session_digest": self.session_digest,
            "source_detach_digest": self.source_detach_digest,
            "source_host_id": self.source_host_id,
            "subject_id": self.subject_id,
            "target_host_id": self.target_host_id,
            "target_ready_digest": self.target_ready_digest,
            "ticket_id": self.ticket_id,
            "valid_epoch": self.valid_epoch,
        }

    def canonical_line(self) -> str:
        return _canonical_json({**self.unsigned_record(), "ticket_hash": self.ticket_hash})


@dataclass(frozen=True)
class HostAttachmentEvent:
    sequence: int
    event_type: str
    host_id: str
    adapter_identity_digest: str
    session_digest: str
    checkpoint_digest: str
    prior_event_digest: str
    event_digest: str

    def unsigned_record(self) -> dict[str, object]:
        return {
            "adapter_identity_digest": self.adapter_identity_digest,
            "checkpoint_digest": self.checkpoint_digest,
            "event_type": self.event_type,
            "host_id": self.host_id,
            "prior_event_digest": self.prior_event_digest,
            "sequence": self.sequence,
            "session_digest": self.session_digest,
        }

    def canonical_line(self) -> str:
        return _canonical_json({**self.unsigned_record(), "event_digest": self.event_digest})


@dataclass(frozen=True)
class AttachmentReplay:
    passed: bool
    active_host_id: str
    host_sequence: Tuple[str, ...]
    substitutions: int
    final_digest: str
    checked_events: int
    first_error: str


@dataclass(frozen=True)
class CampaignReceipt:
    receipt_id: int
    kind: str
    subject: str
    payload: str
    prior_hash: str
    receipt_hash: str


@dataclass(frozen=True)
class CampaignReplay:
    passed: bool
    final_digest: str
    checked_receipts: int
    host_sequence: Tuple[str, ...]
    actions: Tuple[str, ...]
    executed_host_actions: int
    bolt_on_executed_actions: int
    final_native_state: str
    first_error: str


@dataclass(frozen=True)
class LiveSubstitutionReport:
    session_digest: str
    queue_adapter_report: object
    workflow_adapter_report: object
    queue_runtime_before: QueueRuntime
    queue_runtime_after: QueueRuntime
    workflow_runtime_before: WorkflowRuntime
    workflow_runtime_after: WorkflowRuntime
    workflow_final_run: object
    queue_permit: HostExecutionPermit
    workflow_permit: HostExecutionPermit
    queue_outcome: HostExecutionOutcome
    workflow_outcome: HostExecutionOutcome
    checkpoint: PortableCheckpoint
    substitution_ticket: SubstitutionTicket
    attachment_events: Tuple[HostAttachmentEvent, ...]
    attachment_replay: AttachmentReplay
    receipts: Tuple[CampaignReceipt, ...]
    replay: CampaignReplay
    campaign_digest: str
    executed_host_actions: int
    bolt_on_executed_actions: int
    substitutions: int


@dataclass(frozen=True)
class Stage4Qualification:
    passed: bool
    stage_name: str
    stage_version: str
    mode: str
    bolt_on_execution_authority: str
    execution_boundary: str
    frozen_v02_pre_pass: bool
    frozen_v02_post_pass: bool
    frozen_v02_unchanged: bool
    prior_stage_sources_bound: bool
    host_independence_pass: bool
    sources_unchanged: bool
    inputs_unchanged: bool
    deterministic_second_pass: bool
    source_host_hold_executed: bool
    source_host_detached: bool
    checkpoint_pass: bool
    substitution_ticket_pass: bool
    target_host_attached: bool
    target_host_release_executed: bool
    target_host_detached: bool
    target_host_continuation_pass: bool
    attachment_replay_pass: bool
    campaign_replay_pass: bool
    forged_permit_rejected: bool
    reused_permit_rejected: bool
    tampered_checkpoint_rejected: bool
    tampered_ticket_rejected: bool
    receipt_tamper_detection_pass: bool
    receipt_reorder_detection_pass: bool
    no_hidden_execution_authority: bool
    executed_host_actions: int
    bolt_on_executed_actions: int
    substitutions: int
    host_sequence: Tuple[str, ...]
    queue_held_run_digest: str
    workflow_resumed_run_digest: str
    workflow_final_run_digest: str
    campaign_digest: str
    replay_digest: str
    frozen_v02_manifest_sha256: str


class WorkflowLiveAdapter(contract.PortableHostAdapter):
    """Read/project-only adapter for the independent workflow host."""

    def __init__(self) -> None:
        self._identity = contract.build_adapter_identity(
            adapter_id="LIVE-WORKFLOW-STATE-ADAPTER",
            adapter_version=STAGE_VERSION,
            host_family="VERSIONED_FINITE_STATE_WORKFLOW",
            host_instance=WORKFLOW_HOST_ID,
            capabilities=contract.SUPPORTED_ACTIONS,
        )

    def identity(self):
        return self._identity

    def normalize_event(self, raw_event: object):
        if not isinstance(raw_event, workflow_host.WorkflowEvent):
            raise TypeError("workflow live adapter requires WorkflowEvent input")
        return contract.build_canonical_event(
            self._identity,
            sequence=raw_event.sequence,
            event_id=f"WORKFLOW:{raw_event.sequence}:{raw_event.command_id}",
            event_type=raw_event.event_type,
            subject_id=raw_event.task_id,
            state_before=raw_event.state_before,
            state_after=raw_event.state_after,
            attributes=(
                ("operation", raw_event.operation),
                ("reason", raw_event.reason),
                ("revision_after", raw_event.revision_after),
                ("revision_before", raw_event.revision_before),
            ),
        )

    def project_action(self, request, event):
        if event.event_type != workflow_host.APPLIED:
            return contract.build_projection(
                self._identity, request, event, host_operation="",
                would_dispatch=False, executed=False,
                reason_code="SOURCE_EVENT_NOT_APPLIED",
            )
        operation = {
            contract.HOLD: workflow_host.PAUSE,
            contract.RELEASE: workflow_host.RESUME,
        }[request.action]
        return contract.build_projection(
            self._identity, request, event, host_operation=operation,
            would_dispatch=True, executed=False,
            reason_code="LIVE_WORKFLOW_PROJECTION_READY",
        )


class QueueLiveAdapter(contract.PortableHostAdapter):
    """Read/project-only adapter for the independent queue host."""

    def __init__(self) -> None:
        self._identity = contract.build_adapter_identity(
            adapter_id="LIVE-QUEUE-STATE-ADAPTER",
            adapter_version=STAGE_VERSION,
            host_family="DETERMINISTIC_LEASE_QUEUE",
            host_instance=QUEUE_HOST_ID,
            capabilities=contract.SUPPORTED_ACTIONS,
        )

    def identity(self):
        return self._identity

    def normalize_event(self, raw_event: object):
        if not isinstance(raw_event, queue_host.QueueEvent):
            raise TypeError("queue live adapter requires QueueEvent input")
        return contract.build_canonical_event(
            self._identity,
            sequence=raw_event.sequence,
            event_id=f"QUEUE:{raw_event.sequence}:{raw_event.command_id}",
            event_type=raw_event.event_type,
            subject_id=raw_event.item_id,
            state_before=raw_event.phase_before,
            state_after=raw_event.phase_after,
            attributes=(
                ("operation", raw_event.operation),
                ("reason", raw_event.reason),
                ("version_after", raw_event.version_after),
                ("version_before", raw_event.version_before),
            ),
        )

    def project_action(self, request, event):
        if event.event_type != queue_host.APPLIED:
            return contract.build_projection(
                self._identity,
                request,
                event,
                host_operation="",
                would_dispatch=False,
                executed=False,
                reason_code="SOURCE_EVENT_NOT_APPLIED",
            )
        operation = {
            contract.HOLD: queue_host.SUSPEND,
            contract.RELEASE: queue_host.CONTINUE,
        }[request.action]
        return contract.build_projection(
            self._identity,
            request,
            event,
            host_operation=operation,
            would_dispatch=True,
            executed=False,
            reason_code="LIVE_QUEUE_PROJECTION_READY",
        )


def issue_execution_permit(
    *,
    session_digest: str,
    host_id: str,
    identity: object,
    request: object,
    projection: object,
    expected_native_state: str,
    valid_epoch: int,
    issuer: str = "LOCAL_STAGE4_HOST_AUTHORITY",
) -> HostExecutionPermit:
    valid_epoch = _exact_int(valid_epoch, "valid_epoch")
    if not _is_digest(session_digest):
        raise ValueError("session_digest must be a lowercase SHA-256 digest")
    valid_identity, identity_reason = contract.validate_adapter_identity(identity)
    if not valid_identity:
        raise ValueError(f"invalid adapter identity: {identity_reason}")
    valid_request, request_reason = contract.validate_action_request(request)
    if not valid_request:
        raise ValueError(f"invalid request: {request_reason}")
    if projection.executed or not projection.would_dispatch:
        raise ValueError("projection must be non-executing and dispatchable")
    seed = {
        "action": request.action,
        "adapter_identity_digest": identity.identity_digest,
        "expected_native_state": _nonempty_text(
            expected_native_state, "expected_native_state"
        ).upper(),
        "host_id": _nonempty_text(host_id, "host_id"),
        "host_operation": _nonempty_text(projection.host_operation, "host_operation"),
        "issuer": _nonempty_text(issuer, "issuer"),
        "max_uses": 1,
        "projection_digest": projection.projection_digest,
        "request_digest": request.request_digest,
        "session_digest": session_digest,
        "subject_id": request.subject_id,
        "valid_epoch": valid_epoch,
    }
    permit_id = "HP-" + _digest_json(seed)[:24].upper()
    unsigned = {**seed, "permit_id": permit_id}
    return HostExecutionPermit(
        permit_id=permit_id,
        issuer=seed["issuer"],
        session_digest=session_digest,
        host_id=seed["host_id"],
        adapter_identity_digest=identity.identity_digest,
        request_digest=request.request_digest,
        projection_digest=projection.projection_digest,
        action=request.action,
        host_operation=projection.host_operation,
        subject_id=request.subject_id,
        expected_native_state=seed["expected_native_state"],
        valid_epoch=valid_epoch,
        max_uses=1,
        permit_hash=_digest_json(unsigned),
    )


def validate_execution_permit(permit: HostExecutionPermit) -> Tuple[bool, str]:
    if not isinstance(permit, HostExecutionPermit):
        return False, "PERMIT_TYPE_INVALID"
    try:
        if permit.max_uses != 1 or isinstance(permit.max_uses, bool):
            return False, "PERMIT_USE_BUDGET_INVALID"
        if not _is_digest(permit.session_digest):
            return False, "PERMIT_SESSION_INVALID"
        for digest in (
            permit.adapter_identity_digest,
            permit.request_digest,
            permit.projection_digest,
        ):
            if not _is_digest(digest):
                return False, "PERMIT_BINDING_DIGEST_INVALID"
        _exact_int(permit.valid_epoch, "valid_epoch")
        for name in (
            "permit_id",
            "issuer",
            "host_id",
            "action",
            "host_operation",
            "subject_id",
            "expected_native_state",
        ):
            _nonempty_text(getattr(permit, name), name)
    except (TypeError, ValueError):
        return False, "PERMIT_FIELDS_INVALID"
    if permit.action not in contract.SUPPORTED_ACTIONS:
        return False, "PERMIT_ACTION_UNSUPPORTED"
    if permit.permit_hash != _digest_json(permit.unsigned_record()):
        return False, "PERMIT_HASH_MISMATCH"
    return True, "VALID"


def _build_outcome(
    *,
    host_id: str,
    permit_id: str,
    action: str,
    host_operation: str,
    subject_id: str,
    native_state_before: str,
    native_state_after: str,
    native_version_before: int,
    native_version_after: int,
    executed: bool,
    reason_code: str,
    host_run_digest: str,
) -> HostExecutionOutcome:
    unsigned = {
        "action": action,
        "executed": executed,
        "host_id": host_id,
        "host_operation": host_operation,
        "host_run_digest": host_run_digest,
        "native_state_after": native_state_after,
        "native_state_before": native_state_before,
        "native_version_after": native_version_after,
        "native_version_before": native_version_before,
        "permit_id": permit_id,
        "reason_code": reason_code,
        "subject_id": subject_id,
    }
    return HostExecutionOutcome(
        host_id=host_id,
        permit_id=permit_id,
        action=action,
        host_operation=host_operation,
        subject_id=subject_id,
        native_state_before=native_state_before,
        native_state_after=native_state_after,
        native_version_before=native_version_before,
        native_version_after=native_version_after,
        executed=executed,
        reason_code=reason_code,
        host_run_digest=host_run_digest,
        outcome_digest=_digest_json(unsigned),
    )


def validate_execution_outcome(outcome: HostExecutionOutcome) -> Tuple[bool, str]:
    if not isinstance(outcome, HostExecutionOutcome):
        return False, "OUTCOME_TYPE_INVALID"
    if not _is_digest(outcome.host_run_digest):
        return False, "OUTCOME_HOST_DIGEST_INVALID"
    if outcome.outcome_digest != _digest_json(outcome.unsigned_record()):
        return False, "OUTCOME_DIGEST_MISMATCH"
    return True, "VALID"


def make_queue_runtime(commands: Sequence[object]) -> QueueRuntime:
    command_tuple = tuple(commands)
    return QueueRuntime(command_tuple, queue_host.run_queue(command_tuple), ())


def make_workflow_runtime(commands: Sequence[object]) -> WorkflowRuntime:
    command_tuple = tuple(commands)
    return WorkflowRuntime(command_tuple, workflow_host.run_workflow(command_tuple), ())


def _permit_binding_error(
    permit: HostExecutionPermit,
    *,
    host_id: str,
    identity: object,
    request: object,
    projection: object,
    current_epoch: int,
    consumed_ids: Sequence[str],
) -> str:
    valid, reason = validate_execution_permit(permit)
    if not valid:
        return reason
    expected_pairs = (
        (permit.host_id, host_id, "PERMIT_HOST_MISMATCH"),
        (
            permit.adapter_identity_digest,
            identity.identity_digest,
            "PERMIT_ADAPTER_MISMATCH",
        ),
        (permit.request_digest, request.request_digest, "PERMIT_REQUEST_MISMATCH"),
        (
            permit.projection_digest,
            projection.projection_digest,
            "PERMIT_PROJECTION_MISMATCH",
        ),
        (permit.action, request.action, "PERMIT_ACTION_MISMATCH"),
        (permit.host_operation, projection.host_operation, "PERMIT_OPERATION_MISMATCH"),
        (permit.subject_id, request.subject_id, "PERMIT_SUBJECT_MISMATCH"),
        (permit.valid_epoch, current_epoch, "PERMIT_EPOCH_MISMATCH"),
    )
    for actual, expected, mismatch in expected_pairs:
        if actual != expected:
            return mismatch
    if permit.permit_id in tuple(consumed_ids):
        return "PERMIT_ALREADY_CONSUMED"
    if projection.executed:
        return "PROJECTION_CLAIMS_EXECUTION"
    if not projection.would_dispatch:
        return "PROJECTION_NOT_DISPATCHABLE"
    return "NONE"


def execute_queue_host_boundary(
    runtime: QueueRuntime,
    *,
    identity: object,
    request: object,
    projection: object,
    permit: HostExecutionPermit,
    current_epoch: int,
) -> Tuple[QueueRuntime, HostExecutionOutcome]:
    current_epoch = _exact_int(current_epoch, "current_epoch")
    error = _permit_binding_error(
        permit,
        host_id=QUEUE_HOST_ID,
        identity=identity,
        request=request,
        projection=projection,
        current_epoch=current_epoch,
        consumed_ids=runtime.consumed_permit_ids,
    )
    record = next(
        (item for item in runtime.run.final_records if item.item_id == request.subject_id),
        None,
    )
    state = record.phase if record is not None else queue_host.ABSENT
    version = record.version if record is not None else 0
    if error == "NONE" and permit.expected_native_state != state:
        error = "NATIVE_STATE_MISMATCH"
    if error == "NONE" and (
        request.action != contract.HOLD
        or projection.host_operation != queue_host.SUSPEND
    ):
        error = "QUEUE_OPERATION_NOT_AUTHORIZED"
    if error != "NONE":
        return runtime, _build_outcome(
            host_id=QUEUE_HOST_ID,
            permit_id=permit.permit_id,
            action=request.action,
            host_operation=projection.host_operation,
            subject_id=request.subject_id,
            native_state_before=state,
            native_state_after=state,
            native_version_before=version,
            native_version_after=version,
            executed=False,
            reason_code=error,
            host_run_digest=runtime.run.run_digest,
        )
    command = queue_host.QueueCommand(
        f"LIVE-Q-{request.request_id}-{permit.permit_id[-8:]}",
        request.subject_id,
        queue_host.SUSPEND,
        version,
    )
    commands = runtime.commands + (command,)
    run = queue_host.run_queue(commands)
    after = next(item for item in run.final_records if item.item_id == request.subject_id)
    outcome = _build_outcome(
        host_id=QUEUE_HOST_ID,
        permit_id=permit.permit_id,
        action=request.action,
        host_operation=projection.host_operation,
        subject_id=request.subject_id,
        native_state_before=state,
        native_state_after=after.phase,
        native_version_before=version,
        native_version_after=after.version,
        executed=True,
        reason_code="QUEUE_HOST_BOUNDARY_EXECUTED",
        host_run_digest=run.run_digest,
    )
    return QueueRuntime(
        commands,
        run,
        runtime.consumed_permit_ids + (permit.permit_id,),
    ), outcome


def execute_workflow_host_boundary(
    runtime: WorkflowRuntime,
    *,
    identity: object,
    request: object,
    projection: object,
    permit: HostExecutionPermit,
    current_epoch: int,
) -> Tuple[WorkflowRuntime, HostExecutionOutcome]:
    current_epoch = _exact_int(current_epoch, "current_epoch")
    error = _permit_binding_error(
        permit,
        host_id=WORKFLOW_HOST_ID,
        identity=identity,
        request=request,
        projection=projection,
        current_epoch=current_epoch,
        consumed_ids=runtime.consumed_permit_ids,
    )
    record = next(
        (item for item in runtime.run.final_records if item.task_id == request.subject_id),
        None,
    )
    state = record.state if record is not None else workflow_host.ABSENT
    revision = record.revision if record is not None else 0
    if error == "NONE" and permit.expected_native_state != state:
        error = "NATIVE_STATE_MISMATCH"
    if error == "NONE" and (
        request.action != contract.RELEASE
        or projection.host_operation != workflow_host.RESUME
    ):
        error = "WORKFLOW_OPERATION_NOT_AUTHORIZED"
    if error != "NONE":
        return runtime, _build_outcome(
            host_id=WORKFLOW_HOST_ID,
            permit_id=permit.permit_id,
            action=request.action,
            host_operation=projection.host_operation,
            subject_id=request.subject_id,
            native_state_before=state,
            native_state_after=state,
            native_version_before=revision,
            native_version_after=revision,
            executed=False,
            reason_code=error,
            host_run_digest=runtime.run.run_digest,
        )
    command = workflow_host.WorkflowCommand(
        f"LIVE-W-{request.request_id}-{permit.permit_id[-8:]}",
        request.subject_id,
        workflow_host.RESUME,
        revision,
    )
    commands = runtime.commands + (command,)
    run = workflow_host.run_workflow(commands)
    after = next(item for item in run.final_records if item.task_id == request.subject_id)
    outcome = _build_outcome(
        host_id=WORKFLOW_HOST_ID,
        permit_id=permit.permit_id,
        action=request.action,
        host_operation=projection.host_operation,
        subject_id=request.subject_id,
        native_state_before=state,
        native_state_after=after.state,
        native_version_before=revision,
        native_version_after=after.revision,
        executed=True,
        reason_code="WORKFLOW_HOST_BOUNDARY_EXECUTED",
        host_run_digest=run.run_digest,
    )
    return WorkflowRuntime(
        commands,
        run,
        runtime.consumed_permit_ids + (permit.permit_id,),
    ), outcome


def build_checkpoint(
    *, session_digest: str, outcome: HostExecutionOutcome
) -> PortableCheckpoint:
    if not _is_digest(session_digest):
        raise ValueError("session_digest must be a lowercase SHA-256 digest")
    valid, reason = validate_execution_outcome(outcome)
    if not valid or not outcome.executed:
        raise ValueError(f"outcome is not checkpointable: {reason}")
    if (
        outcome.host_id != QUEUE_HOST_ID
        or outcome.action != contract.HOLD
        or outcome.native_state_after != queue_host.HELD
    ):
        raise ValueError("checkpoint requires executed queue HOLD")
    seed = {
        "action_history": [contract.HOLD],
        "portable_state": PORTABLE_HELD,
        "session_digest": session_digest,
        "source_host_id": outcome.host_id,
        "source_outcome_digest": outcome.outcome_digest,
        "source_run_digest": outcome.host_run_digest,
        "subject_id": outcome.subject_id,
    }
    checkpoint_id = "CP-" + _digest_json(seed)[:24].upper()
    unsigned = {**seed, "checkpoint_id": checkpoint_id}
    return PortableCheckpoint(
        checkpoint_id=checkpoint_id,
        session_digest=session_digest,
        subject_id=outcome.subject_id,
        portable_state=PORTABLE_HELD,
        source_host_id=outcome.host_id,
        source_run_digest=outcome.host_run_digest,
        source_outcome_digest=outcome.outcome_digest,
        action_history=(contract.HOLD,),
        checkpoint_digest=_digest_json(unsigned),
    )


def validate_checkpoint(checkpoint: PortableCheckpoint) -> Tuple[bool, str]:
    if not isinstance(checkpoint, PortableCheckpoint):
        return False, "CHECKPOINT_TYPE_INVALID"
    if (
        checkpoint.portable_state != PORTABLE_HELD
        or checkpoint.action_history != (contract.HOLD,)
        or checkpoint.source_host_id != QUEUE_HOST_ID
    ):
        return False, "CHECKPOINT_SEMANTICS_INVALID"
    for digest in (
        checkpoint.session_digest,
        checkpoint.source_run_digest,
        checkpoint.source_outcome_digest,
    ):
        if not _is_digest(digest):
            return False, "CHECKPOINT_DIGEST_FIELD_INVALID"
    if checkpoint.checkpoint_digest != _digest_json(checkpoint.unsigned_record()):
        return False, "CHECKPOINT_DIGEST_MISMATCH"
    return True, "VALID"


def build_attachment_event(
    *,
    sequence: int,
    event_type: str,
    host_id: str,
    adapter_identity_digest: str,
    session_digest: str,
    checkpoint_digest: str = ZERO_DIGEST,
    prior_event_digest: str = ZERO_DIGEST,
) -> HostAttachmentEvent:
    sequence = _exact_int(sequence, "sequence", minimum=1)
    event_type = _nonempty_text(event_type, "event_type").upper()
    if event_type not in ("ATTACH", "DETACH"):
        raise ValueError("unsupported attachment event")
    for name, digest in (
        ("adapter_identity_digest", adapter_identity_digest),
        ("session_digest", session_digest),
        ("checkpoint_digest", checkpoint_digest),
        ("prior_event_digest", prior_event_digest),
    ):
        if not _is_digest(digest):
            raise ValueError(f"{name} must be a lowercase SHA-256 digest")
    unsigned = {
        "adapter_identity_digest": adapter_identity_digest,
        "checkpoint_digest": checkpoint_digest,
        "event_type": event_type,
        "host_id": _nonempty_text(host_id, "host_id"),
        "prior_event_digest": prior_event_digest,
        "sequence": sequence,
        "session_digest": session_digest,
    }
    return HostAttachmentEvent(
        sequence=sequence,
        event_type=event_type,
        host_id=unsigned["host_id"],
        adapter_identity_digest=adapter_identity_digest,
        session_digest=session_digest,
        checkpoint_digest=checkpoint_digest,
        prior_event_digest=prior_event_digest,
        event_digest=_digest_json(unsigned),
    )


def replay_attachment_events(
    events: Sequence[HostAttachmentEvent],
) -> AttachmentReplay:
    active = ""
    active_adapter = ""
    session = ""
    host_sequence: list[str] = []
    prior = ZERO_DIGEST
    substitutions = 0
    for expected, event in enumerate(tuple(events), start=1):
        if not isinstance(event, HostAttachmentEvent):
            return AttachmentReplay(False, active, tuple(host_sequence), substitutions, prior, expected - 1, "ATTACHMENT_TYPE_INVALID")
        if event.sequence != expected:
            return AttachmentReplay(False, active, tuple(host_sequence), substitutions, prior, expected - 1, "ATTACHMENT_SEQUENCE_MISMATCH")
        if event.prior_event_digest != prior:
            return AttachmentReplay(False, active, tuple(host_sequence), substitutions, prior, expected - 1, "ATTACHMENT_PRIOR_DIGEST_MISMATCH")
        if event.event_digest != _digest_json(event.unsigned_record()):
            return AttachmentReplay(False, active, tuple(host_sequence), substitutions, prior, expected - 1, "ATTACHMENT_DIGEST_MISMATCH")
        if not session:
            session = event.session_digest
        elif event.session_digest != session:
            return AttachmentReplay(False, active, tuple(host_sequence), substitutions, prior, expected - 1, "ATTACHMENT_SESSION_MISMATCH")
        if event.event_type == "ATTACH":
            if active:
                return AttachmentReplay(False, active, tuple(host_sequence), substitutions, prior, expected - 1, "ATTACH_WITH_ACTIVE_HOST")
            if not host_sequence and event.checkpoint_digest != ZERO_DIGEST:
                return AttachmentReplay(False, active, tuple(host_sequence), substitutions, prior, expected - 1, "INITIAL_ATTACH_CHECKPOINT_PRESENT")
            if host_sequence and event.checkpoint_digest == ZERO_DIGEST:
                return AttachmentReplay(False, active, tuple(host_sequence), substitutions, prior, expected - 1, "SUBSTITUTION_CHECKPOINT_MISSING")
            active = event.host_id
            active_adapter = event.adapter_identity_digest
            if host_sequence:
                substitutions += 1
            host_sequence.append(event.host_id)
        else:
            if active != event.host_id:
                return AttachmentReplay(False, active, tuple(host_sequence), substitutions, prior, expected - 1, "DETACH_HOST_MISMATCH")
            if event.adapter_identity_digest != active_adapter:
                return AttachmentReplay(False, active, tuple(host_sequence), substitutions, prior, expected - 1, "DETACH_ADAPTER_MISMATCH")
            if event.checkpoint_digest == ZERO_DIGEST:
                return AttachmentReplay(False, active, tuple(host_sequence), substitutions, prior, expected - 1, "DETACH_CHECKPOINT_MISSING")
            active = ""
            active_adapter = ""
        prior = event.event_digest
    return AttachmentReplay(True, active, tuple(host_sequence), substitutions, prior, len(tuple(events)), "NONE")


def issue_substitution_ticket(
    *,
    session_digest: str,
    checkpoint: PortableCheckpoint,
    source_detach_digest: str,
    target_ready_digest: str,
    valid_epoch: int,
    issuer: str = "LOCAL_STAGE4_SUBSTITUTION_AUTHORITY",
) -> SubstitutionTicket:
    valid, reason = validate_checkpoint(checkpoint)
    if not valid:
        raise ValueError(f"invalid checkpoint: {reason}")
    if checkpoint.session_digest != session_digest:
        raise ValueError("checkpoint session mismatch")
    for name, digest in (
        ("source_detach_digest", source_detach_digest),
        ("target_ready_digest", target_ready_digest),
    ):
        if not _is_digest(digest):
            raise ValueError(f"{name} must be a lowercase SHA-256 digest")
    valid_epoch = _exact_int(valid_epoch, "valid_epoch")
    seed = {
        "checkpoint_digest": checkpoint.checkpoint_digest,
        "issuer": _nonempty_text(issuer, "issuer"),
        "session_digest": session_digest,
        "source_detach_digest": source_detach_digest,
        "source_host_id": QUEUE_HOST_ID,
        "subject_id": checkpoint.subject_id,
        "target_host_id": WORKFLOW_HOST_ID,
        "target_ready_digest": target_ready_digest,
        "valid_epoch": valid_epoch,
    }
    ticket_id = "ST-" + _digest_json(seed)[:24].upper()
    unsigned = {**seed, "ticket_id": ticket_id}
    return SubstitutionTicket(
        ticket_id=ticket_id,
        issuer=seed["issuer"],
        session_digest=session_digest,
        subject_id=checkpoint.subject_id,
        source_host_id=QUEUE_HOST_ID,
        target_host_id=WORKFLOW_HOST_ID,
        checkpoint_digest=checkpoint.checkpoint_digest,
        source_detach_digest=source_detach_digest,
        target_ready_digest=target_ready_digest,
        valid_epoch=valid_epoch,
        ticket_hash=_digest_json(unsigned),
    )


def validate_substitution_ticket(
    ticket: SubstitutionTicket,
    *,
    checkpoint: PortableCheckpoint,
    source_detach_digest: str,
    target_ready_digest: str,
    current_epoch: int,
) -> Tuple[bool, str]:
    if not isinstance(ticket, SubstitutionTicket):
        return False, "TICKET_TYPE_INVALID"
    valid_checkpoint, checkpoint_reason = validate_checkpoint(checkpoint)
    if not valid_checkpoint:
        return False, checkpoint_reason
    expected_pairs = (
        (ticket.session_digest, checkpoint.session_digest, "TICKET_SESSION_MISMATCH"),
        (ticket.subject_id, checkpoint.subject_id, "TICKET_SUBJECT_MISMATCH"),
        (ticket.source_host_id, QUEUE_HOST_ID, "TICKET_SOURCE_HOST_MISMATCH"),
        (ticket.target_host_id, WORKFLOW_HOST_ID, "TICKET_TARGET_HOST_MISMATCH"),
        (ticket.checkpoint_digest, checkpoint.checkpoint_digest, "TICKET_CHECKPOINT_MISMATCH"),
        (ticket.source_detach_digest, source_detach_digest, "TICKET_DETACH_MISMATCH"),
        (ticket.target_ready_digest, target_ready_digest, "TICKET_TARGET_READY_MISMATCH"),
        (ticket.valid_epoch, current_epoch, "TICKET_EPOCH_MISMATCH"),
    )
    for actual, expected, reason in expected_pairs:
        if actual != expected:
            return False, reason
    if ticket.ticket_hash != _digest_json(ticket.unsigned_record()):
        return False, "TICKET_HASH_MISMATCH"
    return True, "VALID"


def _receipt_hash(
    receipt_id: int, kind: str, subject: str, payload: str, prior_hash: str
) -> str:
    return _sha256_bytes(
        "|".join((str(receipt_id), kind, subject, payload, prior_hash)).encode("utf-8")
    )


def _append_receipt(
    receipts: list[CampaignReceipt], kind: str, subject: str, payload: str
) -> None:
    prior = receipts[-1].receipt_hash if receipts else ZERO_DIGEST
    receipt_id = len(receipts) + 1
    receipt_hash = _receipt_hash(receipt_id, kind, subject, payload, prior)
    receipts.append(CampaignReceipt(receipt_id, kind, subject, payload, prior, receipt_hash))


def build_campaign_receipts(report: LiveSubstitutionReport) -> Tuple[CampaignReceipt, ...]:
    receipts: list[CampaignReceipt] = []
    _append_receipt(
        receipts,
        "SESSION",
        "OPEN",
        _canonical_json(
            {
                "bolt_on_execution_authority": BOLT_ON_EXECUTION_AUTHORITY,
                "execution_boundary": EXECUTION_BOUNDARY,
                "mode": MODE,
                "session_digest": report.session_digest,
                "stage": STAGE_NAME,
                "version": STAGE_VERSION,
            }
        ),
    )
    attachments = iter(report.attachment_events)
    _append_receipt(receipts, "ATTACHMENT", QUEUE_HOST_ID, next(attachments).canonical_line())
    _append_receipt(receipts, "ADAPTER_REPORT", QUEUE_HOST_ID, report.queue_adapter_report.report_digest)
    _append_receipt(receipts, "REQUEST", contract.HOLD, report.queue_adapter_report.requests[0].canonical_line())
    _append_receipt(receipts, "PROJECTION", queue_host.SUSPEND, report.queue_adapter_report.projections[0].canonical_line())
    _append_receipt(receipts, "EXECUTION_PERMIT", QUEUE_HOST_ID, report.queue_permit.canonical_line())
    _append_receipt(receipts, "HOST_EXECUTION", QUEUE_HOST_ID, report.queue_outcome.canonical_line())
    _append_receipt(receipts, "CHECKPOINT", report.checkpoint.checkpoint_id, report.checkpoint.canonical_line())
    _append_receipt(receipts, "ATTACHMENT", QUEUE_HOST_ID, next(attachments).canonical_line())
    _append_receipt(receipts, "SUBSTITUTION_TICKET", report.substitution_ticket.ticket_id, report.substitution_ticket.canonical_line())
    _append_receipt(
        receipts,
        "TARGET_READY",
        WORKFLOW_HOST_ID,
        _canonical_json(
            {
                "native_state": workflow_host.PAUSED,
                "run_digest": report.workflow_runtime_before.run.run_digest,
                "subject_id": SUBJECT_ID,
            }
        ),
    )
    _append_receipt(receipts, "ATTACHMENT", WORKFLOW_HOST_ID, next(attachments).canonical_line())
    _append_receipt(receipts, "ADAPTER_REPORT", WORKFLOW_HOST_ID, report.workflow_adapter_report.report_digest)
    _append_receipt(receipts, "REQUEST", contract.RELEASE, report.workflow_adapter_report.requests[0].canonical_line())
    _append_receipt(receipts, "PROJECTION", workflow_host.RESUME, report.workflow_adapter_report.projections[0].canonical_line())
    _append_receipt(receipts, "EXECUTION_PERMIT", WORKFLOW_HOST_ID, report.workflow_permit.canonical_line())
    _append_receipt(receipts, "HOST_EXECUTION", WORKFLOW_HOST_ID, report.workflow_outcome.canonical_line())
    _append_receipt(receipts, "ATTACHMENT", WORKFLOW_HOST_ID, next(attachments).canonical_line())
    final_record = report.workflow_final_run.final_records[0]
    _append_receipt(
        receipts,
        "HOST_CONTINUATION",
        WORKFLOW_HOST_ID,
        _canonical_json(
            {
                "final_native_state": final_record.state,
                "final_revision": final_record.revision,
                "run_digest": report.workflow_final_run.run_digest,
                "subject_id": final_record.task_id,
            }
        ),
    )
    _append_receipt(
        receipts,
        "SUMMARY",
        "LIVE_SUBSTITUTION",
        _canonical_json(
            {
                "actions": [contract.HOLD, contract.RELEASE],
                "bolt_on_executed_actions": 0,
                "executed_host_actions": 2,
                "final_host_detached": True,
                "final_native_state": workflow_host.DONE,
                "host_sequence": [QUEUE_HOST_ID, WORKFLOW_HOST_ID],
                "substitutions": 1,
            }
        ),
    )
    return tuple(receipts)


def replay_campaign_receipts(receipts: Sequence[CampaignReceipt]) -> CampaignReplay:
    receipt_tuple = tuple(receipts)
    prior = ZERO_DIGEST
    for expected, receipt in enumerate(receipt_tuple, start=1):
        if receipt.receipt_id != expected:
            return CampaignReplay(False, prior, expected - 1, (), (), 0, 0, "", "RECEIPT_ID_MISMATCH")
        if receipt.prior_hash != prior:
            return CampaignReplay(False, prior, expected - 1, (), (), 0, 0, "", "PRIOR_HASH_MISMATCH")
        expected_hash = _receipt_hash(receipt.receipt_id, receipt.kind, receipt.subject, receipt.payload, receipt.prior_hash)
        if receipt.receipt_hash != expected_hash:
            return CampaignReplay(False, prior, expected - 1, (), (), 0, 0, "", "RECEIPT_HASH_MISMATCH")
        prior = expected_hash
    expected_kinds = (
        "SESSION", "ATTACHMENT", "ADAPTER_REPORT", "REQUEST", "PROJECTION",
        "EXECUTION_PERMIT", "HOST_EXECUTION", "CHECKPOINT", "ATTACHMENT",
        "SUBSTITUTION_TICKET", "TARGET_READY", "ATTACHMENT", "ADAPTER_REPORT",
        "REQUEST", "PROJECTION", "EXECUTION_PERMIT", "HOST_EXECUTION",
        "ATTACHMENT", "HOST_CONTINUATION", "SUMMARY",
    )
    if tuple(item.kind for item in receipt_tuple) != expected_kinds:
        return CampaignReplay(False, prior, len(receipt_tuple), (), (), 0, 0, "", "CAMPAIGN_RECEIPT_SEQUENCE_INVALID")
    try:
        session = json.loads(receipt_tuple[0].payload)
        attachments = []
        for index in (1, 8, 11, 17):
            payload = json.loads(receipt_tuple[index].payload)
            attachments.append(HostAttachmentEvent(**payload))
        queue_request = contract.PortableActionRequest(**json.loads(receipt_tuple[3].payload))
        queue_projection = contract.AdapterProjection(**json.loads(receipt_tuple[4].payload))
        queue_permit = HostExecutionPermit(**json.loads(receipt_tuple[5].payload))
        queue_outcome = HostExecutionOutcome(**json.loads(receipt_tuple[6].payload))
        checkpoint = PortableCheckpoint(
            **{
                **json.loads(receipt_tuple[7].payload),
                "action_history": tuple(json.loads(receipt_tuple[7].payload)["action_history"]),
            }
        )
        ticket = SubstitutionTicket(**json.loads(receipt_tuple[9].payload))
        target_ready = json.loads(receipt_tuple[10].payload)
        workflow_request = contract.PortableActionRequest(**json.loads(receipt_tuple[13].payload))
        workflow_projection = contract.AdapterProjection(**json.loads(receipt_tuple[14].payload))
        workflow_permit = HostExecutionPermit(**json.loads(receipt_tuple[15].payload))
        workflow_outcome = HostExecutionOutcome(**json.loads(receipt_tuple[16].payload))
        continuation = json.loads(receipt_tuple[18].payload)
        summary = json.loads(receipt_tuple[19].payload)
    except (json.JSONDecodeError, TypeError, KeyError):
        return CampaignReplay(False, prior, len(receipt_tuple), (), (), 0, 0, "", "CAMPAIGN_PAYLOAD_INVALID")
    if session.get("bolt_on_execution_authority") != "NONE" or session.get("execution_boundary") != EXECUTION_BOUNDARY:
        return CampaignReplay(False, prior, len(receipt_tuple), (), (), 0, 0, "", "SESSION_AUTHORITY_INVALID")
    attachment_replay = replay_attachment_events(tuple(attachments))
    if not attachment_replay.passed or attachment_replay.active_host_id:
        return CampaignReplay(False, prior, len(receipt_tuple), attachment_replay.host_sequence, (), 0, 0, "", "ATTACHMENT_REPLAY_FAILED")
    for request in (queue_request, workflow_request):
        if not contract.validate_action_request(request)[0]:
            return CampaignReplay(False, prior, len(receipt_tuple), attachment_replay.host_sequence, (), 0, 0, "", "REQUEST_INVALID")
    if queue_request.action != contract.HOLD or workflow_request.action != contract.RELEASE:
        return CampaignReplay(False, prior, len(receipt_tuple), attachment_replay.host_sequence, (), 0, 0, "", "ACTION_ORDER_INVALID")
    if queue_projection.executed or workflow_projection.executed:
        return CampaignReplay(False, prior, len(receipt_tuple), attachment_replay.host_sequence, (), 0, 0, "", "ADAPTER_EXECUTION_NONZERO")
    if queue_projection.host_operation != queue_host.SUSPEND or workflow_projection.host_operation != workflow_host.RESUME:
        return CampaignReplay(False, prior, len(receipt_tuple), attachment_replay.host_sequence, (), 0, 0, "", "HOST_OPERATION_INVALID")
    if not validate_execution_permit(queue_permit)[0] or not validate_execution_permit(workflow_permit)[0]:
        return CampaignReplay(False, prior, len(receipt_tuple), attachment_replay.host_sequence, (), 0, 0, "", "PERMIT_INVALID")
    if not validate_execution_outcome(queue_outcome)[0] or not validate_execution_outcome(workflow_outcome)[0]:
        return CampaignReplay(False, prior, len(receipt_tuple), attachment_replay.host_sequence, (), 0, 0, "", "OUTCOME_INVALID")
    queue_bindings = (
        (queue_permit.host_id, QUEUE_HOST_ID),
        (queue_permit.request_digest, queue_request.request_digest),
        (queue_permit.projection_digest, queue_projection.projection_digest),
        (queue_permit.action, queue_request.action),
        (queue_permit.host_operation, queue_projection.host_operation),
        (queue_permit.subject_id, queue_request.subject_id),
        (queue_outcome.permit_id, queue_permit.permit_id),
        (queue_outcome.host_id, queue_permit.host_id),
        (queue_outcome.action, queue_permit.action),
        (queue_outcome.host_operation, queue_permit.host_operation),
        (queue_outcome.subject_id, queue_permit.subject_id),
    )
    workflow_bindings = (
        (workflow_permit.host_id, WORKFLOW_HOST_ID),
        (workflow_permit.request_digest, workflow_request.request_digest),
        (workflow_permit.projection_digest, workflow_projection.projection_digest),
        (workflow_permit.action, workflow_request.action),
        (workflow_permit.host_operation, workflow_projection.host_operation),
        (workflow_permit.subject_id, workflow_request.subject_id),
        (workflow_outcome.permit_id, workflow_permit.permit_id),
        (workflow_outcome.host_id, workflow_permit.host_id),
        (workflow_outcome.action, workflow_permit.action),
        (workflow_outcome.host_operation, workflow_permit.host_operation),
        (workflow_outcome.subject_id, workflow_permit.subject_id),
    )
    if any(actual != expected for actual, expected in queue_bindings + workflow_bindings):
        return CampaignReplay(False, prior, len(receipt_tuple), attachment_replay.host_sequence, (), 0, 0, "", "EXECUTION_BINDING_MISMATCH")
    if not queue_outcome.executed or not workflow_outcome.executed:
        return CampaignReplay(False, prior, len(receipt_tuple), attachment_replay.host_sequence, (), 0, 0, "", "HOST_EXECUTION_MISSING")
    if (queue_outcome.native_state_before, queue_outcome.native_state_after) != (queue_host.ACTIVE, queue_host.HELD):
        return CampaignReplay(False, prior, len(receipt_tuple), attachment_replay.host_sequence, (), 0, 0, "", "QUEUE_TRANSITION_INVALID")
    if (workflow_outcome.native_state_before, workflow_outcome.native_state_after) != (workflow_host.PAUSED, workflow_host.RUNNING):
        return CampaignReplay(False, prior, len(receipt_tuple), attachment_replay.host_sequence, (), 0, 0, "", "WORKFLOW_TRANSITION_INVALID")
    if not validate_checkpoint(checkpoint)[0] or checkpoint.source_outcome_digest != queue_outcome.outcome_digest:
        return CampaignReplay(False, prior, len(receipt_tuple), attachment_replay.host_sequence, (), 0, 0, "", "CHECKPOINT_INVALID")
    if (
        checkpoint.session_digest != session.get("session_digest")
        or queue_request.governance_session_digest != checkpoint.session_digest
        or workflow_request.governance_session_digest != checkpoint.session_digest
        or any(item.session_digest != checkpoint.session_digest for item in attachments)
        or attachments[1].checkpoint_digest != checkpoint.checkpoint_digest
        or attachments[3].checkpoint_digest != checkpoint.checkpoint_digest
        or target_ready.get("native_state") != workflow_host.PAUSED
        or target_ready.get("subject_id") != checkpoint.subject_id
    ):
        return CampaignReplay(False, prior, len(receipt_tuple), attachment_replay.host_sequence, (), 0, 0, "", "CAMPAIGN_CONTINUITY_MISMATCH")
    valid_ticket, _ = validate_substitution_ticket(
        ticket,
        checkpoint=checkpoint,
        source_detach_digest=attachments[1].event_digest,
        target_ready_digest=target_ready["run_digest"],
        current_epoch=ticket.valid_epoch,
    )
    if not valid_ticket or attachments[2].checkpoint_digest != checkpoint.checkpoint_digest:
        return CampaignReplay(False, prior, len(receipt_tuple), attachment_replay.host_sequence, (), 0, 0, "", "SUBSTITUTION_TICKET_INVALID")
    expected_summary = {
        "actions": [contract.HOLD, contract.RELEASE],
        "bolt_on_executed_actions": 0,
        "executed_host_actions": 2,
        "final_host_detached": True,
        "final_native_state": workflow_host.DONE,
        "host_sequence": [QUEUE_HOST_ID, WORKFLOW_HOST_ID],
        "substitutions": 1,
    }
    if summary != expected_summary or continuation.get("final_native_state") != workflow_host.DONE:
        return CampaignReplay(False, prior, len(receipt_tuple), attachment_replay.host_sequence, (), 0, 0, "", "CAMPAIGN_SUMMARY_INVALID")
    return CampaignReplay(
        True,
        prior,
        len(receipt_tuple),
        attachment_replay.host_sequence,
        (contract.HOLD, contract.RELEASE),
        2,
        0,
        continuation["final_native_state"],
        "NONE",
    )


def _queue_initial_commands() -> Tuple[object, ...]:
    return (
        queue_host.QueueCommand("LIVE-Q-001", SUBJECT_ID, queue_host.ENQUEUE, 0),
        queue_host.QueueCommand("LIVE-Q-002", SUBJECT_ID, queue_host.CLAIM, 1),
    )


def _workflow_prepared_commands() -> Tuple[object, ...]:
    return (
        workflow_host.WorkflowCommand("LIVE-W-001", SUBJECT_ID, workflow_host.REGISTER, 0),
        workflow_host.WorkflowCommand("LIVE-W-002", SUBJECT_ID, workflow_host.START, 1),
        workflow_host.WorkflowCommand("LIVE-W-003", SUBJECT_ID, workflow_host.PAUSE, 2),
    )


def _request_for_event(
    *,
    action: str,
    event: object,
    session_digest: str,
    authority_digest: str,
    current_epoch: int,
) -> object:
    expected_state = (
        event.state_after_digest if action == contract.HOLD else event.state_before_digest
    )
    return contract.build_action_request(
        request_id=1,
        action=action,
        subject_id=event.subject_id,
        source_event_digest=event.event_digest,
        governance_session_digest=session_digest,
        authority_digest=authority_digest,
        expected_state_digest=expected_state,
        current_epoch=current_epoch,
    )


def run_live_substitution() -> LiveSubstitutionReport:
    session_digest = _digest_json({"session": "V03-STAGE-4-LIVE-SUBSTITUTION"})
    authority_digest = _digest_json(
        {
            "authority": "FROZEN-V02-HOLD-RELEASE",
            "stage3_source_sha256": EXPECTED_STAGE3_SOURCE_SHA256,
        }
    )

    queue_adapter = QueueLiveAdapter()
    queue_before = make_queue_runtime(_queue_initial_commands())
    queue_events = tuple(queue_adapter.normalize_event(item) for item in queue_before.run.events)
    claim_event = queue_events[-1]
    queue_request = _request_for_event(
        action=contract.HOLD,
        event=claim_event,
        session_digest=session_digest,
        authority_digest=authority_digest,
        current_epoch=500,
    )
    queue_adapter_report = contract.evaluate_adapter(
        queue_adapter, queue_before.run.events, (queue_request,)
    )
    queue_projection = queue_adapter_report.projections[0]
    queue_permit = issue_execution_permit(
        session_digest=session_digest,
        host_id=QUEUE_HOST_ID,
        identity=queue_adapter.identity(),
        request=queue_request,
        projection=queue_projection,
        expected_native_state=queue_host.ACTIVE,
        valid_epoch=500,
    )
    queue_after, queue_outcome = execute_queue_host_boundary(
        queue_before,
        identity=queue_adapter.identity(),
        request=queue_request,
        projection=queue_projection,
        permit=queue_permit,
        current_epoch=500,
    )
    checkpoint = build_checkpoint(session_digest=session_digest, outcome=queue_outcome)

    attachment_events: list[HostAttachmentEvent] = []
    queue_attach = build_attachment_event(
        sequence=1,
        event_type="ATTACH",
        host_id=QUEUE_HOST_ID,
        adapter_identity_digest=queue_adapter.identity().identity_digest,
        session_digest=session_digest,
    )
    attachment_events.append(queue_attach)
    queue_detach = build_attachment_event(
        sequence=2,
        event_type="DETACH",
        host_id=QUEUE_HOST_ID,
        adapter_identity_digest=queue_adapter.identity().identity_digest,
        session_digest=session_digest,
        checkpoint_digest=checkpoint.checkpoint_digest,
        prior_event_digest=queue_attach.event_digest,
    )
    attachment_events.append(queue_detach)

    workflow_adapter = WorkflowLiveAdapter()
    workflow_before = make_workflow_runtime(_workflow_prepared_commands())
    ticket = issue_substitution_ticket(
        session_digest=session_digest,
        checkpoint=checkpoint,
        source_detach_digest=queue_detach.event_digest,
        target_ready_digest=workflow_before.run.run_digest,
        valid_epoch=501,
    )
    workflow_attach = build_attachment_event(
        sequence=3,
        event_type="ATTACH",
        host_id=WORKFLOW_HOST_ID,
        adapter_identity_digest=workflow_adapter.identity().identity_digest,
        session_digest=session_digest,
        checkpoint_digest=checkpoint.checkpoint_digest,
        prior_event_digest=queue_detach.event_digest,
    )
    attachment_events.append(workflow_attach)

    pause_raw = workflow_before.run.events[-1]
    pause_event = workflow_adapter.normalize_event(pause_raw)
    workflow_request = _request_for_event(
        action=contract.RELEASE,
        event=pause_event,
        session_digest=session_digest,
        authority_digest=authority_digest,
        current_epoch=502,
    )
    workflow_adapter_report = contract.evaluate_adapter(
        workflow_adapter, workflow_before.run.events, (workflow_request,)
    )
    workflow_projection = workflow_adapter_report.projections[0]
    workflow_permit = issue_execution_permit(
        session_digest=session_digest,
        host_id=WORKFLOW_HOST_ID,
        identity=workflow_adapter.identity(),
        request=workflow_request,
        projection=workflow_projection,
        expected_native_state=workflow_host.PAUSED,
        valid_epoch=502,
    )
    workflow_after, workflow_outcome = execute_workflow_host_boundary(
        workflow_before,
        identity=workflow_adapter.identity(),
        request=workflow_request,
        projection=workflow_projection,
        permit=workflow_permit,
        current_epoch=502,
    )
    workflow_detach = build_attachment_event(
        sequence=4,
        event_type="DETACH",
        host_id=WORKFLOW_HOST_ID,
        adapter_identity_digest=workflow_adapter.identity().identity_digest,
        session_digest=session_digest,
        checkpoint_digest=checkpoint.checkpoint_digest,
        prior_event_digest=workflow_attach.event_digest,
    )
    attachment_events.append(workflow_detach)

    resumed_record = workflow_after.run.final_records[0]
    continuation_command = workflow_host.WorkflowCommand(
        "LIVE-W-ORDINARY-COMPLETE",
        SUBJECT_ID,
        workflow_host.COMPLETE,
        resumed_record.revision,
    )
    workflow_final_run = workflow_host.run_workflow(
        workflow_after.commands + (continuation_command,)
    )
    attachment_replay = replay_attachment_events(tuple(attachment_events))

    provisional = LiveSubstitutionReport(
        session_digest=session_digest,
        queue_adapter_report=queue_adapter_report,
        workflow_adapter_report=workflow_adapter_report,
        queue_runtime_before=queue_before,
        queue_runtime_after=queue_after,
        workflow_runtime_before=workflow_before,
        workflow_runtime_after=workflow_after,
        workflow_final_run=workflow_final_run,
        queue_permit=queue_permit,
        workflow_permit=workflow_permit,
        queue_outcome=queue_outcome,
        workflow_outcome=workflow_outcome,
        checkpoint=checkpoint,
        substitution_ticket=ticket,
        attachment_events=tuple(attachment_events),
        attachment_replay=attachment_replay,
        receipts=(),
        replay=CampaignReplay(False, ZERO_DIGEST, 0, (), (), 0, 0, "", "NOT_REPLAYED"),
        campaign_digest=ZERO_DIGEST,
        executed_host_actions=2,
        bolt_on_executed_actions=0,
        substitutions=attachment_replay.substitutions,
    )
    receipts = build_campaign_receipts(provisional)
    replay = replay_campaign_receipts(receipts)
    return replace(
        provisional,
        receipts=receipts,
        replay=replay,
        campaign_digest=receipts[-1].receipt_hash,
    )


def _host_independent(path: Path) -> bool:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    imported: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.extend(alias.name.lower() for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            imported.append((node.module or "").lower())
    prohibited = ("portable_adapter_contract", "natural_math", "cntm", "governance", "bolt_on")
    return not any(token in module for module in imported for token in prohibited)


def run_stage4_qualification(
    *,
    frozen_root: Path = FROZEN_V02_ROOT,
    expected_manifest_sha256: str = contract.EXPECTED_V02_RELEASE_MANIFEST_SHA256,
) -> Stage4Qualification:
    frozen_pre = contract.verify_frozen_v02(frozen_root, expected_manifest_sha256)
    source_before = _source_snapshot()
    inputs_before = repr((_queue_initial_commands(), _workflow_prepared_commands()))

    first = run_live_substitution()
    second = run_live_substitution()

    inputs_after = repr((_queue_initial_commands(), _workflow_prepared_commands()))
    source_after = _source_snapshot()
    frozen_post = contract.verify_frozen_v02(frozen_root, expected_manifest_sha256)

    source_map = dict(source_before)
    prior_stage_sources_bound = (
        source_map.get(CONTRACT_PATH.relative_to(REPOSITORY_ROOT).as_posix())
        == EXPECTED_STAGE1_SOURCE_SHA256
        and source_map.get(STAGE2_PATH.relative_to(REPOSITORY_ROOT).as_posix())
        == EXPECTED_STAGE2_SOURCE_SHA256
        and source_map.get(WORKFLOW_HOST_PATH.relative_to(REPOSITORY_ROOT).as_posix())
        == EXPECTED_WORKFLOW_HOST_SOURCE_SHA256
        and source_map.get(STAGE3_PATH.relative_to(REPOSITORY_ROOT).as_posix())
        == EXPECTED_STAGE3_SOURCE_SHA256
    )

    forged = replace(first.queue_permit, projection_digest="f" * 64)
    _, forged_outcome = execute_queue_host_boundary(
        first.queue_runtime_before,
        identity=first.queue_adapter_report.identity,
        request=first.queue_adapter_report.requests[0],
        projection=first.queue_adapter_report.projections[0],
        permit=forged,
        current_epoch=500,
    )
    _, reused_outcome = execute_queue_host_boundary(
        first.queue_runtime_after,
        identity=first.queue_adapter_report.identity,
        request=first.queue_adapter_report.requests[0],
        projection=first.queue_adapter_report.projections[0],
        permit=first.queue_permit,
        current_epoch=500,
    )
    tampered_checkpoint = replace(first.checkpoint, portable_state="ACTIVE")
    tampered_ticket = replace(first.substitution_ticket, target_host_id="OTHER")

    tampered_receipts = list(first.receipts)
    tampered_receipts[7] = replace(tampered_receipts[7], payload="TAMPERED")
    receipt_tamper_detection_pass = not replay_campaign_receipts(tuple(tampered_receipts)).passed
    reordered_receipts = list(first.receipts)
    reordered_receipts[8], reordered_receipts[9] = reordered_receipts[9], reordered_receipts[8]
    receipt_reorder_detection_pass = not replay_campaign_receipts(tuple(reordered_receipts)).passed

    queue_record = first.queue_runtime_after.run.final_records[0]
    workflow_resumed = first.workflow_runtime_after.run.final_records[0]
    workflow_final = first.workflow_final_run.final_records[0]
    source_host_hold_executed = (
        first.queue_outcome.executed
        and queue_record == queue_host.QueueRecord(SUBJECT_ID, queue_host.HELD, 3)
    )
    target_host_release_executed = (
        first.workflow_outcome.executed
        and workflow_resumed
        == workflow_host.WorkflowRecord(SUBJECT_ID, workflow_host.RUNNING, 4)
    )
    target_host_continuation_pass = (
        workflow_final == workflow_host.WorkflowRecord(SUBJECT_ID, workflow_host.DONE, 5)
        and not first.workflow_final_run.rejected_command_ids
    )
    checkpoint_pass = (
        validate_checkpoint(first.checkpoint)[0]
        and first.checkpoint.source_run_digest == first.queue_runtime_after.run.run_digest
    )
    ticket_pass = validate_substitution_ticket(
        first.substitution_ticket,
        checkpoint=first.checkpoint,
        source_detach_digest=first.attachment_events[1].event_digest,
        target_ready_digest=first.workflow_runtime_before.run.run_digest,
        current_epoch=501,
    )[0]
    no_hidden_execution_authority = (
        BOLT_ON_EXECUTION_AUTHORITY == "NONE"
        and first.bolt_on_executed_actions == 0
        and first.executed_host_actions == 2
        and not first.queue_adapter_report.outcomes[0].executed
        and not first.workflow_adapter_report.outcomes[0].executed
        and not any(
            hasattr(contract.PortableHostAdapter, name)
            for name in ("execute", "apply", "dispatch", "mutate_host")
        )
        and not any(
            hasattr(stage3.CrossHostSemanticAdapter, name)
            for name in ("execute", "apply", "dispatch", "mutate_host")
        )
    )
    frozen_unchanged = frozen_pre.passed and frozen_post.passed and frozen_pre == frozen_post
    deterministic_second_pass = first == second
    passed = (
        frozen_pre.passed
        and frozen_post.passed
        and frozen_unchanged
        and prior_stage_sources_bound
        and _host_independent(QUEUE_HOST_PATH)
        and _host_independent(WORKFLOW_HOST_PATH)
        and source_before == source_after
        and inputs_before == inputs_after
        and deterministic_second_pass
        and first.queue_adapter_report.passed
        and first.workflow_adapter_report.passed
        and source_host_hold_executed
        and first.attachment_events[1].event_type == "DETACH"
        and checkpoint_pass
        and ticket_pass
        and first.attachment_events[2].event_type == "ATTACH"
        and target_host_release_executed
        and first.attachment_events[3].event_type == "DETACH"
        and target_host_continuation_pass
        and first.attachment_replay.passed
        and first.replay.passed
        and first.campaign_digest == first.replay.final_digest
        and not forged_outcome.executed
        and forged_outcome.reason_code == "PERMIT_HASH_MISMATCH"
        and not reused_outcome.executed
        and reused_outcome.reason_code == "PERMIT_ALREADY_CONSUMED"
        and not validate_checkpoint(tampered_checkpoint)[0]
        and not validate_substitution_ticket(
            tampered_ticket,
            checkpoint=first.checkpoint,
            source_detach_digest=first.attachment_events[1].event_digest,
            target_ready_digest=first.workflow_runtime_before.run.run_digest,
            current_epoch=501,
        )[0]
        and receipt_tamper_detection_pass
        and receipt_reorder_detection_pass
        and no_hidden_execution_authority
    )
    return Stage4Qualification(
        passed=passed,
        stage_name=STAGE_NAME,
        stage_version=STAGE_VERSION,
        mode=MODE,
        bolt_on_execution_authority=BOLT_ON_EXECUTION_AUTHORITY,
        execution_boundary=EXECUTION_BOUNDARY,
        frozen_v02_pre_pass=frozen_pre.passed,
        frozen_v02_post_pass=frozen_post.passed,
        frozen_v02_unchanged=frozen_unchanged,
        prior_stage_sources_bound=prior_stage_sources_bound,
        host_independence_pass=_host_independent(QUEUE_HOST_PATH) and _host_independent(WORKFLOW_HOST_PATH),
        sources_unchanged=source_before == source_after,
        inputs_unchanged=inputs_before == inputs_after,
        deterministic_second_pass=deterministic_second_pass,
        source_host_hold_executed=source_host_hold_executed,
        source_host_detached=first.attachment_events[1].event_type == "DETACH",
        checkpoint_pass=checkpoint_pass,
        substitution_ticket_pass=ticket_pass,
        target_host_attached=first.attachment_events[2].event_type == "ATTACH",
        target_host_release_executed=target_host_release_executed,
        target_host_detached=first.attachment_events[3].event_type == "DETACH",
        target_host_continuation_pass=target_host_continuation_pass,
        attachment_replay_pass=first.attachment_replay.passed,
        campaign_replay_pass=first.replay.passed,
        forged_permit_rejected=not forged_outcome.executed,
        reused_permit_rejected=not reused_outcome.executed,
        tampered_checkpoint_rejected=not validate_checkpoint(tampered_checkpoint)[0],
        tampered_ticket_rejected=not validate_substitution_ticket(
            tampered_ticket,
            checkpoint=first.checkpoint,
            source_detach_digest=first.attachment_events[1].event_digest,
            target_ready_digest=first.workflow_runtime_before.run.run_digest,
            current_epoch=501,
        )[0],
        receipt_tamper_detection_pass=receipt_tamper_detection_pass,
        receipt_reorder_detection_pass=receipt_reorder_detection_pass,
        no_hidden_execution_authority=no_hidden_execution_authority,
        executed_host_actions=first.executed_host_actions,
        bolt_on_executed_actions=first.bolt_on_executed_actions,
        substitutions=first.substitutions,
        host_sequence=first.attachment_replay.host_sequence,
        queue_held_run_digest=first.queue_runtime_after.run.run_digest,
        workflow_resumed_run_digest=first.workflow_runtime_after.run.run_digest,
        workflow_final_run_digest=first.workflow_final_run.run_digest,
        campaign_digest=first.campaign_digest,
        replay_digest=first.replay.final_digest,
        frozen_v02_manifest_sha256=frozen_pre.manifest_sha256,
    )


def main() -> int:
    qualification = run_stage4_qualification()
    print(f"Stage: {qualification.stage_name} {qualification.stage_version}")
    print(f"Mode: {qualification.mode}")
    print(f"Bolt-on execution authority: {qualification.bolt_on_execution_authority}")
    print(f"Execution boundary: {qualification.execution_boundary}")
    print(f"Frozen v0.2 manifest: {qualification.frozen_v02_manifest_sha256}")
    print(f"Source host: {queue_host.HOST_NAME} {queue_host.HOST_VERSION}")
    print(f"Target host: {workflow_host.HOST_NAME} {workflow_host.HOST_VERSION}")
    print(f"Host sequence: {' -> '.join(qualification.host_sequence)}")
    print(f"Substitutions: {qualification.substitutions}")
    print(f"Executed host actions: {qualification.executed_host_actions}")
    print(f"Bolt-on executed actions: {qualification.bolt_on_executed_actions}")
    print(f"Queue held run digest: {qualification.queue_held_run_digest}")
    print(f"Workflow resumed run digest: {qualification.workflow_resumed_run_digest}")
    print(f"Workflow final run digest: {qualification.workflow_final_run_digest}")
    print(f"Campaign digest: {qualification.campaign_digest}")
    print(f"Replay digest: {qualification.replay_digest}")
    if not qualification.passed:
        print("STAGE 4 LIVE HOST SUBSTITUTION QUALIFICATION: FAIL")
        return 1
    print("STAGE 4 LIVE HOST SUBSTITUTION QUALIFICATION: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
