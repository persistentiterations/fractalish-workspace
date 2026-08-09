#!/usr/bin/env python3
"""Read-only external observation adapter for the ordinary job service.

The adapter consumes plain mapping records exported by a host.  It has no host
import, no command transport, no authority token, no mutation method, and no
execution surface.  It validates the native snapshot and append-only receipt
chain, then emits a deterministic observation batch with its own hash chain.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Iterable, Mapping, Sequence, Tuple

ADAPTER_ID = "ORDINARY-JOB-READ-ONLY-OBSERVER"
ADAPTER_VERSION = "1.0"
MODE = "READ_ONLY_EXTERNAL_OBSERVATION"
EXECUTION_AUTHORITY = "NONE"
COMMAND_SURFACE: Tuple[str, ...] = ()
ZERO_DIGEST = "0" * 64

EXPECTED_HOST_FAMILY = "ORDINARY VERSIONED JOB SERVICE"
EXPECTED_HOST_VERSION = "1.0"
EXPECTED_INTEGRATION_API = "JOB-SERVICE-READ-COMMAND-1"

REGISTER_JOB = "REGISTER_JOB"
START_JOB = "START_JOB"
CHECKPOINT_JOB = "CHECKPOINT_JOB"
PAUSE_JOB = "PAUSE_JOB"
RESUME_JOB = "RESUME_JOB"
COMPLETE_JOB = "COMPLETE_JOB"
CANCEL_JOB = "CANCEL_JOB"
NATIVE_OPERATIONS = (
    REGISTER_JOB,
    START_JOB,
    CHECKPOINT_JOB,
    PAUSE_JOB,
    RESUME_JOB,
    COMPLETE_JOB,
    CANCEL_JOB,
)

MISSING = "MISSING"
READY = "READY"
RUNNING = "RUNNING"
PAUSED = "PAUSED"
DONE = "DONE"
CANCELLED = "CANCELLED"
NATIVE_STATES = (MISSING, READY, RUNNING, PAUSED, DONE, CANCELLED)
TERMINAL_STATES = (DONE, CANCELLED)
STATE_MAP = {
    MISSING: "ABSENT",
    READY: "READY",
    RUNNING: "ACTIVE",
    PAUSED: "HELD",
    DONE: "DONE",
    CANCELLED: "CANCELLED",
}

SNAPSHOT_KEYS = frozenset(
    {
        "applied_count",
        "command_count",
        "final_receipt_digest",
        "host_family",
        "host_version",
        "integration_api",
        "records",
        "rejected_count",
        "snapshot_digest",
    }
)
RECORD_KEYS = frozenset(
    {
        "checkpoint_count",
        "job_id",
        "last_checkpoint",
        "record_digest",
        "state",
        "version",
    }
)
RECEIPT_KEYS = frozenset(
    {
        "after_state",
        "after_version",
        "applied",
        "before_state",
        "before_version",
        "command_digest",
        "command_id",
        "expected_version",
        "job_id",
        "operation",
        "previous_receipt_digest",
        "reason",
        "receipt_digest",
        "sequence",
        "state_digest",
    }
)


class ObservationRejected(ValueError):
    """Raised when exported observation evidence fails closed."""

    def __init__(self, reason: str):
        super().__init__(reason)
        self.reason = reason


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


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
        raise ObservationRejected(f"{name.upper()}_TYPE_INVALID")
    if value < minimum:
        raise ObservationRejected(f"{name.upper()}_RANGE_INVALID")
    return value


def _nonempty_text(value: object, name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ObservationRejected(f"{name.upper()}_INVALID")
    return value.strip()


def _mapping(value: object, name: str) -> Mapping[str, object]:
    if not isinstance(value, Mapping):
        raise ObservationRejected(f"{name.upper()}_TYPE_INVALID")
    if any(not isinstance(key, str) for key in value):
        raise ObservationRejected(f"{name.upper()}_KEY_INVALID")
    return value


def _exact_keys(value: Mapping[str, object], expected: frozenset[str], name: str) -> None:
    actual = frozenset(value)
    if actual != expected:
        missing = sorted(expected - actual)
        extra = sorted(actual - expected)
        if missing:
            raise ObservationRejected(f"{name.upper()}_FIELD_MISSING:{missing[0]}")
        raise ObservationRejected(f"{name.upper()}_FIELD_EXTRA:{extra[0]}")


def _copy_json(value: object) -> object:
    try:
        return json.loads(_canonical_json(value))
    except (TypeError, ValueError) as exc:
        raise ObservationRejected("NON_CANONICAL_OBSERVATION_VALUE") from exc


@dataclass(frozen=True)
class AdapterIdentity:
    adapter_id: str
    adapter_version: str
    mode: str
    execution_authority: str
    command_surface: Tuple[str, ...]
    identity_digest: str

    def unsigned_record(self) -> dict[str, object]:
        return {
            "adapter_id": self.adapter_id,
            "adapter_version": self.adapter_version,
            "command_surface": list(self.command_surface),
            "execution_authority": self.execution_authority,
            "mode": self.mode,
        }

    def record(self) -> dict[str, object]:
        return {**self.unsigned_record(), "identity_digest": self.identity_digest}


@dataclass(frozen=True)
class ObservedSubject:
    subject_id: str
    native_state: str
    observed_state: str
    native_version: int
    checkpoint_count: int
    source_record_digest: str
    subject_digest: str

    def unsigned_record(self) -> dict[str, object]:
        return {
            "checkpoint_count": self.checkpoint_count,
            "native_state": self.native_state,
            "native_version": self.native_version,
            "observed_state": self.observed_state,
            "source_record_digest": self.source_record_digest,
            "subject_id": self.subject_id,
        }

    def record(self) -> dict[str, object]:
        return {**self.unsigned_record(), "subject_digest": self.subject_digest}


@dataclass(frozen=True)
class ObservationEvent:
    sequence: int
    subject_id: str
    native_operation: str
    native_before_state: str
    native_before_version: int
    native_after_state: str
    native_after_version: int
    observed_before_state: str
    observed_after_state: str
    applied: bool
    reason: str
    source_command_digest: str
    source_receipt_digest: str
    previous_observation_digest: str
    observation_digest: str

    def unsigned_record(self) -> dict[str, object]:
        return {
            "applied": self.applied,
            "native_after_state": self.native_after_state,
            "native_after_version": self.native_after_version,
            "native_before_state": self.native_before_state,
            "native_before_version": self.native_before_version,
            "native_operation": self.native_operation,
            "observed_after_state": self.observed_after_state,
            "observed_before_state": self.observed_before_state,
            "previous_observation_digest": self.previous_observation_digest,
            "reason": self.reason,
            "sequence": self.sequence,
            "source_command_digest": self.source_command_digest,
            "source_receipt_digest": self.source_receipt_digest,
            "subject_id": self.subject_id,
        }

    def record(self) -> dict[str, object]:
        return {**self.unsigned_record(), "observation_digest": self.observation_digest}


@dataclass(frozen=True)
class ObservationBatch:
    adapter_identity: AdapterIdentity
    host_family: str
    host_version: str
    integration_api: str
    source_snapshot_digest: str
    source_final_receipt_digest: str
    source_command_count: int
    source_applied_count: int
    source_rejected_count: int
    subjects: Tuple[ObservedSubject, ...]
    events: Tuple[ObservationEvent, ...]
    final_observation_digest: str
    batch_digest: str

    def unsigned_record(self) -> dict[str, object]:
        return {
            "adapter_identity": self.adapter_identity.record(),
            "events": [event.record() for event in self.events],
            "final_observation_digest": self.final_observation_digest,
            "host_family": self.host_family,
            "host_version": self.host_version,
            "integration_api": self.integration_api,
            "source_applied_count": self.source_applied_count,
            "source_command_count": self.source_command_count,
            "source_final_receipt_digest": self.source_final_receipt_digest,
            "source_rejected_count": self.source_rejected_count,
            "source_snapshot_digest": self.source_snapshot_digest,
            "subjects": [subject.record() for subject in self.subjects],
        }

    def record(self) -> dict[str, object]:
        return {**self.unsigned_record(), "batch_digest": self.batch_digest}


@dataclass(frozen=True)
class ObservationReplay:
    passed: bool
    reason: str
    event_count: int
    final_observation_digest: str
    replay_digest: str


def build_identity() -> AdapterIdentity:
    unsigned = {
        "adapter_id": ADAPTER_ID,
        "adapter_version": ADAPTER_VERSION,
        "command_surface": list(COMMAND_SURFACE),
        "execution_authority": EXECUTION_AUTHORITY,
        "mode": MODE,
    }
    return AdapterIdentity(
        adapter_id=ADAPTER_ID,
        adapter_version=ADAPTER_VERSION,
        mode=MODE,
        execution_authority=EXECUTION_AUTHORITY,
        command_surface=COMMAND_SURFACE,
        identity_digest=_digest_json(unsigned),
    )


def _validate_identity(identity: AdapterIdentity) -> None:
    if identity != build_identity():
        raise ObservationRejected("ADAPTER_IDENTITY_INVALID")


def _normalise_record(raw_record: object) -> ObservedSubject:
    record = _mapping(raw_record, "record")
    _exact_keys(record, RECORD_KEYS, "record")
    job_id = _nonempty_text(record["job_id"], "job_id")
    state = _nonempty_text(record["state"], "record_state").upper()
    if state not in NATIVE_STATES or state == MISSING:
        raise ObservationRejected("RECORD_STATE_INVALID")
    version = _exact_int(record["version"], "record_version", minimum=1)
    checkpoint_count = _exact_int(record["checkpoint_count"], "checkpoint_count")
    last_checkpoint = record["last_checkpoint"]
    if not isinstance(last_checkpoint, str):
        raise ObservationRejected("LAST_CHECKPOINT_TYPE_INVALID")
    record_digest = record["record_digest"]
    if not _is_digest(record_digest):
        raise ObservationRejected("RECORD_DIGEST_INVALID")
    unsigned = {
        "checkpoint_count": checkpoint_count,
        "job_id": job_id,
        "last_checkpoint": last_checkpoint,
        "state": state,
        "version": version,
    }
    if _digest_json(unsigned) != record_digest:
        raise ObservationRejected("RECORD_DIGEST_MISMATCH")
    subject_unsigned = {
        "checkpoint_count": checkpoint_count,
        "native_state": state,
        "native_version": version,
        "observed_state": STATE_MAP[state],
        "source_record_digest": record_digest,
        "subject_id": job_id,
    }
    return ObservedSubject(
        subject_id=job_id,
        native_state=state,
        observed_state=STATE_MAP[state],
        native_version=version,
        checkpoint_count=checkpoint_count,
        source_record_digest=record_digest,
        subject_digest=_digest_json(subject_unsigned),
    )


def _validate_snapshot(raw_snapshot: object) -> Tuple[Mapping[str, object], Tuple[ObservedSubject, ...]]:
    snapshot = _mapping(raw_snapshot, "snapshot")
    _exact_keys(snapshot, SNAPSHOT_KEYS, "snapshot")
    if snapshot["host_family"] != EXPECTED_HOST_FAMILY:
        raise ObservationRejected("HOST_FAMILY_MISMATCH")
    if snapshot["host_version"] != EXPECTED_HOST_VERSION:
        raise ObservationRejected("HOST_VERSION_MISMATCH")
    if snapshot["integration_api"] != EXPECTED_INTEGRATION_API:
        raise ObservationRejected("INTEGRATION_API_MISMATCH")
    command_count = _exact_int(snapshot["command_count"], "command_count")
    applied_count = _exact_int(snapshot["applied_count"], "applied_count")
    rejected_count = _exact_int(snapshot["rejected_count"], "rejected_count")
    if command_count != applied_count + rejected_count:
        raise ObservationRejected("SNAPSHOT_COUNT_MISMATCH")
    if not _is_digest(snapshot["final_receipt_digest"]):
        raise ObservationRejected("FINAL_RECEIPT_DIGEST_INVALID")
    if not _is_digest(snapshot["snapshot_digest"]):
        raise ObservationRejected("SNAPSHOT_DIGEST_INVALID")
    records = snapshot["records"]
    if isinstance(records, (str, bytes)) or not isinstance(records, Sequence):
        raise ObservationRejected("RECORDS_TYPE_INVALID")
    subjects = tuple(_normalise_record(record) for record in records)
    if len({subject.subject_id for subject in subjects}) != len(subjects):
        raise ObservationRejected("DUPLICATE_SUBJECT_RECORD")
    if tuple(sorted(subjects, key=lambda item: item.subject_id)) != subjects:
        raise ObservationRejected("SUBJECT_RECORD_ORDER_INVALID")
    unsigned = {key: _copy_json(value) for key, value in snapshot.items() if key != "snapshot_digest"}
    if _digest_json(unsigned) != snapshot["snapshot_digest"]:
        raise ObservationRejected("SNAPSHOT_DIGEST_MISMATCH")
    return snapshot, subjects


def _validate_receipt_shape(raw_receipt: object, expected_sequence: int, previous_digest: str) -> Mapping[str, object]:
    receipt = _mapping(raw_receipt, "receipt")
    _exact_keys(receipt, RECEIPT_KEYS, "receipt")
    sequence = _exact_int(receipt["sequence"], "receipt_sequence", minimum=1)
    if sequence != expected_sequence:
        raise ObservationRejected("RECEIPT_SEQUENCE_MISMATCH")
    if receipt["previous_receipt_digest"] != previous_digest:
        raise ObservationRejected("RECEIPT_CHAIN_MISMATCH")
    for field in ("command_digest", "receipt_digest", "state_digest"):
        if not _is_digest(receipt[field]):
            raise ObservationRejected(f"{field.upper()}_INVALID")
    for field in ("command_id", "job_id", "operation", "before_state", "after_state", "reason"):
        _nonempty_text(receipt[field], field)
    _exact_int(receipt["expected_version"], "expected_version")
    _exact_int(receipt["before_version"], "before_version")
    _exact_int(receipt["after_version"], "after_version")
    if not isinstance(receipt["applied"], bool):
        raise ObservationRejected("APPLIED_TYPE_INVALID")
    operation = str(receipt["operation"]).upper()
    before_state = str(receipt["before_state"]).upper()
    after_state = str(receipt["after_state"]).upper()
    if operation not in NATIVE_OPERATIONS:
        raise ObservationRejected("UNKNOWN_NATIVE_OPERATION")
    if before_state not in NATIVE_STATES or after_state not in NATIVE_STATES:
        raise ObservationRejected("RECEIPT_STATE_INVALID")
    unsigned = {key: _copy_json(value) for key, value in receipt.items() if key != "receipt_digest"}
    if _digest_json(unsigned) != receipt["receipt_digest"]:
        raise ObservationRejected("RECEIPT_DIGEST_MISMATCH")
    return receipt


def _expected_transition(operation: str, before_state: str) -> str | None:
    if operation == REGISTER_JOB:
        return READY if before_state == MISSING else None
    if before_state in TERMINAL_STATES or before_state == MISSING:
        return None
    if operation == START_JOB:
        return RUNNING if before_state == READY else None
    if operation == CHECKPOINT_JOB:
        return RUNNING if before_state == RUNNING else None
    if operation == PAUSE_JOB:
        return PAUSED if before_state == RUNNING else None
    if operation == RESUME_JOB:
        return RUNNING if before_state == PAUSED else None
    if operation == COMPLETE_JOB:
        return DONE if before_state == RUNNING else None
    if operation == CANCEL_JOB:
        return CANCELLED
    return None


def _event_from_receipt(receipt: Mapping[str, object], previous_observation_digest: str) -> ObservationEvent:
    unsigned = {
        "applied": receipt["applied"],
        "native_after_state": receipt["after_state"],
        "native_after_version": receipt["after_version"],
        "native_before_state": receipt["before_state"],
        "native_before_version": receipt["before_version"],
        "native_operation": receipt["operation"],
        "observed_after_state": STATE_MAP[str(receipt["after_state"])],
        "observed_before_state": STATE_MAP[str(receipt["before_state"])],
        "previous_observation_digest": previous_observation_digest,
        "reason": receipt["reason"],
        "sequence": receipt["sequence"],
        "source_command_digest": receipt["command_digest"],
        "source_receipt_digest": receipt["receipt_digest"],
        "subject_id": receipt["job_id"],
    }
    return ObservationEvent(
        sequence=int(receipt["sequence"]),
        subject_id=str(receipt["job_id"]),
        native_operation=str(receipt["operation"]),
        native_before_state=str(receipt["before_state"]),
        native_before_version=int(receipt["before_version"]),
        native_after_state=str(receipt["after_state"]),
        native_after_version=int(receipt["after_version"]),
        observed_before_state=STATE_MAP[str(receipt["before_state"])],
        observed_after_state=STATE_MAP[str(receipt["after_state"])],
        applied=bool(receipt["applied"]),
        reason=str(receipt["reason"]),
        source_command_digest=str(receipt["command_digest"]),
        source_receipt_digest=str(receipt["receipt_digest"]),
        previous_observation_digest=previous_observation_digest,
        observation_digest=_digest_json(unsigned),
    )


class ReadOnlyObservationAdapter:
    """Validates host exports and produces deterministic observation evidence."""

    def identity(self) -> AdapterIdentity:
        return build_identity()

    def normalise_record(self, raw_record: object) -> ObservedSubject:
        return _normalise_record(raw_record)

    def observe(self, raw_snapshot: object, raw_receipts: Iterable[object]) -> ObservationBatch:
        identity = self.identity()
        _validate_identity(identity)
        snapshot, subjects = _validate_snapshot(raw_snapshot)
        receipts = tuple(raw_receipts)
        if len(receipts) != snapshot["command_count"]:
            raise ObservationRejected("RECEIPT_COUNT_MISMATCH")

        states: dict[str, Tuple[str, int, int]] = {}
        source_previous = ZERO_DIGEST
        observation_previous = ZERO_DIGEST
        events: list[ObservationEvent] = []
        applied_count = 0
        rejected_count = 0

        for index, raw_receipt in enumerate(receipts, 1):
            receipt = _validate_receipt_shape(raw_receipt, index, source_previous)
            job_id = str(receipt["job_id"])
            current_state, current_version, checkpoints = states.get(job_id, (MISSING, 0, 0))
            if receipt["before_state"] != current_state or receipt["before_version"] != current_version:
                raise ObservationRejected("RECEIPT_BEFORE_STATE_MISMATCH")
            if receipt["expected_version"] != current_version:
                if receipt["applied"]:
                    raise ObservationRejected("APPLIED_EXPECTED_VERSION_MISMATCH")
            if receipt["applied"]:
                if receipt["reason"] != "APPLIED":
                    raise ObservationRejected("APPLIED_REASON_INVALID")
                expected_state = _expected_transition(str(receipt["operation"]), current_state)
                if expected_state is None or receipt["after_state"] != expected_state:
                    raise ObservationRejected("APPLIED_TRANSITION_INVALID")
                if receipt["after_version"] != current_version + 1:
                    raise ObservationRejected("APPLIED_VERSION_INVALID")
                if receipt["operation"] == CHECKPOINT_JOB:
                    checkpoints += 1
                states[job_id] = (str(receipt["after_state"]), int(receipt["after_version"]), checkpoints)
                applied_count += 1
            else:
                if receipt["reason"] == "APPLIED":
                    raise ObservationRejected("REJECTED_REASON_INVALID")
                if receipt["after_state"] != current_state or receipt["after_version"] != current_version:
                    raise ObservationRejected("REJECTED_STATE_CHANGED")
                rejected_count += 1

            event = _event_from_receipt(receipt, observation_previous)
            events.append(event)
            observation_previous = event.observation_digest
            source_previous = str(receipt["receipt_digest"])

        if applied_count != snapshot["applied_count"]:
            raise ObservationRejected("APPLIED_COUNT_MISMATCH")
        if rejected_count != snapshot["rejected_count"]:
            raise ObservationRejected("REJECTED_COUNT_MISMATCH")
        if source_previous != snapshot["final_receipt_digest"]:
            raise ObservationRejected("FINAL_RECEIPT_MISMATCH")
        if set(states) != {subject.subject_id for subject in subjects}:
            raise ObservationRejected("SNAPSHOT_SUBJECT_SET_MISMATCH")
        for subject in subjects:
            state, version, checkpoints = states[subject.subject_id]
            if state != subject.native_state:
                raise ObservationRejected("SNAPSHOT_FINAL_STATE_MISMATCH")
            if version != subject.native_version:
                raise ObservationRejected("SNAPSHOT_FINAL_VERSION_MISMATCH")
            if checkpoints != subject.checkpoint_count:
                raise ObservationRejected("SNAPSHOT_CHECKPOINT_COUNT_MISMATCH")

        unsigned = {
            "adapter_identity": identity.record(),
            "events": [event.record() for event in events],
            "final_observation_digest": observation_previous,
            "host_family": snapshot["host_family"],
            "host_version": snapshot["host_version"],
            "integration_api": snapshot["integration_api"],
            "source_applied_count": snapshot["applied_count"],
            "source_command_count": snapshot["command_count"],
            "source_final_receipt_digest": snapshot["final_receipt_digest"],
            "source_rejected_count": snapshot["rejected_count"],
            "source_snapshot_digest": snapshot["snapshot_digest"],
            "subjects": [subject.record() for subject in subjects],
        }
        return ObservationBatch(
            adapter_identity=identity,
            host_family=str(snapshot["host_family"]),
            host_version=str(snapshot["host_version"]),
            integration_api=str(snapshot["integration_api"]),
            source_snapshot_digest=str(snapshot["snapshot_digest"]),
            source_final_receipt_digest=str(snapshot["final_receipt_digest"]),
            source_command_count=int(snapshot["command_count"]),
            source_applied_count=int(snapshot["applied_count"]),
            source_rejected_count=int(snapshot["rejected_count"]),
            subjects=subjects,
            events=tuple(events),
            final_observation_digest=observation_previous,
            batch_digest=_digest_json(unsigned),
        )


def replay_observation(batch: object) -> ObservationReplay:
    if not isinstance(batch, ObservationBatch):
        return ObservationReplay(False, "BATCH_TYPE_INVALID", 0, ZERO_DIGEST, ZERO_DIGEST)
    try:
        _validate_identity(batch.adapter_identity)
    except ObservationRejected as exc:
        return ObservationReplay(False, exc.reason, 0, ZERO_DIGEST, ZERO_DIGEST)
    previous = ZERO_DIGEST
    for expected_sequence, event in enumerate(batch.events, 1):
        if not isinstance(event, ObservationEvent):
            return ObservationReplay(False, "EVENT_TYPE_INVALID", expected_sequence - 1, previous, ZERO_DIGEST)
        if event.sequence != expected_sequence:
            return ObservationReplay(False, "EVENT_SEQUENCE_MISMATCH", expected_sequence - 1, previous, ZERO_DIGEST)
        if event.previous_observation_digest != previous:
            return ObservationReplay(False, "EVENT_CHAIN_MISMATCH", expected_sequence - 1, previous, ZERO_DIGEST)
        if _digest_json(event.unsigned_record()) != event.observation_digest:
            return ObservationReplay(False, "EVENT_DIGEST_MISMATCH", expected_sequence - 1, previous, ZERO_DIGEST)
        if event.observed_before_state != STATE_MAP.get(event.native_before_state):
            return ObservationReplay(False, "EVENT_BEFORE_MAPPING_INVALID", expected_sequence - 1, previous, ZERO_DIGEST)
        if event.observed_after_state != STATE_MAP.get(event.native_after_state):
            return ObservationReplay(False, "EVENT_AFTER_MAPPING_INVALID", expected_sequence - 1, previous, ZERO_DIGEST)
        expected_state = _expected_transition(event.native_operation, event.native_before_state)
        if event.applied:
            if expected_state != event.native_after_state or event.native_after_version != event.native_before_version + 1:
                return ObservationReplay(False, "EVENT_TRANSITION_INVALID", expected_sequence - 1, previous, ZERO_DIGEST)
        elif event.native_after_state != event.native_before_state or event.native_after_version != event.native_before_version:
            return ObservationReplay(False, "EVENT_REJECTION_CHANGED_STATE", expected_sequence - 1, previous, ZERO_DIGEST)
        previous = event.observation_digest
    if previous != batch.final_observation_digest:
        return ObservationReplay(False, "FINAL_OBSERVATION_DIGEST_MISMATCH", len(batch.events), previous, ZERO_DIGEST)
    if _digest_json(batch.unsigned_record()) != batch.batch_digest:
        return ObservationReplay(False, "BATCH_DIGEST_MISMATCH", len(batch.events), previous, ZERO_DIGEST)
    return ObservationReplay(True, "PASS", len(batch.events), previous, batch.batch_digest)


if __name__ == "__main__":
    identity = build_identity()
    print(f"Adapter: {identity.adapter_id} {identity.adapter_version}")
    print(f"Mode: {identity.mode}")
    print(f"Execution authority: {identity.execution_authority}")
    print(f"Command surface entries: {len(identity.command_surface)}")
    print(f"Identity digest: {identity.identity_digest}")
    print("READ-ONLY OBSERVATION ADAPTER SELF-CHECK: PASS")
