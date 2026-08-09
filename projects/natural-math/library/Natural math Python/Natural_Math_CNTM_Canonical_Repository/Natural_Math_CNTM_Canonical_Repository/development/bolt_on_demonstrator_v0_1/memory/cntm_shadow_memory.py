#!/usr/bin/env python3
"""CNTM bounded shadow-memory interface for Bolt-On Demonstrator v0.1.

Stage 4 adds a finite, exact, replayable memory layer beside the unchanged
Stage 1 host, Stage 2 observer, and Stage 3 Natural Math shadow governance.
The memory layer has no authority to alter jobs, host state, observations, or
governance decisions.

Contract
--------
- Shadow mode only; intervention authority is NONE.
- Signed integer and ternary (-1, 0, +1) state only.
- Exact hash-chained records and deterministic replay.
- Finite capacity with atomic rejection on overflow.
- Duplicate sessions are rejected without mutation.
- Contradictory evidence is preserved, not reconciled.
- UNKNOWN remains UNKNOWN and is never forced into a binary answer.
- No file writing and no import or execution of frozen CNTM source.
- Frozen CNTM v3.0F is read only as a SHA-256 identity oracle.
"""

from __future__ import annotations

import hashlib
import importlib.util
from dataclasses import dataclass
from pathlib import Path
from types import SimpleNamespace
import sys
from typing import Iterable, Sequence, Tuple

MEMORY_NAME = "CNTM BOUNDED SHADOW MEMORY INTERFACE"
MEMORY_VERSION = "0.4"
MODE = "SHADOW"
AUTHORITY = "NONE"
DEFAULT_CAPACITY = 64
ZERO_HASH = "0" * 64

THIS_FILE = Path(__file__).resolve()
PROJECT_DIR = THIS_FILE.parents[1]
REPOSITORY_ROOT = THIS_FILE.parents[3]
GOVERNANCE_PATH = PROJECT_DIR / "governance" / "natural_math_shadow_governance.py"
HOST_PATH = PROJECT_DIR / "host" / "ordinary_host.py"
ADAPTER_PATH = PROJECT_DIR / "adapter" / "bolt_on_adapter.py"
CNTM_V3_0F_PATH = (
    REPOSITORY_ROOT
    / "frozen"
    / "cntm"
    / "v3.0F"
    / "cntm_domain_application_v3_0f.py"
)


def _load_governance_module():
    module_name = "bolt_on_stage3_shadow_governance"
    existing = sys.modules.get(module_name)
    if existing is not None:
        return existing
    spec = importlib.util.spec_from_file_location(module_name, GOVERNANCE_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"could not load shadow governance from {GOVERNANCE_PATH}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


governance = _load_governance_module()
adapter = governance.adapter
ordinary_host = governance.ordinary_host


@dataclass(frozen=True)
class MemoryRecord:
    record_id: int
    session_id: str
    kind: str
    subject: str
    ternary: int
    payload: str
    prior_hash: str
    record_hash: str

    def unsigned_line(self) -> str:
        return "|".join(
            (
                str(self.record_id),
                self.session_id,
                self.kind,
                self.subject,
                str(self.ternary),
                self.payload,
                self.prior_hash,
            )
        )


@dataclass(frozen=True)
class MemoryImage:
    capacity: int
    records: Tuple[MemoryRecord, ...]
    session_ids: Tuple[str, ...]
    final_digest: str


@dataclass(frozen=True)
class MemoryWriteResult:
    accepted: bool
    reason_code: str
    session_id: str
    records_written: int
    final_digest: str


@dataclass(frozen=True)
class MemoryReplay:
    passed: bool
    final_digest: str
    checked_records: int
    first_error: str
    session_count: int


@dataclass(frozen=True)
class CNTMShadowMemoryReport:
    governance_report: object
    memory_image: MemoryImage
    write_result: MemoryWriteResult
    replay: MemoryReplay
    cntm_v3_0f_hash: str
    intervention_attempts: int


@dataclass(frozen=True)
class Stage4Qualification:
    passed: bool
    host_output_equivalent: bool
    host_digest_equivalent: bool
    host_source_unchanged: bool
    adapter_source_unchanged: bool
    governance_source_unchanged: bool
    frozen_cntm_unchanged: bool
    input_unchanged: bool
    observation_replay_pass: bool
    governance_replay_pass: bool
    memory_replay_pass: bool
    bounded_write_pass: bool
    duplicate_session_rejected: bool
    contradiction_preserved: bool
    unknown_not_forced: bool
    damage_detected: bool
    intervention_attempts: int
    record_count: int
    session_count: int
    host_digest: str
    observer_digest: str
    governance_digest: str
    memory_digest: str
    cntm_v3_0f_hash: str


def _sha256_file(path: Path) -> str:
    if not path.is_file():
        raise FileNotFoundError(f"required source is missing: {path}")
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _record_hash(
    record_id: int,
    session_id: str,
    kind: str,
    subject: str,
    ternary: int,
    payload: str,
    prior_hash: str,
) -> str:
    unsigned = "|".join(
        (
            str(record_id),
            session_id,
            kind,
            subject,
            str(ternary),
            payload,
            prior_hash,
        )
    )
    return hashlib.sha256(unsigned.encode("utf-8")).hexdigest()


def session_identifier(report: object) -> str:
    payload = "|".join(
        (
            report.observation_report.host_run.run_digest,
            report.observation_report.observer_digest,
            report.governance_digest,
            report.natural_math_rc21_hash,
        )
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def encode_job_payload(decision: object, audit: object) -> str:
    evidence_digest = hashlib.sha256(
        (decision.canonical_line() + "\n" + audit.canonical_line()).encode("utf-8")
    ).hexdigest()
    return ";".join(
        (
            f"decision={decision.decision}",
            f"decision_reason={decision.reason_code}",
            f"expected={decision.expected_outcome}",
            f"observed={','.join(audit.observed_outcomes)}",
            f"audit_status={audit.status}",
            f"audit_reason={audit.reason_code}",
            f"evidence_digest={evidence_digest}",
        )
    )


def _record_specs(report: object, session_id: str) -> Tuple[Tuple[str, str, int, str], ...]:
    decisions = tuple(report.decisions)
    audits = tuple(report.audits)
    if len(decisions) != len(audits):
        raise ValueError("decision and audit counts differ")

    specs: list[Tuple[str, str, int, str]] = []
    specs.append(
        (
            "SESSION_OPEN",
            "SESSION",
            0,
            ";".join(
                (
                    f"memory={MEMORY_NAME}",
                    f"version={MEMORY_VERSION}",
                    f"mode={MODE}",
                    f"authority={AUTHORITY}",
                    f"host_digest={report.observation_report.host_run.run_digest}",
                    f"observer_digest={report.observation_report.observer_digest}",
                    f"governance_digest={report.governance_digest}",
                    f"rc21_hash={report.natural_math_rc21_hash}",
                )
            ),
        )
    )
    for decision, audit in zip(decisions, audits):
        ternary = int(decision.ternary)
        if ternary not in (-1, 0, 1):
            raise ValueError("memory ternary state must be -1, 0, or +1")
        specs.append(
            (
                "JOB_EVIDENCE",
                f"JOB:{decision.ordinal}:{decision.job_id}",
                ternary,
                encode_job_payload(decision, audit),
            )
        )

    counts = {name: 0 for name in (governance.PROCEED, governance.DEFER, governance.RESTRICT, governance.UNKNOWN)}
    for decision in decisions:
        counts[decision.decision] = counts.get(decision.decision, 0) + 1
    specs.append(
        (
            "SESSION_CLOSE",
            "SESSION",
            0,
            ";".join(
                (
                    f"proceed={counts[governance.PROCEED]}",
                    f"defer={counts[governance.DEFER]}",
                    f"restrict={counts[governance.RESTRICT]}",
                    f"unknown={counts[governance.UNKNOWN]}",
                    f"match={sum(1 for item in audits if item.status == 'MATCH')}",
                    f"audit_unknown={sum(1 for item in audits if item.status == governance.UNKNOWN)}",
                    f"intervention_attempts={report.intervention_attempts}",
                    f"session_id={session_id}",
                )
            ),
        )
    )
    return tuple(specs)


class BoundedCNTMShadowMemory:
    """Finite in-memory CNTM evidence store with atomic writes."""

    def __init__(self, capacity: int = DEFAULT_CAPACITY) -> None:
        if isinstance(capacity, bool) or not isinstance(capacity, int) or capacity <= 0:
            raise ValueError("capacity must be a positive integer")
        self.capacity = capacity
        self._records: list[MemoryRecord] = []
        self._session_ids: set[str] = set()

    def snapshot(self) -> MemoryImage:
        final_digest = self._records[-1].record_hash if self._records else ZERO_HASH
        return MemoryImage(
            capacity=self.capacity,
            records=tuple(self._records),
            session_ids=tuple(sorted(self._session_ids)),
            final_digest=final_digest,
        )

    def append_report(self, report: object) -> MemoryWriteResult:
        session_id = session_identifier(report)
        current = self.snapshot()
        if session_id in self._session_ids:
            return MemoryWriteResult(
                False,
                "DUPLICATE_SESSION",
                session_id,
                0,
                current.final_digest,
            )
        try:
            specs = _record_specs(report, session_id)
        except ValueError as error:
            return MemoryWriteResult(
                False,
                "INVALID_SESSION_EVIDENCE:" + str(error),
                session_id,
                0,
                current.final_digest,
            )
        if len(self._records) + len(specs) > self.capacity:
            return MemoryWriteResult(
                False,
                "MEMORY_CAPACITY_EXCEEDED",
                session_id,
                0,
                current.final_digest,
            )

        candidate: list[MemoryRecord] = []
        prior_hash = current.final_digest
        next_id = len(self._records) + 1
        for offset, (kind, subject, ternary, payload) in enumerate(specs):
            record_id = next_id + offset
            record_hash = _record_hash(
                record_id,
                session_id,
                kind,
                subject,
                ternary,
                payload,
                prior_hash,
            )
            candidate.append(
                MemoryRecord(
                    record_id,
                    session_id,
                    kind,
                    subject,
                    ternary,
                    payload,
                    prior_hash,
                    record_hash,
                )
            )
            prior_hash = record_hash

        # Commit only after the entire bounded session has been constructed.
        self._records.extend(candidate)
        self._session_ids.add(session_id)
        return MemoryWriteResult(
            True,
            "SESSION_STORED",
            session_id,
            len(candidate),
            prior_hash,
        )


def replay_memory(records: Sequence[MemoryRecord]) -> MemoryReplay:
    prior_hash = ZERO_HASH
    open_sessions: set[str] = set()
    closed_sessions: set[str] = set()
    for expected_id, record in enumerate(records, start=1):
        if record.record_id != expected_id:
            return MemoryReplay(
                False,
                prior_hash,
                expected_id - 1,
                f"RECORD_ID_MISMATCH:{expected_id}:{record.record_id}",
                len(closed_sessions),
            )
        if record.ternary not in (-1, 0, 1):
            return MemoryReplay(
                False,
                prior_hash,
                expected_id - 1,
                f"TERNARY_DOMAIN_VIOLATION:{expected_id}",
                len(closed_sessions),
            )
        if record.prior_hash != prior_hash:
            return MemoryReplay(
                False,
                prior_hash,
                expected_id - 1,
                f"PRIOR_HASH_MISMATCH:{expected_id}",
                len(closed_sessions),
            )
        expected_hash = _record_hash(
            record.record_id,
            record.session_id,
            record.kind,
            record.subject,
            record.ternary,
            record.payload,
            record.prior_hash,
        )
        if record.record_hash != expected_hash:
            return MemoryReplay(
                False,
                prior_hash,
                expected_id - 1,
                f"RECORD_HASH_MISMATCH:{expected_id}",
                len(closed_sessions),
            )
        if record.kind == "SESSION_OPEN":
            if record.session_id in open_sessions or record.session_id in closed_sessions:
                return MemoryReplay(
                    False,
                    prior_hash,
                    expected_id - 1,
                    f"DUPLICATE_SESSION_OPEN:{expected_id}",
                    len(closed_sessions),
                )
            open_sessions.add(record.session_id)
        elif record.kind == "SESSION_CLOSE":
            if record.session_id not in open_sessions:
                return MemoryReplay(
                    False,
                    prior_hash,
                    expected_id - 1,
                    f"SESSION_CLOSE_WITHOUT_OPEN:{expected_id}",
                    len(closed_sessions),
                )
            open_sessions.remove(record.session_id)
            closed_sessions.add(record.session_id)
        elif record.session_id not in open_sessions:
            return MemoryReplay(
                False,
                prior_hash,
                expected_id - 1,
                f"EVIDENCE_OUTSIDE_SESSION:{expected_id}",
                len(closed_sessions),
            )
        prior_hash = expected_hash

    if open_sessions:
        return MemoryReplay(
            False,
            prior_hash,
            len(records),
            "UNCLOSED_SESSION:" + ",".join(sorted(open_sessions)),
            len(closed_sessions),
        )
    return MemoryReplay(True, prior_hash, len(records), "NONE", len(closed_sessions))


def tamper_memory_record(
    records: Sequence[MemoryRecord],
    index: int,
    replacement_payload: str,
) -> Tuple[MemoryRecord, ...]:
    if not 0 <= index < len(records):
        raise IndexError("record index out of range")
    altered = list(records)
    old = altered[index]
    altered[index] = MemoryRecord(
        old.record_id,
        old.session_id,
        old.kind,
        old.subject,
        old.ternary,
        replacement_payload,
        old.prior_hash,
        old.record_hash,
    )
    return tuple(altered)


def assert_no_float(value: object, path: str = "root") -> None:
    if isinstance(value, float):
        raise AssertionError(f"floating-point value entered shadow memory at {path}")
    if isinstance(value, (str, bytes, int, bool, type(None), Path)):
        return
    if isinstance(value, dict):
        for key, item in value.items():
            assert_no_float(key, path + ".key")
            assert_no_float(item, path + f"[{key!r}]")
        return
    if isinstance(value, (tuple, list, set)):
        for index, item in enumerate(value):
            assert_no_float(item, path + f"[{index}]")
        return
    fields = getattr(value, "__dataclass_fields__", None)
    if fields:
        for name in fields:
            assert_no_float(getattr(value, name), path + "." + name)
        return
    if isinstance(value, BoundedCNTMShadowMemory):
        assert_no_float(value.snapshot(), path + ".snapshot")
        return
    raise AssertionError(f"unsupported object in shadow memory at {path}: {type(value).__name__}")


def run_shadow_memory(
    jobs: Iterable[object],
    starting_value: int = 0,
    capacity: int = DEFAULT_CAPACITY,
) -> CNTMShadowMemoryReport:
    original_jobs = tuple(jobs)
    governance_report = governance.run_shadow_governance(
        original_jobs,
        starting_value=starting_value,
    )
    memory = BoundedCNTMShadowMemory(capacity)
    write_result = memory.append_report(governance_report)
    image = memory.snapshot()
    replay = replay_memory(image.records)
    cntm_hash = _sha256_file(CNTM_V3_0F_PATH)
    report = CNTMShadowMemoryReport(
        governance_report=governance_report,
        memory_image=image,
        write_result=write_result,
        replay=replay,
        cntm_v3_0f_hash=cntm_hash,
        intervention_attempts=0,
    )
    assert_no_float(report, "shadow_memory_report")
    return report


def _synthetic_contradiction_report(base_report: object) -> object:
    decision = governance.GovernanceDecision(
        ordinal=1,
        job_id="CONTRADICTORY",
        decision=governance.UNKNOWN,
        ternary=0,
        reason_code="INSUFFICIENT_EVIDENCE",
        expected_outcome="NONE",
        evidence=(("source", "synthetic_qualification"),),
    )
    audit = governance.OutcomeAudit(
        ordinal=1,
        job_id="CONTRADICTORY",
        decision=governance.UNKNOWN,
        expected_outcome="NONE",
        observed_outcomes=("COMPLETED", "REJECTED"),
        status=governance.UNKNOWN,
        reason_code="CONTRADICTORY_TERMINAL_EVIDENCE",
    )
    synthetic_digest = hashlib.sha256(
        (base_report.governance_digest + decision.canonical_line() + audit.canonical_line()).encode("utf-8")
    ).hexdigest()
    return SimpleNamespace(
        observation_report=base_report.observation_report,
        decisions=(decision,),
        audits=(audit,),
        governance_digest=synthetic_digest,
        natural_math_rc21_hash=base_report.natural_math_rc21_hash,
        intervention_attempts=0,
    )


def qualify_shadow_memory(
    jobs: Iterable[object],
    starting_value: int = 0,
) -> Stage4Qualification:
    original_jobs = tuple(jobs)
    input_before = repr(original_jobs)
    paths = (HOST_PATH, ADAPTER_PATH, GOVERNANCE_PATH, CNTM_V3_0F_PATH)
    before_hashes = tuple(_sha256_file(path) for path in paths)

    direct = ordinary_host.run_jobs(original_jobs, starting_value=starting_value)
    report = run_shadow_memory(original_jobs, starting_value=starting_value)
    base_governance = report.governance_report

    # Duplicate writes must be rejected without changing memory.
    duplicate_memory = BoundedCNTMShadowMemory(DEFAULT_CAPACITY)
    first_write = duplicate_memory.append_report(base_governance)
    duplicate_before = duplicate_memory.snapshot()
    duplicate_write = duplicate_memory.append_report(base_governance)
    duplicate_after = duplicate_memory.snapshot()
    duplicate_rejected = (
        first_write.accepted
        and not duplicate_write.accepted
        and duplicate_write.reason_code == "DUPLICATE_SESSION"
        and duplicate_before == duplicate_after
    )

    # Capacity overflow must be atomic and preserve the empty image.
    required_records = len(base_governance.decisions) + 2
    bounded_memory = BoundedCNTMShadowMemory(required_records - 1)
    bounded_before = bounded_memory.snapshot()
    bounded_result = bounded_memory.append_report(base_governance)
    bounded_after = bounded_memory.snapshot()
    bounded_write_pass = (
        not bounded_result.accepted
        and bounded_result.reason_code == "MEMORY_CAPACITY_EXCEEDED"
        and bounded_before == bounded_after
    )

    # Preserve contradictory evidence and UNKNOWN in an actual memory image.
    contradiction_memory = BoundedCNTMShadowMemory(8)
    contradiction_write = contradiction_memory.append_report(
        _synthetic_contradiction_report(base_governance)
    )
    contradiction_image = contradiction_memory.snapshot()
    job_records = tuple(record for record in contradiction_image.records if record.kind == "JOB_EVIDENCE")
    contradiction_preserved = (
        contradiction_write.accepted
        and len(job_records) == 1
        and "observed=COMPLETED,REJECTED" in job_records[0].payload
        and "audit_reason=CONTRADICTORY_TERMINAL_EVIDENCE" in job_records[0].payload
    )
    unknown_not_forced = (
        len(job_records) == 1
        and job_records[0].ternary == 0
        and "decision=UNKNOWN" in job_records[0].payload
    )

    damaged = tamper_memory_record(report.memory_image.records, 2, "DAMAGED")
    damage_detected = not replay_memory(damaged).passed

    after_hashes = tuple(_sha256_file(path) for path in paths)
    input_after = repr(original_jobs)
    observed = base_governance.observation_report.host_run

    qualification = Stage4Qualification(
        passed=False,
        host_output_equivalent=direct.canonical_text() == observed.canonical_text(),
        host_digest_equivalent=direct.run_digest == observed.run_digest,
        host_source_unchanged=before_hashes[0] == after_hashes[0],
        adapter_source_unchanged=before_hashes[1] == after_hashes[1],
        governance_source_unchanged=before_hashes[2] == after_hashes[2],
        frozen_cntm_unchanged=before_hashes[3] == after_hashes[3],
        input_unchanged=input_before == input_after,
        observation_replay_pass=base_governance.observation_report.replay.passed,
        governance_replay_pass=base_governance.replay.passed,
        memory_replay_pass=report.replay.passed,
        bounded_write_pass=bounded_write_pass,
        duplicate_session_rejected=duplicate_rejected,
        contradiction_preserved=contradiction_preserved,
        unknown_not_forced=unknown_not_forced,
        damage_detected=damage_detected,
        intervention_attempts=report.intervention_attempts,
        record_count=len(report.memory_image.records),
        session_count=len(report.memory_image.session_ids),
        host_digest=direct.run_digest,
        observer_digest=base_governance.observation_report.observer_digest,
        governance_digest=base_governance.governance_digest,
        memory_digest=report.memory_image.final_digest,
        cntm_v3_0f_hash=report.cntm_v3_0f_hash,
    )
    passed = all(
        (
            qualification.host_output_equivalent,
            qualification.host_digest_equivalent,
            qualification.host_source_unchanged,
            qualification.adapter_source_unchanged,
            qualification.governance_source_unchanged,
            qualification.frozen_cntm_unchanged,
            qualification.input_unchanged,
            qualification.observation_replay_pass,
            qualification.governance_replay_pass,
            qualification.memory_replay_pass,
            qualification.bounded_write_pass,
            qualification.duplicate_session_rejected,
            qualification.contradiction_preserved,
            qualification.unknown_not_forced,
            qualification.damage_detected,
            qualification.intervention_attempts == 0,
            qualification.record_count > 0,
            qualification.session_count == 1,
        )
    )
    final = Stage4Qualification(**{**qualification.__dict__, "passed": passed})
    assert_no_float(final, "stage4_qualification")
    return final


def print_qualification(result: Stage4Qualification) -> None:
    print("=" * 88)
    print(f"{MEMORY_NAME} v{MEMORY_VERSION}")
    print("=" * 88)
    print(f"Mode / authority:             {MODE} / {AUTHORITY}")
    print(f"Host output equivalent:       {result.host_output_equivalent}")
    print(f"Host digest equivalent:       {result.host_digest_equivalent}")
    print(f"Host source unchanged:        {result.host_source_unchanged}")
    print(f"Adapter source unchanged:     {result.adapter_source_unchanged}")
    print(f"Governance source unchanged:  {result.governance_source_unchanged}")
    print(f"Frozen CNTM v3.0F unchanged:  {result.frozen_cntm_unchanged}")
    print(f"Input objects unchanged:      {result.input_unchanged}")
    print(f"Observation replay pass:      {result.observation_replay_pass}")
    print(f"Governance replay pass:       {result.governance_replay_pass}")
    print(f"Memory replay pass:           {result.memory_replay_pass}")
    print(f"Memory write bounded:         {result.bounded_write_pass}")
    print(f"Duplicate session rejected:   {result.duplicate_session_rejected}")
    print(f"Contradiction preserved:      {result.contradiction_preserved}")
    print(f"UNKNOWN not forced:           {result.unknown_not_forced}")
    print(f"Memory damage detected:       {result.damage_detected}")
    print(f"Unauthorized interventions:   {result.intervention_attempts}")
    print(f"Memory records / sessions:    {result.record_count} / {result.session_count}")
    print(f"Host digest:                  {result.host_digest}")
    print(f"Observer digest:              {result.observer_digest}")
    print(f"Governance digest:            {result.governance_digest}")
    print(f"Memory digest:                {result.memory_digest}")
    print(f"CNTM v3.0F hash:              {result.cntm_v3_0f_hash}")
    print(f"STAGE 4 SHADOW QUALIFICATION: {'PASS' if result.passed else 'FAIL'}")


def main() -> None:
    print_qualification(qualify_shadow_memory(ordinary_host.baseline_jobs()))


if __name__ == "__main__":
    main()
