#!/usr/bin/env python3
"""Qualification tests for v0.2 Stage 1 bounded authority contract."""

from __future__ import annotations

from dataclasses import replace
import importlib.util
from pathlib import Path
import sys
import unittest

THIS_FILE = Path(__file__).resolve()
PROJECT_DIR = THIS_FILE.parents[1]
MODULE_PATH = PROJECT_DIR / "authority" / "bounded_authority_contract.py"

spec = importlib.util.spec_from_file_location("bounded_authority_contract_v021", MODULE_PATH)
if spec is None or spec.loader is None:
    raise RuntimeError(f"could not load module from {MODULE_PATH}")
contract = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = contract
spec.loader.exec_module(contract)

EXPECTED_AUTHORITY_DIGEST = "8bfb57659ceb61e090c4042b0d08102c83cba48072905f702a1169753ddeb675"
EXPECTED_GRANT_HASH = "b080217ae79c6f5f88c585fb8e7546c211b148cc3acc78654ec56e27e230557f"


class BoundedAuthorityContractTests(unittest.TestCase):
    def setUp(self) -> None:
        self.jobs = contract.ordinary_host.baseline_jobs()
        self.governance = contract.v01_governance.run_shadow_governance(self.jobs)
        self.grant = contract.issue_grant(
            self.governance.governance_digest,
            valid_from_epoch=100,
            valid_through_epoch=100,
        )
        self.requests = contract.derive_requests(self.governance)

    def evaluate(self, grant=None, requests=None, epoch=100, session=None):
        return contract.evaluate_requests(
            self.grant if grant is None else grant,
            self.requests if requests is None else requests,
            current_epoch=epoch,
            expected_session_digest=(
                self.governance.governance_digest if session is None else session
            ),
        )

    def test_stage1_qualification_passes(self) -> None:
        result = contract.qualify_stage1(self.jobs)
        self.assertTrue(result.passed)
        self.assertEqual(result.executed_actions, 0)
        self.assertEqual(result.request_count, 8)
        self.assertEqual(result.would_authorize_count, 8)

    def test_fixed_release_digests_match(self) -> None:
        report = contract.run_dry_run_authority(self.jobs)
        self.assertEqual(report.authority_digest, EXPECTED_AUTHORITY_DIGEST)
        self.assertEqual(report.grant.grant_hash, EXPECTED_GRANT_HASH)

    def test_repeated_run_is_exact(self) -> None:
        first = contract.run_dry_run_authority(self.jobs)
        second = contract.run_dry_run_authority(self.jobs)
        self.assertEqual(first.grant, second.grant)
        self.assertEqual(first.requests, second.requests)
        self.assertEqual(first.outcomes, second.outcomes)
        self.assertEqual(first.receipts, second.receipts)
        self.assertEqual(first.authority_digest, second.authority_digest)

    def test_host_output_and_digest_are_unchanged(self) -> None:
        direct = contract.ordinary_host.run_jobs(self.jobs)
        report = contract.run_dry_run_authority(self.jobs)
        observed = report.governance_report.observation_report.host_run
        self.assertEqual(direct.canonical_text(), observed.canonical_text())
        self.assertEqual(direct.run_digest, observed.run_digest)

    def test_no_action_is_executed(self) -> None:
        report = contract.run_dry_run_authority(self.jobs)
        self.assertEqual(report.executed_actions, 0)
        self.assertTrue(all(not item.executed for item in report.outcomes))

    def test_missing_grant_fails_closed(self) -> None:
        outcomes = contract.evaluate_requests(
            None,
            self.requests,
            current_epoch=100,
            expected_session_digest=self.governance.governance_digest,
        )
        self.assertTrue(all(item.disposition == contract.REJECTED for item in outcomes))
        self.assertTrue(all(item.reason_code == "NO_GRANT" for item in outcomes))

    def test_grant_is_deterministic_and_valid(self) -> None:
        second = contract.issue_grant(
            self.governance.governance_digest,
            valid_from_epoch=100,
            valid_through_epoch=100,
        )
        self.assertEqual(self.grant, second)
        self.assertEqual(contract.validate_grant(self.grant), (True, "VALID"))

    def test_tampered_grant_is_rejected(self) -> None:
        tampered = replace(self.grant, max_actions=self.grant.max_actions + 1)
        self.assertEqual(contract.validate_grant(tampered)[0], False)
        outcomes = self.evaluate(grant=tampered)
        self.assertTrue(all(item.reason_code == "GRANT_HASH_MISMATCH" for item in outcomes))

    def test_grant_is_bound_to_one_session(self) -> None:
        outcomes = self.evaluate(session="f" * 64)
        self.assertTrue(
            all(item.reason_code == "SESSION_DIGEST_MISMATCH" for item in outcomes)
        )

    def test_not_yet_valid_grant_is_rejected(self) -> None:
        grant = contract.issue_grant(
            self.governance.governance_digest,
            valid_from_epoch=101,
            valid_through_epoch=102,
        )
        outcomes = self.evaluate(grant=grant, epoch=100)
        self.assertTrue(all(item.reason_code == "GRANT_NOT_YET_VALID" for item in outcomes))

    def test_expired_grant_is_rejected(self) -> None:
        grant = contract.issue_grant(
            self.governance.governance_digest,
            valid_from_epoch=98,
            valid_through_epoch=99,
        )
        outcomes = self.evaluate(grant=grant, epoch=100)
        self.assertTrue(all(item.reason_code == "GRANT_EXPIRED" for item in outcomes))

    def test_action_scope_is_enforced(self) -> None:
        grant = contract.issue_grant(
            self.governance.governance_digest,
            allowed_actions=(contract.DENY,),
            max_actions=8,
            valid_from_epoch=100,
            valid_through_epoch=100,
        )
        outcomes = self.evaluate(grant=grant)
        self.assertEqual(sum(item.would_authorize for item in outcomes), 2)
        self.assertTrue(
            all(
                item.would_authorize or item.reason_code == "ACTION_OUT_OF_SCOPE"
                for item in outcomes
            )
        )

    def test_action_budget_is_enforced(self) -> None:
        grant = contract.issue_grant(
            self.governance.governance_digest,
            max_actions=2,
            valid_from_epoch=100,
            valid_through_epoch=100,
        )
        outcomes = self.evaluate(grant=grant)
        self.assertEqual(sum(item.would_authorize for item in outcomes), 2)
        self.assertTrue(any(item.reason_code == "ACTION_BUDGET_EXHAUSTED" for item in outcomes))

    def test_zero_action_budget_rejects_every_action(self) -> None:
        grant = contract.issue_grant(
            self.governance.governance_digest,
            max_actions=0,
            valid_from_epoch=100,
            valid_through_epoch=100,
        )
        outcomes = self.evaluate(grant=grant)
        self.assertEqual(sum(item.would_authorize for item in outcomes), 0)
        self.assertTrue(all(item.reason_code == "ACTION_BUDGET_EXHAUSTED" for item in outcomes))

    def test_unknown_always_abstains(self) -> None:
        request = contract.InterventionRequest(
            request_id=1,
            job_ordinal=1,
            job_id="UNKNOWN_JOB",
            source_decision=contract.v01_governance.UNKNOWN,
            requested_action=contract.ABSTAIN,
            source_ternary=0,
            evidence_digest="0" * 64,
        )
        grant = contract.issue_grant(
            self.governance.governance_digest,
            max_actions=1,
            valid_from_epoch=100,
            valid_through_epoch=100,
        )
        outcome = self.evaluate(grant=grant, requests=(request,))[0]
        self.assertEqual(outcome.disposition, contract.ABSTAIN)
        self.assertFalse(outcome.would_authorize)
        self.assertFalse(outcome.executed)

    def test_duplicate_request_identifier_is_rejected(self) -> None:
        duplicate = replace(self.requests[1], request_id=self.requests[0].request_id)
        requests = (self.requests[0], duplicate) + self.requests[2:]
        outcomes = self.evaluate(requests=requests)
        self.assertEqual(outcomes[0].reason_code, "DUPLICATE_REQUEST_ID")
        self.assertEqual(outcomes[1].reason_code, "REQUEST_SEQUENCE_MISMATCH")

    def test_request_sequence_gap_is_rejected(self) -> None:
        altered = (replace(self.requests[0], request_id=2),) + self.requests[1:]
        outcomes = self.evaluate(requests=altered)
        self.assertEqual(outcomes[0].reason_code, "REQUEST_SEQUENCE_MISMATCH")

    def test_receipt_chain_replays(self) -> None:
        report = contract.run_dry_run_authority(self.jobs)
        replay = contract.replay_receipts(report.receipts)
        self.assertTrue(replay.passed)
        self.assertEqual(replay.final_digest, report.authority_digest)

    def test_tampered_receipt_is_detected(self) -> None:
        report = contract.run_dry_run_authority(self.jobs)
        tampered = contract.tamper_receipt(report.receipts, 1, "tampered")
        self.assertFalse(contract.replay_receipts(tampered).passed)

    def test_missing_receipt_changes_terminal_digest(self) -> None:
        report = contract.run_dry_run_authority(self.jobs)
        replay = contract.replay_receipts(report.receipts[:-1])
        self.assertTrue(replay.passed)
        self.assertNotEqual(replay.final_digest, report.authority_digest)

    def test_inputs_and_qualified_sources_are_unchanged(self) -> None:
        jobs_before = repr(self.jobs)
        sources_before = contract._snapshot_sources()
        frozen_before = contract._tree_digest(contract.FROZEN_V01_ROOT)
        contract.run_dry_run_authority(self.jobs)
        self.assertEqual(repr(self.jobs), jobs_before)
        self.assertEqual(contract._snapshot_sources(), sources_before)
        self.assertEqual(contract._tree_digest(contract.FROZEN_V01_ROOT), frozen_before)

    def test_all_gate_ternary_values_are_exact(self) -> None:
        outcomes = self.evaluate()
        self.assertTrue(all(item.ternary in (-1, 0, 1) for item in outcomes))
        self.assertTrue(all(isinstance(item.ternary, int) for item in outcomes))

    def test_invalid_grant_parameters_are_rejected(self) -> None:
        with self.assertRaises(TypeError):
            contract.issue_grant(self.governance.governance_digest, max_actions=True)
        with self.assertRaises(ValueError):
            contract.issue_grant(self.governance.governance_digest, max_actions=-1)
        with self.assertRaises(ValueError):
            contract.issue_grant(
                self.governance.governance_digest,
                valid_from_epoch=2,
                valid_through_epoch=1,
            )
        with self.assertRaises(ValueError):
            contract.issue_grant(
                self.governance.governance_digest,
                allowed_actions=(contract.ALLOW, contract.ALLOW),
            )


if __name__ == "__main__":
    unittest.main(verbosity=2)
