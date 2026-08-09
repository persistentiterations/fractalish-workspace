#!/usr/bin/env python3
from __future__ import annotations
from dataclasses import replace
import importlib.util
from pathlib import Path
import sys
import unittest

THIS_FILE = Path(__file__).resolve()
PROJECT_DIR = THIS_FILE.parents[1]
PATH = PROJECT_DIR / "lifecycle" / "bounded_multi_action_lifecycle.py"
spec = importlib.util.spec_from_file_location("bounded_multi_action_lifecycle", PATH)
if spec is None or spec.loader is None:
    raise RuntimeError(PATH)
lifecycle = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = lifecycle
spec.loader.exec_module(lifecycle)


class BoundedMultiActionLifecycleTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.campaign = lifecycle.run_campaign()
        cls.qualification = lifecycle.qualify_stage4()

    def test_stage4_qualification_passes(self): self.assertTrue(self.qualification.passed)
    def test_four_cycles_exist(self): self.assertEqual(len(self.campaign.cycles), 4)
    def test_each_cycle_executes_hold(self): self.assertTrue(all(c.hold_report.executed_actions == 1 for c in self.campaign.cycles))
    def test_each_cycle_executes_release(self): self.assertTrue(all(c.release_report.executed_actions == 1 for c in self.campaign.cycles))
    def test_total_action_budget_is_exact(self): self.assertEqual(self.campaign.total_executed_actions, 8)
    def test_cycle_ids_are_unique(self): self.assertEqual(len({c.cycle_id for c in self.campaign.cycles}), 4)
    def test_hold_consumption_keys_are_unique(self): self.assertEqual(len(set(self.campaign.hold_consumption_keys)), 4)
    def test_release_consumption_keys_are_unique(self): self.assertEqual(len(set(self.campaign.release_consumption_keys)), 4)
    def test_expired_release_is_rejected(self): self.assertTrue(self.campaign.cycles[1].expired_attempt_rejected)
    def test_fresh_reauthorization_succeeds(self): self.assertTrue(self.campaign.cycles[1].release_report.released)
    def test_cross_cycle_release_is_rejected(self): self.assertTrue(self.campaign.cycles[1].cross_cycle_attempt_rejected)
    def test_checkpoint_recovery_succeeds(self): self.assertTrue(self.campaign.cycles[2].recovered)
    def test_checkpoint_is_bound_to_hold_digest(self): self.assertEqual(self.campaign.cycles[2].checkpoint.hold_mediation_digest, self.campaign.cycles[2].hold_report.mediation_digest)
    def test_checkpoint_tamper_is_detected(self):
        c=self.campaign.cycles[2]; bad=replace(c.checkpoint, held_job_id="X")
        self.assertFalse(lifecycle.validate_checkpoint(bad,c.hold_report)[0])
    def test_checkpoint_hash_tamper_is_detected(self):
        c=self.campaign.cycles[2]; bad=replace(c.checkpoint, checkpoint_hash="0"*64)
        self.assertEqual(lifecycle.validate_checkpoint(bad,c.hold_report)[1],"CHECKPOINT_HASH_MISMATCH")
    def test_detach_uses_exact_ordinary_host(self):
        c=self.campaign.cycles[3]; self.assertEqual(c.detached_host_run,lifecycle.ordinary_host.run_jobs(self.campaign.jobs))
    def test_detach_does_not_destroy_hold(self): self.assertEqual(len(self.campaign.cycles[3].hold_report.held_jobs),1)
    def test_release_after_detach_succeeds(self): self.assertTrue(self.campaign.cycles[3].release_report.released)
    def test_immutable_job_preserved_in_every_cycle(self): self.assertTrue(all(c.release_report.released_jobs == c.hold_report.held_jobs for c in self.campaign.cycles))
    def test_original_batch_restored_every_cycle(self): self.assertTrue(all(c.release_report.restored_batch == self.campaign.jobs for c in self.campaign.cycles))
    def test_host_rules_preserved_every_cycle(self):
        direct=lifecycle.ordinary_host.run_jobs(self.campaign.jobs)
        self.assertTrue(all(c.release_report.released_host_run == direct for c in self.campaign.cycles))
    def test_each_cycle_receipts_replay(self): self.assertTrue(all(c.replay.passed for c in self.campaign.cycles))
    def test_campaign_receipts_replay(self): self.assertTrue(self.campaign.replay.passed)
    def test_campaign_receipt_tamper_detected(self): self.assertFalse(lifecycle.replay_receipts(lifecycle.tamper_receipt(self.campaign.receipts,0)).passed)
    def test_cycle_receipt_tamper_detected(self):
        c=self.campaign.cycles[0]; self.assertFalse(lifecycle.replay_receipts(lifecycle.tamper_receipt(c.receipts,2)).passed)
    def test_repeated_campaign_is_exact(self): self.assertEqual(self.campaign,lifecycle.run_campaign())
    def test_campaign_digest_is_64_hex(self): self.assertEqual(len(self.campaign.campaign_digest),64); int(self.campaign.campaign_digest,16)
    def test_cycle_digests_are_unique(self): self.assertEqual(len({c.cycle_digest for c in self.campaign.cycles}),4)
    def test_boolean_epoch_rejected(self):
        with self.assertRaises(TypeError): lifecycle._cycle("BAD",self.campaign.jobs,True,1)
    def test_checkpoint_requires_active_hold(self):
        bad=replace(self.campaign.cycles[0].hold_report,held_jobs=())
        with self.assertRaises(ValueError): lifecycle.create_checkpoint("BAD",bad,1)
    def test_empty_cycle_id_rejected(self):
        with self.assertRaises(ValueError): lifecycle.create_checkpoint("",self.campaign.cycles[0].hold_report,1)
    def test_cross_cycle_hold_permit_is_blocked(self):
        c1,c2=self.campaign.cycles[:2]
        attempt=lifecycle.mediation.mediate_with_hold(self.campaign.jobs,c2.hold_report.authority_report,c1.hold_report.permit,current_epoch=c2.hold_epoch)
        self.assertFalse(attempt.outcome.executed)
    def test_release_permit_hashes_differ_across_cycles(self): self.assertEqual(len({c.release_report.permit.permit_hash for c in self.campaign.cycles}),4)
    def test_hold_permit_hashes_differ_across_cycles(self): self.assertEqual(len({c.hold_report.permit.permit_hash for c in self.campaign.cycles}),4)
    def test_no_new_action_types(self):
        actions={c.hold_report.permit.action for c in self.campaign.cycles}|{c.release_report.permit.action for c in self.campaign.cycles}
        self.assertEqual(actions,{"HOLD","RELEASE"})
    def test_released_job_remains_delayed_by_host(self): self.assertTrue(all(c.release_report.released_host_run.delayed_ids == ("J005",) for c in self.campaign.cycles))


if __name__ == "__main__": unittest.main(verbosity=2)
