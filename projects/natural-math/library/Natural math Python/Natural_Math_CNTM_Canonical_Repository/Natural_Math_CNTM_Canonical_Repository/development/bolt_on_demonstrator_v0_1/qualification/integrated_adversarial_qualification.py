#!/usr/bin/env python3
"""Integrated adversarial qualification for Bolt-On Demonstrator v0.1.

Stage 5 qualifies the complete shadow-only stack as one bounded system:

    ordinary host -> observation adapter -> Natural Math shadow governance
                  -> CNTM bounded shadow memory

The harness does not grant intervention authority. It executes normal and
adversarial fixtures, preserves multiple distinct sessions in one finite memory
image, injects damage only into immutable copies, verifies deterministic replay,
and proves repeated attachment and detachment leave the host unchanged.

Contract
--------
- Standard-library-only.
- Shadow mode; authority NONE.
- No file writing.
- No import or execution of frozen Natural Math or CNTM programs.
- Exact SHA-256 source identities before and after the campaign.
- Deterministic full-stack campaign digest.
- Fault injection must be detected without damaging clean evidence.
- Capacity and duplicate-session rejection must be atomic.
"""

from __future__ import annotations

import hashlib
import importlib.util
from dataclasses import dataclass
from pathlib import Path
import sys
from typing import Sequence, Tuple

HARNESS_NAME = "BOLT-ON INTEGRATED ADVERSARIAL QUALIFICATION"
HARNESS_VERSION = "0.5"
MODE = "SHADOW"
AUTHORITY = "NONE"
ATTACH_DETACH_CYCLES = 5
SHARED_MEMORY_CAPACITY = 96
ZERO_HASH = "0" * 64

THIS_FILE = Path(__file__).resolve()
PROJECT_DIR = THIS_FILE.parents[1]
REPOSITORY_ROOT = THIS_FILE.parents[3]
MEMORY_PATH = PROJECT_DIR / "memory" / "cntm_shadow_memory.py"


def _load_memory_module():
    module_name = "bolt_on_stage4_cntm_shadow_memory"
    existing = sys.modules.get(module_name)
    if existing is not None:
        return existing
    spec = importlib.util.spec_from_file_location(module_name, MEMORY_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"could not load Stage 4 memory module from {MEMORY_PATH}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


memory = _load_memory_module()
governance = memory.governance
adapter = memory.adapter
ordinary_host = memory.ordinary_host

HOST_PATH = PROJECT_DIR / "host" / "ordinary_host.py"
ADAPTER_PATH = PROJECT_DIR / "adapter" / "bolt_on_adapter.py"
GOVERNANCE_PATH = PROJECT_DIR / "governance" / "natural_math_shadow_governance.py"


@dataclass(frozen=True)
class CampaignFixture:
    name: str
    jobs: Tuple[object, ...]
    starting_value: int = 0


@dataclass(frozen=True)
class CaseResult:
    name: str
    host_equivalent: bool
    observation_replay_pass: bool
    governance_replay_pass: bool
    memory_replay_pass: bool
    intervention_attempts: int
    host_digest: str
    observer_digest: str
    governance_digest: str
    memory_digest: str
    session_id: str
    decision_counts: Tuple[Tuple[str, int], ...]

    def canonical_line(self) -> str:
        counts = ",".join(f"{name}:{count}" for name, count in self.decision_counts)
        return "|".join(
            (
                self.name,
                "1" if self.host_equivalent else "0",
                "1" if self.observation_replay_pass else "0",
                "1" if self.governance_replay_pass else "0",
                "1" if self.memory_replay_pass else "0",
                str(self.intervention_attempts),
                self.host_digest,
                self.observer_digest,
                self.governance_digest,
                self.memory_digest,
                self.session_id,
                counts,
            )
        )


@dataclass(frozen=True)
class FaultResult:
    name: str
    detected: bool
    clean_evidence_preserved: bool
    first_error: str

    def canonical_line(self) -> str:
        return "|".join(
            (
                self.name,
                "1" if self.detected else "0",
                "1" if self.clean_evidence_preserved else "0",
                self.first_error,
            )
        )


@dataclass(frozen=True)
class CleanCampaign:
    cases: Tuple[CaseResult, ...]
    governance_reports: Tuple[object, ...]
    shared_memory_image: object
    shared_memory_replay: object
    shared_write_results: Tuple[object, ...]
    contradiction_session_id: str
    contradiction_preserved: bool
    unknown_not_forced: bool
    duplicate_rejected_atomically: bool
    capacity_rejected_atomically: bool
    faults: Tuple[FaultResult, ...]
    attach_detach_pass: bool
    attach_detach_cycles: int
    source_manifest_before: Tuple[Tuple[str, str], ...]
    source_manifest_after: Tuple[Tuple[str, str], ...]
    frozen_file_count: int
    campaign_digest: str


@dataclass(frozen=True)
class Stage5Qualification:
    passed: bool
    host_modification_required: bool
    frozen_modification_required: bool
    full_stack_replay_pass: bool
    deterministic_campaign_pass: bool
    fault_containment_pass: bool
    safe_attachment_pass: bool
    safe_detachment_pass: bool
    multi_run_memory_consistency_pass: bool
    duplicate_rejection_pass: bool
    capacity_rejection_pass: bool
    contradiction_preserved: bool
    unknown_not_forced: bool
    source_integrity_pass: bool
    unauthorized_interventions: int
    campaign_count: int
    memory_session_count: int
    memory_record_count: int
    fault_count: int
    attach_detach_cycles: int
    frozen_file_count: int
    campaign_digest: str
    repeated_campaign_digest: str
    shared_memory_digest: str


def _sha256_file(path: Path) -> str:
    if not path.is_file():
        raise FileNotFoundError(f"required source is missing: {path}")
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _source_paths() -> Tuple[Path, ...]:
    frozen_paths = tuple(sorted((REPOSITORY_ROOT / "frozen").rglob("*.py")))
    return (HOST_PATH, ADAPTER_PATH, GOVERNANCE_PATH, MEMORY_PATH, *frozen_paths)


def source_manifest() -> Tuple[Tuple[str, str], ...]:
    rows = []
    for path in _source_paths():
        rows.append((path.relative_to(REPOSITORY_ROOT).as_posix(), _sha256_file(path)))
    return tuple(rows)


def campaign_fixtures() -> Tuple[CampaignFixture, ...]:
    Job = ordinary_host.Job
    baseline = ordinary_host.baseline_jobs()
    reordered = (
        baseline[7],
        baseline[4],
        baseline[3],
        baseline[2],
        baseline[1],
        baseline[0],
        baseline[5],
        baseline[6],
    )
    duplicate = (
        Job("DUP", "SET", 1),
        Job("DUP", "ADD", 2),
        Job("DEP", "ADD", 3, ("DUP",)),
        Job("SAFE", "SET", 9),
    )
    missing = (
        Job("MISS", "ADD", 2, ("ABSENT",)),
        Job("BASE", "SET", 8),
        Job("FOLLOW", "ADD", 4, ("BASE",)),
    )
    cycle = (
        Job("CYCLE_A", "ADD", 1, ("CYCLE_B",)),
        Job("CYCLE_B", "ADD", 1, ("CYCLE_A",)),
        Job("CYCLE_SAFE", "SET", 5),
    )
    mixed_invalid = (
        Job("BOOL", "SET", True),
        Job("BADOP", "POWER", 3),
        Job("SELF", "ADD", 1, ("SELF",)),
        Job("VALID", "SET", 6),
    )
    return (
        CampaignFixture("NORMAL", tuple(baseline)),
        CampaignFixture("REORDERED", reordered),
        CampaignFixture("DUPLICATE", duplicate),
        CampaignFixture("MISSING_DEPENDENCY", missing),
        CampaignFixture("DEPENDENCY_CYCLE", cycle),
        CampaignFixture("MIXED_INVALID", mixed_invalid),
    )


def _decision_counts(report: object) -> Tuple[Tuple[str, int], ...]:
    return tuple(
        (name, sum(1 for decision in report.decisions if decision.decision == name))
        for name in (
            governance.PROCEED,
            governance.DEFER,
            governance.RESTRICT,
            governance.UNKNOWN,
        )
    )


def run_case(fixture: CampaignFixture) -> Tuple[CaseResult, object]:
    direct = ordinary_host.run_jobs(fixture.jobs, starting_value=fixture.starting_value)
    report = memory.run_shadow_memory(
        fixture.jobs,
        starting_value=fixture.starting_value,
        capacity=memory.DEFAULT_CAPACITY,
    )
    governance_report = report.governance_report
    observed = governance_report.observation_report.host_run
    session_id = memory.session_identifier(governance_report)
    result = CaseResult(
        name=fixture.name,
        host_equivalent=(
            direct == observed
            and direct.canonical_text() == observed.canonical_text()
            and direct.run_digest == observed.run_digest
        ),
        observation_replay_pass=governance_report.observation_report.replay.passed,
        governance_replay_pass=governance_report.replay.passed,
        memory_replay_pass=report.replay.passed,
        intervention_attempts=report.intervention_attempts,
        host_digest=direct.run_digest,
        observer_digest=governance_report.observation_report.observer_digest,
        governance_digest=governance_report.governance_digest,
        memory_digest=report.memory_image.final_digest,
        session_id=session_id,
        decision_counts=_decision_counts(governance_report),
    )
    return result, governance_report


def _fault_matrix(base_report: object, shared_records: Sequence[object]) -> Tuple[FaultResult, ...]:
    observation = base_report.observation_report

    altered_observation = adapter.tamper_receipt(
        observation.receipts,
        1,
        "DAMAGED_OBSERVATION_PAYLOAD",
    )
    altered_observation_replay = adapter.replay_observation_receipts(altered_observation)
    missing_observation_replay = adapter.replay_observation_receipts(
        observation.receipts[:2] + observation.receipts[3:]
    )

    altered_governance = governance.tamper_governance_receipt(
        base_report.receipts,
        1,
        "DAMAGED_GOVERNANCE_PAYLOAD",
    )
    altered_governance_replay = governance.replay_governance_receipts(altered_governance)
    missing_governance_replay = governance.replay_governance_receipts(
        base_report.receipts[:2] + base_report.receipts[3:]
    )

    altered_memory = memory.tamper_memory_record(
        shared_records,
        2,
        "DAMAGED_MEMORY_PAYLOAD",
    )
    altered_memory_replay = memory.replay_memory(altered_memory)
    missing_memory_replay = memory.replay_memory(
        tuple(shared_records[:2]) + tuple(shared_records[3:])
    )

    clean_observation = adapter.replay_observation_receipts(observation.receipts)
    clean_governance = governance.replay_governance_receipts(base_report.receipts)
    clean_memory = memory.replay_memory(shared_records)

    return (
        FaultResult(
            "OBSERVATION_TAMPER",
            not altered_observation_replay.passed,
            clean_observation.passed,
            altered_observation_replay.first_error,
        ),
        FaultResult(
            "OBSERVATION_MISSING_RECEIPT",
            not missing_observation_replay.passed,
            clean_observation.passed,
            missing_observation_replay.first_error,
        ),
        FaultResult(
            "GOVERNANCE_TAMPER",
            not altered_governance_replay.passed,
            clean_governance.passed,
            altered_governance_replay.first_error,
        ),
        FaultResult(
            "GOVERNANCE_MISSING_RECEIPT",
            not missing_governance_replay.passed,
            clean_governance.passed,
            missing_governance_replay.first_error,
        ),
        FaultResult(
            "MEMORY_TAMPER",
            not altered_memory_replay.passed,
            clean_memory.passed,
            altered_memory_replay.first_error,
        ),
        FaultResult(
            "MEMORY_MISSING_RECORD",
            not missing_memory_replay.passed,
            clean_memory.passed,
            missing_memory_replay.first_error,
        ),
    )


def _attach_detach_qualification(jobs: Sequence[object], cycles: int) -> bool:
    if isinstance(cycles, bool) or not isinstance(cycles, int) or cycles <= 0:
        raise ValueError("cycles must be a positive integer")
    baseline = ordinary_host.run_jobs(jobs)
    for _ in range(cycles):
        before = ordinary_host.run_jobs(jobs)
        attached = memory.run_shadow_memory(jobs)
        after = ordinary_host.run_jobs(jobs)
        observed = attached.governance_report.observation_report.host_run
        if not (
            before == baseline
            and observed == baseline
            and after == baseline
            and before.run_digest == after.run_digest == observed.run_digest
            and attached.intervention_attempts == 0
            and attached.replay.passed
        ):
            return False
    return True


def _campaign_digest(
    cases: Sequence[CaseResult],
    shared_digest: str,
    shared_sessions: Sequence[str],
    contradiction_session_id: str,
    faults: Sequence[FaultResult],
    source_rows: Sequence[Tuple[str, str]],
    attach_detach_pass: bool,
) -> str:
    lines = [f"HARNESS={HARNESS_NAME}", f"VERSION={HARNESS_VERSION}"]
    lines.extend(case.canonical_line() for case in cases)
    lines.append(f"SHARED_DIGEST={shared_digest}")
    lines.append("SESSIONS=" + ",".join(shared_sessions))
    lines.append(f"CONTRADICTION_SESSION={contradiction_session_id}")
    lines.extend(fault.canonical_line() for fault in faults)
    lines.extend(f"SOURCE={path}|{digest}" for path, digest in source_rows)
    lines.append(f"ATTACH_DETACH={'1' if attach_detach_pass else '0'}")
    return hashlib.sha256("\n".join(lines).encode("utf-8")).hexdigest()


def execute_clean_campaign() -> CleanCampaign:
    before = source_manifest()
    fixtures = campaign_fixtures()
    case_results = []
    governance_reports = []
    for fixture in fixtures:
        case, report = run_case(fixture)
        case_results.append(case)
        governance_reports.append(report)

    shared_memory = memory.BoundedCNTMShadowMemory(SHARED_MEMORY_CAPACITY)
    writes = []
    for report in governance_reports:
        writes.append(shared_memory.append_report(report))
        if not memory.replay_memory(shared_memory.snapshot().records).passed:
            raise AssertionError("shared memory failed replay after a clean session write")

    contradiction_report = memory._synthetic_contradiction_report(governance_reports[0])
    contradiction_write = shared_memory.append_report(contradiction_report)
    writes.append(contradiction_write)
    contradiction_session_id = memory.session_identifier(contradiction_report)
    shared_image = shared_memory.snapshot()
    shared_replay = memory.replay_memory(shared_image.records)
    contradiction_records = tuple(
        record
        for record in shared_image.records
        if record.session_id == contradiction_session_id and record.kind == "JOB_EVIDENCE"
    )
    contradiction_preserved = (
        contradiction_write.accepted
        and len(contradiction_records) == 1
        and "observed=COMPLETED,REJECTED" in contradiction_records[0].payload
        and "audit_reason=CONTRADICTORY_TERMINAL_EVIDENCE" in contradiction_records[0].payload
    )
    unknown_not_forced = (
        len(contradiction_records) == 1
        and contradiction_records[0].ternary == 0
        and "decision=UNKNOWN" in contradiction_records[0].payload
    )

    duplicate_before = shared_memory.snapshot()
    duplicate_write = shared_memory.append_report(governance_reports[0])
    duplicate_after = shared_memory.snapshot()
    duplicate_rejected = (
        not duplicate_write.accepted
        and duplicate_write.reason_code == "DUPLICATE_SESSION"
        and duplicate_before == duplicate_after
    )

    records_needed = len(governance_reports[0].decisions) + 2
    too_small = memory.BoundedCNTMShadowMemory(records_needed - 1)
    capacity_before = too_small.snapshot()
    capacity_write = too_small.append_report(governance_reports[0])
    capacity_after = too_small.snapshot()
    capacity_rejected = (
        not capacity_write.accepted
        and capacity_write.reason_code == "MEMORY_CAPACITY_EXCEEDED"
        and capacity_before == capacity_after
    )

    faults = _fault_matrix(governance_reports[0], shared_image.records)
    attach_detach_pass = _attach_detach_qualification(
        ordinary_host.baseline_jobs(),
        ATTACH_DETACH_CYCLES,
    )
    after = source_manifest()
    frozen_count = sum(1 for path, _ in before if path.startswith("frozen/"))
    digest = _campaign_digest(
        case_results,
        shared_image.final_digest,
        shared_image.session_ids,
        contradiction_session_id,
        faults,
        before,
        attach_detach_pass,
    )
    clean = CleanCampaign(
        cases=tuple(case_results),
        governance_reports=tuple(governance_reports),
        shared_memory_image=shared_image,
        shared_memory_replay=shared_replay,
        shared_write_results=tuple(writes),
        contradiction_session_id=contradiction_session_id,
        contradiction_preserved=contradiction_preserved,
        unknown_not_forced=unknown_not_forced,
        duplicate_rejected_atomically=duplicate_rejected,
        capacity_rejected_atomically=capacity_rejected,
        faults=faults,
        attach_detach_pass=attach_detach_pass,
        attach_detach_cycles=ATTACH_DETACH_CYCLES,
        source_manifest_before=before,
        source_manifest_after=after,
        frozen_file_count=frozen_count,
        campaign_digest=digest,
    )
    memory.assert_no_float(clean, "stage5_clean_campaign")
    return clean


def qualify_integrated_stack() -> Stage5Qualification:
    first = execute_clean_campaign()
    second = execute_clean_campaign()

    source_integrity = (
        first.source_manifest_before == first.source_manifest_after
        and second.source_manifest_before == second.source_manifest_after
        and first.source_manifest_before == second.source_manifest_before
    )
    full_stack_replay = all(
        case.observation_replay_pass
        and case.governance_replay_pass
        and case.memory_replay_pass
        for case in first.cases
    ) and first.shared_memory_replay.passed
    deterministic = (
        first.campaign_digest == second.campaign_digest
        and first.cases == second.cases
        and first.shared_memory_image == second.shared_memory_image
        and first.faults == second.faults
    )
    fault_containment = all(
        fault.detected and fault.clean_evidence_preserved for fault in first.faults
    )
    multi_run_consistency = (
        all(write.accepted for write in first.shared_write_results)
        and first.shared_memory_replay.passed
        and first.shared_memory_replay.final_digest == first.shared_memory_image.final_digest
        and first.shared_memory_replay.session_count == len(first.shared_memory_image.session_ids)
        and len(first.shared_memory_image.session_ids) == len(first.cases) + 1
        and len(set(first.shared_memory_image.session_ids)) == len(first.shared_memory_image.session_ids)
    )
    interventions = sum(case.intervention_attempts for case in first.cases)
    host_equivalence = all(case.host_equivalent for case in first.cases)

    draft = Stage5Qualification(
        passed=False,
        host_modification_required=not host_equivalence,
        frozen_modification_required=not source_integrity,
        full_stack_replay_pass=full_stack_replay,
        deterministic_campaign_pass=deterministic,
        fault_containment_pass=fault_containment,
        safe_attachment_pass=first.attach_detach_pass,
        safe_detachment_pass=first.attach_detach_pass,
        multi_run_memory_consistency_pass=multi_run_consistency,
        duplicate_rejection_pass=first.duplicate_rejected_atomically,
        capacity_rejection_pass=first.capacity_rejected_atomically,
        contradiction_preserved=first.contradiction_preserved,
        unknown_not_forced=first.unknown_not_forced,
        source_integrity_pass=source_integrity,
        unauthorized_interventions=interventions,
        campaign_count=len(first.cases),
        memory_session_count=len(first.shared_memory_image.session_ids),
        memory_record_count=len(first.shared_memory_image.records),
        fault_count=len(first.faults),
        attach_detach_cycles=first.attach_detach_cycles,
        frozen_file_count=first.frozen_file_count,
        campaign_digest=first.campaign_digest,
        repeated_campaign_digest=second.campaign_digest,
        shared_memory_digest=first.shared_memory_image.final_digest,
    )
    passed = all(
        (
            not draft.host_modification_required,
            not draft.frozen_modification_required,
            draft.full_stack_replay_pass,
            draft.deterministic_campaign_pass,
            draft.fault_containment_pass,
            draft.safe_attachment_pass,
            draft.safe_detachment_pass,
            draft.multi_run_memory_consistency_pass,
            draft.duplicate_rejection_pass,
            draft.capacity_rejection_pass,
            draft.contradiction_preserved,
            draft.unknown_not_forced,
            draft.source_integrity_pass,
            draft.unauthorized_interventions == 0,
            draft.campaign_count == 6,
            draft.memory_session_count == 7,
            draft.memory_record_count > 0,
            draft.fault_count == 6,
            draft.attach_detach_cycles == ATTACH_DETACH_CYCLES,
            draft.frozen_file_count == 11,
        )
    )
    final = Stage5Qualification(**{**draft.__dict__, "passed": passed})
    memory.assert_no_float(final, "stage5_qualification")
    return final


def print_qualification(result: Stage5Qualification) -> None:
    print("=" * 88)
    print(f"{HARNESS_NAME} v{HARNESS_VERSION}")
    print("=" * 88)
    print(f"Mode / authority:                 {MODE} / {AUTHORITY}")
    print(f"Host modification required:       {result.host_modification_required}")
    print(f"Frozen modification required:     {result.frozen_modification_required}")
    print(f"Full-stack replay:                {result.full_stack_replay_pass}")
    print(f"Deterministic campaign:           {result.deterministic_campaign_pass}")
    print(f"Fault containment:                {result.fault_containment_pass}")
    print(f"Safe attachment:                  {result.safe_attachment_pass}")
    print(f"Safe detachment:                  {result.safe_detachment_pass}")
    print(f"Multi-run memory consistency:     {result.multi_run_memory_consistency_pass}")
    print(f"Duplicate rejection atomic:       {result.duplicate_rejection_pass}")
    print(f"Capacity rejection atomic:        {result.capacity_rejection_pass}")
    print(f"Contradiction preserved:          {result.contradiction_preserved}")
    print(f"UNKNOWN not forced:               {result.unknown_not_forced}")
    print(f"Source integrity:                 {result.source_integrity_pass}")
    print(f"Unauthorized interventions:       {result.unauthorized_interventions}")
    print(f"Campaigns / faults:               {result.campaign_count} / {result.fault_count}")
    print(f"Memory sessions / records:        {result.memory_session_count} / {result.memory_record_count}")
    print(f"Attach-detach cycles:             {result.attach_detach_cycles}")
    print(f"Frozen source files checked:      {result.frozen_file_count}")
    print(f"Campaign digest:                  {result.campaign_digest}")
    print(f"Repeated campaign digest:         {result.repeated_campaign_digest}")
    print(f"Shared memory digest:             {result.shared_memory_digest}")
    print(f"STAGE 5 INTEGRATED QUALIFICATION: {'PASS' if result.passed else 'FAIL'}")


def main() -> None:
    print_qualification(qualify_integrated_stack())


if __name__ == "__main__":
    main()
