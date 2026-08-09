#!/usr/bin/env python3
"""Second independent host qualification for Bolt-On Demonstrator v0.3.

Stage 2 attaches the Stage 1 portable adapter contract to a materially different
host without changing that host or granting the adapter execution authority.
The new host is a versioned finite-state workflow engine, not the arithmetic job
host used by the earlier demonstrator.

The workflow host runs directly first.  Its immutable event ledger is then
observed through a host-specific adapter.  HOLD and RELEASE are projected into
host-native PAUSE and RESUME operations, but no operation is executed in this
stage.  The direct host result, host source, Stage 1 contract source, input
commands, and frozen v0.2 release must remain unchanged.
"""

from __future__ import annotations

import ast
import hashlib
import importlib.util
import json
from dataclasses import dataclass, replace
from pathlib import Path
import sys
from typing import Sequence, Tuple

sys.dont_write_bytecode = True

STAGE_NAME = "SECOND INDEPENDENT HOST"
STAGE_VERSION = "0.3.2"
MODE = "SECOND_HOST_DRY_RUN_ATTACHMENT"
EXECUTION_AUTHORITY = "NONE"
ZERO_DIGEST = "0" * 64
EXPECTED_STAGE1_SOURCE_SHA256 = (
    "fe8b138db0069f1ac4a7832fd0f63d5ae30021cdfd5244e2476f8b3b52a4bbb9"
)

THIS_FILE = Path(__file__).resolve()
PROJECT_DIR = THIS_FILE.parents[1]
REPOSITORY_ROOT = THIS_FILE.parents[3]
CONTRACT_PATH = PROJECT_DIR / "portability" / "portable_adapter_contract.py"
HOST_PATH = PROJECT_DIR / "hosts" / "workflow_state_host.py"
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


contract = _load_module("bolt_on_v03_stage1_contract_for_stage2", CONTRACT_PATH)
workflow_host = _load_module("bolt_on_v03_independent_workflow_host", HOST_PATH)


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


def _source_snapshot() -> Tuple[Tuple[str, str], ...]:
    return tuple(
        (path.relative_to(REPOSITORY_ROOT).as_posix(), _sha256_file(path))
        for path in (CONTRACT_PATH, HOST_PATH, THIS_FILE)
    )


@dataclass(frozen=True)
class AttachmentReceipt:
    receipt_id: int
    kind: str
    subject: str
    payload: str
    prior_hash: str
    receipt_hash: str


@dataclass(frozen=True)
class AttachmentReplay:
    passed: bool
    final_digest: str
    checked_receipts: int
    first_error: str


@dataclass(frozen=True)
class SecondHostAttachmentReport:
    host_run: object
    adapter_report: object
    receipts: Tuple[AttachmentReceipt, ...]
    replay: AttachmentReplay
    attachment_digest: str
    source_hashes: Tuple[Tuple[str, str], ...]
    executed_actions: int


@dataclass(frozen=True)
class Stage2Qualification:
    passed: bool
    stage_name: str
    stage_version: str
    mode: str
    execution_authority: str
    host_name: str
    host_version: str
    frozen_v02_pre_pass: bool
    frozen_v02_post_pass: bool
    frozen_v02_unchanged: bool
    stage1_source_bound: bool
    host_independent_pass: bool
    material_difference_pass: bool
    direct_host_determinism_pass: bool
    direct_host_self_consistency_pass: bool
    adapter_attachment_pass: bool
    host_output_unchanged: bool
    input_unchanged: bool
    sources_unchanged: bool
    receipt_replay_pass: bool
    tamper_detection_pass: bool
    no_hidden_execution_authority: bool
    executed_actions: int
    command_count: int
    event_count: int
    host_run_digest: str
    adapter_report_digest: str
    attachment_digest: str
    frozen_v02_manifest_sha256: str


class WorkflowStateAdapter(contract.PortableHostAdapter):
    """Read-only Stage 1 adapter for the independent workflow host."""

    def __init__(self) -> None:
        self._identity = contract.build_adapter_identity(
            adapter_id="WORKFLOW-STATE-ADAPTER",
            adapter_version=STAGE_VERSION,
            host_family="VERSIONED_FINITE_STATE_WORKFLOW",
            host_instance="WORKFLOW-HOST-B",
            capabilities=contract.SUPPORTED_ACTIONS,
        )

    def identity(self):
        return self._identity

    def normalize_event(self, raw_event: object):
        if not isinstance(raw_event, workflow_host.WorkflowEvent):
            raise TypeError("workflow adapter requires WorkflowEvent input")
        return contract.build_canonical_event(
            self._identity,
            sequence=raw_event.sequence,
            event_id=f"WF:{raw_event.sequence}:{raw_event.command_id}",
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
                self._identity,
                request,
                event,
                host_operation="",
                would_dispatch=False,
                executed=False,
                reason_code="SOURCE_EVENT_NOT_APPLIED",
            )
        operation = {
            contract.HOLD: workflow_host.PAUSE,
            contract.RELEASE: workflow_host.RESUME,
        }[request.action]
        return contract.build_projection(
            self._identity,
            request,
            event,
            host_operation=operation,
            would_dispatch=True,
            executed=False,
            reason_code="SECOND_HOST_PROJECTION_READY",
        )


def _requests_for(
    adapter: WorkflowStateAdapter,
    host_run: object,
) -> Tuple[object, ...]:
    canonical_events = tuple(adapter.normalize_event(item) for item in host_run.events)
    by_operation = {
        raw.operation: canonical
        for raw, canonical in zip(host_run.events, canonical_events, strict=True)
        if raw.event_type == workflow_host.APPLIED
    }
    start_event = by_operation[workflow_host.START]
    checkpoint_event = by_operation[workflow_host.CHECKPOINT]
    session_digest = _digest_json({"session": "V03-STAGE-2-SECOND-HOST"})
    authority_digest = _digest_json(
        {
            "authority": "FROZEN-V02-HOLD-RELEASE",
            "stage1_source_sha256": EXPECTED_STAGE1_SOURCE_SHA256,
        }
    )
    return (
        contract.build_action_request(
            request_id=1,
            action=contract.HOLD,
            subject_id=start_event.subject_id,
            source_event_digest=start_event.event_digest,
            governance_session_digest=session_digest,
            authority_digest=authority_digest,
            expected_state_digest=start_event.state_after_digest,
            current_epoch=400,
        ),
        contract.build_action_request(
            request_id=2,
            action=contract.RELEASE,
            subject_id=checkpoint_event.subject_id,
            source_event_digest=checkpoint_event.event_digest,
            governance_session_digest=session_digest,
            authority_digest=authority_digest,
            expected_state_digest=checkpoint_event.state_before_digest,
            current_epoch=401,
        ),
    )


def _receipt_hash(
    receipt_id: int, kind: str, subject: str, payload: str, prior_hash: str
) -> str:
    return _sha256_bytes(
        "|".join((str(receipt_id), kind, subject, payload, prior_hash)).encode("utf-8")
    )


def build_attachment_receipts(
    host_run: object,
    adapter_report: object,
    source_hashes: Sequence[Tuple[str, str]],
    frozen_verification: object,
) -> Tuple[AttachmentReceipt, ...]:
    receipts: list[AttachmentReceipt] = []
    prior_hash = ZERO_DIGEST

    def append(kind: str, subject: str, payload: str) -> None:
        nonlocal prior_hash
        receipt_id = len(receipts) + 1
        receipt_hash = _receipt_hash(receipt_id, kind, subject, payload, prior_hash)
        receipts.append(
            AttachmentReceipt(
                receipt_id,
                kind,
                subject,
                payload,
                prior_hash,
                receipt_hash,
            )
        )
        prior_hash = receipt_hash

    append(
        "SESSION",
        "OPEN",
        _canonical_json(
            {
                "execution_authority": EXECUTION_AUTHORITY,
                "mode": MODE,
                "stage": STAGE_NAME,
                "version": STAGE_VERSION,
            }
        ),
    )
    append(
        "HOST",
        workflow_host.HOST_NAME,
        _canonical_json(
            {
                "commands": len(host_run.commands),
                "events": len(host_run.events),
                "host_version": workflow_host.HOST_VERSION,
                "run_digest": host_run.run_digest,
            }
        ),
    )
    append(
        "ADAPTER",
        adapter_report.identity.adapter_id,
        _canonical_json(
            {
                "adapter_identity_digest": adapter_report.identity.identity_digest,
                "adapter_report_digest": adapter_report.report_digest,
                "executed_actions": adapter_report.executed_actions,
            }
        ),
    )
    for path, digest in source_hashes:
        append("SOURCE", path, digest)
    append(
        "FROZEN",
        "BOLT_ON_V0.2",
        _canonical_json(
            {
                "checked_files": frozen_verification.checked_files,
                "manifest_sha256": frozen_verification.manifest_sha256,
                "tree_digest": frozen_verification.tree_digest,
            }
        ),
    )
    append(
        "SUMMARY",
        "SECOND_HOST_ATTACHMENT",
        _canonical_json(
            {
                "adapter_passed": adapter_report.passed,
                "executed_actions": adapter_report.executed_actions,
                "host_run_digest": host_run.run_digest,
                "receipt_replay_required": True,
            }
        ),
    )
    return tuple(receipts)


def replay_attachment_receipts(
    receipts: Sequence[AttachmentReceipt],
) -> AttachmentReplay:
    receipt_tuple = tuple(receipts)
    prior_hash = ZERO_DIGEST
    for expected_id, receipt in enumerate(receipt_tuple, start=1):
        if receipt.receipt_id != expected_id:
            return AttachmentReplay(
                False,
                prior_hash,
                expected_id - 1,
                f"RECEIPT_ID_MISMATCH:{expected_id}:{receipt.receipt_id}",
            )
        if receipt.prior_hash != prior_hash:
            return AttachmentReplay(
                False, prior_hash, expected_id - 1, f"PRIOR_HASH_MISMATCH:{expected_id}"
            )
        expected_hash = _receipt_hash(
            receipt.receipt_id,
            receipt.kind,
            receipt.subject,
            receipt.payload,
            receipt.prior_hash,
        )
        if receipt.receipt_hash != expected_hash:
            return AttachmentReplay(
                False,
                prior_hash,
                expected_id - 1,
                f"RECEIPT_HASH_MISMATCH:{expected_id}",
            )
        prior_hash = expected_hash
    if not receipt_tuple:
        return AttachmentReplay(False, prior_hash, 0, "EMPTY_RECEIPT_STREAM")
    if receipt_tuple[0].kind != "SESSION" or receipt_tuple[-1].kind != "SUMMARY":
        return AttachmentReplay(False, prior_hash, len(receipt_tuple), "BOUNDARY_INVALID")
    try:
        summary = json.loads(receipt_tuple[-1].payload)
    except json.JSONDecodeError:
        return AttachmentReplay(False, prior_hash, len(receipt_tuple), "SUMMARY_JSON_INVALID")
    if summary.get("executed_actions") != 0:
        return AttachmentReplay(
            False, prior_hash, len(receipt_tuple), "SUMMARY_EXECUTION_NONZERO"
        )
    if summary.get("adapter_passed") is not True:
        return AttachmentReplay(False, prior_hash, len(receipt_tuple), "ADAPTER_NOT_PASSED")
    return AttachmentReplay(True, prior_hash, len(receipt_tuple), "NONE")


def attach_second_host(
    commands: Sequence[object] | None = None,
    *,
    frozen_root: Path = FROZEN_V02_ROOT,
    expected_manifest_sha256: str = contract.EXPECTED_V02_RELEASE_MANIFEST_SHA256,
) -> SecondHostAttachmentReport:
    command_tuple = tuple(
        workflow_host.baseline_commands() if commands is None else commands
    )
    host_run = workflow_host.run_workflow(command_tuple)
    adapter = WorkflowStateAdapter()
    requests = _requests_for(adapter, host_run)
    adapter_report = contract.evaluate_adapter(adapter, host_run.events, requests)
    frozen = contract.verify_frozen_v02(frozen_root, expected_manifest_sha256)
    sources = _source_snapshot()
    receipts = build_attachment_receipts(host_run, adapter_report, sources, frozen)
    replay = replay_attachment_receipts(receipts)
    return SecondHostAttachmentReport(
        host_run=host_run,
        adapter_report=adapter_report,
        receipts=receipts,
        replay=replay,
        attachment_digest=receipts[-1].receipt_hash if receipts else ZERO_DIGEST,
        source_hashes=sources,
        executed_actions=adapter_report.executed_actions,
    )


def _host_independent() -> bool:
    tree = ast.parse(HOST_PATH.read_text(encoding="utf-8"))
    imported: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.extend(alias.name.lower() for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            imported.append((node.module or "").lower())
    prohibited = ("portable_adapter_contract", "natural_math", "cntm", "governance", "bolt_on")
    return not any(token in module for module in imported for token in prohibited)


def _materially_different() -> bool:
    return (
        hasattr(workflow_host, "WorkflowCommand")
        and hasattr(workflow_host, "WorkflowRecord")
        and hasattr(workflow_host, "WorkflowEvent")
        and hasattr(workflow_host, "run_workflow")
        and not hasattr(workflow_host, "Job")
        and not hasattr(workflow_host, "run_jobs")
        and isinstance(workflow_host.SUPPORTED_OPERATIONS, tuple)
        and set(workflow_host.SUPPORTED_OPERATIONS)
        == {
            workflow_host.REGISTER,
            workflow_host.START,
            workflow_host.CHECKPOINT,
            workflow_host.PAUSE,
            workflow_host.RESUME,
            workflow_host.COMPLETE,
            workflow_host.CANCEL,
        }
    )


def run_stage2_qualification(
    *,
    frozen_root: Path = FROZEN_V02_ROOT,
    expected_manifest_sha256: str = contract.EXPECTED_V02_RELEASE_MANIFEST_SHA256,
) -> Stage2Qualification:
    frozen_pre = contract.verify_frozen_v02(frozen_root, expected_manifest_sha256)
    source_before = _source_snapshot()
    contract_sha_before = _sha256_file(CONTRACT_PATH)
    commands = workflow_host.baseline_commands()
    input_before = repr(commands)

    first_run = workflow_host.run_workflow(commands)
    second_run = workflow_host.run_workflow(commands)
    attachment = attach_second_host(
        commands,
        frozen_root=frozen_root,
        expected_manifest_sha256=expected_manifest_sha256,
    )
    final_run = workflow_host.run_workflow(commands)

    source_after = _source_snapshot()
    contract_sha_after = _sha256_file(CONTRACT_PATH)
    input_after = repr(commands)
    frozen_post = contract.verify_frozen_v02(frozen_root, expected_manifest_sha256)

    tampered = list(attachment.receipts)
    tampered[1] = replace(tampered[1], payload="TAMPERED")
    tamper_detection_pass = not replay_attachment_receipts(tuple(tampered)).passed

    stage1_source_bound = (
        contract_sha_before == EXPECTED_STAGE1_SOURCE_SHA256
        and contract_sha_after == EXPECTED_STAGE1_SOURCE_SHA256
    )
    direct_host_determinism_pass = first_run == second_run == final_run
    direct_host_self_consistency_pass = (
        len(first_run.commands) == 4
        and len(first_run.events) == 4
        and not first_run.rejected_command_ids
        and first_run.final_records
        == (workflow_host.WorkflowRecord("TASK-7", workflow_host.DONE, 4),)
        and _sha256_bytes(first_run.canonical_text().encode("utf-8"))
        == first_run.run_digest
    )
    adapter_attachment_pass = (
        attachment.adapter_report.passed
        and attachment.adapter_report.replay.passed
        and tuple(item.action for item in attachment.adapter_report.outcomes)
        == (contract.HOLD, contract.RELEASE)
        and tuple(item.host_operation for item in attachment.adapter_report.outcomes)
        == (workflow_host.PAUSE, workflow_host.RESUME)
    )
    host_output_unchanged = attachment.host_run == first_run == final_run
    sources_unchanged = source_before == source_after
    frozen_unchanged = frozen_pre.passed and frozen_post.passed and frozen_pre == frozen_post
    no_hidden_execution_authority = (
        EXECUTION_AUTHORITY == "NONE"
        and attachment.executed_actions == 0
        and not any(item.executed for item in attachment.adapter_report.outcomes)
        and not any(
            hasattr(contract.PortableHostAdapter, name)
            for name in ("execute", "apply", "dispatch", "mutate_host")
        )
    )
    passed = (
        frozen_pre.passed
        and frozen_post.passed
        and frozen_unchanged
        and stage1_source_bound
        and _host_independent()
        and _materially_different()
        and direct_host_determinism_pass
        and direct_host_self_consistency_pass
        and adapter_attachment_pass
        and host_output_unchanged
        and input_before == input_after
        and sources_unchanged
        and attachment.replay.passed
        and attachment.replay.final_digest == attachment.attachment_digest
        and tamper_detection_pass
        and no_hidden_execution_authority
    )
    return Stage2Qualification(
        passed=passed,
        stage_name=STAGE_NAME,
        stage_version=STAGE_VERSION,
        mode=MODE,
        execution_authority=EXECUTION_AUTHORITY,
        host_name=workflow_host.HOST_NAME,
        host_version=workflow_host.HOST_VERSION,
        frozen_v02_pre_pass=frozen_pre.passed,
        frozen_v02_post_pass=frozen_post.passed,
        frozen_v02_unchanged=frozen_unchanged,
        stage1_source_bound=stage1_source_bound,
        host_independent_pass=_host_independent(),
        material_difference_pass=_materially_different(),
        direct_host_determinism_pass=direct_host_determinism_pass,
        direct_host_self_consistency_pass=direct_host_self_consistency_pass,
        adapter_attachment_pass=adapter_attachment_pass,
        host_output_unchanged=host_output_unchanged,
        input_unchanged=input_before == input_after,
        sources_unchanged=sources_unchanged,
        receipt_replay_pass=attachment.replay.passed,
        tamper_detection_pass=tamper_detection_pass,
        no_hidden_execution_authority=no_hidden_execution_authority,
        executed_actions=attachment.executed_actions,
        command_count=len(first_run.commands),
        event_count=len(first_run.events),
        host_run_digest=first_run.run_digest,
        adapter_report_digest=attachment.adapter_report.report_digest,
        attachment_digest=attachment.attachment_digest,
        frozen_v02_manifest_sha256=frozen_pre.manifest_sha256,
    )


def main() -> int:
    qualification = run_stage2_qualification()
    print(f"Stage: {qualification.stage_name} {qualification.stage_version}")
    print(f"Host: {qualification.host_name} {qualification.host_version}")
    print(f"Mode: {qualification.mode}")
    print(f"Execution authority: {qualification.execution_authority}")
    print(f"Frozen v0.2 manifest: {qualification.frozen_v02_manifest_sha256}")
    print(f"Commands: {qualification.command_count}")
    print(f"Events: {qualification.event_count}")
    print(f"Host run digest: {qualification.host_run_digest}")
    print(f"Adapter report digest: {qualification.adapter_report_digest}")
    print(f"Attachment digest: {qualification.attachment_digest}")
    print(f"Executed actions: {qualification.executed_actions}")
    if not qualification.passed:
        print("STAGE 2 SECOND INDEPENDENT HOST QUALIFICATION: FAIL")
        return 1
    print("STAGE 2 SECOND INDEPENDENT HOST QUALIFICATION: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
