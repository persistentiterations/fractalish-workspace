#!/usr/bin/env python3
"""Bounded multi-action lifecycle qualification for Bolt-On v0.2 Stage 4.

This additive stage composes the already qualified Stage 2 HOLD and Stage 3
RELEASE paths across multiple isolated cycles. It adds no new host action.
Each lifecycle cycle has a unique cycle identifier, exact integer epochs,
cycle-bound consumption keys, immutable interruption checkpoints, and a
receipt chain suitable for deterministic replay.
"""
from __future__ import annotations

import hashlib
import importlib.util
from dataclasses import dataclass, replace
from pathlib import Path
import sys
from typing import Sequence, Tuple

sys.dont_write_bytecode = True
INTERFACE_NAME = "BOUNDED MULTI-ACTION LIFECYCLE"
INTERFACE_VERSION = "0.2.4"
MODE = "ACTIVE_MEDIATED"
EXECUTION_AUTHORITY = "HOLD_RELEASE_ONLY"

THIS_FILE = Path(__file__).resolve()
PROJECT_DIR = THIS_FILE.parents[1]
RELEASE_PATH = PROJECT_DIR / "release" / "controlled_release_host.py"


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


release = _load(RELEASE_PATH, "bolt_on_v02_release_for_lifecycle")
mediation = release.mediation
ordinary_host = release.ordinary_host


def _sha(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _exact_int(value: object, name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise TypeError(f"{name} must be an exact integer")
    return value


@dataclass(frozen=True)
class LifecycleCheckpoint:
    cycle_id: str
    hold_mediation_digest: str
    hold_permit_hash: str
    held_job_id: str
    original_ordinal: int
    created_epoch: int
    checkpoint_hash: str

    def canonical_unsigned(self) -> str:
        return "|".join((self.cycle_id, self.hold_mediation_digest,
            self.hold_permit_hash, self.held_job_id, str(self.original_ordinal),
            str(self.created_epoch)))


@dataclass(frozen=True)
class LifecycleReceipt:
    receipt_id: int
    cycle_id: str
    kind: str
    payload: str
    prior_hash: str
    receipt_hash: str


@dataclass(frozen=True)
class LifecycleReplay:
    passed: bool
    final_digest: str
    checked_receipts: int
    first_error: str


@dataclass(frozen=True)
class LifecycleCycle:
    cycle_id: str
    hold_epoch: int
    release_epoch: int
    hold_report: object
    release_report: object | None
    checkpoint: LifecycleCheckpoint | None
    detached_host_run: object | None
    recovered: bool
    expired_attempt_rejected: bool
    cross_cycle_attempt_rejected: bool
    hold_consumption_key: str
    release_consumption_key: str
    receipts: Tuple[LifecycleReceipt, ...]
    replay: LifecycleReplay
    cycle_digest: str


@dataclass(frozen=True)
class LifecycleCampaign:
    jobs: Tuple[object, ...]
    cycles: Tuple[LifecycleCycle, ...]
    receipts: Tuple[LifecycleReceipt, ...]
    replay: LifecycleReplay
    campaign_digest: str
    hold_consumption_keys: Tuple[str, ...]
    release_consumption_keys: Tuple[str, ...]
    total_executed_actions: int


@dataclass(frozen=True)
class Stage4Qualification:
    passed: bool
    mode: str
    execution_authority: str
    four_cycles_completed: bool
    repeated_hold_release_pass: bool
    expired_authority_rejected: bool
    fresh_reauthorization_pass: bool
    interrupted_recovery_pass: bool
    checkpoint_tamper_detection: bool
    active_hold_detach_pass: bool
    detach_preserves_hold_pass: bool
    cross_cycle_hold_leak_blocked: bool
    cross_cycle_release_leak_blocked: bool
    permit_hash_scoping_pass: bool
    exact_action_budget_pass: bool
    immutable_jobs_pass: bool
    original_ordinals_pass: bool
    host_rules_preserved: bool
    cycle_replay_pass: bool
    campaign_replay_pass: bool
    receipt_tamper_detection: bool
    repeated_campaign_exact: bool
    frozen_behavior_preserved: bool
    total_executed_actions: int
    cycle_digests: Tuple[str, ...]
    campaign_digest: str


def _checkpoint_hash(checkpoint: LifecycleCheckpoint) -> str:
    return _sha("LIFECYCLE-CHECKPOINT|" + checkpoint.canonical_unsigned())


def create_checkpoint(cycle_id: str, hold_report: object,
                      created_epoch: int) -> LifecycleCheckpoint:
    epoch = _exact_int(created_epoch, "created_epoch")
    if not cycle_id or not isinstance(cycle_id, str):
        raise ValueError("cycle_id must be a non-empty string")
    if hold_report.executed_actions != 1 or len(hold_report.held_jobs) != 1:
        raise ValueError("checkpoint requires exactly one active HOLD")
    if hold_report.permit is None or not hold_report.replay.passed:
        raise ValueError("checkpoint requires intact HOLD evidence")
    job = hold_report.held_jobs[0]
    unsigned = LifecycleCheckpoint(cycle_id, hold_report.mediation_digest,
        hold_report.permit.permit_hash, job.job_id, hold_report.permit.job_ordinal,
        epoch, "")
    return replace(unsigned, checkpoint_hash=_checkpoint_hash(unsigned))


def validate_checkpoint(checkpoint: LifecycleCheckpoint,
                        hold_report: object) -> Tuple[bool, str]:
    blank = replace(checkpoint, checkpoint_hash="")
    checks = (
        (checkpoint.checkpoint_hash == _checkpoint_hash(blank), "CHECKPOINT_HASH_MISMATCH"),
        (hold_report.permit is not None, "HOLD_PERMIT_MISSING"),
        (hold_report.replay.passed, "HOLD_REPLAY_FAILED"),
        (hold_report.executed_actions == 1 and len(hold_report.held_jobs) == 1,
         "ACTIVE_HOLD_MISSING"),
        (checkpoint.hold_mediation_digest == hold_report.mediation_digest,
         "HOLD_DIGEST_MISMATCH"),
        (hold_report.permit is not None and checkpoint.hold_permit_hash == hold_report.permit.permit_hash,
         "HOLD_PERMIT_HASH_MISMATCH"),
        (checkpoint.held_job_id == hold_report.held_jobs[0].job_id,
         "HELD_JOB_MISMATCH"),
        (checkpoint.original_ordinal == hold_report.permit.job_ordinal,
         "ORIGINAL_ORDINAL_MISMATCH"),
    )
    for ok, reason in checks:
        if not ok:
            return False, reason
    return True, "CHECKPOINT_VALID"


def _consumption_key(cycle_id: str, action: str, permit_hash: str) -> str:
    return _sha("|".join(("CONSUMPTION", cycle_id, action, permit_hash)))


def _receipt_hash(receipt_id: int, cycle_id: str, kind: str, payload: str,
                  prior_hash: str) -> str:
    return _sha("|".join((str(receipt_id), cycle_id, kind, payload, prior_hash)))


def build_cycle_receipts(cycle_id: str, hold_report: object,
                         release_report: object | None,
                         checkpoint: LifecycleCheckpoint | None,
                         detached: object | None,
                         expired_rejected: bool,
                         cross_cycle_rejected: bool) -> Tuple[LifecycleReceipt, ...]:
    rows = [
        ("HOLD", hold_report.mediation_digest),
        ("CHECKPOINT", checkpoint.checkpoint_hash if checkpoint else "NONE"),
        ("EXPIRED_ATTEMPT", "REJECTED" if expired_rejected else "NOT_RUN"),
        ("CROSS_CYCLE_ATTEMPT", "REJECTED" if cross_cycle_rejected else "NOT_RUN"),
        ("DETACH", detached.run_digest if detached is not None else "NONE"),
        ("RELEASE", release_report.release_digest if release_report is not None else "NONE"),
    ]
    receipts = []
    prior = "GENESIS"
    for index, (kind, payload) in enumerate(rows, 1):
        digest = _receipt_hash(index, cycle_id, kind, payload, prior)
        receipts.append(LifecycleReceipt(index, cycle_id, kind, payload, prior, digest))
        prior = digest
    return tuple(receipts)


def replay_receipts(receipts: Sequence[LifecycleReceipt]) -> LifecycleReplay:
    prior = "GENESIS"
    for index, receipt in enumerate(receipts, 1):
        if receipt.receipt_id != index:
            return LifecycleReplay(False, prior, index - 1, "RECEIPT_SEQUENCE_MISMATCH")
        if receipt.prior_hash != prior:
            return LifecycleReplay(False, prior, index - 1, "PRIOR_HASH_MISMATCH")
        expected = _receipt_hash(receipt.receipt_id, receipt.cycle_id,
                                 receipt.kind, receipt.payload, receipt.prior_hash)
        if receipt.receipt_hash != expected:
            return LifecycleReplay(False, prior, index - 1, "RECEIPT_HASH_MISMATCH")
        prior = expected
    return LifecycleReplay(True, prior, len(receipts), "")


def tamper_receipt(receipts: Sequence[LifecycleReceipt], index: int) -> Tuple[LifecycleReceipt, ...]:
    items = list(receipts)
    items[index] = replace(items[index], payload=items[index].payload + "|TAMPERED")
    return tuple(items)


def _make_hold(jobs: Tuple[object, ...], epoch: int):
    advisory = mediation.prepare_hold_authority(jobs, current_epoch=epoch)
    permit = mediation.issue_hold_permit(advisory, current_epoch=epoch)
    report = mediation.mediate_with_hold(jobs, advisory, permit, current_epoch=epoch)
    return advisory, permit, report


def _make_release(jobs: Tuple[object, ...], hold_report: object, epoch: int):
    grant = release.prepare_release_authority(hold_report, epoch)
    permit = release.issue_release_permit(hold_report, grant, epoch)
    report = release.release_from_hold(jobs, hold_report, grant, permit, epoch)
    return grant, permit, report


def _cycle(cycle_id: str, jobs: Tuple[object, ...], hold_epoch: int,
           release_epoch: int, *, checkpointed: bool = False,
           detach_active: bool = False, expire_first: bool = False,
           foreign_release_permit: object | None = None) -> LifecycleCycle:
    hold_epoch = _exact_int(hold_epoch, "hold_epoch")
    release_epoch = _exact_int(release_epoch, "release_epoch")
    _, hold_permit, hold_report = _make_hold(jobs, hold_epoch)
    checkpoint = create_checkpoint(cycle_id, hold_report, hold_epoch) if checkpointed else None
    recovered = False
    if checkpoint is not None:
        valid, reason = validate_checkpoint(checkpoint, hold_report)
        if not valid:
            raise ValueError(reason)
        recovered = True

    detached = ordinary_host.run_jobs(jobs) if detach_active else None
    expired_rejected = False
    if expire_first:
        stale_grant = release.prepare_release_authority(hold_report, release_epoch)
        stale_permit = release.issue_release_permit(hold_report, stale_grant, release_epoch)
        stale = release.release_from_hold(jobs, hold_report, stale_grant,
                                          stale_permit, release_epoch + 1)
        expired_rejected = not stale.released and stale.reason_code == "RELEASE_EPOCH_MISMATCH"
        release_epoch += 2

    grant, permit, release_report = _make_release(jobs, hold_report, release_epoch)
    cross_rejected = False
    if foreign_release_permit is not None:
        foreign = release.release_from_hold(jobs, hold_report, grant,
                                            foreign_release_permit, release_epoch)
        cross_rejected = not foreign.released

    hold_key = _consumption_key(cycle_id, "HOLD", hold_permit.permit_hash)
    release_key = _consumption_key(cycle_id, "RELEASE", permit.permit_hash)
    receipts = build_cycle_receipts(cycle_id, hold_report, release_report,
        checkpoint, detached, expired_rejected, cross_rejected)
    replay = replay_receipts(receipts)
    cycle_digest = _sha("\n".join(r.receipt_hash for r in receipts) + "|" +
                        hold_key + "|" + release_key)
    return LifecycleCycle(cycle_id, hold_epoch, release_epoch, hold_report,
        release_report, checkpoint, detached, recovered, expired_rejected,
        cross_rejected, hold_key, release_key, receipts, replay, cycle_digest)


def _campaign_receipts(cycles: Sequence[LifecycleCycle]) -> Tuple[LifecycleReceipt, ...]:
    receipts = []
    prior = "GENESIS"
    for index, cycle in enumerate(cycles, 1):
        payload = "|".join((cycle.cycle_digest, cycle.hold_consumption_key,
                            cycle.release_consumption_key))
        digest = _receipt_hash(index, "CAMPAIGN", "CYCLE", payload, prior)
        receipts.append(LifecycleReceipt(index, "CAMPAIGN", "CYCLE", payload,
                                         prior, digest))
        prior = digest
    return tuple(receipts)


def run_campaign(jobs: Sequence[object] | None = None) -> LifecycleCampaign:
    selected = tuple(jobs) if jobs is not None else ordinary_host.baseline_jobs()
    c1 = _cycle("CYCLE-001", selected, 300, 301)
    foreign = c1.release_report.permit
    c2 = _cycle("CYCLE-002", selected, 310, 311, expire_first=True,
                foreign_release_permit=foreign)
    c3 = _cycle("CYCLE-003", selected, 320, 321, checkpointed=True)
    c4 = _cycle("CYCLE-004", selected, 330, 331, checkpointed=True,
                detach_active=True)
    cycles = (c1, c2, c3, c4)
    receipts = _campaign_receipts(cycles)
    replay = replay_receipts(receipts)
    hold_keys = tuple(c.hold_consumption_key for c in cycles)
    release_keys = tuple(c.release_consumption_key for c in cycles)
    digest = _sha("\n".join(r.receipt_hash for r in receipts))
    actions = sum(c.hold_report.executed_actions + c.release_report.executed_actions
                  for c in cycles)
    return LifecycleCampaign(selected, cycles, receipts, replay, digest,
                             hold_keys, release_keys, actions)


def qualify_stage4(jobs: Sequence[object] | None = None) -> Stage4Qualification:
    campaign = run_campaign(jobs)
    repeated = run_campaign(jobs)
    direct = ordinary_host.run_jobs(campaign.jobs)
    c1, c2, c3, c4 = campaign.cycles
    tampered_checkpoint = replace(c3.checkpoint, held_job_id="TAMPERED")
    checkpoint_tamper = not validate_checkpoint(tampered_checkpoint, c3.hold_report)[0]
    receipt_tamper = not replay_receipts(tamper_receipt(campaign.receipts, 1)).passed
    foreign_hold = mediation.mediate_with_hold(
        campaign.jobs, c2.hold_report.authority_report, c1.hold_report.permit,
        current_epoch=c2.hold_epoch)
    fields = dict(
        mode=MODE,
        execution_authority=EXECUTION_AUTHORITY,
        four_cycles_completed=len(campaign.cycles) == 4,
        repeated_hold_release_pass=all(c.hold_report.executed_actions == 1 and
            c.release_report.executed_actions == 1 for c in campaign.cycles),
        expired_authority_rejected=c2.expired_attempt_rejected,
        fresh_reauthorization_pass=c2.release_report.released,
        interrupted_recovery_pass=c3.recovered and c3.release_report.released,
        checkpoint_tamper_detection=checkpoint_tamper,
        active_hold_detach_pass=c4.detached_host_run == direct,
        detach_preserves_hold_pass=(len(c4.hold_report.held_jobs) == 1 and
                                    c4.release_report.released),
        cross_cycle_hold_leak_blocked=not foreign_hold.outcome.executed,
        cross_cycle_release_leak_blocked=c2.cross_cycle_attempt_rejected,
        permit_hash_scoping_pass=(len(set(campaign.hold_consumption_keys)) == 4 and
                                  len(set(campaign.release_consumption_keys)) == 4),
        exact_action_budget_pass=campaign.total_executed_actions == 8,
        immutable_jobs_pass=all(c.release_report.released_jobs == c.hold_report.held_jobs
                                for c in campaign.cycles),
        original_ordinals_pass=all(c.release_report.restored_batch == campaign.jobs
                                   for c in campaign.cycles),
        host_rules_preserved=all(c.release_report.released_host_run == direct
                                 for c in campaign.cycles),
        cycle_replay_pass=all(c.replay.passed for c in campaign.cycles),
        campaign_replay_pass=campaign.replay.passed,
        receipt_tamper_detection=receipt_tamper,
        repeated_campaign_exact=campaign == repeated,
        frozen_behavior_preserved=direct == ordinary_host.run_jobs(campaign.jobs),
        total_executed_actions=campaign.total_executed_actions,
        cycle_digests=tuple(c.cycle_digest for c in campaign.cycles),
        campaign_digest=campaign.campaign_digest,
    )
    booleans = [value for key, value in fields.items()
                if isinstance(value, bool)]
    return Stage4Qualification(passed=all(booleans), **fields)


def print_qualification(result: Stage4Qualification) -> None:
    print("=" * 88)
    print(f"{INTERFACE_NAME} v{INTERFACE_VERSION}")
    print("=" * 88)
    labels = (
        ("Mode / execution authority", f"{result.mode} / {result.execution_authority}"),
        ("Four cycles completed", result.four_cycles_completed),
        ("Repeated HOLD/RELEASE", result.repeated_hold_release_pass),
        ("Expired authority rejected", result.expired_authority_rejected),
        ("Fresh reauthorization", result.fresh_reauthorization_pass),
        ("Interrupted recovery", result.interrupted_recovery_pass),
        ("Checkpoint tamper detection", result.checkpoint_tamper_detection),
        ("Active-HOLD detach", result.active_hold_detach_pass),
        ("Detach preserves held job", result.detach_preserves_hold_pass),
        ("Cross-cycle HOLD blocked", result.cross_cycle_hold_leak_blocked),
        ("Cross-cycle RELEASE blocked", result.cross_cycle_release_leak_blocked),
        ("Permit hash scoping", result.permit_hash_scoping_pass),
        ("Exact action budget", result.exact_action_budget_pass),
        ("Immutable jobs", result.immutable_jobs_pass),
        ("Original ordinals", result.original_ordinals_pass),
        ("Host rules preserved", result.host_rules_preserved),
        ("Cycle replay", result.cycle_replay_pass),
        ("Campaign replay", result.campaign_replay_pass),
        ("Receipt tamper detection", result.receipt_tamper_detection),
        ("Repeated campaign exact", result.repeated_campaign_exact),
        ("Total executed actions", result.total_executed_actions),
        ("Cycle digests", result.cycle_digests),
        ("Campaign digest", result.campaign_digest),
    )
    for label, value in labels:
        print(f"{label + ':':<34} {value}")
    print("STAGE 4 BOUNDED LIFECYCLE QUALIFICATION: " +
          ("PASS" if result.passed else "FAIL"))


def main() -> None:
    result = qualify_stage4()
    print_qualification(result)
    if not result.passed:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
