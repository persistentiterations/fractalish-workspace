#!/usr/bin/env python3
"""Deterministic native job service.

This module is deliberately self-contained.  It models an ordinary versioned
job service with an append-only command journal and receipt chain.  It has no
knowledge of any external governance, portability, sidecar, or integration
system.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, replace
from typing import Iterable, Mapping, Sequence, Tuple

HOST_FAMILY = "ORDINARY VERSIONED JOB SERVICE"
HOST_VERSION = "1.0"
INTEGRATION_API = "JOB-SERVICE-READ-COMMAND-1"
AUTHORITY_TOKEN = "LOCAL_JOB_SERVICE_AUTHORITY"
ZERO_DIGEST = "0" * 64

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
TERMINAL_STATES = (DONE, CANCELLED)


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


def _nonempty_text(value: object, name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{name} must be a non-empty string")
    return value.strip()


def _exact_int(value: object, name: str, *, minimum: int = 0) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise TypeError(f"{name} must be an exact integer")
    if value < minimum:
        raise ValueError(f"{name} must be >= {minimum}")
    return value


def _normalise_payload(
    payload: Mapping[object, object] | Iterable[Tuple[object, object]] | None,
) -> Tuple[Tuple[str, str], ...]:
    if payload is None:
        return ()
    source = payload.items() if isinstance(payload, Mapping) else tuple(payload)
    rows: list[Tuple[str, str]] = []
    for key, value in source:
        rows.append((_nonempty_text(key, "payload key"), _nonempty_text(value, "payload value")))
    rows.sort()
    if len({key for key, _ in rows}) != len(rows):
        raise ValueError("payload keys must be unique")
    return tuple(rows)


def _expected_command_id(unsigned: Mapping[str, object]) -> str:
    seed = dict(unsigned)
    seed.pop("command_id", None)
    return "CMD-" + _digest_json(seed)[:24].upper()


@dataclass(frozen=True)
class JobCommand:
    command_id: str
    operation: str
    job_id: str
    expected_version: int
    idempotency_key: str
    authority_token: str
    payload: Tuple[Tuple[str, str], ...]
    command_digest: str

    def unsigned_record(self) -> dict[str, object]:
        return {
            "authority_token": self.authority_token,
            "command_id": self.command_id,
            "expected_version": self.expected_version,
            "idempotency_key": self.idempotency_key,
            "job_id": self.job_id,
            "operation": self.operation,
            "payload": [[key, value] for key, value in self.payload],
        }

    def record(self) -> dict[str, object]:
        return {**self.unsigned_record(), "command_digest": self.command_digest}


@dataclass(frozen=True)
class JobRecord:
    job_id: str
    state: str
    version: int
    checkpoint_count: int
    last_checkpoint: str
    record_digest: str

    def unsigned_record(self) -> dict[str, object]:
        return {
            "checkpoint_count": self.checkpoint_count,
            "job_id": self.job_id,
            "last_checkpoint": self.last_checkpoint,
            "state": self.state,
            "version": self.version,
        }

    def record(self) -> dict[str, object]:
        return {**self.unsigned_record(), "record_digest": self.record_digest}


@dataclass(frozen=True)
class HostReceipt:
    sequence: int
    command_id: str
    command_digest: str
    operation: str
    job_id: str
    expected_version: int
    before_state: str
    before_version: int
    after_state: str
    after_version: int
    applied: bool
    reason: str
    state_digest: str
    previous_receipt_digest: str
    receipt_digest: str

    def unsigned_record(self) -> dict[str, object]:
        return {
            "after_state": self.after_state,
            "after_version": self.after_version,
            "applied": self.applied,
            "before_state": self.before_state,
            "before_version": self.before_version,
            "command_digest": self.command_digest,
            "command_id": self.command_id,
            "expected_version": self.expected_version,
            "job_id": self.job_id,
            "operation": self.operation,
            "previous_receipt_digest": self.previous_receipt_digest,
            "reason": self.reason,
            "sequence": self.sequence,
            "state_digest": self.state_digest,
        }

    def record(self) -> dict[str, object]:
        return {**self.unsigned_record(), "receipt_digest": self.receipt_digest}


@dataclass(frozen=True)
class HostSnapshot:
    host_family: str
    host_version: str
    integration_api: str
    records: Tuple[JobRecord, ...]
    command_count: int
    applied_count: int
    rejected_count: int
    final_receipt_digest: str
    snapshot_digest: str

    def unsigned_record(self) -> dict[str, object]:
        return {
            "applied_count": self.applied_count,
            "command_count": self.command_count,
            "final_receipt_digest": self.final_receipt_digest,
            "host_family": self.host_family,
            "host_version": self.host_version,
            "integration_api": self.integration_api,
            "records": [record.record() for record in self.records],
            "rejected_count": self.rejected_count,
        }

    def record(self) -> dict[str, object]:
        return {**self.unsigned_record(), "snapshot_digest": self.snapshot_digest}


@dataclass(frozen=True)
class HostRun:
    commands: Tuple[JobCommand, ...]
    receipts: Tuple[HostReceipt, ...]
    snapshot: HostSnapshot
    run_digest: str

    def unsigned_record(self) -> dict[str, object]:
        return {
            "commands": [command.record() for command in self.commands],
            "receipts": [receipt.record() for receipt in self.receipts],
            "snapshot": self.snapshot.record(),
        }


@dataclass(frozen=True)
class ReplayResult:
    passed: bool
    reason: str
    receipt_count: int
    final_receipt_digest: str
    snapshot_digest: str
    replay_digest: str


class NativeJobService:
    """Versioned command processor with exact receipts and deterministic replay."""

    def __init__(self) -> None:
        self._records: dict[str, JobRecord] = {}
        self._commands: list[JobCommand] = []
        self._receipts: list[HostReceipt] = []
        self._idempotency: dict[str, str] = {}

    @staticmethod
    def _make_record(
        job_id: str,
        state: str,
        version: int,
        checkpoint_count: int = 0,
        last_checkpoint: str = "",
    ) -> JobRecord:
        unsigned = {
            "checkpoint_count": checkpoint_count,
            "job_id": job_id,
            "last_checkpoint": last_checkpoint,
            "state": state,
            "version": version,
        }
        return JobRecord(
            job_id=job_id,
            state=state,
            version=version,
            checkpoint_count=checkpoint_count,
            last_checkpoint=last_checkpoint,
            record_digest=_digest_json(unsigned),
        )

    def _state_digest(self) -> str:
        return _digest_json([self._records[key].record() for key in sorted(self._records)])

    def snapshot(self) -> HostSnapshot:
        records = tuple(self._records[key] for key in sorted(self._records))
        applied = sum(1 for receipt in self._receipts if receipt.applied)
        rejected = len(self._receipts) - applied
        unsigned = {
            "applied_count": applied,
            "command_count": len(self._commands),
            "final_receipt_digest": self._receipts[-1].receipt_digest if self._receipts else ZERO_DIGEST,
            "host_family": HOST_FAMILY,
            "host_version": HOST_VERSION,
            "integration_api": INTEGRATION_API,
            "records": [record.record() for record in records],
            "rejected_count": rejected,
        }
        return HostSnapshot(
            host_family=HOST_FAMILY,
            host_version=HOST_VERSION,
            integration_api=INTEGRATION_API,
            records=records,
            command_count=len(self._commands),
            applied_count=applied,
            rejected_count=rejected,
            final_receipt_digest=unsigned["final_receipt_digest"],
            snapshot_digest=_digest_json(unsigned),
        )

    def _append_receipt(
        self,
        command: JobCommand,
        *,
        before_state: str,
        before_version: int,
        after_state: str,
        after_version: int,
        applied: bool,
        reason: str,
    ) -> HostReceipt:
        unsigned = {
            "after_state": after_state,
            "after_version": after_version,
            "applied": applied,
            "before_state": before_state,
            "before_version": before_version,
            "command_digest": command.command_digest,
            "command_id": command.command_id,
            "expected_version": command.expected_version,
            "job_id": command.job_id,
            "operation": command.operation,
            "previous_receipt_digest": self._receipts[-1].receipt_digest if self._receipts else ZERO_DIGEST,
            "reason": reason,
            "sequence": len(self._receipts) + 1,
            "state_digest": self._state_digest(),
        }
        receipt = HostReceipt(
            sequence=unsigned["sequence"],
            command_id=command.command_id,
            command_digest=command.command_digest,
            operation=command.operation,
            job_id=command.job_id,
            expected_version=command.expected_version,
            before_state=before_state,
            before_version=before_version,
            after_state=after_state,
            after_version=after_version,
            applied=applied,
            reason=reason,
            state_digest=unsigned["state_digest"],
            previous_receipt_digest=unsigned["previous_receipt_digest"],
            receipt_digest=_digest_json(unsigned),
        )
        self._receipts.append(receipt)
        return receipt

    def submit(self, command: JobCommand) -> HostReceipt:
        before = self._records.get(command.job_id)
        before_state = before.state if before else MISSING
        before_version = before.version if before else 0

        valid, reason = validate_command(command)
        if not valid:
            self._commands.append(command)
            return self._append_receipt(
                command,
                before_state=before_state,
                before_version=before_version,
                after_state=before_state,
                after_version=before_version,
                applied=False,
                reason=reason,
            )

        self._commands.append(command)
        prior_digest = self._idempotency.get(command.idempotency_key)
        if prior_digest is not None:
            reason = "DUPLICATE_IDEMPOTENCY_KEY" if prior_digest == command.command_digest else "IDEMPOTENCY_KEY_CONFLICT"
            return self._append_receipt(
                command,
                before_state=before_state,
                before_version=before_version,
                after_state=before_state,
                after_version=before_version,
                applied=False,
                reason=reason,
            )

        if command.authority_token != AUTHORITY_TOKEN:
            return self._append_receipt(
                command,
                before_state=before_state,
                before_version=before_version,
                after_state=before_state,
                after_version=before_version,
                applied=False,
                reason="AUTHORITY_TOKEN_REJECTED",
            )

        if command.operation == REGISTER_JOB:
            if before is not None:
                reason = "JOB_ALREADY_EXISTS"
            elif command.expected_version != 0:
                reason = "EXPECTED_VERSION_MISMATCH"
            else:
                self._records[command.job_id] = self._make_record(command.job_id, READY, 1)
                self._idempotency[command.idempotency_key] = command.command_digest
                return self._append_receipt(
                    command,
                    before_state=MISSING,
                    before_version=0,
                    after_state=READY,
                    after_version=1,
                    applied=True,
                    reason="APPLIED",
                )
        elif before is None:
            reason = "JOB_NOT_FOUND"
        elif command.expected_version != before.version:
            reason = "EXPECTED_VERSION_MISMATCH"
        else:
            transition = _transition(before, command)
            if isinstance(transition, str):
                reason = transition
            else:
                self._records[command.job_id] = transition
                self._idempotency[command.idempotency_key] = command.command_digest
                return self._append_receipt(
                    command,
                    before_state=before.state,
                    before_version=before.version,
                    after_state=transition.state,
                    after_version=transition.version,
                    applied=True,
                    reason="APPLIED",
                )

        return self._append_receipt(
            command,
            before_state=before_state,
            before_version=before_version,
            after_state=before_state,
            after_version=before_version,
            applied=False,
            reason=reason,
        )

    def export_run(self) -> HostRun:
        snapshot = self.snapshot()
        unsigned = {
            "commands": [command.record() for command in self._commands],
            "receipts": [receipt.record() for receipt in self._receipts],
            "snapshot": snapshot.record(),
        }
        return HostRun(
            commands=tuple(self._commands),
            receipts=tuple(self._receipts),
            snapshot=snapshot,
            run_digest=_digest_json(unsigned),
        )


def _transition(record: JobRecord, command: JobCommand) -> JobRecord | str:
    operation = command.operation
    if record.state in TERMINAL_STATES:
        return "TERMINAL_STATE"
    if operation == START_JOB:
        if record.state != READY:
            return "INVALID_STATE_TRANSITION"
        return NativeJobService._make_record(record.job_id, RUNNING, record.version + 1, record.checkpoint_count, record.last_checkpoint)
    if operation == CHECKPOINT_JOB:
        if record.state != RUNNING:
            return "INVALID_STATE_TRANSITION"
        checkpoint = dict(command.payload).get("checkpoint", "")
        if not checkpoint:
            return "CHECKPOINT_REQUIRED"
        return NativeJobService._make_record(record.job_id, RUNNING, record.version + 1, record.checkpoint_count + 1, checkpoint)
    if operation == PAUSE_JOB:
        if record.state != RUNNING:
            return "INVALID_STATE_TRANSITION"
        return NativeJobService._make_record(record.job_id, PAUSED, record.version + 1, record.checkpoint_count, record.last_checkpoint)
    if operation == RESUME_JOB:
        if record.state != PAUSED:
            return "INVALID_STATE_TRANSITION"
        return NativeJobService._make_record(record.job_id, RUNNING, record.version + 1, record.checkpoint_count, record.last_checkpoint)
    if operation == COMPLETE_JOB:
        if record.state != RUNNING:
            return "INVALID_STATE_TRANSITION"
        return NativeJobService._make_record(record.job_id, DONE, record.version + 1, record.checkpoint_count, record.last_checkpoint)
    if operation == CANCEL_JOB:
        return NativeJobService._make_record(record.job_id, CANCELLED, record.version + 1, record.checkpoint_count, record.last_checkpoint)
    return "UNKNOWN_OPERATION"


def make_command(
    operation: str,
    job_id: str,
    expected_version: int,
    idempotency_key: str,
    *,
    authority_token: str = AUTHORITY_TOKEN,
    payload: Mapping[object, object] | Iterable[Tuple[object, object]] | None = None,
) -> JobCommand:
    operation = _nonempty_text(operation, "operation").upper()
    job_id = _nonempty_text(job_id, "job_id")
    expected_version = _exact_int(expected_version, "expected_version")
    idempotency_key = _nonempty_text(idempotency_key, "idempotency_key")
    authority_token = _nonempty_text(authority_token, "authority_token")
    normalised_payload = _normalise_payload(payload)
    seed = {
        "authority_token": authority_token,
        "expected_version": expected_version,
        "idempotency_key": idempotency_key,
        "job_id": job_id,
        "operation": operation,
        "payload": [[key, value] for key, value in normalised_payload],
    }
    command_id = _expected_command_id(seed)
    unsigned = {**seed, "command_id": command_id}
    return JobCommand(
        command_id=command_id,
        operation=operation,
        job_id=job_id,
        expected_version=expected_version,
        idempotency_key=idempotency_key,
        authority_token=authority_token,
        payload=normalised_payload,
        command_digest=_digest_json(unsigned),
    )


def validate_command_integrity(command: object) -> Tuple[bool, str]:
    if not isinstance(command, JobCommand):
        return False, "COMMAND_TYPE_INVALID"
    try:
        _nonempty_text(command.command_id, "command_id")
        _nonempty_text(command.operation, "operation")
        _nonempty_text(command.job_id, "job_id")
        _exact_int(command.expected_version, "expected_version")
        _nonempty_text(command.idempotency_key, "idempotency_key")
        _nonempty_text(command.authority_token, "authority_token")
        _normalise_payload(command.payload)
    except (TypeError, ValueError):
        return False, "COMMAND_FIELDS_INVALID"
    expected_id = _expected_command_id(command.unsigned_record())
    if command.command_id != expected_id:
        return False, "COMMAND_ID_MISMATCH"
    if not _is_digest(command.command_digest):
        return False, "COMMAND_DIGEST_INVALID"
    if _digest_json(command.unsigned_record()) != command.command_digest:
        return False, "COMMAND_DIGEST_MISMATCH"
    return True, "VALID"


def validate_command(command: object) -> Tuple[bool, str]:
    valid, reason = validate_command_integrity(command)
    if not valid:
        return valid, reason
    if command.operation not in NATIVE_OPERATIONS:
        return False, "UNKNOWN_OPERATION"
    return True, "VALID"


def validate_record(record: object) -> Tuple[bool, str]:
    if not isinstance(record, JobRecord):
        return False, "RECORD_TYPE_INVALID"
    if record.state not in (READY, RUNNING, PAUSED, DONE, CANCELLED):
        return False, "RECORD_STATE_INVALID"
    try:
        _nonempty_text(record.job_id, "job_id")
        _exact_int(record.version, "version", minimum=1)
        _exact_int(record.checkpoint_count, "checkpoint_count")
    except (TypeError, ValueError):
        return False, "RECORD_FIELDS_INVALID"
    if not _is_digest(record.record_digest) or _digest_json(record.unsigned_record()) != record.record_digest:
        return False, "RECORD_DIGEST_MISMATCH"
    return True, "VALID"


def validate_receipt(receipt: object, previous_digest: str, expected_sequence: int) -> Tuple[bool, str]:
    if not isinstance(receipt, HostReceipt):
        return False, "RECEIPT_TYPE_INVALID"
    if receipt.sequence != expected_sequence:
        return False, "RECEIPT_SEQUENCE_MISMATCH"
    if receipt.previous_receipt_digest != previous_digest:
        return False, "RECEIPT_CHAIN_MISMATCH"
    if not _is_digest(receipt.receipt_digest):
        return False, "RECEIPT_DIGEST_INVALID"
    if _digest_json(receipt.unsigned_record()) != receipt.receipt_digest:
        return False, "RECEIPT_DIGEST_MISMATCH"
    return True, "VALID"


def replay_run(run: object) -> ReplayResult:
    if not isinstance(run, HostRun):
        return ReplayResult(False, "RUN_TYPE_INVALID", 0, ZERO_DIGEST, ZERO_DIGEST, ZERO_DIGEST)
    if len(run.commands) != len(run.receipts):
        return ReplayResult(False, "COMMAND_RECEIPT_COUNT_MISMATCH", 0, ZERO_DIGEST, ZERO_DIGEST, ZERO_DIGEST)
    service = NativeJobService()
    previous = ZERO_DIGEST
    for index, (command, expected_receipt) in enumerate(zip(run.commands, run.receipts), 1):
        valid_command, reason = validate_command_integrity(command)
        if not valid_command:
            return ReplayResult(False, reason, index - 1, previous, ZERO_DIGEST, ZERO_DIGEST)
        valid_receipt, reason = validate_receipt(expected_receipt, previous, index)
        if not valid_receipt:
            return ReplayResult(False, reason, index - 1, previous, ZERO_DIGEST, ZERO_DIGEST)
        actual_receipt = service.submit(command)
        if actual_receipt != expected_receipt:
            return ReplayResult(False, "RECEIPT_REPLAY_MISMATCH", index - 1, previous, ZERO_DIGEST, ZERO_DIGEST)
        previous = actual_receipt.receipt_digest
    replayed = service.export_run()
    if replayed.snapshot != run.snapshot:
        return ReplayResult(False, "SNAPSHOT_REPLAY_MISMATCH", len(run.receipts), previous, replayed.snapshot.snapshot_digest, replayed.run_digest)
    if replayed.run_digest != run.run_digest:
        return ReplayResult(False, "RUN_DIGEST_MISMATCH", len(run.receipts), previous, replayed.snapshot.snapshot_digest, replayed.run_digest)
    return ReplayResult(True, "PASS", len(run.receipts), previous, replayed.snapshot.snapshot_digest, replayed.run_digest)


def build_native_baseline() -> HostRun:
    service = NativeJobService()
    commands = (
        make_command(REGISTER_JOB, "JOB-001", 0, "BASE-001"),
        make_command(START_JOB, "JOB-001", 1, "BASE-002"),
        make_command(CHECKPOINT_JOB, "JOB-001", 2, "BASE-003", payload={"checkpoint": "NATIVE-CHECKPOINT-1"}),
        make_command(PAUSE_JOB, "JOB-001", 3, "BASE-004"),
        make_command(RESUME_JOB, "JOB-001", 4, "BASE-005"),
        make_command(COMPLETE_JOB, "JOB-001", 5, "BASE-006"),
    )
    for command in commands:
        receipt = service.submit(command)
        if not receipt.applied:
            raise RuntimeError(f"baseline command rejected: {receipt.reason}")
    return service.export_run()


def build_rejection_campaign() -> HostRun:
    service = NativeJobService()
    valid_register = make_command(REGISTER_JOB, "JOB-ATTACK", 0, "VALID-001")
    service.submit(valid_register)
    service.submit(make_command(START_JOB, "JOB-ATTACK", 1, "VALID-002"))

    cases: list[JobCommand] = [
        make_command("UNKNOWN", "JOB-ATTACK", 2, "BAD-001"),
        make_command(PAUSE_JOB, "MISSING-JOB", 0, "BAD-002"),
        make_command(PAUSE_JOB, "JOB-ATTACK", 1, "BAD-003"),
        make_command(PAUSE_JOB, "JOB-ATTACK", 99, "BAD-004"),
        make_command(PAUSE_JOB, "JOB-ATTACK", 2, "BAD-005", authority_token="WRONG"),
        make_command(START_JOB, "JOB-ATTACK", 2, "BAD-006"),
        make_command(RESUME_JOB, "JOB-ATTACK", 2, "BAD-007"),
        make_command(COMPLETE_JOB, "JOB-ATTACK", 1, "BAD-008"),
        make_command(CHECKPOINT_JOB, "JOB-ATTACK", 2, "BAD-009"),
        make_command(REGISTER_JOB, "JOB-ATTACK", 0, "BAD-010"),
    ]
    for command in cases:
        service.submit(command)

    accepted_pause = make_command(PAUSE_JOB, "JOB-ATTACK", 2, "VALID-003")
    service.submit(accepted_pause)
    service.submit(accepted_pause)
    service.submit(make_command(RESUME_JOB, "JOB-ATTACK", 3, "VALID-003"))
    service.submit(make_command(COMPLETE_JOB, "JOB-ATTACK", 3, "BAD-011"))
    service.submit(make_command(CANCEL_JOB, "JOB-ATTACK", 3, "VALID-004"))
    service.submit(make_command(RESUME_JOB, "JOB-ATTACK", 4, "BAD-012"))
    service.submit(make_command(CANCEL_JOB, "JOB-ATTACK", 4, "BAD-013"))
    return service.export_run()


def rehash_command(command: JobCommand) -> JobCommand:
    return replace(command, command_digest=_digest_json(command.unsigned_record()))


if __name__ == "__main__":
    baseline = build_native_baseline()
    replay = replay_run(baseline)
    record = baseline.snapshot.records[0]
    print(f"Host: {HOST_FAMILY} {HOST_VERSION}")
    print(f"Integration API: {INTEGRATION_API}")
    print(f"Native operations: {', '.join(NATIVE_OPERATIONS)}")
    print(f"Commands: {len(baseline.commands)}")
    print(f"Applied: {baseline.snapshot.applied_count}")
    print(f"Rejected: {baseline.snapshot.rejected_count}")
    print(f"Final state: {record.state}")
    print(f"Final version: {record.version}")
    print(f"Checkpoint count: {record.checkpoint_count}")
    print(f"Run digest: {baseline.run_digest}")
    print(f"Replay digest: {replay.replay_digest}")
    print("ORDINARY JOB SERVICE SELF-QUALIFICATION: PASS" if replay.passed else "ORDINARY JOB SERVICE SELF-QUALIFICATION: FAIL")
