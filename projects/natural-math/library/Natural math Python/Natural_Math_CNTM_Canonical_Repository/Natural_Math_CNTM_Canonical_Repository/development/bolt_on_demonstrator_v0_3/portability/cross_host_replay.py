#!/usr/bin/env python3
"""Equivalent-event cross-host replay for Bolt-On Demonstrator v0.3.

Stage 3 proves that materially different host evidence can be normalized into
one exact portable event stream and replayed independently without granting the
bolt-on execution authority.

Two ledgers are deliberately kept separate:

* the host-evidence ledger binds each portable event to its host-specific raw
  evidence and therefore differs across hosts;
* the portable replay ledger contains only the qualified host-neutral semantic
  events and therefore must be byte-for-byte identical across hosts.

The stage does not execute HOLD or RELEASE.  It replays their portable meaning
only.  Frozen v0.2 and all prior v0.3 stage sources are verified before and
after qualification.
"""

from __future__ import annotations

import hashlib
import importlib.util
import json
from dataclasses import dataclass, replace
from pathlib import Path
import sys
from typing import Iterable, Mapping, Sequence, Tuple

sys.dont_write_bytecode = True

STAGE_NAME = "EQUIVALENT-EVENT CROSS-HOST REPLAY"
STAGE_VERSION = "0.3.3"
MODE = "CROSS_HOST_REPLAY_ONLY"
EXECUTION_AUTHORITY = "NONE"
ZERO_DIGEST = "0" * 64

EXPECTED_STAGE1_SOURCE_SHA256 = (
    "fe8b138db0069f1ac4a7832fd0f63d5ae30021cdfd5244e2476f8b3b52a4bbb9"
)
EXPECTED_STAGE2_SOURCE_SHA256 = (
    "44801c04e6b3765387bfc4e4b7fb8d71f2ebfc3534c67cc428d778d412c8c03a"
)
EXPECTED_WORKFLOW_HOST_SOURCE_SHA256 = (
    "c940594a409fe7b159ac5c8843ea00100279f754a3db6911662dbc9553222847"
)

PORTABLE_SUBJECT = "TASK-7"
ACTIVATED = "ACTIVATED"
CONTROL_POINT = "CONTROL_POINT"
READY = "READY"
ACTIVE = "ACTIVE"
AT_CONTROL_POINT = "AT_CONTROL_POINT"
SUPPORTED_PORTABLE_EVENTS = (ACTIVATED, CONTROL_POINT)
SUPPORTED_PORTABLE_STATES = (READY, ACTIVE, AT_CONTROL_POINT)

THIS_FILE = Path(__file__).resolve()
PROJECT_DIR = THIS_FILE.parents[1]
REPOSITORY_ROOT = THIS_FILE.parents[3]
CONTRACT_PATH = PROJECT_DIR / "portability" / "portable_adapter_contract.py"
STAGE2_PATH = PROJECT_DIR / "portability" / "second_independent_host.py"
WORKFLOW_HOST_PATH = PROJECT_DIR / "hosts" / "workflow_state_host.py"
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


contract = _load_module("bolt_on_v03_stage1_contract_for_stage3", CONTRACT_PATH)
stage2 = _load_module("bolt_on_v03_stage2_attachment_for_stage3", STAGE2_PATH)
workflow_host = stage2.workflow_host


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
        for path in (CONTRACT_PATH, STAGE2_PATH, WORKFLOW_HOST_PATH, THIS_FILE)
    )


@dataclass(frozen=True)
class PortableReplayEvent:
    sequence: int
    semantic_id: str
    event_type: str
    subject_id: str
    state_before: str
    state_after: str
    action: str
    semantic_digest: str

    def unsigned_record(self) -> dict[str, object]:
        return {
            "action": self.action,
            "event_type": self.event_type,
            "semantic_id": self.semantic_id,
            "sequence": self.sequence,
            "state_after": self.state_after,
            "state_before": self.state_before,
            "subject_id": self.subject_id,
        }

    def canonical_line(self) -> str:
        return _canonical_json(
            {**self.unsigned_record(), "semantic_digest": self.semantic_digest}
        )


@dataclass(frozen=True)
class HostEvidenceBinding:
    host_id: str
    host_family: str
    host_run_digest: str
    raw_event_digest: str
    portable_semantic_digest: str
    source_sequence: int
    binding_digest: str

    def unsigned_record(self) -> dict[str, object]:
        return {
            "host_family": self.host_family,
            "host_id": self.host_id,
            "host_run_digest": self.host_run_digest,
            "portable_semantic_digest": self.portable_semantic_digest,
            "raw_event_digest": self.raw_event_digest,
            "source_sequence": self.source_sequence,
        }

    def canonical_line(self) -> str:
        return _canonical_json(
            {**self.unsigned_record(), "binding_digest": self.binding_digest}
        )


@dataclass(frozen=True)
class ReplayReceipt:
    receipt_id: int
    kind: str
    subject: str
    payload: str
    prior_hash: str
    receipt_hash: str


@dataclass(frozen=True)
class PortableReplayResult:
    passed: bool
    final_digest: str
    checked_receipts: int
    final_state: str
    actions: Tuple[str, ...]
    semantic_stream_digest: str
    first_error: str


@dataclass(frozen=True)
class EvidenceReplayResult:
    passed: bool
    final_digest: str
    checked_receipts: int
    host_id: str
    binding_count: int
    first_error: str


@dataclass(frozen=True)
class CrossHostProjectionReport:
    host_id: str
    host_family: str
    host_run_digest: str
    portable_events: Tuple[PortableReplayEvent, ...]
    evidence_bindings: Tuple[HostEvidenceBinding, ...]
    portable_receipts: Tuple[ReplayReceipt, ...]
    evidence_receipts: Tuple[ReplayReceipt, ...]
    portable_replay: PortableReplayResult
    evidence_replay: EvidenceReplayResult
    semantic_stream_digest: str
    portable_ledger_digest: str
    evidence_ledger_digest: str
    report_digest: str
    passed: bool
    executed_actions: int
    first_error: str


@dataclass(frozen=True)
class Stage3Qualification:
    passed: bool
    stage_name: str
    stage_version: str
    mode: str
    execution_authority: str
    frozen_v02_pre_pass: bool
    frozen_v02_post_pass: bool
    frozen_v02_unchanged: bool
    prior_stage_sources_bound: bool
    sources_unchanged: bool
    inputs_unchanged: bool
    workflow_host_unchanged: bool
    queue_projection_pass: bool
    workflow_projection_pass: bool
    semantic_events_equivalent: bool
    semantic_stream_digest_equivalent: bool
    portable_ledgers_identical: bool
    portable_replay_equivalent: bool
    host_evidence_distinct: bool
    host_evidence_replay_pass: bool
    portable_tamper_detection_pass: bool
    evidence_tamper_detection_pass: bool
    reorder_detection_pass: bool
    no_hidden_execution_authority: bool
    executed_actions: int
    portable_event_count: int
    portable_semantic_stream_digest: str
    portable_ledger_digest: str
    queue_evidence_ledger_digest: str
    workflow_evidence_ledger_digest: str
    cross_host_replay_digest: str
    frozen_v02_manifest_sha256: str


class CrossHostSemanticAdapter:
    """Read-only semantic adapter surface.  No execution callback exists."""

    host_id: str
    host_family: str

    def project(self, raw_events: Iterable[object], host_run_digest: str):
        raise NotImplementedError


def build_portable_event(
    *,
    sequence: int,
    semantic_id: str,
    event_type: str,
    subject_id: str,
    state_before: str,
    state_after: str,
    action: str,
) -> PortableReplayEvent:
    sequence = _exact_int(sequence, "sequence", minimum=1)
    event_type = _nonempty_text(event_type, "event_type").upper()
    state_before = _nonempty_text(state_before, "state_before").upper()
    state_after = _nonempty_text(state_after, "state_after").upper()
    action = _nonempty_text(action, "action").upper()
    if event_type not in SUPPORTED_PORTABLE_EVENTS:
        raise ValueError("unsupported portable event type")
    if state_before not in SUPPORTED_PORTABLE_STATES or state_after not in SUPPORTED_PORTABLE_STATES:
        raise ValueError("unsupported portable state")
    if action not in contract.SUPPORTED_ACTIONS:
        raise ValueError("unsupported portable action")
    unsigned = {
        "action": action,
        "event_type": event_type,
        "semantic_id": _nonempty_text(semantic_id, "semantic_id"),
        "sequence": sequence,
        "state_after": state_after,
        "state_before": state_before,
        "subject_id": _nonempty_text(subject_id, "subject_id"),
    }
    return PortableReplayEvent(
        sequence=sequence,
        semantic_id=unsigned["semantic_id"],
        event_type=event_type,
        subject_id=unsigned["subject_id"],
        state_before=state_before,
        state_after=state_after,
        action=action,
        semantic_digest=_digest_json(unsigned),
    )


def validate_portable_event(event: PortableReplayEvent) -> Tuple[bool, str]:
    if not isinstance(event, PortableReplayEvent):
        return False, "PORTABLE_EVENT_TYPE_INVALID"
    try:
        expected = build_portable_event(
            sequence=event.sequence,
            semantic_id=event.semantic_id,
            event_type=event.event_type,
            subject_id=event.subject_id,
            state_before=event.state_before,
            state_after=event.state_after,
            action=event.action,
        )
    except (TypeError, ValueError):
        return False, "PORTABLE_EVENT_FIELDS_INVALID"
    if event.semantic_digest != expected.semantic_digest:
        return False, "PORTABLE_EVENT_DIGEST_MISMATCH"
    return True, "VALID"


def build_evidence_binding(
    *,
    host_id: str,
    host_family: str,
    host_run_digest: str,
    raw_event_digest: str,
    portable_event: PortableReplayEvent,
    source_sequence: int,
) -> HostEvidenceBinding:
    source_sequence = _exact_int(source_sequence, "source_sequence", minimum=1)
    for name, digest in (
        ("host_run_digest", host_run_digest),
        ("raw_event_digest", raw_event_digest),
        ("portable_semantic_digest", portable_event.semantic_digest),
    ):
        if not _is_digest(digest):
            raise ValueError(f"{name} must be a lowercase SHA-256 digest")
    unsigned = {
        "host_family": _nonempty_text(host_family, "host_family"),
        "host_id": _nonempty_text(host_id, "host_id"),
        "host_run_digest": host_run_digest,
        "portable_semantic_digest": portable_event.semantic_digest,
        "raw_event_digest": raw_event_digest,
        "source_sequence": source_sequence,
    }
    return HostEvidenceBinding(
        host_id=unsigned["host_id"],
        host_family=unsigned["host_family"],
        host_run_digest=host_run_digest,
        raw_event_digest=raw_event_digest,
        portable_semantic_digest=portable_event.semantic_digest,
        source_sequence=source_sequence,
        binding_digest=_digest_json(unsigned),
    )


def validate_evidence_binding(binding: HostEvidenceBinding) -> Tuple[bool, str]:
    if not isinstance(binding, HostEvidenceBinding):
        return False, "EVIDENCE_BINDING_TYPE_INVALID"
    try:
        portable = PortableReplayEvent(
            sequence=1,
            semantic_id="VALIDATION",
            event_type=ACTIVATED,
            subject_id=PORTABLE_SUBJECT,
            state_before=READY,
            state_after=ACTIVE,
            action=contract.HOLD,
            semantic_digest=binding.portable_semantic_digest,
        )
        # build_evidence_binding only consumes the semantic digest from portable.
        expected = build_evidence_binding(
            host_id=binding.host_id,
            host_family=binding.host_family,
            host_run_digest=binding.host_run_digest,
            raw_event_digest=binding.raw_event_digest,
            portable_event=portable,
            source_sequence=binding.source_sequence,
        )
    except (TypeError, ValueError):
        return False, "EVIDENCE_BINDING_FIELDS_INVALID"
    if binding.binding_digest != expected.binding_digest:
        return False, "EVIDENCE_BINDING_DIGEST_MISMATCH"
    return True, "VALID"


def _semantic_stream_digest(events: Sequence[PortableReplayEvent]) -> str:
    return _digest_json([event.semantic_digest for event in events])


def _receipt_hash(
    receipt_id: int, kind: str, subject: str, payload: str, prior_hash: str
) -> str:
    return _sha256_bytes(
        "|".join((str(receipt_id), kind, subject, payload, prior_hash)).encode("utf-8")
    )


def _append_receipt(
    receipts: list[ReplayReceipt], kind: str, subject: str, payload: str
) -> None:
    prior_hash = receipts[-1].receipt_hash if receipts else ZERO_DIGEST
    receipt_id = len(receipts) + 1
    receipt_hash = _receipt_hash(receipt_id, kind, subject, payload, prior_hash)
    receipts.append(
        ReplayReceipt(receipt_id, kind, subject, payload, prior_hash, receipt_hash)
    )


def build_portable_receipts(
    events: Sequence[PortableReplayEvent],
) -> Tuple[ReplayReceipt, ...]:
    event_tuple = tuple(events)
    receipts: list[ReplayReceipt] = []
    _append_receipt(
        receipts,
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
    for event in event_tuple:
        _append_receipt(receipts, "PORTABLE_EVENT", event.semantic_id, event.canonical_line())
    _append_receipt(
        receipts,
        "SUMMARY",
        "PORTABLE_REPLAY",
        _canonical_json(
            {
                "actions": [event.action for event in event_tuple],
                "events": len(event_tuple),
                "executed_actions": 0,
                "final_state": event_tuple[-1].state_after if event_tuple else READY,
                "semantic_stream_digest": _semantic_stream_digest(event_tuple),
            }
        ),
    )
    return tuple(receipts)


def build_evidence_receipts(
    host_id: str,
    host_family: str,
    host_run_digest: str,
    bindings: Sequence[HostEvidenceBinding],
) -> Tuple[ReplayReceipt, ...]:
    binding_tuple = tuple(bindings)
    receipts: list[ReplayReceipt] = []
    _append_receipt(
        receipts,
        "EVIDENCE_SESSION",
        host_id,
        _canonical_json(
            {
                "execution_authority": EXECUTION_AUTHORITY,
                "host_family": host_family,
                "host_id": host_id,
                "host_run_digest": host_run_digest,
                "mode": MODE,
            }
        ),
    )
    for binding in binding_tuple:
        _append_receipt(
            receipts,
            "EVIDENCE_BINDING",
            f"SOURCE:{binding.source_sequence}",
            binding.canonical_line(),
        )
    _append_receipt(
        receipts,
        "EVIDENCE_SUMMARY",
        host_id,
        _canonical_json(
            {
                "bindings": len(binding_tuple),
                "executed_actions": 0,
                "host_id": host_id,
                "portable_semantic_digests": [
                    item.portable_semantic_digest for item in binding_tuple
                ],
            }
        ),
    )
    return tuple(receipts)


def _verify_chain(receipts: Sequence[ReplayReceipt]) -> Tuple[bool, str, int, str]:
    receipt_tuple = tuple(receipts)
    prior_hash = ZERO_DIGEST
    for expected_id, receipt in enumerate(receipt_tuple, start=1):
        if receipt.receipt_id != expected_id:
            return False, prior_hash, expected_id - 1, "RECEIPT_ID_MISMATCH"
        if receipt.prior_hash != prior_hash:
            return False, prior_hash, expected_id - 1, "PRIOR_HASH_MISMATCH"
        expected_hash = _receipt_hash(
            receipt.receipt_id,
            receipt.kind,
            receipt.subject,
            receipt.payload,
            receipt.prior_hash,
        )
        if receipt.receipt_hash != expected_hash:
            return False, prior_hash, expected_id - 1, "RECEIPT_HASH_MISMATCH"
        prior_hash = expected_hash
    if not receipt_tuple:
        return False, prior_hash, 0, "EMPTY_RECEIPT_STREAM"
    return True, prior_hash, len(receipt_tuple), "NONE"


def replay_portable_receipts(
    receipts: Sequence[ReplayReceipt],
) -> PortableReplayResult:
    receipt_tuple = tuple(receipts)
    chain_ok, final_digest, checked, error = _verify_chain(receipt_tuple)
    if not chain_ok:
        return PortableReplayResult(
            False, final_digest, checked, "", (), ZERO_DIGEST, error
        )
    if receipt_tuple[0].kind != "SESSION" or receipt_tuple[-1].kind != "SUMMARY":
        return PortableReplayResult(
            False, final_digest, checked, "", (), ZERO_DIGEST, "PORTABLE_BOUNDARY_INVALID"
        )
    try:
        session = json.loads(receipt_tuple[0].payload)
    except json.JSONDecodeError:
        return PortableReplayResult(
            False, final_digest, checked, "", (), ZERO_DIGEST, "SESSION_JSON_INVALID"
        )
    if session.get("execution_authority") != "NONE":
        return PortableReplayResult(
            False, final_digest, checked, "", (), ZERO_DIGEST, "EXECUTION_AUTHORITY_NONZERO"
        )

    state = READY
    subject = ""
    actions: list[str] = []
    semantic_digests: list[str] = []
    event_count = 0
    for receipt in receipt_tuple[1:-1]:
        if receipt.kind != "PORTABLE_EVENT":
            return PortableReplayResult(
                False,
                final_digest,
                checked,
                state,
                tuple(actions),
                ZERO_DIGEST,
                "UNEXPECTED_PORTABLE_RECEIPT_KIND",
            )
        try:
            payload = json.loads(receipt.payload)
            event = PortableReplayEvent(
                sequence=payload["sequence"],
                semantic_id=payload["semantic_id"],
                event_type=payload["event_type"],
                subject_id=payload["subject_id"],
                state_before=payload["state_before"],
                state_after=payload["state_after"],
                action=payload["action"],
                semantic_digest=payload["semantic_digest"],
            )
        except (json.JSONDecodeError, KeyError, TypeError):
            return PortableReplayResult(
                False,
                final_digest,
                checked,
                state,
                tuple(actions),
                ZERO_DIGEST,
                "PORTABLE_EVENT_JSON_INVALID",
            )
        valid, reason = validate_portable_event(event)
        if not valid:
            return PortableReplayResult(
                False, final_digest, checked, state, tuple(actions), ZERO_DIGEST, reason
            )
        event_count += 1
        if event.sequence != event_count:
            return PortableReplayResult(
                False,
                final_digest,
                checked,
                state,
                tuple(actions),
                ZERO_DIGEST,
                "PORTABLE_EVENT_SEQUENCE_MISMATCH",
            )
        if subject and event.subject_id != subject:
            return PortableReplayResult(
                False,
                final_digest,
                checked,
                state,
                tuple(actions),
                ZERO_DIGEST,
                "PORTABLE_SUBJECT_MISMATCH",
            )
        subject = event.subject_id
        expected = {
            (READY, ACTIVATED, contract.HOLD): ACTIVE,
            (ACTIVE, CONTROL_POINT, contract.RELEASE): AT_CONTROL_POINT,
        }.get((state, event.event_type, event.action))
        if expected is None or event.state_before != state or event.state_after != expected:
            return PortableReplayResult(
                False,
                final_digest,
                checked,
                state,
                tuple(actions),
                ZERO_DIGEST,
                "ILLEGAL_PORTABLE_TRANSITION",
            )
        state = expected
        actions.append(event.action)
        semantic_digests.append(event.semantic_digest)

    stream_digest = _digest_json(semantic_digests)
    try:
        summary = json.loads(receipt_tuple[-1].payload)
    except json.JSONDecodeError:
        return PortableReplayResult(
            False,
            final_digest,
            checked,
            state,
            tuple(actions),
            stream_digest,
            "SUMMARY_JSON_INVALID",
        )
    expected_summary = {
        "actions": actions,
        "events": event_count,
        "executed_actions": 0,
        "final_state": state,
        "semantic_stream_digest": stream_digest,
    }
    if summary != expected_summary:
        return PortableReplayResult(
            False,
            final_digest,
            checked,
            state,
            tuple(actions),
            stream_digest,
            "PORTABLE_SUMMARY_MISMATCH",
        )
    return PortableReplayResult(
        True,
        final_digest,
        checked,
        state,
        tuple(actions),
        stream_digest,
        "NONE",
    )


def replay_evidence_receipts(
    receipts: Sequence[ReplayReceipt],
) -> EvidenceReplayResult:
    receipt_tuple = tuple(receipts)
    chain_ok, final_digest, checked, error = _verify_chain(receipt_tuple)
    if not chain_ok:
        return EvidenceReplayResult(False, final_digest, checked, "", 0, error)
    if (
        receipt_tuple[0].kind != "EVIDENCE_SESSION"
        or receipt_tuple[-1].kind != "EVIDENCE_SUMMARY"
    ):
        return EvidenceReplayResult(
            False, final_digest, checked, "", 0, "EVIDENCE_BOUNDARY_INVALID"
        )
    try:
        session = json.loads(receipt_tuple[0].payload)
    except json.JSONDecodeError:
        return EvidenceReplayResult(
            False, final_digest, checked, "", 0, "EVIDENCE_SESSION_JSON_INVALID"
        )
    host_id = session.get("host_id")
    if not isinstance(host_id, str) or not host_id:
        return EvidenceReplayResult(
            False, final_digest, checked, "", 0, "EVIDENCE_HOST_ID_INVALID"
        )
    if session.get("execution_authority") != "NONE":
        return EvidenceReplayResult(
            False, final_digest, checked, host_id, 0, "EVIDENCE_EXECUTION_NONZERO"
        )
    binding_digests: list[str] = []
    portable_digests: list[str] = []
    for receipt in receipt_tuple[1:-1]:
        if receipt.kind != "EVIDENCE_BINDING":
            return EvidenceReplayResult(
                False,
                final_digest,
                checked,
                host_id,
                len(binding_digests),
                "UNEXPECTED_EVIDENCE_RECEIPT_KIND",
            )
        try:
            payload = json.loads(receipt.payload)
            binding = HostEvidenceBinding(
                host_id=payload["host_id"],
                host_family=payload["host_family"],
                host_run_digest=payload["host_run_digest"],
                raw_event_digest=payload["raw_event_digest"],
                portable_semantic_digest=payload["portable_semantic_digest"],
                source_sequence=payload["source_sequence"],
                binding_digest=payload["binding_digest"],
            )
        except (json.JSONDecodeError, KeyError, TypeError):
            return EvidenceReplayResult(
                False,
                final_digest,
                checked,
                host_id,
                len(binding_digests),
                "EVIDENCE_BINDING_JSON_INVALID",
            )
        valid, reason = validate_evidence_binding(binding)
        if not valid:
            return EvidenceReplayResult(
                False, final_digest, checked, host_id, len(binding_digests), reason
            )
        if binding.host_id != host_id:
            return EvidenceReplayResult(
                False,
                final_digest,
                checked,
                host_id,
                len(binding_digests),
                "EVIDENCE_HOST_BINDING_MISMATCH",
            )
        binding_digests.append(binding.binding_digest)
        portable_digests.append(binding.portable_semantic_digest)
    try:
        summary = json.loads(receipt_tuple[-1].payload)
    except json.JSONDecodeError:
        return EvidenceReplayResult(
            False,
            final_digest,
            checked,
            host_id,
            len(binding_digests),
            "EVIDENCE_SUMMARY_JSON_INVALID",
        )
    expected_summary = {
        "bindings": len(binding_digests),
        "executed_actions": 0,
        "host_id": host_id,
        "portable_semantic_digests": portable_digests,
    }
    if summary != expected_summary:
        return EvidenceReplayResult(
            False,
            final_digest,
            checked,
            host_id,
            len(binding_digests),
            "EVIDENCE_SUMMARY_MISMATCH",
        )
    return EvidenceReplayResult(
        True, final_digest, checked, host_id, len(binding_digests), "NONE"
    )


class QueueCrossHostAdapter(CrossHostSemanticAdapter):
    host_id = "QUEUE-HOST-A"
    host_family = "DETERMINISTIC_QUEUE"

    def __init__(self) -> None:
        self._base = contract.QueueFixtureAdapter()

    def project(
        self,
        raw_events: Iterable[object],
        host_run_digest: str,
    ) -> Tuple[Tuple[PortableReplayEvent, ...], Tuple[HostEvidenceBinding, ...]]:
        if not _is_digest(host_run_digest):
            raise ValueError("host_run_digest must be a lowercase SHA-256 digest")
        raw_tuple = tuple(raw_events)
        canonical = tuple(self._base.normalize_event(item) for item in raw_tuple)
        if len(canonical) != 2:
            raise ValueError("queue cross-host projection requires exactly two events")
        expected_types = ("DISPATCH", "CHECKPOINT")
        if tuple(item.event_type for item in canonical) != expected_types:
            raise ValueError("queue event sequence is not equivalent")
        portable = (
            build_portable_event(
                sequence=1,
                semantic_id="PORTABLE:1:ACTIVATED",
                event_type=ACTIVATED,
                subject_id=canonical[0].subject_id,
                state_before=READY,
                state_after=ACTIVE,
                action=contract.HOLD,
            ),
            build_portable_event(
                sequence=2,
                semantic_id="PORTABLE:2:CONTROL_POINT",
                event_type=CONTROL_POINT,
                subject_id=canonical[1].subject_id,
                state_before=ACTIVE,
                state_after=AT_CONTROL_POINT,
                action=contract.RELEASE,
            ),
        )
        bindings = tuple(
            build_evidence_binding(
                host_id=self.host_id,
                host_family=self.host_family,
                host_run_digest=host_run_digest,
                raw_event_digest=source.event_digest,
                portable_event=target,
                source_sequence=source.sequence,
            )
            for source, target in zip(canonical, portable, strict=True)
        )
        return portable, bindings


class WorkflowCrossHostAdapter(CrossHostSemanticAdapter):
    host_id = "WORKFLOW-HOST-B"
    host_family = "VERSIONED_FINITE_STATE_WORKFLOW"

    def __init__(self) -> None:
        self._base = stage2.WorkflowStateAdapter()

    def project(
        self,
        raw_events: Iterable[object],
        host_run_digest: str,
    ) -> Tuple[Tuple[PortableReplayEvent, ...], Tuple[HostEvidenceBinding, ...]]:
        if not _is_digest(host_run_digest):
            raise ValueError("host_run_digest must be a lowercase SHA-256 digest")
        applied = tuple(
            item
            for item in tuple(raw_events)
            if isinstance(item, workflow_host.WorkflowEvent)
            and item.event_type == workflow_host.APPLIED
            and item.operation in (workflow_host.START, workflow_host.CHECKPOINT)
        )
        if tuple(item.operation for item in applied) != (
            workflow_host.START,
            workflow_host.CHECKPOINT,
        ):
            raise ValueError("workflow event sequence is not equivalent")
        canonical = tuple(self._base.normalize_event(item) for item in applied)
        portable = (
            build_portable_event(
                sequence=1,
                semantic_id="PORTABLE:1:ACTIVATED",
                event_type=ACTIVATED,
                subject_id=canonical[0].subject_id,
                state_before=READY,
                state_after=ACTIVE,
                action=contract.HOLD,
            ),
            build_portable_event(
                sequence=2,
                semantic_id="PORTABLE:2:CONTROL_POINT",
                event_type=CONTROL_POINT,
                subject_id=canonical[1].subject_id,
                state_before=ACTIVE,
                state_after=AT_CONTROL_POINT,
                action=contract.RELEASE,
            ),
        )
        bindings = tuple(
            build_evidence_binding(
                host_id=self.host_id,
                host_family=self.host_family,
                host_run_digest=host_run_digest,
                raw_event_digest=source.event_digest,
                portable_event=target,
                source_sequence=raw.sequence,
            )
            for raw, source, target in zip(applied, canonical, portable, strict=True)
        )
        return portable, bindings


def _queue_host_digest(raw_events: Sequence[object]) -> str:
    return _digest_json({"host": QueueCrossHostAdapter.host_id, "events": raw_events})


def project_host(
    adapter: CrossHostSemanticAdapter | None,
    raw_events: Iterable[object],
    host_run_digest: str,
) -> CrossHostProjectionReport:
    raw_tuple = tuple(raw_events)
    first_error = "NONE"
    portable: Tuple[PortableReplayEvent, ...] = ()
    bindings: Tuple[HostEvidenceBinding, ...] = ()
    host_id = "MISSING"
    host_family = "MISSING"
    if adapter is None:
        first_error = "NO_CROSS_HOST_ADAPTER"
    else:
        host_id = _nonempty_text(getattr(adapter, "host_id", ""), "host_id")
        host_family = _nonempty_text(getattr(adapter, "host_family", ""), "host_family")
        try:
            portable, bindings = adapter.project(raw_tuple, host_run_digest)
        except Exception:
            first_error = "CROSS_HOST_PROJECTION_EXCEPTION"

    if first_error == "NONE":
        if len(portable) != len(bindings):
            first_error = "PORTABLE_EVIDENCE_COUNT_MISMATCH"
        elif tuple(item.sequence for item in portable) != tuple(
            range(1, len(portable) + 1)
        ):
            first_error = "PORTABLE_EVENT_SEQUENCE_MISMATCH"
        elif len({item.semantic_id for item in portable}) != len(portable):
            first_error = "DUPLICATE_PORTABLE_SEMANTIC_ID"
        elif any(not validate_portable_event(item)[0] for item in portable):
            first_error = "PORTABLE_EVENT_INVALID"
        elif any(not validate_evidence_binding(item)[0] for item in bindings):
            first_error = "EVIDENCE_BINDING_INVALID"
        elif any(
            binding.portable_semantic_digest != event.semantic_digest
            for binding, event in zip(bindings, portable, strict=True)
        ):
            first_error = "EVIDENCE_SEMANTIC_BINDING_MISMATCH"

    portable_receipts = build_portable_receipts(portable)
    evidence_receipts = build_evidence_receipts(
        host_id, host_family, host_run_digest, bindings
    )
    portable_replay = replay_portable_receipts(portable_receipts)
    evidence_replay = replay_evidence_receipts(evidence_receipts)
    stream_digest = _semantic_stream_digest(portable)
    portable_ledger_digest = portable_receipts[-1].receipt_hash
    evidence_ledger_digest = evidence_receipts[-1].receipt_hash
    report_digest = _digest_json(
        {
            "evidence_ledger_digest": evidence_ledger_digest,
            "host_family": host_family,
            "host_id": host_id,
            "host_run_digest": host_run_digest,
            "portable_ledger_digest": portable_ledger_digest,
            "semantic_stream_digest": stream_digest,
        }
    )
    passed = (
        first_error == "NONE"
        and len(portable) == 2
        and portable_replay.passed
        and evidence_replay.passed
        and portable_replay.final_state == AT_CONTROL_POINT
        and portable_replay.actions == (contract.HOLD, contract.RELEASE)
        and portable_replay.semantic_stream_digest == stream_digest
    )
    return CrossHostProjectionReport(
        host_id=host_id,
        host_family=host_family,
        host_run_digest=host_run_digest,
        portable_events=portable,
        evidence_bindings=bindings,
        portable_receipts=portable_receipts,
        evidence_receipts=evidence_receipts,
        portable_replay=portable_replay,
        evidence_replay=evidence_replay,
        semantic_stream_digest=stream_digest,
        portable_ledger_digest=portable_ledger_digest,
        evidence_ledger_digest=evidence_ledger_digest,
        report_digest=report_digest,
        passed=passed,
        executed_actions=0,
        first_error=first_error,
    )


def _rehash_receipts(receipts: Sequence[ReplayReceipt]) -> Tuple[ReplayReceipt, ...]:
    rebuilt: list[ReplayReceipt] = []
    for receipt in receipts:
        prior_hash = rebuilt[-1].receipt_hash if rebuilt else ZERO_DIGEST
        receipt_hash = _receipt_hash(
            receipt.receipt_id,
            receipt.kind,
            receipt.subject,
            receipt.payload,
            prior_hash,
        )
        rebuilt.append(replace(receipt, prior_hash=prior_hash, receipt_hash=receipt_hash))
    return tuple(rebuilt)


def run_stage3_qualification(
    *,
    frozen_root: Path = FROZEN_V02_ROOT,
    expected_manifest_sha256: str = contract.EXPECTED_V02_RELEASE_MANIFEST_SHA256,
) -> Stage3Qualification:
    frozen_pre = contract.verify_frozen_v02(frozen_root, expected_manifest_sha256)
    source_before = _source_snapshot()
    queue_raw = contract._fixture_inputs()[0]
    commands = workflow_host.baseline_commands()
    input_before = repr((queue_raw, commands))
    workflow_before = workflow_host.run_workflow(commands)

    queue_report = project_host(
        QueueCrossHostAdapter(), queue_raw, _queue_host_digest(queue_raw)
    )
    workflow_report = project_host(
        WorkflowCrossHostAdapter(), workflow_before.events, workflow_before.run_digest
    )

    workflow_after = workflow_host.run_workflow(commands)
    input_after = repr((queue_raw, commands))
    source_after = _source_snapshot()
    frozen_post = contract.verify_frozen_v02(frozen_root, expected_manifest_sha256)

    portable_tampered = list(queue_report.portable_receipts)
    portable_tampered[1] = replace(portable_tampered[1], payload="TAMPERED")
    portable_tamper_detection_pass = not replay_portable_receipts(
        tuple(portable_tampered)
    ).passed

    evidence_tampered = list(queue_report.evidence_receipts)
    evidence_tampered[1] = replace(evidence_tampered[1], payload="TAMPERED")
    evidence_tamper_detection_pass = not replay_evidence_receipts(
        tuple(evidence_tampered)
    ).passed

    reordered = list(queue_report.portable_receipts)
    reordered[1], reordered[2] = reordered[2], reordered[1]
    reorder_detection_pass = not replay_portable_receipts(tuple(reordered)).passed

    source_map = dict(source_before)
    prior_stage_sources_bound = (
        source_map.get(CONTRACT_PATH.relative_to(REPOSITORY_ROOT).as_posix())
        == EXPECTED_STAGE1_SOURCE_SHA256
        and source_map.get(STAGE2_PATH.relative_to(REPOSITORY_ROOT).as_posix())
        == EXPECTED_STAGE2_SOURCE_SHA256
        and source_map.get(WORKFLOW_HOST_PATH.relative_to(REPOSITORY_ROOT).as_posix())
        == EXPECTED_WORKFLOW_HOST_SOURCE_SHA256
    )
    semantic_events_equivalent = queue_report.portable_events == workflow_report.portable_events
    semantic_stream_digest_equivalent = (
        queue_report.semantic_stream_digest == workflow_report.semantic_stream_digest
    )
    portable_ledgers_identical = (
        queue_report.portable_receipts == workflow_report.portable_receipts
        and queue_report.portable_ledger_digest
        == workflow_report.portable_ledger_digest
    )
    portable_replay_equivalent = (
        queue_report.portable_replay == workflow_report.portable_replay
        and replay_portable_receipts(queue_report.portable_receipts)
        == replay_portable_receipts(workflow_report.portable_receipts)
    )
    host_evidence_distinct = (
        queue_report.host_id != workflow_report.host_id
        and queue_report.host_family != workflow_report.host_family
        and queue_report.host_run_digest != workflow_report.host_run_digest
        and queue_report.evidence_bindings != workflow_report.evidence_bindings
        and queue_report.evidence_ledger_digest
        != workflow_report.evidence_ledger_digest
    )
    host_evidence_replay_pass = (
        queue_report.evidence_replay.passed
        and workflow_report.evidence_replay.passed
    )
    no_hidden_execution_authority = (
        EXECUTION_AUTHORITY == "NONE"
        and queue_report.executed_actions == 0
        and workflow_report.executed_actions == 0
        and not any(
            hasattr(CrossHostSemanticAdapter, name)
            for name in ("execute", "apply", "dispatch", "mutate_host")
        )
        and not any(
            hasattr(contract.PortableHostAdapter, name)
            for name in ("execute", "apply", "dispatch", "mutate_host")
        )
    )
    frozen_unchanged = frozen_pre.passed and frozen_post.passed and frozen_pre == frozen_post
    passed = (
        frozen_pre.passed
        and frozen_post.passed
        and frozen_unchanged
        and prior_stage_sources_bound
        and source_before == source_after
        and input_before == input_after
        and workflow_before == workflow_after
        and queue_report.passed
        and workflow_report.passed
        and semantic_events_equivalent
        and semantic_stream_digest_equivalent
        and portable_ledgers_identical
        and portable_replay_equivalent
        and host_evidence_distinct
        and host_evidence_replay_pass
        and portable_tamper_detection_pass
        and evidence_tamper_detection_pass
        and reorder_detection_pass
        and no_hidden_execution_authority
    )
    return Stage3Qualification(
        passed=passed,
        stage_name=STAGE_NAME,
        stage_version=STAGE_VERSION,
        mode=MODE,
        execution_authority=EXECUTION_AUTHORITY,
        frozen_v02_pre_pass=frozen_pre.passed,
        frozen_v02_post_pass=frozen_post.passed,
        frozen_v02_unchanged=frozen_unchanged,
        prior_stage_sources_bound=prior_stage_sources_bound,
        sources_unchanged=source_before == source_after,
        inputs_unchanged=input_before == input_after,
        workflow_host_unchanged=workflow_before == workflow_after,
        queue_projection_pass=queue_report.passed,
        workflow_projection_pass=workflow_report.passed,
        semantic_events_equivalent=semantic_events_equivalent,
        semantic_stream_digest_equivalent=semantic_stream_digest_equivalent,
        portable_ledgers_identical=portable_ledgers_identical,
        portable_replay_equivalent=portable_replay_equivalent,
        host_evidence_distinct=host_evidence_distinct,
        host_evidence_replay_pass=host_evidence_replay_pass,
        portable_tamper_detection_pass=portable_tamper_detection_pass,
        evidence_tamper_detection_pass=evidence_tamper_detection_pass,
        reorder_detection_pass=reorder_detection_pass,
        no_hidden_execution_authority=no_hidden_execution_authority,
        executed_actions=0,
        portable_event_count=len(queue_report.portable_events),
        portable_semantic_stream_digest=queue_report.semantic_stream_digest,
        portable_ledger_digest=queue_report.portable_ledger_digest,
        queue_evidence_ledger_digest=queue_report.evidence_ledger_digest,
        workflow_evidence_ledger_digest=workflow_report.evidence_ledger_digest,
        cross_host_replay_digest=queue_report.portable_replay.final_digest,
        frozen_v02_manifest_sha256=frozen_pre.manifest_sha256,
    )


def main() -> int:
    qualification = run_stage3_qualification()
    print(f"Stage: {qualification.stage_name} {qualification.stage_version}")
    print(f"Mode: {qualification.mode}")
    print(f"Execution authority: {qualification.execution_authority}")
    print(f"Frozen v0.2 manifest: {qualification.frozen_v02_manifest_sha256}")
    print(f"Portable events: {qualification.portable_event_count}")
    print(
        "Portable semantic stream digest: "
        f"{qualification.portable_semantic_stream_digest}"
    )
    print(f"Portable ledger digest: {qualification.portable_ledger_digest}")
    print(f"Queue evidence ledger: {qualification.queue_evidence_ledger_digest}")
    print(f"Workflow evidence ledger: {qualification.workflow_evidence_ledger_digest}")
    print(f"Cross-host replay digest: {qualification.cross_host_replay_digest}")
    print(f"Executed actions: {qualification.executed_actions}")
    if not qualification.passed:
        print("STAGE 3 EQUIVALENT-EVENT CROSS-HOST REPLAY: FAIL")
        return 1
    print("STAGE 3 EQUIVALENT-EVENT CROSS-HOST REPLAY: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
