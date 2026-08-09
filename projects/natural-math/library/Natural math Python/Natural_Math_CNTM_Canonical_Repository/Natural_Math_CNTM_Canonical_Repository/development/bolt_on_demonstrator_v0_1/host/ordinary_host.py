#!/usr/bin/env python3
"""Ordinary deterministic host for Bolt-On Demonstrator v0.1, Stage 1.

This program is intentionally independent of Natural Math and CNTM. It provides
a stable host behavior contract that later observation, governance, and memory
layers must preserve unless an explicit intervention is authorized.

Contract
--------
- Standard-library-only.
- Integer state only.
- Deterministic processing order.
- No file output.
- No Natural Math or CNTM imports.
- Exact event ledger and SHA-256 run digest.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from typing import Iterable, Sequence, Tuple

HOST_NAME = "ORDINARY DETERMINISTIC JOB HOST"
HOST_VERSION = "0.1"

SUPPORTED_OPERATIONS: Tuple[str, ...] = (
    "SET",
    "ADD",
    "SUBTRACT",
    "MULTIPLY",
)


@dataclass(frozen=True)
class Job:
    """A plain host job.

    requires contains job IDs that must complete before this job can execute.
    """

    job_id: str
    operation: str
    value: int
    requires: Tuple[str, ...] = ()


@dataclass(frozen=True)
class Event:
    sequence: int
    job_id: str
    event: str
    reason: str
    before: int
    after: int
    round_number: int

    def canonical_line(self) -> str:
        return "|".join(
            (
                str(self.sequence),
                self.job_id,
                self.event,
                self.reason,
                str(self.before),
                str(self.after),
                str(self.round_number),
            )
        )


@dataclass(frozen=True)
class HostRun:
    starting_value: int
    final_value: int
    events: Tuple[Event, ...]
    completed_ids: Tuple[str, ...]
    rejected_ids: Tuple[str, ...]
    delayed_ids: Tuple[str, ...]
    run_digest: str

    def canonical_text(self) -> str:
        lines = [
            f"HOST={HOST_NAME}",
            f"VERSION={HOST_VERSION}",
            f"START={self.starting_value}",
        ]
        lines.extend(event.canonical_line() for event in self.events)
        lines.extend(
            (
                f"COMPLETED={','.join(self.completed_ids)}",
                f"REJECTED={','.join(self.rejected_ids)}",
                f"DELAYED={','.join(self.delayed_ids)}",
                f"FINAL={self.final_value}",
            )
        )
        return "\n".join(lines)


def _normalise_operation(operation: object) -> str:
    return operation.strip().upper() if isinstance(operation, str) else ""


def _validate_job(job: Job, duplicate_ids: set[str]) -> str:
    if not isinstance(job.job_id, str) or not job.job_id.strip():
        return "EMPTY_JOB_ID"
    if job.job_id in duplicate_ids:
        return "DUPLICATE_JOB_ID"
    if _normalise_operation(job.operation) not in SUPPORTED_OPERATIONS:
        return "UNSUPPORTED_OPERATION"
    if isinstance(job.value, bool) or not isinstance(job.value, int):
        return "VALUE_NOT_INTEGER"
    if not isinstance(job.requires, tuple):
        return "REQUIRES_NOT_TUPLE"
    if any(not isinstance(item, str) or not item for item in job.requires):
        return "INVALID_REQUIREMENT_ID"
    if len(set(job.requires)) != len(job.requires):
        return "DUPLICATE_REQUIREMENT_ID"
    if job.job_id in job.requires:
        return "SELF_DEPENDENCY"
    return ""


def _apply(operation: str, current: int, value: int) -> int:
    if operation == "SET":
        return value
    if operation == "ADD":
        return current + value
    if operation == "SUBTRACT":
        return current - value
    if operation == "MULTIPLY":
        return current * value
    raise ValueError(f"unsupported operation: {operation}")


def _digest_for(
    starting_value: int,
    final_value: int,
    events: Sequence[Event],
    completed_ids: Sequence[str],
    rejected_ids: Sequence[str],
    delayed_ids: Sequence[str],
) -> str:
    lines = [
        f"HOST={HOST_NAME}",
        f"VERSION={HOST_VERSION}",
        f"START={starting_value}",
    ]
    lines.extend(event.canonical_line() for event in events)
    lines.extend(
        (
            f"COMPLETED={','.join(completed_ids)}",
            f"REJECTED={','.join(rejected_ids)}",
            f"DELAYED={','.join(delayed_ids)}",
            f"FINAL={final_value}",
        )
    )
    return hashlib.sha256("\n".join(lines).encode("utf-8")).hexdigest()


def run_jobs(jobs: Iterable[Job], starting_value: int = 0) -> HostRun:
    """Run jobs deterministically and return an immutable exact ledger."""

    if isinstance(starting_value, bool) or not isinstance(starting_value, int):
        raise TypeError("starting_value must be an integer")

    job_list = tuple(jobs)
    id_counts: dict[str, int] = {}
    for job in job_list:
        if isinstance(job.job_id, str) and job.job_id:
            id_counts[job.job_id] = id_counts.get(job.job_id, 0) + 1
    duplicate_ids = {job_id for job_id, count in id_counts.items() if count > 1}

    events: list[Event] = []
    pending: list[Job] = []
    completed: list[str] = []
    rejected: list[str] = []
    delayed: list[str] = []
    current = starting_value
    sequence = 1

    for job in job_list:
        reason = _validate_job(job, duplicate_ids)
        display_id = job.job_id if isinstance(job.job_id, str) and job.job_id else "<EMPTY>"
        if reason:
            events.append(
                Event(
                    sequence=sequence,
                    job_id=display_id,
                    event="REJECTED",
                    reason=reason,
                    before=current,
                    after=current,
                    round_number=0,
                )
            )
            rejected.append(display_id)
            sequence += 1
            continue

        operation = _normalise_operation(job.operation)
        normalised = Job(job.job_id, operation, job.value, job.requires)
        pending.append(normalised)
        events.append(
            Event(
                sequence=sequence,
                job_id=job.job_id,
                event="ACCEPTED",
                reason="VALID_JOB",
                before=current,
                after=current,
                round_number=0,
            )
        )
        sequence += 1

    completed_set: set[str] = set()
    round_number = 1

    while pending:
        progress = False
        next_pending: list[Job] = []

        for job in pending:
            missing = tuple(
                requirement
                for requirement in job.requires
                if requirement not in completed_set
            )
            if missing:
                next_pending.append(job)
                continue

            before = current
            current = _apply(job.operation, current, job.value)
            completed.append(job.job_id)
            completed_set.add(job.job_id)
            events.append(
                Event(
                    sequence=sequence,
                    job_id=job.job_id,
                    event="COMPLETED",
                    reason=f"APPLIED_{job.operation}",
                    before=before,
                    after=current,
                    round_number=round_number,
                )
            )
            sequence += 1
            progress = True

        if not progress:
            for job in next_pending:
                missing = tuple(
                    requirement
                    for requirement in job.requires
                    if requirement not in completed_set
                )
                events.append(
                    Event(
                        sequence=sequence,
                        job_id=job.job_id,
                        event="DELAYED",
                        reason="UNMET:" + ",".join(missing),
                        before=current,
                        after=current,
                        round_number=round_number,
                    )
                )
                delayed.append(job.job_id)
                sequence += 1
            break

        pending = next_pending
        round_number += 1

    event_tuple = tuple(events)
    completed_tuple = tuple(completed)
    rejected_tuple = tuple(rejected)
    delayed_tuple = tuple(delayed)
    digest = _digest_for(
        starting_value,
        current,
        event_tuple,
        completed_tuple,
        rejected_tuple,
        delayed_tuple,
    )
    return HostRun(
        starting_value=starting_value,
        final_value=current,
        events=event_tuple,
        completed_ids=completed_tuple,
        rejected_ids=rejected_tuple,
        delayed_ids=delayed_tuple,
        run_digest=digest,
    )


def baseline_jobs() -> Tuple[Job, ...]:
    """Fixed Stage 1 qualification fixture."""

    return (
        Job("J001", "SET", 10),
        Job("J002", "ADD", 5, ("J001",)),
        Job("J003", "MULTIPLY", 3, ("J002",)),
        Job("J004", "SUBTRACT", 4, ("J003",)),
        Job("J005", "ADD", 7, ("J999",)),
        Job("J006", "DIVIDE", 2),
        Job("", "ADD", 1),
        Job("J007", "ADD", 2, ("J004",)),
    )


def print_run(run: HostRun) -> None:
    print("=" * 88)
    print(f"{HOST_NAME} v{HOST_VERSION}")
    print("=" * 88)
    print(f"Starting value: {run.starting_value}")
    print()
    print("SEQ | JOB     | EVENT     | REASON                 | BEFORE | AFTER | ROUND")
    print("-" * 88)
    for event in run.events:
        print(
            f"{event.sequence:>3} | "
            f"{event.job_id:<7} | "
            f"{event.event:<9} | "
            f"{event.reason:<22} | "
            f"{event.before:>6} | "
            f"{event.after:>5} | "
            f"{event.round_number:>5}"
        )
    print("-" * 88)
    print(f"Completed: {run.completed_ids}")
    print(f"Rejected:  {run.rejected_ids}")
    print(f"Delayed:   {run.delayed_ids}")
    print(f"Final value: {run.final_value}")
    print(f"Run digest: {run.run_digest}")


def main() -> None:
    print_run(run_jobs(baseline_jobs(), starting_value=0))


if __name__ == "__main__":
    main()
