#!/usr/bin/env python3
"""Bounded authority contract for Bolt-On Demonstrator v0.2, Stage 1.

This stage defines an explicit, deterministic, deny-by-default authority
boundary around the qualified v0.1 shadow stack. It evaluates what an active
execution gate *would* authorize, but it does not execute, suppress, reorder,
replace, or modify host jobs.

Contract properties
-------------------
- standard-library-only;
- exact integer epochs and action budgets;
- immutable grants, requests, outcomes, and receipts;
- grants are bound to one governance-session digest;
- grants have explicit scope, validity window, and maximum action count;
- UNKNOWN always abstains;
- missing, invalid, expired, tampered, or out-of-scope grants fail closed;
- deterministic replay and receipt-tamper detection;
- zero host intervention in Stage 1.

The SHA-256 grant hash is an integrity binding for this prototype. It is not a
production digital signature or identity-authentication mechanism.
"""

from __future__ import annotations

import hashlib
import importlib.util
from dataclasses import dataclass, replace
from pathlib import Path
import sys
from typing import Iterable, Sequence, Tuple

# Do not create __pycache__ files inside any imported qualified/frozen tree.
sys.dont_write_bytecode = True

INTERFACE_NAME = "BOUNDED AUTHORITY CONTRACT"
INTERFACE_VERSION = "0.2.1"
MODE = "DRY_RUN"
EXECUTION_AUTHORITY = "NONE"

ALLOW = "ALLOW"
HOLD = "HOLD"
DENY = "DENY"
ABSTAIN = "ABSTAIN"
VALID_ACTIONS = (ALLOW, HOLD, DENY)

WOULD_ALLOW = "WOULD_ALLOW"
WOULD_HOLD = "WOULD_HOLD"
WOULD_DENY = "WOULD_DENY"
REJECTED = "REJECTED"

THIS_FILE = Path(__file__).resolve()
PROJECT_DIR = THIS_FILE.parents[1]
REPOSITORY_ROOT = THIS_FILE.parents[3]
V01_PROJECT = REPOSITORY_ROOT / "development" / "bolt_on_demonstrator_v0_1"
V01_GOVERNANCE_PATH = (
    V01_PROJECT / "governance" / "natural_math_shadow_governance.py"
)
FROZEN_V01_ROOT = REPOSITORY_ROOT / "frozen" / "bolt_on" / "v0.1"

V01_QUALIFIED_SOURCE_PATHS = (
    V01_PROJECT / "host" / "ordinary_host.py",
    V01_PROJECT / "adapter" / "bolt_on_adapter.py",
    V01_PROJECT / "governance" / "natural_math_shadow_governance.py",
    V01_PROJECT / "memory" / "cntm_shadow_memory.py",
    V01_PROJECT / "qualification" / "integrated_adversarial_qualification.py",
)


def _load_v01_governance():
    module_name = "bolt_on_v01_shadow_governance_for_v02"
    existing = sys.modules.get(module_name)
    if existing is not None:
        return existing
    spec = importlib.util.spec_from_file_location(module_name, V01_GOVERNANCE_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError(
            f"could not load qualified v0.1 governance from {V01_GOVERNANCE_PATH}"
        )
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


v01_governance = _load_v01_governance()
ordinary_host = v01_governance.ordinary_host


@dataclass(frozen=True)
class AuthorityGrant:
    grant_id: str
    issuer: str
    mode: str
    session_digest: str
    allowed_actions: Tuple[str, ...]
    max_actions: int
    valid_from_epoch: int
    valid_through_epoch: int
    grant_hash: str

    def canonical_unsigned(self) -> str:
        return "|".join(
            (
                self.grant_id,
                self.issuer,
                self.mode,
                self.session_digest,
                ",".join(self.allowed_actions),
                str(self.max_actions),
                str(self.valid_from_epoch),
                str(self.valid_through_epoch),
            )
        )


@dataclass(frozen=True)
class InterventionRequest:
    request_id: int
    job_ordinal: int
    job_id: str
    source_decision: str
    requested_action: str
    source_ternary: int
    evidence_digest: str

    def canonical_line(self) -> str:
        return "|".join(
            (
                str(self.request_id),
                str(self.job_ordinal),
                self.job_id,
                self.source_decision,
                self.requested_action,
                str(self.source_ternary),
                self.evidence_digest,
            )
        )


@dataclass(frozen=True)
class GateOutcome:
    request_id: int
    job_id: str
    requested_action: str
    disposition: str
    would_authorize: bool
    executed: bool
    ternary: int
    reason_code: str

    def canonical_line(self) -> str:
        return "|".join(
            (
                str(self.request_id),
                self.job_id,
                self.requested_action,
                self.disposition,
                "1" if self.would_authorize else "0",
                "1" if self.executed else "0",
                str(self.ternary),
                self.reason_code,
            )
        )


@dataclass(frozen=True)
class AuthorityReceipt:
    receipt_id: int
    kind: str
    subject: str
    payload: str
    prior_hash: str
    receipt_hash: str


@dataclass(frozen=True)
class AuthorityReplay:
    passed: bool
    final_digest: str
    checked_receipts: int
    first_error: str


@dataclass(frozen=True)
class DryRunAuthorityReport:
    governance_report: object
    grant: AuthorityGrant
    requests: Tuple[InterventionRequest, ...]
    outcomes: Tuple[GateOutcome, ...]
    receipts: Tuple[AuthorityReceipt, ...]
    replay: AuthorityReplay
    authority_digest: str
    host_source_hashes: Tuple[Tuple[str, str], ...]
    frozen_v01_digest: str
    executed_actions: int


@dataclass(frozen=True)
class Stage1Qualification:
    passed: bool
    mode: str
    execution_authority: str
    host_output_equivalent: bool
    host_digest_equivalent: bool
    v01_sources_unchanged: bool
    frozen_v01_unchanged: bool
    input_unchanged: bool
    governance_replay_pass: bool
    authority_replay_pass: bool
    deny_by_default_pass: bool
    grant_integrity_pass: bool
    session_binding_pass: bool
    scope_enforced: bool
    budget_enforced: bool
    validity_window_enforced: bool
    unknown_abstention_pass: bool
    tamper_detection_pass: bool
    executed_actions: int
    request_count: int
    would_authorize_count: int
    action_counts: Tuple[Tuple[str, int], ...]
    host_digest: str
    governance_digest: str
    grant_hash: str
    authority_digest: str
    frozen_v01_digest: str


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _sha256_file(path: Path) -> str:
    if not path.is_file():
        raise FileNotFoundError(f"required file is missing: {path}")
    return _sha256_bytes(path.read_bytes())


def _snapshot_sources() -> Tuple[Tuple[str, str], ...]:
    return tuple(
        (path.relative_to(REPOSITORY_ROOT).as_posix(), _sha256_file(path))
        for path in V01_QUALIFIED_SOURCE_PATHS
    )


def _tree_digest(root: Path) -> str:
    if not root.is_dir():
        raise FileNotFoundError(f"required frozen release is missing: {root}")
    lines = []
    for path in sorted(item for item in root.rglob("*") if item.is_file()):
        if "__pycache__" in path.parts or path.suffix == ".pyc":
            continue
        relative = path.relative_to(root).as_posix()
        lines.append(f"{_sha256_file(path)}  {relative}")
    if not lines:
        raise RuntimeError(f"frozen release contains no files: {root}")
    return _sha256_bytes("\n".join(lines).encode("utf-8"))


def _validate_exact_int(value: object, name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise TypeError(f"{name} must be an integer")
    return value


def _grant_hash_from_fields(
    grant_id: str,
    issuer: str,
    mode: str,
    session_digest: str,
    allowed_actions: Sequence[str],
    max_actions: int,
    valid_from_epoch: int,
    valid_through_epoch: int,
) -> str:
    unsigned = "|".join(
        (
            grant_id,
            issuer,
            mode,
            session_digest,
            ",".join(allowed_actions),
            str(max_actions),
            str(valid_from_epoch),
            str(valid_through_epoch),
        )
    )
    return _sha256_bytes(unsigned.encode("utf-8"))


def issue_grant(
    session_digest: str,
    *,
    issuer: str = "LOCAL_QUALIFICATION_AUTHORITY",
    allowed_actions: Sequence[str] = VALID_ACTIONS,
    max_actions: int = 8,
    valid_from_epoch: int = 100,
    valid_through_epoch: int = 100,
) -> AuthorityGrant:
    """Issue one deterministic dry-run grant bound to one session digest."""

    if not isinstance(session_digest, str) or len(session_digest) != 64:
        raise ValueError("session_digest must be a 64-character digest")
    if not isinstance(issuer, str) or not issuer.strip():
        raise ValueError("issuer must be a non-empty string")
    max_actions = _validate_exact_int(max_actions, "max_actions")
    valid_from_epoch = _validate_exact_int(valid_from_epoch, "valid_from_epoch")
    valid_through_epoch = _validate_exact_int(
        valid_through_epoch, "valid_through_epoch"
    )
    if max_actions < 0:
        raise ValueError("max_actions cannot be negative")
    if valid_from_epoch > valid_through_epoch:
        raise ValueError("valid_from_epoch cannot exceed valid_through_epoch")

    normalized = tuple(action.strip().upper() for action in allowed_actions)
    if len(set(normalized)) != len(normalized):
        raise ValueError("allowed_actions cannot contain duplicates")
    if any(action not in VALID_ACTIONS for action in normalized):
        raise ValueError("allowed_actions contains an unsupported action")
    normalized = tuple(action for action in VALID_ACTIONS if action in normalized)

    seed = "|".join(
        (
            issuer.strip(),
            MODE,
            session_digest,
            ",".join(normalized),
            str(max_actions),
            str(valid_from_epoch),
            str(valid_through_epoch),
        )
    )
    grant_id = "G-" + _sha256_bytes(seed.encode("utf-8"))[:20].upper()
    grant_hash = _grant_hash_from_fields(
        grant_id,
        issuer.strip(),
        MODE,
        session_digest,
        normalized,
        max_actions,
        valid_from_epoch,
        valid_through_epoch,
    )
    return AuthorityGrant(
        grant_id=grant_id,
        issuer=issuer.strip(),
        mode=MODE,
        session_digest=session_digest,
        allowed_actions=normalized,
        max_actions=max_actions,
        valid_from_epoch=valid_from_epoch,
        valid_through_epoch=valid_through_epoch,
        grant_hash=grant_hash,
    )


def validate_grant(grant: AuthorityGrant) -> Tuple[bool, str]:
    if grant.mode != MODE:
        return False, "MODE_NOT_DRY_RUN"
    if not isinstance(grant.session_digest, str) or len(grant.session_digest) != 64:
        return False, "INVALID_SESSION_DIGEST"
    if isinstance(grant.max_actions, bool) or not isinstance(grant.max_actions, int):
        return False, "INVALID_ACTION_BUDGET"
    if grant.max_actions < 0:
        return False, "NEGATIVE_ACTION_BUDGET"
    if (
        isinstance(grant.valid_from_epoch, bool)
        or not isinstance(grant.valid_from_epoch, int)
        or isinstance(grant.valid_through_epoch, bool)
        or not isinstance(grant.valid_through_epoch, int)
    ):
        return False, "INVALID_VALIDITY_WINDOW"
    if grant.valid_from_epoch > grant.valid_through_epoch:
        return False, "INVERTED_VALIDITY_WINDOW"
    if len(set(grant.allowed_actions)) != len(grant.allowed_actions):
        return False, "DUPLICATE_ACTION_SCOPE"
    if any(action not in VALID_ACTIONS for action in grant.allowed_actions):
        return False, "UNSUPPORTED_ACTION_SCOPE"
    expected = _grant_hash_from_fields(
        grant.grant_id,
        grant.issuer,
        grant.mode,
        grant.session_digest,
        grant.allowed_actions,
        grant.max_actions,
        grant.valid_from_epoch,
        grant.valid_through_epoch,
    )
    if grant.grant_hash != expected:
        return False, "GRANT_HASH_MISMATCH"
    return True, "VALID"


def _action_for_decision(decision: str) -> str:
    return {
        v01_governance.PROCEED: ALLOW,
        v01_governance.DEFER: HOLD,
        v01_governance.RESTRICT: DENY,
        v01_governance.UNKNOWN: ABSTAIN,
    }.get(decision, ABSTAIN)


def derive_requests(governance_report: object) -> Tuple[InterventionRequest, ...]:
    requests = []
    for request_id, decision in enumerate(governance_report.decisions, start=1):
        evidence_digest = _sha256_bytes(
            "|".join(
                (
                    governance_report.governance_digest,
                    decision.canonical_line(),
                )
            ).encode("utf-8")
        )
        requests.append(
            InterventionRequest(
                request_id=request_id,
                job_ordinal=decision.ordinal,
                job_id=decision.job_id,
                source_decision=decision.decision,
                requested_action=_action_for_decision(decision.decision),
                source_ternary=decision.ternary,
                evidence_digest=evidence_digest,
            )
        )
    return tuple(requests)


def _rejected_outcome(request: InterventionRequest, reason: str) -> GateOutcome:
    return GateOutcome(
        request_id=request.request_id,
        job_id=request.job_id,
        requested_action=request.requested_action,
        disposition=REJECTED,
        would_authorize=False,
        executed=False,
        ternary=0,
        reason_code=reason,
    )


def evaluate_requests(
    grant: AuthorityGrant | None,
    requests: Sequence[InterventionRequest],
    *,
    current_epoch: int,
    expected_session_digest: str,
) -> Tuple[GateOutcome, ...]:
    """Evaluate requests without executing them. Missing authority fails closed."""

    current_epoch = _validate_exact_int(current_epoch, "current_epoch")
    request_tuple = tuple(requests)

    if grant is None:
        return tuple(_rejected_outcome(request, "NO_GRANT") for request in request_tuple)

    valid, validation_reason = validate_grant(grant)
    if not valid:
        return tuple(
            _rejected_outcome(request, validation_reason) for request in request_tuple
        )
    if grant.session_digest != expected_session_digest:
        return tuple(
            _rejected_outcome(request, "SESSION_DIGEST_MISMATCH")
            for request in request_tuple
        )
    if current_epoch < grant.valid_from_epoch:
        return tuple(
            _rejected_outcome(request, "GRANT_NOT_YET_VALID")
            for request in request_tuple
        )
    if current_epoch > grant.valid_through_epoch:
        return tuple(
            _rejected_outcome(request, "GRANT_EXPIRED") for request in request_tuple
        )

    counts: dict[int, int] = {}
    for request in request_tuple:
        counts[request.request_id] = counts.get(request.request_id, 0) + 1

    outcomes = []
    authorized_count = 0
    for expected_id, request in enumerate(request_tuple, start=1):
        if request.request_id != expected_id:
            outcomes.append(_rejected_outcome(request, "REQUEST_SEQUENCE_MISMATCH"))
            continue
        if counts[request.request_id] > 1:
            outcomes.append(_rejected_outcome(request, "DUPLICATE_REQUEST_ID"))
            continue
        if request.requested_action == ABSTAIN or request.source_decision == v01_governance.UNKNOWN:
            outcomes.append(
                GateOutcome(
                    request_id=request.request_id,
                    job_id=request.job_id,
                    requested_action=ABSTAIN,
                    disposition=ABSTAIN,
                    would_authorize=False,
                    executed=False,
                    ternary=0,
                    reason_code="UNKNOWN_MUST_ABSTAIN",
                )
            )
            continue
        if request.requested_action not in VALID_ACTIONS:
            outcomes.append(_rejected_outcome(request, "UNSUPPORTED_REQUEST_ACTION"))
            continue
        if request.requested_action not in grant.allowed_actions:
            outcomes.append(_rejected_outcome(request, "ACTION_OUT_OF_SCOPE"))
            continue
        if authorized_count >= grant.max_actions:
            outcomes.append(_rejected_outcome(request, "ACTION_BUDGET_EXHAUSTED"))
            continue

        disposition = {
            ALLOW: WOULD_ALLOW,
            HOLD: WOULD_HOLD,
            DENY: WOULD_DENY,
        }[request.requested_action]
        ternary = {ALLOW: 1, HOLD: 0, DENY: -1}[request.requested_action]
        outcomes.append(
            GateOutcome(
                request_id=request.request_id,
                job_id=request.job_id,
                requested_action=request.requested_action,
                disposition=disposition,
                would_authorize=True,
                executed=False,
                ternary=ternary,
                reason_code="WITHIN_BOUND_AUTHORITY",
            )
        )
        authorized_count += 1

    return tuple(outcomes)


def _receipt_hash(
    receipt_id: int,
    kind: str,
    subject: str,
    payload: str,
    prior_hash: str,
) -> str:
    unsigned = "|".join((str(receipt_id), kind, subject, payload, prior_hash))
    return _sha256_bytes(unsigned.encode("utf-8"))


def build_receipts(
    governance_report: object,
    grant: AuthorityGrant,
    requests: Sequence[InterventionRequest],
    outcomes: Sequence[GateOutcome],
    frozen_v01_digest: str,
) -> Tuple[AuthorityReceipt, ...]:
    receipts = []
    prior_hash = "0" * 64

    def append(kind: str, subject: str, payload: str) -> None:
        nonlocal prior_hash
        receipt_id = len(receipts) + 1
        receipt_hash = _receipt_hash(
            receipt_id, kind, subject, payload, prior_hash
        )
        receipts.append(
            AuthorityReceipt(
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
                f"host_digest={governance_report.observation_report.host_run.run_digest}",
                f"governance_digest={governance_report.governance_digest}",
                "frozen_v01_verified=1",
            )
        ),
    )
    append("GRANT", grant.grant_id, grant.canonical_unsigned() + "|" + grant.grant_hash)
    for request, outcome in zip(requests, outcomes, strict=True):
        append("REQUEST", f"REQUEST:{request.request_id}", request.canonical_line())
        append("OUTCOME", f"REQUEST:{request.request_id}", outcome.canonical_line())
    append(
        "SUMMARY",
        "DRY_RUN",
        ";".join(
            (
                f"requests={len(requests)}",
                f"would_authorize={sum(1 for item in outcomes if item.would_authorize)}",
                f"abstained={sum(1 for item in outcomes if item.disposition == ABSTAIN)}",
                f"rejected={sum(1 for item in outcomes if item.disposition == REJECTED)}",
                "executed_actions=0",
            )
        ),
    )
    return tuple(receipts)


def replay_receipts(receipts: Sequence[AuthorityReceipt]) -> AuthorityReplay:
    prior_hash = "0" * 64
    for expected_id, receipt in enumerate(receipts, start=1):
        if receipt.receipt_id != expected_id:
            return AuthorityReplay(
                False,
                prior_hash,
                expected_id - 1,
                f"RECEIPT_ID_MISMATCH:{expected_id}:{receipt.receipt_id}",
            )
        if receipt.prior_hash != prior_hash:
            return AuthorityReplay(
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
            return AuthorityReplay(
                False,
                prior_hash,
                expected_id - 1,
                f"RECEIPT_HASH_MISMATCH:{expected_id}",
            )
        prior_hash = expected_hash
    return AuthorityReplay(True, prior_hash, len(receipts), "NONE")


def tamper_receipt(
    receipts: Sequence[AuthorityReceipt], index: int, replacement_payload: str
) -> Tuple[AuthorityReceipt, ...]:
    if not 0 <= index < len(receipts):
        raise IndexError("receipt index out of range")
    altered = list(receipts)
    altered[index] = replace(altered[index], payload=replacement_payload)
    return tuple(altered)


def run_dry_run_authority(
    jobs: Iterable[object],
    *,
    starting_value: int = 0,
    current_epoch: int = 100,
    allowed_actions: Sequence[str] = VALID_ACTIONS,
    max_actions: int = 8,
) -> DryRunAuthorityReport:
    original_jobs = tuple(jobs)
    source_hashes = _snapshot_sources()
    frozen_v01_digest = _tree_digest(FROZEN_V01_ROOT)
    governance_report = v01_governance.run_shadow_governance(
        original_jobs, starting_value=starting_value
    )
    grant = issue_grant(
        governance_report.governance_digest,
        allowed_actions=allowed_actions,
        max_actions=max_actions,
        valid_from_epoch=current_epoch,
        valid_through_epoch=current_epoch,
    )
    requests = derive_requests(governance_report)
    outcomes = evaluate_requests(
        grant,
        requests,
        current_epoch=current_epoch,
        expected_session_digest=governance_report.governance_digest,
    )
    receipts = build_receipts(
        governance_report, grant, requests, outcomes, frozen_v01_digest
    )
    replay = replay_receipts(receipts)
    digest = receipts[-1].receipt_hash if receipts else "0" * 64
    return DryRunAuthorityReport(
        governance_report=governance_report,
        grant=grant,
        requests=requests,
        outcomes=outcomes,
        receipts=receipts,
        replay=replay,
        authority_digest=digest,
        host_source_hashes=source_hashes,
        frozen_v01_digest=frozen_v01_digest,
        executed_actions=0,
    )


def qualify_stage1(
    jobs: Iterable[object], *, starting_value: int = 0
) -> Stage1Qualification:
    original_jobs = tuple(jobs)
    input_before = repr(original_jobs)
    sources_before = _snapshot_sources()
    frozen_before = _tree_digest(FROZEN_V01_ROOT)

    direct = ordinary_host.run_jobs(original_jobs, starting_value=starting_value)
    report = run_dry_run_authority(
        original_jobs, starting_value=starting_value, current_epoch=100
    )

    sources_after = _snapshot_sources()
    frozen_after = _tree_digest(FROZEN_V01_ROOT)
    input_after = repr(original_jobs)
    observed = report.governance_report.observation_report.host_run

    no_grant = evaluate_requests(
        None,
        report.requests,
        current_epoch=100,
        expected_session_digest=report.governance_report.governance_digest,
    )
    deny_by_default_pass = all(
        item.disposition == REJECTED and item.reason_code == "NO_GRANT"
        for item in no_grant
    )

    grant_valid, _ = validate_grant(report.grant)
    tampered_grant = replace(report.grant, max_actions=report.grant.max_actions + 1)
    tampered_valid, _ = validate_grant(tampered_grant)

    wrong_session = evaluate_requests(
        report.grant,
        report.requests,
        current_epoch=100,
        expected_session_digest="f" * 64,
    )
    session_binding_pass = all(
        item.reason_code == "SESSION_DIGEST_MISMATCH" for item in wrong_session
    )

    narrow_grant = issue_grant(
        report.governance_report.governance_digest,
        allowed_actions=(DENY,),
        max_actions=8,
        valid_from_epoch=100,
        valid_through_epoch=100,
    )
    narrow_outcomes = evaluate_requests(
        narrow_grant,
        report.requests,
        current_epoch=100,
        expected_session_digest=report.governance_report.governance_digest,
    )
    scope_enforced = all(
        (
            item.would_authorize
            if item.requested_action == DENY
            else item.disposition in (REJECTED, ABSTAIN)
        )
        for item in narrow_outcomes
    )

    budget_grant = issue_grant(
        report.governance_report.governance_digest,
        max_actions=2,
        valid_from_epoch=100,
        valid_through_epoch=100,
    )
    budget_outcomes = evaluate_requests(
        budget_grant,
        report.requests,
        current_epoch=100,
        expected_session_digest=report.governance_report.governance_digest,
    )
    budget_enforced = (
        sum(1 for item in budget_outcomes if item.would_authorize) == 2
        and any(item.reason_code == "ACTION_BUDGET_EXHAUSTED" for item in budget_outcomes)
    )

    early = evaluate_requests(
        issue_grant(
            report.governance_report.governance_digest,
            valid_from_epoch=101,
            valid_through_epoch=102,
        ),
        report.requests,
        current_epoch=100,
        expected_session_digest=report.governance_report.governance_digest,
    )
    late = evaluate_requests(
        issue_grant(
            report.governance_report.governance_digest,
            valid_from_epoch=98,
            valid_through_epoch=99,
        ),
        report.requests,
        current_epoch=100,
        expected_session_digest=report.governance_report.governance_digest,
    )
    validity_window_enforced = (
        all(item.reason_code == "GRANT_NOT_YET_VALID" for item in early)
        and all(item.reason_code == "GRANT_EXPIRED" for item in late)
    )

    unknown_request = InterventionRequest(
        request_id=1,
        job_ordinal=1,
        job_id="UNKNOWN_JOB",
        source_decision=v01_governance.UNKNOWN,
        requested_action=ABSTAIN,
        source_ternary=0,
        evidence_digest="0" * 64,
    )
    unknown_outcome = evaluate_requests(
        issue_grant(
            report.governance_report.governance_digest,
            max_actions=1,
            valid_from_epoch=100,
            valid_through_epoch=100,
        ),
        (unknown_request,),
        current_epoch=100,
        expected_session_digest=report.governance_report.governance_digest,
    )[0]
    unknown_abstention_pass = (
        unknown_outcome.disposition == ABSTAIN
        and not unknown_outcome.would_authorize
        and not unknown_outcome.executed
    )

    tampered_receipts = tamper_receipt(report.receipts, 1, "tampered")
    tamper_detection_pass = (
        not tampered_valid
        and not replay_receipts(tampered_receipts).passed
        and not replay_receipts(report.receipts[:-1]).final_digest
        == report.authority_digest
    )

    action_counts = tuple(
        (action, sum(1 for item in report.requests if item.requested_action == action))
        for action in (ALLOW, HOLD, DENY, ABSTAIN)
    )
    executed_actions = sum(1 for item in report.outcomes if item.executed)
    would_authorize_count = sum(
        1 for item in report.outcomes if item.would_authorize
    )

    host_output_equivalent = direct.canonical_text() == observed.canonical_text()
    host_digest_equivalent = direct.run_digest == observed.run_digest
    v01_sources_unchanged = sources_before == sources_after == report.host_source_hashes
    frozen_v01_unchanged = frozen_before == frozen_after == report.frozen_v01_digest

    passed = all(
        (
            MODE == "DRY_RUN",
            EXECUTION_AUTHORITY == "NONE",
            host_output_equivalent,
            host_digest_equivalent,
            v01_sources_unchanged,
            frozen_v01_unchanged,
            input_before == input_after,
            report.governance_report.replay.passed,
            report.replay.passed,
            deny_by_default_pass,
            grant_valid,
            session_binding_pass,
            scope_enforced,
            budget_enforced,
            validity_window_enforced,
            unknown_abstention_pass,
            tamper_detection_pass,
            executed_actions == 0,
        )
    )

    return Stage1Qualification(
        passed=passed,
        mode=MODE,
        execution_authority=EXECUTION_AUTHORITY,
        host_output_equivalent=host_output_equivalent,
        host_digest_equivalent=host_digest_equivalent,
        v01_sources_unchanged=v01_sources_unchanged,
        frozen_v01_unchanged=frozen_v01_unchanged,
        input_unchanged=input_before == input_after,
        governance_replay_pass=report.governance_report.replay.passed,
        authority_replay_pass=report.replay.passed,
        deny_by_default_pass=deny_by_default_pass,
        grant_integrity_pass=grant_valid,
        session_binding_pass=session_binding_pass,
        scope_enforced=scope_enforced,
        budget_enforced=budget_enforced,
        validity_window_enforced=validity_window_enforced,
        unknown_abstention_pass=unknown_abstention_pass,
        tamper_detection_pass=tamper_detection_pass,
        executed_actions=executed_actions,
        request_count=len(report.requests),
        would_authorize_count=would_authorize_count,
        action_counts=action_counts,
        host_digest=direct.run_digest,
        governance_digest=report.governance_report.governance_digest,
        grant_hash=report.grant.grant_hash,
        authority_digest=report.authority_digest,
        frozen_v01_digest=report.frozen_v01_digest,
    )


def print_qualification(result: Stage1Qualification) -> None:
    print("=" * 88)
    print(f"{INTERFACE_NAME} v{INTERFACE_VERSION}")
    print("=" * 88)
    print(f"Mode / execution authority:      {result.mode} / {result.execution_authority}")
    print(f"Host output equivalent:          {result.host_output_equivalent}")
    print(f"Host digest equivalent:          {result.host_digest_equivalent}")
    print(f"Qualified v0.1 sources unchanged: {result.v01_sources_unchanged}")
    print(f"Frozen v0.1 release unchanged:   {result.frozen_v01_unchanged}")
    print(f"Input objects unchanged:         {result.input_unchanged}")
    print(f"Governance replay pass:          {result.governance_replay_pass}")
    print(f"Authority replay pass:           {result.authority_replay_pass}")
    print(f"Deny by default:                 {result.deny_by_default_pass}")
    print(f"Grant integrity:                 {result.grant_integrity_pass}")
    print(f"Session binding:                 {result.session_binding_pass}")
    print(f"Scope enforced:                  {result.scope_enforced}")
    print(f"Budget enforced:                 {result.budget_enforced}")
    print(f"Validity window enforced:        {result.validity_window_enforced}")
    print(f"UNKNOWN abstention:              {result.unknown_abstention_pass}")
    print(f"Tamper detection:                {result.tamper_detection_pass}")
    print(f"Requests / would authorize:      {result.request_count} / {result.would_authorize_count}")
    print(f"Executed actions:                {result.executed_actions}")
    print(f"Action counts:                   {result.action_counts}")
    print(f"Host digest:                     {result.host_digest}")
    print(f"Governance digest:               {result.governance_digest}")
    print(f"Grant hash:                      {result.grant_hash}")
    print(f"Authority digest:                {result.authority_digest}")
    print(f"Frozen v0.1 digest:              {result.frozen_v01_digest}")
    print(
        "STAGE 1 BOUNDED AUTHORITY QUALIFICATION: "
        + ("PASS" if result.passed else "FAIL")
    )


def main() -> None:
    result = qualify_stage1(ordinary_host.baseline_jobs(), starting_value=0)
    print_qualification(result)


if __name__ == "__main__":
    main()
