#!/usr/bin/env python3
"""Natural Math shadow-governance interface for Bolt-On Demonstrator v0.1.

Stage 3 attaches a deterministic governance layer to the unchanged Stage 1 host
through the unchanged Stage 2 observation adapter. The layer operates only in
SHADOW mode: it records what it would recommend, but it has no path to alter,
filter, reorder, replace, or suppress host jobs or host outcomes.

The new interface follows the frozen Natural Math v12.0 RC21 boundary:
- bounded authority;
- deterministic local evidence;
- explicit PROCEED / DEFER / RESTRICT / UNKNOWN outcomes;
- exact hash-chained receipts;
- replay and tamper detection;
- no modification of host, observer, or frozen source.

The frozen RC21 file is used as a byte-identity oracle. It is read for SHA-256
verification only; it is not imported, executed, rewritten, or patched.
"""

from __future__ import annotations

import hashlib
import importlib.util
from dataclasses import dataclass
from pathlib import Path
import sys
from typing import Iterable, Mapping, Sequence, Tuple

INTERFACE_NAME = "NATURAL MATH SHADOW GOVERNANCE INTERFACE"
INTERFACE_VERSION = "0.3"
MODE = "SHADOW"
AUTHORITY = "NONE"

PROCEED = "PROCEED"
DEFER = "DEFER"
RESTRICT = "RESTRICT"
UNKNOWN = "UNKNOWN"

THIS_FILE = Path(__file__).resolve()
PROJECT_DIR = THIS_FILE.parents[1]
REPOSITORY_ROOT = THIS_FILE.parents[3]
ADAPTER_PATH = PROJECT_DIR / "adapter" / "bolt_on_adapter.py"
HOST_PATH = PROJECT_DIR / "host" / "ordinary_host.py"
RC21_PATH = (
    REPOSITORY_ROOT
    / "frozen"
    / "natural_math"
    / "v12.0"
    / "natural_math_v12_0_RC21_FINAL_COMPATIBILITY_REPLAY_RELEASE_FREEZE.py"
)


def _load_adapter_module():
    module_name = "bolt_on_stage2_observation_adapter"
    existing = sys.modules.get(module_name)
    if existing is not None:
        return existing
    spec = importlib.util.spec_from_file_location(module_name, ADAPTER_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"could not load observation adapter from {ADAPTER_PATH}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


adapter = _load_adapter_module()
ordinary_host = adapter.ordinary_host


@dataclass(frozen=True)
class GovernanceDecision:
    ordinal: int
    job_id: str
    decision: str
    ternary: int
    reason_code: str
    expected_outcome: str
    evidence: Tuple[Tuple[str, str], ...]

    def canonical_line(self) -> str:
        evidence_text = ",".join(f"{key}={value}" for key, value in self.evidence)
        return "|".join(
            (
                str(self.ordinal),
                self.job_id,
                self.decision,
                str(self.ternary),
                self.reason_code,
                self.expected_outcome,
                evidence_text,
            )
        )


@dataclass(frozen=True)
class OutcomeAudit:
    ordinal: int
    job_id: str
    decision: str
    expected_outcome: str
    observed_outcomes: Tuple[str, ...]
    status: str
    reason_code: str

    def canonical_line(self) -> str:
        return "|".join(
            (
                str(self.ordinal),
                self.job_id,
                self.decision,
                self.expected_outcome,
                ",".join(self.observed_outcomes),
                self.status,
                self.reason_code,
            )
        )


@dataclass(frozen=True)
class GovernanceReceipt:
    receipt_id: int
    kind: str
    subject: str
    payload: str
    prior_hash: str
    receipt_hash: str


@dataclass(frozen=True)
class GovernanceReplay:
    passed: bool
    final_digest: str
    checked_receipts: int
    first_error: str


@dataclass(frozen=True)
class ShadowGovernanceReport:
    observation_report: object
    decisions: Tuple[GovernanceDecision, ...]
    audits: Tuple[OutcomeAudit, ...]
    receipts: Tuple[GovernanceReceipt, ...]
    governance_digest: str
    replay: GovernanceReplay
    natural_math_rc21_hash: str
    intervention_attempts: int


@dataclass(frozen=True)
class ShadowQualification:
    passed: bool
    host_output_equivalent: bool
    host_digest_equivalent: bool
    host_source_unchanged: bool
    adapter_source_unchanged: bool
    frozen_source_unchanged: bool
    input_unchanged: bool
    observation_replay_pass: bool
    governance_replay_pass: bool
    all_outcomes_match: bool
    intervention_attempts: int
    decision_counts: Tuple[Tuple[str, int], ...]
    host_digest: str
    observer_digest: str
    governance_digest: str
    natural_math_rc21_hash: str
    receipt_count: int


def _sha256_file(path: Path) -> str:
    if not path.is_file():
        raise FileNotFoundError(f"required source is missing: {path}")
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _display_id(job_id: str) -> str:
    return job_id if job_id else "<EMPTY>"


def _basic_restriction(
    item: object,
    id_count: int,
) -> Tuple[str, str] | None:
    job_id = item.job_id
    operation = item.operation.strip().upper() if isinstance(item.operation, str) else ""
    requires = tuple(item.requires)

    if (
        job_id == "<UNREADABLE>"
        or operation == "<UNREADABLE>"
        or item.value_type == "unknown"
        or item.value_text == "<UNREADABLE>"
    ):
        return UNKNOWN, "INSUFFICIENT_EVIDENCE"
    if not job_id:
        return RESTRICT, "EMPTY_JOB_ID"
    if id_count > 1:
        return RESTRICT, "DUPLICATE_JOB_ID"
    if operation not in ordinary_host.SUPPORTED_OPERATIONS:
        return RESTRICT, "UNSUPPORTED_OPERATION"
    if item.value_type != "int":
        return RESTRICT, "VALUE_NOT_INTEGER"
    if any(not isinstance(req, str) or not req for req in requires):
        return RESTRICT, "INVALID_REQUIREMENT_ID"
    if len(set(requires)) != len(requires):
        return RESTRICT, "DUPLICATE_REQUIREMENT_ID"
    if job_id in requires:
        return RESTRICT, "SELF_DEPENDENCY"
    return None


def classify_snapshot(snapshot: Sequence[object]) -> Tuple[GovernanceDecision, ...]:
    """Classify immutable observed jobs without changing host inputs."""

    counts: dict[str, int] = {}
    all_ids: set[str] = set()
    for item in snapshot:
        if isinstance(item.job_id, str) and item.job_id:
            all_ids.add(item.job_id)
            counts[item.job_id] = counts.get(item.job_id, 0) + 1

    preliminary: dict[int, Tuple[str, str] | None] = {}
    admissible_ids: set[str] = set()
    item_by_id: dict[str, object] = {}
    for item in snapshot:
        result = _basic_restriction(item, counts.get(item.job_id, 0))
        preliminary[item.ordinal] = result
        if result is None:
            admissible_ids.add(item.job_id)
            item_by_id[item.job_id] = item

    # Resolve only dependency chains that can be proven locally from admitted jobs.
    resolvable: set[str] = set()
    changed = True
    while changed:
        changed = False
        for job_id in sorted(admissible_ids):
            if job_id in resolvable:
                continue
            item = item_by_id[job_id]
            requires = tuple(item.requires)
            if all(requirement in resolvable for requirement in requires):
                resolvable.add(job_id)
                changed = True

    decisions = []
    for item in snapshot:
        display_id = _display_id(item.job_id)
        preliminary_result = preliminary[item.ordinal]
        requires = tuple(item.requires)
        missing = tuple(req for req in requires if req not in all_ids)
        blocked = tuple(req for req in requires if req in all_ids and req not in admissible_ids)

        if preliminary_result is not None:
            decision, reason = preliminary_result
        elif item.job_id in resolvable:
            decision, reason = PROCEED, "LOCAL_EVIDENCE_ADMISSIBLE"
        elif missing:
            decision, reason = DEFER, "MISSING_DEPENDENCY"
        elif blocked:
            decision, reason = DEFER, "DEPENDENCY_NOT_ADMISSIBLE"
        else:
            decision, reason = DEFER, "UNRESOLVED_DEPENDENCY_GRAPH"

        ternary = 1 if decision == PROCEED else -1 if decision == RESTRICT else 0
        expected = (
            "COMPLETED"
            if decision == PROCEED
            else "REJECTED"
            if decision == RESTRICT
            else "DELAYED"
            if decision == DEFER
            else "NONE"
        )
        evidence = tuple(
            sorted(
                (
                    ("id_count", str(counts.get(item.job_id, 0))),
                    ("missing", ",".join(missing)),
                    ("operation", item.operation.strip().upper()),
                    ("requires", ",".join(requires)),
                    ("value_type", item.value_type),
                )
            )
        )
        decisions.append(
            GovernanceDecision(
                ordinal=item.ordinal,
                job_id=display_id,
                decision=decision,
                ternary=ternary,
                reason_code=reason,
                expected_outcome=expected,
                evidence=evidence,
            )
        )
    return tuple(decisions)


def audit_one_decision(
    decision: GovernanceDecision,
    observed_outcomes: Sequence[str],
) -> OutcomeAudit:
    outcomes = tuple(observed_outcomes)
    unique = tuple(sorted(set(outcomes)))
    if not outcomes:
        status, reason = UNKNOWN, "MISSING_TERMINAL_EVIDENCE"
    elif len(unique) > 1:
        status, reason = UNKNOWN, "CONTRADICTORY_TERMINAL_EVIDENCE"
    elif decision.decision == UNKNOWN:
        status, reason = UNKNOWN, "DECISION_NOT_ASSERTED"
    elif unique[0] == decision.expected_outcome:
        status, reason = "MATCH", "EXPECTED_OUTCOME_OBSERVED"
    else:
        status, reason = "MISMATCH", "UNEXPECTED_OUTCOME"
    return OutcomeAudit(
        ordinal=decision.ordinal,
        job_id=decision.job_id,
        decision=decision.decision,
        expected_outcome=decision.expected_outcome,
        observed_outcomes=outcomes,
        status=status,
        reason_code=reason,
    )


def audit_host_outcomes(
    decisions: Sequence[GovernanceDecision],
    host_run: object,
) -> Tuple[OutcomeAudit, ...]:
    terminal_by_id: dict[str, list[str]] = {}
    for event in host_run.events:
        if event.event in ("COMPLETED", "REJECTED", "DELAYED"):
            terminal_by_id.setdefault(event.job_id, []).append(event.event)

    audits = []
    cursors: dict[str, int] = {}
    for decision in decisions:
        items = terminal_by_id.get(decision.job_id, [])
        cursor = cursors.get(decision.job_id, 0)
        outcomes = (items[cursor],) if cursor < len(items) else ()
        cursors[decision.job_id] = cursor + 1
        audits.append(audit_one_decision(decision, outcomes))
    return tuple(audits)


def _receipt_hash(
    receipt_id: int,
    kind: str,
    subject: str,
    payload: str,
    prior_hash: str,
) -> str:
    unsigned = "|".join((str(receipt_id), kind, subject, payload, prior_hash))
    return hashlib.sha256(unsigned.encode("utf-8")).hexdigest()


def build_governance_receipts(
    observation_report: object,
    decisions: Sequence[GovernanceDecision],
    audits: Sequence[OutcomeAudit],
    rc21_hash: str,
) -> Tuple[GovernanceReceipt, ...]:
    receipts = []
    prior_hash = "0" * 64

    def append(kind: str, subject: str, payload: str) -> None:
        nonlocal prior_hash
        receipt_id = len(receipts) + 1
        receipt_hash = _receipt_hash(receipt_id, kind, subject, payload, prior_hash)
        receipts.append(
            GovernanceReceipt(
                receipt_id=receipt_id,
                kind=kind,
                subject=subject,
                payload=payload,
                prior_hash=prior_hash,
                receipt_hash=receipt_hash,
            )
        )
        prior_hash = receipt_hash

    append(
        "SESSION",
        "OPEN",
        ";".join(
            (
                f"interface={INTERFACE_NAME}",
                f"version={INTERFACE_VERSION}",
                f"mode={MODE}",
                f"authority={AUTHORITY}",
                f"host_digest={observation_report.host_run.run_digest}",
                f"observer_digest={observation_report.observer_digest}",
                f"rc21_hash={rc21_hash}",
            )
        ),
    )
    for decision in decisions:
        append("DECISION", f"JOB:{decision.ordinal}:{decision.job_id}", decision.canonical_line())
    for audit in audits:
        append("AUDIT", f"JOB:{audit.ordinal}:{audit.job_id}", audit.canonical_line())
    counts = {name: 0 for name in (PROCEED, DEFER, RESTRICT, UNKNOWN)}
    for decision in decisions:
        counts[decision.decision] += 1
    append(
        "SUMMARY",
        "SHADOW_RUN",
        ";".join(
            (
                f"proceed={counts[PROCEED]}",
                f"defer={counts[DEFER]}",
                f"restrict={counts[RESTRICT]}",
                f"unknown={counts[UNKNOWN]}",
                f"outcome_matches={sum(1 for audit in audits if audit.status == 'MATCH')}",
                "intervention_attempts=0",
            )
        ),
    )
    return tuple(receipts)


def replay_governance_receipts(
    receipts: Sequence[GovernanceReceipt],
) -> GovernanceReplay:
    prior_hash = "0" * 64
    for expected_id, receipt in enumerate(receipts, start=1):
        if receipt.receipt_id != expected_id:
            return GovernanceReplay(
                False,
                prior_hash,
                expected_id - 1,
                f"RECEIPT_ID_MISMATCH:{expected_id}:{receipt.receipt_id}",
            )
        if receipt.prior_hash != prior_hash:
            return GovernanceReplay(
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
            return GovernanceReplay(
                False,
                prior_hash,
                expected_id - 1,
                f"RECEIPT_HASH_MISMATCH:{expected_id}",
            )
        prior_hash = expected_hash
    return GovernanceReplay(True, prior_hash, len(receipts), "NONE")


def tamper_governance_receipt(
    receipts: Sequence[GovernanceReceipt],
    index: int,
    replacement_payload: str,
) -> Tuple[GovernanceReceipt, ...]:
    if not 0 <= index < len(receipts):
        raise IndexError("receipt index out of range")
    altered = list(receipts)
    old = altered[index]
    altered[index] = GovernanceReceipt(
        old.receipt_id,
        old.kind,
        old.subject,
        replacement_payload,
        old.prior_hash,
        old.receipt_hash,
    )
    return tuple(altered)


def run_shadow_governance(
    jobs: Iterable[object],
    starting_value: int = 0,
) -> ShadowGovernanceReport:
    original_jobs = tuple(jobs)
    observation = adapter.observe_jobs(original_jobs, starting_value=starting_value)
    decisions = classify_snapshot(observation.input_snapshot)
    audits = audit_host_outcomes(decisions, observation.host_run)
    rc21_hash = _sha256_file(RC21_PATH)
    receipts = build_governance_receipts(observation, decisions, audits, rc21_hash)
    replay = replay_governance_receipts(receipts)
    governance_digest = receipts[-1].receipt_hash if receipts else "0" * 64
    return ShadowGovernanceReport(
        observation_report=observation,
        decisions=decisions,
        audits=audits,
        receipts=receipts,
        governance_digest=governance_digest,
        replay=replay,
        natural_math_rc21_hash=rc21_hash,
        intervention_attempts=0,
    )


def qualify_shadow_governance(
    jobs: Iterable[object],
    starting_value: int = 0,
) -> ShadowQualification:
    original_jobs = tuple(jobs)
    input_before = repr(original_jobs)
    host_before = _sha256_file(HOST_PATH)
    adapter_before = _sha256_file(ADAPTER_PATH)
    rc21_before = _sha256_file(RC21_PATH)

    direct = ordinary_host.run_jobs(original_jobs, starting_value=starting_value)
    shadow = run_shadow_governance(original_jobs, starting_value=starting_value)

    host_after = _sha256_file(HOST_PATH)
    adapter_after = _sha256_file(ADAPTER_PATH)
    rc21_after = _sha256_file(RC21_PATH)
    input_after = repr(original_jobs)

    observed = shadow.observation_report.host_run
    host_output_equivalent = direct.canonical_text() == observed.canonical_text()
    host_digest_equivalent = direct.run_digest == observed.run_digest
    all_outcomes_match = all(audit.status == "MATCH" for audit in shadow.audits)
    counts = tuple(
        (name, sum(1 for item in shadow.decisions if item.decision == name))
        for name in (PROCEED, DEFER, RESTRICT, UNKNOWN)
    )
    passed = all(
        (
            host_output_equivalent,
            host_digest_equivalent,
            host_before == host_after,
            adapter_before == adapter_after,
            rc21_before == rc21_after,
            input_before == input_after,
            shadow.observation_report.replay.passed,
            shadow.replay.passed,
            all_outcomes_match,
            shadow.intervention_attempts == 0,
        )
    )
    return ShadowQualification(
        passed=passed,
        host_output_equivalent=host_output_equivalent,
        host_digest_equivalent=host_digest_equivalent,
        host_source_unchanged=host_before == host_after,
        adapter_source_unchanged=adapter_before == adapter_after,
        frozen_source_unchanged=rc21_before == rc21_after,
        input_unchanged=input_before == input_after,
        observation_replay_pass=shadow.observation_report.replay.passed,
        governance_replay_pass=shadow.replay.passed,
        all_outcomes_match=all_outcomes_match,
        intervention_attempts=shadow.intervention_attempts,
        decision_counts=counts,
        host_digest=direct.run_digest,
        observer_digest=shadow.observation_report.observer_digest,
        governance_digest=shadow.governance_digest,
        natural_math_rc21_hash=shadow.natural_math_rc21_hash,
        receipt_count=len(shadow.receipts),
    )


def print_qualification(qualification: ShadowQualification) -> None:
    print("=" * 88)
    print(f"{INTERFACE_NAME} v{INTERFACE_VERSION}")
    print("=" * 88)
    print(f"Mode / authority:             {MODE} / {AUTHORITY}")
    print(f"Host output equivalent:       {qualification.host_output_equivalent}")
    print(f"Host digest equivalent:       {qualification.host_digest_equivalent}")
    print(f"Host source unchanged:        {qualification.host_source_unchanged}")
    print(f"Adapter source unchanged:     {qualification.adapter_source_unchanged}")
    print(f"Frozen RC21 unchanged:        {qualification.frozen_source_unchanged}")
    print(f"Input objects unchanged:      {qualification.input_unchanged}")
    print(f"Observation replay pass:      {qualification.observation_replay_pass}")
    print(f"Governance replay pass:       {qualification.governance_replay_pass}")
    print(f"All outcomes match:           {qualification.all_outcomes_match}")
    print(f"Unauthorized interventions:   {qualification.intervention_attempts}")
    print(f"Decision counts:              {qualification.decision_counts}")
    print(f"Governance receipt count:     {qualification.receipt_count}")
    print(f"Host digest:                  {qualification.host_digest}")
    print(f"Observer digest:              {qualification.observer_digest}")
    print(f"Governance digest:            {qualification.governance_digest}")
    print(f"Natural Math RC21 hash:       {qualification.natural_math_rc21_hash}")
    print(f"STAGE 3 SHADOW QUALIFICATION: {'PASS' if qualification.passed else 'FAIL'}")


def main() -> None:
    qualification = qualify_shadow_governance(
        ordinary_host.baseline_jobs(),
        starting_value=0,
    )
    print_qualification(qualification)


if __name__ == "__main__":
    main()
