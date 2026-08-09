#!/usr/bin/env python3
"""Independent deterministic workflow host for Bolt-On Demonstrator v0.3.

This host is deliberately independent of the bolt-on.  It implements a finite,
versioned task-state machine with immutable commands, immutable events, exact
integer revisions, deterministic processing order, and an exact SHA-256 run
receipt.  It imports no Natural Math, CNTM, adapter, governance, or bolt-on
module and can be executed and qualified by itself.

The host-native operations are ordinary workflow operations:

REGISTER  ABSENT -> READY
START     READY -> RUNNING
CHECKPOINT RUNNING -> RUNNING
PAUSE     RUNNING -> PAUSED
RESUME    PAUSED -> RUNNING
COMPLETE  RUNNING -> DONE
CANCEL    READY/RUNNING/PAUSED -> CANCELLED

No file output is performed.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from typing import Iterable, Sequence, Tuple

HOST_NAME = "DETERMINISTIC VERSIONED WORKFLOW HOST"
HOST_VERSION = "1.0"

ABSENT = "ABSENT"
READY = "READY"
RUNNING = "RUNNING"
PAUSED = "PAUSED"
DONE = "DONE"
CANCELLED = "CANCELLED"

REGISTER = "REGISTER"
START = "START"
CHECKPOINT = "CHECKPOINT"
PAUSE = "PAUSE"
RESUME = "RESUME"
COMPLETE = "COMPLETE"
CANCEL = "CANCEL"
SUPPORTED_OPERATIONS: Tuple[str, ...] = (
    REGISTER,
    START,
    CHECKPOINT,
    PAUSE,
    RESUME,
    COMPLETE,
    CANCEL,
)

APPLIED = "APPLIED"
REJECTED = "REJECTED"


@dataclass(frozen=True)
class WorkflowCommand:
    command_id: str
    task_id: str
    operation: str
    expected_revision: int

    def canonical_line(self) -> str:
        return "|".join(
            (
                self.command_id,
                self.task_id,
                self.operation,
                str(self.expected_revision),
            )
        )


@dataclass(frozen=True)
class WorkflowRecord:
    task_id: str
    state: str
    revision: int

    def canonical_line(self) -> str:
        return "|".join((self.task_id, self.state, str(self.revision)))


@dataclass(frozen=True)
class WorkflowEvent:
    sequence: int
    command_id: str
    task_id: str
    event_type: str
    operation: str
    reason: str
    state_before: str
    state_after: str
    revision_before: int
    revision_after: int

    def canonical_line(self) -> str:
        return "|".join(
            (
                str(self.sequence),
                self.command_id,
                self.task_id,
                self.event_type,
                self.operation,
                self.reason,
                self.state_before,
                self.state_after,
                str(self.revision_before),
                str(self.revision_after),
            )
        )


@dataclass(frozen=True)
class WorkflowRun:
    commands: Tuple[WorkflowCommand, ...]
    events: Tuple[WorkflowEvent, ...]
    final_records: Tuple[WorkflowRecord, ...]
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
    REGISTER: {ABSENT: READY},
    START: {READY: RUNNING},
    CHECKPOINT: {RUNNING: RUNNING},
    PAUSE: {RUNNING: PAUSED},
    RESUME: {PAUSED: RUNNING},
    COMPLETE: {RUNNING: DONE},
    CANCEL: {READY: CANCELLED, RUNNING: CANCELLED, PAUSED: CANCELLED},
}


def _normalise_operation(value: object) -> str:
    return value.strip().upper() if isinstance(value, str) else ""


def _valid_text(value: object) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _command_error(command: object, duplicate_ids: set[str]) -> str:
    if not isinstance(command, WorkflowCommand):
        return "COMMAND_TYPE_INVALID"
    if not _valid_text(command.command_id):
        return "EMPTY_COMMAND_ID"
    if command.command_id in duplicate_ids:
        return "DUPLICATE_COMMAND_ID"
    if not _valid_text(command.task_id):
        return "EMPTY_TASK_ID"
    if _normalise_operation(command.operation) not in SUPPORTED_OPERATIONS:
        return "UNSUPPORTED_OPERATION"
    if isinstance(command.expected_revision, bool) or not isinstance(
        command.expected_revision, int
    ):
        return "REVISION_NOT_INTEGER"
    if command.expected_revision < 0:
        return "NEGATIVE_REVISION"
    return ""


def _event(
    sequence: int,
    command: WorkflowCommand,
    *,
    event_type: str,
    reason: str,
    state_before: str,
    state_after: str,
    revision_before: int,
    revision_after: int,
) -> WorkflowEvent:
    return WorkflowEvent(
        sequence=sequence,
        command_id=command.command_id if _valid_text(command.command_id) else "<EMPTY>",
        task_id=command.task_id if _valid_text(command.task_id) else "<EMPTY>",
        event_type=event_type,
        operation=_normalise_operation(command.operation),
        reason=reason,
        state_before=state_before,
        state_after=state_after,
        revision_before=revision_before,
        revision_after=revision_after,
    )


def _digest_run(
    commands: Sequence[WorkflowCommand],
    events: Sequence[WorkflowEvent],
    records: Sequence[WorkflowRecord],
    applied: Sequence[str],
    rejected: Sequence[str],
) -> str:
    provisional = WorkflowRun(
        commands=tuple(commands),
        events=tuple(events),
        final_records=tuple(records),
        applied_command_ids=tuple(applied),
        rejected_command_ids=tuple(rejected),
        run_digest="",
    )
    return hashlib.sha256(provisional.canonical_text().encode("utf-8")).hexdigest()


def run_workflow(commands: Iterable[WorkflowCommand]) -> WorkflowRun:
    """Run a command batch in input order and return an immutable exact ledger."""

    command_tuple = tuple(commands)
    id_counts: dict[str, int] = {}
    for command in command_tuple:
        if isinstance(command, WorkflowCommand) and _valid_text(command.command_id):
            id_counts[command.command_id] = id_counts.get(command.command_id, 0) + 1
    duplicate_ids = {item for item, count in id_counts.items() if count > 1}

    records: dict[str, WorkflowRecord] = {}
    events: list[WorkflowEvent] = []
    applied: list[str] = []
    rejected: list[str] = []

    for sequence, command in enumerate(command_tuple, start=1):
        error = _command_error(command, duplicate_ids)
        if error:
            if isinstance(command, WorkflowCommand):
                event_command = command
            else:
                event_command = WorkflowCommand("<INVALID>", "<INVALID>", "", 0)
            events.append(
                _event(
                    sequence,
                    event_command,
                    event_type=REJECTED,
                    reason=error,
                    state_before=ABSENT,
                    state_after=ABSENT,
                    revision_before=0,
                    revision_after=0,
                )
            )
            rejected.append(event_command.command_id)
            continue

        operation = _normalise_operation(command.operation)
        normalised = WorkflowCommand(
            command.command_id.strip(),
            command.task_id.strip(),
            operation,
            command.expected_revision,
        )
        current = records.get(normalised.task_id)
        state_before = current.state if current is not None else ABSENT
        revision_before = current.revision if current is not None else 0

        if normalised.expected_revision != revision_before:
            events.append(
                _event(
                    sequence,
                    normalised,
                    event_type=REJECTED,
                    reason="REVISION_MISMATCH",
                    state_before=state_before,
                    state_after=state_before,
                    revision_before=revision_before,
                    revision_after=revision_before,
                )
            )
            rejected.append(normalised.command_id)
            continue

        next_state = _TRANSITIONS[operation].get(state_before)
        if next_state is None:
            reason = "RECORD_ALREADY_EXISTS" if operation == REGISTER else "ILLEGAL_TRANSITION"
            if operation != REGISTER and current is None:
                reason = "RECORD_NOT_FOUND"
            events.append(
                _event(
                    sequence,
                    normalised,
                    event_type=REJECTED,
                    reason=reason,
                    state_before=state_before,
                    state_after=state_before,
                    revision_before=revision_before,
                    revision_after=revision_before,
                )
            )
            rejected.append(normalised.command_id)
            continue

        revision_after = revision_before + 1
        updated = WorkflowRecord(normalised.task_id, next_state, revision_after)
        records[normalised.task_id] = updated
        events.append(
            _event(
                sequence,
                normalised,
                event_type=APPLIED,
                reason=f"TRANSITION_{state_before}_TO_{next_state}",
                state_before=state_before,
                state_after=next_state,
                revision_before=revision_before,
                revision_after=revision_after,
            )
        )
        applied.append(normalised.command_id)

    final_records = tuple(records[key] for key in sorted(records))
    digest = _digest_run(command_tuple, events, final_records, applied, rejected)
    return WorkflowRun(
        commands=command_tuple,
        events=tuple(events),
        final_records=final_records,
        applied_command_ids=tuple(applied),
        rejected_command_ids=tuple(rejected),
        run_digest=digest,
    )


def baseline_commands() -> Tuple[WorkflowCommand, ...]:
    return (
        WorkflowCommand("CMD-001", "TASK-7", REGISTER, 0),
        WorkflowCommand("CMD-002", "TASK-7", START, 1),
        WorkflowCommand("CMD-003", "TASK-7", CHECKPOINT, 2),
        WorkflowCommand("CMD-004", "TASK-7", COMPLETE, 3),
    )


def main() -> int:
    run = run_workflow(baseline_commands())
    print(f"Host: {HOST_NAME} {HOST_VERSION}")
    print(f"Commands: {len(run.commands)}")
    print(f"Events: {len(run.events)}")
    print(f"Applied: {len(run.applied_command_ids)}")
    print(f"Rejected: {len(run.rejected_command_ids)}")
    print(f"Final state: {run.final_records[0].state}")
    print(f"Run digest: {run.run_digest}")
    if (
        len(run.events) != 4
        or run.rejected_command_ids
        or run.final_records != (WorkflowRecord("TASK-7", DONE, 4),)
    ):
        print("SECOND INDEPENDENT HOST SELF-QUALIFICATION: FAIL")
        return 1
    print("SECOND INDEPENDENT HOST SELF-QUALIFICATION: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
