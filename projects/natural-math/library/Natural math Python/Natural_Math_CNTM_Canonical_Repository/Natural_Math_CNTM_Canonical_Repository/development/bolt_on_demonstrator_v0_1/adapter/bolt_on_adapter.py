#!/usr/bin/env python3
"""Observation-only adapter for Bolt-On Demonstrator v0.1, Stage 2.

This adapter is intentionally powerless. It creates immutable copies of host
inputs, invokes the unchanged Stage 1 host, and records an independent hash-
chained observation ledger. It cannot modify host state, host source, frozen
Natural Math source, or frozen CNTM source.

Stage 2 contract
----------------
- Standard-library-only.
- No Natural Math or CNTM imports.
- No file writing.
- No intervention or decision authority.
- Host input objects are not mutated.
- Host result equals a direct unobserved run.
- Observation receipts are deterministic and replay-verifiable.
- Receipt tampering is detectable.
"""

from __future__ import annotations

import hashlib
import importlib.util
from dataclasses import dataclass, replace
from pathlib import Path
import sys
from typing import Iterable, Sequence, Tuple

ADAPTER_NAME = "BOLT-ON OBSERVATION-ONLY ADAPTER"
ADAPTER_VERSION = "0.2"

THIS_FILE = Path(__file__).resolve()
PROJECT_DIR = THIS_FILE.parents[1]
HOST_PATH = PROJECT_DIR / "host" / "ordinary_host.py"


def _load_host_module():
    module_name = "bolt_on_stage1_ordinary_host"
    existing = sys.modules.get(module_name)
    if existing is not None:
        return existing
    spec = importlib.util.spec_from_file_location(module_name, HOST_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"could not load host module from {HOST_PATH}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


ordinary_host = _load_host_module()


@dataclass(frozen=True)
class ObservedJob:
    ordinal: int
    job_id: str
    operation: str
    value_text: str
    value_type: str
    requires: Tuple[str, ...]

    def canonical_line(self) -> str:
        return "|".join(
            (
                str(self.ordinal),
                self.job_id,
                self.operation,
                self.value_type,
                self.value_text,
                ",".join(self.requires),
            )
        )


@dataclass(frozen=True)
class ObservationReceipt:
    receipt_id: int
    kind: str
    subject: str
    payload: str
    prior_hash: str
    receipt_hash: str

    def unsigned_line(self) -> str:
        return "|".join(
            (
                str(self.receipt_id),
                self.kind,
                self.subject,
                self.payload,
                self.prior_hash,
            )
        )


@dataclass(frozen=True)
class ReplayResult:
    passed: bool
    final_digest: str
    checked_receipts: int
    first_error: str


@dataclass(frozen=True)
class ObservationReport:
    input_snapshot: Tuple[ObservedJob, ...]
    input_digest: str
    host_run: object
    receipts: Tuple[ObservationReceipt, ...]
    observer_digest: str
    replay: ReplayResult


@dataclass(frozen=True)
class EquivalenceQualification:
    passed: bool
    direct_digest: str
    observed_digest: str
    direct_text: str
    observed_text: str
    host_source_before: str
    host_source_after: str
    input_unchanged: bool
    replay_pass: bool
    observer_digest: str
    receipt_count: int


def _text_value(value: object) -> str:
    if isinstance(value, str):
        return value
    if isinstance(value, bool):
        return "True" if value else "False"
    if isinstance(value, int):
        return str(value)
    return repr(value)


def snapshot_jobs(jobs: Iterable[object]) -> Tuple[ObservedJob, ...]:
    """Copy relevant host job fields into an immutable observation snapshot."""

    snapshots = []
    for ordinal, job in enumerate(tuple(jobs), start=1):
        job_id = getattr(job, "job_id", "")
        operation = getattr(job, "operation", "")
        value = getattr(job, "value", None)
        requires = getattr(job, "requires", ())
        safe_requires = tuple(requires) if isinstance(requires, tuple) else (repr(requires),)
        snapshots.append(
            ObservedJob(
                ordinal=ordinal,
                job_id=job_id if isinstance(job_id, str) else repr(job_id),
                operation=operation if isinstance(operation, str) else repr(operation),
                value_text=_text_value(value),
                value_type=type(value).__name__,
                requires=safe_requires,
            )
        )
    return tuple(snapshots)


def snapshot_digest(snapshot: Sequence[ObservedJob]) -> str:
    payload = "\n".join(item.canonical_line() for item in snapshot)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _copy_jobs_for_host(jobs: Sequence[object]) -> Tuple[object, ...]:
    """Construct fresh host Job objects so caller-owned objects are never passed in."""

    copied = []
    for job in jobs:
        copied.append(
            ordinary_host.Job(
                getattr(job, "job_id", ""),
                getattr(job, "operation", ""),
                getattr(job, "value", None),
                getattr(job, "requires", ()),
            )
        )
    return tuple(copied)


def _receipt_hash(
    receipt_id: int,
    kind: str,
    subject: str,
    payload: str,
    prior_hash: str,
) -> str:
    unsigned = "|".join(
        (str(receipt_id), kind, subject, payload, prior_hash)
    )
    return hashlib.sha256(unsigned.encode("utf-8")).hexdigest()


def build_receipts(
    snapshot: Sequence[ObservedJob],
    input_digest: str,
    host_run: object,
) -> Tuple[ObservationReceipt, ...]:
    receipts = []
    prior_hash = "0" * 64

    def append(kind: str, subject: str, payload: str) -> None:
        nonlocal prior_hash
        receipt_id = len(receipts) + 1
        digest = _receipt_hash(
            receipt_id,
            kind,
            subject,
            payload,
            prior_hash,
        )
        receipts.append(
            ObservationReceipt(
                receipt_id=receipt_id,
                kind=kind,
                subject=subject,
                payload=payload,
                prior_hash=prior_hash,
                receipt_hash=digest,
            )
        )
        prior_hash = digest

    append(
        "SESSION",
        "OPEN",
        f"adapter={ADAPTER_NAME};version={ADAPTER_VERSION};input_digest={input_digest}",
    )

    for item in snapshot:
        append("INPUT", f"JOB:{item.ordinal}", item.canonical_line())

    for event in host_run.events:
        append("OUTPUT", f"EVENT:{event.sequence}", event.canonical_line())

    append(
        "SUMMARY",
        "HOST_RUN",
        ";".join(
            (
                f"host_digest={host_run.run_digest}",
                f"final={host_run.final_value}",
                f"completed={','.join(host_run.completed_ids)}",
                f"rejected={','.join(host_run.rejected_ids)}",
                f"delayed={','.join(host_run.delayed_ids)}",
            )
        ),
    )
    return tuple(receipts)


def replay_observation_receipts(
    receipts: Sequence[ObservationReceipt],
) -> ReplayResult:
    prior_hash = "0" * 64
    for expected_id, receipt in enumerate(receipts, start=1):
        if receipt.receipt_id != expected_id:
            return ReplayResult(
                False,
                prior_hash,
                expected_id - 1,
                f"RECEIPT_ID_MISMATCH:{expected_id}:{receipt.receipt_id}",
            )
        if receipt.prior_hash != prior_hash:
            return ReplayResult(
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
            return ReplayResult(
                False,
                prior_hash,
                expected_id - 1,
                f"RECEIPT_HASH_MISMATCH:{expected_id}",
            )
        prior_hash = expected_hash

    return ReplayResult(True, prior_hash, len(receipts), "NONE")


def observe_jobs(jobs: Iterable[object], starting_value: int = 0) -> ObservationReport:
    original_jobs = tuple(jobs)
    snapshot = snapshot_jobs(original_jobs)
    input_digest = snapshot_digest(snapshot)
    copied_jobs = _copy_jobs_for_host(original_jobs)
    host_run = ordinary_host.run_jobs(copied_jobs, starting_value=starting_value)
    receipts = build_receipts(snapshot, input_digest, host_run)
    replay = replay_observation_receipts(receipts)
    observer_digest = receipts[-1].receipt_hash if receipts else "0" * 64
    return ObservationReport(
        input_snapshot=snapshot,
        input_digest=input_digest,
        host_run=host_run,
        receipts=receipts,
        observer_digest=observer_digest,
        replay=replay,
    )


def qualify_observation_equivalence(
    jobs: Iterable[object],
    starting_value: int = 0,
) -> EquivalenceQualification:
    original_jobs = tuple(jobs)
    input_before = repr(original_jobs)
    host_source_before = hashlib.sha256(HOST_PATH.read_bytes()).hexdigest()

    direct_run = ordinary_host.run_jobs(original_jobs, starting_value=starting_value)
    report = observe_jobs(original_jobs, starting_value=starting_value)

    host_source_after = hashlib.sha256(HOST_PATH.read_bytes()).hexdigest()
    input_after = repr(original_jobs)
    direct_text = direct_run.canonical_text()
    observed_text = report.host_run.canonical_text()
    passed = (
        direct_run == report.host_run
        and direct_run.run_digest == report.host_run.run_digest
        and direct_text == observed_text
        and host_source_before == host_source_after
        and input_before == input_after
        and report.replay.passed
        and report.observer_digest == report.replay.final_digest
    )
    return EquivalenceQualification(
        passed=passed,
        direct_digest=direct_run.run_digest,
        observed_digest=report.host_run.run_digest,
        direct_text=direct_text,
        observed_text=observed_text,
        host_source_before=host_source_before,
        host_source_after=host_source_after,
        input_unchanged=input_before == input_after,
        replay_pass=report.replay.passed,
        observer_digest=report.observer_digest,
        receipt_count=len(report.receipts),
    )


def tamper_receipt(
    receipts: Sequence[ObservationReceipt],
    index: int,
    replacement_payload: str,
) -> Tuple[ObservationReceipt, ...]:
    """Test helper: alter payload without recomputing its receipt hash."""

    if not 0 <= index < len(receipts):
        raise IndexError("receipt index out of range")
    altered = list(receipts)
    altered[index] = replace(altered[index], payload=replacement_payload)
    return tuple(altered)


def print_qualification(qualification: EquivalenceQualification) -> None:
    print("=" * 88)
    print(f"{ADAPTER_NAME} v{ADAPTER_VERSION}")
    print("=" * 88)
    print(f"Host output equivalent:       {qualification.direct_text == qualification.observed_text}")
    print(f"Host digest equivalent:       {qualification.direct_digest == qualification.observed_digest}")
    print(f"Host source unchanged:        {qualification.host_source_before == qualification.host_source_after}")
    print(f"Input objects unchanged:      {qualification.input_unchanged}")
    print(f"Observation replay pass:      {qualification.replay_pass}")
    print(f"Observation receipt count:    {qualification.receipt_count}")
    print(f"Direct host digest:           {qualification.direct_digest}")
    print(f"Observed host digest:         {qualification.observed_digest}")
    print(f"Observer digest:              {qualification.observer_digest}")
    print(f"STAGE 2 EQUIVALENCE:          {'PASS' if qualification.passed else 'FAIL'}")


def main() -> None:
    qualification = qualify_observation_equivalence(
        ordinary_host.baseline_jobs(),
        starting_value=0,
    )
    print_qualification(qualification)


if __name__ == "__main__":
    main()
