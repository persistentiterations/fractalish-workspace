#!/usr/bin/env python3
"""Independent deterministic lease-queue host for Bolt-On Demonstrator v0.3.

This host is deliberately independent of the bolt-on. It implements an exact,
versioned queue-item state machine with immutable commands, immutable events,
deterministic input-order processing, and a SHA-256 run digest. It imports no
Natural Math, CNTM, adapter, governance, or bolt-on module.

Host-native operations:

ENQUEUE   ABSENT -> READY
CLAIM     READY -> ACTIVE
HEARTBEAT ACTIVE -> ACTIVE
SUSPEND   ACTIVE -> HELD
CONTINUE  HELD -> ACTIVE
FINISH    ACTIVE -> COMPLETE
DROP      READY/ACTIVE/HELD -> DROPPED

No file output is performed.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from typing import Iterable, Sequence, Tuple

HOST_NAME = "DETERMINISTIC LEASE QUEUE HOST"
HOST_VERSION = "1.0"

ABSENT = "ABSENT"
READY = "READY"
ACTIVE = "ACTIVE"
HELD = "HELD"
COMPLETE = "COMPLETE"
DROPPED = "DROPPED"

ENQUEUE = "ENQUEUE"
CLAIM = "CLAIM"
HEARTBEAT = "HEARTBEAT"
SUSPEND = "SUSPEND"
CONTINUE = "CONTINUE"
FINISH = "FINISH"
DROP = "DROP"
SUPPORTED_OPERATIONS: Tuple[str, ...] = (
    ENQUEUE,
    CLAIM,
    HEARTBEAT,
    SUSPEND,
    CONTINUE,
    FINISH,
    DROP,
)

APPLIED = "APPLIED"
REJECTED = "REJECTED"


@dataclass(frozen=True)
class QueueCommand:
    command_id: str
    item_id: str
    operation: str
    expected_version: int

    def canonical_line(self) -> str:
        return "|".join(
            (
                self.command_id,
                self.item_id,
                self.operation,
                str(self.expected_version),
            )
        )


@dataclass(frozen=True)
class QueueRecord:
    item_id: str
    phase: str
    version: int

    def canonical_line(self) -> str:
        return "|".join((self.item_id, self.phase, str(self.version)))


@dataclass(frozen=True)
class QueueEvent:
    sequence: int
    command_id: str
    item_id: str
    event_type: str
    operation: str
    reason: str
    phase_before: str
    phase_after: str
    version_before: int
    version_after: int

    def canonical_line(self) -> str:
        return "|".join(
            (
                str(self.sequence),
                self.command_id,
                self.item_id,
                self.event_type,
                self.operation,
                self.reason,
                self.phase_before,
                self.phase_after,
                str(self.version_before),
                str(self.version_after),
            )
        )


@dataclass(frozen=True)
class QueueRun:
    commands: Tuple[QueueCommand, ...]
    events: Tuple[QueueEvent, ...]
    final_records: Tuple[QueueRecord, ...]
    applied_command_ids: Tuple[str, ...]
    rejected_command_ids: Tuple[str, ...]
    run_digest: str

    def canonical_text(self) -> str:
        lines = [f"HOST={HOST_NAME}", f"VERSION={HOST_VERSION}"]
        lines.extend(f"COMMAND={item.canonical_line()}" for item in self.commands)
        lines.extend(f"EVENT={item.canonical_line()}" for item in self.events)
        lines.extend(f"RECORD={item.canonical_line()}" for item in self.final_records)
        lines.extend(
            (
                f"APPLIED={','.join(self.applied_command_ids)}",
                f"REJECTED={','.join(self.rejected_command_ids)}",
            )
        )
        return "\n".join(lines)


_TRANSITIONS = {
    ENQUEUE: {ABSENT: READY},
    CLAIM: {READY: ACTIVE},
    HEARTBEAT: {ACTIVE: ACTIVE},
    SUSPEND: {ACTIVE: HELD},
    CONTINUE: {HELD: ACTIVE},
    FINISH: {ACTIVE: COMPLETE},
    DROP: {READY: DROPPED, ACTIVE: DROPPED, HELD: DROPPED},
}


def _normalise_operation(value: object) -> str:
    return value.strip().upper() if isinstance(value, str) else ""


def _valid_text(value: object) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _command_error(command: object, duplicate_ids: set[str]) -> str:
    if not isinstance(command, QueueCommand):
        return "COMMAND_TYPE_INVALID"
    if not _valid_text(command.command_id):
        return "EMPTY_COMMAND_ID"
    if command.command_id in duplicate_ids:
        return "DUPLICATE_COMMAND_ID"
    if not _valid_text(command.item_id):
        return "EMPTY_ITEM_ID"
    if _normalise_operation(command.operation) not in SUPPORTED_OPERATIONS:
        return "UNSUPPORTED_OPERATION"
    if isinstance(command.expected_version, bool) or not isinstance(
        command.expected_version, int
    ):
        return "VERSION_NOT_INTEGER"
    if command.expected_version < 0:
        return "NEGATIVE_VERSION"
    return ""


def _event(
    sequence: int,
    command: QueueCommand,
    *,
    event_type: str,
    reason: str,
    phase_before: str,
    phase_after: str,
    version_before: int,
    version_after: int,
) -> QueueEvent:
    return QueueEvent(
        sequence=sequence,
        command_id=command.command_id if _valid_text(command.command_id) else "<EMPTY>",
        item_id=command.item_id if _valid_text(command.item_id) else "<EMPTY>",
        event_type=event_type,
        operation=_normalise_operation(command.operation),
        reason=reason,
        phase_before=phase_before,
        phase_after=phase_after,
        version_before=version_before,
        version_after=version_after,
    )


def _digest_run(
    commands: Sequence[QueueCommand],
    events: Sequence[QueueEvent],
    records: Sequence[QueueRecord],
    applied: Sequence[str],
    rejected: Sequence[str],
) -> str:
    provisional = QueueRun(
        commands=tuple(commands),
        events=tuple(events),
        final_records=tuple(records),
        applied_command_ids=tuple(applied),
        rejected_command_ids=tuple(rejected),
        run_digest="",
    )
    return hashlib.sha256(provisional.canonical_text().encode("utf-8")).hexdigest()


def run_queue(commands: Iterable[QueueCommand]) -> QueueRun:
    """Run a queue command batch in input order and return an exact ledger."""

    command_tuple = tuple(commands)
    id_counts: dict[str, int] = {}
    for command in command_tuple:
        if isinstance(command, QueueCommand) and _valid_text(command.command_id):
            id_counts[command.command_id] = id_counts.get(command.command_id, 0) + 1
    duplicate_ids = {item for item, count in id_counts.items() if count > 1}

    records: dict[str, QueueRecord] = {}
    events: list[QueueEvent] = []
    applied: list[str] = []
    rejected: list[str] = []

    for sequence, command in enumerate(command_tuple, start=1):
        error = _command_error(command, duplicate_ids)
        if error:
            event_command = (
                command
                if isinstance(command, QueueCommand)
                else QueueCommand("<INVALID>", "<INVALID>", "", 0)
            )
            events.append(
                _event(
                    sequence,
                    event_command,
                    event_type=REJECTED,
                    reason=error,
                    phase_before=ABSENT,
                    phase_after=ABSENT,
                    version_before=0,
                    version_after=0,
                )
            )
            rejected.append(event_command.command_id)
            continue

        operation = _normalise_operation(command.operation)
        normalised = QueueCommand(
            command.command_id.strip(),
            command.item_id.strip(),
            operation,
            command.expected_version,
        )
        current = records.get(normalised.item_id)
        phase_before = current.phase if current is not None else ABSENT
        version_before = current.version if current is not None else 0

        if normalised.expected_version != version_before:
            events.append(
                _event(
                    sequence,
                    normalised,
                    event_type=REJECTED,
                    reason="VERSION_MISMATCH",
                    phase_before=phase_before,
                    phase_after=phase_before,
                    version_before=version_before,
                    version_after=version_before,
                )
            )
            rejected.append(normalised.command_id)
            continue

        next_phase = _TRANSITIONS[operation].get(phase_before)
        if next_phase is None:
            reason = "ITEM_ALREADY_EXISTS" if operation == ENQUEUE else "ILLEGAL_TRANSITION"
            if operation != ENQUEUE and current is None:
                reason = "ITEM_NOT_FOUND"
            events.append(
                _event(
                    sequence,
                    normalised,
                    event_type=REJECTED,
                    reason=reason,
                    phase_before=phase_before,
                    phase_after=phase_before,
                    version_before=version_before,
                    version_after=version_before,
                )
            )
            rejected.append(normalised.command_id)
            continue

        version_after = version_before + 1
        updated = QueueRecord(normalised.item_id, next_phase, version_after)
        records[normalised.item_id] = updated
        events.append(
            _event(
                sequence,
                normalised,
                event_type=APPLIED,
                reason=f"TRANSITION_{phase_before}_TO_{next_phase}",
                phase_before=phase_before,
                phase_after=next_phase,
                version_before=version_before,
                version_after=version_after,
            )
        )
        applied.append(normalised.command_id)

    final_records = tuple(records[key] for key in sorted(records))
    digest = _digest_run(command_tuple, events, final_records, applied, rejected)
    return QueueRun(
        commands=command_tuple,
        events=tuple(events),
        final_records=final_records,
        applied_command_ids=tuple(applied),
        rejected_command_ids=tuple(rejected),
        run_digest=digest,
    )


def baseline_commands() -> Tuple[QueueCommand, ...]:
    return (
        QueueCommand("QCMD-001", "TASK-7", ENQUEUE, 0),
        QueueCommand("QCMD-002", "TASK-7", CLAIM, 1),
        QueueCommand("QCMD-003", "TASK-7", HEARTBEAT, 2),
        QueueCommand("QCMD-004", "TASK-7", FINISH, 3),
    )


def main() -> int:
    run = run_queue(baseline_commands())
    print(f"Host: {HOST_NAME} {HOST_VERSION}")
    print(f"Commands: {len(run.commands)}")
    print(f"Events: {len(run.events)}")
    print(f"Applied: {len(run.applied_command_ids)}")
    print(f"Rejected: {len(run.rejected_command_ids)}")
    print(f"Final phase: {run.final_records[0].phase}")
    print(f"Run digest: {run.run_digest}")
    if (
        len(run.events) != 4
        or run.rejected_command_ids
        or run.final_records != (QueueRecord("TASK-7", COMPLETE, 4),)
    ):
        print("LEASE QUEUE HOST SELF-QUALIFICATION: FAIL")
        return 1
    print("LEASE QUEUE HOST SELF-QUALIFICATION: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
