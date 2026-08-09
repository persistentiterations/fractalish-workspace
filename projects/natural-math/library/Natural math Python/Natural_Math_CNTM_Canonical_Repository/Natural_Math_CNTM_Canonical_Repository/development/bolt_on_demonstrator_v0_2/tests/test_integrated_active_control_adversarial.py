#!/usr/bin/env python3
import importlib.util,sys,unittest
from pathlib import Path
P=Path(__file__).resolve().parents[1]/'adversarial'/'integrated_active_control_adversarial.py'
s=importlib.util.spec_from_file_location('integrated_active_control_adversarial',P); m=importlib.util.module_from_spec(s); sys.modules[s.name]=m; s.loader.exec_module(m)
class Stage5Tests(unittest.TestCase):
 @classmethod
 def setUpClass(cls): cls.q=m.qualify_stage5(); cls.by={r.name:r for r in cls.q.results}
 def test_qualification(self): self.assertTrue(self.q.passed)
 def test_attack_count(self): self.assertEqual(self.q.attacks_run,12)
 def test_all_blocked(self): self.assertEqual(self.q.attacks_blocked,12)
 def test_forged_hold(self): self.assertTrue(self.q.forged_hold_permit_blocked)
 def test_forged_release(self): self.assertTrue(self.q.forged_release_permit_blocked)
 def test_reordered_cycle(self): self.assertTrue(self.q.reordered_cycle_receipts_blocked)
 def test_reordered_campaign(self): self.assertTrue(self.q.reordered_campaign_receipts_blocked)
 def test_duplicate_hold(self): self.assertTrue(self.q.duplicate_hold_blocked)
 def test_duplicate_release(self): self.assertTrue(self.q.duplicate_release_blocked)
 def test_stale_checkpoint(self): self.assertTrue(self.q.stale_checkpoint_blocked)
 def test_cross_session(self): self.assertTrue(self.q.cross_session_replay_blocked)
 def test_partial_detach(self): self.assertTrue(self.q.partial_detach_safe)
 def test_conflict(self): self.assertTrue(self.q.conflicting_evidence_blocked)
 def test_expired(self): self.assertTrue(self.q.expired_release_blocked)
 def test_tampered_evidence(self): self.assertTrue(self.q.tampered_hold_evidence_blocked)
 def test_baseline(self): self.assertTrue(self.q.baseline_campaign_preserved)
 def test_repeat_exact(self): self.assertTrue(self.q.repeated_attack_campaign_exact)
 def test_actions(self): self.assertTrue(self.q.no_extra_action_types)
 def test_host(self): self.assertTrue(self.q.host_state_unchanged)
 def test_digest_hex(self): self.assertEqual(len(self.q.attack_digest),64); int(self.q.attack_digest,16)
 def test_results_unique(self): self.assertEqual(len({r.name for r in self.q.results}),12)
 def test_evidence_digests_unique(self): self.assertEqual(len({r.evidence_digest for r in self.q.results}),12)
 def test_forged_hold_reason(self): self.assertIn('HASH',self.by['FORGED_HOLD_PERMIT'].reason)
 def test_forged_release_reason(self): self.assertEqual(self.by['FORGED_RELEASE_PERMIT'].reason,'RELEASE_PERMIT_HASH_MISMATCH')
 def test_duplicate_release_reason(self): self.assertEqual(self.by['DUPLICATE_RELEASE'].reason,'RELEASE_PERMIT_ALREADY_CONSUMED')
 def test_expired_reason(self): self.assertEqual(self.by['EXPIRED_RELEASE'].reason,'RELEASE_EPOCH_MISMATCH')
 def test_partial_detach_reason(self): self.assertEqual(self.by['PARTIAL_DETACH'].reason,'HELD_JOB_PRESERVED')
 def test_reordered_cycle_reason(self): self.assertNotEqual(self.by['REORDERED_CYCLE_RECEIPTS'].reason,'')
 def test_reordered_campaign_reason(self): self.assertNotEqual(self.by['REORDERED_CAMPAIGN_RECEIPTS'].reason,'')
 def test_campaign_digest_matches_stage4(self): self.assertEqual(self.q.baseline_campaign_digest,m.lifecycle.run_campaign().campaign_digest)
if __name__=='__main__': unittest.main(verbosity=2)
