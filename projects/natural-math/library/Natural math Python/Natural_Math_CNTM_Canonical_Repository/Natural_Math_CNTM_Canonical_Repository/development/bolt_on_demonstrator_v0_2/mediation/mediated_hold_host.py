#!/usr/bin/env python3
"""Mediated HOLD host for Bolt-On Demonstrator v0.2, Stage 2.

This stage introduces the first active but tightly bounded intervention. A
separate disposable mediator may remove exactly one governance-DEFER job from
one replayed host batch and place that immutable job in a HOLD queue.

The qualified v0.1 host is never edited. Without a valid one-use HOLD permit,
the mediator runs the original batch unchanged. The Stage 1 authority grant
remains a dry-run advisory boundary; Stage 2 adds a separate execution permit
bound to the exact authority digest, governance session, request, job ordinal,
evidence digest, and integer epoch.

Prototype boundaries
--------------------
- standard-library-only;
- integer epochs and exact one-use budgets;
- HOLD is the only executable action;
- no ALLOW, DENY, rewrite, mutation, replacement, or reordering authority;
- permit missing/invalid/expired/reused/evidence-mismatched => passthrough;
- UNKNOWN or non-DEFER evidence can never execute;
- immutable mediation receipts and deterministic replay;
- frozen v0.1 and qualified development sources remain unchanged.

SHA-256 values are deterministic integrity bindings for this demonstrator, not
production identity signatures.
"""

from __future__ import annotations

import hashlib
import importlib.util
from dataclasses import dataclass, replace
from pathlib import Path
import sys
from typing import Iterable, Sequence, Tuple

sys.dont_write_bytecode = True

INTERFACE_NAME = "MEDIATED HOLD HOST"
INTERFACE_VERSION = "0.2.2"
MODE = "ACTIVE_MEDIATED"
EXECUTION_AUTHORITY = "HOLD_ONLY"

HELD = "HELD"
PASSTHROUGH = "PASSTHROUGH"
INTERVENTION_REJECTED = "INTERVENTION_REJECTED"

THIS_FILE = Path(__file__).resolve()
PROJECT_DIR = THIS_FILE.parents[1]
REPOSITORY_ROOT = THIS_FILE.parents[3]
AUTHORITY_PATH = PROJECT_DIR / "authority" / "bounded_authority_contract.py"
FROZEN_V01_ROOT = REPOSITORY_ROOT / "frozen" / "bolt_on" / "v0.1"


def _load_authority_module():
    module_name = "bolt_on_v02_bounded_authority_for_mediation"
    existing = sys.modules.get(module_name)
    if existing is not None:
        return existing
    spec = importlib.util.spec_from_file_location(module_name, AUTHORITY_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"could not load Stage 1 authority from {AUTHORITY_PATH}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


authority = _load_authority_module()
v01_governance = authority.v01_governance
ordinary_host = authority.ordinary_host

BOUND_SOURCE_PATHS = authority.V01_QUALIFIED_SOURCE_PATHS + (AUTHORITY_PATH, THIS_FILE)


@dataclass(frozen=True)
class HoldPermit:
    permit_id: str
    issuer: str
    mode: str
    action: str
    authority_digest: str
    grant_hash: str
    session_digest: str
    request_id: int
    job_ordinal: int
    job_id: str
    evidence_digest: str
    valid_epoch: int
    max_uses: int
    permit_hash: str

    def canonical_unsigned(self) -> str:
        return "|".join(
            (
                self.permit_id,
                self.issuer,
                self.mode,
                self.action,
                self.authority_digest,
                self.grant_hash,
                self.session_digest,
                str(self.request_id),
                str(self.job_ordinal),
                self.job_id,
                self.evidence_digest,
                str(self.valid_epoch),
                str(self.max_uses),
            )
        )


@dataclass(frozen=True)
class MediationOutcome:
    permit_id: str
    request_id: int
    job_ordinal: int
    job_id: str
    requested_action: str
    disposition: str
    executed: bool
    ternary: int
    reason_code: str

    def canonical_line(self) -> str:
        return "|".join(
            (
                self.permit_id,
                str(self.request_id),
                str(self.job_ordinal),
                self.job_id,
                self.requested_action,
                self.disposition,
                "1" if self.executed else "0",
                str(self.ternary),
                self.reason_code,
            )
        )


@dataclass(frozen=True)
class MediationReceipt:
    receipt_id: int
    kind: str
    subject: str
    payload: str
    prior_hash: str
    receipt_hash: str


@dataclass(frozen=True)
class MediationReplay:
    passed: bool
    final_digest: str
    checked_receipts: int
    first_error: str


@dataclass(frozen=True)
class MediatedHoldReport:
    authority_report: object
    permit: HoldPermit | None
    outcome: MediationOutcome
    direct_host_run: object
    mediated_host_run: object
    held_jobs: Tuple[object, ...]
    dispatched_jobs: Tuple[object, ...]
    consumed_permit_ids: Tuple[str, ...]
    receipts: Tuple[MediationReceipt, ...]
    replay: MediationReplay
    mediation_digest: str
    source_hashes: Tuple[Tuple[str, str], ...]
    frozen_v01_digest: str
    executed_actions: int


@dataclass(frozen=True)
class Stage2Qualification:
    passed: bool
    mode: str
    execution_authority: str
    active_hold_executed: bool
    exactly_one_action: bool
    hold_only_enforced: bool
    intended_delta_only: bool
    no_permit_passthrough: bool
    invalid_permit_passthrough: bool
    expired_permit_passthrough: bool
    reused_permit_passthrough: bool
    session_binding_pass: bool
    evidence_binding_pass: bool
    authority_binding_pass: bool
    unknown_abstention_pass: bool
    grant_scope_pass: bool
    authority_replay_pass: bool
    mediation_replay_pass: bool
    tamper_detection_pass: bool
    input_unchanged: bool
    sources_unchanged: bool
    frozen_v01_unchanged: bool
    safe_detach_pass: bool
    executed_actions: int
    held_job_ids: Tuple[str, ...]
    direct_host_digest: str
    mediated_host_digest: str
    authority_digest: str
    permit_hash: str
    mediation_digest: str
    frozen_v01_digest: str


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _snapshot_sources() -> Tuple[Tuple[str, str], ...]:
    return tuple(
        (path.relative_to(REPOSITORY_ROOT).as_posix(), _sha256_file(path))
        for path in BOUND_SOURCE_PATHS
    )


def _tree_digest(root: Path) -> str:
    if not root.is_dir():
        return "MISSING"
    lines = []
    for path in sorted(root.rglob("*")):
        if not path.is_file() or "__pycache__" in path.parts or path.suffix == ".pyc":
            continue
        relative = path.relative_to(root).as_posix()
        lines.append(f"{relative}|{_sha256_file(path)}")
    return _sha256_bytes("\n".join(lines).encode("utf-8"))


def _validate_exact_int(value: object, name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise TypeError(f"{name} must be an exact integer")
    return value


def prepare_hold_authority(
    jobs: Iterable[object], *, starting_value: int = 0, current_epoch: int = 200
):
    """Produce a one-action, HOLD-only Stage 1 advisory report."""

    current_epoch = _validate_exact_int(current_epoch, "current_epoch")
    return authority.run_dry_run_authority(
        tuple(jobs),
        starting_value=starting_value,
        current_epoch=current_epoch,
        allowed_actions=(authority.HOLD,),
        max_actions=1,
    )


def _permit_hash_from_fields(
    permit_id: str,
    issuer: str,
    mode: str,
    action: str,
    authority_digest: str,
    grant_hash: str,
    session_digest: str,
    request_id: int,
    job_ordinal: int,
    job_id: str,
    evidence_digest: str,
    valid_epoch: int,
    max_uses: int,
) -> str:
    unsigned = "|".join(
        (
            permit_id,
            issuer,
            mode,
            action,
            authority_digest,
            grant_hash,
            session_digest,
            str(request_id),
            str(job_ordinal),
            job_id,
            evidence_digest,
            str(valid_epoch),
            str(max_uses),
        )
    )
    return _sha256_bytes(unsigned.encode("utf-8"))


def issue_hold_permit(
    authority_report: object,
    *,
    current_epoch: int,
    issuer: str = "LOCAL_MEDIATED_HOLD_AUTHORITY",
) -> HoldPermit:
    """Issue one deterministic active permit for exactly one authorized HOLD."""

    current_epoch = _validate_exact_int(current_epoch, "current_epoch")
    if not isinstance(issuer, str) or not issuer.strip():
        raise ValueError("issuer must be a non-empty string")
    if not authority_report.replay.passed:
        raise ValueError("authority receipt replay must pass")
    if authority_report.replay.final_digest != authority_report.authority_digest:
        raise ValueError("authority terminal digest mismatch")

    grant_valid, reason = authority.validate_grant(authority_report.grant)
    if not grant_valid:
        raise ValueError(f"invalid Stage 1 grant: {reason}")
    if authority_report.grant.allowed_actions != (authority.HOLD,):
        raise ValueError("Stage 1 grant must be HOLD-only")
    if authority_report.grant.max_actions != 1:
        raise ValueError("Stage 1 grant must have an exact one-action budget")
    if not (
        authority_report.grant.valid_from_epoch
        <= current_epoch
        <= authority_report.grant.valid_through_epoch
    ):
        raise ValueError("Stage 1 grant is not valid at current_epoch")

    candidates = tuple(
        (request, outcome)
        for request, outcome in zip(
            authority_report.requests, authority_report.outcomes, strict=True
        )
        if request.requested_action == authority.HOLD
        and request.source_decision == v01_governance.DEFER
        and outcome.disposition == authority.WOULD_HOLD
        and outcome.would_authorize
        and not outcome.executed
    )
    if len(candidates) != 1:
        raise ValueError("exactly one authorized HOLD candidate is required")

    request, _ = candidates[0]
    seed = "|".join(
        (
            issuer.strip(),
            MODE,
            authority.HOLD,
            authority_report.authority_digest,
            authority_report.grant.grant_hash,
            authority_report.governance_report.governance_digest,
            str(request.request_id),
            str(request.job_ordinal),
            request.job_id,
            request.evidence_digest,
            str(current_epoch),
            "1",
        )
    )
    permit_id = "P-" + _sha256_bytes(seed.encode("utf-8"))[:20].upper()
    permit_hash = _permit_hash_from_fields(
        permit_id,
        issuer.strip(),
        MODE,
        authority.HOLD,
        authority_report.authority_digest,
        authority_report.grant.grant_hash,
        authority_report.governance_report.governance_digest,
        request.request_id,
        request.job_ordinal,
        request.job_id,
        request.evidence_digest,
        current_epoch,
        1,
    )
    return HoldPermit(
        permit_id=permit_id,
        issuer=issuer.strip(),
        mode=MODE,
        action=authority.HOLD,
        authority_digest=authority_report.authority_digest,
        grant_hash=authority_report.grant.grant_hash,
        session_digest=authority_report.governance_report.governance_digest,
        request_id=request.request_id,
        job_ordinal=request.job_ordinal,
        job_id=request.job_id,
        evidence_digest=request.evidence_digest,
        valid_epoch=current_epoch,
        max_uses=1,
        permit_hash=permit_hash,
    )


def validate_hold_permit(permit: HoldPermit) -> Tuple[bool, str]:
    if permit.mode != MODE:
        return False, "PERMIT_MODE_MISMATCH"
    if permit.action != authority.HOLD:
        return False, "NON_HOLD_ACTION_FORBIDDEN"
    if permit.max_uses != 1:
        return False, "PERMIT_NOT_SINGLE_USE"
    exact_int_fields = (
        permit.request_id,
        permit.job_ordinal,
        permit.valid_epoch,
        permit.max_uses,
    )
    if any(isinstance(value, bool) or not isinstance(value, int) for value in exact_int_fields):
        return False, "INVALID_INTEGER_FIELD"
    if permit.request_id < 1 or permit.job_ordinal < 1:
        return False, "INVALID_REQUEST_BINDING"
    digests = (
        permit.authority_digest,
        permit.grant_hash,
        permit.session_digest,
        permit.evidence_digest,
        permit.permit_hash,
    )
    if any(not isinstance(value, str) or len(value) != 64 for value in digests):
        return False, "INVALID_DIGEST_FIELD"
    expected = _permit_hash_from_fields(
        permit.permit_id,
        permit.issuer,
        permit.mode,
        permit.action,
        permit.authority_digest,
        permit.grant_hash,
        permit.session_digest,
        permit.request_id,
        permit.job_ordinal,
        permit.job_id,
        permit.evidence_digest,
        permit.valid_epoch,
        permit.max_uses,
    )
    if permit.permit_hash != expected:
        return False, "PERMIT_HASH_MISMATCH"
    return True, "VALID"


def _rejected_outcome(permit: HoldPermit | None, reason: str) -> MediationOutcome:
    return MediationOutcome(
        permit_id=permit.permit_id if permit is not None else "<NONE>",
        request_id=permit.request_id if permit is not None else 0,
        job_ordinal=permit.job_ordinal if permit is not None else 0,
        job_id=permit.job_id if permit is not None else "<NONE>",
        requested_action=permit.action if permit is not None else authority.HOLD,
        disposition=INTERVENTION_REJECTED,
        executed=False,
        ternary=0,
        reason_code=reason,
    )


def _validate_authority_evidence(
    jobs: Tuple[object, ...],
    authority_report: object,
    permit: HoldPermit,
    *,
    starting_value: int,
    current_epoch: int,
    consumed_permit_ids: Tuple[str, ...],
) -> Tuple[bool, str, object | None]:
    permit_valid, reason = validate_hold_permit(permit)
    if not permit_valid:
        return False, reason, None
    if permit.permit_id in consumed_permit_ids:
        return False, "PERMIT_ALREADY_CONSUMED", None
    if current_epoch != permit.valid_epoch:
        return False, "PERMIT_EPOCH_MISMATCH", None

    current_governance = v01_governance.run_shadow_governance(
        jobs, starting_value=starting_value
    )
    if not current_governance.replay.passed:
        return False, "CURRENT_GOVERNANCE_REPLAY_FAILED", None
    if permit.session_digest != current_governance.governance_digest:
        return False, "SESSION_DIGEST_MISMATCH", None
    if authority_report.governance_report.governance_digest != current_governance.governance_digest:
        return False, "STALE_AUTHORITY_SESSION", None
    if authority_report.authority_digest != permit.authority_digest:
        return False, "AUTHORITY_DIGEST_MISMATCH", None
    if authority_report.grant.grant_hash != permit.grant_hash:
        return False, "GRANT_HASH_BINDING_MISMATCH", None
    if not authority_report.replay.passed:
        return False, "AUTHORITY_REPLAY_FAILED", None
    if authority_report.replay.final_digest != authority_report.authority_digest:
        return False, "AUTHORITY_TERMINAL_DIGEST_MISMATCH", None

    grant_valid, grant_reason = authority.validate_grant(authority_report.grant)
    if not grant_valid:
        return False, grant_reason, None
    if authority_report.grant.allowed_actions != (authority.HOLD,):
        return False, "GRANT_NOT_HOLD_ONLY", None
    if authority_report.grant.max_actions != 1:
        return False, "GRANT_BUDGET_NOT_ONE", None
    if authority_report.grant.session_digest != current_governance.governance_digest:
        return False, "GRANT_SESSION_MISMATCH", None
    if not (
        authority_report.grant.valid_from_epoch
        <= current_epoch
        <= authority_report.grant.valid_through_epoch
    ):
        return False, "GRANT_EPOCH_INVALID", None

    expected_requests = authority.derive_requests(current_governance)
    if authority_report.requests != expected_requests:
        return False, "AUTHORITY_REQUEST_SET_MISMATCH", None
    expected_outcomes = authority.evaluate_requests(
        authority_report.grant,
        expected_requests,
        current_epoch=current_epoch,
        expected_session_digest=current_governance.governance_digest,
    )
    if authority_report.outcomes != expected_outcomes:
        return False, "AUTHORITY_OUTCOME_SET_MISMATCH", None

    matching = tuple(
        (request, outcome)
        for request, outcome in zip(expected_requests, expected_outcomes, strict=True)
        if request.request_id == permit.request_id
    )
    if len(matching) != 1:
        return False, "PERMIT_REQUEST_NOT_FOUND", None
    request, outcome = matching[0]
    if request.job_ordinal != permit.job_ordinal or request.job_id != permit.job_id:
        return False, "PERMIT_JOB_BINDING_MISMATCH", None
    if request.evidence_digest != permit.evidence_digest:
        return False, "PERMIT_EVIDENCE_MISMATCH", None
    if request.source_decision != v01_governance.DEFER:
        return False, "NON_DEFER_DECISION_CANNOT_HOLD", None
    if request.requested_action != authority.HOLD:
        return False, "REQUEST_NOT_HOLD", None
    if outcome.disposition != authority.WOULD_HOLD or not outcome.would_authorize:
        return False, "HOLD_NOT_AUTHORIZED", None
    if outcome.executed:
        return False, "STAGE1_OUTCOME_ALREADY_EXECUTED", None
    if not 1 <= permit.job_ordinal <= len(jobs):
        return False, "JOB_ORDINAL_OUT_OF_RANGE", None

    job = jobs[permit.job_ordinal - 1]
    display_id = job.job_id if isinstance(job.job_id, str) and job.job_id else "<EMPTY>"
    if display_id != permit.job_id:
        return False, "LIVE_JOB_ID_MISMATCH", None
    return True, "VALID", job


def _receipt_hash(
    receipt_id: int, kind: str, subject: str, payload: str, prior_hash: str
) -> str:
    unsigned = "|".join((str(receipt_id), kind, subject, payload, prior_hash))
    return _sha256_bytes(unsigned.encode("utf-8"))


def build_receipts(
    authority_report: object,
    permit: HoldPermit | None,
    outcome: MediationOutcome,
    direct_host_run: object,
    mediated_host_run: object,
    held_jobs: Sequence[object],
    dispatched_jobs: Sequence[object],
    consumed_permit_ids: Sequence[str],
    frozen_v01_digest: str,
) -> Tuple[MediationReceipt, ...]:
    receipts = []
    prior_hash = "0" * 64

    def append(kind: str, subject: str, payload: str) -> None:
        nonlocal prior_hash
        receipt_id = len(receipts) + 1
        receipt_hash = _receipt_hash(receipt_id, kind, subject, payload, prior_hash)
        receipts.append(
            MediationReceipt(
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
                f"execution_authority={EXECUTION_AUTHORITY}",
                f"authority_digest={authority_report.authority_digest}",
                f"frozen_v01_digest={frozen_v01_digest}",
            )
        ),
    )
    append(
        "PERMIT",
        permit.permit_id if permit is not None else "<NONE>",
        permit.canonical_unsigned() + "|" + permit.permit_hash
        if permit is not None
        else "NO_PERMIT",
    )
    append("OUTCOME", outcome.job_id, outcome.canonical_line())
    for ordinal, job in enumerate(held_jobs, start=1):
        append("HELD_JOB", f"HELD:{ordinal}", repr(job))
    append(
        "HOST",
        "DIRECT",
        f"digest={direct_host_run.run_digest};final={direct_host_run.final_value}",
    )
    append(
        "HOST",
        "MEDIATED",
        f"digest={mediated_host_run.run_digest};final={mediated_host_run.final_value}",
    )
    append(
        "SUMMARY",
        "CLOSE",
        ";".join(
            (
                f"input_jobs={len(held_jobs) + len(dispatched_jobs)}",
                f"dispatched_jobs={len(dispatched_jobs)}",
                f"held_jobs={len(held_jobs)}",
                f"executed_actions={1 if outcome.executed else 0}",
                f"consumed_permits={len(consumed_permit_ids)}",
            )
        ),
    )
    return tuple(receipts)


def replay_receipts(receipts: Sequence[MediationReceipt]) -> MediationReplay:
    prior_hash = "0" * 64
    for expected_id, receipt in enumerate(receipts, start=1):
        if receipt.receipt_id != expected_id:
            return MediationReplay(
                False,
                prior_hash,
                expected_id - 1,
                f"RECEIPT_ID_MISMATCH:{expected_id}:{receipt.receipt_id}",
            )
        if receipt.prior_hash != prior_hash:
            return MediationReplay(
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
            return MediationReplay(
                False,
                prior_hash,
                expected_id - 1,
                f"RECEIPT_HASH_MISMATCH:{expected_id}",
            )
        prior_hash = expected_hash
    return MediationReplay(True, prior_hash, len(receipts), "NONE")


def tamper_receipt(
    receipts: Sequence[MediationReceipt], index: int, replacement_payload: str
) -> Tuple[MediationReceipt, ...]:
    if not 0 <= index < len(receipts):
        raise IndexError("receipt index out of range")
    altered = list(receipts)
    altered[index] = replace(altered[index], payload=replacement_payload)
    return tuple(altered)


def mediate_with_hold(
    jobs: Iterable[object],
    authority_report: object,
    permit: HoldPermit | None,
    *,
    starting_value: int = 0,
    current_epoch: int = 200,
    consumed_permit_ids: Sequence[str] = (),
) -> MediatedHoldReport:
    """Apply at most one valid HOLD; otherwise pass the batch through exactly."""

    current_epoch = _validate_exact_int(current_epoch, "current_epoch")
    job_tuple = tuple(jobs)
    consumed_before = tuple(consumed_permit_ids)
    if len(set(consumed_before)) != len(consumed_before):
        raise ValueError("consumed_permit_ids cannot contain duplicates")

    source_hashes = _snapshot_sources()
    frozen_v01_digest = _tree_digest(FROZEN_V01_ROOT)
    direct_host_run = ordinary_host.run_jobs(job_tuple, starting_value=starting_value)

    if permit is None:
        valid, reason, held_job = False, "NO_ACTIVE_PERMIT", None
    else:
        valid, reason, held_job = _validate_authority_evidence(
            job_tuple,
            authority_report,
            permit,
            starting_value=starting_value,
            current_epoch=current_epoch,
            consumed_permit_ids=consumed_before,
        )

    if valid and held_job is not None and permit is not None:
        held_jobs = (held_job,)
        dispatched_jobs = tuple(
            job for ordinal, job in enumerate(job_tuple, start=1)
            if ordinal != permit.job_ordinal
        )
        mediated_host_run = ordinary_host.run_jobs(
            dispatched_jobs, starting_value=starting_value
        )
        consumed_after = consumed_before + (permit.permit_id,)
        outcome = MediationOutcome(
            permit_id=permit.permit_id,
            request_id=permit.request_id,
            job_ordinal=permit.job_ordinal,
            job_id=permit.job_id,
            requested_action=permit.action,
            disposition=HELD,
            executed=True,
            ternary=0,
            reason_code="AUTHORIZED_HOLD_EXECUTED",
        )
    else:
        held_jobs = ()
        dispatched_jobs = job_tuple
        mediated_host_run = direct_host_run
        consumed_after = consumed_before
        outcome = _rejected_outcome(permit, reason)

    receipts = build_receipts(
        authority_report,
        permit,
        outcome,
        direct_host_run,
        mediated_host_run,
        held_jobs,
        dispatched_jobs,
        consumed_after,
        frozen_v01_digest,
    )
    replay = replay_receipts(receipts)
    mediation_digest = receipts[-1].receipt_hash if receipts else "0" * 64
    return MediatedHoldReport(
        authority_report=authority_report,
        permit=permit,
        outcome=outcome,
        direct_host_run=direct_host_run,
        mediated_host_run=mediated_host_run,
        held_jobs=held_jobs,
        dispatched_jobs=dispatched_jobs,
        consumed_permit_ids=consumed_after,
        receipts=receipts,
        replay=replay,
        mediation_digest=mediation_digest,
        source_hashes=source_hashes,
        frozen_v01_digest=frozen_v01_digest,
        executed_actions=1 if outcome.executed else 0,
    )


def run_baseline_active_hold(
    jobs: Iterable[object], *, starting_value: int = 0, current_epoch: int = 200
) -> MediatedHoldReport:
    job_tuple = tuple(jobs)
    advisory = prepare_hold_authority(
        job_tuple, starting_value=starting_value, current_epoch=current_epoch
    )
    permit = issue_hold_permit(advisory, current_epoch=current_epoch)
    return mediate_with_hold(
        job_tuple,
        advisory,
        permit,
        starting_value=starting_value,
        current_epoch=current_epoch,
    )


def qualify_stage2(
    jobs: Iterable[object], *, starting_value: int = 0, current_epoch: int = 200
) -> Stage2Qualification:
    job_tuple = tuple(jobs)
    input_before = repr(job_tuple)
    sources_before = _snapshot_sources()
    frozen_before = _tree_digest(FROZEN_V01_ROOT)

    advisory = prepare_hold_authority(
        job_tuple, starting_value=starting_value, current_epoch=current_epoch
    )
    permit = issue_hold_permit(advisory, current_epoch=current_epoch)
    active = mediate_with_hold(
        job_tuple,
        advisory,
        permit,
        starting_value=starting_value,
        current_epoch=current_epoch,
    )

    no_permit = mediate_with_hold(
        job_tuple,
        advisory,
        None,
        starting_value=starting_value,
        current_epoch=current_epoch,
    )
    tampered_permit = replace(permit, job_id="TAMPERED")
    invalid_permit = mediate_with_hold(
        job_tuple,
        advisory,
        tampered_permit,
        starting_value=starting_value,
        current_epoch=current_epoch,
    )
    expired = mediate_with_hold(
        job_tuple,
        advisory,
        permit,
        starting_value=starting_value,
        current_epoch=current_epoch + 1,
    )
    reused = mediate_with_hold(
        job_tuple,
        advisory,
        permit,
        starting_value=starting_value,
        current_epoch=current_epoch,
        consumed_permit_ids=active.consumed_permit_ids,
    )

    wrong_session_permit = replace(
        permit,
        session_digest="f" * 64,
        permit_hash="0" * 64,
    )
    wrong_session_permit = replace(
        wrong_session_permit,
        permit_hash=_permit_hash_from_fields(
            wrong_session_permit.permit_id,
            wrong_session_permit.issuer,
            wrong_session_permit.mode,
            wrong_session_permit.action,
            wrong_session_permit.authority_digest,
            wrong_session_permit.grant_hash,
            wrong_session_permit.session_digest,
            wrong_session_permit.request_id,
            wrong_session_permit.job_ordinal,
            wrong_session_permit.job_id,
            wrong_session_permit.evidence_digest,
            wrong_session_permit.valid_epoch,
            wrong_session_permit.max_uses,
        ),
    )
    wrong_session = mediate_with_hold(
        job_tuple,
        advisory,
        wrong_session_permit,
        starting_value=starting_value,
        current_epoch=current_epoch,
    )

    wrong_evidence_permit = replace(
        permit,
        evidence_digest="e" * 64,
        permit_hash="0" * 64,
    )
    wrong_evidence_permit = replace(
        wrong_evidence_permit,
        permit_hash=_permit_hash_from_fields(
            wrong_evidence_permit.permit_id,
            wrong_evidence_permit.issuer,
            wrong_evidence_permit.mode,
            wrong_evidence_permit.action,
            wrong_evidence_permit.authority_digest,
            wrong_evidence_permit.grant_hash,
            wrong_evidence_permit.session_digest,
            wrong_evidence_permit.request_id,
            wrong_evidence_permit.job_ordinal,
            wrong_evidence_permit.job_id,
            wrong_evidence_permit.evidence_digest,
            wrong_evidence_permit.valid_epoch,
            wrong_evidence_permit.max_uses,
        ),
    )
    wrong_evidence = mediate_with_hold(
        job_tuple,
        advisory,
        wrong_evidence_permit,
        starting_value=starting_value,
        current_epoch=current_epoch,
    )

    wrong_authority_permit = replace(
        permit,
        authority_digest="a" * 64,
        permit_hash="0" * 64,
    )
    wrong_authority_permit = replace(
        wrong_authority_permit,
        permit_hash=_permit_hash_from_fields(
            wrong_authority_permit.permit_id,
            wrong_authority_permit.issuer,
            wrong_authority_permit.mode,
            wrong_authority_permit.action,
            wrong_authority_permit.authority_digest,
            wrong_authority_permit.grant_hash,
            wrong_authority_permit.session_digest,
            wrong_authority_permit.request_id,
            wrong_authority_permit.job_ordinal,
            wrong_authority_permit.job_id,
            wrong_authority_permit.evidence_digest,
            wrong_authority_permit.valid_epoch,
            wrong_authority_permit.max_uses,
        ),
    )
    wrong_authority = mediate_with_hold(
        job_tuple,
        advisory,
        wrong_authority_permit,
        starting_value=starting_value,
        current_epoch=current_epoch,
    )

    non_hold_permit = replace(
        permit,
        action=authority.ALLOW,
        permit_hash="0" * 64,
    )
    non_hold_permit = replace(
        non_hold_permit,
        permit_hash=_permit_hash_from_fields(
            non_hold_permit.permit_id,
            non_hold_permit.issuer,
            non_hold_permit.mode,
            non_hold_permit.action,
            non_hold_permit.authority_digest,
            non_hold_permit.grant_hash,
            non_hold_permit.session_digest,
            non_hold_permit.request_id,
            non_hold_permit.job_ordinal,
            non_hold_permit.job_id,
            non_hold_permit.evidence_digest,
            non_hold_permit.valid_epoch,
            non_hold_permit.max_uses,
        ),
    )
    non_hold = mediate_with_hold(
        job_tuple,
        advisory,
        non_hold_permit,
        starting_value=starting_value,
        current_epoch=current_epoch,
    )

    # A request changed to UNKNOWN invalidates the authoritative request set and
    # therefore cannot execute.
    unknown_request = replace(
        advisory.requests[permit.request_id - 1],
        source_decision=v01_governance.UNKNOWN,
        requested_action=authority.ABSTAIN,
        source_ternary=0,
    )
    altered_requests = list(advisory.requests)
    altered_requests[permit.request_id - 1] = unknown_request
    unknown_advisory = replace(advisory, requests=tuple(altered_requests))
    unknown_result = mediate_with_hold(
        job_tuple,
        unknown_advisory,
        permit,
        starting_value=starting_value,
        current_epoch=current_epoch,
    )

    direct = active.direct_host_run
    detached = ordinary_host.run_jobs(job_tuple, starting_value=starting_value)
    source_after = _snapshot_sources()
    frozen_after = _tree_digest(FROZEN_V01_ROOT)

    intended_delta_only = (
        active.mediated_host_run.final_value == direct.final_value
        and active.mediated_host_run.completed_ids == direct.completed_ids
        and active.mediated_host_run.rejected_ids == direct.rejected_ids
        and active.held_jobs == (job_tuple[permit.job_ordinal - 1],)
        and permit.job_id in direct.delayed_ids
        and permit.job_id not in active.mediated_host_run.delayed_ids
        and len(active.dispatched_jobs) == len(job_tuple) - 1
    )

    passthrough_reports = (
        no_permit,
        invalid_permit,
        expired,
        reused,
        wrong_session,
        wrong_evidence,
        wrong_authority,
        non_hold,
        unknown_result,
    )
    all_passthrough_exact = all(
        report.executed_actions == 0
        and report.held_jobs == ()
        and report.mediated_host_run == direct
        for report in passthrough_reports
    )

    tampered_receipts = tamper_receipt(active.receipts, 2, "tampered")
    tamper_detection = not replay_receipts(tampered_receipts).passed

    passed = all(
        (
            active.executed_actions == 1,
            active.outcome.disposition == HELD,
            active.outcome.requested_action == authority.HOLD,
            len(active.held_jobs) == 1,
            intended_delta_only,
            all_passthrough_exact,
            wrong_session.outcome.reason_code == "SESSION_DIGEST_MISMATCH",
            wrong_evidence.outcome.reason_code == "PERMIT_EVIDENCE_MISMATCH",
            wrong_authority.outcome.reason_code == "AUTHORITY_DIGEST_MISMATCH",
            non_hold.outcome.reason_code == "NON_HOLD_ACTION_FORBIDDEN",
            unknown_result.executed_actions == 0,
            advisory.replay.passed,
            active.replay.passed,
            active.replay.final_digest == active.mediation_digest,
            tamper_detection,
            repr(job_tuple) == input_before,
            source_after == sources_before,
            frozen_after == frozen_before,
            detached == direct,
        )
    )

    return Stage2Qualification(
        passed=passed,
        mode=MODE,
        execution_authority=EXECUTION_AUTHORITY,
        active_hold_executed=active.executed_actions == 1,
        exactly_one_action=active.executed_actions == 1 and len(active.held_jobs) == 1,
        hold_only_enforced=non_hold.executed_actions == 0,
        intended_delta_only=intended_delta_only,
        no_permit_passthrough=no_permit.mediated_host_run == direct,
        invalid_permit_passthrough=invalid_permit.mediated_host_run == direct,
        expired_permit_passthrough=expired.mediated_host_run == direct,
        reused_permit_passthrough=reused.mediated_host_run == direct,
        session_binding_pass=wrong_session.outcome.reason_code == "SESSION_DIGEST_MISMATCH",
        evidence_binding_pass=wrong_evidence.outcome.reason_code == "PERMIT_EVIDENCE_MISMATCH",
        authority_binding_pass=wrong_authority.outcome.reason_code == "AUTHORITY_DIGEST_MISMATCH",
        unknown_abstention_pass=unknown_result.executed_actions == 0,
        grant_scope_pass=advisory.grant.allowed_actions == (authority.HOLD,)
        and advisory.grant.max_actions == 1,
        authority_replay_pass=advisory.replay.passed,
        mediation_replay_pass=active.replay.passed,
        tamper_detection_pass=tamper_detection,
        input_unchanged=repr(job_tuple) == input_before,
        sources_unchanged=source_after == sources_before,
        frozen_v01_unchanged=frozen_after == frozen_before,
        safe_detach_pass=detached == direct,
        executed_actions=active.executed_actions,
        held_job_ids=tuple(
            job.job_id if isinstance(job.job_id, str) and job.job_id else "<EMPTY>"
            for job in active.held_jobs
        ),
        direct_host_digest=direct.run_digest,
        mediated_host_digest=active.mediated_host_run.run_digest,
        authority_digest=advisory.authority_digest,
        permit_hash=permit.permit_hash,
        mediation_digest=active.mediation_digest,
        frozen_v01_digest=frozen_before,
    )


def print_qualification(result: Stage2Qualification) -> None:
    print("=" * 88)
    print(f"{INTERFACE_NAME} v{INTERFACE_VERSION}")
    print("=" * 88)
    print(f"Mode / execution authority:      {result.mode} / {result.execution_authority}")
    print(f"Active HOLD executed:            {result.active_hold_executed}")
    print(f"Exactly one action:              {result.exactly_one_action}")
    print(f"HOLD-only enforced:              {result.hold_only_enforced}")
    print(f"Intended delta only:             {result.intended_delta_only}")
    print(f"No-permit passthrough:           {result.no_permit_passthrough}")
    print(f"Invalid-permit passthrough:      {result.invalid_permit_passthrough}")
    print(f"Expired-permit passthrough:      {result.expired_permit_passthrough}")
    print(f"Reused-permit passthrough:       {result.reused_permit_passthrough}")
    print(f"Session binding:                 {result.session_binding_pass}")
    print(f"Evidence binding:                {result.evidence_binding_pass}")
    print(f"Authority binding:               {result.authority_binding_pass}")
    print(f"UNKNOWN abstention:              {result.unknown_abstention_pass}")
    print(f"Grant scope / budget:            {result.grant_scope_pass}")
    print(f"Authority replay:                {result.authority_replay_pass}")
    print(f"Mediation replay:                {result.mediation_replay_pass}")
    print(f"Tamper detection:                {result.tamper_detection_pass}")
    print(f"Input unchanged:                 {result.input_unchanged}")
    print(f"Qualified sources unchanged:     {result.sources_unchanged}")
    print(f"Frozen v0.1 unchanged:           {result.frozen_v01_unchanged}")
    print(f"Safe detach:                     {result.safe_detach_pass}")
    print(f"Executed actions:                {result.executed_actions}")
    print(f"Held job IDs:                    {result.held_job_ids}")
    print(f"Direct host digest:              {result.direct_host_digest}")
    print(f"Mediated host digest:            {result.mediated_host_digest}")
    print(f"Authority digest:                {result.authority_digest}")
    print(f"Permit hash:                     {result.permit_hash}")
    print(f"Mediation digest:                {result.mediation_digest}")
    print(f"Frozen v0.1 digest:              {result.frozen_v01_digest}")
    print(
        "STAGE 2 MEDIATED HOLD QUALIFICATION: "
        + ("PASS" if result.passed else "FAIL")
    )


def main() -> None:
    result = qualify_stage2(ordinary_host.baseline_jobs())
    print_qualification(result)
    if not result.passed:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
