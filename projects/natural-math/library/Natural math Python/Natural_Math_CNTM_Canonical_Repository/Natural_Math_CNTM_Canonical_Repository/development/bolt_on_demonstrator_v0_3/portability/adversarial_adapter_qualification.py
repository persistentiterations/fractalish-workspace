#!/usr/bin/env python3
"""Adversarial adapter qualification for Bolt-On Demonstrator v0.3, Stage 5.

Stage 5 attacks the portable adapter, host-execution permit, checkpoint,
substitution-ticket, attachment, and campaign-receipt boundaries qualified in
Stages 1-4.  It adds no host action and does not modify any earlier stage.

The Stage 4 host-owned execution functions remain the only execution surface.
Stage 5 adds strict preflight validation that independently re-derives permit,
checkpoint, and ticket identifiers; pins issuers and sessions; validates the
complete adapter evidence chain; and denies malformed or replayed evidence
before a host-owned boundary may be called.

SHA-256 values are deterministic integrity bindings for this demonstrator, not
production identity signatures.
"""

from __future__ import annotations

import hashlib
import importlib.util
import json
from dataclasses import dataclass, replace
from pathlib import Path
import sys
from typing import Callable, Iterable, Sequence, Tuple

sys.dont_write_bytecode = True

STAGE_NAME = "ADVERSARIAL ADAPTER QUALIFICATION"
STAGE_VERSION = "0.3.5"
MODE = "INTEGRATED_ADVERSARIAL_ADAPTER_TESTING"
BOLT_ON_EXECUTION_AUTHORITY = "NONE"
EXECUTION_BOUNDARY = "HOST_BOUNDARY_ONLY"
ZERO_DIGEST = "0" * 64

EXPECTED_STAGE1_SOURCE_SHA256 = (
    "fe8b138db0069f1ac4a7832fd0f63d5ae30021cdfd5244e2476f8b3b52a4bbb9"
)
EXPECTED_STAGE2_SOURCE_SHA256 = (
    "44801c04e6b3765387bfc4e4b7fb8d71f2ebfc3534c67cc428d778d412c8c03a"
)
EXPECTED_STAGE3_SOURCE_SHA256 = (
    "4c2d4cebbaf50591386fe68a9d0da7448a0d2c8fe89c0d69851389a370eacb98"
)
EXPECTED_STAGE4_SOURCE_SHA256 = (
    "b4b0ed3c7c5306961454be0383d165392409bb03b9ad8d824e0de2d80b77d10d"
)
EXPECTED_WORKFLOW_HOST_SOURCE_SHA256 = (
    "c940594a409fe7b159ac5c8843ea00100279f754a3db6911662dbc9553222847"
)
EXPECTED_QUEUE_HOST_SOURCE_SHA256 = (
    "d1d8b49b3dd13142d3fcc33102a6aede9140eef43ce0a54398e2389164af8e9c"
)

EXPECTED_HOST_PERMIT_ISSUER = "LOCAL_STAGE4_HOST_AUTHORITY"
EXPECTED_SUBSTITUTION_ISSUER = "LOCAL_STAGE4_SUBSTITUTION_AUTHORITY"

THIS_FILE = Path(__file__).resolve()
PROJECT_DIR = THIS_FILE.parents[1]
REPOSITORY_ROOT = THIS_FILE.parents[3]
CONTRACT_PATH = PROJECT_DIR / "portability" / "portable_adapter_contract.py"
STAGE2_PATH = PROJECT_DIR / "portability" / "second_independent_host.py"
STAGE3_PATH = PROJECT_DIR / "portability" / "cross_host_replay.py"
STAGE4_PATH = PROJECT_DIR / "portability" / "live_host_substitution.py"
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


stage4 = _load_module("bolt_on_v03_stage4_for_stage5", STAGE4_PATH)
contract = stage4.contract
workflow_host = stage4.workflow_host
queue_host = stage4.queue_host


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


def _source_snapshot() -> Tuple[Tuple[str, str], ...]:
    paths = (
        CONTRACT_PATH,
        STAGE2_PATH,
        STAGE3_PATH,
        STAGE4_PATH,
        WORKFLOW_HOST_PATH,
        QUEUE_HOST_PATH,
        THIS_FILE,
    )
    return tuple(
        (path.relative_to(REPOSITORY_ROOT).as_posix(), _sha256_file(path))
        for path in paths
    )


def _rehash_dataclass(value: object, digest_field: str):
    unsigned = value.unsigned_record()
    return replace(value, **{digest_field: _digest_json(unsigned)})


def _expected_permit_id(permit: object) -> str:
    seed = dict(permit.unsigned_record())
    seed.pop("permit_id", None)
    return "HP-" + _digest_json(seed)[:24].upper()


def _expected_checkpoint_id(checkpoint: object) -> str:
    seed = dict(checkpoint.unsigned_record())
    seed.pop("checkpoint_id", None)
    return "CP-" + _digest_json(seed)[:24].upper()


def _expected_ticket_id(ticket: object) -> str:
    seed = dict(ticket.unsigned_record())
    seed.pop("ticket_id", None)
    return "ST-" + _digest_json(seed)[:24].upper()


def _record_for_runtime(runtime: object, host_id: str, subject_id: str):
    if host_id == stage4.QUEUE_HOST_ID:
        return next(
            (record for record in runtime.run.final_records if record.item_id == subject_id),
            None,
        )
    if host_id == stage4.WORKFLOW_HOST_ID:
        return next(
            (record for record in runtime.run.final_records if record.task_id == subject_id),
            None,
        )
    return None


def validate_execution_context(
    runtime: object,
    *,
    host_id: str,
    identity: object,
    event: object,
    request: object,
    projection: object,
    permit: object,
    current_epoch: int,
) -> Tuple[bool, str]:
    """Strict Stage 5 preflight before any Stage 4 host-owned executor."""

    valid_identity, reason = contract.validate_adapter_identity(identity)
    if not valid_identity:
        return False, reason
    valid_event, reason = contract.validate_canonical_event(event, identity)
    if not valid_event:
        return False, reason
    valid_request, reason = contract.validate_action_request(request)
    if not valid_request:
        return False, reason
    valid_projection, reason = contract.validate_projection(
        projection, identity, request, event
    )
    if not valid_projection:
        return False, reason
    base_error = stage4._permit_binding_error(
        permit,
        host_id=host_id,
        identity=identity,
        request=request,
        projection=projection,
        current_epoch=current_epoch,
        consumed_ids=runtime.consumed_permit_ids,
    )
    if base_error != "NONE":
        return False, base_error
    if permit.issuer != EXPECTED_HOST_PERMIT_ISSUER:
        return False, "PERMIT_ISSUER_INVALID"
    if permit.session_digest != request.governance_session_digest:
        return False, "PERMIT_SESSION_MISMATCH"
    if permit.permit_id != _expected_permit_id(permit):
        return False, "PERMIT_ID_DERIVATION_MISMATCH"
    if request.current_epoch != current_epoch:
        return False, "REQUEST_EPOCH_MISMATCH"
    if identity.host_instance != host_id:
        return False, "ADAPTER_HOST_INSTANCE_MISMATCH"
    if request.action not in identity.capabilities:
        return False, "ACTION_OUT_OF_SCOPE"
    if event.event_digest != request.source_event_digest:
        return False, "REQUEST_EVENT_BINDING_MISMATCH"
    if event.subject_id != request.subject_id:
        return False, "REQUEST_SUBJECT_MISMATCH"
    expected_state_digest = (
        event.state_after_digest
        if request.action == contract.HOLD
        else event.state_before_digest
    )
    if request.expected_state_digest != expected_state_digest:
        return False, "EXPECTED_STATE_MISMATCH"
    expected_operation = {
        (stage4.QUEUE_HOST_ID, contract.HOLD): queue_host.SUSPEND,
        (stage4.WORKFLOW_HOST_ID, contract.RELEASE): workflow_host.RESUME,
    }.get((host_id, request.action))
    if expected_operation is None:
        return False, "HOST_ACTION_PAIR_UNSUPPORTED"
    if projection.host_operation != expected_operation:
        return False, "HOST_OPERATION_NOT_AUTHORIZED"
    record = _record_for_runtime(runtime, host_id, request.subject_id)
    if record is None:
        return False, "NATIVE_SUBJECT_MISSING"
    native_state = record.phase if host_id == stage4.QUEUE_HOST_ID else record.state
    if native_state != permit.expected_native_state:
        return False, "NATIVE_STATE_MISMATCH"
    return True, "VALID"


def guarded_queue_execution(
    runtime: object,
    *,
    identity: object,
    event: object,
    request: object,
    projection: object,
    permit: object,
    current_epoch: int,
):
    valid, reason = validate_execution_context(
        runtime,
        host_id=stage4.QUEUE_HOST_ID,
        identity=identity,
        event=event,
        request=request,
        projection=projection,
        permit=permit,
        current_epoch=current_epoch,
    )
    if not valid:
        return runtime, stage4._build_outcome(
            host_id=stage4.QUEUE_HOST_ID,
            permit_id=getattr(permit, "permit_id", "<INVALID>"),
            action=getattr(request, "action", "<INVALID>"),
            host_operation=getattr(projection, "host_operation", ""),
            subject_id=getattr(request, "subject_id", "<INVALID>"),
            native_state_before=_record_for_runtime(
                runtime, stage4.QUEUE_HOST_ID, getattr(request, "subject_id", "")
            ).phase
            if _record_for_runtime(
                runtime, stage4.QUEUE_HOST_ID, getattr(request, "subject_id", "")
            )
            is not None
            else queue_host.ABSENT,
            native_state_after=_record_for_runtime(
                runtime, stage4.QUEUE_HOST_ID, getattr(request, "subject_id", "")
            ).phase
            if _record_for_runtime(
                runtime, stage4.QUEUE_HOST_ID, getattr(request, "subject_id", "")
            )
            is not None
            else queue_host.ABSENT,
            native_version_before=_record_for_runtime(
                runtime, stage4.QUEUE_HOST_ID, getattr(request, "subject_id", "")
            ).version
            if _record_for_runtime(
                runtime, stage4.QUEUE_HOST_ID, getattr(request, "subject_id", "")
            )
            is not None
            else 0,
            native_version_after=_record_for_runtime(
                runtime, stage4.QUEUE_HOST_ID, getattr(request, "subject_id", "")
            ).version
            if _record_for_runtime(
                runtime, stage4.QUEUE_HOST_ID, getattr(request, "subject_id", "")
            )
            is not None
            else 0,
            executed=False,
            reason_code=reason,
            host_run_digest=runtime.run.run_digest,
        )
    return stage4.execute_queue_host_boundary(
        runtime,
        identity=identity,
        request=request,
        projection=projection,
        permit=permit,
        current_epoch=current_epoch,
    )


def guarded_workflow_execution(
    runtime: object,
    *,
    identity: object,
    event: object,
    request: object,
    projection: object,
    permit: object,
    current_epoch: int,
):
    valid, reason = validate_execution_context(
        runtime,
        host_id=stage4.WORKFLOW_HOST_ID,
        identity=identity,
        event=event,
        request=request,
        projection=projection,
        permit=permit,
        current_epoch=current_epoch,
    )
    if not valid:
        record = _record_for_runtime(
            runtime, stage4.WORKFLOW_HOST_ID, getattr(request, "subject_id", "")
        )
        state = record.state if record is not None else workflow_host.ABSENT
        revision = record.revision if record is not None else 0
        return runtime, stage4._build_outcome(
            host_id=stage4.WORKFLOW_HOST_ID,
            permit_id=getattr(permit, "permit_id", "<INVALID>"),
            action=getattr(request, "action", "<INVALID>"),
            host_operation=getattr(projection, "host_operation", ""),
            subject_id=getattr(request, "subject_id", "<INVALID>"),
            native_state_before=state,
            native_state_after=state,
            native_version_before=revision,
            native_version_after=revision,
            executed=False,
            reason_code=reason,
            host_run_digest=runtime.run.run_digest,
        )
    return stage4.execute_workflow_host_boundary(
        runtime,
        identity=identity,
        request=request,
        projection=projection,
        permit=permit,
        current_epoch=current_epoch,
    )


def validate_substitution_context(
    ticket: object,
    *,
    checkpoint: object,
    queue_outcome: object,
    source_detach_event: object,
    target_runtime: object,
    current_epoch: int,
    consumed_ticket_ids: Sequence[str] = (),
) -> Tuple[bool, str]:
    valid_checkpoint, reason = stage4.validate_checkpoint(checkpoint)
    if not valid_checkpoint:
        return False, reason
    valid_outcome, reason = stage4.validate_execution_outcome(queue_outcome)
    if not valid_outcome:
        return False, reason
    if not queue_outcome.executed:
        return False, "CHECKPOINT_SOURCE_NOT_EXECUTED"
    if checkpoint.source_outcome_digest != queue_outcome.outcome_digest:
        return False, "CHECKPOINT_OUTCOME_MISMATCH"
    if checkpoint.source_run_digest != queue_outcome.host_run_digest:
        return False, "CHECKPOINT_RUN_MISMATCH"
    if checkpoint.subject_id != queue_outcome.subject_id:
        return False, "CHECKPOINT_SUBJECT_MISMATCH"
    if checkpoint.checkpoint_id != _expected_checkpoint_id(checkpoint):
        return False, "CHECKPOINT_ID_DERIVATION_MISMATCH"
    if checkpoint.session_digest != ticket.session_digest:
        return False, "TICKET_SESSION_MISMATCH"
    if not isinstance(source_detach_event, stage4.HostAttachmentEvent):
        return False, "SOURCE_DETACH_TYPE_INVALID"
    detach_replay = stage4.replay_attachment_events(
        (
            stage4.build_attachment_event(
                sequence=1,
                event_type="ATTACH",
                host_id=stage4.QUEUE_HOST_ID,
                adapter_identity_digest=source_detach_event.adapter_identity_digest,
                session_digest=source_detach_event.session_digest,
            ),
            source_detach_event,
        )
    )
    if not detach_replay.passed:
        return False, detach_replay.first_error
    target_record = _record_for_runtime(
        target_runtime, stage4.WORKFLOW_HOST_ID, checkpoint.subject_id
    )
    if target_record is None:
        return False, "TARGET_SUBJECT_MISSING"
    if target_record.state != workflow_host.PAUSED:
        return False, "TARGET_NOT_READY"
    valid_ticket, reason = stage4.validate_substitution_ticket(
        ticket,
        checkpoint=checkpoint,
        source_detach_digest=source_detach_event.event_digest,
        target_ready_digest=target_runtime.run.run_digest,
        current_epoch=current_epoch,
    )
    if not valid_ticket:
        return False, reason
    if ticket.issuer != EXPECTED_SUBSTITUTION_ISSUER:
        return False, "TICKET_ISSUER_INVALID"
    if ticket.ticket_id != _expected_ticket_id(ticket):
        return False, "TICKET_ID_DERIVATION_MISMATCH"
    if ticket.ticket_id in tuple(consumed_ticket_ids):
        return False, "TICKET_ALREADY_CONSUMED"
    return True, "VALID"


@dataclass(frozen=True)
class AttackSpec:
    attack_id: str
    category: str
    target: str
    expected_reason: str


@dataclass(frozen=True)
class AttackResult:
    attack_id: str
    category: str
    target: str
    expected_reason: str
    observed_reason: str
    rejected: bool
    host_state_unchanged: bool
    attack_host_actions: int
    bolt_on_executed_actions: int
    result_digest: str

    def unsigned_record(self) -> dict[str, object]:
        return {
            "attack_host_actions": self.attack_host_actions,
            "attack_id": self.attack_id,
            "bolt_on_executed_actions": self.bolt_on_executed_actions,
            "category": self.category,
            "expected_reason": self.expected_reason,
            "host_state_unchanged": self.host_state_unchanged,
            "observed_reason": self.observed_reason,
            "rejected": self.rejected,
            "target": self.target,
        }

    def canonical_line(self) -> str:
        return _canonical_json({**self.unsigned_record(), "result_digest": self.result_digest})


@dataclass(frozen=True)
class AdversarialReceipt:
    receipt_id: int
    kind: str
    subject: str
    payload: str
    prior_hash: str
    receipt_hash: str


@dataclass(frozen=True)
class AdversarialReplay:
    passed: bool
    final_digest: str
    checked_receipts: int
    attack_count: int
    rejected_count: int
    attack_host_actions: int
    bolt_on_executed_actions: int
    first_error: str


@dataclass(frozen=True)
class AdversarialCampaignReport:
    baseline: object
    attacks: Tuple[AttackResult, ...]
    receipts: Tuple[AdversarialReceipt, ...]
    replay: AdversarialReplay
    campaign_digest: str
    attack_count: int
    rejected_count: int
    attack_host_actions: int
    bolt_on_executed_actions: int
    categories: Tuple[str, ...]
    sources_before: Tuple[Tuple[str, str], ...]
    sources_after: Tuple[Tuple[str, str], ...]


@dataclass(frozen=True)
class Stage5Qualification:
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
    sources_unchanged: bool
    baseline_stage4_pass: bool
    valid_control_contexts_pass: bool
    deterministic_second_pass: bool
    all_attacks_rejected: bool
    host_state_preserved: bool
    adversarial_replay_pass: bool
    receipt_tamper_detection_pass: bool
    receipt_reorder_detection_pass: bool
    semantic_rehash_detection_pass: bool
    no_hidden_execution_authority: bool
    attack_count: int
    rejected_count: int
    baseline_host_actions: int
    attack_host_actions: int
    bolt_on_executed_actions: int
    category_count: int
    campaign_digest: str
    replay_digest: str
    frozen_v02_manifest_sha256: str


def _attack_result(
    spec: AttackSpec,
    observed_reason: str,
    *,
    host_state_unchanged: bool = True,
    attack_host_actions: int = 0,
    bolt_on_executed_actions: int = 0,
) -> AttackResult:
    unsigned = {
        "attack_host_actions": attack_host_actions,
        "attack_id": spec.attack_id,
        "bolt_on_executed_actions": bolt_on_executed_actions,
        "category": spec.category,
        "expected_reason": spec.expected_reason,
        "host_state_unchanged": host_state_unchanged,
        "observed_reason": observed_reason,
        "rejected": observed_reason == spec.expected_reason,
        "target": spec.target,
    }
    return AttackResult(
        attack_id=spec.attack_id,
        category=spec.category,
        target=spec.target,
        expected_reason=spec.expected_reason,
        observed_reason=observed_reason,
        rejected=unsigned["rejected"],
        host_state_unchanged=host_state_unchanged,
        attack_host_actions=attack_host_actions,
        bolt_on_executed_actions=bolt_on_executed_actions,
        result_digest=_digest_json(unsigned),
    )


def _request_like(request: object, **changes):
    fields = request.unsigned_record()
    fields.update(changes)
    return contract.build_action_request(**fields)


def _projection_rehash(projection: object, **changes):
    changed = replace(projection, **changes)
    return replace(changed, projection_digest=_digest_json(changed.unsigned_record()))


def _campaign_rehash(receipts: Sequence[object]) -> Tuple[object, ...]:
    rebuilt = []
    prior = ZERO_DIGEST
    for number, receipt in enumerate(tuple(receipts), start=1):
        changed = replace(
            receipt,
            receipt_id=number,
            prior_hash=prior,
            receipt_hash=stage4._receipt_hash(
                number, receipt.kind, receipt.subject, receipt.payload, prior
            ),
        )
        rebuilt.append(changed)
        prior = changed.receipt_hash
    return tuple(rebuilt)


def _adapter_attack_reason(name: str, baseline: object) -> str:
    queue_adapter = stage4.QueueLiveAdapter()
    workflow_adapter = stage4.WorkflowLiveAdapter()
    queue_raw = baseline.queue_runtime_before.run.events
    workflow_raw = baseline.workflow_runtime_before.run.events
    queue_request = baseline.queue_adapter_report.requests[0]
    workflow_request = baseline.workflow_adapter_report.requests[0]

    if name == "MISSING_ADAPTER":
        return contract.evaluate_adapter(None, queue_raw, (queue_request,)).first_error

    if name == "IDENTITY_HASH_TAMPER":
        class BadIdentity(stage4.QueueLiveAdapter):
            def identity(self):
                return replace(super().identity(), host_instance="OTHER")
        return contract.evaluate_adapter(BadIdentity(), queue_raw, (queue_request,)).first_error

    if name == "IDENTITY_DRIFT":
        class Drifting(stage4.QueueLiveAdapter):
            def __init__(self):
                super().__init__()
                self.calls = 0
            def identity(self):
                self.calls += 1
                if self.calls == 1:
                    return self._identity
                return contract.build_adapter_identity(
                    adapter_id="DRIFTED",
                    adapter_version=STAGE_VERSION,
                    host_family="DETERMINISTIC_LEASE_QUEUE",
                    host_instance=stage4.QUEUE_HOST_ID,
                )
        return contract.evaluate_adapter(Drifting(), (), ()).first_error

    if name == "IDENTITY_EXCEPTION":
        class Broken(stage4.QueueLiveAdapter):
            def identity(self):
                raise RuntimeError("attack")
        return contract.evaluate_adapter(Broken(), (), ()).first_error

    if name == "EVENT_NORMALIZATION_EXCEPTION":
        class Broken(stage4.QueueLiveAdapter):
            def normalize_event(self, raw_event):
                raise RuntimeError("attack")
        return contract.evaluate_adapter(Broken(), queue_raw, (queue_request,)).first_error

    if name == "FOREIGN_EVENT_BINDING":
        class Foreign(stage4.QueueLiveAdapter):
            def normalize_event(self, raw_event):
                return workflow_adapter.normalize_event(workflow_raw[0])
        return contract.evaluate_adapter(Foreign(), (queue_raw[0],), ()).first_error

    if name == "EVENT_SEQUENCE_REWRITE":
        class Sequence(stage4.QueueLiveAdapter):
            def normalize_event(self, raw_event):
                event = super().normalize_event(raw_event)
                return contract.build_canonical_event(
                    self._identity,
                    sequence=event.sequence + 1,
                    event_id=event.event_id,
                    event_type=event.event_type,
                    subject_id=event.subject_id,
                    state_before=queue_host.ABSENT,
                    state_after=queue_host.READY,
                    attributes=event.attributes,
                )
        return contract.evaluate_adapter(Sequence(), (queue_raw[0],), ()).first_error

    if name == "DUPLICATE_EVENT_ID":
        class Duplicate(stage4.QueueLiveAdapter):
            def normalize_event(self, raw_event):
                event = super().normalize_event(raw_event)
                if event.sequence == 2:
                    raw = queue_raw[1]
                    return contract.build_canonical_event(
                        self._identity,
                        sequence=2,
                        event_id="QUEUE:1:LIVE-Q-001",
                        event_type=raw.event_type,
                        subject_id=raw.item_id,
                        state_before=raw.phase_before,
                        state_after=raw.phase_after,
                        attributes=(
                            ("operation", raw.operation),
                            ("reason", raw.reason),
                            ("version_after", raw.version_after),
                            ("version_before", raw.version_before),
                        ),
                    )
                return event
        return contract.evaluate_adapter(Duplicate(), queue_raw, ()).first_error

    if name == "STALE_SOURCE_EVENT":
        request = _request_like(queue_request, source_event_digest="f" * 64)
        return contract.evaluate_adapter(queue_adapter, queue_raw, (request,)).first_error

    if name == "REQUEST_SUBJECT_SWAP":
        request = _request_like(queue_request, subject_id="TASK-OTHER")
        return contract.evaluate_adapter(queue_adapter, queue_raw, (request,)).first_error

    if name == "EXPECTED_STATE_STALE":
        request = _request_like(queue_request, expected_state_digest="a" * 64)
        return contract.evaluate_adapter(queue_adapter, queue_raw, (request,)).first_error

    if name == "OUT_OF_SCOPE_ACTION":
        class HoldOnly(stage4.WorkflowLiveAdapter):
            def __init__(self):
                self._identity = contract.build_adapter_identity(
                    adapter_id="HOLD-ONLY-WORKFLOW",
                    adapter_version=STAGE_VERSION,
                    host_family="VERSIONED_FINITE_STATE_WORKFLOW",
                    host_instance=stage4.WORKFLOW_HOST_ID,
                    capabilities=(contract.HOLD,),
                )
        adapter = HoldOnly()
        events = tuple(adapter.normalize_event(item) for item in workflow_raw)
        request = stage4._request_for_event(
            action=contract.RELEASE,
            event=events[-1],
            session_digest=baseline.session_digest,
            authority_digest=workflow_request.authority_digest,
            current_epoch=502,
        )
        return contract.evaluate_adapter(adapter, workflow_raw, (request,)).first_error

    class ProjectionBase(stage4.QueueLiveAdapter):
        pass

    if name == "PROJECTION_EXCEPTION":
        class Attack(ProjectionBase):
            def project_action(self, request, event):
                raise RuntimeError("attack")
    elif name == "PROJECTION_EXECUTION_CLAIM":
        class Attack(ProjectionBase):
            def project_action(self, request, event):
                return contract.build_projection(
                    self._identity, request, event,
                    host_operation=queue_host.SUSPEND,
                    would_dispatch=True,
                    executed=True,
                )
    elif name == "PROJECTION_SUBJECT_SWAP":
        class Attack(ProjectionBase):
            def project_action(self, request, event):
                return _projection_rehash(
                    super().project_action(request, event), subject_id="TASK-OTHER"
                )
    elif name == "PROJECTION_ADAPTER_SWAP":
        class Attack(ProjectionBase):
            def project_action(self, request, event):
                return _projection_rehash(
                    super().project_action(request, event),
                    adapter_identity_digest="a" * 64,
                )
    elif name == "PROJECTION_EVENT_SWAP":
        class Attack(ProjectionBase):
            def project_action(self, request, event):
                return _projection_rehash(
                    super().project_action(request, event),
                    source_event_digest="a" * 64,
                )
    elif name == "PROJECTION_STATE_SWAP":
        class Attack(ProjectionBase):
            def project_action(self, request, event):
                return _projection_rehash(
                    super().project_action(request, event),
                    expected_state_digest="a" * 64,
                )
    else:
        raise KeyError(name)
    return contract.evaluate_adapter(Attack(), queue_raw, (queue_request,)).first_error


def _permit_attack_reason(name: str, baseline: object) -> str:
    runtime = baseline.queue_runtime_before
    identity = baseline.queue_adapter_report.identity
    event = baseline.queue_adapter_report.events[-1]
    request = baseline.queue_adapter_report.requests[0]
    projection = baseline.queue_adapter_report.projections[0]
    permit = baseline.queue_permit
    epoch = 500

    if name == "PERMIT_HASH_TAMPER":
        permit = replace(permit, permit_hash="a" * 64)
    elif name == "PERMIT_ID_REKEY":
        permit = _rehash_dataclass(replace(permit, permit_id="HP-FORGED"), "permit_hash")
    elif name == "PERMIT_ISSUER_SWAP":
        permit = _rehash_dataclass(replace(permit, issuer="ATTACKER"), "permit_hash")
    elif name == "PERMIT_SESSION_SWAP":
        permit = _rehash_dataclass(replace(permit, session_digest="a" * 64), "permit_hash")
    elif name == "PERMIT_HOST_SWAP":
        permit = _rehash_dataclass(replace(permit, host_id=stage4.WORKFLOW_HOST_ID), "permit_hash")
    elif name == "PERMIT_ADAPTER_SWAP":
        permit = _rehash_dataclass(replace(permit, adapter_identity_digest="a" * 64), "permit_hash")
    elif name == "PERMIT_REQUEST_SWAP":
        permit = _rehash_dataclass(replace(permit, request_digest="a" * 64), "permit_hash")
    elif name == "PERMIT_PROJECTION_SWAP":
        permit = _rehash_dataclass(replace(permit, projection_digest="a" * 64), "permit_hash")
    elif name == "PERMIT_ACTION_SWAP":
        permit = _rehash_dataclass(replace(permit, action=contract.RELEASE), "permit_hash")
    elif name == "PERMIT_OPERATION_SWAP":
        permit = _rehash_dataclass(replace(permit, host_operation=queue_host.DROP), "permit_hash")
    elif name == "PERMIT_SUBJECT_SWAP":
        permit = _rehash_dataclass(replace(permit, subject_id="TASK-OTHER"), "permit_hash")
    elif name == "PERMIT_EPOCH_SHIFT":
        permit = _rehash_dataclass(replace(permit, valid_epoch=501), "permit_hash")
    elif name == "PERMIT_REUSE":
        runtime = baseline.queue_runtime_after
    elif name == "NATIVE_STATE_DRIFT":
        commands = runtime.commands + (
            queue_host.QueueCommand("ATTACK-PRESTATE", stage4.SUBJECT_ID, queue_host.SUSPEND, 2),
        )
        runtime = stage4.make_queue_runtime(commands)
    else:
        raise KeyError(name)

    valid, reason = validate_execution_context(
        runtime,
        host_id=stage4.QUEUE_HOST_ID,
        identity=identity,
        event=event,
        request=request,
        projection=projection,
        permit=permit,
        current_epoch=epoch,
    )
    return "VALID" if valid else reason


def _substitution_attack_reason(name: str, baseline: object) -> str:
    checkpoint = baseline.checkpoint
    ticket = baseline.substitution_ticket
    outcome = baseline.queue_outcome
    detach = baseline.attachment_events[1]
    target = baseline.workflow_runtime_before
    consumed: Tuple[str, ...] = ()

    if name == "CHECKPOINT_SEMANTICS_REWRITE":
        checkpoint = _rehash_dataclass(
            replace(checkpoint, portable_state="ACTIVE"), "checkpoint_digest"
        )
    elif name == "CHECKPOINT_ID_REKEY":
        checkpoint = _rehash_dataclass(
            replace(checkpoint, checkpoint_id="CP-FORGED"), "checkpoint_digest"
        )
    elif name == "CHECKPOINT_OUTCOME_REBIND":
        checkpoint = _rehash_dataclass(
            replace(checkpoint, source_outcome_digest="a" * 64), "checkpoint_digest"
        )
    elif name == "TICKET_HASH_TAMPER":
        ticket = replace(ticket, ticket_hash="a" * 64)
    elif name == "TICKET_ID_REKEY":
        ticket = _rehash_dataclass(replace(ticket, ticket_id="ST-FORGED"), "ticket_hash")
    elif name == "TICKET_ISSUER_SWAP":
        ticket = _rehash_dataclass(replace(ticket, issuer="ATTACKER"), "ticket_hash")
    elif name == "TICKET_SESSION_SWAP":
        ticket = _rehash_dataclass(replace(ticket, session_digest="a" * 64), "ticket_hash")
    elif name == "TICKET_REUSE":
        consumed = (ticket.ticket_id,)
    elif name == "ATTACH_WITH_ACTIVE_HOST":
        first = baseline.attachment_events[0]
        second = stage4.build_attachment_event(
            sequence=2,
            event_type="ATTACH",
            host_id=stage4.WORKFLOW_HOST_ID,
            adapter_identity_digest=baseline.workflow_adapter_report.identity.identity_digest,
            session_digest=baseline.session_digest,
            checkpoint_digest=checkpoint.checkpoint_digest,
            prior_event_digest=first.event_digest,
        )
        return stage4.replay_attachment_events((first, second)).first_error
    elif name == "ATTACHMENT_REORDER":
        events = list(baseline.attachment_events)
        events[0], events[1] = events[1], events[0]
        return stage4.replay_attachment_events(tuple(events)).first_error
    else:
        raise KeyError(name)

    valid, reason = validate_substitution_context(
        ticket,
        checkpoint=checkpoint,
        queue_outcome=outcome,
        source_detach_event=detach,
        target_runtime=target,
        current_epoch=501,
        consumed_ticket_ids=consumed,
    )
    return "VALID" if valid else reason


def _receipt_attack_reason(name: str, baseline: object) -> str:
    receipts = list(baseline.receipts)
    if name == "CAMPAIGN_RECEIPT_TAMPER":
        receipts[7] = replace(receipts[7], payload="TAMPERED")
        return stage4.replay_campaign_receipts(tuple(receipts)).first_error
    if name == "CAMPAIGN_RECEIPT_REORDER":
        receipts[8], receipts[9] = receipts[9], receipts[8]
        return stage4.replay_campaign_receipts(tuple(receipts)).first_error
    if name == "REHASHED_SESSION_AUTHORITY":
        payload = json.loads(receipts[0].payload)
        payload["bolt_on_execution_authority"] = "DIRECT"
        receipts[0] = replace(receipts[0], payload=_canonical_json(payload))
    elif name == "REHASHED_PROJECTION_EXECUTION":
        payload = json.loads(receipts[4].payload)
        payload["executed"] = True
        receipts[4] = replace(receipts[4], payload=_canonical_json(payload))
    elif name == "REHASHED_HOST_TRANSITION":
        payload = json.loads(receipts[6].payload)
        payload["native_state_after"] = queue_host.COMPLETE
        unsigned = {key: value for key, value in payload.items() if key != "outcome_digest"}
        payload["outcome_digest"] = _digest_json(unsigned)
        receipts[6] = replace(receipts[6], payload=_canonical_json(payload))
    elif name == "REHASHED_SUMMARY":
        payload = json.loads(receipts[-1].payload)
        payload["actions"] = [contract.RELEASE, contract.HOLD]
        receipts[-1] = replace(receipts[-1], payload=_canonical_json(payload))
    else:
        raise KeyError(name)
    return stage4.replay_campaign_receipts(_campaign_rehash(receipts)).first_error


ATTACK_SPECS: Tuple[AttackSpec, ...] = (
    AttackSpec("A01", "ADAPTER", "missing adapter", "NO_ADAPTER"),
    AttackSpec("A02", "ADAPTER", "identity hash tamper", "IDENTITY_DIGEST_MISMATCH"),
    AttackSpec("A03", "ADAPTER", "identity drift", "ADAPTER_IDENTITY_CHANGED"),
    AttackSpec("A04", "ADAPTER", "identity exception", "ADAPTER_IDENTITY_EXCEPTION"),
    AttackSpec("A05", "ADAPTER", "event normalization exception", "EVENT_NORMALIZATION_EXCEPTION"),
    AttackSpec("A06", "ADAPTER", "foreign event binding", "EVENT_ADAPTER_BINDING_MISMATCH"),
    AttackSpec("A07", "ADAPTER", "event sequence rewrite", "EVENT_SEQUENCE_MISMATCH"),
    AttackSpec("A08", "ADAPTER", "duplicate event id", "DUPLICATE_EVENT_ID"),
    AttackSpec("A09", "ADAPTER", "stale source event", "SOURCE_EVENT_NOT_FOUND"),
    AttackSpec("A10", "ADAPTER", "request subject swap", "REQUEST_SUBJECT_MISMATCH"),
    AttackSpec("A11", "ADAPTER", "stale expected state", "EXPECTED_STATE_MISMATCH"),
    AttackSpec("A12", "ADAPTER", "out-of-scope action", "ACTION_OUT_OF_SCOPE"),
    AttackSpec("A13", "ADAPTER", "projection exception", "PROJECTION_EXCEPTION"),
    AttackSpec("A14", "ADAPTER", "projection execution claim", "HIDDEN_EXECUTION_AUTHORITY"),
    AttackSpec("A15", "ADAPTER", "projection subject swap", "PROJECTION_SUBJECT_MISMATCH"),
    AttackSpec("A16", "ADAPTER", "projection adapter swap", "PROJECTION_ADAPTER_MISMATCH"),
    AttackSpec("A17", "ADAPTER", "projection event swap", "PROJECTION_EVENT_MISMATCH"),
    AttackSpec("A18", "ADAPTER", "projection state swap", "PROJECTION_STATE_MISMATCH"),
    AttackSpec("P01", "PERMIT", "permit hash tamper", "PERMIT_HASH_MISMATCH"),
    AttackSpec("P02", "PERMIT", "permit id rekey", "PERMIT_ID_DERIVATION_MISMATCH"),
    AttackSpec("P03", "PERMIT", "permit issuer swap", "PERMIT_ISSUER_INVALID"),
    AttackSpec("P04", "PERMIT", "permit session swap", "PERMIT_SESSION_MISMATCH"),
    AttackSpec("P05", "PERMIT", "permit host swap", "PERMIT_HOST_MISMATCH"),
    AttackSpec("P06", "PERMIT", "permit adapter swap", "PERMIT_ADAPTER_MISMATCH"),
    AttackSpec("P07", "PERMIT", "permit request swap", "PERMIT_REQUEST_MISMATCH"),
    AttackSpec("P08", "PERMIT", "permit projection swap", "PERMIT_PROJECTION_MISMATCH"),
    AttackSpec("P09", "PERMIT", "permit action swap", "PERMIT_ACTION_MISMATCH"),
    AttackSpec("P10", "PERMIT", "permit operation swap", "PERMIT_OPERATION_MISMATCH"),
    AttackSpec("P11", "PERMIT", "permit subject swap", "PERMIT_SUBJECT_MISMATCH"),
    AttackSpec("P12", "PERMIT", "permit epoch shift", "PERMIT_EPOCH_MISMATCH"),
    AttackSpec("P13", "PERMIT", "permit reuse", "PERMIT_ALREADY_CONSUMED"),
    AttackSpec("P14", "PERMIT", "native state drift", "NATIVE_STATE_MISMATCH"),
    AttackSpec("S01", "SUBSTITUTION", "checkpoint semantic rewrite", "CHECKPOINT_SEMANTICS_INVALID"),
    AttackSpec("S02", "SUBSTITUTION", "checkpoint id rekey", "CHECKPOINT_ID_DERIVATION_MISMATCH"),
    AttackSpec("S03", "SUBSTITUTION", "checkpoint outcome rebind", "CHECKPOINT_OUTCOME_MISMATCH"),
    AttackSpec("S04", "SUBSTITUTION", "ticket hash tamper", "TICKET_HASH_MISMATCH"),
    AttackSpec("S05", "SUBSTITUTION", "ticket id rekey", "TICKET_ID_DERIVATION_MISMATCH"),
    AttackSpec("S06", "SUBSTITUTION", "ticket issuer swap", "TICKET_ISSUER_INVALID"),
    AttackSpec("S07", "SUBSTITUTION", "ticket session swap", "TICKET_SESSION_MISMATCH"),
    AttackSpec("S08", "SUBSTITUTION", "ticket reuse", "TICKET_ALREADY_CONSUMED"),
    AttackSpec("S09", "SUBSTITUTION", "attach with active host", "ATTACH_WITH_ACTIVE_HOST"),
    AttackSpec("S10", "SUBSTITUTION", "attachment reorder", "ATTACHMENT_SEQUENCE_MISMATCH"),
    AttackSpec("R01", "RECEIPT", "campaign receipt tamper", "RECEIPT_HASH_MISMATCH"),
    AttackSpec("R02", "RECEIPT", "campaign receipt reorder", "RECEIPT_ID_MISMATCH"),
    AttackSpec("R03", "RECEIPT", "rehashed session authority", "SESSION_AUTHORITY_INVALID"),
    AttackSpec("R04", "RECEIPT", "rehashed projection execution", "ADAPTER_EXECUTION_NONZERO"),
    AttackSpec("R05", "RECEIPT", "rehashed host transition", "QUEUE_TRANSITION_INVALID"),
    AttackSpec("R06", "RECEIPT", "rehashed summary", "CAMPAIGN_SUMMARY_INVALID"),
)


def run_attack(spec: AttackSpec, baseline: object) -> AttackResult:
    name_by_id = {
        "A01": "MISSING_ADAPTER",
        "A02": "IDENTITY_HASH_TAMPER",
        "A03": "IDENTITY_DRIFT",
        "A04": "IDENTITY_EXCEPTION",
        "A05": "EVENT_NORMALIZATION_EXCEPTION",
        "A06": "FOREIGN_EVENT_BINDING",
        "A07": "EVENT_SEQUENCE_REWRITE",
        "A08": "DUPLICATE_EVENT_ID",
        "A09": "STALE_SOURCE_EVENT",
        "A10": "REQUEST_SUBJECT_SWAP",
        "A11": "EXPECTED_STATE_STALE",
        "A12": "OUT_OF_SCOPE_ACTION",
        "A13": "PROJECTION_EXCEPTION",
        "A14": "PROJECTION_EXECUTION_CLAIM",
        "A15": "PROJECTION_SUBJECT_SWAP",
        "A16": "PROJECTION_ADAPTER_SWAP",
        "A17": "PROJECTION_EVENT_SWAP",
        "A18": "PROJECTION_STATE_SWAP",
        "P01": "PERMIT_HASH_TAMPER",
        "P02": "PERMIT_ID_REKEY",
        "P03": "PERMIT_ISSUER_SWAP",
        "P04": "PERMIT_SESSION_SWAP",
        "P05": "PERMIT_HOST_SWAP",
        "P06": "PERMIT_ADAPTER_SWAP",
        "P07": "PERMIT_REQUEST_SWAP",
        "P08": "PERMIT_PROJECTION_SWAP",
        "P09": "PERMIT_ACTION_SWAP",
        "P10": "PERMIT_OPERATION_SWAP",
        "P11": "PERMIT_SUBJECT_SWAP",
        "P12": "PERMIT_EPOCH_SHIFT",
        "P13": "PERMIT_REUSE",
        "P14": "NATIVE_STATE_DRIFT",
        "S01": "CHECKPOINT_SEMANTICS_REWRITE",
        "S02": "CHECKPOINT_ID_REKEY",
        "S03": "CHECKPOINT_OUTCOME_REBIND",
        "S04": "TICKET_HASH_TAMPER",
        "S05": "TICKET_ID_REKEY",
        "S06": "TICKET_ISSUER_SWAP",
        "S07": "TICKET_SESSION_SWAP",
        "S08": "TICKET_REUSE",
        "S09": "ATTACH_WITH_ACTIVE_HOST",
        "S10": "ATTACHMENT_REORDER",
        "R01": "CAMPAIGN_RECEIPT_TAMPER",
        "R02": "CAMPAIGN_RECEIPT_REORDER",
        "R03": "REHASHED_SESSION_AUTHORITY",
        "R04": "REHASHED_PROJECTION_EXECUTION",
        "R05": "REHASHED_HOST_TRANSITION",
        "R06": "REHASHED_SUMMARY",
    }
    before = (
        baseline.queue_runtime_before,
        baseline.queue_runtime_after,
        baseline.workflow_runtime_before,
        baseline.workflow_runtime_after,
        baseline.workflow_final_run,
    )
    name = name_by_id[spec.attack_id]
    if spec.category == "ADAPTER":
        observed = _adapter_attack_reason(name, baseline)
    elif spec.category == "PERMIT":
        observed = _permit_attack_reason(name, baseline)
    elif spec.category == "SUBSTITUTION":
        observed = _substitution_attack_reason(name, baseline)
    else:
        observed = _receipt_attack_reason(name, baseline)
    after = (
        baseline.queue_runtime_before,
        baseline.queue_runtime_after,
        baseline.workflow_runtime_before,
        baseline.workflow_runtime_after,
        baseline.workflow_final_run,
    )
    return _attack_result(spec, observed, host_state_unchanged=before == after)


def _receipt_hash(
    receipt_id: int, kind: str, subject: str, payload: str, prior_hash: str
) -> str:
    return _sha256_bytes(
        "|".join((str(receipt_id), kind, subject, payload, prior_hash)).encode("utf-8")
    )


def build_adversarial_receipts(
    baseline: object, attacks: Sequence[AttackResult]
) -> Tuple[AdversarialReceipt, ...]:
    receipts: list[AdversarialReceipt] = []
    prior = ZERO_DIGEST

    def append(kind: str, subject: str, payload: str) -> None:
        nonlocal prior
        receipt_id = len(receipts) + 1
        digest = _receipt_hash(receipt_id, kind, subject, payload, prior)
        receipts.append(
            AdversarialReceipt(receipt_id, kind, subject, payload, prior, digest)
        )
        prior = digest

    append(
        "SESSION",
        "OPEN",
        _canonical_json(
            {
                "attack_count": len(tuple(attacks)),
                "bolt_on_execution_authority": BOLT_ON_EXECUTION_AUTHORITY,
                "execution_boundary": EXECUTION_BOUNDARY,
                "mode": MODE,
                "stage": STAGE_NAME,
                "version": STAGE_VERSION,
            }
        ),
    )
    append(
        "BASELINE",
        "STAGE4",
        _canonical_json(
            {
                "bolt_on_executed_actions": baseline.bolt_on_executed_actions,
                "campaign_digest": baseline.campaign_digest,
                "executed_host_actions": baseline.executed_host_actions,
                "replay_digest": baseline.replay.final_digest,
                "replay_passed": baseline.replay.passed,
            }
        ),
    )
    for result in attacks:
        append("ATTACK", result.attack_id, result.canonical_line())
    categories = sorted({result.category for result in attacks})
    append(
        "SUMMARY",
        "ADVERSARIAL_CAMPAIGN",
        _canonical_json(
            {
                "attack_count": len(tuple(attacks)),
                "attack_host_actions": sum(item.attack_host_actions for item in attacks),
                "baseline_host_actions": baseline.executed_host_actions,
                "bolt_on_executed_actions": baseline.bolt_on_executed_actions
                + sum(item.bolt_on_executed_actions for item in attacks),
                "categories": categories,
                "host_state_preserved": all(item.host_state_unchanged for item in attacks),
                "rejected_count": sum(item.rejected for item in attacks),
            }
        ),
    )
    return tuple(receipts)


def replay_adversarial_receipts(
    receipts: Sequence[AdversarialReceipt],
) -> AdversarialReplay:
    receipt_tuple = tuple(receipts)
    prior = ZERO_DIGEST
    attack_count = 0
    rejected_count = 0
    attack_host_actions = 0
    bolt_on_actions = 0
    seen_ids: set[str] = set()

    for expected, receipt in enumerate(receipt_tuple, start=1):
        if receipt.receipt_id != expected:
            return AdversarialReplay(False, prior, expected - 1, attack_count, rejected_count, attack_host_actions, bolt_on_actions, f"RECEIPT_ID_MISMATCH:{expected}:{receipt.receipt_id}")
        if receipt.prior_hash != prior:
            return AdversarialReplay(False, prior, expected - 1, attack_count, rejected_count, attack_host_actions, bolt_on_actions, f"PRIOR_HASH_MISMATCH:{expected}")
        digest = _receipt_hash(
            receipt.receipt_id,
            receipt.kind,
            receipt.subject,
            receipt.payload,
            receipt.prior_hash,
        )
        if receipt.receipt_hash != digest:
            return AdversarialReplay(False, prior, expected - 1, attack_count, rejected_count, attack_host_actions, bolt_on_actions, f"RECEIPT_HASH_MISMATCH:{expected}")
        if receipt.kind == "SESSION":
            try:
                payload = json.loads(receipt.payload)
            except json.JSONDecodeError:
                return AdversarialReplay(False, prior, expected - 1, attack_count, rejected_count, attack_host_actions, bolt_on_actions, "SESSION_JSON_INVALID")
            if (
                payload.get("bolt_on_execution_authority") != "NONE"
                or payload.get("execution_boundary") != "HOST_BOUNDARY_ONLY"
                or payload.get("mode") != MODE
            ):
                return AdversarialReplay(False, prior, expected - 1, attack_count, rejected_count, attack_host_actions, bolt_on_actions, "SESSION_BOUNDARY_INVALID")
        elif receipt.kind == "BASELINE":
            try:
                payload = json.loads(receipt.payload)
            except json.JSONDecodeError:
                return AdversarialReplay(False, prior, expected - 1, attack_count, rejected_count, attack_host_actions, bolt_on_actions, "BASELINE_JSON_INVALID")
            if (
                payload.get("executed_host_actions") != 2
                or payload.get("bolt_on_executed_actions") != 0
                or payload.get("campaign_digest") != payload.get("replay_digest")
                or payload.get("replay_passed") is not True
            ):
                return AdversarialReplay(False, prior, expected - 1, attack_count, rejected_count, attack_host_actions, bolt_on_actions, "BASELINE_INVALID")
        elif receipt.kind == "ATTACK":
            try:
                payload = json.loads(receipt.payload)
            except json.JSONDecodeError:
                return AdversarialReplay(False, prior, expected - 1, attack_count, rejected_count, attack_host_actions, bolt_on_actions, "ATTACK_JSON_INVALID")
            result_digest = payload.pop("result_digest", None)
            if result_digest != _digest_json(payload):
                return AdversarialReplay(False, prior, expected - 1, attack_count, rejected_count, attack_host_actions, bolt_on_actions, "ATTACK_RESULT_DIGEST_MISMATCH")
            attack_id = payload.get("attack_id")
            if attack_id in seen_ids:
                return AdversarialReplay(False, prior, expected - 1, attack_count, rejected_count, attack_host_actions, bolt_on_actions, "DUPLICATE_ATTACK_ID")
            seen_ids.add(attack_id)
            if (
                payload.get("rejected") is not True
                or payload.get("observed_reason") != payload.get("expected_reason")
                or payload.get("host_state_unchanged") is not True
                or payload.get("attack_host_actions") != 0
                or payload.get("bolt_on_executed_actions") != 0
            ):
                return AdversarialReplay(False, prior, expected - 1, attack_count, rejected_count, attack_host_actions, bolt_on_actions, "ATTACK_NOT_SAFELY_REJECTED")
            attack_count += 1
            rejected_count += 1
            attack_host_actions += payload["attack_host_actions"]
            bolt_on_actions += payload["bolt_on_executed_actions"]
        elif receipt.kind == "SUMMARY":
            try:
                payload = json.loads(receipt.payload)
            except json.JSONDecodeError:
                return AdversarialReplay(False, prior, expected - 1, attack_count, rejected_count, attack_host_actions, bolt_on_actions, "SUMMARY_JSON_INVALID")
            if (
                payload.get("attack_count") != attack_count
                or payload.get("rejected_count") != rejected_count
                or payload.get("attack_host_actions") != attack_host_actions
                or payload.get("baseline_host_actions") != 2
                or payload.get("bolt_on_executed_actions") != bolt_on_actions
                or payload.get("host_state_preserved") is not True
                or payload.get("categories") != ["ADAPTER", "PERMIT", "RECEIPT", "SUBSTITUTION"]
            ):
                return AdversarialReplay(False, prior, expected - 1, attack_count, rejected_count, attack_host_actions, bolt_on_actions, "SUMMARY_INVALID")
        prior = digest

    if not receipt_tuple or receipt_tuple[0].kind != "SESSION" or receipt_tuple[-1].kind != "SUMMARY":
        return AdversarialReplay(False, prior, len(receipt_tuple), attack_count, rejected_count, attack_host_actions, bolt_on_actions, "RECEIPT_BOUNDARY_INVALID")
    return AdversarialReplay(True, prior, len(receipt_tuple), attack_count, rejected_count, attack_host_actions, bolt_on_actions, "NONE")


def run_adversarial_campaign() -> AdversarialCampaignReport:
    sources_before = _source_snapshot()
    baseline = stage4.run_live_substitution()
    attacks = tuple(run_attack(spec, baseline) for spec in ATTACK_SPECS)
    receipts = build_adversarial_receipts(baseline, attacks)
    replay = replay_adversarial_receipts(receipts)
    sources_after = _source_snapshot()
    return AdversarialCampaignReport(
        baseline=baseline,
        attacks=attacks,
        receipts=receipts,
        replay=replay,
        campaign_digest=receipts[-1].receipt_hash,
        attack_count=len(attacks),
        rejected_count=sum(item.rejected for item in attacks),
        attack_host_actions=sum(item.attack_host_actions for item in attacks),
        bolt_on_executed_actions=baseline.bolt_on_executed_actions
        + sum(item.bolt_on_executed_actions for item in attacks),
        categories=tuple(sorted({item.category for item in attacks})),
        sources_before=sources_before,
        sources_after=sources_after,
    )


def run_stage5_qualification(
    *,
    frozen_root: Path = FROZEN_V02_ROOT,
    expected_manifest_sha256: str = contract.EXPECTED_V02_RELEASE_MANIFEST_SHA256,
) -> Stage5Qualification:
    frozen_pre = contract.verify_frozen_v02(frozen_root, expected_manifest_sha256)
    source_before = _source_snapshot()
    report = run_adversarial_campaign()
    second = run_adversarial_campaign()
    source_after = _source_snapshot()
    frozen_post = contract.verify_frozen_v02(frozen_root, expected_manifest_sha256)

    source_map = dict(source_before)
    prior_bound = (
        source_map[CONTRACT_PATH.relative_to(REPOSITORY_ROOT).as_posix()]
        == EXPECTED_STAGE1_SOURCE_SHA256
        and source_map[STAGE2_PATH.relative_to(REPOSITORY_ROOT).as_posix()]
        == EXPECTED_STAGE2_SOURCE_SHA256
        and source_map[STAGE3_PATH.relative_to(REPOSITORY_ROOT).as_posix()]
        == EXPECTED_STAGE3_SOURCE_SHA256
        and source_map[STAGE4_PATH.relative_to(REPOSITORY_ROOT).as_posix()]
        == EXPECTED_STAGE4_SOURCE_SHA256
        and source_map[WORKFLOW_HOST_PATH.relative_to(REPOSITORY_ROOT).as_posix()]
        == EXPECTED_WORKFLOW_HOST_SOURCE_SHA256
        and source_map[QUEUE_HOST_PATH.relative_to(REPOSITORY_ROOT).as_posix()]
        == EXPECTED_QUEUE_HOST_SOURCE_SHA256
    )

    tampered = list(report.receipts)
    tampered[3] = replace(tampered[3], payload="TAMPERED")
    tamper_detection = not replay_adversarial_receipts(tuple(tampered)).passed

    reordered = list(report.receipts)
    reordered[3], reordered[4] = reordered[4], reordered[3]
    reorder_detection = not replay_adversarial_receipts(tuple(reordered)).passed

    semantic = list(report.receipts)
    attack_payload = json.loads(semantic[2].payload)
    attack_payload["rejected"] = False
    unsigned = {key: value for key, value in attack_payload.items() if key != "result_digest"}
    attack_payload["result_digest"] = _digest_json(unsigned)
    semantic[2] = replace(semantic[2], payload=_canonical_json(attack_payload))
    semantic = list(_rehash_adversarial_receipts(semantic))
    semantic_rehash_detection = (
        replay_adversarial_receipts(tuple(semantic)).first_error
        == "ATTACK_NOT_SAFELY_REJECTED"
    )

    queue_control, _ = validate_execution_context(
        report.baseline.queue_runtime_before,
        host_id=stage4.QUEUE_HOST_ID,
        identity=report.baseline.queue_adapter_report.identity,
        event=report.baseline.queue_adapter_report.events[-1],
        request=report.baseline.queue_adapter_report.requests[0],
        projection=report.baseline.queue_adapter_report.projections[0],
        permit=report.baseline.queue_permit,
        current_epoch=500,
    )
    workflow_control, _ = validate_execution_context(
        report.baseline.workflow_runtime_before,
        host_id=stage4.WORKFLOW_HOST_ID,
        identity=report.baseline.workflow_adapter_report.identity,
        event=report.baseline.workflow_adapter_report.events[-1],
        request=report.baseline.workflow_adapter_report.requests[0],
        projection=report.baseline.workflow_adapter_report.projections[0],
        permit=report.baseline.workflow_permit,
        current_epoch=502,
    )
    substitution_control, _ = validate_substitution_context(
        report.baseline.substitution_ticket,
        checkpoint=report.baseline.checkpoint,
        queue_outcome=report.baseline.queue_outcome,
        source_detach_event=report.baseline.attachment_events[1],
        target_runtime=report.baseline.workflow_runtime_before,
        current_epoch=501,
    )
    valid_controls = queue_control and workflow_control and substitution_control

    no_hidden_execution = (
        BOLT_ON_EXECUTION_AUTHORITY == "NONE"
        and not any(
            hasattr(contract.PortableHostAdapter, name)
            for name in ("execute", "apply", "dispatch", "mutate_host")
        )
        and report.bolt_on_executed_actions == 0
    )
    frozen_unchanged = frozen_pre.passed and frozen_post.passed and frozen_pre == frozen_post
    deterministic = report == second
    all_rejected = report.rejected_count == report.attack_count == len(ATTACK_SPECS)
    host_preserved = all(item.host_state_unchanged for item in report.attacks)
    passed = (
        frozen_pre.passed
        and frozen_post.passed
        and frozen_unchanged
        and prior_bound
        and source_before == source_after
        and report.sources_before == report.sources_after
        and report.baseline.replay.passed
        and report.baseline.campaign_digest == report.baseline.replay.final_digest
        and valid_controls
        and deterministic
        and all_rejected
        and host_preserved
        and report.replay.passed
        and report.campaign_digest == report.replay.final_digest
        and tamper_detection
        and reorder_detection
        and semantic_rehash_detection
        and no_hidden_execution
        and report.attack_host_actions == 0
        and report.baseline.executed_host_actions == 2
        and report.bolt_on_executed_actions == 0
    )
    return Stage5Qualification(
        passed=passed,
        stage_name=STAGE_NAME,
        stage_version=STAGE_VERSION,
        mode=MODE,
        bolt_on_execution_authority=BOLT_ON_EXECUTION_AUTHORITY,
        execution_boundary=EXECUTION_BOUNDARY,
        frozen_v02_pre_pass=frozen_pre.passed,
        frozen_v02_post_pass=frozen_post.passed,
        frozen_v02_unchanged=frozen_unchanged,
        prior_stage_sources_bound=prior_bound,
        sources_unchanged=source_before == source_after,
        baseline_stage4_pass=report.baseline.replay.passed,
        valid_control_contexts_pass=valid_controls,
        deterministic_second_pass=deterministic,
        all_attacks_rejected=all_rejected,
        host_state_preserved=host_preserved,
        adversarial_replay_pass=report.replay.passed,
        receipt_tamper_detection_pass=tamper_detection,
        receipt_reorder_detection_pass=reorder_detection,
        semantic_rehash_detection_pass=semantic_rehash_detection,
        no_hidden_execution_authority=no_hidden_execution,
        attack_count=report.attack_count,
        rejected_count=report.rejected_count,
        baseline_host_actions=report.baseline.executed_host_actions,
        attack_host_actions=report.attack_host_actions,
        bolt_on_executed_actions=report.bolt_on_executed_actions,
        category_count=len(report.categories),
        campaign_digest=report.campaign_digest,
        replay_digest=report.replay.final_digest,
        frozen_v02_manifest_sha256=frozen_pre.manifest_sha256,
    )


def _rehash_adversarial_receipts(
    receipts: Sequence[AdversarialReceipt],
) -> Tuple[AdversarialReceipt, ...]:
    rebuilt = []
    prior = ZERO_DIGEST
    for number, receipt in enumerate(tuple(receipts), start=1):
        digest = _receipt_hash(number, receipt.kind, receipt.subject, receipt.payload, prior)
        changed = replace(
            receipt,
            receipt_id=number,
            prior_hash=prior,
            receipt_hash=digest,
        )
        rebuilt.append(changed)
        prior = digest
    return tuple(rebuilt)


def main() -> int:
    qualification = run_stage5_qualification()
    print(f"Stage: {qualification.stage_name} {qualification.stage_version}")
    print(f"Mode: {qualification.mode}")
    print(f"Bolt-on execution authority: {qualification.bolt_on_execution_authority}")
    print(f"Execution boundary: {qualification.execution_boundary}")
    print(f"Frozen v0.2 manifest: {qualification.frozen_v02_manifest_sha256}")
    print(f"Attack categories: {qualification.category_count}")
    print(f"Attacks executed: {qualification.attack_count}")
    print(f"Attacks safely rejected: {qualification.rejected_count}")
    print(f"Baseline host actions: {qualification.baseline_host_actions}")
    print(f"Host actions during attacks: {qualification.attack_host_actions}")
    print(f"Bolt-on executed actions: {qualification.bolt_on_executed_actions}")
    print(f"Adversarial campaign digest: {qualification.campaign_digest}")
    print(f"Replay digest: {qualification.replay_digest}")
    if not qualification.passed:
        print("STAGE 5 ADVERSARIAL ADAPTER QUALIFICATION: FAIL")
        return 1
    print("STAGE 5 ADVERSARIAL ADAPTER QUALIFICATION: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
