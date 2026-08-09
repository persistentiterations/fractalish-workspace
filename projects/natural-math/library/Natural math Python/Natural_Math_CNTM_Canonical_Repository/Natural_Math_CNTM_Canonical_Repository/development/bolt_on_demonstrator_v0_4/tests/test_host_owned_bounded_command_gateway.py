#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
import json
from dataclasses import replace
from pathlib import Path
import subprocess
import sys
import unittest

sys.dont_write_bytecode = True

THIS_FILE = Path(__file__).resolve()
PROJECT_DIR = THIS_FILE.parents[1]
REPOSITORY_ROOT = THIS_FILE.parents[3]
INTEGRATION_PATH = PROJECT_DIR / "integration" / "host_owned_bounded_command_gateway.py"
PROJECTOR_PATH = PROJECT_DIR / "adapters" / "bounded_action_projector.py"
GATEWAY_PATH = PROJECT_DIR / "gateways" / "host_owned_command_gateway.py"


def load_module(name: str, path: Path):
    existing = sys.modules.get(name)
    if existing is not None:
        return existing
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


stage4 = load_module("v04_stage4_test_integration", INTEGRATION_PATH)
projector = stage4.projector_module
gateway = stage4.gateway_module
host = stage4.host


class ProjectorContractTests(unittest.TestCase):
    def test_identity_valid(self):
        identity = projector.build_identity()
        self.assertEqual(projector.validate_identity(identity), (True, "VALID"))

    def test_identity_execution_authority_none(self):
        self.assertEqual(projector.build_identity().execution_authority, "NONE")

    def test_identity_command_transport_empty(self):
        self.assertEqual(projector.build_identity().command_transport, ())

    def test_supported_actions_exact(self):
        self.assertEqual(projector.build_identity().supported_actions, ("HOLD", "RELEASE"))

    def test_action_map_exact(self):
        self.assertEqual(projector.ACTION_MAP, {"HOLD": "PAUSE_JOB", "RELEASE": "RESUME_JOB"})

    def test_projector_source_binding(self):
        self.assertEqual(stage4._sha256_file(PROJECTOR_PATH), stage4.EXPECTED_PROJECTOR_SOURCE_SHA256)

    def test_projector_self_check(self):
        completed = subprocess.run(
            [sys.executable, str(PROJECTOR_PATH)], cwd=REPOSITORY_ROOT,
            capture_output=True, text=True, encoding="utf-8", errors="replace"
        )
        self.assertEqual(completed.returncode, 0)
        self.assertIn("BOUNDED ACTION PROJECTOR SELF-CHECK: PASS", completed.stdout)

    def test_hold_projection_fields(self):
        service, envelope, permit = stage4.build_attack_fixture()
        self.assertEqual(envelope["action"], "HOLD")
        self.assertEqual(envelope["native_operation"], "PAUSE_JOB")
        self.assertEqual(envelope["expected_native_state"], "RUNNING")
        self.assertEqual(envelope["expected_native_version"], 3)
        self.assertFalse(envelope["executed"])
        self.assertTrue(envelope["would_dispatch"])
        self.assertIsNotNone(permit)
        self.assertEqual(service.snapshot().records[0].state, "RUNNING")

    def test_hold_envelope_valid(self):
        _, envelope, _ = stage4.build_attack_fixture()
        self.assertEqual(projector.validate_envelope_record(envelope), (True, "VALID"))

    def test_release_projection_fields(self):
        campaign = stage4.run_live_campaign()
        envelope = campaign.release_envelope
        self.assertEqual(envelope.action, "RELEASE")
        self.assertEqual(envelope.native_operation, "RESUME_JOB")
        self.assertEqual(envelope.expected_native_state, "PAUSED")
        self.assertEqual(envelope.expected_native_version, 4)
        self.assertFalse(envelope.executed)

    def test_envelope_digest_detects_tamper(self):
        _, envelope, _ = stage4.build_attack_fixture()
        row = dict(envelope)
        row["subject_id"] = "TAMPER"
        valid, reason = projector.validate_envelope_record(row)
        self.assertFalse(valid)
        self.assertIn(reason, {"ENVELOPE_ID_MISMATCH", "ENVELOPE_DIGEST_MISMATCH"})

    def test_envelope_executed_true_rejected(self):
        _, envelope, _ = stage4.build_attack_fixture()
        row = dict(envelope)
        row["executed"] = True
        row = stage4._rehash_envelope(row)
        self.assertEqual(projector.validate_envelope_record(row), (False, "HIDDEN_EXECUTION_AUTHORITY"))

    def test_wrong_operation_rejected(self):
        _, envelope, _ = stage4.build_attack_fixture()
        row = dict(envelope)
        row["native_operation"] = "COMPLETE_JOB"
        row = stage4._rehash_envelope(row)
        self.assertEqual(projector.validate_envelope_record(row), (False, "NATIVE_OPERATION_MAPPING_INVALID"))

    def test_wrong_idempotency_rejected(self):
        _, envelope, _ = stage4.build_attack_fixture()
        row = dict(envelope)
        row["idempotency_key"] = "WRONG"
        row = stage4._rehash_envelope(row)
        self.assertEqual(projector.validate_envelope_record(row), (False, "IDEMPOTENCY_KEY_MISMATCH"))

    def test_portable_request_uses_frozen_contract(self):
        service = stage4._build_setup_service()
        _, batch, _ = stage4._observe(service)
        subject = batch.subjects[0]
        event = batch.events[-1]
        request = projector.build_portable_request(
            request_id=700,
            action="HOLD",
            subject_id=subject.subject_id,
            source_observation_digest=event.observation_digest,
            governance_session_digest=stage4.GOVERNANCE_SESSION_DIGEST,
            authority_digest=stage4.AUTHORITY_DIGEST,
            observed_state=subject.observed_state,
            current_epoch=subject.native_version,
        )
        self.assertEqual(projector.frozen_v03.validate_action_request(request), (True, "VALID"))

    def test_projector_deterministic(self):
        service = stage4._build_setup_service()
        _, batch, _ = stage4._observe(service)
        first = stage4._project("HOLD", 701, batch)
        second = stage4._project("HOLD", 701, batch)
        self.assertEqual(first, second)

    def test_projector_does_not_change_host(self):
        service = stage4._build_setup_service()
        before = service.export_run()
        _, batch, _ = stage4._observe(service)
        stage4._project("HOLD", 702, batch)
        self.assertEqual(before, service.export_run())

    def test_structural_authority_scan(self):
        passed, hits = stage4.structural_authority_scan()
        self.assertTrue(passed, hits)


class GatewayBoundaryTests(unittest.TestCase):
    def test_gateway_source_binding(self):
        self.assertEqual(stage4._sha256_file(GATEWAY_PATH), stage4.EXPECTED_GATEWAY_SOURCE_SHA256)

    def test_gateway_self_check(self):
        completed = subprocess.run(
            [sys.executable, str(GATEWAY_PATH)], cwd=REPOSITORY_ROOT,
            capture_output=True, text=True, encoding="utf-8", errors="replace"
        )
        self.assertEqual(completed.returncode, 0)
        self.assertIn("HOST-OWNED COMMAND GATEWAY SELF-CHECK: PASS", completed.stdout)

    def test_gateway_owner_host(self):
        self.assertEqual(gateway.EXECUTION_OWNER, "HOST")

    def test_bolt_on_authority_none(self):
        self.assertEqual(gateway.BOLT_ON_EXECUTION_AUTHORITY, "NONE")

    def test_permit_valid(self):
        _, _, permit = stage4.build_attack_fixture()
        self.assertEqual(gateway.validate_permit(permit), (True, "VALID"))

    def test_permit_digest_tamper_rejected(self):
        _, _, permit = stage4.build_attack_fixture()
        bad = replace(permit, permit_digest=stage4.ZERO_DIGEST)
        self.assertEqual(gateway.validate_permit(bad), (False, "PERMIT_DIGEST_MISMATCH"))

    def test_valid_hold_executes_one_host_action(self):
        service, envelope, permit = stage4.build_attack_fixture()
        before = len(service.export_run().commands)
        decision = gateway.HostOwnedCommandGateway().process(envelope, permit, service)
        self.assertTrue(decision.accepted)
        self.assertTrue(decision.host_action_executed)
        self.assertEqual(len(service.export_run().commands), before + 1)
        self.assertEqual(service.snapshot().records[0].state, "PAUSED")

    def test_invalid_envelope_executes_no_host_action(self):
        service, envelope, permit = stage4.build_attack_fixture()
        before = service.export_run()
        row = dict(envelope); row["executed"] = True; row = stage4._rehash_envelope(row)
        decision = gateway.HostOwnedCommandGateway().process(row, permit, service)
        self.assertFalse(decision.accepted)
        self.assertFalse(decision.host_action_executed)
        self.assertEqual(before, service.export_run())

    def test_duplicate_rejected(self):
        duplicate, conflict, _ = stage4.run_duplicate_checks()
        self.assertTrue(duplicate)
        self.assertTrue(conflict)

    def test_decision_replay_passes(self):
        campaign = stage4.run_live_campaign()
        replay = gateway.replay_decisions(campaign.decisions)
        self.assertTrue(replay.passed)
        self.assertEqual(replay.accepted_count, 2)
        self.assertEqual(replay.host_action_count, 2)

    def test_decision_replay_detects_tamper(self):
        campaign = stage4.run_live_campaign()
        rows = list(campaign.decisions)
        rows[0] = replace(rows[0], reason="TAMPER")
        self.assertFalse(gateway.replay_decisions(rows).passed)

    def test_decision_replay_detects_reorder(self):
        campaign = stage4.run_live_campaign()
        rows = list(campaign.decisions)
        rows.reverse()
        self.assertFalse(gateway.replay_decisions(rows).passed)

    def test_gateway_decisions_hash_chained(self):
        campaign = stage4.run_live_campaign()
        self.assertEqual(campaign.decisions[0].previous_decision_digest, stage4.ZERO_DIGEST)
        self.assertEqual(campaign.decisions[1].previous_decision_digest, campaign.decisions[0].decision_digest)

    def test_gateway_native_operations_bounded(self):
        campaign = stage4.run_live_campaign()
        self.assertEqual({d.native_operation for d in campaign.decisions}, {"PAUSE_JOB", "RESUME_JOB"})

    def test_gateway_never_claims_bolt_on_execution(self):
        campaign = stage4.run_live_campaign()
        self.assertEqual(stage4.BOLT_ON_EXECUTION_AUTHORITY, "NONE")
        self.assertEqual(sum(int(d.host_action_executed) for d in campaign.decisions), 2)


class LiveCampaignTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.campaign = stage4.run_live_campaign()

    def test_two_projected_requests(self):
        self.assertEqual(len(self.campaign.decisions), 2)

    def test_hold_accepted(self):
        self.assertTrue(self.campaign.decisions[0].accepted)
        self.assertEqual(self.campaign.decisions[0].action, "HOLD")

    def test_release_accepted(self):
        self.assertTrue(self.campaign.decisions[1].accepted)
        self.assertEqual(self.campaign.decisions[1].action, "RELEASE")

    def test_final_state_done(self):
        record = self.campaign.host_run.snapshot.records[0]
        self.assertEqual(record.state, "DONE")
        self.assertEqual(record.version, 6)

    def test_six_native_actions(self):
        self.assertEqual(self.campaign.host_run.snapshot.applied_count, 6)
        self.assertEqual(self.campaign.host_run.snapshot.rejected_count, 0)

    def test_two_gateway_actions(self):
        self.assertEqual(sum(int(d.host_action_executed) for d in self.campaign.decisions), 2)

    def test_four_surrounding_native_actions(self):
        self.assertEqual(self.campaign.host_run.snapshot.applied_count - 2, 4)

    def test_direct_native_equivalence(self):
        self.assertEqual(self.campaign.host_run, self.campaign.direct_run)

    def test_native_run_digest_equal(self):
        self.assertEqual(self.campaign.host_run.run_digest, self.campaign.direct_run.run_digest)

    def test_native_replay_passes(self):
        self.assertTrue(self.campaign.native_replay.passed)
        self.assertEqual(self.campaign.native_replay.replay_digest, self.campaign.host_run.run_digest)

    def test_final_observation_replay_passes(self):
        replay = stage4.observer_module.replay_observation(self.campaign.final_observation)
        self.assertTrue(replay.passed)
        self.assertEqual(replay.replay_digest, self.campaign.final_observation.batch_digest)

    def test_final_observation_has_six_events(self):
        self.assertEqual(len(self.campaign.final_observation.events), 6)

    def test_projected_envelopes_executed_false(self):
        self.assertFalse(self.campaign.hold_envelope.executed)
        self.assertFalse(self.campaign.release_envelope.executed)

    def test_permits_are_distinct(self):
        self.assertNotEqual(self.campaign.hold_permit.permit_digest, self.campaign.release_permit.permit_digest)

    def test_requests_are_distinct(self):
        self.assertNotEqual(self.campaign.hold_request.request_digest, self.campaign.release_request.request_digest)

    def test_campaign_deterministic(self):
        self.assertEqual(self.campaign, stage4.run_live_campaign())


class QualificationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.qualification = stage4.run_stage4_qualification()

    def test_qualification_passes(self):
        self.assertTrue(self.qualification.passed)

    def test_frozen_verification_passes(self):
        self.assertTrue(self.qualification.frozen_verification_pass)

    def test_source_bindings_pass(self):
        self.assertTrue(self.qualification.source_bindings_pass)

    def test_source_unchanged(self):
        self.assertTrue(self.qualification.source_unchanged)

    def test_no_hidden_authority(self):
        self.assertTrue(self.qualification.no_hidden_authority)

    def test_all_adversarial_cases_rejected(self):
        self.assertEqual(
            self.qualification.adversarial_cases,
            self.qualification.adversarial_cases_safely_rejected,
        )

    def test_duplicate_and_conflict_rejected(self):
        self.assertTrue(self.qualification.duplicate_rejection_pass)
        self.assertTrue(self.qualification.idempotency_conflict_pass)

    def test_qualification_receipt_replay(self):
        self.assertEqual(
            self.qualification.qualification_receipt_digest,
            self.qualification.qualification_replay_digest,
        )

    def test_fixed_action_counts(self):
        self.assertEqual(self.qualification.gateway_host_actions, 2)
        self.assertEqual(self.qualification.surrounding_native_actions, 4)
        self.assertEqual(self.qualification.total_native_actions, 6)
        self.assertEqual(self.qualification.bolt_on_executed_actions, 0)

    def test_direct_script_passes(self):
        completed = subprocess.run(
            [sys.executable, str(INTEGRATION_PATH)], cwd=REPOSITORY_ROOT,
            capture_output=True, text=True, encoding="utf-8", errors="replace"
        )
        self.assertEqual(completed.returncode, 0, completed.stdout + completed.stderr)
        self.assertIn("STAGE 4 HOST-OWNED BOUNDED COMMAND GATEWAY: PASS", completed.stdout)

    def test_direct_script_deterministic(self):
        first = subprocess.run(
            [sys.executable, str(INTEGRATION_PATH)], cwd=REPOSITORY_ROOT,
            capture_output=True, text=True, encoding="utf-8", errors="replace"
        )
        second = subprocess.run(
            [sys.executable, str(INTEGRATION_PATH)], cwd=REPOSITORY_ROOT,
            capture_output=True, text=True, encoding="utf-8", errors="replace"
        )
        self.assertEqual(first.stdout, second.stdout)

    def test_qualification_replay_detects_summary_forgery(self):
        receipts = ()
        receipts = stage4.append_qualification_receipt(receipts, "SUMMARY", "STAGE-4", {
            "bolt_on_executed_actions": 1,
            "gateway_host_actions": 2,
            "total_native_host_actions": 6,
        })
        self.assertFalse(stage4.replay_qualification_receipts(receipts).passed)


class AdversarialMatrixTests(unittest.TestCase):
    pass


def _make_attack_test(index: int, name: str, envelope: object, permit: object):
    def test(self):
        service, _, _ = stage4.build_attack_fixture()
        before = service.export_run()
        decision = gateway.HostOwnedCommandGateway().process(envelope, permit, service)
        after = service.export_run()
        self.assertFalse(decision.accepted, name)
        self.assertFalse(decision.host_action_executed, name)
        self.assertEqual(before, after, name)
    test.__name__ = f"test_attack_{index:02d}_{name.lower()}"
    return test


for _index, (_name, _envelope, _permit) in enumerate(stage4.build_adversarial_cases(), 1):
    setattr(
        AdversarialMatrixTests,
        f"test_attack_{_index:02d}_{_name.lower()}",
        _make_attack_test(_index, _name, _envelope, _permit),
    )


if __name__ == "__main__":
    unittest.main()
