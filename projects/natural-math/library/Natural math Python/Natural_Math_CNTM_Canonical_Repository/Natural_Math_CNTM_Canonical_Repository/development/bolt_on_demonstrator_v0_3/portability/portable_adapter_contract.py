#!/usr/bin/env python3
"""Portable adapter contract for Bolt-On Demonstrator v0.3, Stage 1.

This stage defines a host-neutral boundary for adapter substitution.  It does
not attach to a second live host and it does not execute host actions.  An
adapter may only:

1. identify itself and its host family;
2. normalize a host-specific event into an immutable canonical event; and
3. project how a bounded HOLD or RELEASE request would map to that host.

The contract has no execute/apply/dispatch callback.  Every projection must
report ``executed=False``.  Missing, malformed, inconsistent, unsupported, or
execution-claiming adapter evidence fails closed and receives deterministic,
hash-chained receipts.

SHA-256 values are deterministic integrity bindings for this demonstrator, not
production identity signatures.
"""

from __future__ import annotations

import hashlib
import json
from abc import ABC, abstractmethod
from dataclasses import dataclass, replace
from pathlib import Path
import sys
from typing import Iterable, Mapping, Sequence, Tuple

sys.dont_write_bytecode = True

CONTRACT_NAME = "PORTABLE HOST ADAPTER CONTRACT"
CONTRACT_VERSION = "0.3.1"
MODE = "PORTABILITY_DRY_RUN"
EXECUTION_AUTHORITY = "NONE"

HOLD = "HOLD"
RELEASE = "RELEASE"
SUPPORTED_ACTIONS = (HOLD, RELEASE)

WOULD_DISPATCH = "WOULD_DISPATCH"
ABSTAIN = "ABSTAIN"
REJECTED = "REJECTED"

ZERO_DIGEST = "0" * 64
EXPECTED_V02_RELEASE_MANIFEST_SHA256 = (
    "e020199f5327866bfcbe34877466ea06558eb6650c578ce841c37b4c9abd159c"
)

THIS_FILE = Path(__file__).resolve()
PROJECT_DIR = THIS_FILE.parents[1]
REPOSITORY_ROOT = THIS_FILE.parents[3]
FROZEN_V02_ROOT = REPOSITORY_ROOT / "frozen" / "bolt_on" / "v0.2"


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _canonical_json(value: object) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def _digest_json(value: object) -> str:
    return _sha256_bytes(_canonical_json(value).encode("ascii"))


def _is_digest(value: object) -> bool:
    if not isinstance(value, str) or len(value) != 64:
        return False
    return all(character in "0123456789abcdef" for character in value)


def _exact_int(value: object, name: str, *, minimum: int | None = None) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise TypeError(f"{name} must be an exact integer")
    if minimum is not None and value < minimum:
        raise ValueError(f"{name} must be >= {minimum}")
    return value


def _nonempty_text(value: object, name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{name} must be a non-empty string")
    return value.strip()


def _normalise_attributes(
    attributes: Mapping[object, object] | Iterable[Tuple[object, object]],
) -> Tuple[Tuple[str, str], ...]:
    source = attributes.items() if isinstance(attributes, Mapping) else tuple(attributes)
    rows: list[Tuple[str, str]] = []
    for key, value in source:
        normalised_key = _nonempty_text(key, "attribute key")
        if not isinstance(value, (str, int)) or isinstance(value, bool):
            raise TypeError("attribute values must be strings or exact integers")
        rows.append((normalised_key, str(value)))
    rows.sort()
    if len({key for key, _ in rows}) != len(rows):
        raise ValueError("attribute keys must be unique")
    return tuple(rows)


@dataclass(frozen=True)
class AdapterIdentity:
    adapter_id: str
    adapter_version: str
    host_family: str
    host_instance: str
    contract_version: str
    capabilities: Tuple[str, ...]
    identity_digest: str

    def unsigned_record(self) -> dict[str, object]:
        return {
            "adapter_id": self.adapter_id,
            "adapter_version": self.adapter_version,
            "capabilities": list(self.capabilities),
            "contract_version": self.contract_version,
            "host_family": self.host_family,
            "host_instance": self.host_instance,
        }

    def canonical_line(self) -> str:
        return _canonical_json({**self.unsigned_record(), "identity_digest": self.identity_digest})


@dataclass(frozen=True)
class CanonicalHostEvent:
    sequence: int
    event_id: str
    event_type: str
    subject_id: str
    state_before_digest: str
    state_after_digest: str
    attributes: Tuple[Tuple[str, str], ...]
    adapter_identity_digest: str
    semantic_digest: str
    event_digest: str

    def semantic_record(self) -> dict[str, object]:
        return {
            "attributes": [list(item) for item in self.attributes],
            "event_id": self.event_id,
            "event_type": self.event_type,
            "sequence": self.sequence,
            "state_after_digest": self.state_after_digest,
            "state_before_digest": self.state_before_digest,
            "subject_id": self.subject_id,
        }

    def canonical_line(self) -> str:
        return _canonical_json(
            {
                **self.semantic_record(),
                "adapter_identity_digest": self.adapter_identity_digest,
                "event_digest": self.event_digest,
                "semantic_digest": self.semantic_digest,
            }
        )


@dataclass(frozen=True)
class PortableActionRequest:
    request_id: int
    action: str
    subject_id: str
    source_event_digest: str
    governance_session_digest: str
    authority_digest: str
    expected_state_digest: str
    current_epoch: int
    request_digest: str

    def unsigned_record(self) -> dict[str, object]:
        return {
            "action": self.action,
            "authority_digest": self.authority_digest,
            "current_epoch": self.current_epoch,
            "expected_state_digest": self.expected_state_digest,
            "governance_session_digest": self.governance_session_digest,
            "request_id": self.request_id,
            "source_event_digest": self.source_event_digest,
            "subject_id": self.subject_id,
        }

    def canonical_line(self) -> str:
        return _canonical_json({**self.unsigned_record(), "request_digest": self.request_digest})


@dataclass(frozen=True)
class AdapterProjection:
    request_id: int
    action: str
    subject_id: str
    host_operation: str
    adapter_identity_digest: str
    source_event_digest: str
    expected_state_digest: str
    would_dispatch: bool
    executed: bool
    reason_code: str
    projection_digest: str

    def unsigned_record(self) -> dict[str, object]:
        return {
            "action": self.action,
            "adapter_identity_digest": self.adapter_identity_digest,
            "executed": self.executed,
            "expected_state_digest": self.expected_state_digest,
            "host_operation": self.host_operation,
            "reason_code": self.reason_code,
            "request_id": self.request_id,
            "source_event_digest": self.source_event_digest,
            "subject_id": self.subject_id,
            "would_dispatch": self.would_dispatch,
        }

    def canonical_line(self) -> str:
        return _canonical_json({**self.unsigned_record(), "projection_digest": self.projection_digest})


@dataclass(frozen=True)
class PortableOutcome:
    request_id: int
    action: str
    subject_id: str
    disposition: str
    would_dispatch: bool
    executed: bool
    host_operation: str
    reason_code: str
    projection_digest: str

    def canonical_line(self) -> str:
        return _canonical_json(
            {
                "action": self.action,
                "disposition": self.disposition,
                "executed": self.executed,
                "host_operation": self.host_operation,
                "projection_digest": self.projection_digest,
                "reason_code": self.reason_code,
                "request_id": self.request_id,
                "subject_id": self.subject_id,
                "would_dispatch": self.would_dispatch,
            }
        )


@dataclass(frozen=True)
class AdapterReceipt:
    receipt_id: int
    kind: str
    subject: str
    payload: str
    prior_hash: str
    receipt_hash: str


@dataclass(frozen=True)
class AdapterReplay:
    passed: bool
    final_digest: str
    checked_receipts: int
    first_error: str


@dataclass(frozen=True)
class FrozenVerification:
    passed: bool
    manifest_sha256: str
    checked_files: int
    tree_digest: str
    first_error: str


@dataclass(frozen=True)
class AdapterContractReport:
    identity: AdapterIdentity | None
    events: Tuple[CanonicalHostEvent, ...]
    requests: Tuple[PortableActionRequest, ...]
    projections: Tuple[AdapterProjection, ...]
    outcomes: Tuple[PortableOutcome, ...]
    receipts: Tuple[AdapterReceipt, ...]
    replay: AdapterReplay
    report_digest: str
    passed: bool
    executed_actions: int
    first_error: str


@dataclass(frozen=True)
class Stage1Qualification:
    passed: bool
    contract_name: str
    contract_version: str
    mode: str
    execution_authority: str
    frozen_v02_pre_pass: bool
    frozen_v02_post_pass: bool
    frozen_v02_unchanged: bool
    adapters_qualified: int
    semantic_equivalence_pass: bool
    adapter_substitution_pass: bool
    receipt_replay_pass: bool
    no_hidden_execution_authority: bool
    deny_by_default_pass: bool
    tamper_detection_pass: bool
    input_unchanged: bool
    executed_actions: int
    queue_report_digest: str
    ledger_report_digest: str
    semantic_event_digest: str
    frozen_v02_manifest_sha256: str


class PortableHostAdapter(ABC):
    """The complete Stage 1 adapter surface.  No execution callback exists."""

    @abstractmethod
    def identity(self) -> AdapterIdentity:
        raise NotImplementedError

    @abstractmethod
    def normalize_event(self, raw_event: object) -> CanonicalHostEvent:
        raise NotImplementedError

    @abstractmethod
    def project_action(
        self, request: PortableActionRequest, event: CanonicalHostEvent
    ) -> AdapterProjection:
        raise NotImplementedError


def build_adapter_identity(
    *,
    adapter_id: str,
    adapter_version: str,
    host_family: str,
    host_instance: str,
    capabilities: Sequence[str] = SUPPORTED_ACTIONS,
) -> AdapterIdentity:
    normalised = tuple(_nonempty_text(item, "capability").upper() for item in capabilities)
    if len(set(normalised)) != len(normalised):
        raise ValueError("capabilities cannot contain duplicates")
    if any(item not in SUPPORTED_ACTIONS for item in normalised):
        raise ValueError("unsupported capability")
    normalised = tuple(item for item in SUPPORTED_ACTIONS if item in normalised)
    unsigned = {
        "adapter_id": _nonempty_text(adapter_id, "adapter_id"),
        "adapter_version": _nonempty_text(adapter_version, "adapter_version"),
        "capabilities": list(normalised),
        "contract_version": CONTRACT_VERSION,
        "host_family": _nonempty_text(host_family, "host_family"),
        "host_instance": _nonempty_text(host_instance, "host_instance"),
    }
    return AdapterIdentity(
        adapter_id=unsigned["adapter_id"],
        adapter_version=unsigned["adapter_version"],
        host_family=unsigned["host_family"],
        host_instance=unsigned["host_instance"],
        contract_version=CONTRACT_VERSION,
        capabilities=normalised,
        identity_digest=_digest_json(unsigned),
    )


def validate_adapter_identity(identity: AdapterIdentity) -> Tuple[bool, str]:
    if not isinstance(identity, AdapterIdentity):
        return False, "IDENTITY_TYPE_INVALID"
    try:
        expected = build_adapter_identity(
            adapter_id=identity.adapter_id,
            adapter_version=identity.adapter_version,
            host_family=identity.host_family,
            host_instance=identity.host_instance,
            capabilities=identity.capabilities,
        )
    except (TypeError, ValueError):
        return False, "IDENTITY_FIELDS_INVALID"
    if identity.contract_version != CONTRACT_VERSION:
        return False, "CONTRACT_VERSION_MISMATCH"
    if identity.identity_digest != expected.identity_digest:
        return False, "IDENTITY_DIGEST_MISMATCH"
    return True, "VALID"


def state_digest(value: object) -> str:
    if isinstance(value, bool) or not isinstance(value, (str, int)):
        raise TypeError("state value must be a string or exact integer")
    return _digest_json({"type": type(value).__name__, "value": value})


def build_canonical_event(
    identity: AdapterIdentity,
    *,
    sequence: int,
    event_id: str,
    event_type: str,
    subject_id: str,
    state_before: object,
    state_after: object,
    attributes: Mapping[object, object] | Iterable[Tuple[object, object]] = (),
) -> CanonicalHostEvent:
    valid, reason = validate_adapter_identity(identity)
    if not valid:
        raise ValueError(f"invalid adapter identity: {reason}")
    sequence = _exact_int(sequence, "sequence", minimum=1)
    semantic = {
        "attributes": [list(item) for item in _normalise_attributes(attributes)],
        "event_id": _nonempty_text(event_id, "event_id"),
        "event_type": _nonempty_text(event_type, "event_type").upper(),
        "sequence": sequence,
        "state_after_digest": state_digest(state_after),
        "state_before_digest": state_digest(state_before),
        "subject_id": _nonempty_text(subject_id, "subject_id"),
    }
    semantic_digest = _digest_json(semantic)
    event_digest = _digest_json(
        {"adapter_identity_digest": identity.identity_digest, "semantic_digest": semantic_digest}
    )
    return CanonicalHostEvent(
        sequence=sequence,
        event_id=semantic["event_id"],
        event_type=semantic["event_type"],
        subject_id=semantic["subject_id"],
        state_before_digest=semantic["state_before_digest"],
        state_after_digest=semantic["state_after_digest"],
        attributes=tuple(tuple(item) for item in semantic["attributes"]),
        adapter_identity_digest=identity.identity_digest,
        semantic_digest=semantic_digest,
        event_digest=event_digest,
    )


def validate_canonical_event(
    event: CanonicalHostEvent, identity: AdapterIdentity
) -> Tuple[bool, str]:
    if not isinstance(event, CanonicalHostEvent):
        return False, "EVENT_TYPE_INVALID"
    if event.adapter_identity_digest != identity.identity_digest:
        return False, "EVENT_ADAPTER_BINDING_MISMATCH"
    try:
        semantic = event.semantic_record()
        if event.sequence < 1 or isinstance(event.sequence, bool):
            return False, "EVENT_SEQUENCE_INVALID"
        _normalise_attributes(event.attributes)
        for name in ("event_id", "event_type", "subject_id"):
            _nonempty_text(getattr(event, name), name)
    except (TypeError, ValueError):
        return False, "EVENT_FIELDS_INVALID"
    if not _is_digest(event.state_before_digest) or not _is_digest(event.state_after_digest):
        return False, "EVENT_STATE_DIGEST_INVALID"
    expected_semantic = _digest_json(semantic)
    if event.semantic_digest != expected_semantic:
        return False, "SEMANTIC_DIGEST_MISMATCH"
    expected_event = _digest_json(
        {"adapter_identity_digest": identity.identity_digest, "semantic_digest": expected_semantic}
    )
    if event.event_digest != expected_event:
        return False, "EVENT_DIGEST_MISMATCH"
    return True, "VALID"


def build_action_request(
    *,
    request_id: int,
    action: str,
    subject_id: str,
    source_event_digest: str,
    governance_session_digest: str,
    authority_digest: str,
    expected_state_digest: str,
    current_epoch: int,
) -> PortableActionRequest:
    request_id = _exact_int(request_id, "request_id", minimum=1)
    current_epoch = _exact_int(current_epoch, "current_epoch", minimum=0)
    action = _nonempty_text(action, "action").upper()
    if action not in SUPPORTED_ACTIONS:
        raise ValueError("unsupported action")
    for name, value in (
        ("source_event_digest", source_event_digest),
        ("governance_session_digest", governance_session_digest),
        ("authority_digest", authority_digest),
        ("expected_state_digest", expected_state_digest),
    ):
        if not _is_digest(value):
            raise ValueError(f"{name} must be a lowercase SHA-256 digest")
    unsigned = {
        "action": action,
        "authority_digest": authority_digest,
        "current_epoch": current_epoch,
        "expected_state_digest": expected_state_digest,
        "governance_session_digest": governance_session_digest,
        "request_id": request_id,
        "source_event_digest": source_event_digest,
        "subject_id": _nonempty_text(subject_id, "subject_id"),
    }
    return PortableActionRequest(
        request_id=request_id,
        action=action,
        subject_id=unsigned["subject_id"],
        source_event_digest=source_event_digest,
        governance_session_digest=governance_session_digest,
        authority_digest=authority_digest,
        expected_state_digest=expected_state_digest,
        current_epoch=current_epoch,
        request_digest=_digest_json(unsigned),
    )


def validate_action_request(request: PortableActionRequest) -> Tuple[bool, str]:
    if not isinstance(request, PortableActionRequest):
        return False, "REQUEST_TYPE_INVALID"
    try:
        expected = build_action_request(
            request_id=request.request_id,
            action=request.action,
            subject_id=request.subject_id,
            source_event_digest=request.source_event_digest,
            governance_session_digest=request.governance_session_digest,
            authority_digest=request.authority_digest,
            expected_state_digest=request.expected_state_digest,
            current_epoch=request.current_epoch,
        )
    except (TypeError, ValueError):
        return False, "REQUEST_FIELDS_INVALID"
    if request.request_digest != expected.request_digest:
        return False, "REQUEST_DIGEST_MISMATCH"
    return True, "VALID"


def build_projection(
    identity: AdapterIdentity,
    request: PortableActionRequest,
    event: CanonicalHostEvent,
    *,
    host_operation: str,
    would_dispatch: bool,
    executed: bool = False,
    reason_code: str = "ADAPTER_PROJECTION_READY",
) -> AdapterProjection:
    if not isinstance(would_dispatch, bool) or not isinstance(executed, bool):
        raise TypeError("would_dispatch and executed must be booleans")
    unsigned = {
        "action": request.action,
        "adapter_identity_digest": identity.identity_digest,
        "executed": executed,
        "expected_state_digest": request.expected_state_digest,
        "host_operation": _nonempty_text(host_operation, "host_operation") if would_dispatch else "",
        "reason_code": _nonempty_text(reason_code, "reason_code").upper(),
        "request_id": request.request_id,
        "source_event_digest": event.event_digest,
        "subject_id": request.subject_id,
        "would_dispatch": would_dispatch,
    }
    return AdapterProjection(
        request_id=request.request_id,
        action=request.action,
        subject_id=request.subject_id,
        host_operation=unsigned["host_operation"],
        adapter_identity_digest=identity.identity_digest,
        source_event_digest=event.event_digest,
        expected_state_digest=request.expected_state_digest,
        would_dispatch=would_dispatch,
        executed=executed,
        reason_code=unsigned["reason_code"],
        projection_digest=_digest_json(unsigned),
    )


def validate_projection(
    projection: AdapterProjection,
    identity: AdapterIdentity,
    request: PortableActionRequest,
    event: CanonicalHostEvent,
) -> Tuple[bool, str]:
    if not isinstance(projection, AdapterProjection):
        return False, "PROJECTION_TYPE_INVALID"
    if projection.executed:
        return False, "HIDDEN_EXECUTION_AUTHORITY"
    expected_pairs = (
        (projection.request_id, request.request_id, "PROJECTION_REQUEST_MISMATCH"),
        (projection.action, request.action, "PROJECTION_ACTION_MISMATCH"),
        (projection.subject_id, request.subject_id, "PROJECTION_SUBJECT_MISMATCH"),
        (
            projection.adapter_identity_digest,
            identity.identity_digest,
            "PROJECTION_ADAPTER_MISMATCH",
        ),
        (
            projection.source_event_digest,
            event.event_digest,
            "PROJECTION_EVENT_MISMATCH",
        ),
        (
            projection.expected_state_digest,
            request.expected_state_digest,
            "PROJECTION_STATE_MISMATCH",
        ),
    )
    for actual, expected, reason in expected_pairs:
        if actual != expected:
            return False, reason
    if not isinstance(projection.would_dispatch, bool):
        return False, "PROJECTION_DISPATCH_FLAG_INVALID"
    if projection.would_dispatch and not projection.host_operation:
        return False, "PROJECTION_OPERATION_MISSING"
    if not projection.would_dispatch and projection.host_operation:
        return False, "ABSTAIN_OPERATION_PRESENT"
    expected_digest = _digest_json(projection.unsigned_record())
    if projection.projection_digest != expected_digest:
        return False, "PROJECTION_DIGEST_MISMATCH"
    return True, "VALID"


def _rejected_outcome(request: PortableActionRequest, reason: str) -> PortableOutcome:
    return PortableOutcome(
        request_id=request.request_id,
        action=request.action,
        subject_id=request.subject_id,
        disposition=REJECTED,
        would_dispatch=False,
        executed=False,
        host_operation="",
        reason_code=reason,
        projection_digest=ZERO_DIGEST,
    )


def _receipt_hash(
    receipt_id: int, kind: str, subject: str, payload: str, prior_hash: str
) -> str:
    unsigned = "|".join((str(receipt_id), kind, subject, payload, prior_hash))
    return _sha256_bytes(unsigned.encode("utf-8"))


def build_receipts(
    identity: AdapterIdentity | None,
    events: Sequence[CanonicalHostEvent],
    requests: Sequence[PortableActionRequest],
    projections: Sequence[AdapterProjection],
    outcomes: Sequence[PortableOutcome],
    first_error: str,
) -> Tuple[AdapterReceipt, ...]:
    receipts: list[AdapterReceipt] = []
    prior_hash = ZERO_DIGEST

    def append(kind: str, subject: str, payload: str) -> None:
        nonlocal prior_hash
        receipt_id = len(receipts) + 1
        receipt_hash = _receipt_hash(receipt_id, kind, subject, payload, prior_hash)
        receipts.append(
            AdapterReceipt(receipt_id, kind, subject, payload, prior_hash, receipt_hash)
        )
        prior_hash = receipt_hash

    append(
        "SESSION",
        "OPEN",
        _canonical_json(
            {
                "contract": CONTRACT_NAME,
                "execution_authority": EXECUTION_AUTHORITY,
                "mode": MODE,
                "version": CONTRACT_VERSION,
            }
        ),
    )
    if identity is not None:
        append("ADAPTER", identity.adapter_id, identity.canonical_line())
    for event in events:
        append("EVENT", event.event_id, event.canonical_line())
    for request in requests:
        append("REQUEST", f"REQUEST:{request.request_id}", request.canonical_line())
    for projection in projections:
        append(
            "PROJECTION",
            f"REQUEST:{projection.request_id}",
            projection.canonical_line(),
        )
    for outcome in outcomes:
        append("OUTCOME", f"REQUEST:{outcome.request_id}", outcome.canonical_line())
    append(
        "SUMMARY",
        "PORTABILITY_DRY_RUN",
        _canonical_json(
            {
                "events": len(events),
                "executed_actions": sum(1 for item in outcomes if item.executed),
                "first_error": first_error,
                "outcomes": len(outcomes),
                "projections": len(projections),
                "requests": len(requests),
                "would_dispatch": sum(1 for item in outcomes if item.would_dispatch),
            }
        ),
    )
    return tuple(receipts)


def replay_receipts(receipts: Sequence[AdapterReceipt]) -> AdapterReplay:
    prior_hash = ZERO_DIGEST
    for expected_id, receipt in enumerate(tuple(receipts), start=1):
        if receipt.receipt_id != expected_id:
            return AdapterReplay(
                False,
                prior_hash,
                expected_id - 1,
                f"RECEIPT_ID_MISMATCH:{expected_id}:{receipt.receipt_id}",
            )
        if receipt.prior_hash != prior_hash:
            return AdapterReplay(
                False,
                prior_hash,
                expected_id - 1,
                f"PRIOR_HASH_MISMATCH:{expected_id}",
            )
        expected_hash = _receipt_hash(
            receipt.receipt_id,
            receipt.kind,
            receipt.subject,
            receipt.payload,
            receipt.prior_hash,
        )
        if receipt.receipt_hash != expected_hash:
            return AdapterReplay(
                False,
                prior_hash,
                expected_id - 1,
                f"RECEIPT_HASH_MISMATCH:{expected_id}",
            )
        prior_hash = expected_hash
    if not receipts:
        return AdapterReplay(False, prior_hash, 0, "EMPTY_RECEIPT_STREAM")
    if receipts[0].kind != "SESSION" or receipts[-1].kind != "SUMMARY":
        return AdapterReplay(False, prior_hash, len(receipts), "RECEIPT_BOUNDARY_INVALID")
    try:
        summary = json.loads(receipts[-1].payload)
    except json.JSONDecodeError:
        return AdapterReplay(False, prior_hash, len(receipts), "SUMMARY_JSON_INVALID")
    if summary.get("executed_actions") != 0:
        return AdapterReplay(False, prior_hash, len(receipts), "SUMMARY_EXECUTION_NONZERO")
    return AdapterReplay(True, prior_hash, len(receipts), "NONE")


def evaluate_adapter(
    adapter: PortableHostAdapter | None,
    raw_events: Iterable[object],
    requests: Sequence[PortableActionRequest],
) -> AdapterContractReport:
    raw_tuple = tuple(raw_events)
    request_tuple = tuple(requests)
    identity: AdapterIdentity | None = None
    events: list[CanonicalHostEvent] = []
    projections: list[AdapterProjection] = []
    outcomes: list[PortableOutcome] = []
    first_error = "NONE"

    if adapter is None:
        first_error = "NO_ADAPTER"
        outcomes.extend(_rejected_outcome(request, first_error) for request in request_tuple)
    else:
        try:
            identity = adapter.identity()
        except Exception:
            first_error = "ADAPTER_IDENTITY_EXCEPTION"
        if first_error == "NONE":
            valid_identity, reason = validate_adapter_identity(identity)
            if not valid_identity:
                first_error = reason
        if first_error == "NONE":
            for expected_sequence, raw_event in enumerate(raw_tuple, start=1):
                try:
                    event = adapter.normalize_event(raw_event)
                except Exception:
                    first_error = "EVENT_NORMALIZATION_EXCEPTION"
                    break
                valid_event, reason = validate_canonical_event(event, identity)
                if not valid_event:
                    first_error = reason
                    break
                if event.sequence != expected_sequence:
                    first_error = "EVENT_SEQUENCE_MISMATCH"
                    break
                if any(item.event_id == event.event_id for item in events):
                    first_error = "DUPLICATE_EVENT_ID"
                    break
                events.append(event)
        event_by_digest = {item.event_digest: item for item in events}
        seen_request_ids: set[int] = set()
        if first_error != "NONE":
            outcomes.extend(_rejected_outcome(request, first_error) for request in request_tuple)
        else:
            for expected_request_id, request in enumerate(request_tuple, start=1):
                valid_request, reason = validate_action_request(request)
                if not valid_request:
                    outcomes.append(_rejected_outcome(request, reason))
                    if first_error == "NONE":
                        first_error = reason
                    continue
                if request.request_id != expected_request_id:
                    outcomes.append(_rejected_outcome(request, "REQUEST_SEQUENCE_MISMATCH"))
                    if first_error == "NONE":
                        first_error = "REQUEST_SEQUENCE_MISMATCH"
                    continue
                if request.request_id in seen_request_ids:
                    outcomes.append(_rejected_outcome(request, "DUPLICATE_REQUEST_ID"))
                    if first_error == "NONE":
                        first_error = "DUPLICATE_REQUEST_ID"
                    continue
                seen_request_ids.add(request.request_id)
                if request.action not in identity.capabilities:
                    outcomes.append(_rejected_outcome(request, "ACTION_OUT_OF_SCOPE"))
                    if first_error == "NONE":
                        first_error = "ACTION_OUT_OF_SCOPE"
                    continue
                event = event_by_digest.get(request.source_event_digest)
                if event is None:
                    outcomes.append(_rejected_outcome(request, "SOURCE_EVENT_NOT_FOUND"))
                    if first_error == "NONE":
                        first_error = "SOURCE_EVENT_NOT_FOUND"
                    continue
                if request.subject_id != event.subject_id:
                    outcomes.append(_rejected_outcome(request, "REQUEST_SUBJECT_MISMATCH"))
                    if first_error == "NONE":
                        first_error = "REQUEST_SUBJECT_MISMATCH"
                    continue
                expected_state = (
                    event.state_after_digest if request.action == HOLD else event.state_before_digest
                )
                if request.expected_state_digest != expected_state:
                    outcomes.append(_rejected_outcome(request, "EXPECTED_STATE_MISMATCH"))
                    if first_error == "NONE":
                        first_error = "EXPECTED_STATE_MISMATCH"
                    continue
                try:
                    projection = adapter.project_action(request, event)
                except Exception:
                    outcomes.append(_rejected_outcome(request, "PROJECTION_EXCEPTION"))
                    if first_error == "NONE":
                        first_error = "PROJECTION_EXCEPTION"
                    continue
                projections.append(projection)
                valid_projection, reason = validate_projection(
                    projection, identity, request, event
                )
                if not valid_projection:
                    outcomes.append(_rejected_outcome(request, reason))
                    if first_error == "NONE":
                        first_error = reason
                    continue
                if projection.would_dispatch:
                    outcomes.append(
                        PortableOutcome(
                            request_id=request.request_id,
                            action=request.action,
                            subject_id=request.subject_id,
                            disposition=WOULD_DISPATCH,
                            would_dispatch=True,
                            executed=False,
                            host_operation=projection.host_operation,
                            reason_code=projection.reason_code,
                            projection_digest=projection.projection_digest,
                        )
                    )
                else:
                    outcomes.append(
                        PortableOutcome(
                            request_id=request.request_id,
                            action=request.action,
                            subject_id=request.subject_id,
                            disposition=ABSTAIN,
                            would_dispatch=False,
                            executed=False,
                            host_operation="",
                            reason_code=projection.reason_code,
                            projection_digest=projection.projection_digest,
                        )
                    )
            try:
                identity_after = adapter.identity()
            except Exception:
                identity_after = None
            if identity_after != identity and first_error == "NONE":
                first_error = "ADAPTER_IDENTITY_CHANGED"

    receipts = build_receipts(
        identity,
        events,
        request_tuple,
        projections,
        outcomes,
        first_error,
    )
    replay = replay_receipts(receipts)
    report_digest = receipts[-1].receipt_hash if receipts else ZERO_DIGEST
    executed_actions = sum(1 for item in outcomes if item.executed)
    passed = (
        first_error == "NONE"
        and len(events) == len(raw_tuple)
        and len(outcomes) == len(request_tuple)
        and all(item.disposition == WOULD_DISPATCH for item in outcomes)
        and executed_actions == 0
        and replay.passed
        and replay.final_digest == report_digest
    )
    return AdapterContractReport(
        identity=identity,
        events=tuple(events),
        requests=request_tuple,
        projections=tuple(projections),
        outcomes=tuple(outcomes),
        receipts=receipts,
        replay=replay,
        report_digest=report_digest,
        passed=passed,
        executed_actions=executed_actions,
        first_error=first_error,
    )


def verify_frozen_v02(
    root: Path = FROZEN_V02_ROOT,
    expected_manifest_sha256: str = EXPECTED_V02_RELEASE_MANIFEST_SHA256,
) -> FrozenVerification:
    manifest = root / "RELEASE_MANIFEST_SHA256.txt"
    if not root.is_dir() or not manifest.is_file():
        return FrozenVerification(False, "MISSING", 0, ZERO_DIGEST, "MISSING_RELEASE")
    manifest_bytes = manifest.read_bytes()
    manifest_sha = _sha256_bytes(manifest_bytes)
    if manifest_sha != expected_manifest_sha256:
        return FrozenVerification(
            False, manifest_sha, 0, ZERO_DIGEST, "MANIFEST_SHA256_MISMATCH"
        )
    expected: dict[str, str] = {}
    rows: list[str] = []
    for line_number, line in enumerate(
        manifest_bytes.decode("utf-8").splitlines(), start=1
    ):
        if not line.strip():
            continue
        parts = line.split("  ", 1)
        if len(parts) != 2 or not _is_digest(parts[0]) or parts[1] in expected:
            return FrozenVerification(
                False,
                manifest_sha,
                len(expected),
                ZERO_DIGEST,
                f"INVALID_MANIFEST_LINE:{line_number}",
            )
        expected[parts[1]] = parts[0]
        rows.append(line)
    actual = {
        path.relative_to(root).as_posix()
        for path in root.rglob("*")
        if path.is_file()
        and path != manifest
        and "__pycache__" not in path.parts
        and path.suffix != ".pyc"
    }
    missing = sorted(set(expected) - actual)
    extra = sorted(actual - set(expected))
    if missing:
        return FrozenVerification(
            False, manifest_sha, 0, ZERO_DIGEST, f"MISSING_FILE:{missing[0]}"
        )
    if extra:
        return FrozenVerification(
            False, manifest_sha, 0, ZERO_DIGEST, f"EXTRA_FILE:{extra[0]}"
        )
    for relative in sorted(expected):
        actual_sha = _sha256_bytes((root / relative).read_bytes())
        if actual_sha != expected[relative]:
            return FrozenVerification(
                False,
                manifest_sha,
                0,
                ZERO_DIGEST,
                f"FILE_HASH_MISMATCH:{relative}",
            )
    tree_digest = _sha256_bytes(("\n".join(rows) + "\n").encode("utf-8"))
    return FrozenVerification(True, manifest_sha, len(expected), tree_digest, "NONE")


class QueueFixtureAdapter(PortableHostAdapter):
    def __init__(self) -> None:
        self._identity = build_adapter_identity(
            adapter_id="QUEUE-FIXTURE-ADAPTER",
            adapter_version="0.3.1",
            host_family="DETERMINISTIC_QUEUE",
            host_instance="QUEUE-A",
        )

    def identity(self) -> AdapterIdentity:
        return self._identity

    def normalize_event(self, raw_event: object) -> CanonicalHostEvent:
        if not isinstance(raw_event, Mapping):
            raise TypeError("queue fixture event must be a mapping")
        return build_canonical_event(
            self._identity,
            sequence=raw_event["sequence"],
            event_id=raw_event["event_id"],
            event_type=raw_event["event_type"],
            subject_id=raw_event["subject_id"],
            state_before=raw_event["state_before"],
            state_after=raw_event["state_after"],
            attributes={"priority": raw_event["priority"]},
        )

    def project_action(
        self, request: PortableActionRequest, event: CanonicalHostEvent
    ) -> AdapterProjection:
        operation = {HOLD: "QUEUE_PAUSE", RELEASE: "QUEUE_RESUME"}[request.action]
        return build_projection(
            self._identity,
            request,
            event,
            host_operation=operation,
            would_dispatch=True,
        )


class LedgerFixtureAdapter(PortableHostAdapter):
    def __init__(self) -> None:
        self._identity = build_adapter_identity(
            adapter_id="LEDGER-FIXTURE-ADAPTER",
            adapter_version="0.3.1",
            host_family="APPEND_ONLY_LEDGER",
            host_instance="LEDGER-B",
        )

    def identity(self) -> AdapterIdentity:
        return self._identity

    def normalize_event(self, raw_event: object) -> CanonicalHostEvent:
        if not isinstance(raw_event, tuple) or len(raw_event) != 7:
            raise TypeError("ledger fixture event must be a seven-field tuple")
        sequence, event_id, event_type, subject_id, before, after, priority = raw_event
        return build_canonical_event(
            self._identity,
            sequence=sequence,
            event_id=event_id,
            event_type=event_type,
            subject_id=subject_id,
            state_before=before,
            state_after=after,
            attributes=(("priority", priority),),
        )

    def project_action(
        self, request: PortableActionRequest, event: CanonicalHostEvent
    ) -> AdapterProjection:
        operation = {HOLD: "LEDGER_LOCK", RELEASE: "LEDGER_UNLOCK"}[request.action]
        return build_projection(
            self._identity,
            request,
            event,
            host_operation=operation,
            would_dispatch=True,
        )


def _fixture_inputs():
    queue_events = (
        {
            "sequence": 1,
            "event_id": "E-001",
            "event_type": "DISPATCH",
            "subject_id": "TASK-7",
            "state_before": "READY",
            "state_after": "RUNNING",
            "priority": 2,
        },
        {
            "sequence": 2,
            "event_id": "E-002",
            "event_type": "CHECKPOINT",
            "subject_id": "TASK-7",
            "state_before": "RUNNING",
            "state_after": "HELD",
            "priority": 2,
        },
    )
    ledger_events = (
        (1, "E-001", "DISPATCH", "TASK-7", "READY", "RUNNING", 2),
        (2, "E-002", "CHECKPOINT", "TASK-7", "RUNNING", "HELD", 2),
    )
    return queue_events, ledger_events


def _requests_for(events: Sequence[CanonicalHostEvent]) -> Tuple[PortableActionRequest, ...]:
    session_digest = _digest_json({"session": "V03-STAGE-1"})
    authority_digest = _digest_json({"authority": "FROZEN-V02-SEMANTICS"})
    return (
        build_action_request(
            request_id=1,
            action=HOLD,
            subject_id=events[0].subject_id,
            source_event_digest=events[0].event_digest,
            governance_session_digest=session_digest,
            authority_digest=authority_digest,
            expected_state_digest=events[0].state_after_digest,
            current_epoch=300,
        ),
        build_action_request(
            request_id=2,
            action=RELEASE,
            subject_id=events[1].subject_id,
            source_event_digest=events[1].event_digest,
            governance_session_digest=session_digest,
            authority_digest=authority_digest,
            expected_state_digest=events[1].state_before_digest,
            current_epoch=301,
        ),
    )


def run_stage1_qualification(
    *, frozen_root: Path = FROZEN_V02_ROOT,
    expected_manifest_sha256: str = EXPECTED_V02_RELEASE_MANIFEST_SHA256,
) -> Stage1Qualification:
    frozen_pre = verify_frozen_v02(frozen_root, expected_manifest_sha256)
    queue_adapter = QueueFixtureAdapter()
    ledger_adapter = LedgerFixtureAdapter()
    queue_raw, ledger_raw = _fixture_inputs()
    input_before = repr((queue_raw, ledger_raw))

    queue_events = tuple(queue_adapter.normalize_event(item) for item in queue_raw)
    ledger_events = tuple(ledger_adapter.normalize_event(item) for item in ledger_raw)
    queue_report = evaluate_adapter(queue_adapter, queue_raw, _requests_for(queue_events))
    ledger_report = evaluate_adapter(ledger_adapter, ledger_raw, _requests_for(ledger_events))

    no_adapter_report = evaluate_adapter(None, (), _requests_for(queue_events))
    tampered_receipts = list(queue_report.receipts)
    tampered_receipts[2] = replace(tampered_receipts[2], payload="TAMPERED")
    tamper_detection_pass = not replay_receipts(tuple(tampered_receipts)).passed

    frozen_post = verify_frozen_v02(frozen_root, expected_manifest_sha256)
    input_after = repr((queue_raw, ledger_raw))

    semantic_equivalence_pass = (
        tuple(item.semantic_digest for item in queue_report.events)
        == tuple(item.semantic_digest for item in ledger_report.events)
        and tuple(item.event_digest for item in queue_report.events)
        != tuple(item.event_digest for item in ledger_report.events)
    )
    adapter_substitution_pass = (
        tuple(item.action for item in queue_report.outcomes)
        == tuple(item.action for item in ledger_report.outcomes)
        and tuple(item.disposition for item in queue_report.outcomes)
        == tuple(item.disposition for item in ledger_report.outcomes)
        and tuple(item.host_operation for item in queue_report.outcomes)
        != tuple(item.host_operation for item in ledger_report.outcomes)
    )
    no_hidden_execution_authority = (
        not any(item.executed for item in queue_report.outcomes)
        and not any(item.executed for item in ledger_report.outcomes)
        and not any(
            hasattr(PortableHostAdapter, name)
            for name in ("execute", "apply", "dispatch", "mutate_host")
        )
    )
    receipt_replay_pass = queue_report.replay.passed and ledger_report.replay.passed
    deny_by_default_pass = (
        not no_adapter_report.passed
        and no_adapter_report.first_error == "NO_ADAPTER"
        and all(item.disposition == REJECTED for item in no_adapter_report.outcomes)
    )
    frozen_unchanged = (
        frozen_pre.passed
        and frozen_post.passed
        and frozen_pre == frozen_post
    )
    executed_actions = queue_report.executed_actions + ledger_report.executed_actions
    passed = (
        frozen_pre.passed
        and frozen_post.passed
        and frozen_unchanged
        and queue_report.passed
        and ledger_report.passed
        and semantic_equivalence_pass
        and adapter_substitution_pass
        and receipt_replay_pass
        and no_hidden_execution_authority
        and deny_by_default_pass
        and tamper_detection_pass
        and input_before == input_after
        and executed_actions == 0
    )
    return Stage1Qualification(
        passed=passed,
        contract_name=CONTRACT_NAME,
        contract_version=CONTRACT_VERSION,
        mode=MODE,
        execution_authority=EXECUTION_AUTHORITY,
        frozen_v02_pre_pass=frozen_pre.passed,
        frozen_v02_post_pass=frozen_post.passed,
        frozen_v02_unchanged=frozen_unchanged,
        adapters_qualified=sum((queue_report.passed, ledger_report.passed)),
        semantic_equivalence_pass=semantic_equivalence_pass,
        adapter_substitution_pass=adapter_substitution_pass,
        receipt_replay_pass=receipt_replay_pass,
        no_hidden_execution_authority=no_hidden_execution_authority,
        deny_by_default_pass=deny_by_default_pass,
        tamper_detection_pass=tamper_detection_pass,
        input_unchanged=input_before == input_after,
        executed_actions=executed_actions,
        queue_report_digest=queue_report.report_digest,
        ledger_report_digest=ledger_report.report_digest,
        semantic_event_digest=queue_report.events[0].semantic_digest,
        frozen_v02_manifest_sha256=frozen_pre.manifest_sha256,
    )


def main() -> int:
    qualification = run_stage1_qualification()
    print(f"Contract: {qualification.contract_name} {qualification.contract_version}")
    print(f"Mode: {qualification.mode}")
    print(f"Execution authority: {qualification.execution_authority}")
    print(f"Frozen v0.2 manifest: {qualification.frozen_v02_manifest_sha256}")
    print(f"Adapters qualified: {qualification.adapters_qualified}")
    print(f"Semantic event digest: {qualification.semantic_event_digest}")
    print(f"Queue report digest: {qualification.queue_report_digest}")
    print(f"Ledger report digest: {qualification.ledger_report_digest}")
    print(f"Executed actions: {qualification.executed_actions}")
    if not qualification.passed:
        print("STAGE 1 PORTABLE ADAPTER CONTRACT QUALIFICATION: FAIL")
        return 1
    print("STAGE 1 PORTABLE ADAPTER CONTRACT QUALIFICATION: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
