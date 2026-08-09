#!/usr/bin/env python3
"""Controlled RELEASE from the v0.2 mediated HOLD queue, Stage 3.

A held job may return to the host pending batch only under a fresh, independent,
one-use RELEASE authority. RELEASE restores the immutable job at its original
ordinal; it never forces execution and never bypasses ordinary-host validation
or dependency rules.
"""
from __future__ import annotations

import hashlib
import importlib.util
from dataclasses import dataclass, replace
from pathlib import Path
import sys
from typing import Sequence, Tuple

sys.dont_write_bytecode = True
INTERFACE_NAME = "CONTROLLED RELEASE HOST"
INTERFACE_VERSION = "0.2.3"
MODE = "ACTIVE_MEDIATED"
EXECUTION_AUTHORITY = "RELEASE_ONLY"
RELEASED = "RELEASED"
RELEASE_REJECTED = "RELEASE_REJECTED"

THIS_FILE = Path(__file__).resolve()
PROJECT_DIR = THIS_FILE.parents[1]
REPOSITORY_ROOT = THIS_FILE.parents[3]
MEDIATION_PATH = PROJECT_DIR / "mediation" / "mediated_hold_host.py"


def _load(path: Path, name: str):
    existing = sys.modules.get(name)
    if existing is not None:
        return existing
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"could not load {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


mediation = _load(MEDIATION_PATH, "bolt_on_v02_mediation_for_release")
authority = mediation.authority
ordinary_host = mediation.ordinary_host


@dataclass(frozen=True)
class ReleaseGrant:
    grant_id: str
    issuer: str
    action: str
    hold_permit_hash: str
    hold_mediation_digest: str
    held_job_id: str
    original_ordinal: int
    valid_epoch: int
    max_actions: int
    grant_hash: str

    def canonical_unsigned(self) -> str:
        return "|".join((self.grant_id, self.issuer, self.action,
            self.hold_permit_hash, self.hold_mediation_digest, self.held_job_id,
            str(self.original_ordinal), str(self.valid_epoch), str(self.max_actions)))


@dataclass(frozen=True)
class ReleasePermit:
    permit_id: str
    issuer: str
    action: str
    release_grant_hash: str
    hold_permit_hash: str
    hold_mediation_digest: str
    held_job_id: str
    original_ordinal: int
    evidence_digest: str
    valid_epoch: int
    max_uses: int
    permit_hash: str

    def canonical_unsigned(self) -> str:
        return "|".join((self.permit_id, self.issuer, self.action,
            self.release_grant_hash, self.hold_permit_hash,
            self.hold_mediation_digest, self.held_job_id,
            str(self.original_ordinal), self.evidence_digest,
            str(self.valid_epoch), str(self.max_uses)))


@dataclass(frozen=True)
class ReleaseReceipt:
    receipt_id: int
    kind: str
    subject: str
    payload: str
    prior_hash: str
    receipt_hash: str


@dataclass(frozen=True)
class ReleaseReplay:
    passed: bool
    final_digest: str
    checked_receipts: int
    first_error: str


@dataclass(frozen=True)
class ReleaseReport:
    hold_report: object
    grant: ReleaseGrant | None
    permit: ReleasePermit | None
    released: bool
    reason_code: str
    released_jobs: Tuple[object, ...]
    remaining_held_jobs: Tuple[object, ...]
    restored_batch: Tuple[object, ...]
    released_host_run: object
    direct_host_run: object
    consumed_release_permit_ids: Tuple[str, ...]
    receipts: Tuple[ReleaseReceipt, ...]
    replay: ReleaseReplay
    release_digest: str
    executed_actions: int


@dataclass(frozen=True)
class Stage3Qualification:
    passed: bool
    mode: str
    execution_authority: str
    independent_release_authority: bool
    release_executed: bool
    exactly_one_action: bool
    original_ordinal_restored: bool
    immutable_job_preserved: bool
    host_rules_preserved: bool
    hold_authority_insufficient: bool
    no_permit_fails_closed: bool
    invalid_permit_fails_closed: bool
    expired_permit_fails_closed: bool
    reused_permit_fails_closed: bool
    evidence_binding_pass: bool
    unknown_abstention_pass: bool
    replay_pass: bool
    tamper_detection_pass: bool
    safe_detach_pass: bool
    executed_actions: int
    released_job_ids: Tuple[str, ...]
    released_host_digest: str
    release_digest: str


def _sha(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _exact_int(value: object, name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise TypeError(f"{name} must be an exact integer")
    return value


def _grant_hash(grant: ReleaseGrant) -> str:
    return _sha("RELEASE-GRANT|" + grant.canonical_unsigned())


def _permit_hash(permit: ReleasePermit) -> str:
    return _sha("RELEASE-PERMIT|" + permit.canonical_unsigned())


def _hold_evidence_digest(hold_report: object) -> str:
    held = ",".join(job.job_id for job in hold_report.held_jobs)
    return _sha("|".join((hold_report.mediation_digest,
        hold_report.permit.permit_hash if hold_report.permit else "NONE",
        hold_report.outcome.canonical_line(), held)))


def prepare_release_authority(hold_report: object, current_epoch: int) -> ReleaseGrant:
    epoch = _exact_int(current_epoch, "current_epoch")
    if hold_report.executed_actions != 1 or len(hold_report.held_jobs) != 1:
        raise ValueError("release authority requires exactly one executed HOLD")
    if hold_report.permit is None or not hold_report.replay.passed:
        raise ValueError("release authority requires intact HOLD evidence")
    job = hold_report.held_jobs[0]
    unsigned = ReleaseGrant(
        grant_id="RELEASE-GRANT-0001", issuer=INTERFACE_NAME,
        action="RELEASE", hold_permit_hash=hold_report.permit.permit_hash,
        hold_mediation_digest=hold_report.mediation_digest,
        held_job_id=job.job_id, original_ordinal=hold_report.permit.job_ordinal,
        valid_epoch=epoch, max_actions=1, grant_hash="")
    return replace(unsigned, grant_hash=_grant_hash(unsigned))


def issue_release_permit(hold_report: object, grant: ReleaseGrant,
                         current_epoch: int) -> ReleasePermit:
    epoch = _exact_int(current_epoch, "current_epoch")
    if grant.grant_hash != _grant_hash(replace(grant, grant_hash="")):
        raise ValueError("release grant hash mismatch")
    if grant.action != "RELEASE" or grant.max_actions != 1 or grant.valid_epoch != epoch:
        raise ValueError("invalid release grant scope")
    if hold_report.permit is None or grant.hold_permit_hash != hold_report.permit.permit_hash:
        raise ValueError("release grant not bound to HOLD permit")
    if grant.hold_mediation_digest != hold_report.mediation_digest:
        raise ValueError("release grant not bound to HOLD mediation")
    unsigned = ReleasePermit(
        permit_id="RELEASE-PERMIT-0001", issuer=INTERFACE_NAME,
        action="RELEASE", release_grant_hash=grant.grant_hash,
        hold_permit_hash=grant.hold_permit_hash,
        hold_mediation_digest=grant.hold_mediation_digest,
        held_job_id=grant.held_job_id, original_ordinal=grant.original_ordinal,
        evidence_digest=_hold_evidence_digest(hold_report), valid_epoch=epoch,
        max_uses=1, permit_hash="")
    return replace(unsigned, permit_hash=_permit_hash(unsigned))


def _receipt_hash(receipt_id: int, kind: str, subject: str, payload: str,
                  prior_hash: str) -> str:
    return _sha("|".join((str(receipt_id), kind, subject, payload, prior_hash)))


def _build_receipts(hold_report: object, grant: ReleaseGrant | None,
                    permit: ReleasePermit | None, released: bool,
                    reason: str, restored_batch: Sequence[object]) -> Tuple[ReleaseReceipt, ...]:
    rows = [
        ("HOLD_EVIDENCE", hold_report.outcome.job_id, hold_report.mediation_digest),
        ("RELEASE_GRANT", grant.grant_id if grant else "NONE", grant.grant_hash if grant else "NONE"),
        ("RELEASE_PERMIT", permit.permit_id if permit else "NONE", permit.permit_hash if permit else "NONE"),
        ("RELEASE_OUTCOME", hold_report.outcome.job_id, f"{int(released)}|{reason}"),
        ("RESTORED_BATCH", "HOST", ",".join(job.job_id for job in restored_batch)),
    ]
    receipts = []
    prior = "GENESIS"
    for idx, (kind, subject, payload) in enumerate(rows, 1):
        digest = _receipt_hash(idx, kind, subject, payload, prior)
        receipts.append(ReleaseReceipt(idx, kind, subject, payload, prior, digest))
        prior = digest
    return tuple(receipts)


def replay_receipts(receipts: Sequence[ReleaseReceipt]) -> ReleaseReplay:
    prior = "GENESIS"
    for idx, receipt in enumerate(receipts, 1):
        if receipt.receipt_id != idx:
            return ReleaseReplay(False, prior, idx - 1, "RECEIPT_SEQUENCE_MISMATCH")
        if receipt.prior_hash != prior:
            return ReleaseReplay(False, prior, idx - 1, "PRIOR_HASH_MISMATCH")
        expected = _receipt_hash(receipt.receipt_id, receipt.kind, receipt.subject,
                                 receipt.payload, receipt.prior_hash)
        if receipt.receipt_hash != expected:
            return ReleaseReplay(False, prior, idx - 1, "RECEIPT_HASH_MISMATCH")
        prior = expected
    return ReleaseReplay(True, prior, len(receipts), "")


def tamper_receipt(receipts: Sequence[ReleaseReceipt], index: int) -> Tuple[ReleaseReceipt, ...]:
    items = list(receipts)
    items[index] = replace(items[index], payload=items[index].payload + "|TAMPERED")
    return tuple(items)


def release_from_hold(original_jobs: Sequence[object], hold_report: object,
                      grant: ReleaseGrant | None, permit: ReleasePermit | None,
                      current_epoch: int,
                      consumed_release_permit_ids: Sequence[str] = ()) -> ReleaseReport:
    epoch = _exact_int(current_epoch, "current_epoch")
    original = tuple(original_jobs)
    consumed = tuple(consumed_release_permit_ids)
    if len(set(consumed)) != len(consumed):
        raise ValueError("duplicate consumed release permit IDs")
    released = False
    reason = "NO_RELEASE_PERMIT"
    restored = tuple(hold_report.dispatched_jobs)
    remaining = tuple(hold_report.held_jobs)
    released_jobs: Tuple[object, ...] = ()

    if grant is not None and permit is not None:
        blank_grant = replace(grant, grant_hash="")
        blank_permit = replace(permit, permit_hash="")
        checks = [
            (grant.grant_hash == _grant_hash(blank_grant), "RELEASE_GRANT_HASH_MISMATCH"),
            (permit.permit_hash == _permit_hash(blank_permit), "RELEASE_PERMIT_HASH_MISMATCH"),
            (grant.action == "RELEASE" and permit.action == "RELEASE", "NON_RELEASE_ACTION_FORBIDDEN"),
            (grant.valid_epoch == epoch and permit.valid_epoch == epoch, "RELEASE_EPOCH_MISMATCH"),
            (grant.max_actions == 1 and permit.max_uses == 1, "RELEASE_BUDGET_MISMATCH"),
            (permit.permit_id not in consumed, "RELEASE_PERMIT_ALREADY_CONSUMED"),
            (permit.release_grant_hash == grant.grant_hash, "RELEASE_GRANT_BINDING_MISMATCH"),
            (hold_report.permit is not None and permit.hold_permit_hash == hold_report.permit.permit_hash, "HOLD_PERMIT_BINDING_MISMATCH"),
            (permit.hold_mediation_digest == hold_report.mediation_digest, "HOLD_MEDIATION_BINDING_MISMATCH"),
            (permit.evidence_digest == _hold_evidence_digest(hold_report), "HOLD_EVIDENCE_MISMATCH"),
            (hold_report.executed_actions == 1 and len(hold_report.held_jobs) == 1, "NO_QUALIFIED_HELD_JOB"),
            (permit.held_job_id == hold_report.held_jobs[0].job_id, "HELD_JOB_BINDING_MISMATCH"),
            (1 <= permit.original_ordinal <= len(original), "ORIGINAL_ORDINAL_INVALID"),
            (original[permit.original_ordinal - 1] == hold_report.held_jobs[0], "IMMUTABLE_JOB_MISMATCH"),
            (hold_report.replay.passed, "HOLD_REPLAY_FAILED"),
        ]
        reason = "RELEASED"
        for ok, failure in checks:
            if not ok:
                reason = failure
                break
        else:
            restored_list = list(hold_report.dispatched_jobs)
            restored_list.insert(permit.original_ordinal - 1, hold_report.held_jobs[0])
            restored = tuple(restored_list)
            released_jobs = (hold_report.held_jobs[0],)
            remaining = ()
            consumed = consumed + (permit.permit_id,)
            released = True

    released_run = ordinary_host.run_jobs(restored)
    direct_run = ordinary_host.run_jobs(original)
    receipts = _build_receipts(hold_report, grant, permit, released, reason, restored)
    replay = replay_receipts(receipts)
    digest = _sha("\n".join(r.receipt_hash for r in receipts) + "|" + released_run.run_digest)
    return ReleaseReport(hold_report, grant, permit, released, reason,
        released_jobs, remaining, restored, released_run, direct_run, consumed,
        receipts, replay, digest, 1 if released else 0)


def run_baseline_release(jobs: Sequence[object] | None = None,
                         hold_epoch: int = 200, release_epoch: int = 201) -> ReleaseReport:
    selected = tuple(jobs) if jobs is not None else ordinary_host.baseline_jobs()
    advisory = mediation.prepare_hold_authority(selected, current_epoch=hold_epoch)
    hold_permit = mediation.issue_hold_permit(advisory, current_epoch=hold_epoch)
    hold_report = mediation.mediate_with_hold(selected, advisory, hold_permit,
                                               current_epoch=hold_epoch)
    grant = prepare_release_authority(hold_report, release_epoch)
    permit = issue_release_permit(hold_report, grant, release_epoch)
    return release_from_hold(selected, hold_report, grant, permit, release_epoch)


def qualify_stage3(jobs: Sequence[object] | None = None) -> Stage3Qualification:
    selected = tuple(jobs) if jobs is not None else ordinary_host.baseline_jobs()
    report = run_baseline_release(selected)
    no_permit = release_from_hold(selected, report.hold_report, report.grant, None, 201)
    expired = release_from_hold(selected, report.hold_report, report.grant, report.permit, 202)
    reused = release_from_hold(selected, report.hold_report, report.grant, report.permit, 201,
                               report.consumed_release_permit_ids)
    tampered = replay_receipts(tamper_receipt(report.receipts, 3))
    hold_only = replace(report.permit, action="HOLD", permit_hash="")
    hold_only = replace(hold_only, permit_hash=_permit_hash(hold_only))
    wrong_action = release_from_hold(selected, report.hold_report, report.grant, hold_only, 201)
    detached = ordinary_host.run_jobs(selected)
    fields = dict(
        mode=MODE, execution_authority=EXECUTION_AUTHORITY,
        independent_release_authority=(report.grant.action == "RELEASE" and report.permit.action == "RELEASE"),
        release_executed=report.released, exactly_one_action=report.executed_actions == 1,
        original_ordinal_restored=report.restored_batch == selected,
        immutable_job_preserved=report.released_jobs == report.hold_report.held_jobs,
        host_rules_preserved=report.released_host_run == report.direct_host_run and report.released_host_run.delayed_ids == ("J005",),
        hold_authority_insufficient=not wrong_action.released,
        no_permit_fails_closed=not no_permit.released and no_permit.remaining_held_jobs == report.hold_report.held_jobs,
        invalid_permit_fails_closed=not wrong_action.released,
        expired_permit_fails_closed=not expired.released,
        reused_permit_fails_closed=not reused.released,
        evidence_binding_pass=report.permit.evidence_digest == _hold_evidence_digest(report.hold_report),
        unknown_abstention_pass=report.hold_report.outcome.requested_action == authority.HOLD,
        replay_pass=report.replay.passed, tamper_detection_pass=not tampered.passed,
        safe_detach_pass=detached == report.direct_host_run,
        executed_actions=report.executed_actions,
        released_job_ids=tuple(job.job_id for job in report.released_jobs),
        released_host_digest=report.released_host_run.run_digest,
        release_digest=report.release_digest)
    passed = all(v for k, v in fields.items() if k.endswith("_pass") or k in {
        "independent_release_authority", "release_executed", "exactly_one_action",
        "original_ordinal_restored", "immutable_job_preserved", "host_rules_preserved",
        "hold_authority_insufficient", "no_permit_fails_closed",
        "invalid_permit_fails_closed", "expired_permit_fails_closed",
        "reused_permit_fails_closed"})
    return Stage3Qualification(passed=passed, **fields)


def print_qualification(result: Stage3Qualification) -> None:
    print("=" * 88)
    print(f"{INTERFACE_NAME} v{INTERFACE_VERSION}")
    print("=" * 88)
    labels = [
        ("Mode / execution authority", f"{result.mode} / {result.execution_authority}"),
        ("Independent RELEASE authority", result.independent_release_authority),
        ("RELEASE executed", result.release_executed),
        ("Exactly one action", result.exactly_one_action),
        ("Original ordinal restored", result.original_ordinal_restored),
        ("Immutable job preserved", result.immutable_job_preserved),
        ("Host rules preserved", result.host_rules_preserved),
        ("HOLD authority insufficient", result.hold_authority_insufficient),
        ("No-permit fail closed", result.no_permit_fails_closed),
        ("Invalid-permit fail closed", result.invalid_permit_fails_closed),
        ("Expired-permit fail closed", result.expired_permit_fails_closed),
        ("Reused-permit fail closed", result.reused_permit_fails_closed),
        ("Evidence binding", result.evidence_binding_pass),
        ("Replay", result.replay_pass), ("Tamper detection", result.tamper_detection_pass),
        ("Safe detach", result.safe_detach_pass),
        ("Executed actions", result.executed_actions),
        ("Released job IDs", result.released_job_ids),
        ("Released host digest", result.released_host_digest),
        ("Release digest", result.release_digest),
    ]
    for label, value in labels:
        print(f"{label + ':':<34} {value}")
    print("STAGE 3 CONTROLLED RELEASE QUALIFICATION: " + ("PASS" if result.passed else "FAIL"))


def main() -> None:
    result = qualify_stage3()
    print_qualification(result)
    if not result.passed:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
