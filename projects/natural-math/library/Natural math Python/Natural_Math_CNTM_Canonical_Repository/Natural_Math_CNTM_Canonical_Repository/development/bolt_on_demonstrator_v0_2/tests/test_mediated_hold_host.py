#!/usr/bin/env python3
"""Qualification tests for v0.2 Stage 2 mediated HOLD execution."""

from __future__ import annotations

from dataclasses import replace
import importlib.util
from pathlib import Path
import sys
import unittest

THIS_FILE = Path(__file__).resolve()
PROJECT_DIR = THIS_FILE.parents[1]
MEDIATION_PATH = PROJECT_DIR / "mediation" / "mediated_hold_host.py"

spec = importlib.util.spec_from_file_location("mediated_hold_host", MEDIATION_PATH)
if spec is None or spec.loader is None:
    raise RuntimeError(f"could not load mediation module from {MEDIATION_PATH}")
mediation = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = mediation
spec.loader.exec_module(mediation)

EXPECTED_AUTHORITY_DIGEST = "c1ce6e705e6dd9547feaee476212bb28ec274b0f87fd39b50e0d8ed39daba162"
EXPECTED_PERMIT_HASH = "0e3dc0a854720caebae299ea5883703e04bee3eda29f3c9b1b61d80b2eb47f56"
EXPECTED_MEDIATION_DIGEST = "3b90f8f8230e3dfe7791ece89649aa019f641025a8588050d5cc2b7bb5157ac9"
EXPECTED_MEDIATED_HOST_DIGEST = "aec393e6c4c1f9cc20872f7f88ae9dbd158e96ee4f48c8fd33a8bd85bb834eae"


class MediatedHoldHostTests(unittest.TestCase):
    def setUp(self) -> None:
        self.jobs = mediation.ordinary_host.baseline_jobs()
        self.epoch = 200
        self.advisory = mediation.prepare_hold_authority(
            self.jobs, current_epoch=self.epoch
        )
        self.permit = mediation.issue_hold_permit(
            self.advisory, current_epoch=self.epoch
        )

    def mediate(self, permit="DEFAULT", **kwargs):
        selected = self.permit if permit == "DEFAULT" else permit
        return mediation.mediate_with_hold(
            self.jobs,
            self.advisory,
            selected,
            current_epoch=self.epoch,
            **kwargs,
        )

    def rehash(self, permit):
        return replace(
            permit,
            permit_hash=mediation._permit_hash_from_fields(
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
            ),
        )

    def test_stage2_qualification_passes(self) -> None:
        result = mediation.qualify_stage2(self.jobs)
        self.assertTrue(result.passed)
        self.assertEqual(result.executed_actions, 1)
        self.assertEqual(result.held_job_ids, ("J005",))

    def test_fixed_release_digests_match(self) -> None:
        report = self.mediate()
        self.assertEqual(report.authority_report.authority_digest, EXPECTED_AUTHORITY_DIGEST)
        self.assertEqual(report.permit.permit_hash, EXPECTED_PERMIT_HASH)
        self.assertEqual(report.mediation_digest, EXPECTED_MEDIATION_DIGEST)
        self.assertEqual(report.mediated_host_run.run_digest, EXPECTED_MEDIATED_HOST_DIGEST)

    def test_active_hold_executes_exactly_once(self) -> None:
        report = self.mediate()
        self.assertEqual(report.executed_actions, 1)
        self.assertTrue(report.outcome.executed)
        self.assertEqual(report.outcome.disposition, mediation.HELD)
        self.assertEqual(len(report.held_jobs), 1)
        self.assertEqual(report.held_jobs[0].job_id, "J005")

    def test_only_hold_action_is_accepted(self) -> None:
        altered = self.rehash(replace(self.permit, action=mediation.authority.ALLOW))
        report = self.mediate(permit=altered)
        self.assertEqual(report.executed_actions, 0)
        self.assertEqual(report.outcome.reason_code, "NON_HOLD_ACTION_FORBIDDEN")

    def test_no_permit_is_exact_passthrough(self) -> None:
        report = self.mediate(permit=None)
        self.assertEqual(report.executed_actions, 0)
        self.assertEqual(report.mediated_host_run, report.direct_host_run)
        self.assertEqual(report.outcome.reason_code, "NO_ACTIVE_PERMIT")

    def test_tampered_permit_is_exact_passthrough(self) -> None:
        report = self.mediate(permit=replace(self.permit, job_id="TAMPERED"))
        self.assertEqual(report.executed_actions, 0)
        self.assertEqual(report.mediated_host_run, report.direct_host_run)
        self.assertEqual(report.outcome.reason_code, "PERMIT_HASH_MISMATCH")

    def test_wrong_session_is_exact_passthrough(self) -> None:
        altered = self.rehash(replace(self.permit, session_digest="f" * 64))
        report = self.mediate(permit=altered)
        self.assertEqual(report.outcome.reason_code, "SESSION_DIGEST_MISMATCH")
        self.assertEqual(report.mediated_host_run, report.direct_host_run)

    def test_wrong_authority_digest_is_exact_passthrough(self) -> None:
        altered = self.rehash(replace(self.permit, authority_digest="a" * 64))
        report = self.mediate(permit=altered)
        self.assertEqual(report.outcome.reason_code, "AUTHORITY_DIGEST_MISMATCH")
        self.assertEqual(report.mediated_host_run, report.direct_host_run)

    def test_wrong_grant_hash_is_exact_passthrough(self) -> None:
        altered = self.rehash(replace(self.permit, grant_hash="b" * 64))
        report = self.mediate(permit=altered)
        self.assertEqual(report.outcome.reason_code, "GRANT_HASH_BINDING_MISMATCH")
        self.assertEqual(report.mediated_host_run, report.direct_host_run)

    def test_wrong_evidence_digest_is_exact_passthrough(self) -> None:
        altered = self.rehash(replace(self.permit, evidence_digest="e" * 64))
        report = self.mediate(permit=altered)
        self.assertEqual(report.outcome.reason_code, "PERMIT_EVIDENCE_MISMATCH")
        self.assertEqual(report.mediated_host_run, report.direct_host_run)

    def test_wrong_job_ordinal_is_exact_passthrough(self) -> None:
        altered = self.rehash(replace(self.permit, job_ordinal=1))
        report = self.mediate(permit=altered)
        self.assertEqual(report.outcome.reason_code, "PERMIT_JOB_BINDING_MISMATCH")
        self.assertEqual(report.mediated_host_run, report.direct_host_run)

    def test_wrong_job_id_with_valid_hash_is_exact_passthrough(self) -> None:
        altered = self.rehash(replace(self.permit, job_id="J001"))
        report = self.mediate(permit=altered)
        self.assertEqual(report.outcome.reason_code, "PERMIT_JOB_BINDING_MISMATCH")
        self.assertEqual(report.mediated_host_run, report.direct_host_run)

    def test_expired_epoch_is_exact_passthrough(self) -> None:
        report = mediation.mediate_with_hold(
            self.jobs,
            self.advisory,
            self.permit,
            current_epoch=self.epoch + 1,
        )
        self.assertEqual(report.outcome.reason_code, "PERMIT_EPOCH_MISMATCH")
        self.assertEqual(report.mediated_host_run, report.direct_host_run)

    def test_permit_is_single_use(self) -> None:
        first = self.mediate()
        second = self.mediate(consumed_permit_ids=first.consumed_permit_ids)
        self.assertEqual(first.executed_actions, 1)
        self.assertEqual(second.executed_actions, 0)
        self.assertEqual(second.outcome.reason_code, "PERMIT_ALREADY_CONSUMED")
        self.assertEqual(second.mediated_host_run, second.direct_host_run)

    def test_duplicate_consumed_permit_ids_are_rejected(self) -> None:
        with self.assertRaises(ValueError):
            self.mediate(consumed_permit_ids=(self.permit.permit_id, self.permit.permit_id))

    def test_authority_grant_is_hold_only_and_one_action(self) -> None:
        self.assertEqual(self.advisory.grant.allowed_actions, (mediation.authority.HOLD,))
        self.assertEqual(self.advisory.grant.max_actions, 1)
        self.assertEqual(sum(item.would_authorize for item in self.advisory.outcomes), 1)

    def test_permit_issuance_requires_exactly_one_hold_candidate(self) -> None:
        altered = replace(
            self.advisory,
            outcomes=tuple(
                replace(item, would_authorize=False, disposition=mediation.authority.REJECTED)
                for item in self.advisory.outcomes
            ),
        )
        with self.assertRaises(ValueError):
            mediation.issue_hold_permit(altered, current_epoch=self.epoch)

    def test_unknown_request_cannot_execute(self) -> None:
        requests = list(self.advisory.requests)
        target = requests[self.permit.request_id - 1]
        requests[self.permit.request_id - 1] = replace(
            target,
            source_decision=mediation.v01_governance.UNKNOWN,
            requested_action=mediation.authority.ABSTAIN,
            source_ternary=0,
        )
        altered = replace(self.advisory, requests=tuple(requests))
        report = mediation.mediate_with_hold(
            self.jobs, altered, self.permit, current_epoch=self.epoch
        )
        self.assertEqual(report.executed_actions, 0)
        self.assertEqual(report.outcome.reason_code, "AUTHORITY_REQUEST_SET_MISMATCH")

    def test_stale_authority_session_cannot_execute(self) -> None:
        changed_jobs = self.jobs + (mediation.ordinary_host.Job("J008", "ADD", 1),)
        report = mediation.mediate_with_hold(
            changed_jobs, self.advisory, self.permit, current_epoch=self.epoch
        )
        self.assertEqual(report.executed_actions, 0)
        self.assertEqual(report.outcome.reason_code, "SESSION_DIGEST_MISMATCH")

    def test_active_hold_preserves_intended_state_delta_only(self) -> None:
        report = self.mediate()
        self.assertEqual(report.direct_host_run.final_value, 43)
        self.assertEqual(report.mediated_host_run.final_value, 43)
        self.assertEqual(report.direct_host_run.completed_ids, report.mediated_host_run.completed_ids)
        self.assertEqual(report.direct_host_run.rejected_ids, report.mediated_host_run.rejected_ids)
        self.assertEqual(report.direct_host_run.delayed_ids, ("J005",))
        self.assertEqual(report.mediated_host_run.delayed_ids, ())
        self.assertEqual(len(report.dispatched_jobs), len(self.jobs) - 1)

    def test_dispatched_jobs_keep_original_relative_order(self) -> None:
        report = self.mediate()
        expected = tuple(job for job in self.jobs if job.job_id != "J005")
        self.assertEqual(report.dispatched_jobs, expected)

    def test_input_jobs_are_not_mutated(self) -> None:
        before = repr(self.jobs)
        self.mediate()
        self.assertEqual(repr(self.jobs), before)

    def test_safe_detach_restores_exact_original_host_behavior(self) -> None:
        report = self.mediate()
        detached = mediation.ordinary_host.run_jobs(self.jobs)
        self.assertEqual(detached, report.direct_host_run)

    def test_mediation_receipts_replay(self) -> None:
        report = self.mediate()
        replay = mediation.replay_receipts(report.receipts)
        self.assertTrue(replay.passed)
        self.assertEqual(replay.final_digest, report.mediation_digest)

    def test_tampered_mediation_receipt_is_detected(self) -> None:
        report = self.mediate()
        tampered = mediation.tamper_receipt(report.receipts, 2, "tampered")
        self.assertFalse(mediation.replay_receipts(tampered).passed)

    def test_missing_mediation_receipt_changes_terminal_digest(self) -> None:
        report = self.mediate()
        replay = mediation.replay_receipts(report.receipts[:-1])
        self.assertTrue(replay.passed)
        self.assertNotEqual(replay.final_digest, report.mediation_digest)

    def test_repeated_active_run_is_exact(self) -> None:
        first = self.mediate()
        second = self.mediate()
        self.assertEqual(first.outcome, second.outcome)
        self.assertEqual(first.held_jobs, second.held_jobs)
        self.assertEqual(first.mediated_host_run, second.mediated_host_run)
        self.assertEqual(first.receipts, second.receipts)
        self.assertEqual(first.mediation_digest, second.mediation_digest)

    def test_qualified_sources_and_frozen_release_are_unchanged(self) -> None:
        sources_before = mediation._snapshot_sources()
        frozen_before = mediation._tree_digest(mediation.FROZEN_V01_ROOT)
        self.mediate()
        self.assertEqual(mediation._snapshot_sources(), sources_before)
        self.assertEqual(mediation._tree_digest(mediation.FROZEN_V01_ROOT), frozen_before)

    def test_all_mediation_ternary_values_are_exact(self) -> None:
        active = self.mediate()
        denied = self.mediate(permit=None)
        self.assertIn(active.outcome.ternary, (-1, 0, 1))
        self.assertIn(denied.outcome.ternary, (-1, 0, 1))
        self.assertIsInstance(active.outcome.ternary, int)
        self.assertIsInstance(denied.outcome.ternary, int)

    def test_invalid_epoch_type_is_rejected(self) -> None:
        with self.assertRaises(TypeError):
            mediation.prepare_hold_authority(self.jobs, current_epoch=True)
        with self.assertRaises(TypeError):
            mediation.mediate_with_hold(
                self.jobs, self.advisory, self.permit, current_epoch=True
            )

    def test_invalid_permit_issuer_is_rejected(self) -> None:
        with self.assertRaises(ValueError):
            mediation.issue_hold_permit(
                self.advisory, current_epoch=self.epoch, issuer=""
            )


if __name__ == "__main__":
    unittest.main(verbosity=2)
